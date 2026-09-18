# ocr - VRChatチャット吹き出し OCR パイプライン

## 概要

VRChatの画面上に浮かぶチャット吹き出し（他プレイヤーのテキストチャット）を光学文字認識で読み取り、既存の翻訳パイプラインに流し込むためのモジュール群です。音声はマイク／スピーカーで文字起こしされていましたが、**画面に描画される他人のチャットは翻訳できない** という穴を埋めるための実装です。

出力先はメインメッセージログと SteamVR オーバーレイの2系統。VRChatの OSC チャットボックス（`/chatbox/input`）へは**送信しません**（他人の発言を自分のチャットボックスに垂れ流すのはユーザー体験・コミュニティ規範の両面で不適切なため、初版で明示的に封印）。

## 主要コンポーネント

`src-python/models/ocr/` 配下に配置されており、既存の `models/transcription/` の構造（recorder → transcriber → pipeline）を踏襲しています。

### ocr_capture_hwnd.py — HWND ウィンドウキャプチャ
- Win32 API (`ctypes`、`user32.PrintWindow`/`PW_RENDERFULLCONTENT`) で対象ウィンドウの
  クライアント領域を直接レンダリングし BGR ndarray として取得。`mss` 等の画面座標
  グラブは使っていない — VRCT自身が画面上でVRChatウィンドウに重なっている場合、
  座標ベースのグラブだと最前面(=VRCT側)を誤って撮ってしまうため、ウィンドウ自身の
  サーフェスから直接描画させる `PrintWindow` を採用している
- 対象ウィンドウはタイトルの部分一致(大文字小文字を区別しない)で検索する。既定は
  "VRChat" だが `config.OCR_WINDOW_TITLE` で変更可能(改造版ランチャー等で
  ウィンドウタイトルが異なるクライアントに対応するため)
- 最小化時（`IsIconic`）や空フレームは None を返してスキップ

### ocr_capture_openvr.py — OpenVR ミラーテクスチャキャプチャ
- `IVRCompositor::GetMirrorTextureGL(Eye_Left)` で HMD 左目の submitted 画像を取得
- PyOpenGL + GLFW（非表示ウィンドウ）で GL コンテキストを作成し `glGetTexImage` で読み出し
- OpenVR は既存 `models/overlay/overlay.py` と同じく `openvr` パッケージを使用

### ocr_capture.py — バックエンド選択ファサード
- SteamVR 起動状態を 5 秒間隔でリチェックし、backend を自動切り替え
  - **SteamVR 起動中** → OpenVR ミラーテクスチャ
  - **SteamVR 非起動** → HWND キャプチャ
- 切り替えの理由: VR プレイヤーは負荷軽減のため VRChat のデスクトップミラーウィンドウを最小化することが多く、その場合 HWND では黒フレームしか取れないため

### ocr_bubble_detector.py — 吹き出し検出（YOLOv8n / ONNX）
- 収集したVRChatのスクリーンショットで学習した検出モデルで、吹き出しの矩形を直接得る
- 推論は onnxruntime のみ（faster-whisper が Silero VAD 用に既に依存しているので追加依存なし）。
  ultralytics も torch も推論には不要。NMS はエクスポート時にグラフへ焼き込んであるので、
  このモジュールがやるのは letterbox と、元画像の画素座標への戻しだけ
- モデルは `src-python/models/ocr/onnx/chatbox_yolov8n.onnx`（約12MB）を同梱。
  `findModelPath()` が凍結時は `_internal/ocr_onnx/`、ソース実行時はパッケージ内を見る。
  最初の `detect()` まで読み込まないので、OCRを使わない起動ではメモリも時間も使わない
- 結果は信頼度の降順。`MAX_CANDIDATES_PER_TICK` で上位数件のみOCRに回す
- 実行時の閾値は `BubbleDetector(confidence=...)`（既定0.15）。val20枚での実測は
  0.15で20/20・余分な候補5、0.25で19/20・余分2、0.5で18/20・余分0。取りこぼしは
  翻訳されない文が出ることを意味するのに対し、余分な候補はOCR側の
  `OCR_MIN_CONFIDENCE` で文字が読めずに落ちるだけなので、取りこぼしを優先している
- 速度は約300ms/枚（CPU、imgsz=1280、RTX 2080 Ti機のCPUでの実測）
- 学習・再学習とモデルの差し替え手順は [docs/ocr_yolo_training.md](../../../docs/ocr_yolo_training.md)

#### 経緯: 色/輪郭ヒューリスティックからの置き換え（2026-09-17）
初版は OpenCV の adaptiveThreshold → 輪郭抽出 → 幾何フィルタ（面積比・アスペクト比・
画面端マージン・下部HUD除外）に、吹き出しパネルの「縁の色ばらつき」フィルタと位置
スコアリングを足した実装だった。VRChatのチャット吹き出しは、ワールド制作者が作る
看板・UIパネルと同じ「ワールド内3D要素」として描画されるため形状だけでは区別できず、
色ばらつきでの判別も実機で反証された（工場ゲームのUIパネル文字を誤検出）。
学習ベースの検出器に置き換えたことでこの一連のヒューリスティックは不要になり、
パラメータ（`collar_width` / `max_collar_std` / `center_bias_weight` 等）も含めて削除済み。

### ocr_engine_rapidocr.py — OCRエンジン (RapidOCR / ONNX PP-OCR)
- モデル指定ごとに推論器を遅延生成してキャッシュする。`readtext_bgr(crop)` は
  `[{"text", "confidence"}, ...]` を返し、例外は投げない (失敗時は空リスト)
- **onnxruntimeのみで動く**。faster-whisper が Silero VAD 用に既に依存しているので、
  実行時依存は増えない。PaddlePaddle も torch も要らない
- `Det.limit_side_len=320`。RapidOCRの既定は短辺を736pxまで**拡大**する設定
  (`limit_type="min"`) で、吹き出しの切り出しは小さい(短辺100px前後のこともある)ため
  7倍に引き伸ばされ1枚2秒近くかかっていた。320で実測1778ms→790msになり精度は落ちなかった

#### 経緯: EasyOCRからの置き換え (2026-09-18)
学習用データセットの吹き出し95枚をCPUで読み比べた結果。CERは低いほど良い。

| エンジン | CER | ほぼ正解(CER≤0.2) | 中央値 |
|---|---|---|---|
| EasyOCR (ja+en) | 0.69 | 34% | 643 ms/枚 |
| **PP-OCRv6 small** | **0.27** | **66%** | 790 ms/枚 |
| PP-OCRv5 ch | 0.62 | 54% | 918 ms/枚 |

速度はEasyOCRと同程度(中央値はむしろEasyOCRが速い)で、**速くなったから替えたのではない**。
決め手は精度と依存の重さ。EasyOCRは縦書き(あいうえお/かきくけ)を全く読めず、句読点が落ち、
単語間のスペースが潰れていた。またEasyOCRはtorchを必須依存に持ち、torch(1.2GB)・
scipy(119MB)・scikit-image(30MB)を配布物へ連れてきていた。

### ocr_languages.py — 設定値からモデルを決める
- PP-OCRv6 small は1モデルに**日本語・英語・中国語(簡繁)＋ラテン文字系40言語**が入るので、
  この範囲は `auto` のまま言語を選ばせずに読める
- ハングル・キリル文字・タイ文字・アラビア文字・デーヴァナーガリーは v6 small に含まれず、
  PP-OCRv5 のスクリプト別モデルへ切り替える。選択肢はこの5系統 (6言語) と `auto` だけ
- 旧バージョンが保存した言語名 (Japanese / English など) は auto と同じモデルへ解決する
- 未対応の値は None を返し、呼び出し側が起動を拒否する。黙って別モデルへ
  フォールバックしない

| 設定値 | 使うモデル |
|---|---|
| `auto` (既定) と日英中・ラテン系の言語名 | PP-OCRv6 small |
| Korean | PP-OCRv5 mobile / korean |
| Russian, Ukrainian | PP-OCRv5 mobile / cyrillic |
| Thai | PP-OCRv5 mobile / th |
| Arabic | PP-OCRv5 mobile / arabic (精度は低め) |
| Hindi | PP-OCRv5 mobile / devanagari |

モデルは配布物へ同梱する (計78MB)。実行時にネットワークへ出ないよう、ビルド前に
`tools/fetch_ocr_models.py` で rapidocr パッケージ内へ取得し、spec の datas でまとめて含める。

### ocr_pipeline.py — オーケストレーター
- 独立スレッドで poll ループを回し、capture → detect → OCR → dedup → callback
- コールバックのペイロードはマイク／スピーカーの transcript 結果と同じ形状で、`Controller.ocrMessage` から既存の翻訳・オーバーレイ経路に載せられる

## クラス構造

### OcrPipeline クラス (ocr_pipeline.py)

```python
class OcrPipeline:
    def __init__(
        self,
        callback: Callable[[dict], None],
        source_language: str = "auto",
        poll_interval_ms: int = 750,
        min_confidence: float = 0.55,
        use_gpu: bool = True,
        min_text_length: int = 2,
        dedup_cooldown_sec: int = 8,
    ) -> None:
        self._callback = callback
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._capture: Optional[OcrCapture] = None
        self._detector = BubbleDetector()
        self._dedup = _DedupCache()
        self._reader = None
```

### OcrCapture クラス (ocr_capture.py)

```python
class OcrCapture:
    BACKEND_HWND = "hwnd"
    BACKEND_OPENVR = "openvr_mirror"
    BACKEND_NONE = "none"

    def __init__(self) -> None:
        self._hwnd = HwndCapture()
        self._openvr: Optional[OpenVRMirrorCapture] = None
        self._backend = self.BACKEND_NONE
```

## 処理フロー

```
┌───────────────────┐        ┌──────────────────┐
│  OcrCapture       │        │ BubbleDetector   │
│  (HWND / OpenVR)  │──BGR──►│ (YOLOv8n / ONNX) │
└───────────────────┘        └────────┬─────────┘
                                      │ [(bbox, crop), ...]
                                      ▼
                             ┌──────────────────┐
                             │ RapidOCR (ONNX)  │
                             │ (crop→words+conf)│
                             └────────┬─────────┘
                                      │ merged text
                                      ▼
                             ┌──────────────────┐
                             │ _DedupCache      │  ← text_hash + cooldown
                             │ (LRU)            │
                             └────────┬─────────┘
                                      │ unique text
                                      ▼
                             ┌──────────────────┐
                             │ callback         │
                             │ (Controller.     │
                             │  ocrMessage)     │
                             └────────┬─────────┘
                                      │
                                      ▼
                          既存 Translator → UI ログ + Overlay
                                     （OSC には送らない）
```

## 重複抑制（dedup）

**覚えている間は同じ文を配送しない。** 時間で解禁する方式ではない。

- 配送した文を `_DedupCache` (最大128件) に持ち、見るたびに「最後に見た時刻」を更新する
- 保持時間は画面から**消えてから**測る。`OCR_DEDUP_COOLDOWN_SEC` 秒あいだ現れなければ忘れ、
  以降に同じ文が出たら新しい発言として配送する
- 保持時間の下限は **tick間隔の2倍**。1tickはOCR1件あたり約0.8秒かかるので、設定値の方が
  短いと出続けている吹き出しでも見るたびに忘れられ、同じ文が繰り返し配送される
  (実機で 1秒設定 / tick 1〜2.6秒のときに再現、2026-09-18)
- 編集距離2以内の文は同じものとして扱う。OCRのゆらぎで1〜2文字違うだけの同じ吹き出しを
  別物として配送しないため

## 1 tick あたりの処理量制限

混雑したワールドや文字の多い UI では候補矩形が数十件になることがあり、全件 OCR するとループが数秒止まって Whisper と GPU を奪い合います。そのため:

- `MAX_CANDIDATES_PER_TICK`（既定 6）で件数を制限（detector が面積降順に並べているので大きい吹き出しが優先されます）
- `TICK_OCR_BUDGET_RATIO`（既定 0.8）× poll interval を時間予算とし、超過した時点でその tick を打ち切り

## OpenVR セッションの共有について

OpenVR の初期化は**プロセス単位**で、`models/overlay/overlay.py` が既に `openvr.init()` したセッションを保持しています。そのため本モジュールは:

- `openvr.init()` は呼ぶ（既存セッションに合流する形になる）
- **`openvr.shutdown()` は決して呼ばない** — 呼ぶと VR オーバーレイのセッションまで巻き添えで破棄されるため
- ミラーテクスチャは**初回に 1 度だけ取得**し、以降フレーム毎に `lockGLSharedTextureForAccess` / `unlockGLSharedTextureForAccess` で囲んで読み出し
- 失敗時はテクスチャのみ解放して `_initialized` を落とし、次 tick で再取得（SteamVR 再起動やオーバーレイ側 shutdown からの自動復帰）

## 設定の反映タイミング

OCR系の設定は**実行中でも次のtickから反映される**。`Controller` の各setterが
`model.updateOCRCaptureSettings()` を呼び、`OcrPipeline.applyConfig()` が値を預かって、
ワーカースレッドが次のtickの頭で `_applyPending()` で取り込む。

| 設定 | 反映のされ方 |
|---|---|
| `OCR_SOURCE_LANGUAGE` | 使うモデルが変わる場合だけ推論器を作り直す (キャッシュ済みなら即座)。重複抑制のキャッシュも捨てる |
| `OCR_WINDOW_TITLE` | キャプチャを開き直す |
| `OCR_POLL_INTERVAL_MS` / `OCR_MIN_CONFIDENCE` / `OCR_BUBBLE_MIN_TEXT_LENGTH` / `OCR_DEDUP_COOLDOWN_SEC` | 値を差し替えるだけ |

ReaderとキャプチャはOSリソース・スレッドに紐づくので、値を書き換えたスレッドではなく
**使っているワーカースレッドの側で**作り直す。これが `applyConfig` が値を預かるだけで、
実際の切り替えを `_applyPending()` に任せている理由。

## 設定キー

`src-python/config.py` に `ManagedProperty` として追加されています。

| キー | 型 | 既定値 | 説明 |
|---|---|---|---|
| `ENABLE_OCR_CAPTURE` | bool | False | OCR パイプラインの有効化（serialize=False, 起動毎にオフ） |
| `OCR_SOURCE_LANGUAGE` | str | "auto" | 読み取る言語。`auto` は日英中＋ラテン文字系を1モデルで読む。別モデルが要る文字体系のみ明示選択する（選択肢は `ocr_languages.SELECTABLE_LANGUAGES`） |
| `OCR_WINDOW_TITLE` | str | "VRChat" | キャプチャ対象ウィンドウのタイトル部分一致文字列（大文字小文字を区別しない） |
| `OCR_POLL_INTERVAL_MS` | int | 750 | キャプチャ間隔（100〜5000 でクランプ） |
| `OCR_MIN_CONFIDENCE` | float | 0.85 | OCR 信頼度の下限（0.1〜0.99）。PP-OCRは誤読時もスコアが高く、実測では 0.55 で誤りを1件も落とせず、0.85 なら正解を失わずに誤りの34%を落とせた |
| `OCR_BUBBLE_MIN_TEXT_LENGTH` | int | 2 | 最小テキスト長（1〜50） |
| `OCR_DEDUP_COOLDOWN_SEC` | int | 30 | 配送済みの文を覚えておく秒数（1〜120）。覚えている間は同じ文を配送しない |

## エンドポイント

`mainloop.py` に登録済み。Frontend からは `useOcr()` フック経由で自動的に叩かれます。

- `/set/enable/ocr_capture`, `/set/disable/ocr_capture` — 開始・停止
- `/get/data/ocr_*`, `/set/data/ocr_*` — 各設定キー（setterは実行中のパイプラインへ即時反映する）
  - エンジンを選ぶ設定は持たない。実装が1つしか無いのに保存値と判定値がずれてOCRが起動しなくなる事故を起こしたため (2026-09-18)
- `/get/data/selectable_ocr_source_languages` — OCRで選べる言語の一覧（UIのドロップダウンの中身）
- `/run/transcription_ocr_message` — OCR 結果を UI ログに配送（`useReceiveRoutes.js`）

## Controller 連携

- `Controller.startOcrCapture()` / `stopOcrCapture()` — スレッド起動・停止
- `model.updateOCRCaptureSettings()` — 設定変更を実行中のパイプラインへ渡す（各setterから呼ばれる）
- `Controller.ocrMessage(result)` — OCR 結果を翻訳し UI ログ + Overlay に配送
  - `micMessage` / `speakerMessage` と同じ VRAM エラー・word filter 分岐
  - **OSC 送信は行わない**（コード内コメントで明示）

## UI

- サイドバー: `config_page/sidebar_section/SidebarSection.jsx` に "OCR" タブ追加
- 設定画面: `config_page/setting_section/setting_box/ocr/Ocr.jsx`
  - 有効化トグル、ソース言語入力、GPU トグル、poll interval / min confidence / min text length / dedup cooldown スライダー

## 動作確認手順

Windows + VRCT ビルド前提。詳細は「VR モードでのデスクトップミラー最小化」ケースを含めて検証してください。

1. `pip install -r requirements.txt` で依存を追加インストール
2. VRCT 起動 → 設定画面 → OCR タブ
3. Desktop モード：VRChat 起動 → 他プレイヤーがチャットを打つワールドに入る → OCR 有効化 → ログに翻訳が並ぶこと
4. VR モード（通常）：SteamVR 起動 → VRChat VR モード → OCR 有効化 → メインログとオーバーレイに翻訳が出ること
5. VR モード（最小化）：上記状態でデスクトップミラーウィンドウを最小化 → 翻訳が継続すること（backend が `openvr_mirror` に切り替わっている）
6. VRChat のチャットボックスに OCR 翻訳が**流れていないこと**を確認

## 既知の制約

- **学習データが1ワールド・1セッションの100枚**しかない。別のワールドや距離・
  明るさが大きく違う場面では取りこぼしや誤検出が出る可能性が高い。取りこぼすなら
  `BubbleDetector(confidence=...)` を下げ、その場面の画像を集めて再学習する
- **ワールド由来のテキスト**（看板・ワールド内の案内文）は検出対象外として学習している。
  アバターのチャット吹き出し（角丸の暗いパネル＋しっぽ）だけを拾う
- **VRChat Desktop モード起動 + SteamVR も起動中** というレアケースでは、OpenVR ミラー側に VRChat の映像が来ないため OCR 対象なしになる（誤翻訳より無害）
- **設定変更は次回 OCR 開始時に反映**されます（`OCR_SOURCE_LANGUAGE` 等はパイプライン起動時に読み込まれるため、実行中の変更を反映するには一度 OFF→ON が必要）
- **GLFW の初期化を OCR スレッドから行っている**点は Windows では実用上問題ありませんが、GLFW の公式なスレッド要件（多くの API はメインスレッド呼び出しを想定）からは外れています。将来的にキャプチャ用 GL コンテキストを専用スレッドに集約する余地があります
