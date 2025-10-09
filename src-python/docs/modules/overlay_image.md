# overlay_image.py — 画像生成ユーティリティ
目的: `models.overlay.overlay_image.OverlayImage` の実装に基づき、オーバーレイ用のテキストボックス／ログ画像を PIL (Pillow) で生成するための仕様書です。

このドキュメントは実装に合わせて書かれており、主要な公開メソッドの振る舞い、引数、返り値、例外、使用例、注意点を含みます。

概要
------
- 提供クラス: `OverlayImage`
- 役割: 文字列（元文／翻訳）やメッセージタイプ(send/receive) を受け取り、Small/Large 向けの RGBA PIL.Image を生成する。
- 依存: Pillow (PIL)、フォントファイル群（`fonts/` ディレクトリまたは環境配下）

主要機能
--------
- テキストをラップして画像化する（行折り返しを含む）
- 複数テキストブロック（原文＋複数の翻訳）を縦に連結して一つの画像にする
- 背景（角丸矩形）を合成して最終的な RGBA 画像を返す
- Small と Large で UI 設定（幅、高さ、フォントサイズ等）を切り替え
- フォント探索: 実行環境の `fonts/` 配下または相対パスからフォントを探し、見つからない場合は FileNotFoundError を投げる

公開 API（要約）
-----------------
- class OverlayImage(root_path: str | None = None)
	- コンストラクタ引数
		- root_path: フォント等のリソースのベースディレクトリ。None の場合は実装に合わせて repo の `fonts/` を候補パスとして探索する。

- OverlayImage.createOverlayImageSmallLog(message: str, your_language: str, translation: list | None = None, target_language: list | None = None) -> PIL.Image.Image
	- 説明: Small ログ向け（横長・1行〜複数行）にテキストブロックを作成して結合し、角丸背景と合成して RGBA 画像を返す。
	- 引数
		- message: 表示する原文テキスト（None を許容しない想定）
		- your_language: 原文の言語キー（フォントマッピングに使用）
		- translation: 翻訳テキストのリスト（省略可）
		- target_language: 翻訳それぞれに対応する言語キーのリスト（省略可）
	- 戻り値: PIL.Image.Image (RGBA)
	- 例外: フォントが見つからない場合は FileNotFoundError を投げる可能性あり

- OverlayImage.createOverlayImageLargeLog(message_type: str, message: str | None = None, your_language: str | None = None, translation: list | None = None, target_language: list | None = None) -> PIL.Image.Image
	- 説明: Large ログ（複数行 + ヘッダ（Send/Receive）や時刻）向けに、複数ブロックを作成して縦結合し、背景を合成して返す。
	- 引数
		- message_type: 'send' または 'receive'（UI 向けアンカー／色指定に使用）
		- message: 表示する原文テキスト（None 可。この場合翻訳のみを表示することもある）
		- your_language: 原文の言語キー（フォント選定に使用）
		- translation: 翻訳テキストのリスト（省略可）
		- target_language: 翻訳それぞれに対応する言語キーのリスト（省略可）
	- 戻り値: PIL.Image.Image (RGBA)
	- 例外: フォント未発見などで FileNotFoundError を投げる可能性あり

内部で使われる補助メソッド（要旨）
---------------------------------
- concatenateImagesVertically(img1, img2, margin=0) -> Image
- addImageMargin(image, top, right, bottom, left, color) -> Image
- createTextboxSmallLog(...) -> Image
- createTextImageLargeLog(...) -> Image
- createTextboxLargeLog(...) -> Image
- getUiSizeSmallLog(), getUiColorSmallLog(), getUiSizeLargeLog(), getUiColorLargeLog()

フォントとローカライズ
-----------------------
- 実装は `LANGUAGES` マッピングを持ち、言語キーからフォントファイル名を決定します（例: "Japanese" -> "NotoSansJP-Regular.ttf"）。
- フォントは `root_path` を基準に探索します。実行環境によりフォントファイルの場所が異なるため、実装は複数パスを順に試します。フォントが見つからない場合は FileNotFoundError を発生させる設計です。

描画と折り返しロジック（実装に基づく注意点）
--------------------------------------------
- テキスト幅を計算し、基準幅に収まるように文字数ベースで分割して折り返す単純なロジックを採用しています。厳密な単語単位折り返しではなく、文字数ベースの分割になります。
- Small/Large でフォントサイズや余白、角丸半径などを分けており、複数行のテキストブロックを縦結合することで最終画像を作ります。

使用例
------
Small ログ画像を作る例:

```python
from models.overlay.overlay_image import OverlayImage

overlay = OverlayImage()
img = overlay.createOverlayImageSmallLog(
		message='こんにちは、世界！',
		your_language='Japanese',
		translation=['Hello, world!'],
		target_language=['English']
)
img.save('overlay_small.png')
```

Large ログ（複数メッセージ履歴）を作る例:

```python
from models.overlay.overlay_image import OverlayImage
from datetime import datetime

overlay = OverlayImage()
img = overlay.createOverlayImageLargeLog(
		message_type='send',
		message='Hello from VRCT',
		your_language='English',
		translation=['こんにちは'],
		target_language=['Japanese']
)
img.save('overlay_large.png')
```

実装上の注意と推奨事項
-----------------------
- 実行環境にフォントが存在することを確認してください（`fonts/` に主要フォントを置くのが簡単です）。
- Pillow (PIL) のバージョンに依存する描画 API を使っています。Pillow は v8〜最新程度で問題ありません。
- 長いテキストの折り返しは単純な文字幅分割ロジックです。より自然な折り返し（単語単位・ルビ考慮等）が必要なら実装拡張を推奨します。
- 生成画像は RGBA（透過）です。Overlay 側の API（`overlay.setOverlayRaw` 相当）へ渡して使う前提です。

復元メモ
--------
このファイルは実装ファイル `models/overlay/overlay_image.py` を参照して復元しました。実装を変更した場合は本ドキュメントも同期して更新してください。

関連ファイル
-------------
- 実装: `models/overlay/overlay_image.py`
- ヘルパ: `models/overlay/overlay_utils.py`
- フォント: `fonts/` ディレクトリ
