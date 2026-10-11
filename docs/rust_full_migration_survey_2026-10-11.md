# バックエンド全面 Rust 化の現状調査（2026-10-11）

目的は速度ではなく、Python バックエンド全体を Rust へ移すこと。この文書は計画の前提となる「現状の地図」と「置換先の候補」をまとめたもの。調査はコードの読み取りと公開情報（crates.io / GitHub / HF）のみで、PoC は未実施。

## 1. 現状の規模と構成

- Python は約 2.96 万行（テスト・重みを除く）。テストは `src-python/test/` に約 117 ファイル。
- Rust 化済み: `native/vrct-audio`（PCM 変換・FLAC・VAD 前処理・エネルギー区間検出、814 行）、`native/vrct-graphics`（VR UI の WGC→D3D11→SteamVR、825 行）、`src-python/translator_engines.pyd`（Google/Bing/Papago の無料 Web 翻訳。**ソースはこのリポジトリに無く、独自ライセンス**）。
- `src-tauri/src/lib.rs`（191 行）にバックエンドのロジックは無い（フォント一覧、zip 取得、VR パネルのウィンドウ管理だけ）。

### UI とバックエンドの境界（IPC）

| 項目 | 現状 |
|---|---|
| 起動 | UI（JS）が Tauri shell プラグインで sidecar exe を spawn。Rust 側は sidecar を管理していない |
| UI→バックエンド | stdin に 1 行 1 JSON `{"endpoint": "/set/data/x", "data": base64(JSON)}` |
| バックエンド→UI | stdout に 1 行 1 JSON `{"status", "endpoint", "result"}`（result は素の JSON） |
| status | 200 成功 / 400 ErrorCode 付き / 348 ログ / 423 初期化中・ロック中（サーバー側で再キュー）/ 404 / 500 |
| エンドポイント | 331 件（`/get/data` 146、`/set/data` 88、`/set/enable`・`/set/disable` 各 33、`/delete/data` 11、`/run/*` 約 20）。push 用の名前が別に約 90 |
| stderr | `Warning:` を含まない行は UI が致命的エラーとして通知する |
| 終了 | `/run/shutdown` の 2 秒後に UI が閉じる。20 秒ごとの watchdog、途絶で 30 秒後に自己終了 |
| VR パネル | 別ウィンドウは sidecar を持たず、main ウィンドウ経由で中継 |

### 機能ブロック

| ブロック | 主なファイル（行数） | 外部依存 |
|---|---|---|
| IPC・ディスパッチ | mainloop（910）、utils の IPC 部分 | 標準ライブラリ |
| 制御・状態 | controller（5380）、model（2780）、config（1507）、errors（893） | psutil, requests, flashtext |
| 録音・デバイス | device_manager（1030）、active_endpoint_tracker（439）、recorder（667）ほか | PyAudioWPatch, pycaw/comtypes |
| VAD | audio_vad（394） | Silero VAD の ONNX（faster-whisper 同梱） |
| 文字起こし | transcriber（672）、providers（348）、whisper（230）、deepgram、google_speech、languages（761） | faster-whisper, ctranslate2, av, pydub, requests |
| 翻訳 | translator（699）、utils、providers、LLM 各社（各 160〜195） | ctranslate2, transformers, langchain-*, deepl, PyYAML, translator_engines.pyd |
| 音訳 | transliterator（229）、kana_to_hepburn（216）、context_rules（134） | SudachiPy + SudachiDict-full |
| OSC/OSCQuery | osc（268） | python-osc, tinyoscquery（zeroconf） |
| VR オーバーレイ | overlay（3517）、overlay_image（732）、window_capture（323）ほか | openvr, Pillow, numpy, cv2, glfw/PyOpenGL（OpenGL 経路） |
| OCR | ocr_pipeline（450）、capture 各種、bubble_detector（225）、engine_rapidocr（126） | rapidocr（onnxruntime, PP-OCR）, opencv |
| WebSocket / OBS | websocket_server（271）、obs_browser_source_server（358） | websockets, http.server |
| その他 | clipboard（320）、telemetry（約 460）、更新・モデル取得（model.py 内） | pyperclip, aptabase, huggingface_hub |

## 2. 置換先の候補（3 分類）

### 既存クレートで置き換えられるもの

| 対象 | 候補 | 確度 |
|---|---|---|
| Whisper 推論本体 | ct2rs 0.10.1（CTranslate2 の Rust バインディング、MIT） | 見込み（Windows+CUDA は未検証） |
| 翻訳（CTranslate2 の M2M100/NLLB） | ct2rs + tokenizers / sentencepiece | 見込み |
| Silero VAD・YOLOX 吹き出し検出 | ort（ONNX Runtime。2.0 は rc.13 で安定版なし） | 確認済み（前後処理は数十行） |
| OCR（PP-OCR） | oar-ocr 0.10 / ppocr-rs 0.7 + ort、clipper2 | 見込み |
| OSC 送受信 | rosc | 確認済み |
| OSCQuery（mDNS） | mdns-sd、vrchat_osc | 見込み（VRChat 実機の検証が必要） |
| WebSocket / OBS 用 HTTP | tokio-tungstenite / axum | 確認済み |
| LLM 各社（langchain は `.invoke` 1 回だけ） | reqwest 直、または async-openai | 確認済み |
| DeepL・HF のファイル取得・テレメトリ | reqwest（deepl / hf-hub / aptabase-rs も有り） | 確認済み |
| psutil・pyperclip・YAML・ログ・bidi・flashtext | sysinfo・arboard・serde・tracing・unicode-bidi・aho-corasick | 確認済み（flashtext は単語境界の差に注意） |
| FLAC 書き出し（pydub / av の用途） | flacenc（既に vrct-audio で使用中） | 確認済み |
| 画面キャプチャ | windows クレート（vrct-graphics で実装済み） | 確認済み |
| 日本語の形態素解析 | sudachi.rs（公式。crates.io には無く git 依存、v0.7 は不安定と明記） | 見込み |

### Rust で自作が必要なもの

| 対象 | 理由 | 規模 |
|---|---|---|
| Whisper のセグメントの `avg_logprob` / `no_speech_prob` と言語検出の整形 | ct2rs の高レベル API に無い。VRCT はこの 2 つで出力を捨てている | 小〜中 |
| M2M100 / NLLB の言語トークン処理とトークナイザ | ct2rs #97（未解決）。M2M100 は `tokenizer.json` が無い | 中 |
| OpenVR オーバーレイ（約 40 API、イベント、コントローラー入力） | 安全な高レベルクレートが無い。`openvr_sys` の上に薄いラッパー | 中〜大 |
| WASAPI 録音（ループバック含む）とデバイス変更通知（COM コールバック） | pycaw / IMMNotificationClient 相当 | 中 |
| かな→ヘボン式・文脈ルール | VRCT 独自のルールの移植 | 小〜中 |
| PP-OCR 後処理の細部（`limit_side_len`、言語別認識モデル） | クレートの設定粒度次第 | 小〜中 |
| VRChat 向けの mDNS の癖への対処 | 既存クレートが対応しているか不明 | 小〜中 |
| IPC・設定・エラー・331 エンドポイントの本体 | アプリ固有のロジック | 大（全体の中心） |

### Python に残さざるを得ないもの

確認できた範囲では無い。条件付きで次の 2 点に注意する。

- **CTranslate2 を Windows + CUDA で使えるか**: ct2rs は Windows を「十分にテストされていない」としている。ビルドや配布が通らない場合でも、Python に戻すのではなく、C++ の CTranslate2 を直接 FFI で呼ぶ選択肢がある。
- **`translator_engines.pyd`**: 中身は Rust 製だが、このリポジトリにはソースが無く、PyO3 の拡張としてしか使えない。Rust のバックエンドから使うには、元のソース（Rust のクレートとして）が必要。

## 3. 移行の前に判断が必要なこと

1. **バックエンドの置き場所**: Rust の sidecar にして今の IPC 契約を保つ（UI は無変更）か、Tauri の本体に組み込んで `invoke` / `emit` にする（UI の通信部分を書き換える）か。
2. **移行のしかた**: 今のように Python を土台にしたまま部品を Rust にしていき最後に土台を差し替えるか、Rust の sidecar を新しく立てて機能ごとに移すか。
3. **translator_engines のソース**の入手。
4. **PoC を先に行う 3 点**: ct2rs（Windows+CUDA、Whisper のスコア、NLLB/M2M100、終了時のハング #64）、ort（Silero VAD・YOLOX・PP-OCR を 1 プロセスで、CPU/CUDA/DirectML の配布）、VRChat 実機での OSCQuery（mdns-sd / vrchat_osc）。
5. **テストの移し方**: 117 ファイルの Python テストのうち、IPC の入出力で書けるもの（エンドポイント契約）は、Rust の sidecar にもそのまま当てられる。言語に依存しない契約テストに寄せると移行の安全網になる。

## 出典（主なもの）

- ct2rs: https://github.com/jkawamoto/ctranslate2-rs （issue #97, #64, #138）、https://docs.rs/ct2rs/latest/ct2rs/
- ort: https://crates.io/crates/ort
- oar-ocr: https://github.com/GreatV/oar-ocr
- vrchat_osc: https://github.com/minetake01/vrchat_osc 、mdns-sd: https://crates.io/crates/mdns-sd
- sudachi.rs: https://github.com/WorksApplications/sudachi.rs
- ovr_overlay（README のオーバーレイ対応状況）: https://github.com/TheButlah/ovr_overlay
- HF tokenizer: https://huggingface.co/facebook/m2m100_418M 、https://huggingface.co/facebook/nllb-200-distilled-600M

## 4. 決定事項（2026-10-11、ユーザー）

- **translator_engines のソース**は `D:\WORKSPACE\WORK\VRChatProject\translator_engines`（別リポジトリ、約 1900 行の Rust、独自ライセンス「VRCT の部品としてのみ使用可」）。Google/Bing/Papago の本体（`google.rs` ほか、reqwest blocking）は素の Rust で、PyO3 に依存するのは `lib.rs` の入口 5 関数だけ。今は `crate-type = ["cdylib"]` のみなので、Rust のバックエンドから使うには `rlib` の追加と PyO3 部分の feature 分離、Rust 向けの公開関数が必要（別リポジトリのため、変更は相談してから）。
- **置き場所は A: Rust の sidecar**。今の IPC 契約（stdin/stdout の 1 行 JSON、base64 の data、status、エンドポイント名）を保ち、UI は変更しない。
