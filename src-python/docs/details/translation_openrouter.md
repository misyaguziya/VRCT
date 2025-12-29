# translation_openrouter.py - OpenRouter 翻訳クライアント

## 概要

OpenRouter API を用いた統合 LLM 翻訳クライアントラッパー。OpenAI 互換エンドポイント (`https://openrouter.ai/api/v1`) を利用し、複数の LLM プロバイダーへの統一アクセスを提供する。

## 最近の更新 (2025-12-29)

- OpenRouter API 認証チェック方法を変更
  - **以前:** `client.models.list()` を呼び出して認証確認
  - **現在:** `https://openrouter.ai/api/v1/auth/key` エンドポイントに GET リクエスト送信して確認
  - **理由:** より信頼性の高い専用認証エンドポイントを使用し、高速かつ確実に API キー有効性を検証
- 認証失敗時の sensitive data 処理
  - API キー検証失敗時はレスポンス `data` フィールドに `None` を設定（API キーを露出させない）
  - エラーメッセージのみを返却し、具体的なキー情報は隠蔽

### 影響

| 項目 | 内容 |
|------|------|
| 柔軟性 | 複数 LLM プロバイダーを単一インターフェースで利用 |
| 互換性 | OpenAI 互換 API で既存実装との一貫性維持 |
| 拡張性 | 新規モデル追加時も API キー再設定不要 |

## 責務

- OpenRouter API Key (20文字以上) を用いた認証確認
  - `https://openrouter.ai/api/v1/auth/key` エンドポイントへの HTTP GET リクエストで検証（タイムアウト10秒）
  - ステータスコード 200 で有効と判定
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

