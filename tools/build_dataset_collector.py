"""Build only the standalone collector; never clean or release the VRCT app."""

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


ROOT = Path(__file__).resolve().parents[1]
NAME = "VRCT-Dataset-Collector"
PACKAGES = ("numpy", "Pillow", "psutil", "openvr", "setuptools", "pyinstaller",
            "pyinstaller-hooks-contrib", "packaging", "altgraph", "typing_extensions")


def copy_licenses(destination: Path) -> dict:
    versions = {}
    destination.mkdir()
    shutil.copy2(ROOT / "LICENSE", destination / "VRCT-MIT.txt")
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", destination / "Python.txt")
    shutil.copy2(ROOT / "tools/dataset_collector/Valve-OpenVR-LICENSE.txt", destination)
    shutil.copy2(ROOT / "tools/dataset_collector/OpenSSL-LICENSE.txt", destination)
    for name in PACKAGES:
        distribution = metadata.distribution(name)
        versions[name] = distribution.version
        licenses = [f for f in distribution.files or []
                    if any(word in f.name.lower() for word in ("license", "copying", "notice"))]
        if not licenses:
            raise RuntimeError(f"No license files found for {name}")
        for relative in licenses:
            # Retain vendor paths so same-named LICENSE files do not collide.
            target = destination / name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(distribution.locate_file(relative), target)
    return versions


def build() -> Path:
    if sys.platform != "win32" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("Build with Windows x64 Python")
    if sys.version_info[:2] != (3, 11) or sys.maxsize <= 2**32:
        raise RuntimeError("Build with CPython 3.11 x64")
    for line in (ROOT / "requirements-dataset-collector.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, expected = line.split("==")
            if metadata.version(name) != expected:
                raise RuntimeError(f"Expected {line}; use requirements-dataset-collector.txt in a dedicated venv")
    work = ROOT / "build/dataset_collector"
    work.mkdir(parents=True, exist_ok=True)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    environment = os.environ.copy()
    windows = Path(os.environ["SystemRoot"])
    # Do not collect unrelated DLLs from a developer's tools on PATH.
    environment["PATH"] = os.pathsep.join(str(p) for p in (
        Path(sys.executable).parent, Path(sys.base_prefix), Path(sys.base_prefix) / "DLLs",
        windows / "System32", windows))
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    with tempfile.TemporaryDirectory(prefix="package_", dir=work) as temporary:
        stage = Path(temporary) / NAME
        stage.mkdir()
        versions = copy_licenses(stage / "licenses")
        shutil.copy2(ROOT / "tools/dataset_collector/README.txt", stage)
        subprocess.run([sys.executable, "-m", "PyInstaller", str(ROOT / "spec/dataset_collector.spec"),
                        "--distpath", str(stage), "--workpath", str(work / "pyinstaller"),
                        "--noconfirm", "--clean"], cwd=ROOT, env=environment, check=True)
        executable = stage / f"{NAME}.exe"
        # Run from outside the source tree and never capture user images during a build.
        subprocess.run([str(executable), "--help"], cwd=temporary, check=True, timeout=60,
                       env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run([str(executable), "--manual", "--duration", "0.1"], cwd=temporary,
                       check=True, timeout=60, env=environment, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        info = {"built_at_utc": datetime.now(timezone.utc).isoformat(),
                "platform": "windows-x64", "python": platform.python_version(),
                "packages": versions, "exe_sha256": hashlib.sha256(executable.read_bytes()).hexdigest()}
        (stage / "BUILD-INFO.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
        archive = dist / f"{NAME}-windows-x64.zip"
        temporary_archive = Path(temporary) / archive.name
        # Zip only the fresh staging tree, never an old dist/ or dataset directory.
        with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    package.write(path, f"{NAME}/{path.relative_to(stage).as_posix()}")
        # Copy only package files; preserve any existing collected images beside the exe.
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
