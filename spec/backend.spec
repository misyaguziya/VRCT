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
    "amd": ".venv_amd",
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
    # AMD 側に相当するものは無い。ROCm のランタイムは Python パッケージでは
    # なく HIP SDK が置くただの DLL なので、hiddenimports では拾えない。
    # 下の _rocmRuntimeDatas() で明示的に同梱する。
    "amd": [],
}

# --- AMD (ROCm) ランタイムの同梱 ---------------------------------------------
#
# 収集ロジックは tools/rocm_bundle.py に置いてある。診断 exe
# (tools/amd_spike/check_amd.spec) と同じものを使うため。glob と gfx リストを
# 2箇所に書くと必ずドリフトする (backend_cuda.spec の hf_xet が実例)。
#
# 注意: この系統は現時点では開発・実機検証用で、配布はしていない。
# 実機で動くことを確認するまで release.yml もインストーラも触らない
# (設計 §9 の Phase 1 / Phase 3 の切り分け)。
import sys as _sys

# spec の置き場所。PyInstaller は SPECPATH を注入するが、この spec を
# 素の exec で評価する場面 (src-python/test/test_spec_editions.py) もあるので
# __file__ にもフォールバックする。
_spec_dir = globals().get('SPECPATH') or os.path.dirname(
    os.path.abspath(globals().get('__file__', 'spec')))
_sys.path.insert(0, os.path.join(_spec_dir, '..', 'tools'))
from rocm_bundle import rocmRuntimeDatas as _rocmRuntimeDatas  # noqa: E402

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
        ] + (_rocmRuntimeDatas() if _EDITION == "amd" else []),
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
