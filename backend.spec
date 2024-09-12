# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src-python\\webui_mainloop.py'],
    pathex=[],
    binaries=[],
    datas=[('./fonts', 'fonts/'), ('.venv/Lib/site-packages/zeroconf', 'zeroconf/'), ('.venv/Lib/site-packages/openvr', 'openvr/'), ('.venv/Lib/site-packages/pykakasi', 'pykakasi/')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pandas', 'matplotlib', 'PyQt5'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='backend-x86_64-pc-windows-msvc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src-ui\\assets\\chato_icon_fill.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='.',
)
