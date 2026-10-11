"""重みの取得 (Hugging Face) と検証済みの印 (.weight_verified.json) を、今の Python 版のコードで記録する。

    python native/reference/export_weights.py   ->  native/testdata/weights/weights.json

downloadWhisperWeight / downloadCTranslate2Weight を一時フォルダへ呼び、要求・書かれたファイル・戻り値を
書く。印は更新時刻を決めて作ったファイルで writeWeightVerifiedCache / isWeightVerifiedCache を呼ぶ。
huggingface_hub がこの PC の Hugging Face トークンを自動で付けないよう HF_HUB_DISABLE_IMPLICIT_TOKEN を立てる。
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["HF_HUB_OFFLINE"] = "0"
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC / "models" / "translation"))
sys.path.insert(0, str(Path(__file__).parent))

from http_capture import capture  # noqa: E402

state = {"flaky": 0, "tree_fail": False}
TREES = {
    "Systran/faster-whisper-base": ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt", "README.md",
                                    ".gitattributes"],
    "jncraton/m2m100_418M-ct2-int8": ["config.json", "model.bin", "shared_vocabulary.json", "sub/inner.txt",
                                      "../evil.txt", "a/../b.txt", "missing.txt", "flaky.txt", "dir with space/x y.json"],
}


def responder(entry):
    url = entry["url"]
    if "/api/models/" in url:
        if state["tree_fail"]:
            return 500, {}, {"error": "server"}
        repo = url.split("/api/models/")[1].split("/tree/")[0]
        return 200, {}, [{"type": "file", "oid": f"oid{i}", "size": 10, "path": p}
                         for i, p in enumerate(TREES[repo])]
    if "/resolve/main/" in url:
        name = url.split("/resolve/main/")[1]
        if name.endswith("missing.txt") or name in ("preprocessor_config.json", "vocabulary.json"):
            return 404, {}, "not found"
        if name.endswith("flaky.txt") and state["flaky"] < 1:
            state["flaky"] += 1
            return 500, {}, "busy"
        return 200, {"content-type": "application/octet-stream"}, f"content of {name}".encode() * (
            3000 if name.endswith("model.bin") else 1)
    return 404, {}, {"error": "not found"}


def files_under(root):
    out = {}
    for dirpath, _, names in os.walk(root):
        for n in names:
            p = Path(dirpath) / n
            out[p.relative_to(root).as_posix()] = p.read_bytes().decode("utf-8", "replace")[:40]
    return dict(sorted(out.items()))


if __name__ == "__main__":
    # models.transcription.transcription_whisper imports `utils` from src-python
    from models.transcription.transcription_whisper import downloadWhisperWeight
    from translation_utils import downloadCTranslate2Weight
    from utils import isWeightVerifiedCache, writeWeightVerifiedCache

    steps = []

    def step(label, call):
        temp = Path(tempfile.mkdtemp())
        progress = []
        with capture(responder) as records:
            try:
                result = call(str(temp), progress)
            except Exception as e:
                result = {"error": type(e).__name__}
        steps.append({"step": label, "result": result, "progress_last": progress[-1] if progress else None,
                      "files": files_under(temp), "requests": records})
        print(label, result, len(records), list(files_under(temp))[:12])
        shutil.rmtree(temp, ignore_errors=True)

    step("whisper", lambda root, p: downloadWhisperWeight(root, "base", p.append, lambda: p.append("end")))
    step("ct2", lambda root, p: downloadCTranslate2Weight(root, "m2m100_418M-ct2-int8", p.append,
                                                          lambda: p.append("end")))
    state["tree_fail"] = True
    step("whisper tree fails", lambda root, p: downloadWhisperWeight(root, "base", p.append, lambda: p.append("end")))
    step("ct2 tree fails", lambda root, p: downloadCTranslate2Weight(root, "m2m100_418M-ct2-int8", p.append,
                                                                     lambda: p.append("end")))

    # .weight_verified.json
    temp = Path(tempfile.mkdtemp())
    (temp / "sub").mkdir()
    # tie*.bin: mtimes exactly halfway at 3 decimals (round() goes to even)
    files = {"model.bin": b"x" * 5, "sub/vocab.txt": b"vocab", "config.json": b"{}", "tie1.bin": b"", "tie2.bin": b"t"}
    times = {"model.bin": 1760140800123456700, "sub/vocab.txt": 1760140801999999900, "config.json": 1700000000000500000,
             "tie1.bin": 1700000000062500000, "tie2.bin": 1700000000187500000}
    for name, data in files.items():
        (temp / name).write_bytes(data)
        os.utime(temp / name, ns=(times[name], times[name]))
    writeWeightVerifiedCache(str(temp))
    marker = json.loads((temp / ".weight_verified.json").read_text(encoding="utf-8"))
    verified = isWeightVerifiedCache(str(temp))
    os.utime(temp / "config.json", ns=(times["config.json"] + 10_000_000, times["config.json"] + 10_000_000))
    verified_after_touch = isWeightVerifiedCache(str(temp))
    shutil.rmtree(temp, ignore_errors=True)

    out = ROOT / "native" / "testdata" / "weights" / "weights.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"trees": TREES, "steps": steps, "marker": {
        "files": {k: v.decode() for k, v in files.items()}, "mtime_ns": times, "written": marker,
        "verified": verified, "verified_after_touch": verified_after_touch}}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(out)
