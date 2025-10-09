# VRCT — ドキュメント

このドキュメントセットは、VRCT プロジェクト（`src-python`）に含まれる実装の仕様書 / 設計書 / 詳細設計書です。

目的
- ソースコード構造、モジュール間データフロー、API エンドポイント、設定、実行手順、トラブルシュートを網羅して開発・運用の参照を容易にする。

対象
- `utils.py`, `model.py`, `controller.py`, `mainloop.py`, `device_manager.py`, `config.py` および `models/` 以下の全モジュール。

ドキュメント構成（主要ファイル）
- `architecture.md` — アーキテクチャ概観
- `modules/`  — 各モジュールごとの詳細設計（個別ファイル）
- `api.md` — 外部/内部向け API エンドポイント マッピング（`mainloop.py` の `mapping` / `run_mapping` に準拠）
- `runtime.md` — 実行／セットアップ手順、依存関係
- `diagrams.md` — システム図（Mermaid とテキスト両方）
- `CODING_RULES.md` — プロジェクト固有のコーディング規約（命名・型方針・lint/mypy 方針 等）
- `CHANGELOG.md` — 変更履歴