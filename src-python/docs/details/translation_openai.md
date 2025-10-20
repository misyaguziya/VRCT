# translation_openai.py - OpenAI 翻訳クライアント

## 概要

OpenAI API (公式または互換エンドポイント) を用いた汎用 LLM 翻訳クライアントラッパー。モデル一覧取得・認証・モデル選択・翻訳実行を提供する。

## 最近の更新 (2025-10-20)

- 除外キーワード (`whisper`, `embedding`, `image`, `tts`, `audio`, `search`, `transcribe`, `diarize`, `vision`) を用いて翻訳非適合モデルをフィルタ
- Fine-tune モデル (`ft:`) は root が `gpt-` で始まる場合採用
- YAML (`prompt/translation_openai.yml`) からシステムプロンプト (`system_prompt`) をロードする構成へ統合

### 影響

| 項目 | 内容 |
|------|------|
| 正確性 | 不適合モデル除外で翻訳品質安定 |
| 保守性 | フィルタリングロジック明示化で再利用容易 |
| 一貫性 | 他翻訳クライアントと API 形状統一 |

## 責務

- OpenAI API Key を用いた認証確認
- 利用可能モデルのフィルタリングとソート
- 選択モデルの検証と内部保持
- LangChain `ChatOpenAI` インスタンス生成
- システムプロンプトによる翻訳実行

## 公開API (メソッド)

```python
class OpenAIClient:
    def __init__(base_url: str | None = None, root_path: str = None)
    def getModelList() -> list[str]
    def getAuthKey() -> str | None
    def setAuthKey(api_key: str) -> bool
    def getModel() -> str | None
    def setModel(model: str) -> bool
    def updateClient() -> None
    def translate(text: str, input_lang: str, output_lang: str) -> str
```

### メソッド詳細

- `setAuthKey`: `_authentication_check` に成功した場合のみ内部保存
- `getModelList`: モデル列挙後フィルタリング適用しソート
- `setModel`: 取得済みリスト内のモデルのみ受理
- `updateClient`: `ChatOpenAI` を選択モデルで再生成
- `translate`: システム + ユーザメッセージ構築→LLM呼び出し→レスポンス正規化

## 使用例

```python
client = OpenAIClient()
if client.setAuthKey("OPENAI_API_KEY"):
    models = client.getModelList()
    client.setModel(models[0])
    client.updateClient()
    result = client.translate("こんにちは世界", "Japanese", "English")
    print(result)
```

## 依存関係

- `openai.OpenAI`: モデル列挙 / 推論
- `langchain_openai.ChatOpenAI`: LangChain ラッパー
- `translation_languages.translation_lang`: 対応言語集合
- `translation_utils.loadPromptConfig`: プロンプト YAML ロード

## 注意事項

- `base_url` が None の場合公式エンドポイント
- ストリーミング無効 (streaming=False) 固定
- API Key 無設定時 `getModelList()` は空

## 制限事項

- エラーメッセージ詳細は包括的に扱わない (上位層でロギング)
- 翻訳結果の構造が複雑 (list/dict) 場合を単純文字列へ normalize するのみ

## 関連ドキュメント

- `details/translation_translator.md`
- `details/translation_languages.md`

