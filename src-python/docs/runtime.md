# 実行手順と依存関係

対象 OS: Windows を想定（device_manager は WASAPI / pycaw を使う）。

必須依存（概略）:
- Python 3.10+ 推奨
- pip パッケージ:
  - torch
  - ctranslate2
  - transformers
  - requests
  - pyaudiowpatch
  - pycaw
  - speech_recognition
  - pydub
  - websockets
  - python-osc
  - tinyoscquery
  - sudachipy
  - pillow
  - flashtext
  - faster_whisper (オプション: Whisper をローカルで使う場合)
  - deepl / translators（外部翻訳を使う場合）

実行手順 (開発環境):
1. 仮想環境を作成し有効化
2. 必要パッケージをインストール
   - requirements.txt を用意する場合はそこからインストール
3. `src-python` をワークディレクトリにして `python mainloop.py` を実行

注意点:
- Whisper / CTranslate2 の重みは初回にダウンロードする必要がある。Controller の downloadCtranslate2Weight / downloadWhisperWeight エンドポイントからトリガできる。
- OpenVR (SteamVR) を使う Overlay は SteamVR が動作している環境でのみ動作。
- Windows 固有: device_manager が pyaudiowpatch と pycaw に依存。Linux/Mac での互換性は保証されない。

ログ:
- process.log (標準動作ログ)
- error.log (トレースバック)
- models 用のロガーは `model.startLogger()` により PATH_LOGS 配下に日付付きファイルを作成する。

デバッグ:
- `utils.printLog` と `utils.printResponse` が stdout に JSON を出すため、GUI 側はそれをパースして UI 更新を行う。
- WebSocket を有効にすると外部クライアントに JSON をブロードキャストできる。
