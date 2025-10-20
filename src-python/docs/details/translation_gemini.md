# translation_gemini.py - Gemini 翻訳クライアント

## 概要

Google Gemini / Gemma 系モデルを翻訳用途で利用するためのクライアントラッパー。モデル一覧取得・認証・モデル選択・翻訳実行を統一インターフェースで提供する。

## 最近の更新 (2025-10-20)

- 新規追加: Gemini クライアント統合
- 除外キーワード (`audio`, `image`, `veo`, `tts`, `robotics`, `computer-use`) により非テキスト指向モデルをフィルタ
- `generateContent` をサポートするモデルのみ採用
- YAML (`prompt/translation_gemini.yml`) からシステムプロンプト (`system_prompt`) をロード

### 影響

| 項目 | 内容 |
|------|------|
| 正確性 | 非テキスト特化モデル除外で翻訳品質安定 |
| 保守性 | 明示的フィルタリングロジックで再利用容易 |
| 一貫性 | 他 LLM クライアントとの API 形状統一 |

## 責務

- API Key 認証確認
- Gemini/Gemma 系モデル列挙とフィルタリング
- モデル選択検証と内部保持
- LangChain `ChatGoogleGenerativeAI` インスタンス生成
- システムプロンプトによる翻訳実行

## 公開API (メソッド)

```python
class GeminiClient:
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

- `setAuthKey`: `_authentication_check` 成功時のみ内部保存
- `getModelList`: フィルタリング適用後ソート
- `setModel`: 取得済みモデル一覧内のみ受理
- `updateClient`: `ChatGoogleGenerativeAI` を再構築
- `translate`: システム + ユーザメッセージ構築→呼び出し→レスポンス正規化

## 使用例

```python
client = GeminiClient()
if client.setAuthKey("GEMINI_API_KEY"):
    models = client.getModelList()
    if models:
        client.setModel(models[0])
        client.updateClient()
        result = client.translate("こんにちは世界", "Japanese", "English")
        print(result)
```

## 依存関係

- `google.genai`: モデル列挙 / 認証
- `langchain_google_genai.ChatGoogleGenerativeAI`: LangChain ラッパー
- `translation_languages.translation_lang`: 対応言語集合
- `translation_utils.loadPromptConfig`: プロンプト YAML ロード

## 注意事項

- 非テキスト向けモデル (画像/音声/ロボティクス等) は除外
- ストリーミング無効 (streaming=False)
- API Key 必須 (未設定時 getModelList 不可)

## 制限事項

- 詳細エラーを包括的に扱わない (上位層でロギング/フォールバック)
- 複雑レスポンス構造は単純文字列へ normalize のみ

## 関連ドキュメント

- `details/translation_translator.md`
- `details/translation_languages.md`

