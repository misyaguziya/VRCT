"""ソフトの更新 (GitHub のリリース一覧・setup.exe の取得と SHA-256 の照合・インストーラの引数) と
版の比較を、今の Python 版のコード (model.py / config.py / packaging) で記録する。

    python native/reference/export_update.py   ->  native/testdata/update/update.json

config の値 (チャンネル・現在の版・保存先・UI の言語) は差し替え、インストーラの起動とアプリの終了は
記録だけにする。setup.exe の中身は make_setup() の決まったバイト列 (Rust 側も同じものを作る)。
src-python/config.json は前後で退避して戻す。
"""

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).parent))

from http_capture import capture  # noqa: E402

SETUP_SIZE = 1024 * 1024 + 12345


def make_setup():
    return bytes((i * 7 + 3) % 251 for i in range(SETUP_SIZE))


SETUP = make_setup()
SETUP_SHA = hashlib.sha256(SETUP).hexdigest()


def release(name, tag, prerelease, sha=None, sha_url=None):
    assets = [{"name": "VRCT_setup.exe", "browser_download_url": f"https://github.com/x/{tag}/VRCT_setup.exe"}]
    if sha_url:
        assets.append({"name": "VRCT_setup.exe.sha256", "browser_download_url": sha_url})
    return {"name": name, "tag_name": tag, "prerelease": prerelease, "draft": False,
            "published_at": f"2026-10-0{len(tag) % 9}T00:00:00Z", "assets": assets}


RELEASES = [
    {"name": "3.8.0", "tag_name": "v3.8.0", "draft": True, "prerelease": False},
    release("3.7.0-beta.2", "v3.7.0-beta.2", True, sha_url="https://example.com/beta2.sha256"),
    release("3.6.1", "v3.6.1", False, sha_url="https://example.com/ok.sha256"),
    release("3.6.1-rc.1", "v3.6.1-rc.1", True),
    release("3.6.0", "v3.6.0", False, sha_url="https://example.com/bad.sha256"),
    release("3.5.0", "v3.5.0", False, sha_url="https://example.com/broken.sha256"),
    release("3.4.0", "v3.4.0", False),
    {"name": 3, "tag_name": "v3"}, "not a dict", {"tag_name": "v9"},
]
LATEST = RELEASES[2]


def responder(entry):
    url = entry["url"]
    if url.endswith("/releases/latest"):
        return 200, {}, LATEST
    if url.endswith("/releases"):
        return 200, {}, RELEASES
    if url.endswith("ok.sha256"):
        return 200, {"content-type": "text/plain"}, f"{SETUP_SHA.upper()}  VRCT_setup.exe\n"
    if url.endswith("beta2.sha256"):
        return 200, {"content-type": "text/plain"}, SETUP_SHA
    if url.endswith("bad.sha256"):
        return 200, {"content-type": "text/plain"}, "0" * 64
    if url.endswith("broken.sha256"):
        return 500, {}, "error"
    if url.endswith("VRCT_setup.exe"):
        if "/v3.4.0/" in url or "/v3.6.1-rc.1/" in url:
            return 404, {}, "not found"
        return 200, {"content-type": "application/octet-stream"}, SETUP
    return 404, {}, {"error": "not found"}


VERSIONS = ["3.6.0", "3.6.0-beta.1", "3.6.0b1", "3.6.0-rc.1", "3.6.0rc2", "3.6.1", "3.6", "3.6.0.0", "3.10.0",
            "3.4.3", "3.4.2", "v3.7.0", "3.7.0-alpha", "3.7.0.dev1", "3.7.0.post1", "1!1.0", "3.6.0+local.1",
            "3.6.0-beta", "3.6.0-beta.10", "3.6.0-beta.2", "3.6.0c1", "3.6.0pre1", "3.6.0-preview.3", " 3.6.0 ",
            "3.6.0.beta.1", "3.6.0_beta_1", "3.6.0-1", "not a version", "", "3..6"]


def main():
    backup = SRC / "config.json.export-backup"
    if (SRC / "config.json").exists():
        shutil.copy2(SRC / "config.json", backup)
    try:
        run()
    finally:
        if backup.exists():
            shutil.move(backup, SRC / "config.json")


def run():
    import model as model_module
    from config import config
    from packaging.version import InvalidVersion, parse
    Model = model_module.Model
    temp = Path(tempfile.mkdtemp())
    config._PATH_LOCAL = str(temp)
    config._UI_LANGUAGE = "ja"
    launched = []
    model_module.Popen = lambda args, cwd=None: launched.append({"args": args, "cwd_is_local": cwd == str(temp)})
    Model._quitApp = staticmethod(lambda: launched.append("quit"))
    steps = []

    def step(label, call, **settings):
        for key, value in settings.items():
            setattr(config, f"_{key}", value)
        launched.clear()
        (temp / "VRCT_setup.exe").unlink(missing_ok=True)
        with capture(responder) as records:
            try:
                result = call()
            except Exception as e:
                result = {"error": type(e).__name__}
        if isinstance(result, list):
            result = [r.__dict__ if hasattr(r, "__dict__") else r for r in result]
        setup = temp / "VRCT_setup.exe"
        steps.append({"step": label, "settings": settings, "result": result, "launched": list(launched),
                      "setup_written": setup.exists() and setup.read_bytes() == SETUP, "requests": records})
        print(label, repr(result)[:80], len(records), launched)

    for channel, version in [("stable", "3.6.0"), ("stable", "3.6.1"), ("beta", "3.6.0-beta.1"), ("beta", "3.8.0")]:
        step(f"check {channel} {version}", Model.checkSoftwareUpdated, SELECTED_RELEASE_CHANNEL=channel, VERSION=version)
    step("list releases", Model.listAvailableReleases, SELECTED_RELEASE_CHANNEL="stable", VERSION="3.6.0")
    for channel, target in [("stable", None), ("beta", None), ("stable", "3.6.1"), ("stable", "3.7.0-beta.2"),
                            ("stable", "3.6.0"), ("stable", "3.5.0"), ("stable", "3.6.1-rc.1"), ("stable", "3.4.0"),
                            ("stable", "9.9.9")]:
        step(f"update cpu {channel} {target}", lambda: Model.updateSoftware(target), SELECTED_RELEASE_CHANNEL=channel,
             VERSION="3.6.0")
    step("update gpu stable None", lambda: Model.updateCudaSoftware(None), SELECTED_RELEASE_CHANNEL="stable",
         VERSION="3.6.0")

    def key(v):
        try:
            return parse(v)
        except InvalidVersion:
            return None
    compare = []
    for a in VERSIONS:
        for b in VERSIONS:
            pa, pb = key(a), key(b)
            compare.append({"a": a, "b": b, "gt": None if pa is None or pb is None else pa > pb,
                            "eq": None if pa is None or pb is None else pa == pb})
    supported = {v: Model._isVersionSupported(v) for v in VERSIONS}
    channel = {v: config._channelForVersion(v) for v in VERSIONS}
    out = ROOT / "native" / "testdata" / "update" / "update.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"setup_size": SETUP_SIZE, "setup_sha256": SETUP_SHA, "releases": RELEASES,
                               "steps": steps, "compare": compare, "supported": supported, "channel": channel},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(temp, ignore_errors=True)
    print(out)


if __name__ == "__main__":
    main()
