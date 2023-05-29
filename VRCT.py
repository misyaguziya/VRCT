import os
import json
import deepl
from pythonosc import osc_message_builder
from pythonosc import udp_client
import customtkinter
from PIL import Image

# global
PATH_CONFIG = "./config.json"
OSC_IP_ADDRESS = "127.0.0.1"
OSC_PORT = 9000
TARGET_LANG = "EN-US"
ENABLE_TRANSLATION = True
CHOICE_TRANSLATOR = "DeepL"
ENABLE_FOREGROUND = True
AUTH_KEY = None
TRANSLATOR = None
MESSAGE_FORMAT = "[message]([translation])"

# load config
if os.path.isfile(PATH_CONFIG) is not False:
    with open(PATH_CONFIG, 'r') as fp:
        config = json.load(fp)
    if "OSC_IP_ADDRESS" in config.keys():
        OSC_IP_ADDRESS = config["OSC_IP_ADDRESS"]
    if "OSC_PORT" in config.keys():
        OSC_PORT = config["OSC_PORT"]
    if "TARGET_LANG" in config.keys():
        TARGET_LANG = config["TARGET_LANG"]
    if "ENABLE_TRANSLATION" in config.keys():
        ENABLE_TRANSLATION = config["ENABLE_TRANSLATION"]
    if "CHOICE_TRANSLATOR" in config.keys():
        CHOICE_TRANSLATOR = config["CHOICE_TRANSLATOR"]
    if "ENABLE_FOREGROUND" in config.keys():
        ENABLE_FOREGROUND = config["ENABLE_FOREGROUND"]
    if "AUTH_KEY" in config.keys():
        AUTH_KEY = config["AUTH_KEY"]
    if "MESSAGE_FORMAT" in config.keys():
        MESSAGE_FORMAT = config["MESSAGE_FORMAT"]

with open(PATH_CONFIG, 'w') as fp:
    config = {
        "OSC_IP_ADDRESS": OSC_IP_ADDRESS,
        "OSC_PORT": OSC_PORT,
        "TARGET_LANG": TARGET_LANG,
        "ENABLE_TRANSLATION": ENABLE_TRANSLATION,
        "CHOICE_TRANSLATOR": CHOICE_TRANSLATOR,
        "ENABLE_FOREGROUND": ENABLE_FOREGROUND,
        "AUTH_KEY": AUTH_KEY,
        "MESSAGE_FORMAT": MESSAGE_FORMAT,
    }
    json.dump(config, fp, indent=4)

# deepl connect
if AUTH_KEY is not None:
    TRANSLATOR = deepl.Translator(AUTH_KEY)
    try:
        TRANSLATOR.translate_text(" ", target_lang="EN-US")
    except:
        TRANSLATOR = None

# GUI
customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class ToplevelWindow_information(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.geometry(f"{500}x{300}")
        # self.resizable(False, False)

        self.after(200, lambda: self.iconbitmap("./img/app.ico"))
        self.title("Information")
        # create textbox information
        self.textbox_information = customtkinter.CTkTextbox(self)
        self.textbox_information.grid(row=0, column=0, padx=(10, 10), pady=(10, 10), sticky="nsew")
        textbox_information_message = """VRCT(v0.2b)

# 概要
VRChatで使用されるChatBoxをOSC経由でメッセージを送信するツールになります。
翻訳機能としてDeepLのAPIを使用してメッセージとその翻訳部分を同時に送信することができます。

# 使用方法
    初期設定時
        1. DeepLのAPIを使用するためにアカウント登録し、認証キーを取得する
        2. configボタンでconfigウィンドウを開きDeepL Auth Keyに認証キーを記載しcheckボタンを押す
        3. configウィンドウを閉じる

    通常使用時
        1. メッセージボックスにメッセージを記入
        2. Enterキーを押し、メッセージを送信する

# その他の設定
    コンボボックス
        翻訳機能の有効無効
        翻訳する言語の選択

    configウィンドウ
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
- 翻訳機能有効無効のチェックボックスを追加
- 常に最前面の有効無効のチェックボックスを追加

# 注意事項
再配布とかはやめてね
"""

        self.textbox_information.insert("0.0", textbox_information_message)
        self.textbox_information.configure(state='disabled')

class ToplevelWindow_config(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry(f"{450}x{160}")
        self.resizable(False, False)

        self.after(200, lambda: self.iconbitmap("./img/app.ico"))
        self.title("Config")
        self.label_ip_address = customtkinter.CTkLabel(self, text="OSC IP address:", fg_color="transparent")
        self.label_ip_address.grid(row=0, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_ip_address = customtkinter.CTkEntry(self, width=300, placeholder_text=OSC_IP_ADDRESS)
        self.entry_ip_address.grid(row=0, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_ip_address = customtkinter.CTkButton(self, text="✓", width=1, command=self.update_ip_address)
        self.button_ip_address.grid(row=0, column=2, columnspan=1, padx=1, pady=5, sticky="nsew")

        self.label_port = customtkinter.CTkLabel(self, text="OSC Port:", fg_color="transparent")
        self.label_port.grid(row=1, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_port = customtkinter.CTkEntry(self, placeholder_text=OSC_PORT)
        self.entry_port.grid(row=1, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_port = customtkinter.CTkButton(self, text="✓", width=1, command=self.update_port)
        self.button_port.grid(row=1, column=2, columnspan=1, padx=1, pady=5, sticky="nsew")

        self.label_authkey = customtkinter.CTkLabel(self, text="DeepL Auth Key:", fg_color="transparent")
        self.label_authkey.grid(row=2, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_authkey = customtkinter.CTkEntry(self, placeholder_text=AUTH_KEY)
        self.entry_authkey.grid(row=2, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_authkey = customtkinter.CTkButton(self, text="✓", width=1, command=self.update_authkey)
        self.button_authkey.grid(row=2, column=2, columnspan=1, padx=1, pady=5, sticky="nsew")

        self.label_message_format = customtkinter.CTkLabel(self, text="Message Format:", fg_color="transparent")
        self.label_message_format.grid(row=3, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_message_format = customtkinter.CTkEntry(self, placeholder_text=MESSAGE_FORMAT)
        self.entry_message_format.grid(row=3, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_message_format = customtkinter.CTkButton(self, text="✓", width=1, command=self.update_message_format)
        self.button_message_format.grid(row=3, column=2, columnspan=1, padx=1, pady=5, sticky="nsew")

    def update_ip_address(self):
        global OSC_IP_ADDRESS
        OSC_IP_ADDRESS = self.entry_ip_address.get()
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["OSC_IP_ADDRESS"] = OSC_IP_ADDRESS
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

    def update_port(self):
        global OSC_PORT
        OSC_PORT = self.entry_port.get()
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["OSC_PORT"] = OSC_PORT
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

    def update_authkey(self):
        global AUTH_KEY
        global TRANSLATOR
        AUTH_KEY = self.entry_authkey.get()
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["AUTH_KEY"] = AUTH_KEY
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

        TRANSLATOR = deepl.Translator(AUTH_KEY)
        try:
            TRANSLATOR.translate_text(" ", target_lang="EN-US")
        except:
            TRANSLATOR = None

    def update_message_format(self):
        global MESSAGE_FORMAT
        MESSAGE_FORMAT = self.entry_message_format.get()
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["MESSAGE_FORMAT"] = MESSAGE_FORMAT
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.iconbitmap('./img/app.ico')
        self.title("VRCT")
        self.geometry(f"{400}x{190}")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # sidebar left
        self.sidebar_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # checkbox translation
        self.checkbox_translation = customtkinter.CTkCheckBox(self.sidebar_frame, text="translation", onvalue=True, offvalue=False, command=self.checkbox_translation_callback)
        self.checkbox_translation.grid(row=0, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # checkbox foreground
        self.checkbox_foreground = customtkinter.CTkCheckBox(self.sidebar_frame, text="foreground", onvalue=True, offvalue=False, command=self.checkbox_foreground_callback)
        self.checkbox_foreground.grid(row=1, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # combobox translator
        self.combobox_translator = customtkinter.CTkComboBox(self.sidebar_frame, command=self.combobox_translator_callback)
        self.combobox_translator.grid(row=2, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # combobox language
        self.combobox_language = customtkinter.CTkComboBox(self.sidebar_frame, command=self.combobox_language_callback)
        self.combobox_language.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="we")

        # button information
        self.button_information = customtkinter.CTkButton(self.sidebar_frame, text="", width=70, command=self.open_information,
                                                        image=customtkinter.CTkImage(Image.open("./img/info-icon-white.png")))
        self.button_information.grid(row=5, column=0, padx=5, pady=(10, 10), sticky="wse")
        self.information_window = None

        # button config
        self.button_config = customtkinter.CTkButton(self.sidebar_frame, text="", width=70, command=self.open_config,
                                                    image=customtkinter.CTkImage(Image.open("./img/config-icon-white.png")))
        self.button_config.grid(row=5, column=1, padx=5, pady=(10, 10), sticky="wse")
        self.config_window = None

        # create textbox message log
        self.textbox_message_log = customtkinter.CTkTextbox(self)
        self.textbox_message_log.grid(row=0, column=1, padx=(10, 10), pady=(10, 5), sticky="nsew")
        self.textbox_message_log.configure(state='disabled')

        # create entry message box
        self.entry_message_box = customtkinter.CTkEntry(self, placeholder_text="message")
        self.entry_message_box.grid(row=1, column=1, columnspan=2, padx=(10, 10), pady=(5, 10), sticky="nsew")

        # set default values
        if ENABLE_TRANSLATION:
            self.checkbox_translation.select()
        else:
            self.checkbox_translation.deselect()

        if ENABLE_FOREGROUND:
            self.checkbox_foreground.select()
            self.attributes("-topmost", True)
        else:
            self.checkbox_foreground.deselect()
            self.attributes("-topmost", False)

        self.combobox_translator.configure(values=["DeepL"],)
        self.combobox_language.configure(values=[
                "JA","BG","CS","DA","DE","EL","EN","EN-US","EN-GB","ES","ET","FI","FR","HU",
                "ID","IT","KO","LT","LV","NB","NL","PL","PT","PT-BR","PT-PT","RO","RU","SK",
                "SL","SV","TR","UK","ZH",
            ],)
        self.entry_message_box.bind("<Return>", self.press_key)

        if TRANSLATOR is None:
            # error update Auth key
            self.textbox_message_log.configure(state='normal')
            self.textbox_message_log.insert("0.0", f"Auth Keyを設定してないか間違っています\n")
            self.textbox_message_log.configure(state='disabled')

        self.combobox_language.set(TARGET_LANG)
        self.combobox_translator.set(CHOICE_TRANSLATOR)

    def open_config(self):
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = ToplevelWindow_config(self)
        self.config_window.focus()

    def open_information(self):
        if self.information_window is None or not self.information_window.winfo_exists():
            self.information_window = ToplevelWindow_information(self)
        self.information_window.focus()

    def checkbox_translation_callback(self):
        global ENABLE_TRANSLATION
        ENABLE_TRANSLATION = self.checkbox_translation.get()
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["ENABLE_TRANSLATION"] = ENABLE_TRANSLATION
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

    def combobox_translator_callback(self, choice):
        global CHOICE_TRANSLATOR
        CHOICE_TRANSLATOR = choice
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["CHOICE_TRANSLATOR"] = CHOICE_TRANSLATOR
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

    def combobox_language_callback(self, choice):
        global TARGET_LANG
        TARGET_LANG = choice
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["TARGET_LANG"] = TARGET_LANG
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

    def checkbox_foreground_callback(self):
        global ENABLE_FOREGROUND
        ENABLE_FOREGROUND = self.checkbox_foreground.get()
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["ENABLE_FOREGROUND"] = ENABLE_FOREGROUND
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

        if ENABLE_FOREGROUND:
            self.attributes("-topmost", True)
        else:
            self.attributes("-topmost", False)

    def press_key(self, event):
        if TRANSLATOR is None:
            # error update Auth key
            self.textbox_message_log.configure(state='normal')
            self.textbox_message_log.insert("0.0", f"Auth Keyを設定してないか間違っています\n")
            self.textbox_message_log.configure(state='disabled')
        else:
            message = self.entry_message_box.get()

            # translate
            if self.checkbox_translation.get() is True:
                result = TRANSLATOR.translate_text(message, target_lang=TARGET_LANG)
                chat_message = MESSAGE_FORMAT.replace("[message]", message).replace("[translation]", result.text)
            else:
                chat_message = f"{message}"

            # send OSC message
            message = osc_message_builder.OscMessageBuilder(address="/chatbox/input")
            message.add_arg(f"{chat_message}")
            message.add_arg(True)
            message.add_arg(True)
            message = message.build()
            client = udp_client.SimpleUDPClient(OSC_IP_ADDRESS, OSC_PORT)
            client.send(message)

            # update textbox message log
            self.textbox_message_log.configure(state='normal')
            self.textbox_message_log.insert("0.0", f"{chat_message}\n")
            self.textbox_message_log.configure(state='disabled')

            # delete message in entry message box
            self.entry_message_box.delete(0, customtkinter.END)

if __name__ == "__main__":
    app = App()
    app.mainloop()