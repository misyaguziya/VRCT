# -*- mode: python ; coding: utf-8 -*-
"""協力者へ渡す AMD 検証用 exe をビルドする。

    set VRCT_BUILD_EDITION=amd
    .venv_amd\\Scripts\\pyinstaller tools/amd_spike/check_amd.spec --distpath dist_amd_check

VRCT 本体ではなく tools/amd_spike/check_amd.py だけを固めた診断ツール。
Python も pip も ROCm wheel も要らず、展開して exe を叩くだけで
レポートが出る状態にして渡すのが目的。

VRCT 本体 (VRCT_amd.zip) を先に配らない理由:
AMD エディションには CPU フォールバックが無い
(docs/amd-gpu-support-design-2026-09-19.md §10.5)。ROCm の同梱が少しでも
間違っていると、協力者には「何も動かない」という情報しか返ってこない。
まずこの診断 exe で「ランタイムがロードできるか」「速いか」を確定させる。

ROCm ランタイムの収集は tools/rocm_bundle.py に寄せてあり、本体の
spec/backend.spec と同じものを使う。ここで同梱に成功すれば、本体側の
同梱も成立することの裏付けになる。
"""

import os
import sys

_spec_dir = globals().get('SPECPATH') or os.path.dirname(
    os.path.abspath(globals().get('__file__', '.')))
_tools_dir = os.path.abspath(os.path.join(_spec_dir, '..'))
_repo_root = os.path.abspath(os.path.join(_tools_dir, '..'))
sys.path.insert(0, _tools_dir)
from rocm_bundle import rocmRuntimeDatas  # noqa: E402

_use_upx = os.environ.get("VRCT_PYINSTALLER_UPX") == "1"

a = Analysis(
    [os.path.join(_tools_dir, 'amd_spike', 'check_amd.py')],
    pathex=[],
    binaries=[],
    # ROCm ランタイムを同梱する。HIP_PATH が無ければここで止まる。
    datas=rocmRuntimeDatas() + [
        # ダブルクリックで解放テストだけを回せるようにする。引数を付け忘れると
        # 20 分コースになり、協力者の時間を無駄にするため。
        (os.path.join(_tools_dir, 'amd_spike', 'run-release-check.bat'), '.'),
    ],
    # faster_whisper.vad は本体の spec と同じ理由で明示が要る
    # (遅延 import されるので依存解析に掛からない)。
    hiddenimports=['faster_whisper.vad'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 診断に要らない重いものを落とす。本体の spec より広めに切っている。
    excludes=[
        'pandas', 'matplotlib', 'PyQt5', 'tkinter',
        'openvr', 'OpenGL', 'glfw',          # VR オーバーレイ
        'rapidocr', 'cv2',                   # OCR
        'transformers', 'sentencepiece',     # 翻訳
        'langchain_openai', 'langchain_google_genai', 'google',
        'pycaw', 'pyaudiowpatch', 'pydub',   # 音声入出力
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VRCT-AMD-Check',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=_use_upx,
    console=True,          # レポートを画面で読ませるので必須
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
    name='VRCT-AMD-Check',
)
