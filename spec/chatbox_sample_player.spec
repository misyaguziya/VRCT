# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / "tools/chatbox_sample_player.py")],
    pathex=[], binaries=[], datas=[], hiddenimports=[],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="VRCT-Chatbox-Sample-Player", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=True,
    icon=str(root / "src-tauri/icons/icon.ico"),
)
