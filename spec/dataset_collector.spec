# -*- mode: python ; coding: utf-8 -*-
"""Standalone Windows x64 collector. Build via bat/build_dataset_collector.bat."""

from importlib.util import find_spec
from pathlib import Path

root = Path(SPECPATH).parent
openvr_dir = Path(find_spec("openvr").origin).parent

a = Analysis(
    [str(root / "tools/ocr_dataset_collector.py")],
    pathex=[str(root / "tools")],
    binaries=[(str(openvr_dir / "libopenvr_api_64.dll"), "openvr")],
    datas=[(str(root / "src-python/models/ocr/ocr_capture_hwnd.py"), "capture")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Optional imaging/scientific integrations are not used for PNG capture.
    excludes=["torch", "cv2", "scipy", "pandas", "matplotlib", "tkinter", "IPython", "pytest",
              "yaml", "cffi", "pycparser"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="VRCT-Dataset-Collector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=str(root / "src-tauri/icons/icon.ico"),
)
