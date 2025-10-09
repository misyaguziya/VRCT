## 翻訳モジュール (models.translation)

このドキュメントは `models/translation` 配下に対して行った最近の変更点、セットアップ手順、API の使い方、テスト方針、トラブルシュートをまとめたものです。

### 概要
- モジュールの責務: テキストの翻訳を行う高レベルの `Translator` クラス、言語コードのマッピング、CTranslate2 用の重み・トークナイザのダウンロード/検証ユーティリティを提供します。
- 変更点の狙い: 型注釈と docstring を追加し、`translation_utils.py` のダウンロード/検証ロジックをシンプルで堅牢な実装へ置換しました。これにより初回セットアップの手順が明確になります。

### 主な変更点（サマリ）
- `translation_translator.py`: 型注釈、docstring を追記。外部依存は存在するが、例外が発生してもモジュールが壊れないように保護されています。
- `translation_languages.py`: 言語コードマッピングの説明を追加。
- `translation_utils.py`: 重みファイルの検証（SHA-256 ハッシュ照合）、zip 展開、`transformers.AutoTokenizer` を使ったトークナイザ取得、ダウンロード進捗用のコールバックを備えた実装へ置換。

### インストール（依存関係）
必須ではないものが含まれます。開発・最小稼働に必要なパッケージはプロジェクト全体の要件に従ってください。

主に使うパッケージ:
- `requests` — ダウンロード処理
- `transformers` — トークナイザ取得（AutoTokenizer）
- `ctranslate2` — CTranslate2 を使う場合（ランタイムのみ、テストではモック推奨）

推奨インストール例（任意）:

```powershell
pip install requests transformers ctranslate2
```

DeepL や `translators` といった外部 API ラッパーはオプショナルです。CI やローカルテストではモックして動作確認してください。

### 初回セットアップ / 重みの準備
`translation_utils.py` に含まれるユーティリティ関数:

- `checkCTranslate2Weight(root: str, weight_type: str = "small") -> bool`
  - 指定した `root/weights/ctranslate2/<model_dir>` 以下に必要なファイルが存在し、既知のハッシュと一致するかをチェックします。

- `downloadCTranslate2Weight(root: str, weight_type: str = "small", callback: Optional[Callable[[float], None]] = None, end_callback: Optional[Callable[[], None]] = None) -> None`
  - 重みを ZIP 形式でダウンロードして展開します。
  - `callback(progress: float)` は 0.0〜1.0 の進捗通知に使えます。
  - `end_callback()` は処理完了時に呼び出されます。

- `downloadCTranslate2Tokenizer(path: str, weight_type: str = "small") -> None`
  - `transformers.AutoTokenizer.from_pretrained` を利用してトークナイザをダウンロード/キャッシュします（`cache_dir` に保存）。

呼び出し例（簡単）:

```python
from models.translation import translation_utils as tu

# ルートディレクトリ（プロジェクトルートなど）
root = "."
if not tu.checkCTranslate2Weight(root, "small"):
    tu.downloadCTranslate2Weight(root, "small", callback=lambda p: print(f"{p*100:.1f}%"))
    tu.downloadCTranslate2Tokenizer(root, "small")
```

注意: 大きなモデル（`large`）はダウンロードに時間とディスク容量を要します。

### API 使用例 (`Translator` の簡易例)

以下は `Translator` の想定されるシンプルな使い方です（実装は `translation_translator.py` を参照してください）。

```python
from models.translation.translation_translator import Translator

tr = Translator()
result = tr.translate("Hello", src_lang="en", target_lang="ja")
if result:
    print(result)
else:
    print("翻訳に失敗しました")
```

戻り値とエラー: 既存のコードベースとの互換性を重視し、失敗時は False を返すケースがあります。API 呼び出し前に戻り値の型を確認してください。

### テスト方針
- 外部サービス（DeepL、web 翻訳ラッパー、ctranslate2、transformers）はユニットテストでモックします。
- 推奨: `pytest` と `unittest.mock` を使い、`Translator.translate` の成功パス・失敗パスを検証するテストを追加してください。

簡単なテスト設計:
- 正常系: ctranslate2 経由の翻訳が正しく呼ばれる（モックで期待レスポンスを返す）
- フォールバック系: ctranslate2 が利用できない場合に別の翻訳経路を辿る（モック）

### トラブルシュート
- `ModuleNotFoundError` (例: `sudachidict_full`) — transliteration/別モジュールで必要な辞書が無い場合。該当パッケージのインストールか、当該機能を無効にしてください。
- ハッシュ不一致 — ダウンロード済みファイルの破損が疑われます。該当ファイルを削除して再ダウンロードしてください。
- `transformers` のトークナイザが取得できない場合、ネットワークやキャッシュ先の権限を確認してください。

### 変更履歴
- 2025-10-09: 型注釈と docstring の追加、`translation_utils.py` を再実装してダウンロード/検証ロジックを整理。

---
このドキュメントは簡潔な参照用です。必要なら実行例やさらに詳細なトラブルシュート手順（コマンド出力例、ログの取り方など）を追加します。
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
