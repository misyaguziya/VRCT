import os
import customtkinter

class ToplevelWindowInformation(customtkinter.CTkToplevel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        # self.geometry(f"{500}x{300}")
        self.minsize(500, 300)

        self.after(200, lambda: self.iconbitmap(os.path.join(os.path.dirname(__file__), "img", "app.ico")))
        self.title("Information")
        # create textbox information
        self.textbox_information = customtkinter.CTkTextbox(
            self,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.textbox_information.grid(row=0, column=0, padx=(10, 10), pady=(10, 10), sticky="nsew")
        textbox_information_message = """VRCT(v0.4b)

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
        3. ParameterタブのDeepL Auth Keyに認証キーを記載し、フロッピーアイコンのボタンを押す
        4. configウィンドウを閉じる

    通常使用時
        1. メッセージボックスにメッセージを記入
        2. Enterキーを押し、メッセージを送信する

# その他の設定
    translation チェックボックス: 翻訳の有効無効
    foreground チェックボックス: 最前面表示の有効無効

    configウィンドウ
        UIタブ
            Select translator: 翻訳エンジンの変更
            Select Language: 翻訳する言語[source, target]を選択
            Transparency: ウィンドウの透過度の調整
            Appearance Theme: ウィンドウテーマを選択
            UI Scaling: UIサイズを調整
            Font Family: 表示フォントを選択
        Parameterタブ
            OSC IP address: 変更不要
            OSC port: 変更不要
            DeepL Auth key: DeepLの認証キーの設定
            Message Format: 送信するメッセージのデコレーションの設定
                [message]がメッセージボックスに記入したメッセージに置換される
                [translation]が翻訳されたメッセージに置換される
                初期フォーマット:"[message]([translation])"

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

# 注意事項
再配布とかはやめてね
"""

        self.textbox_information.insert("end", textbox_information_message)
        self.textbox_information.configure(state='disabled')