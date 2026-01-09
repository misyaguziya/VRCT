# 翻訳プロンプトへの履歴注入（Chat/Mic/Speaker）

LLM は直前までの会話文脈を理解して翻訳品質を向上させられます。そのため、システムプロンプトに最近の履歴（Chat/Mic/Speaker）を内包する機能を追加しました。大量のログでトークン消費が増えないよう、YAML 設定で取り込み範囲と上限を管理できます。

## アーキテクチャ

### 履歴管理（Model）

**`model.py`** でChat/Mic/Speakerのメッセージ履歴を一元管理：

```python
# 履歴バッファ（最大50件）
self.translation_history: list[dict] = []
self.translation_history_max_items = 50

# 履歴追加（オリジナルメッセージのみ、翻訳結果は保存しない）
model.addTranslationHistory("chat", "こんにちは")
model.addTranslationHistory("mic", "今日はいい天気")  
model.addTranslationHistory("speaker", "Hello!")

# 履歴取得
history = model.getTranslationHistory(max_items=10)

# 履歴クリア
model.clearTranslationHistory()
```

### 自動注入（Model → Translator → 各LLMクライアント）

- **`model.getTranslate()`** で履歴を取得し、`translator.translate(..., context_history=history)` に渡す。
- **`Translator.translate()`** 側でエンジンごとの分岐直前に `setContextHistory()` を呼び、履歴をプロンプト組み立てに反映する。

```python
# model.getTranslate()
history = self.getTranslationHistory()
translation = self.translator.translate(
  translator_name=translator_name,
  weight_type=config.CTRANSLATE2_WEIGHT_TYPE,
  source_language=source_language,
  target_language=target_language,
  target_country=target_country,
  message=message,
  context_history=history,
)

# Translator.translate() の一例（OpenAI）
case "OpenAI_API":
  if self.openai_client is None:
    result = False
  else:
    if context_history:
      self.openai_client.setContextHistory(context_history)
    result = self.openai_client.translate(message, input_lang=source_language, output_lang=target_language)
```

### メッセージ処理（Controller）

**`controller.py`** で各メッセージ処理完了後に履歴へ追加（翻訳の成否に関係なく、オリジナル文だけ保存）：

- **Chat**: `chatMessage()` の末尾で `model.addTranslationHistory("chat", ...)`
- **Mic**: `micMessage()` の末尾で `model.addTranslationHistory("mic", ...)`
- **Speaker**: `speakerMessage()` の末尾で `model.addTranslationHistory("speaker", ...)`

## 設定ファイル（例: OpenAI）

`src-python/models/translation/translation_settings/prompt/translation_openai.yml`

```yaml
system_prompt: |
  You are a helpful translation assistant.
  Supported languages:
  {supported_languages}

  Translate the user provided text from {input_lang} to {output_lang}.
  Return ONLY the translated text. Do not add quotes or extra commentary.
history:
  use_history: true               # 履歴をプロンプトへ注入するか
  sources: [chat, mic, speaker]   # 取り込み対象の履歴種別
  max_messages: 10                # 注入する履歴件数の上限（新しい順）
  max_chars: 4000                 # 履歴整形後の最大文字数（超過時は先頭を切り捨て）
  header_template: |
    Conversation context (recent {max_messages} messages):
    {history}
  item_template: "[{timestamp}][{source}] {text}"
```

- `system_prompt`: 従来どおり、`{supported_languages}`/`{input_lang}`/`{output_lang}` が利用可能。
- `history.use_history`: 履歴注入を有効化します。
- `history.sources`: 取り込み対象ソース。`chat`/`mic`/`speaker` から選択。
- `history.max_messages`: 新しい順に N 件を取り込みます。
- `history.max_chars`: 整形後の履歴文字列の最大長。上限を超えた場合は先頭側を切り捨て（新しい文脈を優先）。
- `history.header_template`: 履歴ヘッダの整形テンプレート。`{max_messages}`/`{history}` が利用可能。
- `history.item_template`: 各履歴アイテムの整形テンプレート。`{timestamp}`（HH:MM形式）/`{source}`/`{text}` が利用可能。

## 実装（OpenAI クライアント）

`src-python/models/translation/translation_openai.py`

- `OpenAIClient.setContextHistory(history_items: list[dict])` を追加。
  - `history_items` は以下のキーを含む辞書の配列：
    - `source`: `"chat" | "mic" | "speaker"`
    - `text`:   文字列
    - `timestamp`: ISO形式の日時文字列（HH:MM形式にフォーマットされてプロンプトに挿入）
- `translate()` 呼び出し時、YAML の `history` 設定に基づき、指定履歴をシステムプロンプト末尾へ整形して注入します。
- 文字数上限は簡易的に `max_chars` で制御（トークンカウントは行わず、過剰消費抑制用の安全策）。

## 使い方

### 基本的な流れ

1. **メッセージ発生時に履歴追加**（controller.py で自動実行）
```python
# Chat送信時（オリジナルメッセージのみ保存）
model.addTranslationHistory("chat", user_message)

# Mic入力時（音声認識結果のみ保存）
model.addTranslationHistory("mic", transcribed_text)

# Speaker受信時（受信したオリジナルメッセージのみ保存）
model.addTranslationHistory("speaker", received_text)
```

2. **翻訳時に自動注入**（model.py で自動実行）
```python
# getTranslate() 内で自動的に履歴が各LLMクライアントへ注入される
translation = model.getTranslate(translator_name, ...)
```

3. **設定の調整**（YAML編集）
```yaml
history:
  use_history: true          # 有効/無効
  sources: [chat, mic]       # chatとmicのみ使う場合
  max_messages: 5            # 最新5件のみ
  max_chars: 2000            # 2000文字まで
```

### 手動で履歴を操作（必要な場合のみ）

```python
# 履歴をクリア
model.clearTranslationHistory()

# 履歴を取得
recent_history = model.getTranslationHistory(max_items=10)

# 手動で追加
model.addTranslationHistory("chat", "カスタムメッセージ")
```

## 連携方法（開発者向け）

既存のcontroller/model統合により、**自動で動作**します：

1. ユーザーがChat入力 → `controller.chatMessage()` → メッセージ処理完了後に `model.addTranslationHistory()` 呼び出し（翻訳の成功/失敗に関係なく）
2. マイク音声 → `controller.micMessage()` → メッセージ処理完了後に `model.addTranslationHistory()` 呼び出し（翻訳の成功/失敗に関係なく）
3. スピーカー受信 → `controller.speakerMessage()` → メッセージ処理完了後に `model.addTranslationHistory()` 呼び出し（翻訳の成功/失敗に関係なく）
4. 翻訳実行 → `model.getTranslate()` → LLMクライアントへ履歴を自動注入 → `client.translate()` で履歴付きプロンプト生成

**重要**: 履歴にはオリジナルメッセージのみが保存されます。翻訳結果は履歴に含まれません。これによりトークン消費を抑え、文脈として必要な情報のみを提供します。

**追加実装は不要です。** YAML設定を変更するだけで履歴注入の有効/無効や範囲を制御できます。

## 連携方法

## 対応状況

✅ **全LLMクライアントに展開済み**

以下のすべてのクライアントで履歴注入機能が利用可能です：
- OpenAI (`translation_openai.py` / `translation_openai.yml`)
- Gemini (`translation_gemini.py` / `translation_gemini.yml`)
- Groq (`translation_groq.py` / `translation_groq.yml`)
- OpenRouter (`translation_openrouter.py` / `translation_openrouter.yml`)
- LMStudio (`translation_lmstudio.py` / `translation_lmstudio.yml`)
- Ollama (`translation_ollama.py` / `translation_ollama.yml`)
- Plamo (`translation_plamo.py` / `translation_plamo.yml`)

各クライアントで同一の設定形式とAPIインターフェースを使用します：
- `setContextHistory(history_items: list[dict])` メソッド
- YAML の `history` セクション

## 今後の拡張案

- 実トークン見積りに基づく切り詰め（tiktoken 等）
- 要約モデルを使った古い履歴の縮約
