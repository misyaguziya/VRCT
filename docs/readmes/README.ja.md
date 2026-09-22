<div align="center">

<picture>
    <source srcset="/docs/img/vrct_logo_white.png" media="(prefers-color-scheme: dark)" width="50%">
    <source srcset="/docs/img/vrct_logo_black.png" media="(prefers-color-scheme: light)" width="50%">
    <img src="/docs/img/vrct_logo.png" alt="VRCT Logo" width="50%">
</picture>

<br>
<br>

[![GitHub release](https://img.shields.io/github/v/release/misyaguziya/VRCT.svg)](https://github.com/misyaguziya/VRCT/releases)
[![Downloads](https://img.shields.io/github/downloads/misyaguziya/VRCT/total)](https://github.com/misyaguziya/VRCT/releases)
[![Licence](https://img.shields.io/github/license/misyaguziya/VRCT)](https://github.com/misyaguziya/VRCT/blob/master/LICENSE)
[![Booth](https://img.shields.io/badge/Store-Booth.pm-red)](https://misyaguziya.booth.pm/items/5155325)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA)](https://github.com/sponsors/misyaguziya)

<h3>
Become a VRCT Supporter on:
</h3>

<a href="https://vrct-dev.fanbox.cc">
    <picture>
        <source srcset="/docs/img/pixiv_fanbox_white.png" media="(prefers-color-scheme: dark)" height="18px">
        <source srcset="/docs/img/pixiv_fanbox_black.png" media="(prefers-color-scheme: light)" height="18px">
        <img src="/docs/img/pixiv_fanbox_black.png" alt="PIXIV FANBOX" height="18px">
    </picture>
</a>&emsp;&nbsp;

<a href="https://patreon.com/vrct_dev">
    <picture>
        <source srcset="/docs/img/patreon_logo_white.png" media="(prefers-color-scheme: dark)" height="22px">
        <source srcset="/docs/img/patreon_logo_black.png" media="(prefers-color-scheme: light)" height="22px">
        <img src="/docs/img/patreon_logo_black.png" alt="Patreon" height="22px">
    </picture>
</a>&emsp;&nbsp;

<br>

<picture>
    <source srcset="/docs/img/supporter_section_border_d.png" media="(prefers-color-scheme: dark)">
    <source srcset="/docs/img/supporter_section_border_l.png" media="(prefers-color-scheme: light)">
    <img src="/docs/img/supporter_section_border_d.png" alt="Supporter Section Border">
</picture>

<br>
<br>

| [English](/docs/readmes/README.en.md) | **日本語** | [한국어](/docs/readmes/README.ko.md) | [繁體中文](/docs/readmes/README.zh-Hant.md) |

<h3>
VRCTは翻訳や文字起こしでVRChatの会話をサポートするソフトウェアです。
</h3>

![](/docs/img/main_window.png)

<div align="left">

# ダウンロード＆インストール
好きな場所からダウンロードしてください。
- [Github.com](https://github.com/misyaguziya/VRCT/releases/)
- [BOOTH.pm](https://misyaguziya.booth.pm/items/5155325)

ダウンロードしてexeを起動するだけです。

# VRCTってなに？
VRCTは話す言語の異なる人同士が会話を行うためにチャットもしくは音声の翻訳を行うことで会話をサポートするソフトウェアです。
これらの機能はVRChat内で使用するために設計されています。
※サポート対象外ですがその他の用途として映画鑑賞等でも使用されています。

VRCTはあなたの会話を以下でサポートをします。
- 💬 **VRChatへのチャット送信機能**
- 🌐 **翻訳機能**
- 🎙 **マイクの文字起こし機能**
- 🔈 **スピーカーの文字起こし機能**

# ドキュメント
初期設定や基本機能、その他の機能についても記載してあります。
- [Documents Link](https://misyaguziya.github.io/VRCT-Docs/)

# 使い方(Youtube)
<div align="center">

[![](https://img.youtube.com/vi/rUTad037n8Q/0.jpg)](https://www.youtube.com/watch?v=rUTad037n8Q)

<div align="left">

## Author
- [みしゃ(misyaguzi)](https://github.com/misyaguziya) (メイン開発)
- [しいな(Shiina_12siy)](https://twitter.com/Shiina_12siy) (UI/UX, UI多言語対応)
- [レラ](https://github.com/soumt-r) (テクニカルサポート)
- [どね](https://twitter.com/done_vrc) (ロゴデザイン)

## テレメトリー（利用統計情報）

VRCTは[Aptabase](https://aptabase.com)を通じて、アプリの改善のために匿名のテレメトリーデータを収集しています。収集されるデータは、起動回数、起動時間、使用機能です。個人を特定できる情報は一切収集されません。

テレメトリーはアプリの設定からいつでも無効化できます。詳細は[Aptabaseプライバシーポリシー](https://aptabase.com/legal/privacy)をご確認ください。

## ライセンス

VRCT は [MIT License](/LICENSE) で公開しています。ただし OCR 機能が使うチャットボックス
検出モデル（`src-python/models/ocr/onnx/chatbox_yolox_tiny.onnx`）は例外で、**VRCT 専用の
利用許諾**が適用されます。VRCT として、また **VRCT の開発・修正・検証のためのフォークとして**
実行することは自由で、リポジトリをフォークしてモデルを含んだまま持っていて構いません。
できないのは、フォーク独自のリリース版にモデルを同梱すること、VRCT 以外のソフトウェアへ
持ち出すこと、単体での再配布、派生モデルの作成です。
条文は [LICENSE.txt](/src-python/models/ocr/onnx/LICENSE.txt)、範囲は [NOTICE.md](/NOTICE.md) を
確認してください。モデルを持たない状態でもビルド・実行でき、その場合は吹き出し検出だけが
無効になります（自前で学習する手順は [docs/ocr_yolo_training.md](/docs/ocr_yolo_training.md)）。

## Thanks to our contributors
<a href="https://github.com/misyaguziya/VRCT/graphs/contributors" target="_blank">
  <img src="https://contrib.rocks/image?repo=misyaguziya/VRCT" />
</a>

---

VRCT は VRChat によって承認されておらず、VRChat または VRChat の開発もしくは管理に公式に関与する者の見解や意見が反映されたものではありません。VRChat および関連するすべての財産は 米国VRChat, Incの商標または登録商標です。