# アーキテクチャ概観

VRCT（src-python）は、ローカル音声キャプチャ・音声認識・翻訳・VR 表示・OSC/ WebSocket 連携を統合するアプリケーションです。主な責務は次の通り。

- device_manager: オーディオ入出力デバイスの発見、監視、コールバック通知。
- transcription (models/transcription/*): マイク/スピーカーからの音声取得、認識（Google/Whisper）、議事録管理。
- translation (models/translation/*): 翻訳エンジン（DeepL/API、CTranslate2、Google など）管理と実行。
- overlay (models/overlay/*): VR オーバーレイの画像生成と OpenVR を使った描画管理。
- osc (models/osc/osc.py): VRChat 等との OSC（および OSCQuery）でのやり取り。
- websocket (models/websocket/*): 外部クライアント向け WebSocket ブロードキャスト。
- model.py: 高レベルなファサード。各機能のインスタンス化とランタイム操作。
- controller.py: UI/外部メッセージを受け、config を更新・機能を起動するコマンド実行層。
- mainloop.py: stdin 経由のコマンド受付ループとマッピング定義。GUI からの操作を受ける想定。
- utils.py: ロギング、ネットワークチェック、デバイス/計算デバイスタイプ判定などのユーティリティ。
- config.py: シングルトン設定ストア。アプリ起動中に共有して使うすべての設定値。

設計上のポイント:
- シングルトン/ファサード: `model` と `config` はシングルトンでグローバルに参照される。これにより UI 層（Controller）と低レイヤ（models/*）の橋渡しを行う。
- 非同期処理: デバイス監視、音声録音・認識、WebSocket サーバー、Overlay のループはそれぞれ別スレッド／非同期ループで実行される。
- フォールバック: 翻訳はまず選択されたエンジンを使い、失敗時に CTranslate2 にフォールバックする仕組みがある。
- VRAM エラー検出: Whisper / CTranslate2 等で VRAM 不足が起きた場合、特殊なエラー検出を行い翻訳/音声機能を無効化して回復を試みる。
