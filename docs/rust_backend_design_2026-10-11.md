# Rust バックエンド 設計書（2026-10-11）

Python バックエンド（約 3 万行）を Rust に置き換えるための設計。前提の調査は `rust_full_migration_survey_2026-10-11.md`、実測は `rust_full_poc_results_2026-10-11.md`、全エンドポイントは付録 A（`rust_backend_design_appendix_endpoints.md`）。

## 0. 前提（決定済み）

| 項目 | 決定 |
|---|---|
| 目的 | 速さではなく、バックエンド全体を Rust にすること |
| 置き場所 | Rust の sidecar（`VRCT-sidecar.exe`）。今の IPC 契約（stdin/stdout の 1 行 JSON、base64 の `data`、status、エンドポイント名）を保ち、UI は変えない |
| 結果の一致 | 推論（Whisper・翻訳・VAD・YOLOX・OCR）は今の Python と数値まで一致させる。PoC で全て達成済み |
| CTranslate2 | Python の wheel の `ctranslate2.dll` を自作の C の受け口から呼ぶ。版の更新は DLL とヘッダーを差し替え、回帰テストを流す（§7） |
| CUDA | 対応する。CUDA Toolkit は不要（cuBLAS / cuDNN の DLL を同梱） |
| OCR | RapidOCR 3.9.2 の前後処理を自前で移植済み（Apache-2.0 の表示あり） |
| OSCQuery | `vrchat_osc` クレート |
| 参照 | 第三者のフォークは参照しない。設計・実装は一次情報（各ライブラリのソース・仕様）から |
| 対象 | Windows x64 のみ |
| 移行元 | v3.6.x からの上書きインストールを保証する。それより古い版のための互換処理は持ち込まない |
| UI との確認 | 契約テストで見つかった、UI の使い方が不明な応答・挙動は、ユーザーに確認する（ユーザーがフロントエンドと調整） |
| §11 の決定 | 2026-10-11 にすべて決定（§11 の表） |

## 1. 要点

1. **1 つの実行ファイル + 少数のネイティブ DLL**。sidecar は Rust のワークスペースから作る。推論の DLL（CTranslate2・onnxruntime・OpenBLAS）だけは今の Python 版と同じバイナリを同梱する。
2. **契約は付録 A と §3 で固定**。330 の要求エンドポイントと 81 の push を同じ名前・同じ JSON で返す。言語に依存しない契約テスト（sidecar に stdin で投げて stdout を見る）を先に作り、Python 版と Rust 版の両方に当てる。
3. **一致の基準を 3 段に分ける**（§8）。推論は数値まで、IPC と外部 API への要求は JSON まで、デバイス・描画は振る舞い（実機で確認）。
4. **移行は「部品 → 土台」の順**（§9）。推論・ネットワーク・ファイルなど部品をクレートとして作り、Python と照合してから、最後に IPC・設定・制御（今の `mainloop` / `config` / `controller`）を Rust で書いて差し替える。デバイスに触れる部品（録音・オーバーレイ・キャプチャ）は、今までと同じく PyO3 で今の Python 版に組み込んで実機確認できるようにする。

## 2. 全体構成

```
UI (Tauri, 変更なし)
  │ stdin: {"endpoint", "data": base64(JSON)}      stdout: {"status","endpoint","result"} / {"status":348,...}
  ▼
VRCT-sidecar.exe (Rust)
  ├ ipc        受信スレッド・振り分け・stdout 書き込みスレッド・ログ
  ├ app        状態 (AppState)・設定 (config.json)・起動/終了・watchdog・エンドポイント本体
  ├ pipeline   メッセージパイプライン (mic / speaker / chat / ocr)
  ├ audio      録音 (PortAudio / WASAPI)・デバイス管理・既定デバイス追跡・エネルギー・区切り・VAD
  ├ asr        ローカル Whisper (CTranslate2) と API (Google / OpenAI 互換 / Deepgram)
  ├ translate  CTranslate2 (NLLB / M2M100)・Web 翻訳・DeepL・LLM 各社
  ├ translit   Sudachi + かな→ヘボン式
  ├ ocr        キャプチャ・吹き出し検出 (YOLOX)・RapidOCR
  ├ overlay    OpenVR オーバーレイ・文字描画・VR UI (GPU)
  ├ osc        OSC 送信・OSCQuery
  ├ net        WebSocket・OBS ブラウザソース・ネットワーク確認
  └ platform   クリップボード・プロセス確認/優先度・ファイルを開く・重み/更新のダウンロード・テレメトリー
  │
  ├ ctranslate2.dll / libiomp5md.dll / cudnn64_9.dll   (ctranslate2 4.6.0 の wheel から)
  ├ onnxruntime.dll                                     (onnxruntime の wheel から)
  ├ libopenblas64_*.dll                                 (numpy 1.26.4 の wheel から、メル特徴量の行列積だけ)
  └ (CUDA 版) cublas64_12.dll / cublasLt64_12.dll / cudnn*_9.dll (nvidia-*-cu12 の wheel から)
```

### 2.1 ワークスペース

`native/` にワークスペースを作る。クレートはビルドの境界（C++ のビルド、PyO3、重いテスト）でだけ分け、アプリの中身は 1 つのクレートのモジュールにする。

| クレート | 中身 | 由来 |
|---|---|---|
| `vrct-backend`（bin） | ipc / app / pipeline / asr / translate / translit / osc / net / platform | 新規 |
| `vrct-ct2` | CTranslate2 の受け口（`shim/ct2_shim.cpp`、`build.rs` で DLL からインポートライブラリを生成）と安全な Rust の型 | `native/poc-ct2dll` を育てた（P1） |
| `vrct-whisper` | faster-whisper 1.1.1 の移植（メル特徴量、`transcribe` のループ、抑止トークン、言語判定） | `native/poc-ct2/src/mel.rs` ほか（P1） |
| `vrct-ocr` | YOLOX・RapidOCR・OpenCV / numpy の移植、Clipper、bidi | `native/poc-ort` を育てた（P1） |
| `vrct-audio` | 既存。PyO3 部分を feature に分け、録音・デバイス管理を追加 | 既存 |
| `vrct-graphics` | 既存。VR UI の GPU 経路。オーバーレイ全体の土台へ | 既存 |
| `vrct-webtranslate` | Web 翻訳（Google / Bing / Papago）。別リポジトリ `translator_engines` のソースを取り込み、PyO3 の入口（`lib.rs` の 5 関数）を外して Rust の関数として公開する（ユーザー承認済み） | `D:\WORKSPACE\WORK\VRChatProject\translator_engines` |

`vrct-audio` / `vrct-graphics` / `vrct-ocr` は feature `python` で PyO3 の入口を残し、移行中は今の Python 版からも使えるようにする（実機確認のため）。土台を差し替えた後に `python` feature は消す。今の Python 版が使っている `translator_engines.pyd` は、切り替えまでそのまま使う。

## 3. IPC（契約）

今の `mainloop.py` / `utils.py` の挙動をそのまま写す。UI 側（`StartPythonController.jsx`、`useReceiveRoutes.js`）が依存しているのは次の点。

| 項目 | 契約 |
|---|---|
| 受信 | stdin の 1 行 = `{"endpoint": str, "data": base64(JSON) | null}`。base64 / JSON の失敗は `{}` として扱い、error.log に残す |
| 応答 | stdout の 1 行 = `{"status": int, "endpoint": str, "result": any}`。`result` は素の JSON |
| status | 200 / 400（`result` = `{error_code, message, data, details, category, severity}`）/ 404（`"Invalid endpoint"`）/ 423（`"Locked endpoint"`、`"Locked endpoint (busy)"`）/ 500（`"Internal error"`）/ 348（ログ。UI は捨てる） |
| push | `run_mapping` の 81 件を同じ形で、任意のスレッドから送る |
| 起動完了 | `/run/initialization_complete` の `result` に、全 `/get/data/*`（`available_releases` を除く）の結果をまとめて 1 回送る |
| stderr | **書かない**。UI は `Warning:` を含まない stderr の行を致命的エラーとして通知する（§3.3） |

### 3.1 振り分け

- 受信スレッド 1 本 → キュー → 処理ワーカー。ワーカー数の既定は 3（今と同じ。並びの前提を変えないため。テストで確かめてから増やせるよう設定値にする）。
- **同じ機能は直列**: `/set/enable/X` と `/set/disable/X` を同じ鍵 `/lock/set/X` に寄せ、鍵ごとの排他。取れなければ 50 ms 後に再キュー、400 回（約 20 秒）で `423 "Locked endpoint (busy)"`。
- **初期化中**: 付録 A で ✗ のエンドポイントは初期化が終わるまで 423 を返して 100 ms ごとに再キュー、300 回（約 30 秒）で 423 を返す。
- ハンドラの型は `fn(&App, Option<Value>) -> Response`（`Response = {status, result}`）。表を 1 か所に置き、付録 A と突き合わせるテストを持つ。
- 処理は同期（ブロッキング）で書き、ワーカーは OS スレッド。ネットワーク・推論の待ちは各モジュールの中で閉じる（§5）。

### 3.2 stdout とログ

- 書き込みは専用スレッド 1 本。応答は無制限キュー（取りこぼさない）、348 のログは 200 件の有界キュー（あふれたら古いものを捨てる）。応答を優先して出す。
- 書き込みが 50 回続けて失敗したら UI が消えたとみなして終了する。
- 秘密の伏せ字: エンドポイント名（空白は `_` にして）に `auth_key` / `api_key` / `password` / `token` / `secret` を含むものは値を `***MASKED***`、集約応答（`initialization_complete`）はキーごとに再帰で判定。`/run/vr_panel_pointer` は process.log に残さない。
- `process.log`・`error.log` は今と同じ場所・名前、10 MB で切り詰め（ローテートしない。Tauri の監視対象を増やさないため）。
- JSON の違いは許す: Python は非 ASCII を `\uXXXX` で出すが、Rust は UTF-8 のまま出す（UI の `JSON.parse` では同じ値）。348 の `data` 文字列（Python の `str()`）は中身が変わってよい（UI は使っていない）。

### 3.3 stderr を空にする

stderr に出うるものを全部止める。

- Rust の panic: panic フックで error.log と `crash_trace.log` に書き、stdout に `{"status": 500, ...}` を出してから終了する（UI は 500 を通知する）。
- CTranslate2: 受け口の初期化で `set_log_level(off)`（`CT2_VERBOSE` を開発時だけ通す）。
- onnxruntime: 環境のログ水準を致命のみにする（RapidOCR の `log_severity_level = 4` と同じ）。
- それでも残るもの（ドライバー等）に備え、起動直後に CRT の `stderr` を `error.log` へ付け替える（受け口の C++ 側で `freopen`。P0 で確認済み: `CT2_VERBOSE=1` の CTranslate2 のログ 14 行が、付け替え後は stderr に 0 行、ファイルに 14 行）。onnxruntime はログの水準で止める。

### 3.4 終了と watchdog

- `/run/shutdown`: 各機能を止め、設定を保存し、テレメトリーを送って終了（UI は 2 秒後に閉じる）。
- `/run/feed_watchdog` が 60 秒途絶えたら（20 秒ごとに確認）停止処理を始め、30 秒で必ず終了する（`escalateShutdown` と同じ）。
- stdin の EOF は「UI がいない」とみなす。今は EOF で待ち続けるだけなので、Rust 版も watchdog に任せる（挙動を変えない）。

## 4. 状態と設定

### 4.1 AppState

モジュールのシングルトン（今の `config` / `model`）はやめ、`Arc<App>` に集める。

```
App
 ├ config: Mutex<Config>          設定 (§4.2)。読み出しは複製を返す
 ├ flags:  起動時は OFF で保存しない状態 (翻訳/文字起こし/OCR の ON・OFF 等)
 ├ init:   初期化中かどうか (振り分けの 423 判定に使う)
 ├ services: 各モジュールの稼働中のもの (録音セッション、翻訳器、オーバーレイ、OSC、サーバー…)
 └ push:   stdout 書き込みスレッドへの送信口
```

### 4.2 設定（`config.json`）

- 156 項目を **1 つの表（宣言マクロ）** で定義する: 名前（今と同じ UPPER_SNAKE）・型・既定値・検証関数・保存方法（遅延 / 即時）・保存対象かどうか・読み取り専用か。Rust の構造体・JSON の読み書き・`/get` `/set` の多くはこの表から作る。
- 保存: 遅延保存（今の `_debounce_time`）と即時保存。一時ファイルに書いて `fsync` → `rename`。字下げ 4、非 ASCII はそのまま（今と同じ書式）。
- 読み込み: 表に無いキーは捨てる、読み取り専用・非保存は無視、検証で拒否された値は既定値のまま error.log に残す（今と同じ）。読み込み後の補正も同じ順で行う: `SELECTED_RELEASE_CHANNEL` を実行中の版から決め直す、`installer_language.txt` を反映して消す、選択中のモデルが一覧に無ければ先頭へ、WebSocket のトークンが無ければ生成。
- 検証の拒否は `ConfigValidationError` と同じく 400 の ErrorCode にする（`_configValidationErrorResponse` の対応表を写す）。キー単位で旧値に戻す検証（ホットキー等）はそのまま。

### 4.3 エラーコード

`errors.py` の `ErrorCode`（88 件）と `ERROR_METADATA`（カテゴリー・既定メッセージ・深刻度）を、`native/reference/export_error_codes.py` で `native/data/error_codes.json` に書き出し、Rust 版はそれを取り込む（手で写さない）。契約テストで、同じ入力に同じ `error_code` / `message` / `category` / `severity` が返ることを確かめる。`register_error_report_hook`（テレメトリーへの報告）も同じ位置に置く。

## 5. 実行モデル

| 種類 | 方式 |
|---|---|
| IPC | 受信 1 本、ワーカー 3 本、stdout 書き込み 1 本（すべて OS スレッド） |
| 録音 | デバイスごとに読み取りスレッド 1 本。コールバックからは有界キューに積むだけ（あふれたら古いものを捨てる、今の `putDroppingOldestOnFull`） |
| 推論 | Whisper・翻訳は CTranslate2 のプール（`inter_threads=1`, `intra_threads=4`、今と同じ）を呼ぶ。呼び出し側は専用スレッド。onnxruntime の Session はモデルごと 1 つ |
| ネットワーク | HTTP は `reqwest` のブロッキング API（タイムアウトは今の値を写す）。WebSocket・OBS・OSCQuery は小さな tokio ランタイム 1 つの上で動かす |
| 取り消し | 停止要求は各セッションの停止フラグ + `join` の上限時間（今の値: 録音の open 8 秒、停止 15〜20 秒）。上限を超えたら置き去りにして先へ進み、記録する |

## 6. 機能ごとの設計

一致の基準: **N** = 数値まで一致（推論）、**C** = IPC の JSON・外部 API への要求が一致、**B** = 振る舞いが同じ（実機で確認）。

### 6.1 録音・デバイス（`audio`）— B

| 今 | Rust | 注意 |
|---|---|---|
| PyAudioWPatch（PortAudio + WASAPI ループバック） | **`cpal`（WASAPI）**。ループバックは出力デバイスに入力ストリームを開く（`cpal` 0.16 で動作確認済み） | 下の「デバイス名の互換」 |
| pycaw / comtypes（既定デバイス・変更通知） | `windows` クレートで `IMMDeviceEnumerator` / `IMMNotificationClient` | 通知はコールバックからキューへ積むだけにする |
| `active_endpoint_tracker` | 同じ判定を移植 | 後始末のタイムアウトは今の値 |
| エネルギー・区切り（`vrct-audio`）・Silero VAD（ort、PoC で一致確認済み） | そのまま使う。Silero VAD は録音と一緒に P3 で `vrct-audio` へ移す（PoC のコードは git の履歴 `native/poc-ort/src/main.rs`） | 3 秒境界・語尾の扱いは今の Rust 側の修正を引き継ぐ |
| `audioop` / `pydub` / `av`（形式変換） | `vrct-audio` の PCM 変換・FLAC | 16 kHz / 16 bit への変換の丸めを Python と比べる |

**デバイス名の互換**（2026-10-11、同じ PC で PyAudioWPatch と `cpal` を比べた結果）:

- `cpal` のデバイス名は、PortAudio の「Windows WASAPI」ホストの名前と完全に同じ（Windows のフレンドリー名）。既定の入力・出力も同じ。
- PortAudio のループバックは `<出力デバイス名> [Loopback]` という名前で、設定の `SELECTED_SPEAKER_DEVICE` にもこの名前が入る。Rust 版も一覧と設定ではこの名前を使い、開くときに末尾を外して出力デバイスを探す。
- ホストは WASAPI だけになる。ホストの一覧は `["Windows WASAPI"]` を返す。設定に `MME` / `Windows DirectSound` が入っていたら、読み込み時に `Windows WASAPI` へ移し、デバイスは名前の前方一致（MME は 31 文字で切れている）で探し、無ければ既定のデバイスにする。
- `cpal` は共有モードの float32（この PC では 48 kHz）で受け取る。int16 への変換（PortAudio が中でしていた）は自前で行う。録音の値は Python と少し変わりうるが、この層は B（振る舞い）で確認する。

デバイスまわりは過去に実機でしか分からない不具合が多かった。PyO3 で今の Python 版に組み込み、抜き差し・既定の切り替え・VRChat 起動中の検証を、移行の前に一つずつ実機で行う（今までと同じ手順）。

### 6.2 文字起こし（`asr` / `vrct-whisper`）— N（ローカル）・C（API）

- ローカル Whisper: `WhisperModel.transcribe` のうち VRCT が使う経路を移植する。`beam_size=5`、`temperature=0.0`、`without_timestamps=True`、`word_timestamps=False`、`vad_filter=False`、言語指定あり・なし、`no_repeat_ngram_size`、`condition_on_previous_text`（30 秒を超える音声で前の窓の文字を次の窓のプロンプトに入れる）、`log_prob_threshold` / `no_speech_threshold` による捨て方、`get_suppressed_tokens`、言語判定（最後のフレーム込みの 30 秒を別にエンコード）。
- メル特徴量は numpy と同じ計算（PoC 済み）。行列積だけ numpy の OpenBLAS を呼ぶ。
- 重みの読み込み失敗・VRAM 不足（`CUDA out of memory` / `CUBLAS_STATUS_ALLOC_FAILED`）を今と同じ ErrorCode にする。
- API: Google（非公式 v2、FLAC を送る。元は speech_recognition の BSD のコード）、OpenAI 互換（Groq / OpenAI / Custom）、Deepgram。HTTP の要求を Python と同じにする（§8 の「要求の記録と比較」）。

### 6.3 翻訳（`translate`）— N（CTranslate2）・C（その他）

- CTranslate2: NLLB は `tokenizer.json`（tokenizers クレート）、M2M100 は `sentencepiece.bpe.model` + `vocab.json`（`M2M100Tokenizer` の処理を移植: spm で分割 → 語彙で ID → 言語トークン + `</s>`）。復号は transformers の `decode`（既定の空白の掃除を含む）と一致させる。大きめの文のコーパスで Python と照合する。
- Web 翻訳（Google / Bing / Papago）: `translator_engines` のソースを `vrct-webtranslate` として取り込む。中身は今も Rust（reqwest のブロッキング）なので、PyO3 の入口を外すだけ。
- DeepL: REST を直接呼ぶ（`deepl` パッケージが送る要求と同じにする）。
- LLM（OpenAI / Groq / OpenRouter / Plamo / LM Studio / Ollama / OpenAI 互換）: langchain は 1 回の `invoke` だけなので、各 API を `reqwest` で直接呼ぶ。プロンプトは今の YAML をそのまま読む。要求の本文（モデル名・メッセージ・温度など、langchain が付ける既定値を含む）を Python と同じにする。モデル一覧の取得・認証確認も同じ API。
- Gemini: 翻訳は langchain-google-genai 2.1.10 の `ChatGoogleGenerativeAI`（transport の指定なし = **gRPC** の `GenerativeService.GenerateContent`）、モデル一覧は google-genai 1.45 の SDK（REST）。Rust 版は同じ API の REST 版（`models/{model}:generateContent`）で送る。HTTP の記録では比べられないので、Python 側は送る直前の要求オブジェクト（protobuf）を JSON にして書き出し、Rust の REST の本文と項目ごとに比べる。
- 起動時の各エンジンの確認は並列（今と同じ）。

### 6.4 音訳（`translit`）— N

- SudachiPy 0.6.10（`dict_type="full"`, `SplitMode.C`）の中身は sudachi.rs そのもの。Rust 版は sudachi.rs の同じ版（タグ `v0.6.10`、git 依存で固定）を使う。辞書は SudachiDict-full 20250825 の `system_full.dic` を同じものを使う。かな→ヘボン式・文脈ルールは移植。
- 一致の確認: 日本語のコーパスで、トークン・読み・ローマ字を Python と比べる。

### 6.5 メッセージパイプライン（`pipeline`）— C

`models/message_pipeline.py` の `MessageDirectionSpec`（mic / speaker / chat / ocr）をそのまま Rust の定数にする。順序: ワードフィルター（mic/speaker/ocr）→ 繰り返し検出 → 翻訳 → 音訳 → OSC → オーバーレイ → クリップボード（mic）→ UI へ push / 戻り値（chat）→ WebSocket → ロガー → 履歴。ワードフィルターは flashtext と同じ語境界の規則で書く（aho-corasick だけでは境界の扱いが違う）。

### 6.6 OSC / OSCQuery（`osc`）— B

- 送信（`/chatbox/input`, `/chatbox/typing`）は設定の IP:ポートへ UDP（rosc）。
- 受信と OSCQuery は `vrchat_osc`（mDNS の VRChat 固有の癖に対応済み）。受信は 1 本で順に処理し、`/avatar/change` の問い合わせは別スレッド（今の修正を引き継ぐ）。
- 実機確認: VRChat 先起動・VRCT 先起動の両方でミュート同期と通知（`native/poc-oscquery`）。

### 6.7 VR オーバーレイ（`overlay` / `vrct-graphics`）— B

- OpenVR: `vrct-openvr`。今の Python 版と同じ Valve の openvr_api 1.26.7（pyopenvr 1.26.701 が同梱する DLL とバイト単位で同じ。`third_party.toml` で Valve の GitHub のタグから取る）を、C の関数テーブル（`FnTable:IVROverlay_027` など。並びは `native/reference/gen_openvr_tables.py` が pyopenvr の定義から生成）で呼び、使う約 30 の関数だけを安全な型で包む。オーバーレイ・OCR・クリップボードは参照カウント付きの 1 つのセッションを共有する。`openvr` / `openvr_sys` クレート（SDK 2.15.6）は、インターフェースの版が上がって挙動が変わりうることと、ビルドに CMake と libclang が要ることから使わない（2026-10-12、ユーザー判断）。
- VR UI（ランチャー・ログウィンドウ）: 既存の GPU 経路（WGC → D3D11 → SteamVR）だけを使う。OpenGL の退避経路（`VRCT_OVERLAY_GPU=0`）は持ち込まない。2026-10-12 に `vrct-overlay` へ移植（ログのオーバーレイも同じスレッド。画像は D3D11 のテクスチャで渡す）。姿勢・並び・マスク・吹き出しの判定は `native/reference/export_overlay_vr.py` の記録と照合。今の Python 版では `VRCT_RUST_OVERLAY=1`（`models/overlay/rust_overlay.py`）で Rust 版に切り替わり、SteamVR の接続は pyopenvr と同じ DLL を Rust が持つ（`openvr_session` も同じ参照の数に乗る）。実機で確認済み。計測の記録（`VRCT_OVERLAY_PROFILE`）と処理の止まりの見張りは持ち込まない。SteamVR を終了した後は、次の起動を待ってつなぎ直す（Python 版は止まったまま）。
- 文字の描画（小さいログ・大きいログ・ふりがな）: 最終的には VR UI へ切り替える前提なので、**機能が動けば十分**（画像の一致は求めない）。FreeType 系のクレートで `overlay_image.py` の配置（折り返し・ふりがな・色・大きさ）を移植し、実機で見て確認する。

### 6.8 OCR（`vrct-ocr`）— N（認識）・B（キャプチャ）

- 検出（YOLOX）・認識（RapidOCR の移植）は PoC で全段階一致済み。アラビア語の表示順（python-bidi 0.6.11 = unicode-bidi クレート）を追加する。
- キャプチャ: D3D11（SteamVR のミラー）、ウィンドウ（HWND）、OpenVR。`windows` クレートで書き直す。黒画面判定（12 ms 版）も移植。
- パイプライン（重複の抑制、周期の 80% の予算、最大 6 候補）は `ocr_pipeline.py` を移植。

### 6.9 WebSocket・OBS・クリップボード（`net` / `platform`）— C・B

- WebSocket サーバー: tokio-tungstenite。認証トークン・送る JSON は今と同じ。異常切断で落ちない（過去の不具合の再発防止テストを持つ）。
- OBS ブラウザソース: 小さな HTTP サーバー（std の `TcpListener`。止めたらすぐ同じポートで始め直せるよう、待ち受けを閉じてから戻る）で同じ HTML と同じ API。
- クリップボード: arboard + Win32（フォーカス・貼り付け）。SteamVR 起動中の判定も同じ。

### 6.10 重み・ソフトの更新（`platform`）— B

- 重み: Hugging Face から取得。**ディレクトリ構成・`.weight_verified.json` の印を今と同じにする**（既存のインストールの重みをそのまま使うため）。再試行・タイムアウト・進捗の push 間引きも同じ。
- ソフト更新: GitHub API でリリース一覧、`VRCT_setup.exe` を取得して `.sha256` で照合（公開されているのに取れなければ中止）、引数（`/EDITION`, `/UILANG`, `/CHANNEL`）を付けて起動し終了。

### 6.11 その他（`platform`）

テレメトリー（Aptabase の HTTP API を直接、イベント名・重複の抑制は同じ。キーは今の CI が secrets から `telemetry_keys.py` を作っているのを、ビルド時の環境変数（`option_env!`）に替える。キーの無いビルドは送らない）、プロセスの確認（VRChat / SteamVR）、優先度、ログ・設定ファイルを開く、ネットワーク確認、計算デバイスの一覧（`ct2_cuda_device_count` と `ct2_supported_compute_types` を受け口に用意済み）と `getBestComputeType` の規則。

## 7. ネイティブ依存の固定と更新

`native/third_party.toml` に版と取り出すファイル・SHA-256 を書き、ビルド前に `cargo xtask fetch-native` が PyPI の wheel（zip）とタグのヘッダーを取ってきて `native/third_party/` に置く（Python は不要）。

| 依存 | 取り出し元 | ファイル | 用途 |
|---|---|---|---|
| CTranslate2 4.6.0 | `ctranslate2` の wheel + GitHub タグ `v4.6.0` の `include/` | `ctranslate2.dll`, `libiomp5md.dll`, `cudnn64_9.dll`, ヘッダー | Whisper・翻訳 |
| onnxruntime | `onnxruntime` の wheel（今の Python と同じ版） | `onnxruntime.dll` | VAD・YOLOX・OCR |
| OpenBLAS | `numpy` 1.26.4 の wheel | `libopenblas64_*.dll` | メル特徴量の行列積 |
| CUDA（CUDA 版のみ） | `nvidia-cublas-cu12` 12.8.4.1、`nvidia-cudnn-cu12` 9.7.1.26 の wheel（今と同じ） | `cublas*`, `cudnn*` | CTranslate2 の CUDA |

**更新の手順**: `third_party.toml` の版を上げる → `fetch-native` → ビルド（インポートライブラリは自動で作り直す）→ 回帰テスト（§8 の推論コーパス）。受け口のコードを直すのは CTranslate2 が C++ の API を変えたときだけ（4.6.0 → 4.8.2 では 0 行、実測）。移行が終わった後は「Python と一致」ではなく「前の版の結果からの変化を確認して承認」になる（今 Python で `pip` の版を上げるときと同じ）。

## 8. 一致の基準と検証

| 層 | 対象 | 方法 | 合格 |
|---|---|---|---|
| N（数値） | Whisper・NLLB・M2M100・VAD・YOLOX・OCR・Sudachi | Python で基準を書き出し、Rust と比べる（`poc-ct2dll`・`poc-ort` の比較を CI のテストにする）。コーパスを増やす（音声 数十本、翻訳 数百文 × 言語、吹き出し数百枚、日本語文） | 完全一致 |
| C（契約） | 330 エンドポイント・81 push・ErrorCode | 言語に依存しない契約テスト（sidecar を起動し、stdin に投げて stdout を見る）。今の Python のテストのうち IPC で書けるものを移す。まず Python 版に当てて通ることを確かめ、それを Rust 版の合格基準にする | JSON が一致（順序と 348 は除く） |
| C（外部 API） | LLM・DeepL・Deepgram・Google 音声・Hugging Face・GitHub・Aptabase | ローカルの模擬サーバーへ向けて、Python と Rust が送る HTTP 要求（パス・ヘッダー・本文）を記録して比べる | 秘密以外が一致 |
| B（振る舞い） | 録音・デバイス変更・OSC・SteamVR・キャプチャ・オーバーレイの表示 | 実機の確認表（今までの検証手順を再利用）。項目ごとに実機で 1 つずつ | 確認表がすべて合格 |

数値の一致は、AVX2 と FMA を持つ x64 CPU を基準にする（numpy・OpenBLAS は CPU によって計算方法を変えるため。対象は Windows x64 のみ）。基準データを作るための Python 環境は、移行が終わるまで残す。作った基準（JSON・小さい音声と画像）はテストとともに保存し、Python を消した後も回帰テストに使う。

## 9. 移行の段階

| 段階 | 内容 | 完了条件 |
|---|---|---|
| P0 土台 | ワークスペース、`third_party.toml` と `fetch-native`、契約テストの枠（Python 版に当てて通す）、基準データの書き出しスクリプト、ErrorCode の変換 | 契約テストが Python 版で全件通る。**2026-10-11 完了**: 191 件に応答・期待の status との違い 0・stderr 0 行、Python 同士の比較で差 0。取得した DLL は venv のものと同一、それでのビルドと stderr の付け替えを確認 |
| P1 推論 | `vrct-ct2`・`vrct-whisper`（transcribe の全経路）・翻訳（NLLB / M2M100）・`vrct-ocr`（bidi 追加）・Sudachi | §8 の N がコーパスで全件一致。**2026-10-11 完了**（Silero VAD は P3 へ）: NLLB 600M・M2M100 418M（分割・翻訳・復号）、Whisper base（58 ケース、80 / 128 メルの特徴量、30 秒超を含む）を CPU（int8）と CUDA（int8_float16）で、OCR（合成画像 54 枚と実際の画面 80 枚、6 言語のモデル、bidi）と音訳（85 文、カタカナ列 500）を CPU で、すべて違い 0。基準は `native/testdata/`、作り方は `native/reference/`。1.3B / 3.3B / 1.2B / Whisper の他の大きさは重みが手元に無く未照合（同じ処理） |
| P2 外部 API・ファイル | ASR / 翻訳の API、DeepL、Web 翻訳（`vrct-webtranslate`）、重み・更新、テレメトリー、WebSocket、OBS | §8 の外部 API の比較が一致、サーバーの再発防止テスト。**2026-10-12 完了**: Python が送る直前の HTTP の要求（httpx / requests / urllib）を記録し、Rust の要求とメソッド・URL・本文・ヘッダーで比べて違い 0。LLM 8 種（認証・モデル一覧・翻訳、401 を含む）、DeepL（429 の再試行を含む）、文字起こしの API 40 手順と Deepgram の言語の解決 811 件、ソフトの更新 15 手順と版の比較 900 件、重みの取得（範囲外のファイル名・404・500 の再試行を含む）と `.weight_verified.json`（Python が書いた印をそのまま読む）、テレメトリー（起動 11 通りの送信と状態ファイル）、OBS のページ（設定 10 通り）と応答。Web 翻訳は取り込んだ単体テスト 17 件。WebSocket はトークンの検査と、閉じずに切れたクライアントがいても他へ届き続ける再発防止テスト。トークナイザーの取得は B（transformers の要求は写さず、読む側と同じキャッシュの形に書く）。Python と変えた点: Hugging Face のトークンを送らない、トークナイザーがそろっていれば取りに行かない |
| P3 デバイス | 録音・デバイス管理・既定の追跡・OSC/OSCQuery・オーバーレイ（OpenVR・文字描画）・キャプチャ・クリップボード。PyO3 で今の Python 版に組み込んで実機確認 | 実機の確認表がすべて合格。**2026-10-12 完了**: 音声の前処理・VAD・録音デバイス（`VRCT_RUST_AUDIO=1` で実機の抜き差し・スピーカーの自動切り替え・ミュート同期 OK）、OSC、OpenVR の層（値は pyopenvr と一致）、OCR のキャプチャ（実機でミラー取得）、ログの文字画像（大きさ一致）、ログのオーバーレイと VR UI（`VRCT_RUST_OVERLAY=1` で実機 OK）、クリップボードのアプリ名（実機で Python と同じ名前）。OSCQuery は P4 で VRChat とつないで確かめる |
| P4 土台の差し替え | `ipc` / `app`（設定・エラー・起動/終了・watchdog）/ `pipeline` / 330 エンドポイントの本体を Rust で実装し、P1〜P3 の部品をつなぐ | 契約テストが Rust 版で全件通る、実機の通し確認。**2026-10-13 実装完了**（VR の実機確認は後で）: `VRCT-sidecar.exe`（`vrct-backend` の bin）で 330 件すべてを Rust で処理。契約テスト 216 件・起動時の値 144 件で Python との差 0、stderr 0 行。設定の検証は 6181 通りで一致、ルート表と push 名は `mainloop.py` から書き出したものと一致（`tests/routes.rs`）。UI からは `npm run dev-rust-fast`（dev_sidecar の `VRCT_DEV_BACKEND=rust`、配置は `cargo xtask stage-sidecar`）。実機確認済み: チャット・翻訳、音声（一覧・メーター・文字起こし・切り替え・抜き差し・自動選択）、OSC / OSCQuery とミュート同期（両方の起動順）、OCR、終了。未確認: オーバーレイと VR UI |
| P5 切り替え | 配布（spec・bat・インストーラ）を Rust 版に。まず beta チャンネルで並行運用、`config.json`・重み・ログの互換を確認 | beta で問題なし → stable へ、Python のコードと依存を削除。**2026-10-13 配布の組み替え**: `bat/build(_cuda).bat` は `fetch-native` → `cargo build --release` → `cargo xtask stage-sidecar --release` で `src-tauri/bin` に exe と `_internal/`（DLL・翻訳設定・フォント・Sudachi 辞書・Silero・OCR モデル・ライセンス）を置く。DLL は `_internal` から読む（`AddDllDirectory`、ctranslate2 は遅延読み込み）。版は `package.json` からビルド時に、テレメトリーの鍵は CI がタグのチャンネルで選んで渡す。インストーラは上書き時に古い `_internal` を退避して入れ替える。契約テストは `_internal` の配置で差 0。stable は Python のまま（Python のコードは残す） |

P1〜P3 は互いに独立していて並行できる。P4 は P1〜P3 がそろってから。

## 10. 配布

- 中身: `VRCT-sidecar.exe` + §7 の DLL + 今と同じデータ（言語表・プロンプトの YAML、Sudachi 辞書、ONNX モデル、Whisper / CTranslate2 の重みは今と同じく初回にダウンロード）。
- CPU 版 / CUDA 版の 2 つ（今と同じ）。CUDA 版だけ cuBLAS / cuDNN の DLL を足す。
- 置き場所・ファイル名（`config.json`、`logs/`、`process.log`、`error.log`、`weights/`）は今と同じにして、上書きインストールでそのまま動くようにする。
- 互換は v3.6.x の `config.json`・重み・ログまで。それより古い版のための処理（重みフォルダの旧名からの改名 `backwardCompatibleTranslatorCTranslate2ModelRenameWeightsDir` など）は持ち込まない。P4 で、Python に残っている互換処理を一つずつ「v3.6.x で要るか」で仕分ける。
- Python の実行環境（PyInstaller の出力）が無くなる分、配布物は小さくなる見込み（P5 で実測）。2026-10-13 の CPU 版の実測: 合計 589 MB（重みを除く）。うち Sudachi 辞書 343 MB、exe と DLL 132 MB、OCR モデル 84 MB、フォント 28 MB。

## 11. 決定事項（2026-10-11、ユーザー）

| # | 項目 | 決定 |
|---|---|---|
| 1 | 移行の進め方 | §9 の「部品 → 土台」 |
| 2 | 録音のライブラリ | Rust のもの（`cpal` の WASAPI）。デバイス名の互換は §6.1 |
| 3 | `translator_engines` | Python のために作ったもの。ソースをこのリポジトリに取り込んでよい（`vrct-webtranslate`） |
| 4 | オーバーレイの経路 | GPU 経路のみ |
| 5 | オーバーレイの文字画像 | 最終的に VR UI へ切り替える前提なので、機能が動けば十分（画像の一致は求めない） |
| 6 | Sudachi | sudachi.rs（SudachiPy 0.6.10 と同じ v0.6.10） |
| 7 | 振り分けのワーカー数 | 当面 3 |
| 8 | 対象 | Windows x64 のみ |
| 9 | 移行元 | v3.6.x から（それより古い版の互換処理は持ち込まない） |
| 10 | UI 側の確認 | ユーザーに聞く（ユーザーがフロントエンドと調整） |

### 残っている確認（P0〜P1 の最初に行う）

| 項目 | 確認の内容 | 外れた場合 | 結果 |
|---|---|---|---|
| M2M100 のトークナイザー | `M2M100Tokenizer`（sentencepiece 0.2.1 + `vocab.json`）と同じ ID 列になるか。NLLB もコーパスを広げる | 自前の処理を足す | **済**（2026-10-11）。sentencepiece は `sentencepiece-sys` 0.14（0.2.1 を同梱）、`M2M100Tokenizer` の分割・ID 化・追加トークンの扱いを移植。M2M100 418M で分割 414・翻訳 170・復号 570 件が一致 |
| transformers の `decode` | 空白の掃除などの既定の処理が、文のコーパスで一致するか | 自前の処理を足す | **済**。NLLB は tokenizers を Python と同じ 0.19.1 に固定し、`clean_up_tokenization` を足す。M2M100 は遅いトークナイザーの `_decode`（言語トークンを空白でつなぐ扱いを含む）を移植。語彙からの乱択 400 件を含めて一致 |
| LLM の要求 | langchain が付ける既定値を含め、各社の要求の本文が一致するか | 既定値を写す | **済**（P2）。o 系のモデルの system を `developer` にする規則、o1 の温度 1.0 も写した |
| stderr の付け替え | `freopen` が各 DLL の出力に効くか | 別の方法で止める | **済**（P0） |
| 重みのフォルダ | Hugging Face から取ったときのフォルダ構成と `.weight_verified.json` を再現できるか | 既存の重みを読む移行処理を足す | **読む側は済**。CTranslate2 の重みは `weights/ctranslate2/<dir>/`、トークナイザーは HF のキャッシュの形（`<dir>/tokenizer/models--org--name/snapshots/<refs/main>/`）。Rust はこの形を読む（`vrct-backend::hf_cache`）。**書く側も済**（P2、`vrct-backend::weights`） |
| ort | 2.0 が rc のまま | 版を固定し、安定版が出たら上げる | `=2.0.0-rc.13` に固定 |

### Python の挙動のうち、そのまま写したもの（直すかは P4 以降で決める）

| 箇所 | 挙動 |
|---|---|
| テレメトリー | 送る時刻は現地時刻に「Z」を付けたもの（aptabase 0.1.0 の `datetime.now().isoformat() + "Z"`）。UTC との差の分ずれて記録される |
| テレメトリー | 起動時に無効で、あとから有効にしても（`init` を 2 回目に呼ぶ）何も送られない。エラーは「送った」と記録だけされる |
| WebSocket | 待ち受けに失敗しても `checkWebSocketServerAlive` は true を返す（`model.py`）。**P4 で決定**: Rust は起動に失敗したら止まっている扱い（記録を残す）。設定（`WEBSOCKET_SERVER`）は Python と同じく ON のまま |

### P4 で Python から変えた点（ユーザーの判断を含む）

| 箇所 | 変えた点 |
|---|---|
| OSCQuery | vrchat_osc の説明どおり `VRChatOSC::new(None)`（ループバック以外で告知）。127.0.0.1 を渡すとループバックでしか告知されず、VRChat（mDNS をループバックで受けない）に見つからない。MuteSelf の問い合わせは受信の開始から 1 秒待つ（Python の OSCQueryBrowser の最初の sleep(1) と同じ理由） |
| ミュート同期 | ミュートした瞬間から、切り出し途中の発話・待ち行列・まとめ途中の音声を捨て、処理中だった結果も出さない。入力は読み続けて音量メーターは動かす（ユーザー要望。Python は区切りで止まり、解除後に溜まった音声を文字起こししていた） |
| Whisper（この PC）の送り方 | Google と同じく、区切りが届くたびに伸びていく音声を文字起こしして出す（VRCT 3.5.1 の動き、ユーザー判断）。develop の Python は発話の確定（無音 phrase_timeout 秒など）を待ってから 1 回だけ送るので、話し終わりから表示まで 3 秒余計にかかっていた。溜まったときは 1 回にまとめる仕組みはそのまま。有料の API（Groq / OpenAI / Custom / Deepgram）は確定してから 1 回 |
| 録音デバイスが開けないとき | マイク・スピーカーとも既定のデバイスへ選択を付け替えて UI に知らせる（ユーザー判断）。Python はスピーカーでも既定のマイクを録音していた |
| 未知のエンドポイント | 404 / 423 の result は Python と同じ null（最初の実装は文字列を返していた） |
| 互換処理 | v3.6.x で要るものだけ（§10）: AUTH_KEYS などの欠けたキーの補完、MME などから WASAPI へのデバイス名の移行、Python が書いた重みの印とトークナイザーのキャッシュ、`installer_language.txt`。重みフォルダの旧名からの改名は持ち込まない |
| 重み | Python の huggingface_hub は、PC に保存された Hugging Face のトークンを公開リポジトリへの要求にも付けていた。Rust 版は付けない |

## 12. 付録

- 付録 A: `rust_backend_design_appendix_endpoints.md`（要求 330 件・push 81 件、領域別、初期化中に受け付けるか、Python のハンドラ名）
- PoC: `native/poc-ct2dll`（CTranslate2 の受け口）、`native/poc-ct2`（メル特徴量、ct2rs での試行）、`native/poc-ort`（VAD・YOLOX・OCR）、`native/poc-oscquery`（OSCQuery）
