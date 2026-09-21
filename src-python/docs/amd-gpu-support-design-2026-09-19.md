# AMD GPU 対応 設計書 (2026-09-19)

前提調査: `amd-gpu-support-feasibility-2026-09-19.md`（先に読むこと）
対象 issue: [#88](https://github.com/misyaguziya/VRCT/issues/88)
ブランチ: `feature/amd-gpu-support`

**この設計書の要点は「第3エディションは必要だが最後に必要」であり、
その手前の PR-1〜PR-5 は Radeon を1台も持たずに安全にマージできる、という線引きにある。**

---

## 1. 設計判断を左右した実測事実

設計前の想定を覆した事実が 3 つある。いずれもコードで確認済み。

### 1-1. NSIS インストーラは本体を同梱していない。ダウンローダである

`src-tauri/nsis/template.nsi:737-785` は実行時に zip 名を選び、GitHub Release から落とす。

```
!define SOFTWARE_DOWNLOAD_FILENAME     "VRCT.zip"
!define SOFTWARE_DOWNLOAD_FILENAME_GPU "VRCT_cuda.zip"
...
${If} $SelectedEdition == "gpu"
  StrCpy $file_name "${SOFTWARE_DOWNLOAD_FILENAME_GPU}"
```

**エディション追加の配布側コストは「zip 名 1 個 + 空き容量バジェット 2 個 + 分岐 1 つ」に収まる。**
`issue-triage-2026-07-31.md` の「配布コストが大きい」判定は、
インストーラが本体を同梱している場合の見積もりに近く、実態より重く見ていた。

さらにエディション選択ページ（`template.nsi:199-235`）の文言は**ハードコードされた英語**で、
LangString ではない。**NSIS 側の locale 作業は発生しない。**

実測値（`template.nsi:743-745` のコメント）:
`VRCT.zip` 約485MB / 展開約1.5GB、`VRCT_cuda.zip` 約3461MB / 展開約5757MB。
（前調査レポートで「約4GB」と書いたのは `REQ_DOWNLOAD_MB_GPU 4096` = バジェット値との混同。
実サイズは約3.4GB。）

### 1-2. 起動経路に GPU が一切無い

**これがフォールバック設計の土台であり、新しい安全弁を作らなくてよい根拠。**

| 事実 | 箇所 |
|---|---|
| `ENABLE_TRANSLATION` / `ENABLE_TRANSCRIPTION_SEND` / `_RECEIVE` は `serialize=False` かつ `False` 初期化 = **毎回 OFF で起動** | `config.py:791-793`, `1055-1057` |
| 重みの検証は**必ず CPU** で行う | `transcription_whisper.py:126` (`device="cpu"` 固定), `translation_utils.py:111` |
| 既定の計算デバイスは `SELECTABLE_COMPUTE_DEVICE_LIST[0]` = **常に CPU** | `config.py:1202-1203` |

→ **GPU は「ユーザーが設定で明示的に選び」かつ「機能を ON にした」瞬間にしか触られない。**
したがって #2021 のようなネイティブクラッシュが起きても
「起動するたびに死ぬ」ループにはならない。再起動すればアプリは立ち上がり、
ユーザーは設定で CPU に戻せる。

### 1-3. `_compute_device_validator` は dict の完全一致を要求する

```python
def _compute_device_validator(val, inst):
    for dev in inst.SELECTABLE_COMPUTE_DEVICE_LIST:
        if dev == val:
            return copy.deepcopy(val)
    return None
```
`config.py:642-648`

不一致なら `ConfigValidationError` → `config.py:1343` で捕捉 → 初期値（CPU）のまま。
**つまり `compute_types` リストの中身を変えると、既存ユーザーの保存済みデバイス選択が
黙って CPU にリセットされる。**

→ **制約: NVIDIA 側のデバイス一覧・compute_type 生成ロジックには一切触れない。**

### 1-4. 既存のドリフトが 1 件ある（3本目を作るべきでない根拠）

`spec/backend_cuda.spec:20` は `hf_xet` を **`.venv`（CPU 側）** から拾っている。
他の行は `.venv_cuda` を使っているので、これはコピー由来の取り違え。
**spec を 3 本目にコピーすれば同種の事故が確実に増える。**

---

## 2. 配布形態の比較と結論

| 軸 | 案A 第3エディション | 案B GPU版を統合 | 案C オンデマンド取得 (LM Studio 方式) | **案D 段階分離** |
|---|---|---|---|---|
| 技術的成立性 | ○ | **✗ 破綻** | △ | ○ |
| ビルド系統 | +1 | 0 | 0 | +1（CI 対象外に保留可） |
| 配布サイズ | AMD 約0.8〜1GB | **全 GPU ユーザーが約3.9GB** | 基本485MB + 後から約440MB | 変化なし |
| NSIS / locale | 小（zip名+バジェット+ラジオ1、locale 1キー×5言語） | 0 | 0 | 0 |
| 新規機構 | **なし**（既存の仕組みに値を足すだけ） | 2系統の site-packages + `sys.path` 切替 | ランタイムパックの DL/検証/展開/活性化/版整合 | なし |
| 既存版への risk | ほぼゼロ（独立 venv/zip） | 高 | 中（**CPU 版の起動時 import 経路**を改造） | **ゼロ** |
| 実機未検証下で出せるか | △ | ✗ | ✗ | **◎** |

### 案B の却下理由（構造的）

**CUDA 版 CT2 と ROCm 版 CT2 は同じ配布名 `ctranslate2`。1 つの venv に共存できない。**
共存させるには 2 本の site-packages ツリーと起動時 `sys.path` 切替が必要で、
かつ全 GPU ユーザーが約3.9GB を落とすことになる。得るものが無い。

### 案C の却下理由（現時点では）

魅力は「NSIS/locale/更新導線に触らずに済む」点。しかし買うものが大きすぎる。

1. 案B と同じ `ctranslate2` 二重化問題を、**CPU 版の起動パス**に持ち込む。
   `utils.py:77` は import 時点で ctranslate2 を読むので、
   切替判断を config 読込より前に押し出す必要がある。壊してはいけない箇所が変わる。
2. パック側のライフサイクル保守が**永続的に**増える（CT2 更新ごとにパック再ビルド、
   旧パック無効化、アプリ版とパック版の互換表）。案A は zip 1 個に固まるので不要。
3. 新しい失敗モード一式（部分DL、破損、AV 誤検知、パスの空白、展開先の権限）。
4. **そして VRCT の NSIS は既にオンデマンドダウンローダである（§1-1）。**
   案C が節約する「インストーラの肥大」という問題はそもそも存在しない。

→ ランタイム変種が 4 つ以上（NVIDIA/AMD/Intel/CPU）になったら案C が正解になる。2 つでは過剰。

### 結論: **案D → 案A**

まず案D（コード層と開発者向けビルド系統のみ）をマージし、実機 spike を通した後に案A を出す。
案A は新しい抽象化を一切導入しない。

---

## 3. デバイス抽象化（`src-python/utils.py`）

**新しいレイヤは作らない。CUDA 固有な 3 点を「テーブル 1 つ + 分岐 1 つ」に一般化する。**

| 現状 | 変更後 |
|---|---|
| `_CUBLAS_LIBRARY_NAME` (411行) | `_GPU_RUNTIMES` = 2 要素のタプル。各要素は `(vendor, 判定用DLL候補, ドライバDLL候補, シンボル名3つ)`。**NVIDIA 行は現状と完全に同値**（`cublas64_12.dll` / `nvcuda.dll` / `cuInit,cuDeviceGet,cuDeviceGetName`）。AMD 行は `("hipblas.dll","libhipblas.dll")` / `("amdhip64_7.dll","amdhip64.dll")` / `hipInit,hipDeviceGet,hipDeviceGetName`。**`libhipblas.dll` を候補に入れるのが #2016 への安価なヘッジ。** シンボル名はプレフィックス合成せず全部書く（grep 可能性優先） |
| `_getCudaDeviceNames()` (413-463行) | `_getGpuDeviceNames()` に改名。先頭で `_getGpuRuntime()`（`lru_cache`、判定用 DLL がロードできた最初の行を返す。無ければ `None`）を引き、以降は現状のロジックをテーブルの値で回すだけ。制御フロー・キャッシュ・例外処理は現状のまま |
| 名前キーワード分岐 (487-490行) | **AMD ではデバイス名の文字列一致を使わない。** どのランタイムがロードできたかでベンダーが確定しているので、vendor == `amd` の場合だけ別の許可リストを適用する。`"AMD Radeon(TM) Graphics"` 系の命名ゆれに依存しない。**NVIDIA 側の分岐は 1 文字も変えない**（§1-3） |
| `getBestComputeType()` の `preferred_types` (524-538行) | 同様に vendor == `amd` の場合だけ AMD 用の優先順位。NVIDIA 用 dict は不変 |
| `_registerBundledCudaLibraries()` (19-59行) | `_registerBundledGpuLibraries()` に改名。既存 `nvidia` ブロックは**そのまま温存**し ROCm ブロックを追加。両ブロックとも対象が無ければ何もせず抜ける = CPU/CUDA 版は挙動不変 |

### compute_type の初期方針（保守的）

AMD の許可リストは **`{"float16", "float32"}` のみ**（`get_supported_compute_types` との積集合は現状通り）。
優先順は `["float16", "float32"]`。**`int8` / `bfloat16` / `int8_*` は実測まで出さない。**

根拠: PR #1989 で唯一の肯定報告が Strix Halo の float16。
#2021 は float16/int8 の両方で落ちており dtype で回避できる問題ではない。
実績のある 1 つに絞るのが妥当。

### アーキ世代ゲート（AMD のみ）

`hipDeviceComputeCapability(major*, minor*, device)` を叩き、
**`major in (11, 12)` 以外のデバイスは一覧に出さない。**

過剰設計ではない。同梱する Tensile カーネルの gfx セット
（RDNA3 = gfx1100/1101/1102、RDNA3.5 = gfx1150/1151、RDNA4 = gfx1200/1201）が
major 11/12 にちょうど一致し、**それ以外（Ryzen APU の gfx90c=9、gfx103x=10）は
同梱していないので必ずモデルロードで失敗する**。
「Ryzen APU + Radeon dGPU」「Ryzen APU のみ」は実際に多い構成なので、選ばせない方が正しい。

`hipGetDeviceProperties` の巨大構造体は使わない（3 引数の API で足りる）。
RDNA4 が駄目だと分かったら `(11,)` に変える 1 行。

> **未検証の前提**: 「gfx1100 → major 11」というマッピングは HIP の仕様から妥当と見ているが
> 実機で確認していない。spike 項目 2 で確定させる。崩れたら
> `hipGetDeviceProperties` の `gcnArchName` 文字列に落とす。

---

## 4. `COMPUTE_MODE` の表現

**3 値化する（`"cpu"` / `"cuda"` / `"rocm"`）。後方互換の懸念は無い。**

- `COMPUTE_MODE` は `config.py:785` で **`serialize=False` かつ readonly**。
  config.json に一切書かれない。**既存ファイルへの影響ゼロ。**
- 永続化されるのは `SELECTED_*_COMPUTE_DEVICE` の dict だけ。
  AMD でも `device` は `"cuda"` のままなので、
  **NVIDIA ユーザーの保存値は触られない**（NVIDIA 用 compute_types 生成を変えない限り = §1-3）。
- AMD ユーザーが CPU 版に戻った場合、保存済み dict は validator の完全一致に失敗して
  CPU に落ちる = 既存の安全な挙動そのまま。

`config.py:1049-1051` を「cuda エントリがあるなら `utils` が返すランタイム名、無ければ `cpu`」に変更（2行）。

ベンダーを別フィールドに分ける案は採らない。利用側（Updater の選択肢、VersionLabel のバッジ）は
結局「どの zip を落とすか」の 1 軸しか要らない。YAGNI。

値は `"amd"` ではなく **`"rocm"`** を推奨（既存値 `"cuda"` がベンダー名でなくランタイム名なので並びが揃う）。
NSIS 側の `/EDITION` は `cpu|gpu|amd` を維持し（既存 2 値を壊さない）、
`model.py` に `{"cpu":"cpu", "cuda":"gpu", "rocm":"amd"}` の**対応表を 1 つだけ**置く。

---

## 5. 更新導線

**3 本立てにせず 1 本に畳む。**

- `model.py:1931-1964` — `updateSoftware` / `updateCudaSoftware` の**重複 2 関数を削除**し
  `updateSoftware(target_version=None, edition="cpu")` 1 本に。`/EDITION=` に渡す値だけが差分で
  他は完全に同一コード。
- `controller.py:3462-3474` — 2 メソッドを 1 本に。payload を
  `{"version": str|None, "edition": "cpu"|"gpu"|"amd"}` へ。
  **文字列が来たら `edition="cpu"` とみなす 1 行の後方互換分岐**を入れる。
  edition は既知 3 値のホワイトリストで検証（`/EDITION=` は外部プロセスの引数になるので信頼境界）。
- `mainloop.py:242` の `/run/update_cuda_software` は**削除**。
  `src-ui/logics/useReceiveRoutes.js:18` と `useUpdateSoftware.js:10` も削除して 1 関数化。
  **エンドポイントを増やさず減らす。**

---

## 6. PyInstaller

**spec は 3 本にしない。`backend.spec` をパラメータ化して 1 本にし、`backend_cuda.spec` を削除する。**

- `VRCT_BUILD_EDITION`（`cpu`/`cuda`/`amd`、既定 `cpu`）を env から読み、
  venv ディレクトリ名・`hiddenimports` 追加分・ROCm DLL の `binaries`/`datas` を切り替える。
- これは既存の重複除去でもある（§1-4 の `hf_xet` ドリフトが消える）。
- 検証は「CPU/CUDA 双方をビルドして出力ツリーを現行と diff」で機械的に取れる。

### 同梱すべきもの（Phase 3 で有効化）

Ollama zip の実測内訳と koboldcpp の前例に基づく。

```
amdhip64_7.dll          18MB   ← 要検証: ドライバ提供なら不要 (spike 4)
amd_comgr_*.dll        115MB   ← 1系統のみ。CT2 が実行時コンパイルを
                                  しないなら不要の可能性あり (spike 4)
hipblas.dll              1MB   ← #2016 対策で libhipblas.dll のコピーも検討
hipblaslt.dll            6MB
rocblas.dll             41MB
rocblas/library/**   100-120MB ← Tensile。gfx1100/1101/1102/1150/1151/1200/1201 のみ
```

配置は koboldcpp と同じ「バンドル直下」= `datas` の dest を `.` にして `_internal/` 直下へ。
PyInstaller の bootloader が `_internal` を DLL 検索パスに入れるため
**frozen ビルドでは追加コード不要な見込み**。

ただし **`rocblas.dll` は Tensile を自分の隣の `rocblas/library` から探すので、
この相対関係を崩さないこと。** 念のため `ROCBLAS_TENSILE_LIBPATH` を
`_registerBundledGpuLibraries()` で明示設定するのが確実
（既存の `_registerBundledCudaLibraries` が `PATH` まで足している「素の LoadLibrary 対策」と同じ発想）。
dev（非 frozen）では `%HIP_PATH%\bin` を `add_dll_directory` するフォールバックを同じ関数に置く。
両方とも「無ければ何もしない」。

---

## 7. requirements / venv

- **`requirements_amd.txt`（新規）** — `-r requirements.txt` を include し CT2 だけ差し替え。
  ただし **ROCm wheel は zip 内にあり URL 直指定できない**ので、
  `tools/fetch_ct2_rocm_wheel.py`（新規、`tools/fetch_ocr_models.py` と同じ位置づけ）で
  GitHub Release の zip を **SHA-256 固定**で取得・展開し、`install.bat` がそれを `pip install` する。
  requirements 側にはコメントでバージョンと取得元を明記。
- `bat/install.bat` — `.venv_amd` ブロックを追加（既存 2 ブロックのコピー + fetch 呼び出し）。
- `.gitignore` に `.venv_amd/`。
- **`utils/dev_sidecar/src/main.rs:31-36`** は `.venv` / `.venv_cuda` のみホワイトリストしているので
  `.venv_amd` を 1 行追加（エラーメッセージも）。
- `package.json` に `build-python-amd` / `dev-amd-fast` / `release-amd`
  （`zip.py --zip_name VRCT_amd.zip`）。既にパラメータ化済みなので追加コストほぼゼロ。

---

## 8. フォールバック / エラー処理

**結論: 新しい安全弁（セーフモード用マーカーファイル等）は要らない。**
§1-2 の通り、既存の構造がすでに「起動不能」を構造的に防いでいる。加えて:

- Python 例外レベルの失敗は既に無害化されている
  （`controller.py:3589-3593` 付近、`controller.py:1428-1430` — 非 VRAM エラーは
  `errorLogging()` して機能 OFF・アプリ継続）。
- **一覧に出さないことが最強のフォールバック** — §3 のアーキ世代ゲートと
  「判定用 DLL がロードできなければ GPU を列挙しない」既存設計（`utils.py:436-441`）で、
  動かない構成は選択肢に出ない。

追加すべきは次の 2 点だけ。

### 8-1. OOM 文字列判定の共通化と HIP 対応

現状 `model.py:2041` と `transcription_whisper.py:212` に**同じ文字列一致が重複している**。
`utils.py` に marker タプル 1 つ + `isOutOfMemoryMessage(msg)` を置き両方から使う
（両ファイルとも既に `utils` を import 済み）。

追加するマーカーは **HIP 固有トークンのみ**
（`hipErrorOutOfMemory` / `HIPBLAS_STATUS_ALLOC_FAILED` / `rocblas_status_memory_error`）。
**汎用の `"out of memory"` 小文字一致まで広げない** — CPU 版で CPU RAM 不足を
「VRAM エラー」と誤分類しうる。
正確な文字列は spike でログから採取して確定する（現時点では推測なので、
テストは「マーカーを足せば効く」構造だけを守る）。

### 8-2. GPU 失敗時の自動 CPU 降格は「既存の別課題」として切り出す

`controller.py:1426` のコメントは「Default のデバイス設定に戻す」と書いてあるが、
実装は `SELECTED_TRANSLATION_COMPUTE_DEVICE` を変更せず**同じ設定で再ロードしている**。
つまり「**GPU で失敗したら CPU に落ちて動き続ける**」挙動は **CUDA でも現状存在しない**
（VRAM エラー時は翻訳が無効化されるだけ）。

真の自動降格を入れるなら「`SELECTED_*_COMPUTE_DEVICE` を一覧の [0]（CPU）に書き換えて
1 回だけ再試行する」ヘルパー 1 つで済むが、**これは AMD 対応の必須要件ではなく
CUDA ユーザーの挙動も変える**ため、**独立した小 PR に切り出す**。
ベンダー別に分岐させるとかえって悪くなるので、やるなら両ベンダー共通で。

---

## 9. 段階的導入計画

### Phase 1 — 実機なしで安全に出せる範囲（ここまで先にマージ可）

| PR | 内容 | 検証 |
|---|---|---|
| **PR-1** | OOM 判定の共通化。`utils.py` に marker + 判定関数、`model.py:2037-2043` と `transcription_whisper.py:209-214` を差し替え。HIP マーカー追加込み。既存 CUDA 文字列の挙動は不変 | 既存 `test_controller_audio.py:200,215` / `test_model_input_translate_parallel.py:130` がそのまま通る + 新規ユニットテスト |
| **PR-2** | 更新導線の 1 本化（§5）。**この時点で edition は `cpu`/`gpu` のみ受ける** | `test_model_update.py` を書き換え、`/EDITION=cpu` と `/EDITION=gpu` の引数列が**現行と完全一致**することを assert |
| **PR-3** | spec のパラメータ化（§6）。`backend_cuda.spec` 削除、`build_cuda.bat` / `package.json` 追随。`hf_xet` ドリフト修正込み | CPU/CUDA をビルドして出力ツリーを現行と diff（**人手のゲート。ここは自動化できない**） |
| **PR-4** | デバイス層のベンダー一般化（§3）。`config.py:1049` の 3 値化込み。**AMD 経路は未活性** | §10 のテスト計画 + CPU/CUDA 実機で `getComputeDeviceList()` の出力が変化しないことを 1 回確認 |
| **PR-5** | AMD ビルド系統（§7）。**`release.yml` と `template.nsi` と `locales/*` には触らない。誰もこのビルドを受け取らない** | `npm run build-python-amd` が通る |

**PR-4 は CPU 版・CUDA 版の実行結果を 1 ビットも変えない**
（AMD の判定用 DLL が存在しないので必ず NVIDIA 行または `None` に落ちる）。全てモックでテスト可能。

→ **ここが実機検証ゲート。** Phase 1 は AMD ユーザーに何も届かないが、spike の足場が全部揃う。

### Phase 2 — 実機 spike（Radeon RX 7000 系 必須）

**順序が重要。前が NG なら後ろは無意味。**

1. `.venv_amd` で `ctranslate2.get_cuda_device_count()` /
   `get_supported_compute_types("cuda",0)` が AMD デバイスに応答するか
2. `hipInit` / `hipDeviceGet` / `hipDeviceGetName` / `hipDeviceComputeCapability` が
   `amdhip64*.dll` から ctypes で引けるか（§3 の設計前提）。
   **gfx1100 → major 11 のマッピングもここで確認**
3. **#2016: `libhipblas.dll` → `hipblas.dll` のコピーでロードが通るか。**
   通らなければ **ROCm 7.1 で CT2 を自前ビルド**（Ollama と同じ）に切り替える。**最大の分岐点**
4. `amdhip64.dll` / `amd_comgr` はドライバ提供か（同梱 130MB 超の削減可否）
5. `faster-whisper large-v3-turbo` を `device="cuda"`、float16 で実行。
   落ちる/精度異常のログ文字列を採取（OOM マーカー確定に使う）
6. **スレッド安全性の確認（下記 §11 R9）** — mic/speaker 同時実行で
   `ctranslate2.Translator` を叩く既存経路が ROCm でも安全か
7. **1 発話あたりのレイテンシ**を同一機の CPU (`large-v3-turbo-int8`) と比較。
   **改善しないならここで打ち切り、Phase 3 に進まない**
8. RDNA4 (#2021) が入手できれば同じことを。駄目ならアーキゲートを `(11,)` に絞る 1 行

### Phase 3 — 配布（案A。spike 7 を通った場合のみ）

| PR | 内容 |
|---|---|
| **PR-6** | `/EDITION=amd` を受けるが **UI には出さない**。`template.nsi` に `SOFTWARE_DOWNLOAD_FILENAME_AMD` / `REQ_*_MB_AMD` 追加、`template.nsi:777-785` を 3 分岐化。`PageChooseEdition` は `$SelectedEdition == "amd"` のとき `Abort`（ページスキップ）する 2 行のみ。**ラジオボタンは追加しない。** `release.yml` に `VRCT_amd.zip` + `.sha256`。**`src-tauri/nsis/licenses/` に ROCm 各コンポーネントの MIT / Apache-2.0 表記を追加（再配布の法的義務。省略不可）** |
| **PR-7** | UI に露出。`template.nsi` に 3 つ目のラジオ（英語ハードコードなので locale 不要）、`locales/{en,ja,ko,zh-Hans,zh-Hant}.yml` に `compute_mode_amd` と警告文言、`Updater.jsx:97-100` に `rocm` 追加 + `SummaryCustomDiff` の 2 値三項を関数化、`AppErrorBoundary.jsx:108-117` の `is_cpu` 二分岐を edition 解決に置換、`VersionLabel.jsx:13` のバッジ。**推奨: まず beta チャンネルのみで露出**（`Updater.jsx` で `target_channel === "beta"` のときだけ選択肢に出す ≒ 3 行） |

---

## 10. テスト計画（実機なしで守れる範囲）

`src-python/test/test_utils_compute_device.py` は既に
「CPU 版で GPU を出さない」という**まさに同型の回帰**をモックだけで守っている。同じ形で拡張する。
**実機は 1 台も要らない。**

`setUp` に `utils._getGpuRuntime.cache_clear()` を追加し、`ctypes.CDLL` を DLL 名で分岐する fake に差し替える。

1. **CUDA 版の完全な回帰ガード（最重要）** — `cublas64_12.dll` だけロードでき
   `hipblas.dll` が OSError の環境で、`getComputeDeviceList()` / `getBestComputeType()` の出力が
   **現行の期待値と完全一致**。既存 4 テスト（GTX 制限、未知GPU→float32、名前取得失敗、index 範囲外）を
   維持し `_GPU_RUNTIMES` 導入後も緑であること。**これが「既存を壊さない」の機械的な保証。**
2. **CPU 版** — 両方の DLL が OSError → 一覧が `["cpu"]` のみ、`COMPUTE_MODE == "cpu"`
3. **AMD 版** — `hipblas.dll` のみロード可 + fake HIP ドライバ
   （`hipInit`→0, `hipDeviceGetName`→`"AMD Radeon RX 7900 XTX"`, `hipDeviceComputeCapability`→(11,0)）で、
   `device == "cuda"` / `compute_types` が積集合 / `getBestComputeType` が `float16`
4. **`libhipblas.dll` フォールバック** — `hipblas.dll` が無く `libhipblas.dll` だけある場合も
   AMD として検出される（#2016 ヘッジの回帰）
5. **アーキゲート** — capability major 9/10 は一覧に出ない。`(11,0)` と `(12,0)` は出る
6. **ベンダー同時検出の優先順** — 両方ロードできる異常系でテーブル先頭（NVIDIA）が選ばれ決定論的
7. **config 後方互換** — `SELECTABLE_COMPUTE_DEVICE_LIST` が NVIDIA 構成のとき、
   既存 config.json 相当の `SELECTED_*_COMPUTE_DEVICE` dict が validator を通ること。
   **現状これを守るテストが無い**（§1-3 の事故を防ぐ）
8. **OOM 判定** — 既存 2 文字列 + HIP 3 文字列が True、`"Cannot allocate memory"` 等が False
9. **更新導線** — `test_model_update.py` を edition パラメータ化に追随。
   `cpu`→`/EDITION=cpu`、`gpu`→`/EDITION=gpu`、`amd`→`/EDITION=amd`、
   不正値→**インストーラを起動しない**ことを assert
10. **ROCm DLL ディレクトリ登録** — `os.add_dll_directory` をモックし、
    (a) ROCm ディレクトリが無いとき何も呼ばれない（CPU/CUDA 版不変の保証）、
    (b) あるとき登録され `ROCBLAS_TENSILE_LIBPATH` が設定される

実機でしか守れないもの: spike 項目と NSIS の実ダウンロード。
後者は既存 CPU/GPU と同じコードパスなので `/EDITION=amd` の手動実行 1 回で足りる。

---

## 10.5. 実環境で確定した事実 (2026-09-20、PR-5 の検証)

`.venv_amd` を実際に作り `tools/fetch_ct2_rocm_wheel.py` を通して確認した。
**AMD GPU は不要**な範囲の検証だが、設計の前提が2つ変わる。

### ROCm 版 ctranslate2 は HIP ランタイムを「静的に」要求する

`ctranslate2.dll` の PE インポート表 (実測):

| ビルド | インポートする GPU 関連 DLL | wheel 同梱 |
|---|---|---|
| CPU / CUDA (PyPI 4.6.0) | `cudnn64_9.dll` | `cudnn64_9.dll` を同梱。cuBLAS は**遅延ロード**でインポート表に出ない |
| **ROCm (4.8.2)** | **`hipblas.dll`, `amdhip64_7.dll`** | **同梱なし** |

**帰結1: ROCm ランタイムが無いと `import ctranslate2` 自体が FileNotFoundError で失敗する。**
CUDA 版は cuBLAS が無くても import は成功し「GPU が無い」と振る舞うだけだったが、
AMD 版は挙動が違う。

**帰結2: AMD エディションには CPU フォールバックが無い。**
ctranslate2 は1つしか入らないので、ROCm DLL の同梱に失敗すると
GPU だけでなく **CPU 推論も含めて推論機能が全部死ぬ**。§8 の
「GPU で失敗したら CPU に落ちて動き続ける」は CUDA 版では成り立つが、
AMD 版では**同梱が失敗した時点で詰む**。配布 (Phase 3) では同梱の正しさが
CUDA 版より重い意味を持つ。

なお `utils.py` 側は正しく劣化することを実機確認済み
(ROCm ランタイム不在の `.venv_amd` で `import utils` が成功し、
GPU を一覧に出さず `['cpu']` のみを返す)。アプリは起動する。

**帰結3: #2016 は確実に踏む。**
wheel は `hipblas.dll` という名前を**静的に**要求する。AMD の Windows HIP SDK
7.1.1 が置くのは `libhipblas.dll` なので、ローダが名前解決に失敗する。
`utils.py` の `_GPU_RUNTIMES` が候補に `libhipblas.dll` を持っているのは
**検出のためのヘッジであって、これだけでは動かない**。
実機では `libhipblas.dll` を `hipblas.dll` としてコピーするか、
ROCm 7.1 で CT2 を自前ビルドする必要がある (spike 3)。

### 同梱サイズの見積もりを上方修正する

`ctranslate2.dll` の実サイズ:

| ビルド | ctranslate2.dll |
|---|---|
| CPU / CUDA | 60,924,928 bytes (58MB) |
| **ROCm** | **290,648,064 bytes (277MB)** |

wheel が圧縮 21.6MB なのは device code がよく圧縮されるためで、
**gfx カーネルは ctranslate2.dll の中に入っている**。外部から必要なのは
HIP ランタイムと BLAS だけ、という切り分けになる。

調査レポート (`amd-gpu-support-feasibility-2026-09-19.md` §5) で
「約 280〜300MB」としていた追加分は、この 219MB 差を数えていなかった。
**改訂後の見積もり: CPU 版 + 約 500〜530MB**
(ctranslate2.dll の差 219MB + ROCm ランタイム約 181MB + Tensile 約 100〜120MB)。
VRCT の CUDA 版が約 3.4GB であることを思えば依然許容範囲だが、
「CPU 版に近い軽さ」ではない。

### install.bat の順序は正しい

`requirements.txt` は `ctranslate2==4.6.0` を**完全一致で固定**しているので、
ROCm wheel を先に入れてから requirements を流すと CPU 版に戻される。
現行の「requirements → fetch スクリプト」の順序で正しい。
なお fetch 後に `faster-whisper==1.1.1` を入れても ROCm 版は保持された
(faster-whisper の要求が範囲指定で 4.8.2 を満たすため)。

---

## 10.6. 実機検証で確定した事実 (2026-09-21、Radeon RX 7900 XTX)

協力者の実機で `VRCT-AMD-Check.exe`（`tools/amd_spike/check_amd.py` の凍結版）を
実行した結果。HIP SDK 未インストールの素の Windows 機。

| spike | 結果 |
|---|---|
| 1 (R1) | **OK** — `get_cuda_device_count()` = 2、`get_supported_compute_types("cuda", i)` が両デバイスに応答 |
| 2 (R3) | **OK** — 5 シンボルすべて実在。**gfx1100 → compute capability 11.0**。§3 のアーキゲートはそのまま使える |
| 3 (R2) | **不要になった** — ROCm 7.2 の wheel は `hipblas.dll` を要求し、同梱物にそれがある。`libhipblas.dll` は無い。自前ビルドは回避できた |
| 4/5 (R4/R5) | **同梱で自己完結** — HIP SDK 無しの機で `amdhip64_7.dll` / `hipblas.dll` が `_internal/` からロードされた |
| 5 (R7) | **採取不要** — float16 でロード・推論とも成功。OOM 文字列は出ていない |
| 6 (R9) | **OK** — 2 スレッド × 2 回を 2.5 秒で完走。ハング・例外なし |
| 7 | **大差で通過** — GPU 0.289s / CPU(int8) 6.045s = **20.95 倍**。打ち切り基準 1.2 倍を大きく超える |
| 8 (R6) | 未実施（RDNA4 の実機が無い） |

2 回目の実行（Stage D/E/F 追加版）でモデルのロード時間も採った:

| | 時間 |
|---|---|
| GPU ロード (float16, large-v3-turbo) | **1.9s** |
| CPU ロード (int8, 同じモデル) | 1.9s |
| 1 発話 (GPU, best of 3) | 0.289s ← 1 回目と一致 |

**rocBLAS / Tensile の初期化は起動時間の問題にならない。** 同梱している
gfx ターゲット 7 種を削る動機は**サイズだけ**で、起動の速さは理由にならない。
1 発話のレイテンシも 1 回目と同値なので、計測は安定している。

### 統合 GPU が 2 台目として見える。設計はこれを正しく弾いた

| index | 名前 | compute capability | `hipMemGetInfo` | アーキゲート |
|---|---|---|---|---|
| 0 | AMD Radeon RX 7900 XTX | 11.0 | 24.0 GiB | **通す** |
| 1 | AMD Radeon(TM) Graphics（APU の iGPU） | 10.3 | **36.2 GiB** | **弾く** (major=10) |

CT2 の `get_supported_compute_types` は iGPU にも float16 を返す。つまり
**CT2 は選別しない**ので、`utils.py` のゲートが唯一の防波堤である。

**ゲートが無いと実害が出る形が具体化した（2026-09-21 の 2 回目の実行）**:
iGPU は共有メモリを見ているため **36.2 GiB** と報告する。dGPU の 24.0 GiB
より大きい。つまり一覧に両方出すと、ユーザーには「VRAM の大きい方」が
iGPU に見える。名前（`AMD Radeon(TM) Graphics`）も dGPU と紛らわしい。
**VRAM 表記を UI に出す場合、この値をそのまま信じさせてはいけない。**
`getComputeDeviceList` は `device_index` を dict のキーとして明示的に持ち回る
（リストの位置ではない）ため、1 台弾いても残りのインデックスはずれない。
この構造が実機で意味を持つことを確認できた。

### 翻訳側の基準値（NVIDIA、比較用）

Stage C は faster-whisper しか見ていない。VRCT は CT2 を**翻訳**にも使っており
（`ctranslate2.Translator`、全メッセージが通る）、そこは未検証だった。
Stage F を足すにあたり、RTX 2080 Ti で基準値を取った
（`jncraton/m2m100_418M-ct2-int8`、1文、`inter_threads=1` / `intra_threads=4`、best-of-5）:

| device / compute_type | 最速 | CPU int8 比 |
|---|---|---|
| cpu / int8 | 0.793s | 1.00x |
| **cuda / float16** | **0.401s** | **1.98x** |
| cuda / int8_float32 | 0.958s | 0.83x |
| cuda / float32 | 1.269s | 0.63x |
| cuda / int8_float16 | 2.476s | **0.32x** |

つまり翻訳も GPU で速くなるが、音声認識の 20.95 倍とは桁が違う（1文は小さい仕事）。
AMD 側がこの 1.98x を大きく下回るなら AMD 固有の問題と言える。

**副産物（AMD とは独立の既存問題）**: `getBestComputeType` の RTX 向け優先順位は
`int8_bfloat16 → int8_float16 → ...` なので、2080 Ti では **`int8_float16` が選ばれる**。
上表のとおりそれは `float16` の **6 倍遅く**、CPU よりも遅い。
AMD 側は `_AMD_COMPUTE_TYPES = ("float16", "float32")` で float16 を先に返すため、
この罠を偶然踏まずに済んでいる。**AMD 対応とは別件として切り出す。**

### ROCm 版はモデルの解放から帰ってこない（新規 R10）

上記の計測を全部終えた後、**プロセスが終了しない**。最後の出力行から 5 分以上、
CPU も GPU も動いていない状態で止まる。止まる場所は `WhisperModel` の参照が
落ちてデストラクタが走るところ（計測はすべて完了・出力済み）。

診断ツール側は `os._exit` で回避した。レポートの書き出しがハングより後ろに
あったため、**1 回目は計測結果を丸ごと失った**（協力者がコンソールを
コピーしてくれて助かった）。

**VRCT 本体はこれでは済まない。** `transcription_transcriber.py:165` で
`WhisperModel` を組むのは Transcriber の `__init__` であり、モデル変更・
デバイス変更のたびに Transcriber ごと作り直す。古い Transcriber が GC される
= デストラクタが走る = **その経路がフリーズする**。アプリ終了時も同じ。

Phase 3 に入る前に切り分けが必要:

- GPU モデルと CPU モデルのどちらの解放で止まるのか（今回の出力では区別不能）
- 解放そのものか、OpenMP / HIP のスレッド終了待ちか
- VRCT の「モデル切り替え」で再現するか（ツールの終了経路だけの問題か）

再現し続けるなら、対処は「解放しない（プロセス生存中はモデルを使い回す）」か
「解放を別スレッドに投げてタイムアウトで諦める」のどちらか。どちらも設計に響く。
**R9 は晴れたが、代わりに R10 が出た。**

---

## 11. リスクと未決事項

**R1〜R5・R7・R9 は 2026-09-21 の RX 7900 XTX 実機検証で解消した（§10.6）。
残るのは R6 / R8 と、新たに出た R10。**

| # | 未決事項 | 影響 | ブロック箇所 |
|---|---|---|---|
| R1 | ROCm CT2 で `get_cuda_device_count` / `get_supported_compute_types("cuda", i)` が AMD を返すか | 返さなければ「CT2 が個数、HIP が名前」という設計前提が崩れ、個数も HIP から取る必要 | spike 1。崩れても直す範囲は `_getGpuDeviceNames` 内のみ |
| R2 | **#2016 の DLL 名回避策が効くか。効かなければ ROCm 7.1 での CT2 自前ビルドを背負う** | 自前ビルドになると PR-5 の取得方法が「ビルド済み wheel を自前ホスト」に変わり CI が 1 段重くなる | spike 3。**Phase 3 に進む最大の前提** |
| R3 | `hipDeviceComputeCapability` / `hipDeviceGetName` の export 実在、および gfx→major のマッピング | 無ければアーキゲートを `hipGetDeviceProperties` の `gcnArchName` 文字列に落とす | spike 2 |
| R4 | ROCm 版 CT2 が MIOpen 等の追加 DLL を要求するか（CUDA 版は cuDNN を wheel 同梱、cuBLAS は外） | 同梱リストとサイズが増える | spike。**wheel の中身を見れば実機前でも半分分かる** |
| R5 | `amdhip64.dll` / `amd_comgr` がドライバ提供か | 同梱 130MB 超の増減。設計は変わらない | spike 4 |
| R6 | RDNA4 (#2021) の可否 | アーキゲートが `(11,12)` か `(11,)` か。1 行 | spike 8。入手できなければ**保守的に `(11,)` で出す** |
| R7 | HIP の OOM エラー文字列の実物 | VRAM エラーが「その他のエラー」に落ち、専用 UI 通知の代わりに機能 OFF になる（**アプリは死なない**） | spike 5。出荷ブロッカーではない |
| R8 | Tensile の探索パス（`rocblas/library` の相対位置 / `ROCBLAS_TENSILE_LIBPATH`） | frozen ビルドでだけ動かない可能性 | Phase 3 のビルド後実機 |
| **R10** | **ROCm 版 CT2 のモデル解放が返ってこない（§10.6 で実機確認）。** `transcription_transcriber.py:165` はモデル変更ごとに Transcriber を作り直すため、古いモデルの解放が UI 経路で走る | **モデル切り替え・デバイス切り替え・アプリ終了がフリーズしうる。** 診断ツールは `os._exit` で逃げたが本体では通らない | **Phase 3 の前に切り分ける。出荷ブロッカー候補** |
| **R9** | **ROCm 版 CT2 の `Translator` がスレッドセーフか。** `translation_translator.py:144` は `_ctranslate2_lock` (RLock) を持ち、mic/speaker の 2 経路から同一 translator を叩く設計。CUDA 版 CT2 はスレッドセーフだが **ROCm バックエンドは新規実装**で同じ保証があるか不明 | 保証が無いと実機フリーズを起こす。**過去に同種の失敗例がある**（外部ライブラリのクライアントをスレッドセーフと仮定した結果） | **spike 6。ここは必ず確認する** |

### 設計判断として明示的に先送りしたもの

- **GPU 失敗時の自動 CPU 降格**（§8-2）— AMD 対応の必須要件ではない。独立 PR。
- **`COMPUTE_MODE` をデバイス検出由来からビルドスタンプ由来へ** — 現状
  「CUDA 版を NVIDIA GPU 無しの機で動かすと `COMPUTE_MODE == "cpu"` になり
  Updater が CPU 版を preselect する」という軽微な既存不整合があるが、AMD 対応とは独立。触らない。
- **OCR / VAD の GPU 化** — NVIDIA でも CPU 実行（`CPUExecutionProvider` 固定）。
  AMD 対応ではなく全ユーザー向け最適化。混ぜない。
- **案C（ランタイムパック）** — ランタイム変種が 4 つ以上になったら再検討。
  そのとき PR-2/PR-3 の一本化が効いてくる。

---

## 12. 一行まとめ

第3エディションは必要だが**最後に**必要で、しかも VRCT の NSIS が既にオンデマンドダウンローダである
（`template.nsi:737-749`）ため案A の追加コストは
「zip 名 1 個・バジェット 2 個・ラジオ 1 個・locale 1 キー×5 言語・CI 1 ビルド」に収まる。
案B/C は `ctranslate2` が単一パッケージ名であるために `sys.path` 切替という新機構を要求し、
案C はそれを**CPU 版の起動パス**に持ち込む。したがって **D→A**。
そして **PR-1〜PR-5 は Radeon が 1 台も無くても安全にマージでき**、実機ゲートは
「#2016 の回避」「スレッド安全性」「CPU 比でレイテンシが改善するか」の 3 点にだけ置く。
