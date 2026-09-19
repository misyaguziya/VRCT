# VRCT — AMD GPU (ROCm) hardware check

*日本語は下にあります / Japanese below.*

Related: [issue #88](https://github.com/misyaguziya/VRCT/issues/88) ·
design notes: `src-python/docs/amd-gpu-support-design-2026-09-19.md`

## Why this exists

VRCT's GPU acceleration currently runs on CUDA. CTranslate2 — the one library
behind both VRCT's speech recognition and its translation — added official
ROCm/HIP support in February 2026, so AMD support has become technically
plausible. The remaining unknowns are not things we can look up: **we need to
know whether it actually works on a real Radeon, and whether it is actually
faster than the CPU path VRCT already has.**

Nobody on the project has an AMD GPU. That is the only reason this script
exists. If you have a Radeon RX 7000 or RX 9000 series card and 30 minutes,
running it would directly unblock the decision.

**Even a run that fails early is useful.** Several of the things we want to
know are "does this fail, and how". Please send the report either way.

## What it does and does not do

- It **does not send anything anywhere.** It writes `amd_spike_report.txt` next
  to wherever you run it. You read it, then decide whether to share it.
- It **does not touch your VRCT installation**, settings, or any of its files.
  It is a standalone diagnostic.
- It **does not require the AMD HIP SDK.** Whether the HIP runtime is available
  without it is one of the things we are trying to find out.
- Usernames and home directory paths are replaced with `<USER>` / `<HOME>` in
  the report. Please still skim it before sharing.

## Requirements

- Windows 10 or 11
- An AMD Radeon GPU — RX 7000 (RDNA3) or RX 9000 (RDNA4) is what we most want
  to hear about. Other cards are still interesting, especially if they fail.
- A recent AMD Adrenalin driver
- Python 3.11 (64-bit) — <https://www.python.org/downloads/>
- About 2 GB of disk for the model in Stage C (less if you use the tiny model)

## Setup

Open PowerShell in a folder of your choice.

**1. Create a clean virtual environment.** A clean one matters: if a CPU or
CUDA build of `ctranslate2` is already installed somewhere, the results are
meaningless.

```powershell
python -m venv .venv_amd_test
.\.venv_amd_test\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

**2. Install faster-whisper first.** This pulls in the regular PyPI
`ctranslate2`, which we overwrite in the next step. Doing it in this order
matters — if you install the ROCm wheel first, installing faster-whisper
afterwards would replace it with the CPU build.

```powershell
pip install faster-whisper==1.1.1
```

**3. Get the ROCm CTranslate2 wheel.** It is not on PyPI. Download
`rocm-python-wheels-Windows.zip` from a CTranslate2 release (v4.7.0 or later —
the latest is fine):

<https://github.com/OpenNMT/CTranslate2/releases>

Unzip it, then install the `.whl` inside it **over** the one pip just
installed:

```powershell
pip install --force-reinstall --no-deps <path-to-the-extracted>\ctranslate2-*.whl
```

`--no-deps` is important: without it pip may pull the PyPI `ctranslate2` back
in and undo this step.

**4. Run the check.**

```powershell
python check_amd.py
```

If you would rather start small and fast, do a first pass with the tiny model
(~75 MB instead of ~1.6 GB):

```powershell
python check_amd.py --model Systran/faster-whisper-tiny
```

You can also stop before the download entirely — Stage A alone answers two of
our questions and takes seconds:

```powershell
python check_amd.py --stage a
```

To measure with real speech instead of the generated test tone, pass a 16 kHz
mono wav:

```powershell
python check_amd.py --audio my_recording.wav
```

## What each stage is checking

The stages are ordered so that a failure makes the later ones pointless, and
the script stops when that happens.

**Stage A — HIP runtime** (seconds, no downloads)

| Check | Why we care |
|---|---|
| Can `amdhip64*.dll` be loaded, and from where? | If it comes from your driver rather than the HIP SDK, VRCT can ship AMD support without asking users to install anything extra. This decides roughly 130 MB of installer size. |
| Is it `hipblas.dll` or `libhipblas.dll`? | [CTranslate2 #2016](https://github.com/OpenNMT/CTranslate2/issues/2016) — the published wheel is built against ROCm 7.2, which renamed this file. Knowing which name your machine has tells us whether that bug will bite. |
| Do `hipInit` / `hipDeviceGetName` / `hipDeviceComputeCapability` exist, and what do they return? | VRCT needs these to list your GPU in its settings and to pick a precision. The reported "compute capability" also tells us your GPU generation. |

**Stage B — CTranslate2** (seconds)

Confirms you really have the ROCm build (by reading which libraries
`ctranslate2.dll` links against — a device count alone is not proof, since
CTranslate2 reports a count even on CPU-only builds) and that it can see your
GPU through its `cuda` API. The ROCm build reusing the name `"cuda"` is what
makes the VRCT change small, so this is worth confirming directly.

**Stage C — actually running Whisper** (downloads a model)

| Check | Why we care |
|---|---|
| Does the model load on the GPU with float16? | [CTranslate2 #2021](https://github.com/OpenNMT/CTranslate2/issues/2021) reports RX 9070 XT crashing here. If it crashes for you too, **the exact exception text is the single most valuable thing you can send us** — we use it to recognise out-of-memory errors properly. |
| Two threads using one model at once | VRCT transcribes your microphone and your speakers at the same time, through one model. A previous bug in a different library caused real freezes this way, so we do not want to assume this is safe. |
| Time per utterance, GPU vs CPU | **This is the deciding question.** VRCT already has a reasonably fast CPU path (`large-v3-turbo-int8`). If the GPU is not meaningfully faster, AMD support is not worth a separate installer edition. A result showing little gain is a genuinely useful answer, not a failed test. |

## What to send back

Attach or paste `amd_spike_report.txt` into
[issue #88](https://github.com/misyaguziya/VRCT/issues/88), plus:

- your GPU model and Adrenalin driver version
- whether you had the AMD HIP SDK installed beforehand (and if so, which version)

If the script stopped early, that is fine — send what it produced. If it
crashed hard enough to print nothing, the console output pasted as text is
just as good.

## If something goes wrong

- **"No HIP runtime found"** — update your Adrenalin driver and try again. If
  it still fails, that is itself a finding worth reporting.
- **"this looks like the NVIDIA/CUDA build"** — step 3 did not take effect.
  Check that you passed `--no-deps`, and that you are in the right venv.
- **Anything hangs** — close the window. A hang in the concurrency check is
  exactly one of the things we are looking for; please tell us where it hung.

Thank you — this genuinely is the part we cannot do ourselves.

---

# 日本語

関連: [issue #88](https://github.com/misyaguziya/VRCT/issues/88) ·
設計: `src-python/docs/amd-gpu-support-design-2026-09-19.md`

## これは何か

issue #88 (AMD GPU 対応) の実機検証を、Radeon を持っている協力者に依頼するための
スクリプトと手順。**開発側に AMD の実機が無いことが唯一の理由。**

設計調査の結果、配布・ライセンス・実装は「解ける」ことが確定した。
残る未知は 2 点だけで、どちらも調べ物では埋まらない。

1. **実機で本当に動くか** (CTranslate2 #2016 の DLL 不整合、#2021 の RDNA4 クラッシュ)
2. **CPU 版より本当に速いか** (VRCT は既に `large-v3-turbo-int8` の CPU 経路を持っている)

## 段階と、開発側が知りたいこと

前の段階が駄目なら後ろは意味がないので、失敗した時点で止まる設計。

| 段階 | 確認項目 | 設計上の対応 |
|---|---|---|
| A | `amdhip64*.dll` がドライバ由来か SDK 由来か | ドライバ由来なら同梱 130MB 以上を削減できる (設計 §6, spike 4) |
| A | `hipblas.dll` / `libhipblas.dll` のどちらがあるか | #2016 が実機で起きるかの判定 (spike 3、**最大の分岐点**) |
| A | `hipDeviceComputeCapability` の戻り値 | 「major 11/12 だけ一覧に出す」というアーキゲートの前提 (R3) |
| B | ROCm ビルドかどうか (PE インポート表を読む) | `get_cuda_device_count() > 0` では判定できない。CPU 版でも GPU が見えてしまうため (`test_utils_compute_device.py` の実測) |
| B | `get_supported_compute_types("cuda", i)` | `device="cuda"` 流用という設計前提の確認 (R1) |
| C | float16 でのモデルロード | #2021 の再現確認。**例外の文字列が OOM マーカー確定に必要** (R7) |
| C | 2 スレッド同時実行 | mic/speaker の 2 経路が同一モデルを叩く。過去に別ライブラリで実機フリーズあり (R9) |
| C | 1 発話レイテンシの CPU 比 | **これが本題。** 改善しないなら第 3 エディションを作る価値がない (spike 7) |

## 依頼時の注意

- スクリプトは**何も送信しない**。`amd_spike_report.txt` をローカルに書くだけ。
  ユーザー名とホームディレクトリは伏せ字にしてあるが、共有前に目視確認を促している。
- **VRCT 本体には一切触らない**。設定もファイルも読み書きしない。
- **HIP SDK のインストールを前提にしていない**。それが不要かどうかが検証項目そのものなので。
- 実行時の出力は**英語**。issue #88 の要望者が英語話者のため。
  コード中のコメントはリポジトリの作法どおり日本語。

## 手順書の落とし穴 (英語側に書いてある内容)

**faster-whisper を先に入れ、その後に ROCm wheel を上書きする**順序が重要。
逆にすると faster-whisper の依存解決で PyPI の CPU 版 `ctranslate2` に戻される。
上書き時は `--force-reinstall --no-deps` を付けないと同じことが起きる。

## 結果が返ってきたら

- `gpu_load_error` の文字列 → `utils.py` の `_OUT_OF_MEMORY_MARKERS` を実物に差し替える
  (PR-1 で「マーカーを足せば効く」構造にしてある)
- `hipblas_names` → #2016 の回避可否。駄目なら ROCm 7.1 での CT2 自前ビルドへ方針転換
- `hip_devices[].major` → アーキゲートを `(11, 12)` にするか `(11,)` に絞るか
- `thread_safety` → `hang` なら VRCT 側で GPU アクセスを直列化する必要がある
- `speedup` → 1.2 倍を下回るなら **AMD 対応を見送る判断もありうる**
