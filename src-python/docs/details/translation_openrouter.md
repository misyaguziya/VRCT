# translation_openrouter.py - OpenRouter 翻訳クライアント

## 概要

OpenRouter API を用いた統合 LLM 翻訳クライアントラッパー。OpenAI 互換エンドポイント (`https://openrouter.ai/api/v1`) を利用し、複数の LLM プロバイダーへの統一アクセスを提供する。

## 最近の更新 (2025-12-10)

- OpenRouter API サポートを新規追加
- 単一 API キーで複数 LLM プロバイダーへアクセス可能
- 除外キーワード (`whisper`, `embedding`, `image`, `tts`, `audio`, `search`, `transcribe`, `diarize`, `vision`) によるテキスト処理モデルのフィルタリング
- YAML (`prompt/translation_openrouter.yml`) からシステムプロンプトをロード

### 影響

| 項目 | 内容 |
|------|------|
| 柔軟性 | 複数 LLM プロバイダーを単一インターフェースで利用 |
| 互換性 | OpenAI 互換 API で既存実装との一貫性維持 |
| 拡張性 | 新規モデル追加時も API キー再設定不要 |

## 責務

- OpenRouter API Key (20文字以上) を用いた認証確認
- 利用可能モデルのフィルタリングとソート
- 選択モデルの検証と内部保持
- LangChain `ChatOpenAI` インスタンス生成（base_url に OpenRouter エンドポイント指定）
- システムプロンプトによる翻訳実行

## 公開API (メソッド)

```python
class OpenRouterClient:
    def __init__(root_path: str = None)
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
- `updateClient`: `ChatOpenAI` を選択モデル・OpenRouter base_url で再生成
- `translate`: システム + ユーザメッセージ構築→LLM呼び出し→レスポンス正規化

## 使用例

```python
client = OpenRouterClient()
if client.setAuthKey("sk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"):
    models = client.getModelList()
    # OpenRouter は多数のモデルを提供
    client.setModel("anthropic/claude-3-sonnet")
    client.updateClient()
    result = client.translate("こんにちは世界", "Japanese", "English")
    print(result)
```

## 依存関係

- `openai.OpenAI`: モデル列挙 / 推論（OpenRouter エンドポイント経由）
- `langchain_openai.ChatOpenAI`: LangChain ラッパー
- `translation_languages.translation_lang`: 対応言語集合
- `translation_utils.loadPromptConfig`: プロンプト YAML ロード

## 注意事項

- base_url は固定で `https://openrouter.ai/api/v1`
- ストリーミング無効 (streaming=False) 固定
- API Key 無設定時 `getModelList()` は空
- API Key は20文字以上であることを検証

## 制限事項

- エラーメッセージ詳細は包括的に扱わない (上位層でロギング)
- 翻訳結果の構造が複雑 (list/dict) 場合を単純文字列へ normalize するのみ
- OpenRouter の料金体系はモデル毎に異なる（利用前に確認が必要）

## 関連ドキュメント

- `details/translation_translator.md`
- `details/translation_languages.md`
- `details/translation_openai.md` (類似実装)
- `details/translation_groq.md` (類似実装)

