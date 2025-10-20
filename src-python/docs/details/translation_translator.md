# translation_translator.py - 翻訳エンジン統合クラス

## 概要

複数の翻訳エンジンを統合管理する高レベル翻訳インターフェースです。DeepL、Google、Bing、Papago、CTranslate2などの多様な翻訳サービスを統一的に扱い、エラー時の自動フォールバック機能と認証管理を提供します。

## 主要機能

### 多エンジン統合
- DeepL（無料版・API版）
- Google Translate（Webスクレイピング）
- Microsoft Translator（Bing）
- Papago Translator
- CTranslate2（ローカル翻訳）

### 統一インターフェース
- エンジン依存を隠蔽した単一の翻訳メソッド
- 自動エラーハンドリング・フォールバック
- 認証情報の統合管理

### オフライン翻訳対応
- CTranslate2による完全オフライン翻訳
- 複数モデルサイズ（small/large）対応
- CUDA高速化サポート

## クラス構造

### Translator クラス
```python
class Translator:
    def __init__(self) -> None:
        self.deepl_client: Optional[DeepLClient] = None
        self.ctranslate2_translator: Any = None
        self.ctranslate2_tokenizer: Any = None
        self.is_loaded_ctranslate2_model: bool = False
        self.is_changed_translator_parameters: bool = False
        self.is_enable_translators: bool = ENABLE_TRANSLATORS
```

翻訳機能の中核クラス

#### 属性
- **deepl_client**: DeepL APIクライアント
- **ctranslate2_translator**: ローカル翻訳モデル
- **ctranslate2_tokenizer**: CTranslate2トークナイザー
- **is_loaded_ctranslate2_model**: ローカルモデル読み込み状態
- **is_enable_translators**: Web翻訳サービス利用可能フラグ

## 主要メソッド

### 翻訳実行

```python
translate(translator_name: str, source_language: str, target_language: str, 
          target_country: str, message: str) -> Any
```

統一翻訳インターフェース

#### パラメータ
- **translator_name**: 翻訳エンジン名（"DeepL", "Google", "CTranslate2"等）
- **source_language**: 送信元言語
- **target_language**: 送信先言語
- **target_country**: 送信先国・地域
- **message**: 翻訳対象テキスト

#### 戻り値
- **str**: 翻訳結果（成功時）
- **False**: 翻訳失敗時

### DeepL認証管理

```python
authenticationDeepLAuthKey(authkey: str) -> bool
```

DeepL APIキーの認証と設定

#### パラメータ
- **authkey**: DeepL APIキー

#### 戻り値
- **bool**: 認証成功可否

### CTranslate2管理

```python
changeCTranslate2Model(path: str, model_type: str, device: str = "cpu",
                      device_index: int = 0, compute_type: str = "auto") -> None
```

ローカル翻訳モデルの読み込み・変更

#### パラメータ
- **path**: モデルファイルのベースパス
- **model_type**: モデルサイズ（"small"/"large"）
- **device**: 計算デバイス（"cpu"/"cuda"）
- **device_index**: デバイスインデックス
- **compute_type**: 計算精度タイプ

### 状態管理

```python
isLoadedCTranslate2Model() -> bool
```

CTranslate2モデルの読み込み状態確認

```python
isChangedTranslatorParameters() -> bool
setChangedTranslatorParameters(is_changed: bool) -> None
```

翻訳設定変更フラグの管理

## 使用方法

### 基本的な翻訳

```python
from models.translation.translation_translator import Translator

# 翻訳器の初期化
translator = Translator()

# Google翻訳の使用
result = translator.translate(
    translator_name="Google",
    source_language="Japanese",
    target_language="English", 
    target_country="United States",
    message="こんにちは、世界！"
)

if result != False:
    print(f"翻訳結果: {result}")  # "Hello, world!"
else:
    print("翻訳に失敗しました")
```

### DeepL API使用

```python
# DeepL APIキーの設定
api_key = "your-deepl-api-key"
auth_success = translator.authenticationDeepLAuthKey(api_key)

if auth_success:
    print("DeepL API認証成功")
    
    # DeepL APIで翻訳
    result = translator.translate(
        translator_name="DeepL_API",
        source_language="English",
        target_language="Japanese",
        target_country="Japan", 
        message="Hello, world!"
    )
    print(f"DeepL翻訳: {result}")
else:
    print("DeepL API認証失敗")
```

### ローカル翻訳（CTranslate2）の使用

```python
# ローカルモデルの読み込み
translator.changeCTranslate2Model(
    path=".",                    # アプリケーションルート
    model_type="small",          # smallモデル使用
    device="cuda",               # GPU使用
    device_index=0,
    compute_type="float16"       # 半精度で高速化
)

# モデル読み込み確認
if translator.isLoadedCTranslate2Model():
    print("CTranslate2モデル読み込み完了")
    
    # ローカル翻訳実行
    result = translator.translate(
        translator_name="CTranslate2",
        source_language="Japanese",
        target_language="English",
        target_country="United States",
        message="機械翻訳のテストです"
    )
    print(f"ローカル翻訳: {result}")
else:
    print("CTranslate2モデル読み込み失敗")
```

### エラーハンドリング付きの翻訳

```python
def safe_translate(translator, message, source_lang="Japanese", target_lang="English"):
    """安全な翻訳処理"""
    # 翻訳エンジンの優先順位
    engines = ["DeepL_API", "DeepL", "Google", "CTranslate2"]
    
    for engine in engines:
        try:
            result = translator.translate(
                translator_name=engine,
                source_language=source_lang,
                target_language=target_lang,
                target_country="United States",
                message=message
            )
            
            if result != False:
                print(f"{engine}で翻訳成功: {result}")
                return result
            else:
                print(f"{engine}翻訳失敗、次のエンジンを試行")
                
        except Exception as e:
            print(f"{engine}でエラー: {e}")
            continue
    
    print("全ての翻訳エンジンで失敗")
    return None

# 使用例
result = safe_translate(translator, "こんにちは")
```

### 翻訳設定の管理

```python
# 設定変更フラグの確認
if translator.isChangedTranslatorParameters():
    print("翻訳設定が変更されています")
    
    # 設定変更の適用（例：モデル再読み込み）
    translator.changeCTranslate2Model(".", "small", "cpu")
    
    # フラグのリセット
    translator.setChangedTranslatorParameters(False)
```

## 翻訳エンジン比較

### DeepL API（有料）
- **精度**: 最高レベル
- **速度**: 高速
- **制限**: API使用料、月間制限
- **対応**: 26言語、地域別対応

### DeepL（無料）
- **精度**: 高品質
- **速度**: 中程度
- **制限**: 月間使用量制限、文字数制限
- **対応**: 26言語

### Google Translate
- **精度**: 良好
- **速度**: 高速
- **制限**: アクセス頻度制限
- **対応**: 100+言語

### CTranslate2（ローカル）
- **精度**: 中〜高（モデル依存）
- **速度**: 高速（GPU使用時）
- **制限**: なし（オフライン）
- **対応**: 主要言語ペア

### その他（Bing, Papago等）
- **精度**: 中程度
- **速度**: 中程度
- **制限**: サービス依存
- **対応**: サービス固有

## CTranslate2詳細

### 対応モデル
```python
ctranslate2_weights = {
    "small": {
        "url": "m2m100_418m.zip",
        "directory_name": "m2m100_418m", 
        "tokenizer": "facebook/m2m100_418M"
    },
    "large": {
        "url": "m2m100_12b.zip", 
        "directory_name": "m2m100_12b",
        "tokenizer": "facebook/m2m100_1.2b"
    }
}
```

### パフォーマンス特性

#### small モデル
- **サイズ**: ~400MB
- **メモリ**: ~1GB RAM
- **VRAM**: ~500MB（CUDA使用時）
- **速度**: 高速
- **精度**: 良好

#### large モデル
- **サイズ**: ~4.8GB
- **メモリ**: ~6GB RAM  
- **VRAM**: ~3GB（CUDA使用時）
- **速度**: 中程度
- **精度**: 高品質

### 計算タイプ設定
```python
# CPU使用時
compute_type = "int8"          # 速度重視

# CUDA使用時
compute_type = "float16"       # バランス重視
compute_type = "int8_float16"  # メモリ効率重視
```

## エラーハンドリング

### ネットワークエラー
- 接続タイムアウト
- API制限超過
- サービス一時停止

### 認証エラー
- 無効なAPIキー
- 期限切れアカウント
- 使用量上限到達

### モデルエラー
- ファイル破損
- VRAM不足
- 非対応言語ペア

### 対応策
```python
def robust_translation(translator, message, source_lang, target_lang):
    """堅牢な翻訳処理"""
    # オンライン翻訳を先に試行
    online_engines = ["DeepL_API", "DeepL", "Google"]
    
    for engine in online_engines:
        try:
            result = translator.translate(engine, source_lang, target_lang, "", message)
            if result != False:
                return result
        except Exception as e:
            print(f"{engine}エラー: {e}")
            continue
    
    # オンライン翻訳が全て失敗した場合、ローカル翻訳にフォールバック
    try:
        if not translator.isLoadedCTranslate2Model():
            translator.changeCTranslate2Model(".", "small", "cpu")
            
        result = translator.translate("CTranslate2", source_lang, target_lang, "", message)
        if result != False:
            return result
    except Exception as e:
        print(f"ローカル翻訳エラー: {e}")
    
    return "翻訳に失敗しました"
```

## 依存関係

### 必須依存関係
- `translation_languages`: 言語コード管理
- `translation_utils`: CTranslate2ユーティリティ
- `utils`: エラーログ、計算デバイス管理

### オプション依存関係
- `deepl`: DeepL APIライブラリ
- `translators`: Web翻訳サービスライブラリ
- `ctranslate2`: ローカル翻訳エンジン
- `transformers`: トークナイザー

## 設定要件

### 環境変数
- `DEEPL_AUTH_KEY`: DeepL APIキー（オプション）

### ファイル配置
```
root/
└── weights/
    └── ctranslate2/
        ├── m2m100_418m/     # smallモデル
        └── m2m100_12b/      # largeモデル
```

## 注意事項

- Web翻訳サービスは利用制限に注意
- CTranslate2の初回読み込みは時間がかかる
- GPU使用時はVRAM消費量に注意
- API認証情報の適切な管理が必要
- 長文翻訳時は分割処理を推奨

## 関連モジュール

- `translation_languages.py`: 言語コードマッピング
- `translation_utils.py`: CTranslate2ユーティリティ
- `config.py`: 翻訳設定管理
- `model.py`: 翻訳機能統合
- `controller.py`: 翻訳制御インターフェース

## 最近の更新 (2025-10-20)

### 新規ローカル LLM エンジン追加

LMStudio / Ollama を翻訳エンジンとして追加。接続確認後にモデルリスト (`SELECTABLE_LMSTUDIO_MODEL_LIST` / `SELECTABLE_OLLAMA_MODEL_LIST`) を取得し、未選択なら先頭モデルを自動選択 (`SELECTED_LMSTUDIO_MODEL` / `SELECTED_OLLAMA_MODEL`)。現時点では CTranslate2 と同様にローカル動作を想定し、翻訳関数側は将来の統合（温度等パラメータ）に備えて抽象化維持。

### モデル選択プロパティ名称統一

Plamo / Gemini / OpenAI の選択モデルプロパティを `SELECTED_*` 形式へ変更。旧名称 (`PLAMO_MODEL` / `GEMINI_MODEL` / `OPENAI_MODEL`) は利用停止。自動認証後のモデルリスト更新ロジックで未選択時に先頭補完を行う。

### OpenAI / Gemini / Plamo 認証後のモデルリスト自動更新

Auth設定メソッド完了時に `SELECTABLE_*_MODEL_LIST` を再取得し不足時は UI へ push。OpenAI はキー設定直後に最新モデルリストを反映し高速化。Gemini / Plamo も同様に `updateTranslator*Client()` 呼び出しでクライアント再生成。

### CTranslate2 言語ネスト化対応

`translation_lang["CTranslate2"][weight_type]["source"|"target"]` へ構造変更。`CTRANSLATE2_WEIGHT_TYPE` により重みタイプ別の言語集合を参照。Translator 内では `translator_name == "CTranslate2"` の分岐で weight_type を参照して言語判定を行う実装に変更。

### YAML 言語マッピング導入

外部ファイル `languages.yml` を読み込んで翻訳エンジン別対応言語を動的拡張。新言語追加は YAML 編集のみで実現（コード再デプロイ不要）。読み込み失敗時は空辞書でフォールバックし既存ハードコードを保持。

### VRAM エラー検知とフォールバック

DeepL / Plamo / Gemini / OpenAI 実行時の VRAM 不足検知で自動的に CTranslate2 へ切替し翻訳を停止 (`ENABLE_TRANSLATION=False`)。ユーザー通知後は再度有効化要求時に再初期化を試行。安定性向上のためログへ VRAM エラー詳細を記録。

### トークナイザーパス修正

CTranslate2 トークナイザーのダウンロード処理で保存ディレクトリ作成とパス使用順序不整合を修正。これにより初回起動時の失敗率低下。

### 全言語ペア包括テスト導入

`backend_test.py` にて `test_translate_all_language_pairs()` を追加。複数エンジン・全言語ペアを列挙実行し `translation_test_results.json` を生成。失敗ペアの早期検出と YAML 追加言語検証に活用。

### 影響

| 項目 | 内容 |
|------|------|
| ローカルLLM | オフライン翻訳候補拡充 (LMStudio/Ollama) |
| プロパティ統一 | SELECTED_* 命名で一貫性と保守性向上 |
| CTranslate2構造 | 重みタイプ毎に最適言語集合参照可能 |
| YAML外部化 | 言語追加/削除が設定ファイル編集のみで完結 |
| VRAM検知 | エラー時自動停止 + 軽量エンジン切替で安定性向上 |
| Tokenizer修正 | 初回セットアップ失敗減少 |
| 包括テスト | 言語組合せの網羅的品質担保 |
