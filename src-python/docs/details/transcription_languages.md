# transcription_languages.py - 音声認識言語マッピング

## 概要

音声認識エンジンが対応する言語コードのマッピングテーブルを提供するモジュールです。異なる音声認識エンジンの言語コード仕様の差異を吸収し、統一的なインターフェースを提供します。

## 主要機能

### 言語マッピングテーブル
- 表示用言語名から各エンジン固有の言語コードへの変換
- 国・地域固有の言語バリエーション対応
- 複数音声認識エンジンの統一的な言語管理

### 対応エンジン
- Google Speech Recognition
- OpenAI Whisper（faster-whisper）
- その他の音声認識エンジン

## データ構造

### transcription_lang
```python
transcription_lang: Dict[str, List[Dict[str, str]]]
```

言語とその地域バリエーションのマッピング

```python
transcription_lang = {
    "English": [
        {"country": "United States", "google_language_code": "en-US"},
        {"country": "United Kingdom", "google_language_code": "en-GB"},
        {"country": "Australia", "google_language_code": "en-AU"}
    ],
    "Japanese": [
        {"country": "Japan", "google_language_code": "ja-JP"}
    ],
    "Korean": [
        {"country": "South Korea", "google_language_code": "ko-KR"}
    ]
}
```

## 使用方法

### 基本的な言語コード取得

```python
from models.transcription.transcription_languages import transcription_lang

# 日本語の言語コード取得
japanese_codes = transcription_lang.get("Japanese", [])
if japanese_codes:
    code = japanese_codes[0]["google_language_code"]  # "ja-JP"

# 英語の地域別言語コード取得
english_codes = transcription_lang.get("English", [])
for region in english_codes:
    print(f"{region['country']}: {region['google_language_code']}")
```

### 利用可能言語の一覧取得

```python
# 対応言語の一覧
supported_languages = list(transcription_lang.keys())
print(f"対応言語: {supported_languages}")

# 言語と国の組み合わせ一覧
language_country_pairs = []
for lang, countries in transcription_lang.items():
    for country_data in countries:
        language_country_pairs.append({
            "language": lang,
            "country": country_data["country"],
            "code": country_data["google_language_code"]
        })
```

### 翻訳システムとの連携

```python
# 翻訳システムで対応している言語の確認
from models.translation.translation_languages import translation_lang

transcription_langs = list(transcription_lang.keys())
translation_langs = []
for engine in translation_lang.keys():
    translation_langs.extend(translation_lang[engine]["source"].keys())

# 音声認識と翻訳の両方で対応している言語
supported_langs = list(filter(lambda x: x in transcription_langs, translation_langs))
```

## 主要対応言語

### 西欧言語
- **English**: US, UK, Australia, Canada, India, South Africa
- **Spanish**: Spain, Mexico, Argentina, Colombia
- **French**: France, Canada, Belgium
- **German**: Germany, Austria, Switzerland
- **Italian**: Italy
- **Portuguese**: Brazil, Portugal

### アジア言語
- **Japanese**: Japan
- **Korean**: South Korea  
- **Chinese**: China (Simplified), Taiwan (Traditional), Hong Kong
- **Thai**: Thailand
- **Vietnamese**: Vietnam

### その他の言語
- **Russian**: Russia
- **Arabic**: Saudi Arabia, UAE, Egypt
- **Hindi**: India
- **Dutch**: Netherlands
- **Swedish**: Sweden
- **Norwegian**: Norway

## エンジン別言語コード形式

### Google Speech Recognition
- RFC 5646準拠の言語タグ形式
- 例: "ja-JP", "en-US", "zh-CN"

### OpenAI Whisper
- ISO 639-1言語コード（2文字）
- 例: "ja", "en", "zh"

### その他のエンジン
- エンジン固有の形式に対応
- マッピングテーブルによる変換

## 地域対応

### 同一言語の地域別対応
```python
# 英語の地域バリエーション
"English": [
    {"country": "United States", "google_language_code": "en-US"},
    {"country": "United Kingdom", "google_language_code": "en-GB"},
    {"country": "Australia", "google_language_code": "en-AU"},
    {"country": "Canada", "google_language_code": "en-CA"},
    {"country": "India", "google_language_code": "en-IN"}
]
```

### 方言・変種対応
```python
# 中国語の簡体字・繁体字対応
"Chinese Simplified": [
    {"country": "China", "google_language_code": "zh-CN"}
],
"Chinese Traditional": [
    {"country": "Taiwan", "google_language_code": "zh-TW"},
    {"country": "Hong Kong", "google_language_code": "zh-HK"}
]
```

## 統合利用

### VRCTでの利用例

```python
def get_supported_transcription_languages():
    """音声認識対応言語の取得"""
    languages = []
    for language, countries in transcription_lang.items():
        for country_data in countries:
            languages.append({
                "language": language,
                "country": country_data["country"],
                "display_name": f"{language} ({country_data['country']})",
                "code": country_data["google_language_code"]
            })
    return languages
```

### エラーハンドリング

```python
def get_language_code(language: str, country: str = None) -> str:
    """安全な言語コード取得"""
    try:
        countries = transcription_lang.get(language, [])
        if not countries:
            return "en-US"  # フォールバック
            
        if country:
            for country_data in countries:
                if country_data["country"] == country:
                    return country_data["google_language_code"]
                    
        # 国指定なしまたは見つからない場合は最初の項目を返す
        return countries[0]["google_language_code"]
    except (KeyError, IndexError):
        return "en-US"  # エラー時のフォールバック
```

## 拡張性

### 新言語の追加
```python
# 新しい言語の追加例
transcription_lang["Turkish"] = [
    {"country": "Turkey", "google_language_code": "tr-TR"}
]
```

### 新エンジンへの対応
```python
# 新しいエンジンのコードフィールドを追加
transcription_lang["English"][0]["azure_language_code"] = "en-US"
transcription_lang["English"][0]["aws_language_code"] = "en-US"
```

## 注意事項

- 言語コードは各エンジンの仕様に依存
- 新しいエンジン追加時は対応コードの追加が必要
- 地域固有の音声認識精度差に注意
- エンジンによってサポート言語が異なる場合がある

## 関連モジュール

- `transcription_transcriber.py`: 音声認識エンジン本体
- `translation_languages.py`: 翻訳エンジン言語マッピング
- `config.py`: 言語設定管理
- `controller.py`: 言語選択UI制御