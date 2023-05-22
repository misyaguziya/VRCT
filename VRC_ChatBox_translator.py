import os
import json
import deepl
from pythonosc import osc_message_builder
from pythonosc import udp_client
import customtkinter

# global
OSC_IP_ADDRESS = "127.0.0.1"
OSC_PORT = 9000
TARGET_LANG = "EN-US"
CHOICE_TRANSLATOR = "DeepL"
AUTH_KEY = None
TRANSLATOR = None
PATH_CONFIG = "./config.json"

# load config
if os.path.isfile(PATH_CONFIG) is False:
    with open(PATH_CONFIG, 'w') as fp:
        config = {
            "OSC_IP_ADDRESS": "127.0.0.1",
            "OSC_PORT": 9000,
            "TARGET_LANG": "EN-US",
            "CHOICE_TRANSLATOR": "DeepL",
            "AUTH_KEY": None
        }
        json.dump(config, fp, indent=4)

with open(PATH_CONFIG, 'r') as fp:
    config = json.load(fp)
if "OSC_IP_ADDRESS" in config.keys():
    OSC_IP_ADDRESS = config["OSC_IP_ADDRESS"]
if "OSC_PORT" in config.keys():
    OSC_PORT = config["OSC_PORT"]
if "TARGET_LANG" in config.keys():
    TARGET_LANG = config["TARGET_LANG"]
if "CHOICE_TRANSLATOR" in config.keys():
    CHOICE_TRANSLATOR = config["CHOICE_TRANSLATOR"]
if "AUTH_KEY" in config.keys():
    AUTH_KEY = config["AUTH_KEY"]

# deepl connect
if AUTH_KEY is not None:
    TRANSLATOR = deepl.Translator(AUTH_KEY)

# GUI
customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class ToplevelWindow_config(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry(f"{280}x{150}")
        self.resizable(False, False)

        self.title("Config")
        self.label_ip_address = customtkinter.CTkLabel(self, text="OSC IP address:", fg_color="transparent")
        self.label_ip_address.grid(row=0, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_ip_address = customtkinter.CTkEntry(self, placeholder_text=OSC_IP_ADDRESS)
        self.entry_ip_address.grid(row=0, column=2, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_ip_address = customtkinter.CTkButton(self, text="✓", width=1, command=self.update_ip_address)
        self.button_ip_address.grid(row=0, column=3, columnspan=1, padx=1, pady=5, sticky="nsew")

        self.label_port = customtkinter.CTkLabel(self, text="OSC Port:", fg_color="transparent")
        self.label_port.grid(row=1, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_port = customtkinter.CTkEntry(self, placeholder_text=OSC_PORT)
        self.entry_port.grid(row=1, column=2, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_port = customtkinter.CTkButton(self, text="✓", width=1, command=self.update_port)
        self.button_port.grid(row=1, column=3, columnspan=1, padx=1, pady=5, sticky="nsew")

        self.label_authkey = customtkinter.CTkLabel(self, text="DeepL Auth Key:", fg_color="transparent")
        self.label_authkey.grid(row=2, column=0, columnspan=1, padx=5, pady=5, sticky="nsew")
        self.entry_authkey = customtkinter.CTkEntry(self, placeholder_text=AUTH_KEY)
        self.entry_authkey.grid(row=2, column=2, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_authkey = customtkinter.CTkButton(self, text="✓", width=1, command=self.update_authkey)
        self.button_authkey.grid(row=2, column=3, columnspan=1, padx=1, pady=5, sticky="nsew")

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
        try:
            TRANSLATOR = deepl.Translator(AUTH_KEY)
        except:
            TRANSLATOR = None

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("VRC ChatBox Translator")
        self.geometry(f"{400}x{180}")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # sidebar left
        self.sidebar_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.combobox_translator = customtkinter.CTkComboBox(self.sidebar_frame, command=self.combobox_translator_callback)
        self.combobox_translator.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.combobox_language = customtkinter.CTkComboBox(self.sidebar_frame, command=self.combobox_language_callback)
        self.combobox_language.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="w")
        self.button_config = customtkinter.CTkButton(self.sidebar_frame, text="config", command=self.open_config)
        self.button_config.grid(row=4, column=0, padx=10, pady=(10, 10), sticky="s")
        self.config_window = None

        # create textbox
        self.textbox = customtkinter.CTkTextbox(self)
        self.textbox.grid(row=0, column=1, padx=(10, 10), pady=(10, 5), sticky="nsew")

        # create entry
        self.entry = customtkinter.CTkEntry(self, placeholder_text="message")
        self.entry.grid(row=1, column=1, columnspan=2, padx=(10, 10), pady=(5, 10), sticky="nsew")

        # set default values
        self.combobox_translator.configure(values=["DeepL",  "Disable"],)
        self.combobox_language.configure(values=[
                "JA","BG","CS","DA","DE","EL","EN","EN-US","EN-GB","ES","ET","FI","FR","HU",
                "ID","IT","KO","LT","LV","NB","NL","PL","PT","PT-BR","PT-PT","RO","RU","SK",
                "SL","SV","TR","UK","ZH",
            ],)
        self.entry.bind("<Return>", self.press_key)

        if TRANSLATOR is None:
            self.textbox.insert("0.0", f"Auth Keyを設定してください\n")

        self.combobox_language.set(TARGET_LANG)
        self.combobox_translator.set(CHOICE_TRANSLATOR)


    def open_config(self):
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = ToplevelWindow_config(self)
        self.config_window.focus()

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

    def press_key(self, event):
        if TRANSLATOR is None:
            self.textbox.insert("0.0", f"Auth Keyを設定してください\n")
        else:
            entry = self.entry.get()

            # translate
            if CHOICE_TRANSLATOR != "Disable":
                result = TRANSLATOR.translate_text(entry, target_lang=TARGET_LANG)
                chat_message = f"{entry} ({result.text})"
            else:
                chat_message = f"{entry}"

            # send OSC message
            message = osc_message_builder.OscMessageBuilder(address="/chatbox/input")
            message.add_arg(f"{chat_message}")
            message.add_arg(True)
            message.add_arg(True)
            message = message.build()
            client = udp_client.SimpleUDPClient(OSC_IP_ADDRESS, OSC_PORT)
            client.send(message)

            # delete Entry message
            self.textbox.insert("0.0", f"{chat_message}\n")
            self.entry.delete(0, customtkinter.END)

app = App()
app.mainloop()