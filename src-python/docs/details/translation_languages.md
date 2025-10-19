# translation_languages.py - 翻訳言語マッピング

## 概要

翻訳エンジンが対応する言語コードのマッピングテーブルを提供するモジュールです。複数の翻訳エンジン（DeepL、Google、Bing、Papago等）の言語コード仕様の差異を吸収し、統一的な翻訳言語管理を実現します。

## 主要機能

### 多エンジン対応

- DeepL（無料版・API版）
- Google Translate
- Microsoft Translator（Bing）
- Papago Translator
- その他のWeb翻訳サービス

### 言語コード統合管理

- 各エンジン固有の言語コード形式を統一
- 送信元（source）と送信先（target）言語の分離管理
- 地域固有言語バリエーションの対応

## データ構造

### translation_lang

```python
translation_lang: Dict[str, Dict[str, Dict[str, str]]] = {
    "エンジン名": {
        "source": {"言語名": "言語コード", ...},
        "target": {"言語名": "言語コード", ...}
    }
}
```

### DeepL翻訳エンジン（無料版）

```python
translation_lang["DeepL"] = {
    "source": {
        "Arabic": "ar", "Bulgarian": "bg", "Czech": "cs", "Danish": "da",
        "German": "de", "Greek": "el", "English": "en", "Spanish": "es",
        "Estonian": "et", "Finnish": "fi", "French": "fr", "Irish": "ga",
        "Croatian": "hr", "Hungarian": "hu", "Indonesian": "id", 
        "Icelandic": "is", "Italian": "it", "Japanese": "ja",
        "Korean": "ko", "Lithuanian": "lt", "Latvian": "lv",
        "Maltese": "mt", "Bokmal": "nb", "Dutch": "nl",
        "Norwegian": "no", "Polish": "pl", "Portuguese": "pt",
        "Romanian": "ro", "Russian": "ru", "Slovak": "sk",
        "Slovenian": "sl", "Swedish": "sv", "Turkish": "tr",
        "Ukrainian": "uk", "Chinese Simplified": "zh",
        "Chinese Traditional": "zh"
    },
    "target": {/* 同じマッピング */}
}
```

### DeepL API（有料版 概要）

```python
translation_lang["DeepL_API"] = {
    "source": {/* 基本的にDeepLと同様 */},
    "target": {
        "Japanese": "ja",
        "English American": "en-US",    # 地域別対応
        "English British": "en-GB",
        "Portuguese Brazilian": "pt-BR", # ブラジル・ポルトガル語
        "Portuguese European": "pt-PT",  # ヨーロッパ・ポルトガル語
        "Chinese Simplified": "zh",
        "Chinese Traditional": "zh"
        /* その他の言語 */
    }
}
```

## 主要対応言語

### 西欧言語

- **English**: 英語（米国・英国バリエーション）
- **German**: ドイツ語
- **French**: フランス語
- **Spanish**: スペイン語
- **Italian**: イタリア語
- **Portuguese**: ポルトガル語（ブラジル・欧州）
- **Dutch**: オランダ語
- **Swedish**: スウェーデン語
- **Norwegian**: ノルウェー語

### 東欧・スラブ言語

- **Russian**: ロシア語
- **Polish**: ポーランド語
- **Czech**: チェコ語
- **Slovak**: スロバキア語
- **Ukrainian**: ウクライナ語
- **Bulgarian**: ブルガリア語
- **Croatian**: クロアチア語
- **Slovenian**: スロベニア語

### アジア言語

- **Japanese**: 日本語
- **Korean**: 韓国語
- **Chinese Simplified**: 中国語（簡体字）
- **Chinese Traditional**: 中国語（繁体字）
- **Indonesian**: インドネシア語

### その他の言語

- **Arabic**: アラビア語
- **Turkish**: トルコ語
- **Finnish**: フィンランド語
- **Estonian**: エストニア語
- **Latvian**: ラトビア語
- **Lithuanian**: リトアニア語
- **Maltese**: マルタ語
- **Irish**: アイルランド語

## 使用方法

### 基本的な言語コード取得

```python
from models.translation.translation_languages import translation_lang

# DeepLで日本語から英語への翻訳
deepl_source = translation_lang["DeepL"]["source"]["Japanese"]  # "ja"
deepl_target = translation_lang["DeepL"]["target"]["English"]   # "en"

# DeepL APIで地域固有の英語指定
deepl_api_target = translation_lang["DeepL_API"]["target"]["English American"]  # "en-US"
```

### 対応言語の確認

```python
def get_supported_languages(engine_name):
    """指定エンジンの対応言語一覧取得"""
    if engine_name in translation_lang:
        engine_data = translation_lang[engine_name]
        source_langs = list(engine_data["source"].keys())
        target_langs = list(engine_data["target"].keys()) 
        return {
            "source": source_langs,
            "target": target_langs,
            "common": list(set(source_langs) & set(target_langs))
        }
    return None

# 使用例
deepl_langs = get_supported_languages("DeepL")
print(f"DeepL対応言語数: {len(deepl_langs['common'])}")
```

### 言語コード変換

```python
def convert_language_code(language_name, from_engine, to_engine, direction="source"):
    """エンジン間での言語コード変換"""
    try:
        # 元エンジンから言語名を確認
        from_codes = translation_lang[from_engine][direction]
        to_codes = translation_lang[to_engine][direction]
        
        if language_name in from_codes and language_name in to_codes:
            return to_codes[language_name]
        return None
    except KeyError:
        return None

# 使用例：DeepLからGoogle Translateへの変換
google_code = convert_language_code("Japanese", "DeepL", "Google", "target")
```

### 翻訳システムでの統合利用

```python
class TranslationLanguageManager:
    """翻訳言語管理クラス"""
    
    @staticmethod
    def get_language_code(engine, language, direction="target"):
        """安全な言語コード取得"""
        try:
            return translation_lang[engine][direction][language]
        except KeyError:
            return None
    
    @staticmethod
    def is_language_supported(engine, language, direction="target"):
        """言語サポート確認"""
        try:
            return language in translation_lang[engine][direction]
        except KeyError:
            return False
    
    @staticmethod
    def get_compatible_engines(source_lang, target_lang):
        """両言語をサポートするエンジン一覧"""
        compatible = []
        for engine in translation_lang:
            source_supported = TranslationLanguageManager.is_language_supported(
                engine, source_lang, "source"
            )
            target_supported = TranslationLanguageManager.is_language_supported(
                engine, target_lang, "target"
            )
            if source_supported and target_supported:
                compatible.append(engine)
        return compatible

# 使用例
manager = TranslationLanguageManager()

# 日本語→英語をサポートするエンジン
engines = manager.get_compatible_engines("Japanese", "English")
print(f"対応エンジン: {engines}")

# 特定エンジンでの言語コード取得
ja_code = manager.get_language_code("DeepL", "Japanese", "source")
en_code = manager.get_language_code("DeepL", "English", "target")
```

## エンジン別特徴

### DeepL（無料版）

- **強み**: 高精度、自然な翻訳
- **制限**: 月間使用量制限、API制限
- **対応**: 26言語

### DeepL API（有料版）

- **強み**: DeepLの高精度、地域別言語対応
- **制限**: 従量課金
- **対応**: 地域固有言語バリエーション

### Google Translate

- **強み**: 多言語対応、高速
- **制限**: API制限、精度のばらつき
- **対応**: 100+言語

### Microsoft Translator

- **強み**: リアルタイム翻訳、音声対応
- **制限**: APIキー必要
- **対応**: 70+言語

## 地域バリエーション対応

### 英語の地域別対応

```python
# DeepL APIでの英語バリエーション
"English American": "en-US",    # アメリカ英語
"English British": "en-GB",     # イギリス英語
```

### ポルトガル語の地域別対応

```python
# ブラジル・ポルトガル語とヨーロッパ・ポルトガル語
"Portuguese Brazilian": "pt-BR",
"Portuguese European": "pt-PT",
```

### 中国語の文字体系対応

```python
# 簡体字・繁体字の区別
"Chinese Simplified": "zh",     # 簡体字（中国本土）
"Chinese Traditional": "zh",    # 繁体字（台湾・香港）
```

## 拡張性

### 新エンジンの追加

```python
# 新しい翻訳エンジンの追加例
translation_lang["NewEngine"] = {
    "source": {
        "Japanese": "jp",
        "English": "en",
        "Korean": "kr"
    },
    "target": {
        "Japanese": "jp",
        "English": "en",
        "Korean": "kr"
    }
}
```

### 新言語の追加

```python
# 既存エンジンへの新言語追加
translation_lang["DeepL"]["source"]["Hindi"] = "hi"
translation_lang["DeepL"]["target"]["Hindi"] = "hi"
```

## エラーハンドリング

### 安全な言語コード取得

```python
def safe_get_language_code(engine, language, direction="target", fallback="en"):
    """フォールバック機能付き言語コード取得"""
    try:
        return translation_lang[engine][direction][language]
    except KeyError:
        # フォールバック言語を返す
        try:
            return translation_lang[engine][direction].get("English", fallback)
        except KeyError:
            return fallback
```

### 言語サポート検証

```python
def validate_translation_pair(engine, source_lang, target_lang):
    """翻訳ペアの有効性検証"""
    try:
        engine_data = translation_lang[engine]
        source_supported = source_lang in engine_data["source"]
        target_supported = target_lang in engine_data["target"]
        
        return {
            "valid": source_supported and target_supported,
            "source_supported": source_supported,
            "target_supported": target_supported
        }
    except KeyError:
        return {
            "valid": False,
            "source_supported": False,
            "target_supported": False,
            "error": f"Unknown engine: {engine}"
        }
```

## 注意事項

- エンジンによって言語コード形式が異なる
- 地域バリエーションはエンジンにより対応状況が異なる
- 新しい言語追加時は全エンジンでの対応状況を確認
- API制限や課金体系はエンジンごとに異なる
- 一部の言語ペアは翻訳精度に差がある場合がある

## 関連モジュール

- `translation_translator.py`: 翻訳エンジン本体
- `translation_utils.py`: 翻訳ユーティリティ
- `transcription_languages.py`: 音声認識言語マッピング
- `config.py`: 翻訳言語設定管理
- `controller.py`: 言語選択UI制御

## 最近の更新 (2025-10-20)

### CTranslate2 言語構造変更

従来: 重みタイプがトップレベルキー (`translation_lang["m2m100_418M-ct2-int8"]`).

現在: `translation_lang["CTranslate2"][weight_type]["source"|"target"]` のネスト構造。`model.findTranslationEngines` / `translation_translator` で `engine == "CTranslate2"` の場合は `CTRANSLATE2_WEIGHT_TYPE` を用いて内部辞書へアクセス。

### 外部 YAML 言語マッピング導入

`models/translation/languages/languages.yml` を追加し、`config.init_config()` 内で `loadTranslationLanguages(path=config.PATH_LOCAL)` を呼び出し、既存 `translation_lang` にマージ/上書き。読込失敗時は空辞書を返しフォールバック。（PyYAML 追加）

### LMStudio / Ollama 翻訳モデル対応準備

新規ローカル LLM 接続用として LMStudio / Ollama 追加。現段階ではモデルリスト・選択用のエンドポイントとプロパティ (`SELECTABLE_LMSTUDIO_MODEL_LIST`, `SELECTED_LMSTUDIO_MODEL`, `SELECTABLE_OLLAMA_MODEL_LIST`, `SELECTED_OLLAMA_MODEL`) を定義。言語マッピングは今後 YAML 拡張で統合予定（未実装部分は翻訳本体の `translate()` に未統合）。

### モデル選択プロパティ名称統一

Plamo / Gemini / OpenAI の選択モデルプロパティを `PLAMO_MODEL` / `GEMINI_MODEL` / `OPENAI_MODEL` から `SELECTED_PLAMO_MODEL` / `SELECTED_GEMINI_MODEL` / `SELECTED_OPENAI_MODEL` へ統一。保存キーも `SELECTED_*` に更新。

### 影響

| 項目 | 内容 |
|------|------|
| CTranslate2 | ネスト化により言語参照コード修正が必要 |
| YAML | 動的言語追加がコード編集無しに可能 |
| LLM接続 | 今後言語マッピングを YAML で拡張予定（未実装） |
| プロパティ | SELECTED_* へ統一で UI/設定整合性向上 |
