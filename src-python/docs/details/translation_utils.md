# translation_utils.py - CTranslate2モデル管理ユーティリティ

## 概要

CTranslate2によるローカル機械翻訳モデルの自動ダウンロード、展開、管理を行うユーティリティモジュールです。複数のモデルサイズ（small/large）とプラットフォーム（CPU/CUDA）に対応し、モデルファイルの完全性チェックと自動修復機能を提供します。

## 主要機能

### モデル自動管理
- CTranslate2モデルの自動ダウンロード
- ZIP形式モデルの展開・配置
- モデルファイルの完全性検証
- 破損モデルの自動再取得

### マルチプラットフォーム対応
- CPU版・CUDA版の両対応
- 複数モデルサイズの管理
- プラットフォーム別最適化

## 定数・設定

### モデル定義

```python
# CTranslate2重みファイル情報
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

### 設定パラメータ
- **BASE_WEIGHTS_URL**: モデル配布ベースURL
- **LOCAL_WEIGHTS_DIR**: ローカル保存ディレクトリ
- **CHUNK_SIZE**: ダウンロード時のチャンクサイズ

## 主要機能

### モデルダウンロード

```python
def downloadCTranslate2Model(model_type: str, device: str = "cpu") -> bool:
    """CTranslate2モデルの自動ダウンロード"""
```

指定されたモデルタイプとデバイス用のモデルをダウンロード

#### パラメータ
- **model_type**: モデルサイズ（"small"/"large"）
- **device**: 計算デバイス（"cpu"/"cuda"）

#### 戻り値
- **bool**: ダウンロード成功可否

### モデル存在確認

```python
def checkCTranslate2ModelExists(model_type: str, device: str = "cpu") -> bool:
    """モデルファイルの存在確認"""
```

指定されたモデルがローカルに存在するかチェック

#### パラメータ
- **model_type**: 確認対象モデルタイプ
- **device**: 対象デバイス

#### 戻り値
- **bool**: モデル存在可否

### モデル完全性検証

```python
def validateCTranslate2Model(model_type: str, device: str = "cpu") -> bool:
    """モデルファイルの完全性検証"""  
```

ダウンロード済みモデルの整合性を確認

#### パラメータ
- **model_type**: 検証対象モデル
- **device**: 対象デバイス

#### 戻り値
- **bool**: モデル正常性

## 使用方法

### 基本的なモデル管理

```python
from models.translation.translation_utils import *

# smallモデル（CPU版）のダウンロード確認
if not checkCTranslate2ModelExists("small", "cpu"):
    print("smallモデルが見つかりません。ダウンロード中...")
    success = downloadCTranslate2Model("small", "cpu")
    
    if success:
        print("ダウンロード完了")
    else:
        print("ダウンロード失敗")
else:
    print("smallモデルは既に存在します")
```

### GPU用モデルの準備

```python
# CUDA版largeモデルのセットアップ
model_type = "large"
device = "cuda" 

# 既存モデルの確認
if checkCTranslate2ModelExists(model_type, device):
    # モデルの完全性検証
    if validateCTranslate2Model(model_type, device):
        print(f"{model_type}モデル（{device}版）準備完了")
    else:
        print("モデルが破損しています。再ダウンロード中...")
        # 破損モデルの再取得
        downloadCTranslate2Model(model_type, device)
else:
    # 新規ダウンロード
    print(f"{model_type}モデル（{device}版）をダウンロード中...")
    downloadCTranslate2Model(model_type, device)
```

### 自動モデル管理システム

```python
def ensureModelReady(model_type="small", device="cpu", max_retries=3):
    """モデルの準備を保証する関数"""
    
    for attempt in range(max_retries):
        print(f"モデル準備 試行 {attempt + 1}/{max_retries}")
        
        # モデル存在確認
        if not checkCTranslate2ModelExists(model_type, device):
            print("モデルが見つかりません。ダウンロード中...")
            if not downloadCTranslate2Model(model_type, device):
                print(f"ダウンロード失敗（試行 {attempt + 1}）")
                continue
        
        # モデル完全性確認
        if validateCTranslate2Model(model_type, device):
            print("モデル準備完了")
            return True
        else:
            print("モデルが破損しています。再取得中...")
            # 破損ファイルの削除（実装依存）
            # remove_corrupted_model(model_type, device)
            continue
    
    print("モデル準備に失敗しました")
    return False

# 使用例
if ensureModelReady("small", "cpu"):
    print("翻訳システム初期化可能")
else:
    print("翻訳システム初期化失敗")
```

### 複数モデルの一括管理

```python
def setupAllModels():
    """全モデルの一括セットアップ"""
    
    models = [
        ("small", "cpu"),
        ("small", "cuda"), 
        ("large", "cpu"),
        ("large", "cuda")
    ]
    
    results = {}
    
    for model_type, device in models:
        print(f"\n=== {model_type}モデル（{device}版）セットアップ ===")
        
        # デバイス利用可能性チェック（CUDA版の場合）
        if device == "cuda" and not torch.cuda.is_available():
            print("CUDA環境が利用できません。スキップします。")
            results[(model_type, device)] = False
            continue
        
        # モデル準備
        success = ensureModelReady(model_type, device)
        results[(model_type, device)] = success
        
        if success:
            print(f"✓ {model_type}（{device}版）準備完了")
        else:
            print(f"✗ {model_type}（{device}版）準備失敗")
    
    # 結果サマリー
    print("\n=== セットアップ結果 ===")
    for (model_type, device), success in results.items():
        status = "成功" if success else "失敗"
        print(f"{model_type}（{device}版）: {status}")
    
    return results

# 全モデルセットアップの実行
setupAllModels()
```

## モデル仕様

### smallモデル（m2m100_418m）

```python
model_info = {
    "name": "m2m100_418m",
    "size": "~400MB",
    "parameters": "418M", 
    "languages": "100言語",
    "tokenizer": "facebook/m2m100_418M",
    "memory_requirements": {
        "cpu": "~1GB RAM",
        "cuda": "~500MB VRAM"
    },
    "performance": {
        "speed": "高速",
        "quality": "良好"
    }
}
```

#### 特徴
- 高速処理に適している
- メモリ使用量が少ない
- リアルタイム翻訳に最適
- 100言語ペア対応

### largeモデル（m2m100_12b）

```python
model_info = {
    "name": "m2m100_12b", 
    "size": "~4.8GB",
    "parameters": "1.2B",
    "languages": "100言語",
    "tokenizer": "facebook/m2m100_1.2b", 
    "memory_requirements": {
        "cpu": "~6GB RAM",
        "cuda": "~3GB VRAM"
    },
    "performance": {
        "speed": "中程度",
        "quality": "高品質"
    }
}
```

#### 特徴
- 高品質翻訳が可能
- 大容量メモリが必要
- バッチ処理に適している
- 複雑な文章に対応

## ファイル構造

### ディレクトリレイアウト
```
weights/
└── ctranslate2/
    ├── m2m100_418m/          # smallモデル（CPU版）
    │   ├── model.bin
    │   ├── vocabulary.txt
    │   ├── config.json
    │   └── shared_vocabulary.txt
    ├── m2m100_418m_cuda/     # smallモデル（CUDA版）
    │   └── [同様のファイル構成]
    ├── m2m100_12b/           # largeモデル（CPU版）
    │   └── [同様のファイル構成]
    └── m2m100_12b_cuda/      # largeモデル（CUDA版）
        └── [同様のファイル構成]
```

### 必須ファイル
- `model.bin`: 変換済みモデルウェイト
- `vocabulary.txt`: 語彙ファイル
- `config.json`: モデル設定ファイル
- `shared_vocabulary.txt`: 共有語彙ファイル

## ダウンロード処理

### ネットワーク処理

```python
def downloadWithProgress(url: str, destination: str) -> bool:
    """進捗表示付きダウンロード"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(destination, 'wb') as file:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    file.write(chunk)
                    downloaded += len(chunk)
                    
                    # 進捗表示
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\rダウンロード進捗: {progress:.1f}%", end="")
        
        print(f"\nダウンロード完了: {destination}")
        return True
        
    except Exception as e:
        print(f"\nダウンロードエラー: {e}")
        return False
```

### 展開処理

```python
def extractZipModel(zip_path: str, extract_to: str) -> bool:
    """ZIPファイルの展開"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 展開先ディレクトリの作成
            os.makedirs(extract_to, exist_ok=True)
            
            # ファイル展開
            zip_ref.extractall(extract_to)
            
        print(f"展開完了: {extract_to}")
        
        # 元のZIPファイルを削除（オプション）
        os.remove(zip_path)
        print(f"一時ファイル削除: {zip_path}")
        
        return True
        
    except Exception as e:
        print(f"展開エラー: {e}")
        return False
```

## エラーハンドリング

### ネットワークエラー
- 接続タイムアウト
- ダウンロード中断
- サーバーエラー

### ファイルシステムエラー
- 容量不足
- 権限エラー
- ファイル破損

### リトライ機構

```python
def downloadWithRetry(url: str, destination: str, max_retries: int = 3) -> bool:
    """リトライ付きダウンロード"""
    
    for attempt in range(max_retries):
        print(f"ダウンロード試行 {attempt + 1}/{max_retries}")
        
        try:
            if downloadWithProgress(url, destination):
                return True
        except Exception as e:
            print(f"試行 {attempt + 1} 失敗: {e}")
            
            # 一時ファイルの清理
            if os.path.exists(destination):
                os.remove(destination)
            
            # 最後の試行でない場合は少し待機
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数バックオフ
    
    print("全ての試行が失敗しました")
    return False
```

## パフォーマンス最適化

### ダウンロード最適化
- チャンク単位での分割ダウンロード
- 進捗表示による体験向上
- 自動リトライによる信頼性確保

### ストレージ最適化
- 一時ファイルの自動削除
- 重複ファイルの検出・排除
- 容量効率的なファイル管理

### メモリ最適化
- ストリーミングダウンロード
- 大容量ファイル対応
- メモリ使用量の制御

## 依存関係

### 必須依存関係
- `requests`: HTTPダウンロード
- `zipfile`: アーカイブ展開
- `os`: ファイルシステム操作
- `pathlib`: パス操作

### オプション依存関係
- `tqdm`: 進捗バー表示（実装による）
- `hashlib`: ファイル整合性検証（実装による）

## 注意事項

- 初回ダウンロードは時間がかかる（モデルサイズ依存）
- 十分なストレージ容量を確保
- ネットワーク環境によってダウンロード速度が変動
- CUDA版は対応GPU環境が必要
- モデルファイルのバックアップ推奨

## 関連モジュール

- `translation_translator.py`: モデル利用クラス
- `translation_languages.py`: 言語コード管理
- `config.py`: 設定管理
- `utils.py`: 共通ユーティリティ
- `device_manager.py`: デバイス管理