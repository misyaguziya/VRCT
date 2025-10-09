# models/watchdog — 詳細設計

目的: 外部（Process 管理側）へ定期的に "生存" を知らせるために使う軽量ウォッチドッグ。

設計:
- class Watchdog(timeout:int=60, interval:int=20)
  - feed(): 最終フィード時刻を更新
  - setCallback(callback): タイムアウト時に呼ぶコールバックを登録
  - start(): 現状は単純で、呼び出し側がループ中に start() を呼ぶかたち。実装は簡易（将来的にスレッド化推奨）

注意:
- 現行実装は非常にシンプルで、長時間のブロッキングやスレッド運用の見直しが必要になり得る。
