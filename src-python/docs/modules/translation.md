# models/translation — 詳細設計

構成ファイル:
- translation_translator.py — Translator クラス。DeepL/API、Google、Bing、Papago、CTranslate2 を統一インターフェースで扱う。
- translation_utils.py — 重みファイルのダウンロード・検証ロジック（CTranslate2 用）。
- translation_languages.py — 各エンジンの対応言語マップ。

Translator の契約:
- translate(translator_name, source_language, target_language, target_country, message) -> str|False
  - 成功時は文字列、失敗または一時的エラーは False を返す。
- changeCTranslate2Model(path, model_type, device, device_index, compute_type)
  - CTranslate2 の Translator オブジェクトと Tokenizer を初期化する。

フォールバック:
- Controller/Model 層で翻訳が失敗した場合に CTranslate2 にフォールバックする実装がある。

外部依存:
- ctranslate2, transformers, deepl（オプション）、translators（任意）

安全性:
- 翻訳 API キー（DeepL）は Translator.authenticationDeepLAuthKey で検証して保持。
