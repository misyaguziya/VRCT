# -*- mode: python ; coding: utf-8 -*-

import os

# ビルドするエディション。bat/build.bat と bat/build_cuda.bat が
# VRCT_BUILD_EDITION で渡す。既定を "cpu" にしているのは、素で
# `pyinstaller spec/backend.spec` を叩いたときに従来と同じ CPU 版が出るため。
#
# もともと backend.spec と backend_cuda.spec の2本に分かれていたが、差分は
# venv パス4行と hiddenimports の nvidia.* 2要素だけだった。しかも既に
# ドリフトしていた (backend_cuda.spec が hf_xet だけ .venv = CPU 側を指しており、
# CUDA 版のビルドが .venv の存在に依存していた)。3本目 (AMD) をコピーで足すと
# 同種の事故が確実に増えるので、1本にまとめた (AMD 対応 PR-3)。
_EDITION = os.environ.get("VRCT_BUILD_EDITION", "cpu")

_VENV_BY_EDITION = {
    "cpu": ".venv",
    "cuda": ".venv_cuda",
}
if _EDITION not in _VENV_BY_EDITION:
    raise SystemExit(
        f"VRCT_BUILD_EDITION must be one of {sorted(_VENV_BY_EDITION)}, got {_EDITION!r}"
    )
_VENV = _VENV_BY_EDITION[_EDITION]

# nvidia.cublas / nvidia.cudnn は ctranslate2 が GPU 実行時に LoadLibrary で
# 遅延ロードするDLLの提供元で、Python からは import されないので依存解析に
# 掛からない。ここで明示して pyinstaller-hooks-contrib の hook-nvidia.* に
# _internal/nvidia/<lib>/bin/ へ収集させる (2026-09-18 に torch を落とすまでは、
# torch が同梱していた同じDLL群が torch 経由で収集されていた)。実行時のDLL
# 検索パス登録は src-python/utils.py の _registerBundledGpuLibraries が行う。
_EXTRA_HIDDENIMPORTS_BY_EDITION = {
    "cpu": [],
    "cuda": ['nvidia.cublas', 'nvidia.cudnn'],
}

# UPX compression roughly doubles the PyInstaller collect step and adds
# a few seconds to sidecar startup. Default to disabled so ordinary
# rebuilds are fast; release scripts can opt in by setting
# VRCT_PYINSTALLER_UPX=1.
_use_upx = os.environ.get("VRCT_PYINSTALLER_UPX") == "1"


a = Analysis(
    ['..\\src-python\\mainloop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('./../src-python/models/overlay/fonts', 'fonts/'),
        ('./../src-python/models/translation/translation_settings/prompt', 'translation_settings/prompt/'),
        ('./../src-python/models/translation/translation_settings/languages', 'translation_settings/languages/'),
        ('./../src-python/models/ocr/onnx', 'ocr_onnx/'),
        (f'./../{_VENV}/Lib/site-packages/zeroconf', 'zeroconf/'),
        (f'./../{_VENV}/Lib/site-packages/openvr', 'openvr/'),
        (f'./../{_VENV}/Lib/site-packages/faster_whisper', 'faster_whisper/'),
        (f'./../{_VENV}/Lib/site-packages/hf_xet', 'hf_xet/'),
        (f'./../{_VENV}/Lib/site-packages/rapidocr', 'rapidocr/'),
        ],
    hiddenimports=[
        'faster_whisper.vad', 'models.transcription.audio_pipeline', 'rapidocr',
        'cv2', 'OpenGL', 'glfw', 'models.ocr',
        ] + _EXTRA_HIDDENIMPORTS_BY_EDITION[_EDITION],
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
    name='VRCT-sidecar-x86_64-pc-windows-msvc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=_use_upx,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=_use_upx,
    upx_exclude=[],
    name='.',
)
