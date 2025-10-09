# VRCT backend — コーディングルール

目的:
- 可読性と保守性を保ちながら既存スタイルを尊重する。
- 漸進的に型注釈を導入し、mypy と ruff のチェックに合わせる。
- 自動化（CI / pre-commit）へ導出しやすくする。

注意: 既存の命名・構造（関数名・クラス名・変数名・run mapping のキー等）はコード上の互換性のためそのまま維持します。以下は新規実装やリファクタ時に従うべきルールです。

## 目次
- 命名規則
- モジュール・パッケージ構成
- インポート
- 型注釈と mypy 方針
- ドキュメンテーション / docstrings
- エラーハンドリングとロギング
- 非同期 / スレッド / キューの扱い
- テストと CI
- リファクタ・互換性の観点

---

## 命名規則
- モジュール名: 小文字、アンダースコアで区切る（例: `overlay_utils.py`）。既存ファイルに従う。
- パッケージ名: 小文字（`models`, `websocket` など）。
- クラス名: CapWords (PascalCase)。既存クラス（`Controller`, `Model`, `Overlay`）に従う。
- 関数・メソッド名: snake_case。
- 変数名: snake_case。短い一時変数は `i`, `j`, `buf` 等の伝統的な省略形を可とするが、意味ある名前を優先する。
- 定数: UPPER_SNAKE_CASE（`config.py` の定数に合わせる）。
- run_mapping のキー: 現在は短い key（例: `transcription_mic`）を内部で使い `run_mapping` に `/run/...` を置いている。この慣習は維持する。Controller 内で `self.run_mapping[...]` を直接参照する実装は許容される。

例: `selected_translation_compute_device` は内部 key、`/run/selected_translation_compute_device` が外部イベント名である点を区別して使う。

## モジュール・パッケージ構成
- 各サブ領域（ocr, overlay, transcription, translation, websocket 等）は `models/` 下に整理済みのため、同様の粒度で新機能は追加する。
- パッケージは必ず `__init__.py` を置く（static analysis / mypy のため）。空の `__init__.py` でも可。これにより相対インポートが安定する。

## インポート
- 標準ライブラリ、サードパーティ、ローカルの順でインポートをまとめる。
- ローカルモジュールを参照する場合は相対 import を使ってもよいが、プロジェクト全体を PYTHONPATH に入れてテスト／静的解析できるようにすること。
- 例:
```
import os
import json

import numpy as np

from . import overlay_utils
```

## 型注釈と mypy 方針
- 戦略: Relax + incremental annotations（漸進的型付け）。以下を守る。
  - 新規コードは可能な限り型注釈を追加する（関数シグネチャ・返り値）。
  - 既存の大きな関数は段階的に注釈する。まずモジュール境界（public API）のシグネチャに注釈を入れる。内部の細かい変数は後回し。
  - CI では初期段階で mypy を `--ignore-missing-imports --allow-untyped-defs --allow-redefinition` のように緩めて実行する。段階的に `--check-untyped-defs` を有効化していく。
  - 型の `Any` を多用しない。どうしても必要な場合は `# type: ignore[assignment]` を付けて理由をコメントに残す。

## docstrings / コメント
- 重要な public 関数・メソッドとクラスに短い docstring を追加する（目的・引数・返り値の要約）。Google/Numpy スタイルのどちらかに統一する必要はないが、プロジェクト内で混乱しないよう短く統一すること。
- 実装トリッキーな箇所には `# NOTE:` や `# FIXME:` コメントを残し、必要なら issue を紐付ける（例: `# NOTE: keep in sync with mainloop.run_mapping`）。

## エラーハンドリングとロギング
- 例外をキャッチするときは有用なコンテキストをログに残す（`errorLogging()` のようなユーティリティを使う）。
- broad except: を使う場合は最低限 `errorLogging()` を呼び、必要なら `raise` して上位へ伝播する。

## 非同期 / スレッド / キューの扱い
- スレッドは `threading.Thread` を使っている箇所があるため、スレッド間通信は `queue.Queue` ベースで実装すること。
- スレッドを生成する関数は `start_` プレフィックス（例: `start_transcription_thread`）のように命名すると分かりやすい。

## テスト・CI
- まずは軽量な CI ワークフローを入れる:
  - ruff check
  - mypy (relaxed)
  - 自動テスト（将来的に pytest を追加）
- pre-commit フックの導入を推奨: ruff auto-fix と isort (import 整理) を採用できる。

## リファクタ・互換性
- 既存 public API（stdin/stdout の endpoint 仕様や `run_mapping` のキー、Controller のメソッド名）は後方互換を優先する。変更が必要な場合は CHANGELOG に明示する。

## 小さなコーディング規約チェックリスト（PR テンプレ）
- 新しい public メソッドには docstring を付けたか
- 既存命名規則に従っているか（snake_case / PascalCase / UPPER_SNAKE_CASE）
- 型アノテーションをシグネチャに追加したか（可能な限り）
- 直接 stdout に JSON を print する箇所は `printResponse` 等ユーティリティ経由か確認する

---

このドキュメントは現状のスタイルを尊重して最小限の規則を与えることを目的としています。次のステップを希望する場合:
- CI に ruff/mypy を組み込む PR を作成
- pre-commit 用の設定ファイル（`.pre-commit-config.yaml`）を追加して自動整形を導入
- 型注釈・テストのためのタスク分割（優先順位をつけた TODO）

要望があれば、これをベースに `.pre-commit-config.yaml`、`pyproject.toml` の ruff 設定、あるいは CI ワークフローの雛形（GitHub Actions）を作成します。

## Copilot と共同作業するための具体例とテンプレート
以下は Copilot に推奨プロンプトを投げやすく、また PR 作成時に便利なテンプレート類です。コピー＆ペーストして使用してください。

### 関数テンプレート（型注釈 + docstring）
```python
from typing import Any, Dict, Optional

def example_handler(endpoint: str, data: Any) -> Dict[str, Any]:
    """Handle an example endpoint.

    Args:
        endpoint: incoming endpoint string (e.g. '/get/data/version')
        data: request payload (None for many GETs)

    Returns:
        A dict suitable for printResponse(status, endpoint, result)
    """
    # implementation...
    result = {"status": 200, "endpoint": endpoint, "result": data}
    return result
```

### Controller の run 発行パターン（推奨）
Controller 内で run を呼ぶときは `self.run(self.run_mapping["key"], payload)` の形を維持してください。Copilot に尋ねるときは「この run key に対応する payload の形は？」と聞くとペイロード例を生成しやすいです。

### Docstring 例（Google スタイル）
```python
def set_selected_tab_no(tab_no: int) -> Dict[str, Any]:
    """Set the current tab.

    Args:
        tab_no: index of tab to select

    Returns:
        A response dict with status and new tab number
    """
    ...
```

### PR チェックリスト（拡張版）
- コーディング規則に従っているか
- 新しい public API の docstring があるか
- 型注釈を最小限追加しているか（特に関数シグネチャ）
- ruff check が通るか
- mypy（relaxed）で重大な型エラーが出ていないか
- docs (必要箇所) を更新したか（API 変更があれば）

### 推奨 `.pre-commit-config.yaml`（例）
```yaml
repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.14.0
    hooks:
      - id: ruff
        args: ["--fix"]
  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.18.2
    hooks:
      - id: mypy
        args: ["--ignore-missing-imports", "--allow-untyped-defs", "--allow-redefinition"]
```

### 推奨 ruff 設定（pyproject.toml への最小設定例）
```toml
[tool.ruff]
line-length = 88
extend-ignore = ["E203"]
select = ["E", "F", "W", "C90"]
```

---

更新が必要なら私が `.pre-commit-config.yaml`、`pyproject.toml`、および CI ワークフロー (GitHub Actions) の雛形を作成してコミットまでできます。どれを優先しますか？
