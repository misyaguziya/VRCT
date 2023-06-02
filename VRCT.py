import os
import json
import deepl
from pythonosc import osc_message_builder
from pythonosc import udp_client
import tkinter as tk
import customtkinter
from PIL import Image

# global
PATH_CONFIG = "./config.json"
OSC_IP_ADDRESS = "127.0.0.1"
OSC_PORT = 9000
TARGET_LANG = "EN-US"
ENABLE_TRANSLATION = True
CHOICE_TRANSLATOR = "DeepL"
ENABLE_FOREGROUND = False
AUTH_KEY = None
TRANSLATOR = None
MESSAGE_FORMAT = "[message]([translation])"
FONT_FAMILY = "Yu Gothic UI"
TRANSPARENCY = 100
APPEARANCE_THEME = "System"
UI_SCALING = "100%"

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
    if "FONT_FAMILY" in config.keys():
        FONT_FAMILY = config["FONT_FAMILY"]
    if "TRANSPARENCY" in config.keys():
        TRANSPARENCY = config["TRANSPARENCY"]
    if "APPEARANCE_THEME" in config.keys():
        APPEARANCE_THEME = config["APPEARANCE_THEME"]
    if "UI_SCALING" in config.keys():
        UI_SCALING = config["UI_SCALING"]

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
        "FONT_FAMILY": FONT_FAMILY,
        "TRANSPARENCY": TRANSPARENCY,
        "APPEARANCE_THEME": APPEARANCE_THEME,
        "UI_SCALING": UI_SCALING,
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
customtkinter.set_appearance_mode(APPEARANCE_THEME)
customtkinter.set_default_color_theme("blue")

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
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
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
    translation チェックボックス: 翻訳の有効無効
    foreground チェックボックス: 最前面表示の有効無効

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
- configボタンをギアアイコンに変更
- 詳細情報のボタンを追加
- 翻訳機能有効無効のチェックボックスを追加
- 最前面表示の有効無効のチェックボックスを追加
- いくつかのバグを修正

# 注意事項
再配布とかはやめてね
"""

        self.textbox_information.insert("0.0", textbox_information_message)
        self.textbox_information.configure(state='disabled')

class ToplevelWindowConfig(customtkinter.CTkToplevel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        # self.geometry(f"{350}x{270}")
        # self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.after(200, lambda: self.iconbitmap(os.path.join(os.path.dirname(__file__), "img", "app.ico")))
        self.title("Config")

        # tabwiew config
        self.tabview_config = customtkinter.CTkTabview(self)
        self.tabview_config.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.tabview_config.add("GUI")
        self.tabview_config.add("Parameter")
        self.tabview_config.tab("GUI").grid_columnconfigure(0, weight=1)
        self.tabview_config.tab("Parameter").grid_columnconfigure(0, weight=1)
        self.tabview_config._segmented_button.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))

        # optionmenu translator
        self.label_translator = customtkinter.CTkLabel(
            self.tabview_config.tab("GUI"),
            text="Select Translator:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_translator.grid(row=0, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.optionmenu_translator = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("GUI"),
            values=["DeepL"],
            command=self.optionmenu_translator_callback,
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.optionmenu_translator.grid(row=0, column=1, columnspan=2 ,padx=(0, 5), pady=5, sticky="nsew")
        self.optionmenu_translator.set(CHOICE_TRANSLATOR)

        # optionmenu language
        self.label_language = customtkinter.CTkLabel(
            self.tabview_config.tab("GUI"),
            text="Select Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_language.grid(row=1, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.optionmenu_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("GUI"),
            command=self.optionmenu_language_callback,
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.optionmenu_language.grid(row=1, column=1, columnspan=2, padx=(0, 5), pady=5, sticky="nsew")
        self.optionmenu_language.configure(
            values=[
                "JA","BG","CS","DA","DE","EL","EN","EN-US","EN-GB","ES","ET","FI","FR","HU",
                "ID","IT","KO","LT","LV","NB","NL","PL","PT","PT-BR","PT-PT","RO","RU","SK",
                "SL","SV","TR","UK","ZH",
            ]
        )
        self.optionmenu_language.set(TARGET_LANG)

        # slider transparency
        self.label_transparency = customtkinter.CTkLabel(
            self.tabview_config.tab("GUI"),
            text="Transparency:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_transparency.grid(row=2, column=0, columnspan=1, padx=(0, 5), pady=5, sticky="nsew")
        self.slider_transparency = customtkinter.CTkSlider(
            self.tabview_config.tab("GUI"),
            from_=50,
            to=100,
            command=self.slider_transparency_callback
        )
        self.slider_transparency.grid(row=2, column=1, columnspan=2, padx=5, pady=10, sticky="nsew")
        self.slider_transparency.set(TRANSPARENCY)

        # optionmenu theme
        self.label_appearance_theme = customtkinter.CTkLabel(
            self.tabview_config.tab("GUI"),
            text="Appearance Theme:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_appearance_theme.grid(row=3, column=0, columnspan=1, padx=(0, 5), pady=5, sticky="nsew")
        self.optionmenu_appearance_theme = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("GUI"),
            values=["Light", "Dark", "System"],
            command=self.optionmenu_theme_callback
        )
        self.optionmenu_appearance_theme.grid(row=3, column=1, columnspan=2, padx=(0, 5), pady=5, sticky="nsew")
        self.optionmenu_appearance_theme.set(APPEARANCE_THEME)

        # optionmenu UI scaling
        self.label_ui_scaling = customtkinter.CTkLabel(
            self.tabview_config.tab("GUI"),
            text="UI Scaling:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_ui_scaling.grid(row=4, column=0, columnspan=1, padx=(0, 5), pady=5, sticky="nsew")
        self.optionmenu_ui_scaling = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("GUI"),
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.optionmenu_ui_scaling_callback
        )
        self.optionmenu_ui_scaling.grid(row=4, column=1, columnspan=2, padx=(0, 5), pady=5, sticky="nsew")
        self.optionmenu_ui_scaling.set(UI_SCALING)

        # optionmenu font family
        self.label_font_family = customtkinter.CTkLabel(
            self.tabview_config.tab("GUI"),
            text="Font Family:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_font_family.grid(row=5, column=0, columnspan=1, padx=(0, 5), pady=5, sticky="nsew")
        font_families = list(tk.font.families())
        self.optionmenu_font_family = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("GUI"),
            values=font_families,
            command=self.optionmenu_font_family_callback
        )
        self.optionmenu_font_family.grid(row=5, column=1, columnspan=2, padx=(0, 5), pady=5, sticky="nsew")
        self.optionmenu_font_family.set(FONT_FAMILY)

        # entry ip address
        self.label_ip_address = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="OSC IP address:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_ip_address.grid(row=0, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_ip_address = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            placeholder_text=OSC_IP_ADDRESS,
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.entry_ip_address.grid(row=0, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_ip_address = customtkinter.CTkButton(
            self.tabview_config.tab("Parameter"),
            text="",
            width=1,
            command=self.update_ip_address,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "save-icon.png")))
        )
        self.button_ip_address.grid(row=0, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

        # entry port
        self.label_port = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="OSC Port:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_port.grid(row=1, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_port = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            placeholder_text=OSC_PORT,
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.entry_port.grid(row=1, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_port = customtkinter.CTkButton(
            self.tabview_config.tab("Parameter"),
            text="",
            width=1,
            command=self.update_port,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "save-icon.png")))
        )
        self.button_port.grid(row=1, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

        # entry authkey
        self.label_authkey = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="DeepL Auth Key:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_authkey.grid(row=2, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_authkey = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            placeholder_text=AUTH_KEY,
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.entry_authkey.grid(row=2, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_authkey = customtkinter.CTkButton(
            self.tabview_config.tab("Parameter"),
            text="",
            width=1,
            command=self.update_authkey,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "save-icon.png")))
        )
        self.button_authkey.grid(row=2, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

        # entry message format
        self.label_message_format = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="Message Format:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.label_message_format.grid(row=3, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_message_format = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            placeholder_text=MESSAGE_FORMAT,
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.entry_message_format.grid(row=3, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_message_format = customtkinter.CTkButton(
            self.tabview_config.tab("Parameter"),
            text="",
            width=1,
            command=self.update_message_format,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "save-icon.png")))
        )
        self.button_message_format.grid(row=3, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

    def update_ip_address(self):
        value = self.entry_ip_address.get()
        if len(value) > 0:
            global OSC_IP_ADDRESS
            OSC_IP_ADDRESS = value
            with open(PATH_CONFIG, "r") as fp:
                config = json.load(fp)
            config["OSC_IP_ADDRESS"] = OSC_IP_ADDRESS
            with open(PATH_CONFIG, "w") as fp:
                json.dump(config, fp, indent=4)

    def update_port(self):
        value = self.entry_port.get()
        if len(value) > 0:
            global OSC_PORT
            OSC_PORT = value
            with open(PATH_CONFIG, "r") as fp:
                config = json.load(fp)
            config["OSC_PORT"] = OSC_PORT
            with open(PATH_CONFIG, "w") as fp:
                json.dump(config, fp, indent=4)

    def update_authkey(self):
        value = self.entry_authkey.get()
        if len(value) > 0:
            global AUTH_KEY
            global TRANSLATOR
            AUTH_KEY = value
            with open(PATH_CONFIG, "r") as fp:
                config = json.load(fp)
            config["AUTH_KEY"] = AUTH_KEY
            with open(PATH_CONFIG, "w") as fp:
                json.dump(config, fp, indent=4)

            TRANSLATOR = deepl.Translator(AUTH_KEY)
            self.parent.textbox_message_log.configure(state='normal')
            self.parent.textbox_message_log.delete("0.0", "end")
            self.parent.textbox_message_log.configure(state='disabled')
            try:
                TRANSLATOR.translate_text(" ", target_lang="EN-US")
            except:
                TRANSLATOR = None
                self.parent.textbox_message_log.configure(state='normal')
                self.parent.textbox_message_log.insert("0.0", f"Auth Keyを設定してないか間違っています\n")
                self.parent.textbox_message_log.configure(state='disabled')

    def update_message_format(self):
        value = self.entry_message_format.get()
        if len(value) > 0:
            global MESSAGE_FORMAT
            MESSAGE_FORMAT = value
            with open(PATH_CONFIG, "r") as fp:
                config = json.load(fp)
            config["MESSAGE_FORMAT"] = MESSAGE_FORMAT
            with open(PATH_CONFIG, "w") as fp:
                json.dump(config, fp, indent=4)

    def slider_transparency_callback(self, value):
        global TRANSPARENCY
        TRANSPARENCY = value
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["TRANSPARENCY"] = TRANSPARENCY
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)
        self.parent.wm_attributes("-alpha", TRANSPARENCY/100)

    def optionmenu_translator_callback(self, choice):
        global CHOICE_TRANSLATOR
        CHOICE_TRANSLATOR = choice
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["CHOICE_TRANSLATOR"] = CHOICE_TRANSLATOR
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

    def optionmenu_language_callback(self, choice):
        global TARGET_LANG
        TARGET_LANG = choice
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["TARGET_LANG"] = TARGET_LANG
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

    def optionmenu_theme_callback(self, choice):
        global APPEARANCE_THEME
        APPEARANCE_THEME = choice
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["APPEARANCE_THEME"] = APPEARANCE_THEME
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)
        customtkinter.set_appearance_mode(APPEARANCE_THEME)

    def optionmenu_ui_scaling_callback(self, choice):
        global UI_SCALING
        UI_SCALING = choice
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["UI_SCALING"] = UI_SCALING
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)
        new_scaling_float = int(UI_SCALING.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def optionmenu_font_family_callback(self, choice):
        global FONT_FAMILY
        FONT_FAMILY = choice
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["FONT_FAMILY"] = FONT_FAMILY
        with open(PATH_CONFIG, "w") as fp:
            json.dump(config, fp, indent=4)

        self.parent.checkbox_translation.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.parent.checkbox_foreground.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.parent.textbox_message_log.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.parent.entry_message_box.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.parent.information_window.textbox_information.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.tabview_config._segmented_button.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_translator.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.optionmenu_translator.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_language.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.optionmenu_language.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_transparency.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_appearance_theme.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.optionmenu_appearance_theme.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_ui_scaling.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.optionmenu_ui_scaling.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_font_family.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.optionmenu_font_family.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_ip_address.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.entry_ip_address.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_port.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.entry_port.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_authkey.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.entry_authkey.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.label_message_format.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))
        self.entry_message_format.configure(font=customtkinter.CTkFont(family=FONT_FAMILY))

class App(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(os.path.join(os.path.dirname(__file__), "img", "app.ico"))
        self.title("VRCT")
        self.geometry(f"{400}x{110}")
        self.minsize(400, 110)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # sidebar left
        self.sidebar_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # checkbox translation
        self.checkbox_translation = customtkinter.CTkCheckBox(
            self.sidebar_frame,
            text="translation",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_translation_callback,
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.checkbox_translation.grid(row=0, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # checkbox foreground
        self.checkbox_foreground = customtkinter.CTkCheckBox(
            self.sidebar_frame,
            text="foreground",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_foreground_callback,
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.checkbox_foreground.grid(row=1, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # button information
        self.button_information = customtkinter.CTkButton(
            self.sidebar_frame,
            text="",
            width=25,
            command=self.open_information,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "info-icon-white.png")))
        )
        self.button_information.grid(row=5, column=0, padx=(10, 5), pady=(5, 5), sticky="wse")
        self.information_window = None

        # button config
        self.button_config = customtkinter.CTkButton(
            self.sidebar_frame,
            text="",
            width=25,
            command=self.open_config,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "config-icon-white.png")))
        )
        self.button_config.grid(row=5, column=1, padx=(5, 10), pady=(5, 5), sticky="wse")
        self.config_window = None

        # create textbox message log
        self.textbox_message_log = customtkinter.CTkTextbox(
            self,
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
        self.textbox_message_log.grid(row=0, column=1, padx=(10, 10), pady=(10, 5), sticky="nsew")
        self.textbox_message_log.configure(state='disabled')

        # create entry message box
        self.entry_message_box = customtkinter.CTkEntry(
            self,
            placeholder_text="message",
            font=customtkinter.CTkFont(family=FONT_FAMILY)
        )
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

        self.entry_message_box.bind("<Return>", self.entry_message_box_press_key_enter)

        if TRANSLATOR is None:
            # error update Auth key
            self.textbox_message_log.configure(state='normal')
            self.textbox_message_log.insert("0.0", f"Auth Keyを設定してないか間違っています\n")
            self.textbox_message_log.configure(state='disabled')

        self.wm_attributes("-alpha", TRANSPARENCY/100)

    def open_config(self):
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = ToplevelWindowConfig(self)
        self.config_window.focus()

    def open_information(self):
        if self.information_window is None or not self.information_window.winfo_exists():
            self.information_window = ToplevelWindowInformation(self)
        self.information_window.focus()

    def checkbox_translation_callback(self):
        global ENABLE_TRANSLATION
        ENABLE_TRANSLATION = self.checkbox_translation.get()
        with open(PATH_CONFIG, "r") as fp:
            config = json.load(fp)
        config["ENABLE_TRANSLATION"] = ENABLE_TRANSLATION
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

    def entry_message_box_press_key_enter(self, event):
        message = self.entry_message_box.get()
        if len(message) > 0:
            # translate
            if (self.checkbox_translation.get() is True) and (TRANSLATOR is not None):
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