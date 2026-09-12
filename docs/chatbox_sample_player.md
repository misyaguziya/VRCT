# 多言語チャットの送信と撮影

送信役の別PCで `VRCT-Chatbox-Sample-Player-windows-x64.zip` を展開し、
VRChatのOSCを有効にしてからexeを起動する。Enterで開始、Pで一時停止・再開、Qで終了。
通知音なしで `127.0.0.1:9000` の `/chatbox/input` に `[本文, true, false]` を送る。
本文は6秒ごとにシャッフルして繰り返す。撮影側は既存のDataset Collectorを使う。
送信元と撮影側のPCを取り違えないこと。

仕様・操作・撮影条件の詳細は [同梱READMEの原本](../tools/chatbox_samples/README.txt) を参照。
サンプルの原本は `tools/chatbox_samples/` 内のJSON。生成済みのJSONL/TXT一覧は配布物に含む。
言語、文の長さ、改行、文字幅、混在文字を変え、画像内のチャットボックスの形状を広く集める。
RTL文字や結合文字、絵文字の字形がVRChatで正しく描かれるかは撮影時に確認する。

VRChatの公式仕様は144文字・折り返し込み最大9行。送信前検証では保守的に
UTF-16単位で144以下、明示改行で9行以下に制限し、本文を勝手に切り詰めない。
[Chatbox OSC](https://docs.vrchat.com/docs/osc-as-input-controller#chatbox)、
[公式Wiki](https://wiki.vrchat.com/wiki/Chatbox)。

## ビルド

既存の `.venv` に `requirements-chatbox-sample-player.txt` の依存がある場合:

```powershell
.\bat\build_chatbox_sample_player.bat
```

別環境ではCPython 3.11 x64で専用venvを作り、同requirementsをインストールする。
`VRCT_CHATBOX_PYTHON` 環境変数にそのpython.exeの絶対パスを指定できる。
ビルド中は `--list` と `--dry-run` だけを実行し、VRChatへ送信しない。
配布ZIPにはexe、編集用JSON、一覧JSONL/TXT、README、ライセンス、BUILD-INFOを同梱する。
ログは同梱しない。既存の収集ツールexeやVRCT本体は変更しない。

## 検証

```powershell
.\.venv\Scripts\python.exe -m pytest -q src-python\test_chatbox_sample_player.py
.\.venv\Scripts\python.exe -m ruff check tools\chatbox_sample_player.py tools\build_chatbox_sample_player.py src-python\test_chatbox_sample_player.py
```

OSCテストはローカルのテスト専用一時ポートへ送り、UTF-8本文・bool引数・通知音無効を検証する。
VRChatの9000番ポートや外部PCにはテスト送信しない。
UDP送信成功とVRChatへの表示成功は区別する。自動ラベルの正解は実際の画像から作成する。

### 配布候補の検証結果（2026-09-12）

- サンプル246件、20言語・表記と混在例。全件144 UTF-16単位以下、明示9行以下。
  長さ別はtiny 40件、short 77件、medium 80件、long 49件。
- 上記pytestは23件成功、ruffと`git diff --check`も成功。独立レビューの重大指摘なし。
- 専用ビルドが成功。ZIPは6,978,123 bytes、14ファイルでCRC正常。
  元JSON・JSONL・TXTの本文一致、ライセンス同梱、画像・送信ログの混入なし。
- ソース外の一時フォルダへZIPを展開し、WindowsのみのPATHでexeの
  `--list`と`--dry-run --max-messages 1`が正常終了。
- 日本語・空白を含む展開先から実exeを起動し、専用のループバックUDP受信先で
  アラビア語、ヒンディー語の改行、絵文字、144単位の漢字を受信。
  本文と`[text, true, false]`の型を保持し、指定3秒以上の間隔と送信ログ4件を確認。
- 実exeのdry-runでPによる一時停止中は件数不変、再開後の進行、Rの状態表示、
  Qによる正常終了を確認。通常起動の開始待ちでQ→Enterによる取り消しも確認。

```text
ZIP SHA256: 4a65f8f3d1183d0ef8a3f8f27c77fb947870c7d48047e684b127251ddffa4ce2
EXE SHA256: e5fa12c3d34244632d06eec443cf116d0a0c4f6111c4ac6fc64593dc286dcc76
```

配布物は未署名。Python未導入の別PCと、VRChat上の実表示・全言語の字形は未検証。
実VRChatへの送信は行っていない。送信役PCでOSCを有効にし、撮影側から短文・長文・
改行・RTL文字・絵文字がどのように見えるかを確認してから収集する。
