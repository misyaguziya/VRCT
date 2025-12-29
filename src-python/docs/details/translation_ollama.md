# translation_ollama.py - Ollama ローカル LLM 翻訳クライアント

## 概要

Ollama サーバー上で稼働するローカル LLM を翻訳エンジンとして扱うためのクライアントラッパー。モデル一覧取得・モデル選択・翻訳実行を統一パターンで提供する。

## 最近の更新 (2025-12-30)

- 接続失敗時のエラーハンドリング改善
  - `/api/ping` への疎通確認失敗時にモデルリストをクリア (`SELECTABLE_OLLAMA_MODEL_LIST = []`)
  - 選択モデルをクリア (`SELECTED_OLLAMA_MODEL = None`)
  - `SELECTABLE_TRANSLATION_ENGINE_STATUS["Ollama"]` を False に設定
  - フロントエンドに通知して UI を同期

## 最近の更新 (2025-10-20)

- 新規追加: Ollama を翻訳エンジン群へ統合
- `/api/ping` を用いた疎通確認による簡易認証
- `/api/tags` から利用可能モデル一覧抽出・ソート
- YAML (`prompt/translation_ollama.yml`) からシステムプロンプト (`system_prompt`) と対応言語をロード

### 影響

| 項目 | 内容 |
|------|------|
| 拡張性 | LAN 内ローカル推論を利用可能 |
| 可搬性 | GPU/CPU 任意構成の Ollama 環境に適応 |
| 一貫性 | 他翻訳クライアント (OpenAI/Gemini/Plamo/LMStudio) と統一 API |

## 責務

- Ollama インスタンスへの接続確認
- モデル一覧取得 (タグ列挙) とソート
- 選択モデルの検証と内部保持
- LangChain `ChatOllama` インスタンス生成
- システムプロンプトとユーザ入力を組み立てて翻訳実行

## 公開API (メソッド)

```python
class OllamaClient:
    def __init__(root_path: str = None)
    def authenticationCheck() -> bool
    def getModelList() -> list[str]
    def getModel() -> str | None
    def setModel(model: str) -> bool
    def updateClient() -> None
    def translate(text: str, input_lang: str, output_lang: str) -> str
```

### メソッド詳細

- `authenticationCheck`: `/api/ping` が 200 を返すかで利用可否判定
- `getModelList`: 認証成功時のみ `/api/tags` 結果から name 抽出
- `setModel`: 取得済みモデル一覧内に存在する場合のみ設定
- `updateClient`: `ChatOllama` を最新モデルで再生成
- `translate`: system / user メッセージを LLM へ送信し結合結果を正規化

## 使用例

```python
client = OllamaClient()
if client.authenticationCheck():
    models = client.getModelList()
    if models:
        client.setModel(models[0])
        client.updateClient()
        translated = client.translate("こんにちは世界", "Japanese", "English")
        print(translated)
```

## 依存関係

- `requests`: Ping/タグ API 呼び出し
- `langchain_ollama.ChatOllama`: LangChain LLM ラッパー
- `translation_languages.translation_lang`: 対応言語集合
- `translation_utils.loadPromptConfig`: プロンプト YAML ロード

## 注意事項

- サーバー既定 URL: `http://localhost:11434`
- モデル一覧取得は起動しているローカルサーバー状態に依存
- `updateClient()` 呼び出し前は `translate()` を利用不可
- **接続失敗時の自動処理:**
  - `/api/ping` への疎通確認が失敗すると、自動的にモデルリストと選択モデルがクリアされる
  - `SELECTABLE_TRANSLATION_ENGINE_STATUS["Ollama"]` が False に設定され、エンジンが使用不可状態になる
  - Controller が自動的にフロントエンドに状態変化を通知

## 制限事項

- ストリーミング未対応 (streaming=False)
- エラー詳細は包括的に扱わない (上位層でフォールバック)

## 関連ドキュメント

- `details/translation_translator.md`
- `details/translation_languages.md`

