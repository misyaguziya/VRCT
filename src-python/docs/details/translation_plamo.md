# translation_plamo.py - Plamo 翻訳クライアント

## 概要

Preferred Networks 提供の Plamo API を利用した翻訳向け LLM クライアントラッパー。モデル一覧取得・認証・モデル選択・翻訳実行を統一インターフェースで提供する。

## 最近の更新 (2025-10-20)

- 新規追加: Plamo クライアント統合
- プロンプト設定を YAML (`prompt/translation_plamo.yml`) からロード（システムプロンプト `system_prompt`）
- モデル一覧取得後ソートして再現性を確保

### 影響

| 項目 | 内容 |
|------|------|
| 拡張性 | 日本発 API への対応により選択肢拡大 |
| 保守性 | 他 LLM クライアントと同一構造でメンテ容易 |
| 一貫性 | メソッド命名/責務の統一化 |

## 責務

- API Key 認証確認
- 利用可能モデルの列挙とソート
- モデル選択の検証
- LangChain `ChatOpenAI` インスタンス生成
- システムプロンプトによる翻訳実行

## 公開API (メソッド)

```python
class PlamoClient:
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
- `getModelList`: 認証済み状態でモデル列挙→ソート
- `setModel`: 列挙済みリスト内モデルのみ受理
- `updateClient`: `ChatOpenAI` を再構築
- `translate`: システム + ユーザメッセージで推論し応答正規化

## 使用例

```python
client = PlamoClient()
if client.setAuthKey("PLAMO_API_KEY"):
    models = client.getModelList()
    if models:
        client.setModel(models[0])
        client.updateClient()
        result = client.translate("こんにちは世界", "Japanese", "English")
        print(result)
```

## 依存関係

- `openai.OpenAI`: Plamo 互換 API 呼び出し
- `langchain_openai.ChatOpenAI`: LangChain ラッパー
- `translation_languages.translation_lang`: 対応言語集合
- `translation_utils.loadPromptConfig`: プロンプト YAML ロード

## 注意事項

- BASE_URL 固定: `https://api.platform.preferredai.jp/v1`
- API Key 未設定時はモデル一覧取得不可
- ストリーミング無効 (streaming=False)

## 制限事項

- 詳細エラーは包括的に扱わず (上位層でログ/フォールバック)
- 翻訳結果の構造が複雑な場合単純文字列へ normalize のみ

## 関連ドキュメント

- `details/translation_translator.md`
- `details/translation_languages.md`

