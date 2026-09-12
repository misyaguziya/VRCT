"""Package the local OSC sample player without sending any chat messages."""

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile

from chatbox_sample_player import load_samples


ROOT = Path(__file__).resolve().parents[1]
NAME = "VRCT-Chatbox-Sample-Player"


def build():
    if sys.platform != "win32" or sys.version_info[:2] != (3, 11) or sys.maxsize <= 2**32:
        raise RuntimeError("Build with CPython 3.11 x64 on Windows")
    versions = {}
    for line in (ROOT / "requirements-chatbox-sample-player.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, expected = line.split("==")
            versions[name] = metadata.version(name)
            if versions[name] != expected:
                raise RuntimeError(f"Expected {line}; use requirements-chatbox-sample-player.txt")
    source = ROOT / "tools/chatbox_samples"
    samples = load_samples(source)
    work = ROOT / "build/chatbox_sample_player"
    work.mkdir(parents=True, exist_ok=True)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    environment = os.environ.copy()
    windows = Path(os.environ["SystemRoot"])
    environment["PATH"] = os.pathsep.join(str(p) for p in (
        Path(sys.executable).parent, Path(sys.base_prefix), Path(sys.base_prefix) / "DLLs",
        windows / "System32", windows))
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    with tempfile.TemporaryDirectory(prefix="package_", dir=work) as temporary:
        stage = Path(temporary) / NAME
        (stage / "chatbox_samples").mkdir(parents=True)
        for path in source.glob("*.json"):
            shutil.copy2(path, stage / "chatbox_samples" / path.name)
        shutil.copy2(source / "README.txt", stage)
        licenses = stage / "licenses"
        licenses.mkdir()
        shutil.copy2(ROOT / "LICENSE", licenses / "VRCT-MIT.txt")
        shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", licenses / "Python.txt")
        for name in versions:
            distribution = metadata.distribution(name)
            files = [f for f in distribution.files or []
                     if any(word in f.name.lower() for word in ("license", "copying", "notice"))]
            if not files:
                raise RuntimeError(f"No license files for {name}")
            for relative in files:
                target = licenses / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(distribution.locate_file(relative), target)
        with (stage / "samples.jsonl").open("w", encoding="utf-8") as stream:
            for sample in samples:
                stream.write(json.dumps({**asdict(sample), "utf16_units": sample.units,
                                         "length": sample.length,
                                         "explicit_lines": sample.text.count("\n") + 1}, ensure_ascii=False) + "\n")
        (stage / "samples.txt").write_text("\n\n".join(
            f"[{s.id} / {s.length} / {s.units} UTF-16 units]\n{s.text}" for s in samples) + "\n",
            encoding="utf-8-sig")
        subprocess.run([sys.executable, "-m", "PyInstaller", str(ROOT / "spec/chatbox_sample_player.spec"),
                        "--distpath", str(stage), "--workpath", str(work / "pyinstaller"),
                        "--noconfirm", "--clean"], cwd=ROOT, env=environment, check=True)
        exe = stage / f"{NAME}.exe"
        for args in (["--list"], ["--dry-run", "--max-messages", "1"]):
            subprocess.run([str(exe), *args], cwd=temporary, env=environment, check=True,
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        info = {"built_at_utc": datetime.now(timezone.utc).isoformat(), "platform": "windows-x64",
                "python": platform.python_version(), "packages": versions, "samples": len(samples),
                "exe_sha256": hashlib.sha256(exe.read_bytes()).hexdigest()}
        (stage / "BUILD-INFO.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
        archive = dist / f"{NAME}-windows-x64.zip"
        temporary_archive = Path(temporary) / archive.name
        with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    package.write(path, f"{NAME}/{path.relative_to(stage).as_posix()}")
        shutil.copytree(stage, dist / NAME, dirs_exist_ok=True)
        temporary_archive.replace(archive)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
        print(f"Created: {archive} ({len(samples)} samples)")


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            for output in (exc.stdout, exc.stderr):
                if output:
                    print(output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output,
                          file=sys.stderr)
        raise SystemExit(1)
