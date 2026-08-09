# ocr - VRChatチャット吹き出し OCR パイプライン

## 概要

VRChatの画面上に浮かぶチャット吹き出し（他プレイヤーのテキストチャット）を光学文字認識で読み取り、既存の翻訳パイプラインに流し込むためのモジュール群です。音声はマイク／スピーカーで文字起こしされていましたが、**画面に描画される他人のチャットは翻訳できない** という穴を埋めるための実装です。

出力先はメインメッセージログと SteamVR オーバーレイの2系統。VRChatの OSC チャットボックス（`/chatbox/input`）へは**送信しません**（他人の発言を自分のチャットボックスに垂れ流すのはユーザー体験・コミュニティ規範の両面で不適切なため、初版で明示的に封印）。

## 主要コンポーネント

`src-python/models/ocr/` 配下に配置されており、既存の `models/transcription/` の構造（recorder → transcriber → pipeline）を踏襲しています。

### ocr_capture_hwnd.py — HWND ウィンドウキャプチャ
- `mss` で "VRChat" ウィンドウのクライアント領域を BGR ndarray として取得
- ウィンドウ検索は `models/clipboard/clipboard.py` の `find_windows_by_title_substring` と同型
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

### ocr_bubble_detector.py — 吹き出し候補 ROI 抽出
- OpenCV で画面から吹き出しらしい矩形を絞り込む前処理
- 手順: グレースケール → GaussianBlur → adaptiveThreshold → morphologyClose → findContours
- フィルタ: 面積比 / アスペクト比 / 画面端マージン / 下部 HUD 除外
- OCR は候補矩形の crop に対してのみ走らせるので、画面全体走査に比べ大幅に効率的かつ誤検出（名札・ワールドサインなど）を減らせる

### ocr_engine_easyocr.py — EasyOCR ラッパー
- `easyocr.Reader` を `(langs, gpu)` キーの遅延シングルトンで管理
- GPU 初期化失敗時（CUDA なし・VRAM 圧迫）は自動的に CPU にフォールバック
- 戻り値は `[{"text": str, "confidence": float}]` に正規化

### ocr_languages.py — 言語コード変換
- VRCT の言語名（"Japanese" 等）を EasyOCR のコード（"ja" 等）にマップ
- `"auto"` は JP + EN の 2 言語リーダーをロード（VRChat での実用範囲をカバー）

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
│  (HWND / OpenVR)  │──BGR──►│ (OpenCV ROI 抽出)│
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

VRChat の吹き出しは 7 秒前後画面に残るため、tick 毎に再翻訳しないよう抑制する必要があります。

- テキストを `casefold()` → `blake2b` 8 バイトハッシュ化
- LRU に `(last_seen_monotonic, bbox_center)` を記録
- 同一ハッシュがクールダウン期間内（既定 8 秒）に再出現したらスキップ
- 30 秒経過した項目は evict

## 設定キー

`src-python/config.py` に `ManagedProperty` として追加されています。

| キー | 型 | 既定値 | 説明 |
|---|---|---|---|
| `ENABLE_OCR_CAPTURE` | bool | False | OCR パイプラインの有効化（serialize=False, 起動毎にオフ） |
| `OCR_ENGINE` | str | "EasyOCR" | 使用エンジン（将来の切替のため） |
| `OCR_SOURCE_LANGUAGE` | str | "auto" | ソース言語（"auto" = JP+EN） |
| `OCR_TARGET_LANGUAGE` | str | "auto" | ターゲット言語（既存翻訳設定に追従） |
| `OCR_POLL_INTERVAL_MS` | int | 750 | キャプチャ間隔（100〜5000 でクランプ） |
| `OCR_MIN_CONFIDENCE` | float | 0.55 | OCR 信頼度の下限（0.1〜0.99） |
| `OCR_USE_GPU` | bool | True | GPU 使用（失敗時 CPU 自動フォールバック） |
| `OCR_BUBBLE_MIN_TEXT_LENGTH` | int | 2 | 最小テキスト長（1〜50） |
| `OCR_DEDUP_COOLDOWN_SEC` | int | 8 | 重複抑制クールダウン秒数（1〜120） |

## エンドポイント

`mainloop.py` に登録済み。Frontend からは `useOcr()` フック経由で自動的に叩かれます。

- `/set/enable/ocr_capture`, `/set/disable/ocr_capture` — 開始・停止
- `/get/data/ocr_*`, `/set/data/ocr_*` — 各設定キー
- `/run/transcription_ocr_message` — OCR 結果を UI ログに配送（`useReceiveRoutes.js`）

## Controller 連携

- `Controller.startOcrCapture()` / `stopOcrCapture()` — スレッド起動・停止
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

- **明るい背景に重なった吹き出し**は輪郭が壊れて取りこぼす可能性あり。`OCR_MIN_CONFIDENCE` を下げるか、将来的には detector を学習ベースに置き換える計画
- **ワールドサインや看板テキスト**を吹き出しと誤検出することがある。位置フィルタ（画面端・下部 HUD 除外）で軽減済みだが完全には防げない
- **EasyOCR 初回モデル DL**（`~/.EasyOCR/`）中はしばらく無反応に見える。UI 側の進捗表示は未実装（今後の改善候補）
- **VRChat Desktop モード起動 + SteamVR も起動中** というレアケースでは、OpenVR ミラー側に VRChat の映像が来ないため OCR 対象なしになる（誤翻訳より無害）
