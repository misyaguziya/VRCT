"""ROCm (AMD) 版 CTranslate2 の wheel を取得して、実行中の venv へ入れる。

    python tools/fetch_ct2_rocm_wheel.py

bat/install.bat の .venv_amd ブロックから呼ばれる (AMD 対応 PR-5)。

なぜスクリプトが必要か:
ROCm 版 CTranslate2 は **PyPI に無い**。GitHub Releases に
`rocm-python-wheels-Windows.zip` として添付されているだけで、中に Python
バージョンごとの wheel が7個入っている。requirements に URL を直接書けない
(zip であって wheel ではない) ので、取得と展開をここでやる。

SHA-256 は下にピン留めしてある。不一致なら中止する (fail-closed)。
これは model.py の _downloadVerifiedSetup と同じ方針で、
「取れなかった/合わなかったら進めない」を守る。

CTranslate2 のバージョンが CPU版/CUDA版 (requirements.txt の 4.6.0) と
違う点に注意。ROCm wheel は 4.7.0 以降しか存在しないため。AMD 系統は
実機検証用の開発向けなので今はこれで進める (設計 §7)。
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "build" / "ct2_rocm"

# ピン留め。更新するときは3つ全部を一緒に直すこと。
# SHA-256 と size は GitHub の release asset API の digest/size から取れる
# (ダウンロード不要):
#   curl -s https://api.github.com/repos/OpenNMT/CTranslate2/releases/tags/<tag>
CT2_VERSION = "4.8.2"
ASSET_URL = (
    "https://github.com/OpenNMT/CTranslate2/releases/download/"
    f"v{CT2_VERSION}/rocm-python-wheels-Windows.zip"
)
ASSET_SHA256 = "43da4baa5feaee49f77e176277a9647f99c493173c81a0bc60f491cac97532c2"
ASSET_SIZE = 137538158

_CHUNK = 1024 * 1024


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".part")
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=60) as response, open(partial, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = response.read(_CHUNK)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / 1e6:6.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    print()
    partial.replace(dest)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetchVerifiedArchive() -> Path:
    """zip を取得して SHA-256 を検証する。キャッシュがあれば再利用する。"""
    archive = CACHE_DIR / f"ct2-rocm-windows-{CT2_VERSION}.zip"
    if archive.exists():
        if _sha256(archive) == ASSET_SHA256:
            print(f"using cached {archive.relative_to(REPO_ROOT)}")
            return archive
        print("cached archive does not match the pinned hash; re-downloading")
        archive.unlink()

    _download(ASSET_URL, archive)

    actual_size = archive.stat().st_size
    if actual_size != ASSET_SIZE:
        archive.unlink()
        raise SystemExit(
            f"downloaded size {actual_size} != expected {ASSET_SIZE}; aborting"
        )
    actual = _sha256(archive)
    if actual != ASSET_SHA256:
        archive.unlink()
        raise SystemExit(
            "SHA-256 mismatch; aborting (not installing an unverified wheel)\n"
            f"  expected {ASSET_SHA256}\n  actual   {actual}"
        )
    print("SHA-256 verified")
    return archive


def _wheelTagForThisInterpreter() -> str:
    """実行中の Python に合う wheel のタグ (例 "cp311")。"""
    return f"cp{sys.version_info.major}{sys.version_info.minor}"


def _extractMatchingWheel(archive: Path) -> Path:
    """この Python 向けの wheel を1つ取り出してパスを返す。"""
    tag = _wheelTagForThisInterpreter()
    with zipfile.ZipFile(archive) as zf:
        names = [n for n in zf.namelist() if n.endswith(".whl")]
        # free-threaded ビルド ("cp314t") は避け、通常版を選ぶ。
        matches = [n for n in names if f"-{tag}-{tag}-" in n]
        if not matches:
            available = sorted({n.split("/")[-1] for n in names})
            raise SystemExit(
                f"no wheel for {tag} in {archive.name}. available:\n  "
                + "\n  ".join(available)
            )
        member = matches[0]
        target = CACHE_DIR / Path(member).name
        with zf.open(member) as src, open(target, "wb") as out:
            while True:
                chunk = src.read(_CHUNK)
                if not chunk:
                    break
                out.write(chunk)
    print(f"extracted {target.name}")
    return target


def _install(wheel: Path) -> None:
    """現在の venv へ入れる。

    --no-deps が要る: 付けないと pip が依存解決で PyPI の (CPU版)
    ctranslate2 を引き直し、この wheel を上書きしてしまう。
    --force-reinstall は requirements.txt 側で既に入っている
    ctranslate2==4.6.0 を確実に置き換えるため。
    """
    print(f"installing into {sys.prefix}")
    subprocess.run(
        [sys.executable, "-m", "pip", "install",
         "--force-reinstall", "--no-deps", str(wheel)],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch and install the ROCm build of CTranslate2 (AMD GPUs)")
    parser.add_argument("--no-install", action="store_true",
                        help="fetch and extract only; do not run pip")
    args = parser.parse_args()

    archive = _fetchVerifiedArchive()
    wheel = _extractMatchingWheel(archive)
    if args.no_install:
        print(wheel)
        return 0
    _install(wheel)
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
