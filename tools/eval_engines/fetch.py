"""P5 の評価に使う物を取ってくる (標準ライブラリだけ)。

    python tools/eval_engines/fetch.py --root D:/path/to/vrct-eval

manifest.json の実行ファイル・モデルと、カタログ (native/data/model_catalog.json) の Whisper を
<root> に置き、FLEURS のテスト分から 4 言語に共通の文を n 件取り出す。どれも SHA-256 (FLEURS の
TSV は git の blob SHA-1) を照合し、合わなければ止まる。途中で切れたものは .part から再開する。
"""

import argparse
import array
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import sys
import tarfile
import urllib.request
import wave
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CHUNK = 1 << 20


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(CHUNK):
            h.update(block)
    return h.hexdigest()


def git_sha1_of(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def check(path, sha256=None, git_sha1=None):
    if sha256:
        return sha256_of(path) == sha256
    return git_sha1_of(path) == git_sha1


def download(url, dest, sha256=None, git_sha1=None):
    dest = Path(dest)
    if dest.is_file() and check(dest, sha256, git_sha1):
        print(f"ok      {dest}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    done = part.stat().st_size if part.exists() else 0
    request = urllib.request.Request(url, headers={"User-Agent": "vrct-eval"})
    if done:
        request.add_header("Range", f"bytes={done}-")
    with urllib.request.urlopen(request, timeout=60) as response:
        resumed = done and response.status == 206
        with open(part, "ab" if resumed else "wb") as out:
            shutil.copyfileobj(response, out, CHUNK)
    if not check(part, sha256, git_sha1):
        part.unlink()
        sys.exit(f"checksum mismatch: {url}")
    part.replace(dest)
    print(f"fetched {dest}")
    return dest


def extract_zip(archive, into):
    into = Path(into)
    if into.is_dir() and any(into.iterdir()):
        return
    into.mkdir(parents=True, exist_ok=True)
    root = into.resolve()
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            target = (into / name).resolve()
            if root not in target.parents and target != root:
                sys.exit(f"unsafe path in {archive}: {name}")
        z.extractall(into)
    print(f"extract {into}")


def fetch_whisper(root, ids):
    catalog = json.loads((REPO / "native/data/model_catalog.json").read_text(encoding="utf-8"))
    for model in catalog["models"]:
        if model["id"] not in ids:
            continue
        for f in model["files"]:
            url = f"https://huggingface.co/{model['repo']}/resolve/{model['revision']}/{f['path']}"
            download(url, root / "weights/whisper" / model["id"] / f["path"], sha256=f["sha256"])


def to_pcm16(data):
    """FLEURS's 32 bit float WAVE (16 kHz mono) as 16 bit PCM, what VRCT records and transcribes"""
    at, fmt, samples = 12, None, None
    while at + 8 <= len(data):
        size = struct.unpack_from("<I", data, at + 4)[0]
        if data[at:at + 4] == b"fmt ":
            fmt = struct.unpack_from("<HHIIHH", data, at + 8)
        elif data[at:at + 4] == b"data":
            samples = data[at + 8:at + 8 + size]
        at += 8 + size + (size & 1)
    tag, channels, rate, _, _, bits = fmt
    if (tag, channels, rate, bits) != (3, 1, 16000, 32):
        sys.exit(f"unexpected FLEURS format {fmt}")
    floats = array.array("f", samples[: len(samples) // 4 * 4])
    pcm = array.array("h", (max(-32768, min(32767, round(x * 32767))) for x in floats))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm.tobytes())
    return out.getvalue()


def read_tsv(path):
    # id, file name, raw transcription, normalized transcription, characters, samples, gender
    with open(path, encoding="utf-8", newline="") as f:
        return [row for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE) if len(row) >= 3]


def fetch_fleurs(root, spec):
    base = f"https://huggingface.co/datasets/google/fleurs/resolve/{spec['revision']}/data"
    raw = root / "fleurs-raw"
    rows = {}
    for lang, l in spec["languages"].items():
        tsv = download(f"{base}/{l['config']}/test.tsv", raw / l["config"] / "test.tsv", git_sha1=l["tsv_git_sha1"])
        rows[lang] = read_tsv(tsv)
    common = set.intersection(*({r[0] for r in rs} for rs in rows.values()))
    ids = sorted(common, key=int)[: spec["n"]]
    out = root / "data/fleurs"
    refs = {}
    for lang, l in spec["languages"].items():
        first = {}
        for r in rows[lang]:
            first.setdefault(r[0], r)
        wanted = {first[i][1]: i for i in ids}
        refs[lang] = {i: first[i][2] for i in ids}
        lang_dir = out / lang
        if lang_dir.is_dir() and len(list(lang_dir.glob("*.wav"))) == len(ids):
            print(f"ok      {lang_dir}")
            continue
        tar = download(f"{base}/{l['config']}/audio/test.tar.gz", raw / l["config"] / "test.tar.gz",
                       sha256=l["audio_sha256"])
        lang_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar, "r:gz") as t:
            for member in t:
                name = Path(member.name).name
                if member.isfile() and name in wanted:
                    (lang_dir / f"{wanted[name]}.wav").write_bytes(to_pcm16(t.extractfile(member).read()))
        print(f"extract {lang_dir} ({len(list(lang_dir.glob('*.wav')))} files)")
    (out / "refs.json").write_text(json.dumps({"ids": ids, "text": refs}, ensure_ascii=False, indent=1),
                                   encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", required=True, type=Path, help="where the evaluation files go (outside the repository)")
    parser.add_argument("--skip-fleurs", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    for f in manifest["files"]:
        path = download(f["url"], root / f["dest"], sha256=f["sha256"])
        if "extract" in f:
            extract_zip(path, root / f["extract"])
    fetch_whisper(root, manifest["whisper_from_catalog"])
    if not args.skip_fleurs:
        fetch_fleurs(root, manifest["fleurs"])


if __name__ == "__main__":
    main()
