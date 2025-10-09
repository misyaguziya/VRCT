## mainloop モジュール（src-python/mainloop.py）

このドキュメントは `mainloop.py` の実装と、2025-10-09 に行ったリファクタの概要をまとめます。`mainloop` は標準入力から JSON を受け取り、`controller` のメソッドにルーティングして標準出力へ JSON で応答を返す小さなメインループです。

重要な変更点（2025-10-09）:
- `Main` クラスに `start()` / `stop()` を追加し、受信スレッドとハンドラスレッドのライフサイクル管理を明示化しました。
- `queue.get(timeout=...)` を使ってポーリング負荷を下げ、`_stop_event` による安全なシャットダウンを可能にしました。
- 標準入力の JSON パースエラーと一般例外のハンドリングを強化しました。
- `startReceiver()` / `startHandler()` を使って個別にスレッドを起動することも可能です。

クラス: Main
- __init__(controller_instance: Controller, mapping_data: dict) -> None
  - `controller_instance`: `Controller` のインスタンス。
  - `mapping_data`: `mainloop` 内で使用する `mapping`（エンドポイント -> ハンドラ情報）辞書。
- start() -> None
  - 内部で `startReceiver()` と `startHandler()` を呼び、両スレッドを起動します。
- stop(wait: float = 2.0) -> None
  - シャットダウンシグナルをセットし、スレッド終了を待ちます（デフォルト 2 秒）。

使い方（例）:

```python
from mainloop import Main, mapping, controller

main_instance = Main(controller_instance=controller, mapping_data=mapping)
main_instance.start()

# 実行中に別スレッドや外部シグナルで停止させる
main_instance.stop()
```

既存のスクリプト互換性:
- 既存コードが `startReceiver()` や `startHandler()` を直接呼んでいる場合、そのまま動作します。`start()` / `stop()` を使うと簡潔に起動 / 停止が行えます。

注意点と推奨事項:
- `stop()` を呼ばないとバックグラウンドスレッドがデーモンであってもプロセス終了前にクリーンアップが不十分になる場合があります。アプリ終了時は `stop()` を呼ぶことを推奨します。
- `queue.get(timeout=...)` を使うことで即時性よりも CPU 使用量の低減を優先しています。非常に低レイテンシが必要なケースでは timeout を短くしてください（ただし CPU 使用量に注意）。

スクリプト連携:
- `mainloop.mapping` と `mainloop.run_mapping` は `scripts/print_mapping.py` などのツールから直接参照されます。mapping のキー/値を変更する場合はそれらのスクリプトも確認してください。

変更履歴:
- 2025-10-09: start/stop ライフサイクル、タイムアウト付きキュー取得、エラー処理強化を追加。
