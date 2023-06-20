import os
import json
import queue
import time
import customtkinter
from PIL import Image

import utils
import translation
import transcription
import osc_tools
import window_config
import window_information

class App(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # init config
        self.PATH_CONFIG = "./config.json"
        ## main window
        self.ENABLE_TRANSLATION = False
        self.ENABLE_TRANSCRIPTION_SEND = False
        self.ENABLE_TRANSCRIPTION_RECEIVE = False
        self.ENABLE_FOREGROUND = False
        ## UI
        self.TRANSPARENCY = 100
        self.APPEARANCE_THEME = "System"
        self.UI_SCALING = "100%"
        self.FONT_FAMILY = "Yu Gothic UI"
        ## Translation
        self.CHOICE_TRANSLATOR = "DeepL(web)"
        self.INPUT_SOURCE_LANG = "JA"
        self.INPUT_TARGET_LANG = "EN"
        self.OUTPUT_SOURCE_LANG = "EN"
        self.OUTPUT_TARGET_LANG = "JA"
        ## Transcription
        self.CHOICE_MIC_DEVICE = None
        self.INPUT_MIC_VOICE_LANGUAGE = "ja-JP"
        self.INPUT_MIC_IS_DYNAMIC = False
        self.INPUT_MIC_THRESHOLD = 300
        self.CHOICE_SPEAKER_DEVICE = None
        self.INPUT_SPEAKER_VOICE_LANGUAGE = "en-US"
        self.INPUT_SPEAKER_SAMPLING_RATE = 16000
        self.INPUT_SPEAKER_INTERVAL = 4
        self.INPUT_SPEAKER_BUFFER_SIZE = 4096

        ## Parameter
        self.OSC_IP_ADDRESS = "127.0.0.1"
        self.OSC_PORT = 9000
        self.AUTH_KEYS = {
            "DeepL(web)": None,
            "DeepL(auth)": None,
            "Bing(web)": None,
            "Google(web)": None,
        }
        self.MESSAGE_FORMAT = "[message]([translation])"

        # load config
        if os.path.isfile(self.PATH_CONFIG) is not False:
            with open(self.PATH_CONFIG, 'r') as fp:
                config = json.load(fp)
            # main window
            if "ENABLE_TRANSLATION" in config.keys():
                self.ENABLE_TRANSLATION = config["ENABLE_TRANSLATION"]
            if "ENABLE_TRANSCRIPTION_SEND" in config.keys():
                self.ENABLE_TRANSCRIPTION_SEND = config["ENABLE_TRANSCRIPTION_SEND"]
            if "ENABLE_TRANSCRIPTION_RECEIVE" in config.keys():
                self.ENABLE_TRANSCRIPTION_RECEIVE = config["ENABLE_TRANSCRIPTION_RECEIVE"]
            if "ENABLE_FOREGROUND" in config.keys():
                self.ENABLE_FOREGROUND = config["ENABLE_FOREGROUND"]

            # tab ui
            if "TRANSPARENCY" in config.keys():
                self.TRANSPARENCY = config["TRANSPARENCY"]
            if "APPEARANCE_THEME" in config.keys():
                self.APPEARANCE_THEME = config["APPEARANCE_THEME"]
            if "UI_SCALING" in config.keys():
                self.UI_SCALING = config["UI_SCALING"]
            if "FONT_FAMILY" in config.keys():
                self.FONT_FAMILY = config["FONT_FAMILY"]

            # translation
            if "CHOICE_TRANSLATOR" in config.keys():
                self.CHOICE_TRANSLATOR = config["CHOICE_TRANSLATOR"]
            if "INPUT_SOURCE_LANG" in config.keys():
                self.INPUT_SOURCE_LANG = config["INPUT_SOURCE_LANG"]
            if "INPUT_TARGET_LANG" in config.keys():
                self.INPUT_TARGET_LANG = config["INPUT_TARGET_LANG"]
            if "OUTPUT_SOURCE_LANG" in config.keys():
                self.OUTPUT_SOURCE_LANG = config["OUTPUT_SOURCE_LANG"]
            if "OUTPUT_TARGET_LANG" in config.keys():
                self.OUTPUT_TARGET_LANG = config["OUTPUT_TARGET_LANG"]

            # Transcription
            if "CHOICE_MIC_DEVICE" in config.keys():
                self.CHOICE_MIC_DEVICE = config["CHOICE_MIC_DEVICE"]
            if "INPUT_MIC_VOICE_LANGUAGE" in config.keys():
                self.INPUT_MIC_VOICE_LANGUAGE = config["INPUT_MIC_VOICE_LANGUAGE"]
            if "INPUT_MIC_IS_DYNAMIC" in config.keys():
                self.INPUT_MIC_IS_DYNAMIC = config["INPUT_MIC_IS_DYNAMIC"]
            if "INPUT_MIC_THRESHOLD" in config.keys():
                self.INPUT_MIC_THRESHOLD = config["INPUT_MIC_THRESHOLD"]
            if "CHOICE_SPEAKER_DEVICE" in config.keys():
                self.CHOICE_SPEAKER_DEVICE = config["CHOICE_SPEAKER_DEVICE"]
            if "INPUT_SPEAKER_VOICE_LANGUAGE" in config.keys():
                self.INPUT_SPEAKER_VOICE_LANGUAGE = config["INPUT_SPEAKER_VOICE_LANGUAGE"]
            if "INPUT_SPEAKER_SAMPLING_RATE" in config.keys():
                self.INPUT_SPEAKER_SAMPLING_RATE = config["INPUT_SPEAKER_SAMPLING_RATE"]
            if "INPUT_SPEAKER_INTERVAL" in config.keys():
                self.INPUT_SPEAKER_INTERVAL = config["INPUT_SPEAKER_INTERVAL"]
            if "INPUT_SPEAKER_BUFFER_SIZE" in config.keys():
                self.INPUT_SPEAKER_BUFFER_SIZE = config["INPUT_SPEAKER_BUFFER_SIZE"]

            # Parameter
            if "OSC_IP_ADDRESS" in config.keys():
                self.OSC_IP_ADDRESS = config["OSC_IP_ADDRESS"]
            if "OSC_PORT" in config.keys():
                self.OSC_PORT = config["OSC_PORT"]
            if "AUTH_KEYS" in config.keys():
                self.AUTH_KEYS = config["AUTH_KEYS"]
            if "MESSAGE_FORMAT" in config.keys():
                self.MESSAGE_FORMAT = config["MESSAGE_FORMAT"]

        with open(self.PATH_CONFIG, 'w') as fp:
            config = {
                "ENABLE_TRANSLATION": self.ENABLE_TRANSLATION,
                "ENABLE_TRANSCRIPTION_SEND": self.ENABLE_TRANSCRIPTION_SEND,
                "ENABLE_TRANSCRIPTION_RECEIVE": self.ENABLE_TRANSCRIPTION_RECEIVE,
                "ENABLE_FOREGROUND": self.ENABLE_FOREGROUND,
                "TRANSPARENCY": self.TRANSPARENCY,
                "APPEARANCE_THEME": self.APPEARANCE_THEME,
                "UI_SCALING": self.UI_SCALING,
                "FONT_FAMILY": self.FONT_FAMILY,
                "CHOICE_TRANSLATOR": self.CHOICE_TRANSLATOR,
                "INPUT_SOURCE_LANG": self.INPUT_SOURCE_LANG,
                "INPUT_TARGET_LANG": self.INPUT_TARGET_LANG,
                "OUTPUT_SOURCE_LANG": self.OUTPUT_SOURCE_LANG,
                "OUTPUT_TARGET_LANG": self.OUTPUT_TARGET_LANG,
                "CHOICE_MIC_DEVICE": self.CHOICE_MIC_DEVICE,
                "INPUT_MIC_VOICE_LANGUAGE": self.INPUT_MIC_VOICE_LANGUAGE,
                "INPUT_MIC_IS_DYNAMIC": self.INPUT_MIC_IS_DYNAMIC,
                "INPUT_MIC_THRESHOLD": self.INPUT_MIC_THRESHOLD,
                "CHOICE_SPEAKER_DEVICE": self.CHOICE_SPEAKER_DEVICE,
                "INPUT_SPEAKER_VOICE_LANGUAGE": self.INPUT_SPEAKER_VOICE_LANGUAGE,
                "INPUT_SPEAKER_SAMPLING_RATE": self.INPUT_SPEAKER_SAMPLING_RATE,
                "INPUT_SPEAKER_INTERVAL": self.INPUT_SPEAKER_INTERVAL,
                "INPUT_SPEAKER_BUFFER_SIZE": self.INPUT_SPEAKER_BUFFER_SIZE,
                "OSC_IP_ADDRESS": self.OSC_IP_ADDRESS,
                "OSC_PORT": self.OSC_PORT,
                "AUTH_KEYS": self.AUTH_KEYS,
                "MESSAGE_FORMAT": self.MESSAGE_FORMAT,
            }
            json.dump(config, fp, indent=4)

        ## set UI theme
        customtkinter.set_appearance_mode(self.APPEARANCE_THEME)
        customtkinter.set_default_color_theme("blue")

        # init main window
        self.iconbitmap(os.path.join(os.path.dirname(__file__), "img", "app.ico"))
        self.title("VRCT")
        self.geometry(f"{400}x{175}")
        self.minsize(400, 175)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # add sidebar left
        self.sidebar_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # add checkbox translation
        self.checkbox_translation = customtkinter.CTkCheckBox(
            self.sidebar_frame,
            text="translation",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_translation_callback,
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_translation.grid(row=0, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # add checkbox transcription send
        self.checkbox_transcription_send = customtkinter.CTkCheckBox(
            self.sidebar_frame,
            text="voice2chatbox",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_transcription_send_callback,
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_transcription_send.grid(row=1, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # add checkbox transcription receive
        self.checkbox_transcription_receive = customtkinter.CTkCheckBox(
            self.sidebar_frame,
            text="speaker2log",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_transcription_receive_callback,
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_transcription_receive.grid(row=2, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # add checkbox foreground
        self.checkbox_foreground = customtkinter.CTkCheckBox(
            self.sidebar_frame,
            text="foreground",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_foreground_callback,
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_foreground.grid(row=3, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # add button information
        self.button_information = customtkinter.CTkButton(
            self.sidebar_frame,
            text="",
            width=25,
            command=self.button_information_callback,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "info-icon-white.png")))
        )
        self.button_information.grid(row=5, column=0, padx=(10, 5), pady=(5, 5), sticky="wse")
        self.information_window = None

        # add button config
        self.button_config = customtkinter.CTkButton(
            self.sidebar_frame,
            text="",
            width=25,
            command=self.button_config_callback,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "config-icon-white.png")))
        )
        self.button_config.grid(row=5, column=1, padx=(5, 10), pady=(5, 5), sticky="wse")
        self.config_window = None

        # add tabview textbox
        self.tabview_logs = customtkinter.CTkTabview(master=self)
        self.tabview_logs.add("log")
        self.tabview_logs.add("send")
        self.tabview_logs.add("receive")
        self.tabview_logs.add("system")
        self.tabview_logs.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        self.tabview_logs._segmented_button.grid(sticky="W")
        self.tabview_logs.tab("log").grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab("log").grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab("send").grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab("send").grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab("receive").grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab("receive").grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab("system").grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab("system").grid_columnconfigure(0, weight=1)
        self.tabview_logs.configure(fg_color="transparent")

        # add textbox message log
        self.textbox_message_log = customtkinter.CTkTextbox(
            self.tabview_logs.tab("log"),
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_log.configure(state='disabled')

        # add textbox message send log
        self.textbox_message_send_log = customtkinter.CTkTextbox(
            self.tabview_logs.tab("send"),
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_send_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_send_log.configure(state='disabled')

        # add textbox message receive log
        self.textbox_message_receive_log = customtkinter.CTkTextbox(
            self.tabview_logs.tab("receive"),
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_receive_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_receive_log.configure(state='disabled')

        # add textbox message system log
        self.textbox_message_system_log = customtkinter.CTkTextbox(
            self.tabview_logs.tab("system"),
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_system_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_system_log.configure(state='disabled')

        # add entry message box
        self.entry_message_box = customtkinter.CTkEntry(
            self,
            placeholder_text="message",
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.entry_message_box.grid(row=1, column=1, columnspan=2, padx=5, pady=(5, 10), sticky="nsew")

        # set default values
        ## set translator instance
        self.translator = translation.Translator()
        if self.translator.authentication(self.CHOICE_TRANSLATOR, self.AUTH_KEYS[self.CHOICE_TRANSLATOR]) is False:
            # error update Auth key
            utils.print_textbox(self.textbox_message_log, "Auth Key or language setting is incorrect", "ERROR")
            utils.print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")

        ## set transcription instance
        self.mic_queue = queue.Queue()
        self.spk_queue = queue.Queue()
        self.vr = transcription.VoiceRecognizer(self.mic_queue, self.spk_queue)
        self.CHOICE_MIC_DEVICE = self.CHOICE_MIC_DEVICE if self.CHOICE_MIC_DEVICE is not None else self.vr.search_default_device()[0]
        self.CHOICE_SPEAKER_DEVICE = self.CHOICE_SPEAKER_DEVICE if self.CHOICE_SPEAKER_DEVICE is not None else self.vr.search_default_device()[1]

        ## set checkbox enable translation
        if self.ENABLE_TRANSLATION:
            self.checkbox_translation.select()
            self.checkbox_translation_callback()
        else:
            self.checkbox_translation.deselect()

        ## set checkbox enable transcription send
        self.th_vr_listen_mic = None
        self.th_vr_recognize_mic = None
        if self.ENABLE_TRANSCRIPTION_SEND:
            self.checkbox_transcription_send.select()
            self.checkbox_transcription_send_callback()
        else:
            self.checkbox_transcription_send.deselect()

        ## set checkbox enable transcription receive
        self.th_vr_listen_spk = None
        self.th_vr_recognize_spk = None
        if self.ENABLE_TRANSCRIPTION_RECEIVE:
            self.checkbox_transcription_receive.select()
            self.checkbox_transcription_receive_callback()
        else:
            self.checkbox_transcription_receive.deselect()

        ## set set checkbox enable foreground
        if self.ENABLE_FOREGROUND:
            self.checkbox_foreground.select()
            self.checkbox_foreground_callback()
        else:
            self.checkbox_foreground.deselect()

        ## set bind entry message box
        self.entry_message_box.bind("<Return>", self.entry_message_box_press_key_enter)
        self.entry_message_box.bind("<Any-KeyPress>", self.entry_message_box_press_key_any)
        self.entry_message_box.bind("<Leave>", self.entry_message_box_leave)

        ## set transparency for main window
        self.wm_attributes("-alpha", self.TRANSPARENCY/100)

        ## set UI scale
        new_scaling_float = int(self.UI_SCALING.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

        # delete window
        self.protocol("WM_DELETE_WINDOW", self.delete_window)

    def button_config_callback(self):
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = window_config.ToplevelWindowConfig(self)
        self.config_window.focus()

    def button_information_callback(self):
        if self.information_window is None or not self.information_window.winfo_exists():
            self.information_window = window_information.ToplevelWindowInformation(self)
        self.information_window.focus()

    def checkbox_translation_callback(self):
        self.ENABLE_TRANSLATION = self.checkbox_translation.get()
        if self.ENABLE_TRANSLATION:
            utils.print_textbox(self.textbox_message_log, "Start translation", "INFO")
            utils.print_textbox(self.textbox_message_system_log, "Start translation", "INFO")
        else:
            utils.print_textbox(self.textbox_message_log, "Stop translation", "INFO")
            utils.print_textbox(self.textbox_message_system_log, "Stop translation", "INFO")
        utils.save_json(self.PATH_CONFIG, "ENABLE_TRANSLATION", self.ENABLE_TRANSLATION)

    def checkbox_transcription_send_callback(self):
        self.ENABLE_TRANSCRIPTION_SEND = self.checkbox_transcription_send.get()
        if self.ENABLE_TRANSCRIPTION_SEND is True:
            utils.print_textbox(self.textbox_message_log, "Start voice2chatbox", "INFO")
            utils.print_textbox(self.textbox_message_system_log, "Start voice2chatbox", "INFO")
            # start threading
            self.vr.set_mic(
                device_name=self.CHOICE_MIC_DEVICE,
                threshold=int(self.INPUT_MIC_THRESHOLD),
                is_dynamic=self.INPUT_MIC_IS_DYNAMIC,
                language=self.INPUT_MIC_VOICE_LANGUAGE,
            )
            self.vr.init_mic()
            self.th_vr_listen_mic = utils.thread_fnc(self.vr_listen_mic)
            self.th_vr_recognize_mic = utils.thread_fnc(self.vr_recognize_mic)
            self.th_vr_listen_mic.start()
            self.th_vr_recognize_mic.start()
        else:
            if isinstance(self.th_vr_listen_mic, utils.thread_fnc):
                self.th_vr_listen_mic.stop()
            if isinstance(self.th_vr_recognize_mic, utils.thread_fnc):
                self.th_vr_recognize_mic.stop()

            utils.print_textbox(self.textbox_message_log, "Stop voice2chatbox", "INFO")
            utils.print_textbox(self.textbox_message_system_log, "Stop voice2chatbox", "INFO")
        utils.save_json(self.PATH_CONFIG, "ENABLE_TRANSCRIPTION_SEND", self.ENABLE_TRANSCRIPTION_SEND)

    def checkbox_transcription_receive_callback(self):
        self.ENABLE_TRANSCRIPTION_RECEIVE = self.checkbox_transcription_receive.get()
        if self.ENABLE_TRANSCRIPTION_RECEIVE is True:
            utils.print_textbox(self.textbox_message_log,  "Start speaker2log", "INFO")
            utils.print_textbox(self.textbox_message_system_log, "Start speaker2log", "INFO")

            self.vr.set_spk(
                device_name=self.CHOICE_SPEAKER_DEVICE,
                interval=int(self.INPUT_SPEAKER_INTERVAL),
                language=self.INPUT_SPEAKER_VOICE_LANGUAGE,
            )
            self.vr.start_spk_recording()
            self.th_vr_recognize_spk = utils.thread_fnc(self.vr_recognize_spk)
            self.th_vr_recognize_spk.start()
        else:
            if self.vr.spk_stream is not None:
                self.vr.close_spk_stream()
            if isinstance(self.th_vr_recognize_spk, utils.thread_fnc):
                self.th_vr_recognize_spk.stop()

            utils.print_textbox(self.textbox_message_log,  "Stop speaker2log", "INFO")
            utils.print_textbox(self.textbox_message_system_log, "Stop speaker2log", "INFO")
        utils.save_json(self.PATH_CONFIG, "ENABLE_TRANSCRIPTION_RECEIVE", self.ENABLE_TRANSCRIPTION_RECEIVE)

    def vr_listen_mic(self):
        self.vr.listen_mic()

    def vr_recognize_mic(self):
        message = self.vr.recognize_mic()
        if len(message) > 0:
            # translate
            if self.checkbox_translation.get() is False:
                voice_message = f"{message}"
            elif self.translator.translator_status[self.CHOICE_TRANSLATOR] is False:
                utils.print_textbox(self.textbox_message_log,  "Auth Key or language setting is incorrect", "ERROR")
                utils.print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
                voice_message = f"{message}"
            else:
                result = self.translator.translate(
                    translator_name=self.CHOICE_TRANSLATOR,
                    source_language=self.INPUT_SOURCE_LANG,
                    target_language=self.INPUT_TARGET_LANG,
                    message=message
                )
                voice_message = self.MESSAGE_FORMAT.replace("[message]", message).replace("[translation]", result)
            # send OSC message
            osc_tools.send_message(voice_message, self.OSC_IP_ADDRESS, self.OSC_PORT)
            # update textbox message log
            utils.print_textbox(self.textbox_message_log,  f"{voice_message}", "SEND")
            utils.print_textbox(self.textbox_message_send_log, f"{voice_message}", "SEND")

    def vr_listen_spk(self):
        self.vr.listen_spk()

    def vr_recognize_spk(self):
        message = self.vr.recognize_spk()
        if len(message) > 0:
            # translate
            if self.checkbox_translation.get() is False:
                voice_message = f"{message}"
            elif self.translator.translator_status[self.CHOICE_TRANSLATOR] is False:
                utils.print_textbox(self.textbox_message_log,  "Auth Key or language setting is incorrect", "ERROR")
                utils.print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
                voice_message = f"{message}"
            else:
                result = self.translator.translate(
                    translator_name=self.CHOICE_TRANSLATOR,
                    source_language=self.OUTPUT_SOURCE_LANG,
                    target_language=self.OUTPUT_TARGET_LANG,
                    message=message
                )
                voice_message = self.MESSAGE_FORMAT.replace("[message]", message).replace("[translation]", result)
            # send OSC message
            # osc_tools.send_message(voice_message, self.OSC_IP_ADDRESS, self.OSC_PORT)
            # update textbox message receive log
            utils.print_textbox(self.textbox_message_log,  f"{voice_message}", "RECEIVE")
            utils.print_textbox(self.textbox_message_receive_log, f"{voice_message}", "RECEIVE")

    def checkbox_foreground_callback(self):
        self.ENABLE_FOREGROUND = self.checkbox_foreground.get()
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)
            utils.print_textbox(self.textbox_message_log,  "Start foreground", "INFO")
            utils.print_textbox(self.textbox_message_system_log, "Start foreground", "INFO")
        else:
            self.attributes("-topmost", False)
            utils.print_textbox(self.textbox_message_log,  "Stop foreground", "INFO")
            utils.print_textbox(self.textbox_message_system_log, "Stop foreground", "INFO")
        utils.save_json(self.PATH_CONFIG, "ENABLE_FOREGROUND", self.ENABLE_FOREGROUND)

    def entry_message_box_press_key_enter(self, event):
        # send OSC typing
        osc_tools.send_typing(False, self.OSC_IP_ADDRESS, self.OSC_PORT)

        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)

        message = self.entry_message_box.get()
        if len(message) > 0:
            # translate
            if self.checkbox_translation.get() is False:
                chat_message = f"{message}"
            elif self.translator.translator_status[self.CHOICE_TRANSLATOR] is False:
                utils.print_textbox(self.textbox_message_log,  "Auth Key or language setting is incorrect", "ERROR")
                utils.print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
                chat_message = f"{message}"
            else:
                result = self.translator.translate(
                    translator_name=self.CHOICE_TRANSLATOR,
                    source_language=self.INPUT_SOURCE_LANG,
                    target_language=self.INPUT_TARGET_LANG,
                    message=message
                )
                chat_message = self.MESSAGE_FORMAT.replace("[message]", message).replace("[translation]", result)

            # send OSC message
            osc_tools.send_message(chat_message, self.OSC_IP_ADDRESS, self.OSC_PORT)

            # update textbox message log
            utils.print_textbox(self.textbox_message_log,  f"{chat_message}", "SEND")
            utils.print_textbox(self.textbox_message_send_log, f"{chat_message}", "SEND")

            # delete message in entry message box
            # self.entry_message_box.delete(0, customtkinter.END)

    def entry_message_box_press_key_any(self, event):
        # send OSC typing
        osc_tools.send_typing(True, self.OSC_IP_ADDRESS, self.OSC_PORT)
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", False)

    def entry_message_box_leave(self, event):
        # send OSC typing
        osc_tools.send_typing(False, self.OSC_IP_ADDRESS, self.OSC_PORT)
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)

    def delete_window(self):
        if isinstance(self.th_vr_listen_mic, utils.thread_fnc):
            while not self.th_vr_listen_mic.stopped():
                self.th_vr_listen_mic.stop()
        if isinstance(self.th_vr_recognize_mic, utils.thread_fnc):
            while not self.th_vr_recognize_mic.stopped():
                self.th_vr_recognize_mic.stop()
        if self.vr.spk_stream is not None:
            self.vr.close_spk_stream()
        if isinstance(self.th_vr_recognize_spk, utils.thread_fnc):
            while not self.th_vr_recognize_spk.stopped():
                self.th_vr_recognize_spk.stop()
        self.destroy()

    
if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        print(e)