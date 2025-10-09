# models/osc — 詳細設計

目的: VRChat 等と OSC / OSCQuery 経由で値の取得やチャット送信を行う。

主要クラス/関数:
- class OSCHandler
  - sendMessage(message: str, notification: bool=True): OSC で chatbox/input を送信
  - sendTyping(flag: bool): chatbox/typing を送信
  - receiveOscParameters(): OSCQuery を立て、指定したフィルタに対してローカルでサーバを実装してイベントを受ける
  - getOSCParameterValue(address: str): OSCQuery を通じて現在値を問い合わせる（use tinyoscquery）

注意点:
- `is_osc_query_enabled` が True のときに OSCQuery を使う（127.0.0.1 や localhost の場合に True）
- 受信ハンドラは dispatcher にマップしてコールバックを呼ぶ。
- ネットワーク環境や OSCQuery の可否により動作が変わるため例外処理が多く入っている。

依存: python-osc, tinyoscquery
