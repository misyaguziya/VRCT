# AMD GPU 対応 技術的実現可能性レポート (2026-09-19)

対象 issue: [#88 \[Feature\]: AMD GPU Support VIA RocM](https://github.com/misyaguziya/VRCT/issues/88)

`issue-triage-2026-07-31.md` で #88 は「実装・配布・検証コストが大きい」として Reject 候補に置かれ、
推奨対応は「需要観測を続け、**設計調査タスクへ分離**」だった。本レポートがその設計調査にあたる。

---

## 1. 結論

**技術的には可能。しかも 2026-02 に状況が大きく変わり、以前の「不可能」判定は既に古い。
ただし現時点では出荷できない。ブロッカーは VRCT 側ではなく上流と AMD 側にある。**

3 行で:

- CTranslate2 が 2026-02-02 に **公式で ROCm/HIP 対応をマージ**し、v4.7.0 以降 **Windows 向け wheel を配布**している。
- しかも AMD デバイスも `device="cuda"` のまま扱うので、**VRCT 側のコード変更は驚くほど小さい**（§4）。
- だが「wheel が ROCm 7.2 ビルドなのに AMD が Windows 向けに出している HIP SDK は 7.1.1 まで」という
  未解決の DLL 不整合（#2016）と、RDNA4 のクラッシュ（#2021）が残っている（§5）。

**2026-09-19 追記（先行事例調査の結果、当初の結論が一部変わった）:**

- 当初「致命的」としていた**「ユーザーに HIP SDK を要求する」問題は否定された**。
  Ollama / llama.cpp / koboldcpp-rocm は**ビルド時のみ SDK を使い、DLL を同梱して配っている**。
  とくに **koboldcpp-rocm は PyInstaller 配布という VRCT と同一形態の直接の前例**（§6.5 A）。
- **再配布ライセンスも問題なし。** `amdhip64.dll` (ROCm/clr) は **MIT**、
  `amd_comgr.dll` は **Apache-2.0 with LLVM Exceptions**、rocBLAS/hipBLAS も MIT。
  proprietary EULA の話ではなかった。義務はライセンス表記の同梱のみ（§5 ブロッカー 1'）。
- **容量も当初見積もりより小さい。約 280〜300MB**（当初 550〜930MB と書いたのは過大）。
  Ollama の zip を実地調査して算定した（§5）。VRCT の GPU 版は既に約 4GB なので許容範囲。
- **VRChat 領域の競合（TaSTT / VRCTextboxSTT）は 1 つも AMD 対応していない**（§6.5 B）。
  遅れているわけではなく、やれば差別化になる。
- 業界は whisper.cpp + Vulkan に収束しつつあるが、**それらは STT 専用アプリ**。
  **VRCT は翻訳でも CTranslate2 を使うので、Vulkan では GPU 負荷の半分しか解決しない**（§6.5 C）。
  CTranslate2-ROCm の「両方 GPU・推論コード変更ゼロ」は事例にない固有の利点。

判定: **今は採らない。ただし Reject（恒久的に不採用）ではなく、
「上流ブロッカー解消待ち + 実機検証（spike）」に格上げすべき。**

**実機不要の検証 3 項目は 2026-09-19 に完了した**（§7）。その結果、
**配布・ライセンス・実装の 3 つはいずれも「解ける」と確定**し、
**未知は「実機で動くか」と「速くなるか」の 2 点だけに絞られた。**
残る技術ブロッカーは CT2 #2016（回避策の候補あり）と #2021（RDNA4 の安定性）。

---

## 2. 現状 VRCT が GPU を使っている範囲（コード実測）

意外に狭い。**GPU で回っているのは 2 か所だけで、どちらも同じ 1 つのライブラリに集約されている。**

| 用途 | 呼び出し箇所 | 実行系 |
|---|---|---|
| 音声認識 (Whisper) | `models/transcription/transcription_whisper.py:199` | faster-whisper → **CTranslate2** |
| 機械翻訳 (NLLB/M2M100) | `models/translation/translation_translator.py:462` | **CTranslate2** 直接 |
| OCR (PP-OCR / YOLO) | `models/ocr/ocr_bubble_detector.py:102` | onnxruntime、**`CPUExecutionProvider` 固定** |
| VAD (Silero) | `models/transcription/audio_vad.py` | onnxruntime、CPU |

重要な帰結が 2 つある。

1. **AMD 対応は「2 つの問題」ではなく「1 つの問題」**。faster-whisper は CTranslate2 の
   ラッパーに過ぎないので、`CTranslate2 が AMD で動くか` だけが論点。
2. **OCR と VAD は現在 NVIDIA 環境でも CPU 実行**。つまり OCR は AMD/NVIDIA 間の
   格差要因ではない。「AMD 対応」として OCR を GPU 化する話は、
   AMD 対応ではなく**全ユーザー向けの別の最適化**であり、本件と混ぜて考えるべきではない。

### デバイス層はすでにほぼベンダー中立

`utils.py` の `getComputeDeviceList()` / `getBestComputeType()` は device 文字列と
compute_type を組み立てるだけの薄い層で、NVIDIA 固有なのは以下 3 点に限られる。

- `utils.py:411` — `cublas64_12.dll` をロードできるかで「この build は GPU 実行可能か」を判定
- `utils.py:445` — CUDA Driver API (`nvcuda.dll`) を直接叩いてデバイス名を取得
- `utils.py:484-495` — device 名の `GTX` / `RTX` / `Tesla` / `A100` / `Quadro` キーワード一致で
  compute_type の可否を決定（未知の名前は `float32` に落とす）

このうち 3 つ目が地味に効く。**AMD の GPU 名（例 `Radeon RX 7900 XTX`）はどのキーワードにも
一致しないので、現状のロジックのままでは自動的に `float32` 固定に落ちる。**
`float16`/`int8` を使わせるには、ここに明示的な分岐が必要（§4）。

### 配布は「2 ビルド 2 インストーラ」軸

- `COMPUTE_MODE` は起動時に CUDA デバイスが見つかったかで決まる (`config.py:1049`)。実行時切替ではない。
- CPU/GPU の切替は NSIS インストーラの再実行 (`/EDITION=cpu|gpu`, `model.py:1949`)。
- 配布物は `VRCT.zip` (約 485MB) と `VRCT_cuda.zip` (約 4GB) の 2 本 (`src-tauri/nsis/template.nsi:738-749`)。
- ビルド系統も 2 本: `spec/backend.spec` / `spec/backend_cuda.spec`、venv も `.venv` / `.venv_cuda` (`bat/install.bat`)。

**AMD を第 3 のエディションにすると、spec・venv・zip・インストーラのページ・locale 文言・
更新フロー (`updateCudaSoftware` 相当) が 1 系統まるごと増える。** ここが #88 triage の
「配布コストが大きい」の実体。

---

## 3. 2026-02 の状況変化（これが本レポートの主題）

前回調査時点の常識（「CTranslate2 は CUDA 専用、AMD は不可」）は**もう正しくない**。

| 事実 | 出典 |
|---|---|
| ROCm/HIP 対応 PR がマージ済み（2026-02-02、全 20 チェック pass） | [OpenNMT/CTranslate2 PR #1989](https://github.com/OpenNMT/CTranslate2/pull/1989) |
| 長年の要望 issue がこれで対応 | [Issue #1072](https://github.com/OpenNMT/CTranslate2/issues/1072) |
| v4.7.0 (2026-02-03) 以降、各 Release に `rocm-python-wheels-Windows.zip` (約 137MB) が添付。最新 v4.8.2 でも継続 | [Releases](https://github.com/OpenNMT/CTranslate2/releases) |
| **AMD でも `device="cuda"` を流用**（HIP を既存 CUDA API 経由で露出） | PR #1989 |
| ビルド対象は **gfx803〜gfx1201**（GCN3 〜 RDNA4 全域、gfx1150/1151 含む） | PR #1989 |
| faster-whisper-large-v3 (float16) が AMD Strix Halo で wheel のまま動作した報告 | PR #1989 コメント |

一方で注意点:

- **PyPI 配布されていない**。GitHub Releases から zip を手動取得する形のみ。
- **公式ドキュメントに一切記載がない**。`installation.html` は `-DWITH_HIP=ON` ビルドオプションの
  言及のみ、`hardware_support.html` は NVIDIA のみ。つまり**上流の扱いとしてまだ半公式**。

---

## 4. VRCT に適用する場合の変更見積もり

`device="cuda"` が流用される点が決定的で、**アプリ側の改修は小さい**。

| 箇所 | 変更内容 | 規模 |
|---|---|---|
| `requirements_amd.txt` (新規) | `requirements.txt` を include し、CT2 の ROCm wheel をローカル参照で指定 | 小 |
| `utils.py:411` | GPU 可否判定を `cublas64_12.dll` から HIP 相当 (`hipblas.dll`) にも対応させる | 小 |
| `utils.py:445` | デバイス名取得。`nvcuda.dll` が無い AMD 環境では HIP API または WMI にフォールバック | 中 |
| `utils.py:484-495` | compute_type のキーワード表に AMD を追加（`Radeon` 等）。RDNA3 以降は `float16` 可の想定だが**要実測** | 小 |
| `spec/backend_amd.spec` (新規) | `backend_cuda.spec` の `hiddenimports` から `nvidia.*` を外し HIP ランタイムを収集 | 中 |
| `bat/install.bat`, `bat/build_amd.bat` | `.venv_amd` 系統の追加 | 小 |
| `template.nsi`, `model.py`, `locales/*.yml`, `Updater.jsx` | 第 3 エディション（zip 名・容量要件・ラジオボタン・更新導線・4 言語の文言） | **中〜大** |

**コードの難所は推論側ではなく配布側**というのが結論。`transcription_whisper.py` と
`translation_translator.py` は**一行も変えなくてよい**見込み（`device` 文字列がそのまま `"cuda"` のため）。

---

## 5. それでも今は出荷できない理由

### ~~ブロッカー 1（決定的）: エンドユーザーに AMD HIP SDK のインストールを要求する見込み~~

**→ 2026-09-19 の追加調査で否定された。先行事例により解決手段は確立している。詳細は §6.5。**

当初の懸念は「HIP ランタイムがドライバ同梱ではなく AMD の HIP SDK 側から来るので、
ユーザーに SDK インストールを要求することになり配布として成立しない」だった。

しかし **Ollama / llama.cpp / koboldcpp-rocm は、ビルドマシン上でのみ HIP SDK を使い、
生成された DLL 群を配布物に同梱している**。エンドユーザーに必要なのは対応する AMD ドライバだけで、
SDK のインストールは要求されない。つまり VRCT でも**同じことができる**。

残るのは「できるか」ではなく **「同梱してよいか（ライセンス）」と「その容量を許容するか」**
という別種の問題に変わった。→ ブロッカー 1'（新規）へ。

### ~~ブロッカー 1'（新規・要ユーザー判断）: 再配布ライセンス~~ → **解消（2026-09-19 実地確認）**

当初「`amdhip64.dll` と `amd_comgr.dll` は AMD proprietary で再配布可否が不明」としていたが、
**上流のライセンスを一次資料で追ったところ、すべて permissive だった。**

| 同梱が必要な DLL | 上流リポジトリ | ライセンス | 再配布 |
|---|---|---|---|
| `amdhip64_*.dll` (HIP ランタイム) | [ROCm/clr](https://github.com/ROCm/clr/blob/develop/LICENSE.md) | **MIT** | 可 |
| `amd_comgr_*.dll` (コンパイラランタイム) | [ROCm/llvm-project `amd/comgr`](https://raw.githubusercontent.com/ROCm/llvm-project/amd-staging/amd/comgr/LICENSE.txt) | **Apache-2.0 with LLVM Exceptions** | 可（Object 形式の再配布を明示的に許諾） |
| `rocblas.dll` | ROCm/rocBLAS | **MIT** | 可 |
| `hipblas.dll` / `hipblaslt.dll` | ROCm | **MIT** | 可 |

AMD 公式のライセンスページも「ROCm はコンポーネント単位で個別にライセンスされる」と述べ、
HIP を MIT、Comgr を NCSA/Apache 系として列挙している。
**つまり proprietary EULA の問題ではなく、通常の permissive OSS の再配布であり、法務的な障害はない。**

**ただし義務が 1 つある: MIT / Apache-2.0 はいずれも著作権表示とライセンス文の同梱を要求する。**
VRCT は既に `src-tauri/nsis/licenses/` でサードパーティライセンスを同梱する仕組みを持つので、
ここに ROCm 各コンポーネントの表記を追加する必要がある。

なお **Ollama の配布 zip にはライセンス表記が入っていない**（`README_ROCm.txt` は展開手順のみ）。
これは Ollama 側のコンプライアンス上の不備と読むべきで、**真似すべき前例ではない**。

残る理論上の穴: AMD の Windows HIP SDK インストーラ自体が追加条項を持つ EULA を提示する可能性は
読めていない。ただし上流ソースが MIT/Apache なので、**SDK 経由で取得した DLL であっても
同一ソースのビルド成果物**であり、実務上のリスクは低いと判断する。

### 容量コスト（Ollama の配布物を実地調査して確定）

`ollama-windows-amd64-rocm.zip` (**255,956,786 bytes / 244MB**、展開後 **1000.7MB**、
914 エントリ、ROCm **7.1**) を HTTP range リクエストで実際に開いて内訳を確認した。

| ファイル | 展開後サイズ | VRCT に必要か |
|---|---|---|
| `ggml-hip.dll` | 504.77 MB | **不要**（Ollama 自身の HIP カーネル。VRCT は CT2 の ROCm wheel が相当分を持つ） |
| `amd_comgr_3.dll` + `amd_comgr0701.dll` | 115.27 MB × 2 | **片方のみ必要**（Ollama は HIP 2 系統対応のため重複） |
| `rocblas.dll` | 41.07 MB | 必要 |
| `amdhip64_7.dll` | 18.17 MB | 必要 |
| `libhipblaslt.dll` / `libhipblas.dll` | 6.01 / 0.71 MB | 必要 |
| MSVC 再頒布可能ランタイム一式 | 約 1.4 MB | VRCT は既に同梱済み |
| rocBLAS Tensile カーネル (9 gfx 分) | **約 198 MB** | **絞り込み可**（下記） |

同梱されている gfx ターゲットは **9 種**:
`gfx906`(Vega/CDNA) / `gfx1030`(RDNA2) / `gfx1100`,`gfx1101`,`gfx1102`(RDNA3) /
`gfx1150`,`gfx1151`(RDNA3.5 APU) / `gfx1200`,`gfx1201`(**RDNA4**)。

**VRCT の現実的な見積もり（RDNA3 + RDNA4 に絞る場合）:**

```
amd_comgr (1系統)      115 MB
rocblas.dll             41 MB
amdhip64.dll            18 MB
hipblas + hipblaslt      7 MB
Tensile (gfx1100-1102,
         gfx1200-1201)  約 100-120 MB
------------------------------------
合計 約 280-300 MB (展開後)
```

当初レポートの「550〜930MB」は過大だった。**実際は約 280〜300MB。**
**VRCT の GPU 版は既に約 4GB** (`VRCT_cuda.zip`) なので、比率としては十分許容範囲。
容量は障害ではなく「対応 GPU 世代を絞る設計判断」にすぎない。

**重要な副産物: Ollama は ROCm 7.1 でビルドしている。**
これは AMD の Windows HIP SDK が提供する 7.1.1 と一致する。
つまり **CT2 のブロッカー 2（#2016、wheel が 7.2 ビルド）は、
Ollama と同じく 7.1 系で CT2 を自前ビルドすれば回避できる可能性がある。**

### ブロッカー 2: 未解決の DLL 名不整合 — [CTranslate2 Issue #2016](https://github.com/OpenNMT/CTranslate2/issues/2016)

- 配布 wheel は **ROCm 7.2** ビルド。しかし **AMD の Windows 向け HIP SDK インストーラは 7.1.1 まで**。
- 7.1.1 の `libhipblas.dll` が 7.2 で `hipblas.dll` にリネームされたため、
  **CT2 のロード時に DLL を解決できずクラッシュする**。
- 2026-02-14 open、**メンテナ未回答・リンクされた修正なし**（2026-09-19 時点）。

なお報告内容から見て `libhipblas.dll` を `hipblas.dll` としてコピー/リネームする回避策が
成立する可能性はあるが、**動作報告は存在しない**。試す価値はある（§7 検証項目 2）が、
自前ビルドの前提を背負う判断になる。

### ブロッカー 3: RDNA4 での安定性 — [CTranslate2 Issue #2021](https://github.com/OpenNMT/CTranslate2/issues/2021)

RX 9070 XT (gfx1201) で `faster-whisper` が `Memory access fault by GPU node-1` でクラッシュ。
**float16 / int8 双方、small / large-v3 双方で再現**。報告は Linux 環境だが、
**最新世代 GPU ほど動かない**という逆転はサポート対象の定義を難しくする。未解決。

### 付随する問題: GPU 化の利得データはまだ薄い（1件だけ見つかった）

**CTranslate2-ROCm 経路での AMD 実測値は依然として見つかっていない。**

whisper.cpp + Vulkan 経路については 1 件だけ実測がある。
[Subtitle Edit #10200](https://github.com/SubtitleEdit/subtitleedit/issues/10200) で
**RX 9070 XT + Windows + 自前ビルドの whisper.cpp 1.8.3** にて
45 分の実番組で **"close to 8x realtime"**（RTF 約 0.125）との報告。

ただし**解釈に注意**が必要:

- これは **実時間比 8 倍であって、CPU 比 8 倍ではない**。
  報告に **CPU ベースラインの数値が無く、使用モデル（large-v3 / turbo 等）も明示されていない**。
- VRCT は既に `large-v3-turbo-int8` の CPU 経路を持つので、
  **「VRCT の CPU 実行に対して何倍速くなるか」は依然として未検証**。
- リアルタイム字幕という VRCT の用途では、バッチ処理の RTF よりも
  **1 発話あたりのレイテンシ**が効く。この観点の実測は皆無。

なお同じ RX 9070 XT が CTranslate2 #2021 ではクラッシュしている。
**同じ GPU で Vulkan 経路は動き ROCm 経路は落ちる**、という対比は経路選択上の重要な材料。

---

## 6. 代替案の評価（いずれも本命ではない）

| 案 | 判定 | 理由 |
|---|---|---|
| **whisper.cpp + Vulkan へ移行** | 不採用 | 公式 Windows Vulkan バイナリは配布されず、リリース添付の要望 [#3673](https://github.com/ggml-org/whisper.cpp/issues/3673) は *Closed as not planned*。pip に Vulkan 版 wheel なし（ソースビルド + Vulkan SDK 必須）。Windows 固有の不具合が複数 open（`--processors > 1` でクラッシュ [#2415](https://github.com/ggml-org/whisper.cpp/issues/2415)、v1.8.0 の AMD 検出回帰 [#3455](https://github.com/ggml-org/whisper.cpp/issues/3455)、CPU フォールバック不全 [#2411](https://github.com/ggml-org/whisper.cpp/issues/2411)）。**加えて GGUF への重み形式変更で `_MODELS` 9 エントリ全部の配布元が変わる**。実測の優位性データも無い |
| **ONNX + DirectML EP (sherpa-onnx 等)** | 保留 | DirectML は AMD で確実に動くが Microsoft が *maintenance mode* を明言し新機能は WinML へ。sherpa-onnx では **Whisper medium が DirectML で失敗する既知不具合** [#1240](https://github.com/k2-fsa/sherpa-onnx/issues/1240)。VRCT が使う large-v3 級で動く保証がない |
| **ZLUDA (CUDA 互換レイヤ)** | 不採用 | 商業スポンサー撤退で「週末プロジェクト」に後退。**cuDNN が Windows 安定パスで未対応**と開発者が明言 — VRCT の GPU 経路は cuBLAS と cuDNN **両方**を要求する (`utils.py:406`) ので構造的に穴がある。faster-whisper での成功報告はゼロ（[Discussion #1294](https://github.com/SYSTRAN/faster-whisper/discussions/1294) は無回答） |
| **CTranslate2 ROCm を Linux/WSL2 で** | 対象外 | VRCT は Windows ネイティブ (openvr / pycaw / PyAudioWPatch / WASAPI) |
| **Ryzen AI NPU オフロード** | 対象外 | Ryzen AI 300 シリーズ以降の機種限定。Radeon dGPU ユーザーに適用できず、#88 の要望とずれる |
| **OCR を DirectML 化** | 別件 | RapidOCR は `use_dml=True` で対応可能だが、**現状 NVIDIA でも CPU 実行**なので AMD 対応ではない。やるなら全ユーザー向け最適化として独立に判断すべき |

---

## 6.5. 先行事例調査（2026-09-19 追加）

### A. ROCm を HIP SDK 非依存で配布している実例 — **手法は確立している**

| プロジェクト | ユーザーに SDK 要求 | 配布方式 |
|---|---|---|
| **Ollama** | **なし** | インストーラ (約1.46GB) に NVIDIA/AMD 両方同梱。加えて `ollama-windows-amd64-rocm.zip` (244MB) を別配布。CI (`scripts/build_windows.ps1`) がビルドマシンの `HIP_PATH` を使ってコンパイルし、生成 DLL を梱包 |
| **llama.cpp** | **なし** | `windows-hip` リリースジョブが同じパターン。`ggml-hip.dll` / `amdhip64_*.dll` / `hipblas.dll` / `rocblas.dll` + Tensile を zip 同梱 |
| **koboldcpp-rocm** | **なし** | **PyInstaller に `--add-data` で同梱**（下記）。Tensile は `rocblas-6.2.0.dll.7z` として Release に添付 |
| **LM Studio** | **なし** | 本体を軽量に保ち、ROCm を「Runtime Extension Pack」としてアプリ内から**オンデマンド追加ダウンロード** |
| **Amuse AI** (AMD 推し) | なし | **ROCm を使わず ONNX Runtime + DirectML**。SDK 問題を根本回避する別解。ただしプロジェクト自体は終了状態 |

**VRCT にとって最重要なのは koboldcpp-rocm。PyInstaller 配布という点で VRCT と同一形態**であり、
DLL 同梱パターンをほぼそのまま移植できる直接の前例になる。実際のスクリプトを確認したところ、
やっていることは **ROCm インストールディレクトリからの素朴な `--add-data`** だった:

```
--add-data "./koboldcpp_hipblas.dll;."
--add-data "C:/Program Files/AMD/ROCm/5.7/bin/hipblas.dll;."
--add-data "C:/Program Files/AMD/ROCm/5.7/bin/rocblas.dll;."
--add-data "C:/Program Files/AMD/ROCm/5.7/bin/rocblas;."      <- Tensile カーネル一式
--add-data "C:/Windows/System32/msvcp140.dll;."
```

VRCT は CLI フラグではなく `.spec` を使うので、`backend_amd.spec` の `binaries` / `datas` に
同じものを並べるだけで等価になる。**特別な仕掛けは要らない。**

なお **koboldcpp は `amdhip64.dll` を同梱していない**（Ollama は同梱している）。
これは近年の Adrenalin ドライバが `amdhip64.dll` を提供するため不要になっている可能性を示す。
もしそうなら VRCT の同梱サイズはさらに 18MB + comgr 115MB 分減る。**要検証**。

**LM Studio の方式も検討価値が高い。** 本体インストーラを膨らませず AMD ランタイムを
オンデマンド取得する形なら、**第 3 エディションを作らずに CPU 版へ後付けする**設計が成立し得る。
これは §4 で「中〜大」と見積もった配布側コスト（zip・NSIS・locale・更新導線）を回避できる可能性がある。

注意点として gfx1201 (RDNA4) の初期化失敗が報告されている
([ollama#14686](https://github.com/ollama/ollama/issues/14686))。
CTranslate2 #2021 の RDNA4 クラッシュと合わせ、**RDNA4 は実装横断でまだ未成熟**と読める。
ただし**配布物には RDNA4 のカーネルが実際に入っている**ことを実地確認したので（§5 の内訳表）、
「未対応」ではなく「入っているが不安定」が正しい。

### B. Whisper / VRChat 系アプリの AMD 対応状況

| アプリ | AMD 対応 | 技術 |
|---|---|---|
| **TaSTT** (VRChat 向け) | **なし** | CTranslate2 + CUDA 前提。CUDA DLL 約1GB 同梱。CPU 代替は「かなり遅い」と明記 |
| **VRCTextboxSTT** (VRChat 向け) | **なし** | faster-whisper + CUDA 前提。AMD は「ZLUDA で運試し」の記述のみ、実績なし |
| **Vibe** | あり | whisper.cpp + Vulkan。**単一 Windows インストーラで NVIDIA/AMD/Intel 横断** |
| **Subtitle Edit** | 手動 | whisper.cpp + Vulkan バイナリを手動配置。RX 9070 XT の実測報告元 |
| **Buzz** | 部分的 | whisper.cpp + Vulkan。ただし「GPU 検出されるが Vulkan が有効にならず CPU 実行」バグ報告あり |
| **Const-me/Whisper** | 理論上 | DirectCompute (D3D11) でベンダー非依存だが、**直近 push が約1年前・large-v3 が実質動作しない** issue が放置。**2026 年時点で推奨できない** |
| **whisper-amd-windows** | あり | ONNX Runtime + DirectML。CTranslate2 を捨てて ONNX に載せ替える方式。RX 7000/9000 の動作報告は「まだ未テスト」 |

**重要な所見: VRChat 領域の競合は 1 つも AMD 対応していない。**
TaSTT も VRCTextboxSTT も CUDA 必須設計で、AMD ユーザーへの案内は CPU 実行か ZLUDA の運試しのみ。
**VRCT が対応で遅れているという状況ではない。** 逆に、対応すれば明確な差別化要素になる。

**業界全体の傾向**: 「AMD 対応する場合は whisper.cpp + Vulkan」に収束しつつある。
Vulkan ランタイムはドライバ同梱なので**再配布ライセンス問題も 900MB の Tensile も発生しない**のが強み。

### C. ただし Vulkan 経路は VRCT の GPU 負荷の「半分」しか解決しない

先行事例が Vulkan に寄っている点は重い材料だが、**そのまま VRCT に当てはまらない事情がある**。

上記アプリはいずれも **STT 専用**だが、**VRCT は CTranslate2 を音声認識と翻訳の両方で使っている**
（§2）。whisper.cpp + Vulkan に移っても **NLLB/M2M100 の翻訳は CPU に残る**。
つまり:

| 経路 | STT | 翻訳 | 推論コード変更 | ライセンス | 容量増 |
|---|---|---|---|---|---|
| **CTranslate2-ROCm** | GPU | **GPU** | **ゼロ** | **要確認** | 280〜930MB |
| **whisper.cpp + Vulkan** | GPU | **CPU のまま** | 大（GGUF 移行・重み9エントリ再配布） | 問題なし | ほぼゼロ |

**CTranslate2-ROCm は「両方 GPU・コード変更ゼロ」という、他のどのアプリも持っていない利点がある。**
先行事例が Vulkan を選んでいるのは翻訳を CTranslate2 でやっていないからで、
VRCT の構成では ROCm 経路の相対価値が事例より高い。ここは事例をそのまま真似すべきでない箇所。

---

## 7. 推奨アクション

**いま実装に着手しない。ただし #88 は Reject ではなく「上流待ち + 時間を区切った spike」に変更する。**

理由: ブロッカー 1〜3 はいずれも VRCT 側で直せない。上流（CTranslate2 / AMD）の動き次第で
状況が数か月単位で変わる領域であり、2026-02 の変化がまさにそれを実証している。

### 検証順序（2026-09-19 の先行事例調査を受けて改訂）

**当初ゲートにしていた「SDK 無しで動くか」は先行事例で答えが出た**（同梱すれば動く）。
ゲートは**ライセンス確認**に移った。順序が重要で、**1 が NG なら以降は全部無意味**。

**実機不要の 3 項目（当初のゲート）は 2026-09-19 に完了した。** 以下は結果と残りの項目。

- ~~1. HIP SDK EULA の再配布条項の確認~~ → **完了。全コンポーネントが MIT / Apache-2.0 で再配布可。**
  ライセンス表記の同梱義務のみ発生（§5 ブロッカー 1'）。**法務上のゲートは通過した。**
- ~~2. Ollama の配布物の実物確認~~ → **完了。** `amdhip64_7.dll` と `amd_comgr_3.dll` を
  公式が実際に同梱していることを確認。gfx 9 種（RDNA4 含む）。展開後 1000.7MB の内訳判明。
  VRCT 相当分は **約 280〜300MB** と算定（§5）。
- ~~3. koboldcpp-rocm のビルドスクリプト解析~~ → **完了。** 素朴な `--add-data` で足りることを確認。
  `.spec` の `binaries`/`datas` に並べるだけで等価（§6.5 A）。

**残り（実機が必要。ここから先は Radeon RX 7000/9000 系が無いと進まない）:**

4. **Issue #2016 の回避策検証**
   HIP SDK 7.1.1 環境で `libhipblas.dll` → `hipblas.dll` のコピーでロードが通るか。
   **または** Ollama と同じく **ROCm 7.1 で CT2 を自前ビルド**して 7.2 由来の不整合を回避する
   （§5 末尾。こちらが本筋かもしれない）。
5. **`amdhip64.dll` はドライバが提供するか**
   koboldcpp が同梱していないことから、近年の Adrenalin ドライバが提供している可能性がある。
   もし提供されていれば同梱サイズが 130MB 以上減る。
6. **動作と精度**
   `faster-whisper large-v3-turbo` を `device="cuda"` のまま実行。
   `float16` / `int8` が使えるか（`utils.py` の compute_type 分岐設計に直結）。
   **RDNA4 (#2021) と RDNA3 の両方**で確認したい。片方だけ動く可能性が高い。
7. **速度 — リアルタイム字幕としてのレイテンシ**
   同一機の CPU (`large-v3-turbo-int8`) と比較。
   バッチの RTF ではなく **1 発話あたりのレイテンシ**を測る。VRCT の用途はこれ。
   **改善しないなら、そもそも AMD 対応の価値がない。**

**現状の総括: 配布・ライセンス・実装の 3 つはいずれも「解ける」ことが分かった。
未知なのは「実機で動くか」と「速くなるか」だけに絞られた。**

### 上流の監視対象（次回棚卸し時に再確認する 3 点）

- AMD が **Windows 向け HIP SDK 7.2** を出したか（ブロッカー 2 が自然解消する）
- [CTranslate2 #2016](https://github.com/OpenNMT/CTranslate2/issues/2016) にメンテナ回答 / 修正が付いたか
- [CTranslate2 #2021](https://github.com/OpenNMT/CTranslate2/issues/2021) の RDNA4 クラッシュが解消したか、
  および ROCm wheel が公式ドキュメント（`hardware_support.html`）に掲載されたか（= 上流の本気度の指標）

### 当面 AMD ユーザーに案内できる回避策

現行コードのままでも以下は利用可能であり、#88 への暫定回答として使える。

- CPU 版 + `large-v3-turbo-int8` (794MB) — 精度と速度の妥協点
- クラウド STT（Groq / OpenAI 互換 / Deepgram）— `transcription_providers.py` で実装済み
- Web 翻訳系 / DeepL / LLM 翻訳 — ローカル CTranslate2 を使わない経路

---

## 8. 未確認事項（推測で埋めていない項目）

**2026-09-19 に解消した項目（記録として残す）:**

- ~~AMD HIP SDK EULA の再配布条項~~ → 上流が MIT / Apache-2.0 と判明。再配布可（§5）。
- ~~Ollama 公式が `amdhip64.dll` を同梱しているか~~ → zip を実地調査し **同梱を確認**。
  community fork の記述との食い違いは、fork 独自のポリシーだった。
- ~~gfx ターゲット数と 244MB に収まる理由~~ → 9 種。`ggml-hip.dll` 504MB が支配的で、
  Tensile は約 198MB。VRCT には前者が不要なため見積もりが大幅に下がった。
- ~~Ollama が ROCm 6.2 固定という情報~~ → **誤り。実際は ROCm 7.1**（`rocm_v7_1` ディレクトリ）。

**残る未確認事項:**

- **AMD の Windows HIP SDK インストーラが提示する EULA 本文。** 上流が permissive なので
  実務上のリスクは低いと判断したが、インストーラ側が追加条項を課していないかは読めていない。
- **`amdhip64.dll` が Adrenalin ドライバに含まれるか。** koboldcpp が同梱していない事実からの
  推測。含まれるなら同梱サイズが 130MB 以上減る。§7 検証項目 5。

**技術面:**

- `libhipblas.dll` → `hipblas.dll` のリネーム回避策が実際に機能するか（動作報告なし）。
- **CTranslate2-ROCm 経路**での AMD dGPU 実測値。Vulkan 経路の 1 件（RX 9070 XT,
  "close to 8x realtime"）は見つかったが、**ROCm 経路の実測は依然ゼロ**。
- 上記 Vulkan 実測の **CPU ベースラインと使用モデル**（報告に記載がない）。
- **リアルタイム字幕用途での 1 発話レイテンシ**の実測 — Vulkan/ROCm どちらも皆無。
  VRCT の用途に直結する数字がまだ誰も測っていない。
- ROCm ビルドで `get_supported_compute_types("cuda", i)` が NVIDIA と同じ形で応答するか
  （`device="cuda"` 流用から強く示唆されるが、PR #1989 に明記なし）。
- gfx1100 系（RX 7900 XTX/XT、ROCm 公式サポート対象）× HIP SDK 7.1.1 という
  現実的な組み合わせでの動作報告 — 見つからなかった。#2016 は DLL 不整合、#2021 は RDNA4。
- **ROCm 7.1 で CT2 を自前ビルドすれば #2016 を回避できるか**（Ollama が 7.1 を使っている
  ことからの推論。§7 検証項目 4）。

**なお AMD が「Windows アプリに ROCm を同梱する」ための公式ガイダンスや
redistributable パッケージを出している形跡は確認できなかった。** NVIDIA の CUDA
Redistributable リストに相当するものが無く、各プロジェクトが個別に判断している状況。
上流が permissive なので支障はないが、AMD 側の姿勢としては「想定された配布経路ではない」と読める。

---

## 付録: 調査に使ったコマンド

Ollama の配布 zip は 244MB あるが、**ダウンロードせずに中身を確認できる**
（zip の中央ディレクトリは末尾にあるので HTTP range リクエストで足りる）。
再調査時はこれを使うと速い。スクリプトは
`scratchpad/peek_zip.py` に置いた（`io.RawIOBase` の `readinto` を range 取得で実装し、
`zipfile.ZipFile` に食わせるだけ）。

```
python peek_zip.py "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64-rocm.zip"
```
