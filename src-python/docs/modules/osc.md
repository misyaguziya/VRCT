## OSC モジュール (models.osc)

このドキュメントは `models/osc/osc.py` の使い方と注意点を簡潔にまとめたものです。

### 概要
- `OSCHandler` クラスは OSC メッセージの送信 (/chatbox/input, /chatbox/typing 等) と、
  ローカル環境では OSCQuery でエンドポイントを公開するための薄いラッパーを提供します。

### 依存関係
- `python-osc` — UDP クライアント/サーバ
- `tinyoscquery` — OSCQuery を利用する場合に必要（オプショナル）

### 使い方（例）

```python
from models.osc.osc import OSCHandler

handler = OSCHandler(ip_address="127.0.0.1", port=9000)
handler.setDictFilterAndTarget({
    "/chatbox/input": lambda addr, *args: print(args),
})
handler.receiveOscParameters()
handler.sendTyping(True)
handler.sendMessage("Hello")
handler.oscServerStop()
```

### 注意点
- `tinyoscquery` がインストールされていない場合、OSCQuery 関連機能は無効になりますが、送信（UDP クライアント）は動作します。
- サービスのアドバタイズ中に例外が発生した場合、内部でリトライします。
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
