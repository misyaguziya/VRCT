ご購入ありがとうございます。
フィードバックお待ちしております。

# 概要
VRChatで使用されるChatBoxをOSC経由でメッセージを送信するツールになります。
翻訳エンジンを使用してメッセージとその翻訳部分を同時に送信することができます。
(翻訳エンジンはDeepL,Google,Bingに対応)

# 使用方法
    初期設定時
        0. VRChatのOSCを有効にする（重要）

        (任意)
        1. DeepLのAPIを使用するためにアカウント登録し、認証キーを取得する
        2. ギアアイコンのボタンでconfigウィンドウを開く
        3. ParameterタブのDeepL Auth Keyに認証キーを記載
        4. configウィンドウを閉じる

    通常使用時
        1. メッセージボックスにメッセージを記入
        2. Enterキーを押し、メッセージを送信する

# その他の設定
    translation チェックボックス: 翻訳の有効無効
    voice2chatbox チェックボックス : マイクの音声を文字起こししてチャットボックスに送信する
    speaker2log チェックボックス : スピーカーの音声から文字起こししてログに表示する
    foreground チェックボックス: 最前面表示の有効無効

    テキストボックス
        logタブ
            すべてのログを表示
        sendタブ
            送信したメッセージを表示
        receiveタブ
            受信したメッセージを表示
        systemタブ
            機能についてのメッセージを表示

    configウィンドウ
        UIタブ
            Transparency: ウィンドウの透過度の調整
            Appearance Theme: ウィンドウテーマを選択
            UI Scaling: UIサイズを調整
            Font Family: 表示フォントを選択
            UI Language: UIの表示言語を選択
        Translationタブ
            Select Translator: 翻訳エンジンの変更
            Send Language: 送信するメッセージに対して翻訳する言語[source, target]を選択
            Receive Language: 受信したメッセージに対して翻訳する言語[source, target]を選択
        Transcriptionタブ
            Input Mic Host: マイクのホストAPIを選択
            Input Mic Device: マイクを選択
            Input Mic Voice Language: 入力する音声の言語
            Input Mic Energy Threshold: 音声取得のしきい値
            Check threshold point: Input Mic Energy Thresholdのしきい値を視覚化
            Input Mic Dynamic Energy Threshold: 音声取得のしきい値の自動調整
            Input Mic Record Timeout: 音声の区切りの無音時間
            Input Mic Phase Timeout: 文字起こしする音声時間の上限
            Input Mic Max Phrases: 保留する単語の上限
            Input Mic Word Filter: MICの文字起こし時にWord Filterで設定した文字が入っていた場合にChatboxに表示しない (ex AAA,BBB,CCC)
            Input Speaker Device: スピーカーを選択
            Input Speaker Voice Language: 受信する音声の言語
            Input Speaker Energy Threshold: 音声取得のしきい値
            Check threshold point: Input Speaker Energy Thresholdのしきい値を視覚化
            Input Speaker Dynamic Energy Threshold: 音声取得のしきい値の自動調整
            Input Speaker Record Timeout: 音声の区切りの無音時間
            Input Speaker Phase Timeout: 文字起こしする音声時間の上限
            Input Speaker Max Phrases: 保留する単語の上限
        Parameterタブ
            OSC IP address: 変更不要
            OSC port: 変更不要
            DeepL Auth key: DeepLの認証キーの設定
            Message Format: 送信するメッセージのデコレーションの設定
                [message]がメッセージボックスに記入したメッセージに置換される
                [translation]が翻訳されたメッセージに置換される
                初期フォーマット:"[message]([translation])"
        Othersタブ
            Auto clear chat box: メッセージ送信後に書き込んだメッセージを空にする
            (New!) Notification XSOverlay: XSOverlayの通知機能を有効(VR only)

    設定の初期化
        config.jsonを削除

# お問い合わせ
要望などはTwitterまで
https://twitter.com/misya_ai

# アップデート履歴
[2023-05-29: v0.1b] v0.1b リリース
[2023-05-30: v0.2b]
- configボタンをギアアイコンに変更
- 詳細情報のボタンを追加
- 翻訳機能有効無効のチェックボックスを追加
- 最前面表示の有効無効のチェックボックスを追加
- いくつかのバグを修正
[2023-06-03: v0.3b]
- 全体的にUIを刷新
- 透過機能を追加
- テーマのLight/Dark/Systemのモードの変更機能を追加
- UIのスケール変更機能を追加
- フォントの変更機能を追加
[2023-06-06: v0.4b]
- 翻訳エンジンを追加
- 入力と出力の翻訳言語を選択できるように変更
[2023-06-20: v1.0]
- マイクからの音声の文字起こし機能を追加
- スピーカーからの音声の文字起こし機能を追加
[2023-06-28: v1.1]
- いくつかのバクを修正
- 翻訳/文字起こし言語の表記を略称からわかりやすい文字に変更
- 文字起こしの処理の軽量化
[2023-07-05: v1.2]
- 文字起こし精度の向上
[2023-07-21: v1.3]
- UIの表示言語を日本語/英語を選択できる機能を追加
- Energy Thresholdの視覚化機能を追加
- 文字起こしの誤認識対策のため、Word Filterを追加
- WASAPI以外のHostAPIでもマイクとして使用できるようにHostAPIを選択できる機能を追加
- メッセージ送信後に書き込んだメッセージを空にするか選択できる機能を追加
- バグ対策のため、translation/voice2chatbox/speaker2log/foregroundは起動時はOFFになるように変更
- バグ対策のため、スピーカーについて既定デバイス以外を選択した時にERRORが出るように変更
- 半角入力時に一部の文字が書き込めないバグを修正
[2023-07-22: v1.3.1]
- UIの表示言語選択に韓国語を追加
[2023-07-30: v1.3.2]
- 試験的にXSOverlayへの通知機能を追加
- checkbox ONの状態でもConfigを開けるように変更
- 文字起こし言語の表示を修正
- いくつかのバグを修正

# 注意事項
再配布とかはやめてね