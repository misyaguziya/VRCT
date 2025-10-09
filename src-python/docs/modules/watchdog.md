# models/watchdog — 詳細設計

目的: 外部（Process 管理側）へ定期的に "生存" を知らせるために使う軽量ウォッチドッグ。

設計:
- class Watchdog(timeout: int = 60, interval: int = 20)
  - feed(): 最終フィード時刻を更新
  - setCallback(callback): タイムアウト時に呼ぶコールバックを登録（zero-arg を想定）
  - start(): 単一チェックを行い、`interval` 秒の sleep を行う（継続監視は呼び出し側でループまたはスレッド化）

注意:
- 現行実装は非常にシンプルで、長時間のブロッキングやスレッド運用の見直しが必要になり得る。

変更点（実装に入れた改善）:
- コールバック属性を初期化しておくことで AttributeError を防止
- コールバック呼び出し内の例外はウォッチドッグ本体に影響を与えないよう try/except で保護
- メソッドに型注釈と docstring を追加

短い使用例（ポーリング方式）:

```py
import time
from models.watchdog.watchdog import Watchdog

def on_timeout():
    print('watchdog timed out')

wd = Watchdog(timeout=5, interval=1)
wd.setCallback(on_timeout)

# 別スレッドにせず、単純なループでポーリングする例
while True:
    wd.start()  # ここで timeout をチェックし、必要なら callback を呼ぶ
    # アプリケーションの他処理...
    time.sleep(0.5)

    # 正常時に feed を呼ぶ例
    # wd.feed()
```

使用例（スレッド化ヘルパを用意するアプローチ）:

```py
import time
from threading import Thread, Event
from models.watchdog.watchdog import Watchdog

stop_event = Event()

def run_watchdog(wd: Watchdog, stop_event: Event):
    # シンプルなバックグラウンド実行ループ（安全な停止用フラグ付き）
    while not stop_event.is_set():
        wd.start()

wd = Watchdog(timeout=10, interval=1)
wd.setCallback(lambda: print('timed out'))
thread = Thread(target=run_watchdog, args=(wd, stop_event), daemon=True)
thread.start()

# 正常動作時
wd.feed()
time.sleep(2)

# 停止する場合は stop_event.set() を呼ぶ
stop_event.set()
thread.join()
```

拡張案（将来の改善）:
- `start_in_thread()` / `stop()` を Watchdog に組み込む（内部で Thread と Event を管理して安全に停止できるようにする）
- コールバックに引数を渡せるようにする（context 情報、呼び出し回数など）
- asyncio と相互運用できるバージョン（async/await ベース）を用意する
- ロギング統合（標準 logging を使って状態変化を記録）
- 単発（one-shot）/繰り返しの動作モード指定

簡易テスト済み:
- 基本的なコールバックの有効／無効挙動をローカルで確認済み（feed 後は呼ばれず、タイムアウト状態で呼ばれる）。

注意事項:
- フル自動化（CI での運用）を行う場合は、スレッド起動・停止のテストを追加することを推奨します。
