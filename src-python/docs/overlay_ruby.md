# 小型ログ ルビ表示機能 (Ruby Overlay for Small Log)

## 概要
小型ログ (Small Log Overlay) に日本語原文が含まれる場合、ローマ字(hepburn) を上段、ひらがな(hira) を下段として原文メッセージの上に 2 段のルビを表示できます。翻訳行には現段階ではルビを付与しません。

## 有効化条件
- 原文 `message` が存在し空文字列でない。
- `model.createOverlayImageSmallLog` 内で自動的に `convertMessageToTransliteration(..., hiragana=True, romaji=True)` を呼び出しトークン生成。
- 生成されたトークンに `hepburn` または `hira` が含まれる。

## 大ログ (Large Log) への拡張

大ログについてもトークン単位のルビ描画をサポートしました。`createOverlayImageLargeLog` / `createTextboxLargeLog` 系の API に以下のような追加引数が入り、同等のルビ出力が可能です。

- transliteration_tokens: Optional[List[dict]] — 原文用トークン（orig/hira/hepburn）
- translation_transliteration_tokens: Optional[List[List[dict]] | List[dict]] — 翻訳ごとのトークン配列、もしくは先頭翻訳用の平坦な List[dict]
- ruby_font_scale: float — ルビのフォント倍率（原文フォントサイズに対するスケール）
- ruby_line_spacing: int — ルビ行間ピクセル

対応挙動:

- 原文のみが存在し、その原文にトークンがあれば原文にトークン単位ルビを振ります。

- 原文と翻訳の両方が存在する場合は、原則として原文のルビを抑止し、翻訳側にルビを振ります（翻訳側にトークンがある場合）。

- `translation_transliteration_tokens` は二通りの入力形式を受け付けます:

	- List[List[dict]] — 各翻訳行ごとの tokens 配列（推奨）

	- List[dict] — 平坦な tokens 配列（最初の翻訳行に適用されます）

フォールバック:

- トークン単位レイアウトで横幅がはみ出す or 改行がある場合は、既存のブロックルビ（romaji 上 / hira 下 を 1 行ブロックで表示）へ自動フォールバックします。

注意点:

- 既存の表示ロジックの互換性を保つため、引数は省略可能です（None/[]）。
- フラットな `translation_transliteration_tokens` を渡す場合は最初の翻訳にのみ適用されます。複数翻訳に個別のルビを渡す場合は List[List[dict]] 形式で与えてください。

## 設定キー (`config.OVERLAY_SMALL_LOG_SETTINGS`)
| キー | 型 | 初期値 | 説明 |
| ---- | --- | ------ | ---- |
| ruby_font_scale | float | 0.5 | ルビ文字サイズ倍率 (原文フォントサイズ * 倍率)。安全範囲 0.05〜3.0 |
| ruby_line_spacing | int | 4 | ローマ字行とひらがな行の垂直スペース (px)。0〜200 |

## レイアウト仕様

1. ルビブロック (romaji 上 / hiragana 下) を中央揃えで描画。

2. その下に従来の本文テキストボックスを縦方向に連結。

3. フォントファミリは本文と同一 (言語に対応する NotoSans 系)。

4. ルビが存在しない場合は従来表示のみ。

## フォールバック

- ルビ生成中に例外が発生した場合はログを記録し、ルビ無しで本文のみ表示。

- トークンが空の場合（両方 False など）は従来表示。

## 例

以下は `createOverlayImageLargeLog` を使って、翻訳側にだけルビを渡す例（平坦な tokens を渡す場合と翻訳ごとの tokens を渡す場合）:

```python
# 平坦な tokens を渡して最初の翻訳に適用
overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！", "Japanese", ["Hello, World!"], ["English"], transliteration_tokens=[], translation_transliteration_tokens=[
	{"orig": "こんにちは", "hira": "こんにちは", "hepburn": "konnichiha"},
	{"orig": "世界", "hira": "せかい", "hepburn": "sekai"},
])

# 翻訳ごとに tokens を与える（推奨）
overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！", "Japanese", ["Hello, World!"], ["English"], transliteration_tokens=[], translation_transliteration_tokens=[
	[
		{"orig": "Hello", "hira": "", "hepburn": "Hello"},
		{"orig": "World", "hira": "", "hepburn": "World"},
	]
])
```

## 今後の拡張候補
- 翻訳行へのルビ付与オプション。
- トークン単位での幅センタリングと折り返し。
- 高度な幅計測 (可変幅フォント対応改善)。

## 簡易テスト
`src-python/overlay_ruby_test.py` を実行すると `overlay_small_ruby_test.png` が生成され、縦順と配置を確認できます。

```bash
# PowerShell (仮想環境有効化後)
python src-python/overlay_ruby_test.py
```

## 注意
UI スケーリングは OpenVR 側の表示サイズのみ変更し、画像内部フォントサイズは直接変更しません。ルビの視認性が低い場合は `ruby_font_scale` を調整してください。
