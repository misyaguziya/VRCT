# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / "tools/gemini_bbox_labeler.py")],
    pathex=[], binaries=[], datas=[], hiddenimports=[],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["numpy", "cv2", "matplotlib", "scipy", "pandas", "torch", "tensorflow", "openvr"],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="VRCT-Gemini-Annotator", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=True,
    icon=str(root / "src-tauri/icons/icon.ico"),
)
