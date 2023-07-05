# VRCT (VRChat Chatbox Translator & Transcription)

## Overview
VRChatのChatBoxにOSC経由でメッセージを送信するツール  
翻訳エンジンを使用してメッセージとその翻訳部分を同時に送信することができる  

## Requirement
- python 3.9.13
- pillow
- PyAudioWPatch
- python-osc
- customtkinter
- deepl
- deepl-translate(https://github.com/misyaguziya/deepl-translate)
- translators(https://github.com/misyaguziya/translators)
- custom_speech_recognition(https://github.com/misyaguziya/custom_speech_recognition)

deepl-translate/translators/custom_speech_recognitionについては追加実装をしています。`pip install`でinstallした場合、動かないので注意

## install
```bash
pip install -r requirements.txt
```

```bash
git clone https://github.com/misyaguziya/translators.git
python ./translators/setup.py install
git clone https://github.com/misyaguziya/deepl-translate.git
python ./deepl_translate/setup.py install
git clone https://github.com/misyaguziya/custom_speech_recognition.git
python ./custom_speech_recognition/setup.py install
```

## Usage
```bash
ptyhon VRCT.py
```

## Features

### init
0. VRChatのOSCを有効にする（重要）

(任意)
1. DeepLのAPIを使用するためにアカウント登録し、認証キーを取得する
2. ギアアイコンのボタンでconfigウィンドウを開く
3. ParameterタブのDeepL Auth Keyに認証キーを記載し、フロッピーアイコンのボタンを押す
4. configウィンドウを閉じる

### Normal use
1. メッセージボックスにメッセージを記入
2. Enterキーを押し、メッセージを送信する

### About Checkboxes
- translation: 翻訳の有効無効
- voice2chatbox: マイクの音声を文字起こししてチャットボックスに送信する
- speaker2log: スピーカーの音声から文字起こししてログに表示する
- foreground: 最前面表示の有効無効

### About Textbox
- log tab: すべてのログを表示
- send tab: 送信したメッセージを表示
- receive tab: 受信したメッセージを表示
- system tab: 機能についてのメッセージを表示

### About Config Window
- UI tab
    - Transparency: ウィンドウの透過度の調整
    - Appearance Theme: ウィンドウテーマを選択
    - UI Scaling: UIサイズを調整
    - Font Family: 表示フォントを選択
- Translation tab
    - Select Translator: 翻訳エンジンの変更
    - Send Language: 送信するメッセージに対して翻訳する言語[source, target]を選択
    - Receive Language: 受信したメッセージに対して翻訳する言語[source, target]を選択
- Transcription tab
    - Input Mic Device: マイクを選択
    - Input Mic Voice Language: 入力する音声の言語
    - Input Mic Energy Threshold: 音声取得のしきい値
    - Input Mic Dynamic Energy Threshold: 音声取得のしきい値の自動調整
    - Input Mic Record Timeout: 音声の区切りの無音時間
    - Input Mic Max Phrases: 保留する単語の上限
    - Input Speaker Device: スピーカーを選択
    - Input Speaker Voice Language: 受信する音声の言語
    - Input Speaker Energy Threshold: 音声取得のしきい値
    - Input Speaker Dynamic Energy Threshold: 音声取得のしきい値の自動調整
    - Input Speaker Record Timeout: 音声の区切りの無音時間
    - Input Speaker Max Phrases: 保留する単語の上限
- Parameter tab
    - OSC IP address: 変更不要
    - OSC port: 変更不要
    - DeepL Auth key: DeepLの認証キーの設定
    - Message Format: 送信するメッセージのデコレーションの設定
        - [message]がメッセージボックスに記入したメッセージに置換される
        - [translation]が翻訳されたメッセージに置換される
        - 初期フォーマット:`[message]([translation])`

## Author
みしゃ(misyaguzi)  
twitter: https://twitter.com/misya_ai  
booth: https://misyaguziya.booth.pm/items/4814313