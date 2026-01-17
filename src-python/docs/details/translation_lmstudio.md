# translation_lmstudio.py - LMStudio ローカル LLM 翻訳クライアント

## 概要

LMStudio 互換 OpenAI API を利用したローカル LLM 翻訳クライアントラッパー。モデル一覧取得・モデル選択・翻訳処理を統一インターフェースで提供する。

## 最近の更新 (2025-12-30)

- 接続失敗時のエラーハンドリング改善
  - URL への疎通確認失敗時にモデルリストをクリア (`SELECTABLE_LMSTUDIO_MODEL_LIST = []`)
  - 選択モデルをクリア (`SELECTED_LMSTUDIO_MODEL = None`)
  - `SELECTABLE_TRANSLATION_ENGINE_STATUS["LMStudio"]` を False に設定
  - フロントエンドに通知して UI を同期

## 最近の更新 (2025-10-20)

- 新規追加: ローカル LLM (LMStudio) を翻訳エンジン群へ統合
- `getModelList()` により現在起動中インスタンスから利用可能モデルを取得
- `setModel()` 成功時に `updateClient()` を呼ぶことで LangChain `ChatOpenAI` を再構築
- YAML (`prompt/translation_lmstudio.yml`) からシステムプロンプト (`system_prompt`) と対応言語をロード

### 影響

| 項目 | 内容 |
|------|------|
| 拡張性 | ネットワーク不要のローカル推論を利用可能 |
| 一貫性 | 他 API クライアント (OpenAI/Plamo/Gemini/Ollama) と同一メソッド構成 |
| 保守性 | 翻訳ロジックを共通フォーマットへ集約 |

## 責務

- LMStudio エンドポイントへの疎通確認 (認証代替)
- 利用可能モデル一覧の収集とソート
- 選択モデルの検証と内部保持
- LangChain ラッパーインスタンス生成
- システムプロンプトによる指示付き翻訳実行

## 公開API (メソッド)

```python
class LMStudioClient:
    def __init__(base_url: str | None = None, root_path: str = None)
    def getBaseURL() -> str | None
    def setBaseURL(base_url: str | None) -> bool
    def getModelList() -> list[str]
    def getModel() -> str | None
    def setModel(model: str) -> bool
    def updateClient() -> None
    def translate(text: str, input_lang: str, output_lang: str) -> str
```

### メソッド詳細

- `setBaseURL`: 疎通確認 (_authentication_check) に成功した場合のみ内部更新
- `getModelList`: `OpenAI` クライアントで `/models` を列挙し id を抽出
- `setModel`: `getModelList` 内のモデル名のみ受理
- `updateClient`: `ChatOpenAI` インスタンスを最新モデルで再生成
- `translate`: システム / ユーザメッセージで LLM へ問い合わせし文字列レスポンスを正規化

## 使用例

```python
client = LMStudioClient(base_url="http://localhost:1234/v1")
models = client.getModelList()
if models:
    client.setModel(models[0])
    client.updateClient()
    translated = client.translate("こんにちは世界", "Japanese", "English")
    print(translated)
```

## 依存関係

- `openai.OpenAI`: LMStudio OpenAI 互換 API 呼び出し
- `langchain_openai.ChatOpenAI`: LangChain 抽象化
- `translation_languages.translation_lang`: 対応言語集合
- `translation_utils.loadPromptConfig`: プロンプト YAML ロード

## 注意事項

- `api_key` は固定文字列 "lmstudio" (LMStudio 側で不要のため) を利用
- モデル一覧取得はエンドポイントの互換性に依存 (古いバージョン非対応の可能性)
- `updateClient()` 呼び出し前は `translate()` を利用できない
- **接続失敗時の自動処理:**
  - URL への疎通確認（接続テスト）が失敗すると、自動的にモデルリストと選択モデルがクリアされる
  - `SELECTABLE_TRANSLATION_ENGINE_STATUS["LMStudio"]` が False に設定され、エンジンが使用不可状態になる
  - Controller が自動的にフロントエンドに状態変化を通知

## 制限事項

- ストリーミング未対応 (streaming=False)
- エラーハンドリングは包括的ではなく詳細原因は上位層で処理必要

## 関連ドキュメント

- `details/translation_translator.md`
- `details/translation_languages.md`

