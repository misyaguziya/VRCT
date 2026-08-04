# translation_utils.py - CTranslate2モデル管理ユーティリティ

## 概要

CTranslate2によるローカル機械翻訳モデル（オンライン翻訳のフォールバック）の自動ダウンロード・存在確認・トークナイザー取得を行うユーティリティモジュールです。モデルは Hugging Face Hub 上の int8 量子化済み CTranslate2 変換済みモデルをそのまま利用し、ZIP展開のような追加変換は行いません。

## モデル定義

```python
ctranslate2_weights = {
    "m2m100_418M-ct2-int8": {
        "hf_repo": "jncraton/m2m100_418M-ct2-int8",
        "directory_name": "m2m100_418M-ct2-int8",
        "tokenizer": "facebook/m2m100_418M",
    },
    "m2m100_1.2B-ct2-int8": {
        "hf_repo": "jncraton/m2m100_1.2B-ct2-int8",
        "directory_name": "m2m100_1.2B-ct2-int8",
        "tokenizer": "facebook/m2m100_1.2B",
    },
    "nllb-200-distilled-600M-ct2-int8": {
        "hf_repo": "JustFrederik/nllb-200-distilled-600M-ct2-int8",
        "directory_name": "nllb-200-distilled-600M-ct2-int8",
        "tokenizer": "facebook/nllb-200-distilled-600M",
    },
    "nllb-200-distilled-1.3B-ct2-int8": {
        "hf_repo": "OpenNMT/nllb-200-distilled-1.3B-ct2-int8",
        "directory_name": "nllb-200-distilled-1.3B-ct2-int8",
        "tokenizer": "facebook/nllb-200-distilled-1.3B",
    },
    "nllb-200-3.3B-ct2-int8": {
        "hf_repo": "OpenNMT/nllb-200-3.3B-ct2-int8",
        "directory_name": "nllb-200-3.3B-ct2-int8",
        "tokenizer": "facebook/nllb-200-3.3B",
    },
}
```

`weight_type`（辞書のキー）は `config.CTRANSLATE2_WEIGHT_TYPE` に保存される値、かつ UI（`SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST` 経由）の選択肢と一致します。新しいCTranslate2モデルを追加する場合は、この辞書にエントリを追加し、`translation_settings/languages/languages.yml` の `CTranslate2` セクションに同名キーで言語マッピングを追加します（NLLB系モデルは Flores-200 言語コードを共有しているため `&nllb_langs` / `*nllb_langs` の YAML アンカーを再利用できます）。

デフォルトモデル（`config.py` の `CTRANSLATE2_WEIGHT_TYPE` 初期値）は `nllb-200-distilled-600M-ct2-int8`（新規インストール時）。m2m100系はレガシー選択肢として引き続き利用可能です。

## 主要関数

### `backwardCompatibleRenameWeightsDir(root: str) -> None`
旧バージョンで使われていたディレクトリ名（`m2m100_418M`, `m2m100_12b`）を現行の `directory_name`（`m2m100_418M-ct2-int8` 等）へリネームする後方互換処理。存在しない場合は何もしない。

### `checkCTranslate2Weight(root: str, weight_type: str = "m2m100_418M-ct2-int8") -> bool`
実際に `ctranslate2.Translator(path, compute_type=...)` でロードできるかどうかでモデルの存在・健全性を判定する（ファイル一覧の突合ではなく、ロード可否そのものをチェックする）。

### `downloadCTranslate2Weight(root, weight_type, callback=None, end_callback=None) -> None`
1. `huggingface_hub.list_repo_files` で対象リポジトリのファイル一覧を取得
2. `checkCTranslate2Weight` で既にロード可能なら即終了
3. `weights/ctranslate2/<directory_name>/` を作成し、各ファイルを `hf_hub_url` 経由で `requests.get(stream=True)` によりチャンクダウンロード
4. `model.bin` のダウンロードのみ `callback(progress: float)` で進捗を通知（他ファイルは進捗コールバックなし）
5. 完了後 `end_callback()` を呼ぶ

ネットワークエラーは `errorLogging()` で記録され、例外は再送出しない（既存の防御的スタイルに合わせる）。

### `downloadCTranslate2Tokenizer(path: str, weight_type: str = "m2m100_418M-ct2-int8") -> None`
`transformers.AutoTokenizer.from_pretrained(tokenizer, cache_dir=...)` でトークナイザーを `weights/ctranslate2/<directory_name>/tokenizer/` にダウンロード・キャッシュする。失敗時は `errorLogging()` の後、カレントディレクトリ相対パス（`./weights/...`）にフォールバックして再試行する。

## ファイル構造

```
weights/
└── ctranslate2/
    ├── m2m100_418M-ct2-int8/
    │   ├── model.bin
    │   ├── (ctranslate2変換済みモデルの各種ファイル)
    │   └── tokenizer/            # AutoTokenizer のキャッシュ
    ├── nllb-200-distilled-600M-ct2-int8/
    │   ├── model.bin
    │   └── tokenizer/
    └── ...（weight_typeごとに同様のディレクトリ）
```

## 依存関係
- `ctranslate2`: モデルロード・推論エンジン
- `transformers`: `AutoTokenizer`（HFトークナイザーのロード）
- `huggingface_hub`: リポジトリのファイル一覧取得・URL解決
- `requests`: チャンク単位のファイルダウンロード
- `yaml`: 言語マッピング（`loadTranslatePromptConfig` 等）読み込み

## 関連モジュール
- `translation_translator.py`: `Translator.changeCTranslate2Model()` / `translateCTranslate2()` からこのモジュールの `ctranslate2_weights` を参照してモデルロード・推論を行う
- `translation_languages.py` / `translation_settings/languages/languages.yml`: `weight_type` ごとの言語コードマッピング（`CTranslate2` セクション）
- `config.py`: `CTRANSLATE2_WEIGHT_TYPE` / `SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST` / `SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT`（ダウンロード済みフラグ管理）
- `controller.py`: `DownloadCTranslate2` によるダウンロードフロー制御、VRAM不足検知時のCTranslate2への自動切り替え（`changeToCTranslate2Process()`）
