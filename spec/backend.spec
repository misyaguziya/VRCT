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
    # 下の _amdRuntimeDatas() で明示的に同梱する。
    "amd": [],
}

# --- AMD (ROCm) ランタイムの同梱 ---------------------------------------------
#
# ROCm 版 ctranslate2 の wheel は約21.6MB で、通常の PyPI 版とほぼ同じ大きさ
# しかない (実測 2026-09-19)。つまり ROCm のランタイムは wheel に入っておらず、
# 外から与える必要がある。CUDA 版が nvidia-*-cu12 wheel から cuBLAS/cuDNN を
# 取れるのとは事情が違う。
#
# Ollama / llama.cpp / koboldcpp-rocm と同じ方針で、ビルドマシンの HIP SDK から
# DLL を集めて配布物へ同梱する (エンドユーザーに SDK を入れさせない)。
# ライセンスはいずれも MIT / Apache-2.0 で再配布可能
# (docs/amd-gpu-support-feasibility-2026-09-19.md §5)。
#
# 注意: この系統は現時点では開発・実機検証用で、配布はしていない。
# 実機で動くことを確認するまで release.yml もインストーラも触らない
# (設計 §9 の Phase 1 / Phase 3 の切り分け)。
_HIP_PATH = os.environ.get("HIP_PATH", "")

# rocBLAS の Tensile カーネルを同梱する gfx ターゲット。
# RDNA3 = gfx1100/1101/1102、RDNA3.5 (APU) = gfx1150/1151、RDNA4 = gfx1200/1201。
# 全 gfx を入れると 900MB 近くなるので絞る。ここを増減させたときは
# src-python/utils.py の _AMD_SUPPORTED_ARCH_MAJORS も合わせること
# (デバイス一覧に出す世代と、カーネルを持っている世代が食い違うと、
# 選べるのに必ずモデル読み込みで失敗する)。
# 両者の整合は src-python/test/test_spec_editions.py で検査している。
_AMD_GFX_TARGETS = (
    "gfx1100", "gfx1101", "gfx1102",
    "gfx1150", "gfx1151",
    "gfx1200", "gfx1201",
)

# バンドル直下 (_internal/) へ置く DLL。PyInstaller の bootloader が
# _internal を DLL 検索パスに入れるので、実行時の追加処理は要らない見込み。
# datas (binaries ではない) で入れるのは、PyInstaller にこれら巨大な
# サードパーティ DLL の依存解析をさせないため。
_AMD_RUNTIME_DLL_GLOBS = (
    "amdhip64*.dll",     # HIP ランタイム本体 (ROCm/clr, MIT)
    "amd_comgr*.dll",    # コンパイラランタイム (Apache-2.0 with LLVM Exceptions)
    "hipblas.dll",
    "libhipblas.dll",    # ROCm 7.1.1 以前の名前。#2016 のヘッジ
    "hipblaslt.dll",
    "libhipblaslt.dll",
    "rocblas.dll",
)


def _amdRuntimeDatas():
    """HIP SDK から同梱する DLL と Tensile カーネルの datas を組み立てる。"""
    import glob as _glob

    if not _HIP_PATH:
        raise SystemExit(
            "VRCT_BUILD_EDITION=amd needs HIP_PATH set to the AMD HIP SDK "
            "(the ROCm runtime is not part of the ctranslate2 wheel)."
        )
    hip_bin = os.path.join(_HIP_PATH, "bin")
    if not os.path.isdir(hip_bin):
        raise SystemExit(f"HIP_PATH does not look like an SDK: {hip_bin} is missing")

    datas = []
    for pattern in _AMD_RUNTIME_DLL_GLOBS:
        for path in sorted(_glob.glob(os.path.join(hip_bin, pattern))):
            datas.append((path, '.'))
    if not datas:
        raise SystemExit(f"no ROCm runtime DLLs found under {hip_bin}")

    # Tensile カーネル。rocblas.dll が自分の隣の rocblas/library から探すので、
    # この相対位置は崩さないこと。ファイル名に gfx ターゲットが入っているので
    # 同梱対象だけを選ぶ。どの gfx にも属さないファイル (共通のインデックス等)
    # は落とすと動かないので残す。
    library_dir = os.path.join(hip_bin, "rocblas", "library")
    if os.path.isdir(library_dir):
        for path in sorted(_glob.glob(os.path.join(library_dir, "*"))):
            if not os.path.isfile(path):
                continue
            name = os.path.basename(path)
            has_gfx = "gfx" in name
            if has_gfx and not any(target in name for target in _AMD_GFX_TARGETS):
                continue
            datas.append((path, os.path.join('rocblas', 'library')))
    return datas

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
        ] + (_amdRuntimeDatas() if _EDITION == "amd" else []),
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
