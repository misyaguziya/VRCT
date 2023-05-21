import json
import deepl
from pythonosc import osc_message_builder
from pythonosc import udp_client
import customtkinter

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("VRC ChatBox translator")
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
        self.token_input_button = customtkinter.CTkButton(self.sidebar_frame, text="auth key", command=self.open_token_input_button_event)
        self.token_input_button.grid(row=5, column=0, padx=10, pady=(10, 10), sticky="s")

        # create textbox
        self.textbox = customtkinter.CTkTextbox(self)
        self.textbox.grid(row=0, column=1, padx=(10, 10), pady=(10, 5), sticky="nsew")

        # create entry
        self.entry = customtkinter.CTkEntry(self, placeholder_text="message")
        self.entry.grid(row=1, column=1, columnspan=2, padx=(10, 10), pady=(5, 10), sticky="nsew")

        # set default values
        self.combobox_translator.configure(values=["DeepL",  "None"],)
        self.combobox_language.configure(values=[
                "EN-US","JA","BG","CS","DA","DE","EL","EN","EN-GB","ES","ET","FI","FR","HU",
                "ID","IT","KO","LT","LV","NB","NL","PL","PT","PT-BR","PT-PT","RO","RU","SK",
                "SL","SV","TR","UK","ZH",
            ],)
        self.entry.bind("<Return>", self.press_key)

        # setting OSC
        self.ip_address = "127.0.0.1"
        self.port = 9000

        # setting DeepL
        try:
            with open('./setting.json', 'r') as fp:
                self.auth_key = json.load(fp)["auth_key"]
            self.translator = deepl.Translator(self.auth_key)
        except:
            self.textbox.insert("0.0", f"auth key を設定してください\n")

        self.target_lang = 'EN-US'
        self.combobox_language.set(self.target_lang)
        self.choice_translator = 'DeepL'
        self.combobox_translator.set(self.choice_translator)

    def combobox_translator_callback(self, choice):
        self.choice_translator = choice

    def combobox_language_callback(self, choice):
        self.target_lang = choice

    def open_token_input_button_event(self):
        dialog = customtkinter.CTkInputDialog(text="Type auth key:", title="auth key")
        input = dialog.get_input()

        if input != "":
            with open('./setting.json', 'w') as fp:
                json.dump({'auth_key': input}, fp, indent=4)

            self.auth_key = input
            self.translator = deepl.Translator(self.auth_key)

    def press_key(self, event):
        entry = self.entry.get()

        # translate
        if self.choice_translator != "None":
            result = self.translator.translate_text(entry, target_lang=self.target_lang)
            chat_message = f"{entry} ({result.text})"
        else:
            chat_message = f"{entry}"

        # send OSC message
        message = osc_message_builder.OscMessageBuilder(address="/chatbox/input")
        message.add_arg(f"{chat_message}")
        message.add_arg(True)
        message.add_arg(True)
        message = message.build()
        client = udp_client.SimpleUDPClient(self.ip_address, self.port)
        client.send(message)

        # delete Entry message
        self.textbox.insert("0.0", f"{chat_message}\n")
        self.entry.delete(0, customtkinter.END)

app = App()
app.mainloop()