# VRCT AMD 版 テストのお願い / AMD edition test

[日本語](#日本語) | [English](#english)

## 日本語

Radeon の GPU で VRCT の音声認識・翻訳を動かす「AMD 版」のテスト版です。

### 対象

- RDNA3（Radeon RX 7000）、RDNA3.5（Ryzen AI 300 / Ryzen AI Max の内蔵 GPU）、RDNA4（Radeon RX 9000）
- 最近の AMD Software: Adrenalin Edition（`C:\Windows\System32\amdhip64_7.dll` があること）

### 準備

1. `VRCT_amd.zip` を、**英数字だけのパス**のフォルダーに展開します（例 `C:\VRCT-amd-test`）。インストール済みの VRCT とは別のフォルダーにしてください。
2. 展開したフォルダーの `VRCT.exe` を起動します。初回はモデルのダウンロードがあります。
3. 設定 →「翻訳」の「AI翻訳の処理デバイス」と、設定 →「音声認識」の「AI音声認識で使用する処理デバイス」で Radeon を選びます（既定は CPU）。

### 確認してほしいこと

| # | 内容 | 結果の例 |
|---|---|---|
| 1 | 上の処理デバイスの一覧に Radeon が出る。設定画面の左下のバージョン表示に「AMD」と出る | 出た / 出ない |
| 2 | Radeon を選んで翻訳する（チャットに文字を入れて送る） | 訳が出る / エラー |
| 3 | Radeon を選んで音声認識する（マイクで話す） | 文字になる / エラー |
| 4 | 翻訳と音声認識を同時に ON にして 5 分ほど使う | 問題なし / 止まった |
| 5 | Whisper のモデルを別のもの（例 large-v3-turbo）に切り替え、また音声認識する。タスクマネージャーの「専用 GPU メモリ」が切り替えの前後で増え続けないか | 増え続けない / 増える |
| 6 | 30 分以上つけたまま使う | 問題なし / 止まった・落ちた |
| 7 | （できれば）処理デバイスを CPU に戻しても動く | 動く / 動かない |

### 送ってほしいもの

- 上の表の結果と、GPU の名前・ドライバーの版
- `VRCT.exe` と同じフォルダーの `process.log` と `error.log`（個人情報が気になる部分は消して構いません）
- エラーが出たときは画面のスクリーンショット

`process.log` の最初のほうに `Loaded ROCm CTranslate2` と、GPU ごとに `(gfx11xx): used` のような行が出ていれば、Radeon が使われています。`Using CPU: ...` の行は、Radeon を使えなかった理由です。

## English

A test build of the "AMD edition", which runs VRCT's transcription and translation on Radeon GPUs.

### Supported

- RDNA3 (Radeon RX 7000), RDNA3.5 (Ryzen AI 300 / Ryzen AI Max integrated GPUs), RDNA4 (Radeon RX 9000)
- A recent AMD Software: Adrenalin Edition (`C:\Windows\System32\amdhip64_7.dll` must exist)

### Setup

1. Extract `VRCT_amd.zip` into a folder whose **path has only ASCII letters and digits** (e.g. `C:\VRCT-amd-test`), separate from any installed VRCT.
2. Run `VRCT.exe` in that folder. The first start downloads the models.
3. In Settings → Translation ("Processing device for AI translation") and Settings → Transcription (the processing device for AI transcription), choose the Radeon (the default is CPU).

### What to check

| # | Check | Result |
|---|---|---|
| 1 | The Radeon appears in those processing device lists, and the version label at the bottom left of the Settings screen shows "AMD" | yes / no |
| 2 | Translate with the Radeon selected (type and send a chat message) | translated / error |
| 3 | Transcribe with the Radeon selected (speak into the mic) | text appears / error |
| 4 | Use translation and transcription together for about 5 minutes | fine / stopped |
| 5 | Switch the Whisper model (e.g. to large-v3-turbo) and transcribe again; in Task Manager, "Dedicated GPU memory" should not keep growing across switches | stable / keeps growing |
| 6 | Keep it running for 30 minutes or more | fine / stopped or crashed |
| 7 | (Optional) It still works after switching the processing device back to CPU | works / doesn't |

### Please send

- The results above, your GPU model and driver version
- `process.log` and `error.log` from the folder with `VRCT.exe` (feel free to remove anything personal)
- Screenshots of any error

Near the top of `process.log`, `Loaded ROCm CTranslate2` and a line like `(gfx11xx): used` for your GPU mean the Radeon is in use. A `Using CPU: ...` line gives the reason the Radeon could not be used.
