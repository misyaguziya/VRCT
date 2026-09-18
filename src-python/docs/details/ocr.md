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
  翻訳されない文が出ることを意味するのに対し、余分な候補は EasyOCR 側の
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

### ocr_engine_easyocr.py — EasyOCR ラッパー
- `easyocr.Reader` を `(langs, gpu)` キーの遅延シングルトンで管理
- GPU 初期化失敗時（CUDA なし・VRAM 圧迫）は自動的に CPU にフォールバック
- 戻り値は `[{"text": str, "confidence": float}]` に正規化

### ocr_languages.py — 言語コード変換

- VRCTの言語名 <-> EasyOCRの言語コードの対応表。`SUPPORTED_LANGUAGES` がUIの選択肢になる
- **autoは無い**。EasyOCRのReaderは1つのスクリプトグループしか同時にロードできず
  (ja / ko / ch_sim / ch_tra / th / ta / te / kn はそれぞれ英語としか併用できない)、
  「全言語を自動で読む」が原理的に作れないため、読み取る言語は明示選択のみにしている
- 英語以外を選ぶと `[その言語, 'en']` を読み込む。吹き出しにラテン文字が混ざるため
- 未対応・未選択は空リストを返し、呼び出し側が起動を拒否する。黙って英語へ
  フォールバックしていた頃、日本語の吹き出しが英語モデルで読まれてローマ字のような
  文字列になる不具合が実機で出た (2026-09-18)

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
                             │ EasyOCR Reader   │
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

VRChat の吹き出しは数秒〜数十秒画面に残るため、tick 毎に再翻訳しないよう抑制する必要があります。

- テキストを `casefold()` → `blake2b` 8 バイトハッシュ化
- LRU に `(last_seen_monotonic, text, bbox_center)` を記録
- **クールダウンは「最後に画面で見かけた時刻」から計測**します。吹き出しを見かけるたびにタイムスタンプを更新するため、長く残り続ける吹き出しはクールダウン秒数ごとに再送されるのではなく、**消えてからクールダウン経過後に初めて再送対象**に戻ります
- OCR のブレ（1〜2 文字の誤認識）で別ハッシュになるケースに備え、既存エントリとの**編集距離 2 以内**を近似重複として同一視します（`_similar()`、追加依存なしの打ち切り付き DP）
- 30 秒経過した項目は evict

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
| `OCR_SOURCE_LANGUAGE` / `OCR_USE_GPU` | EasyOCR Readerを作り直す (同じ組み合わせはキャッシュ済みなので即座)。重複抑制のキャッシュも捨てる |
| `OCR_WINDOW_TITLE` | キャプチャを開き直す |
| `OCR_POLL_INTERVAL_MS` / `OCR_MIN_CONFIDENCE` / `OCR_BUBBLE_MIN_TEXT_LENGTH` / `OCR_DEDUP_COOLDOWN_SEC` | 値を差し替えるだけ |
| `OCR_ENGINE` | 起動時のみ (EasyOCR以外は未対応) |

ReaderとキャプチャはOSリソース・スレッドに紐づくので、値を書き換えたスレッドではなく
**使っているワーカースレッドの側で**作り直す。これが `applyConfig` が値を預かるだけで、
実際の切り替えを `_applyPending()` に任せている理由。

## 設定キー

`src-python/config.py` に `ManagedProperty` として追加されています。

| キー | 型 | 既定値 | 説明 |
|---|---|---|---|
| `ENABLE_OCR_CAPTURE` | bool | False | OCR パイプラインの有効化（serialize=False, 起動毎にオフ） |
| `OCR_ENGINE` | str | "EasyOCR" | 使用エンジン（将来の切替のため） |
| `OCR_SOURCE_LANGUAGE` | str | "" | 読み取る言語（VRCTの言語名）。**明示選択のみ、autoは無い**。"" は未選択で、この状態ではOCRは起動しない。選べるのは `ocr_languages.SUPPORTED_LANGUAGES` に載っている言語だけ |
| `OCR_WINDOW_TITLE` | str | "VRChat" | キャプチャ対象ウィンドウのタイトル部分一致文字列（大文字小文字を区別しない） |
| `OCR_POLL_INTERVAL_MS` | int | 750 | キャプチャ間隔（100〜5000 でクランプ） |
| `OCR_MIN_CONFIDENCE` | float | 0.55 | OCR 信頼度の下限（0.1〜0.99） |
| `OCR_USE_GPU` | bool | True | GPU 使用（失敗時 CPU 自動フォールバック） |
| `OCR_BUBBLE_MIN_TEXT_LENGTH` | int | 2 | 最小テキスト長（1〜50） |
| `OCR_DEDUP_COOLDOWN_SEC` | int | 8 | 重複抑制クールダウン秒数（1〜120） |

## エンドポイント

`mainloop.py` に登録済み。Frontend からは `useOcr()` フック経由で自動的に叩かれます。

- `/set/enable/ocr_capture`, `/set/disable/ocr_capture` — 開始・停止
- `/get/data/ocr_*`, `/set/data/ocr_*` — 各設定キー（setterは実行中のパイプラインへ即時反映する）
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
- **EasyOCR 初回モデル DL**（`~/.EasyOCR/`）中はしばらく無反応に見える。UI 側の進捗表示は未実装（今後の改善候補）
- **VRChat Desktop モード起動 + SteamVR も起動中** というレアケースでは、OpenVR ミラー側に VRChat の映像が来ないため OCR 対象なしになる（誤翻訳より無害）
- **設定変更は次回 OCR 開始時に反映**されます（`OCR_SOURCE_LANGUAGE` 等はパイプライン起動時に読み込まれるため、実行中の変更を反映するには一度 OFF→ON が必要）
- **GLFW の初期化を OCR スレッドから行っている**点は Windows では実用上問題ありませんが、GLFW の公式なスレッド要件（多くの API はメインスレッド呼び出しを想定）からは外れています。将来的にキャプチャ用 GL コンテキストを専用スレッドに集約する余地があります
