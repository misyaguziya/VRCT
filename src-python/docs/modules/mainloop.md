## mainloop モジュール（src-python/mainloop.py）

このドキュメントは `mainloop.py` の実装と、最近行ったリファクタの概要をまとめます。`mainloop` は標準入力から JSON を受け取り、`controller` のメソッドにルーティングして標準出力へ JSON で応答を返す小さなメインループです。

重要な変更点:
- 2025-10-09: `Main` クラスに `start()` / `stop()` を追加し、受信スレッドとハンドラスレッドのライフサイクル管理を明示化しました。`queue.get(timeout=...)` による安全なシャットダウンを可能にしています。
- 2025-10-13: ハンドラの振る舞いを改善しました（マルチワーカー化とロック正規化）:
  - マルチワーカー化: ハンドラ処理はデフォルトで複数ワーカー（例: 3 本）で並列実行されます。これにより、1 つの重い処理が他のすべてのリクエストをブロックしてしまう問題を緩和します。
  - ロック正規化: `/set/enable/<feature>` と `/set/disable/<feature>` のような on/off ペアは同一のロックキーに正規化され、同一機能の on と off が同時に別スレッドで実行されることを防ぎます。これにより、遅い方の処理結果が後から上書きして最終状態が意図しないものになる不具合を防止します。

クラス: Main
- __init__(controller_instance: Controller, mapping_data: dict, worker_count: int = 3) -> None
  - `controller_instance`: `Controller` のインスタンス。
  - `mapping_data`: `mainloop` 内で使用する `mapping`（エンドポイント -> ハンドラ情報）辞書。
  - `worker_count`: ハンドラワーカー数（デフォルト 3）。実行環境に応じて調整可能です。
- start() -> None
  - 内部で `startReceiver()` と `startHandler()` を呼び、受信とハンドラのスレッド群を起動します。
- stop(wait: float = 2.0) -> None
  - シャットダウンシグナルをセットし、スレッド終了を待ちます（デフォルト 2 秒）。

動作の重要ポイント
- キュー運用: 受信した JSON は内部キューに入れられ、ハンドラワーカーが順次取り出して処理します。`queue.get(timeout=...)` を使っているため CPU 負荷を抑えつつ安全に停止できます。
- 同期応答設計: 各エンドポイントは基本的に呼び出し元に同期的に結果を返します（`handler` が戻り値としてステータスと結果を返す）。今回の変更でもこの設計は維持されています。
- 同一機能直列化: `/set/enable/X` と `/set/disable/X` のような on/off ペアは内部で同一の "ロックキー" に正規化され、同時に両方が実行されることを防ぎます。これにより、enable と disable が競合して遅い方が勝つ問題が解消されます。

使い方（例）:

```python
from mainloop import Main, mapping, controller

main_instance = Main(controller_instance=controller, mapping_data=mapping)
main_instance.start()

# 実行中に別スレッドや外部シグナルで停止させる
main_instance.stop()
```

確認手順（変更の検証）:
1. バックエンドを起動しておく。
2. UI／テストスクリプトから `/set/enable/translation` と `/set/disable/translation` を高速に交互送信する（数十〜数百ミリ秒間隔で連打）。
3. ログ（`printLog` 出力）を確認し、同一機能の複数実行が同時に走っていないこと、最終状態が遅い方に常に上書きされないことを確認する。
4. 必要に応じて `worker_count` を増減して挙動を確認する（PC リソースに応じて 1〜6 程度を推奨）。

注意点と推奨事項:
- `worker_count` を増やすと他のエンドポイントの並列処理性は上がりますが、controller/model 側で共有リソース（GPU メモリやデバイスハンドルなど）への同時アクセスが許可されていない場合は、controller 側で機能単位のロック（例: translation_lock）を追加してください。
- このドキュメントの変更は `mainloop` の外側から見える挙動（同期応答、ログ、ロックの方針）を説明するものです。controller 内の処理自体は引き続き同期的に実行されます。必要があれば、enable 系の重い処理を非同期化して完了通知をイベントで返す設計（UI 変更が必要）も検討してください。

変更履歴:
- 2025-10-09: start/stop ライフサイクル、タイムアウト付きキュー取得、エラー処理強化を追加。
- 2025-10-13: マルチワーカー化（デフォルト 3）と enable/disable のロック正規化を実装。これにより同一機能の on/off の同時実行を防止し、UI からの高速トグルで最終状態が遅い方に上書きされる問題を修正しました。
