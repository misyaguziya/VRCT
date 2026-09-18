# [2026/09/09] VRCT v3.5.1 Release 🛠️

インストーラーの安定性を改善し、録音時間の設定に関する不具合を修正しました。

## 🛠️ インストーラーの改善

  * GPU版の大容量パッケージを正しく展開できるよう、展開処理をWindows標準の`tar.exe`に変更しました。
  * ダウンロード前に、エディション（CPU/GPU）に応じた必要空き容量を確認するようにしました。
  * パッケージサイズを取得でき、空き容量に余裕がある場合は、4本の接続を使って並列ダウンロードするようにしました。条件を満たさない場合は通常の1本接続でダウンロードします。
  * ダウンロードまたは展開に失敗した場合、最大3回まで再試行するようにしました。
  * 展開後に`VRCT.exe`の存在を確認し、インストールが不完全なまま成功扱いになる問題を防止しました。
  * ダウンロード・展開の進捗や失敗理由をインストーラーの詳細表示に出力するようにしました。
  * Windows標準の`tar.exe`が利用できない環境では、必要なWindowsバージョンを案内してインストールを中断するようにしました。

## 🐛 バグ修正

  * 録音時間に`0`を設定した場合、録音開始直後に終了して音声認識できなくなる問題を修正しました。`0`以下は無制限録音として扱われます。([#113](https://github.com/misyaguziya/VRCT/issues/113))

* * *

## 🔗 リンク (Link)

  * [Booth](https://misyaguziya.booth.pm/)
  * [GitHub](https://github.com/misyaguziya/VRCT)
  * [Documents](https://misyaguziya.github.io/VRCT-Docs/)
  * [Patreon](https://www.patreon.com/vrct_dev) / [PIXIV FANBOX](https://vrct-dev.fanbox.cc/)
  * [Video](https://youtu.be/rUTad037n8Q)
  * [VRCT Status](https://docs.google.com/spreadsheets/d/1_L5i-1U6PB1dnaPPTE_5uKMfqOpkLziPyRkiMLi4mqU/edit?usp=sharing)
