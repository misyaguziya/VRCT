"""AMD (ROCm) ランタイムを PyInstaller の datas として集める。

`spec/backend.spec`（VRCT 本体の AMD エディション）と
`tools/amd_spike/check_amd.spec`（協力者へ渡す診断 exe）の両方から使う。
同じ glob と gfx リストを2箇所に書くと必ずドリフトするので1箇所に寄せた
（`spec/backend_cuda.spec` の hf_xet で実際にそれをやっている）。

背景（2026-09-20 に実測、docs/amd-gpu-support-design-2026-09-19.md §10.5）:
ROCm 版 ctranslate2.dll は hipblas.dll と amdhip64_7.dll を**静的に**
インポートする。CPU/CUDA 版が cuBLAS を遅延ロードするのとは違い、これらが
無いと `import ctranslate2` 自体が失敗する。つまり同梱は必須で、
失敗したときの CPU フォールバックも存在しない。

ライセンス: 同梱する DLL はいずれも MIT / Apache-2.0 with LLVM Exceptions で
再配布可。ただし著作権表示とライセンス文の同梱が義務
（docs/amd-gpu-support-feasibility-2026-09-19.md §5）。
"""

from __future__ import annotations

import glob
import os

# rocBLAS の Tensile カーネルを同梱する gfx ターゲット。
# RDNA3 = gfx1100/1101/1102、RDNA3.5 (APU) = gfx1150/1151、RDNA4 = gfx1200/1201。
# 全 gfx を入れると 900MB 近くなるので絞る。
#
# ここを増減させたときは src-python/utils.py の _AMD_SUPPORTED_ARCH_MAJORS も
# 合わせること。デバイス一覧に出す世代とカーネルを持っている世代が食い違うと、
# 選べるのに必ずモデル読み込みで失敗する。
# 両者の整合は src-python/test/test_spec_editions.py で検査している。
AMD_GFX_TARGETS = (
    "gfx1100", "gfx1101", "gfx1102",
    "gfx1150", "gfx1151",
    "gfx1200", "gfx1201",
)

# バンドル直下 (_internal/) へ置く DLL。PyInstaller の bootloader が
# _internal を DLL 検索パスに入れるので、実行時の追加処理は要らない見込み。
# datas (binaries ではない) で入れるのは、PyInstaller にこれら巨大な
# サードパーティ DLL の依存解析をさせないため。
AMD_RUNTIME_DLL_GLOBS = (
    "amdhip64*.dll",     # HIP ランタイム本体 (ROCm/clr, MIT)
    "amd_comgr*.dll",    # コンパイラランタイム (Apache-2.0 with LLVM Exceptions)
    "hipblas.dll",       # wheel が静的に要求する名前
    "libhipblas.dll",    # ROCm 7.1.x 以前の名前。#2016 のヘッジ
    "hipblaslt.dll",
    "libhipblaslt.dll",
    "rocblas.dll",
)


def rocmRuntimeDatas(hip_path: str | None = None):
    """HIP SDK から同梱する DLL と Tensile カーネルの datas を返す。

    hip_path 未指定なら環境変数 HIP_PATH を見る。
    見つからなければ SystemExit で止める。黙って ROCm 抜きの配布物を作ると、
    実行時に初めて壊れて原因が分からなくなる。
    """
    if hip_path is None:
        hip_path = os.environ.get("HIP_PATH", "")
    if not hip_path:
        raise SystemExit(
            "HIP_PATH is not set. Install the AMD HIP SDK for Windows "
            "(7.2.x or newer) first -- the ROCm runtime is not part of the "
            "ctranslate2 wheel."
        )
    hip_bin = os.path.join(hip_path, "bin")
    if not os.path.isdir(hip_bin):
        raise SystemExit(f"HIP_PATH does not look like an SDK: {hip_bin} is missing")

    datas = []
    for pattern in AMD_RUNTIME_DLL_GLOBS:
        for path in sorted(glob.glob(os.path.join(hip_bin, pattern))):
            datas.append((path, '.'))
    if not datas:
        raise SystemExit(f"no ROCm runtime DLLs found under {hip_bin}")

    # Tensile カーネル。rocblas.dll が自分の隣の rocblas/library から探すので、
    # この相対位置は崩さないこと。ファイル名に gfx ターゲットが入っているので
    # 同梱対象だけを選ぶ。どの gfx にも属さないファイル (共通のインデックス等)
    # は落とすと動かないので残す。
    library_dir = os.path.join(hip_bin, "rocblas", "library")
    if os.path.isdir(library_dir):
        for path in sorted(glob.glob(os.path.join(library_dir, "*"))):
            if not os.path.isfile(path):
                continue
            name = os.path.basename(path)
            if "gfx" in name and not any(t in name for t in AMD_GFX_TARGETS):
                continue
            datas.append((path, os.path.join('rocblas', 'library')))
    return datas
