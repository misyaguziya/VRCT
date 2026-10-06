"""Build the annotation wizard and verify it offline; no user images or keys."""

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

from PIL import Image
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
NAME = "VRCT-Gemini-Annotator"


def build() -> Path:
    if sys.platform != "win32" or sys.version_info[:2] != (3, 11) or sys.maxsize <= 2**32:
        raise RuntimeError("Build with CPython 3.11 x64 on Windows")
    versions = {}
    for line in (ROOT / "requirements-gemini-annotator.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, expected = line.split("==")
            versions[name] = metadata.version(name)
            if versions[name] != expected:
                raise RuntimeError(f"Expected {line}; use requirements-gemini-annotator.txt")
    installed = {canonicalize_name(d.metadata["Name"]) for d in metadata.distributions()}
    unexpected = installed - {canonicalize_name(n) for n in versions} - {"pip"}
    if unexpected:
        raise RuntimeError("Use a clean dedicated venv; additional distributions would affect bundling: "
                           + ", ".join(sorted(unexpected)))
    work = ROOT / "build/gemini_annotator"
    work.mkdir(parents=True, exist_ok=True)
    dist = ROOT / "tool-dist"
    dist.mkdir(exist_ok=True)
    env = os.environ.copy()
    windows = Path(os.environ["SystemRoot"])
    env["PATH"] = os.pathsep.join(str(p) for p in (
        Path(sys.executable).parent, Path(sys.base_prefix), Path(sys.base_prefix) / "DLLs",
        windows / "System32", windows))
    for key in ("PYTHONPATH", "PYTHONHOME", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI"):
        env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="package_", dir=work) as temporary:
        stage = Path(temporary) / NAME
        licenses = stage / "licenses"
        licenses.mkdir(parents=True)
        shutil.copy2(ROOT / "LICENSE", licenses / "VRCT-MIT.txt")
        shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", licenses / "Python.txt")
        shutil.copy2(ROOT / "tools/dataset_collector/OpenSSL-LICENSE.txt", licenses)
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
        shutil.copy2(ROOT / "tools/gemini_annotator/README.txt", stage)
        subprocess.run([sys.executable, "-m", "PyInstaller", str(ROOT / "spec/gemini_annotator.spec"),
                        "--distpath", str(stage), "--workpath", str(work / "pyinstaller"),
                        "--noconfirm", "--clean"], cwd=ROOT, env=env, check=True)
        exe = stage / f"{NAME}.exe"
        # A synthetic capture validates prepare/export outside the source checkout.
        fixture = Path(temporary) / "capture" / "session" / "unlabeled"
        fixture.mkdir(parents=True)
        Image.new("RGB", (80, 120), "navy").save(fixture / "synthetic.png")
        (fixture / "synthetic.json").write_text(json.dumps({
            "image": "synthetic.png", "width": 80, "height": 120,
            "session": "session", "run_id": "offline", "label": "unlabeled"}), encoding="utf-8")
        job = Path(temporary) / "test-job"
        for args in (["--help"], ["check"], ["prepare", str(fixture.parent.parent), "--out", str(job)],
                     ["status", str(job)], ["export", str(job)]):
            subprocess.run([str(exe), *args], cwd=temporary, env=env, check=True,
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        assert not (job / "attempts").exists()
        info = {"built_at_utc": datetime.now(timezone.utc).isoformat(), "platform": "windows-x64",
                "python": platform.python_version(), "packages": versions,
                "exe_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(), "offline_smoke_test": "PASS"}
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
    return archive


if __name__ == "__main__":
    try:
        print(f"Created: {build()}")
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            for output in (exc.stdout, exc.stderr):
                if output:
                    print(output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output,
                          file=sys.stderr)
        raise SystemExit(1)
