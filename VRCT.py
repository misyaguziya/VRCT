from time import sleep
from os import path as os_path
from json import load as json_load
from json import dump as json_dump
from queue import Queue
import tkinter as tk
import customtkinter
from customtkinter import CTk, CTkFrame, CTkCheckBox, CTkFont, CTkButton, CTkImage, CTkTabview, CTkTextbox, CTkEntry
from PIL.Image import open as Image_open
from flashtext import KeywordProcessor

from threading import Thread
from utils import save_json, print_textbox, thread_fnc, get_localized_text, widget_main_window_label_setter
from osc_tools import send_typing, send_message, send_test_action, receive_osc_parameters
from window_config import ToplevelWindowConfig
from window_information import ToplevelWindowInformation
from languages import transcription_lang, translators, translation_lang, selectable_languages
from audio_utils import get_input_device_list, get_output_device_list, get_default_input_device, get_default_output_device
from audio_recorder import SelectedMicRecorder, SelectedSpeakerRecorder
from audio_transcriber import AudioTranscriber
from translation import Translator
from notification import notification_xsoverlay_for_vrct

class App(CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # init instance
        self.translator = Translator()
        self.keyword_processor = KeywordProcessor()

        # init config
        self.PATH_CONFIG = "./config.json"

        ## main window
        self.ENABLE_TRANSLATION = False
        # self.ENABLE_TRANSCRIPTION_SEND = False
        # self.ENABLE_TRANSCRIPTION_RECEIVE = False
        self.ENABLE_FOREGROUND = False
        ## UI
        self.TRANSPARENCY = 100
        self.APPEARANCE_THEME = "System"
        self.UI_SCALING = "100%"
        self.FONT_FAMILY = "Yu Gothic UI"
        self.UI_LANGUAGE = "en"
        ## Translation
        self.CHOICE_TRANSLATOR = translators[0]
        self.INPUT_SOURCE_LANG = list(translation_lang[self.CHOICE_TRANSLATOR].keys())[0]
        self.INPUT_TARGET_LANG = list(translation_lang[self.CHOICE_TRANSLATOR].keys())[1]
        self.OUTPUT_SOURCE_LANG = list(translation_lang[self.CHOICE_TRANSLATOR].keys())[1]
        self.OUTPUT_TARGET_LANG = list(translation_lang[self.CHOICE_TRANSLATOR].keys())[0]
        ## Transcription Send
        self.CHOICE_MIC_HOST = get_default_input_device()["host"]["name"]
        self.CHOICE_MIC_DEVICE = get_default_input_device()["device"]["name"]
        self.INPUT_MIC_VOICE_LANGUAGE = list(transcription_lang.keys())[0]
        self.INPUT_MIC_ENERGY_THRESHOLD = 300
        self.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = True
        self.INPUT_MIC_RECORD_TIMEOUT = 3
        self.INPUT_MIC_PHRASE_TIMEOUT = 3
        self.INPUT_MIC_MAX_PHRASES = 10
        self.INPUT_MIC_WORD_FILTER = []
        ## Transcription Receive
        self.CHOICE_SPEAKER_DEVICE = get_default_output_device()["name"]
        self.INPUT_SPEAKER_VOICE_LANGUAGE = list(transcription_lang.keys())[1]
        self.INPUT_SPEAKER_ENERGY_THRESHOLD = 300
        self.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = True
        self.INPUT_SPEAKER_RECORD_TIMEOUT = 3
        self.INPUT_SPEAKER_PHRASE_TIMEOUT = 3
        self.INPUT_SPEAKER_MAX_PHRASES = 10

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
        # Others
        self.ENABLE_AUTO_CLEAR_CHATBOX = False
        self.ENABLE_OSC = False
        self.ENABLE_NOTICE_XSOVERLAY =False

        # load config
        if os_path.isfile(self.PATH_CONFIG) is not False:
            with open(self.PATH_CONFIG, 'r') as fp:
                config = json_load(fp)
            # main window
            # main windowは初期はすべてOFFにする
            # if "ENABLE_TRANSLATION" in config.keys():
            #     if type(config["ENABLE_TRANSLATION"]) is bool:
            #         self.ENABLE_TRANSLATION = config["ENABLE_TRANSLATION"]

            # 環境に依ってマイクとスピーカーを同時起動するとエラーが発生するため、起動時は強制的にOFFにする
            # if "ENABLE_TRANSCRIPTION_SEND" in config.keys():
            #     if type(config["ENABLE_TRANSCRIPTION_SEND"]) is bool:
            #         self.ENABLE_TRANSCRIPTION_SEND = config["ENABLE_TRANSCRIPTION_SEND"]
            # if "ENABLE_TRANSCRIPTION_RECEIVE" in config.keys():
            #     if type(config["ENABLE_TRANSCRIPTION_RECEIVE"]) is bool:
            #         self.ENABLE_TRANSCRIPTION_RECEIVE = config["ENABLE_TRANSCRIPTION_RECEIVE"]

            # if "ENABLE_FOREGROUND" in config.keys():
            #     if type(config["ENABLE_FOREGROUND"]) is bool:
            #         self.ENABLE_FOREGROUND = config["ENABLE_FOREGROUND"]

            # tab ui
            if "TRANSPARENCY" in config.keys():
                if type(config["TRANSPARENCY"]) is int:
                    if 0 <= config["TRANSPARENCY"] <= 100:
                        self.TRANSPARENCY = config["TRANSPARENCY"]
            if "APPEARANCE_THEME" in config.keys():
                if config["APPEARANCE_THEME"] in ["Light", "Dark", "System"]:
                    self.APPEARANCE_THEME = config["APPEARANCE_THEME"]
            if "UI_SCALING" in config.keys():
                if config["UI_SCALING"] in ["80%", "90%", "100%", "110%", "120%"]:
                    self.UI_SCALING = config["UI_SCALING"]
            if "FONT_FAMILY" in config.keys():
                if config["FONT_FAMILY"] in list(tk.font.families()):
                    self.FONT_FAMILY = config["FONT_FAMILY"]
            if "UI_LANGUAGE" in config.keys():
                if config["UI_LANGUAGE"] in list(selectable_languages.keys()):
                    self.UI_LANGUAGE = config["UI_LANGUAGE"]

            # translation
            if "CHOICE_TRANSLATOR" in config.keys():
                if config["CHOICE_TRANSLATOR"] in list(self.translator.translator_status.keys()):
                    self.CHOICE_TRANSLATOR = config["CHOICE_TRANSLATOR"]
            if "INPUT_SOURCE_LANG" in config.keys():
                if config["INPUT_SOURCE_LANG"] in list(translation_lang[self.CHOICE_TRANSLATOR].keys()):
                    self.INPUT_SOURCE_LANG = config["INPUT_SOURCE_LANG"]
            if "INPUT_TARGET_LANG" in config.keys():
                if config["INPUT_SOURCE_LANG"] in list(translation_lang[self.CHOICE_TRANSLATOR].keys()):
                    self.INPUT_TARGET_LANG = config["INPUT_TARGET_LANG"]
            if "OUTPUT_SOURCE_LANG" in config.keys():
                if config["INPUT_SOURCE_LANG"] in list(translation_lang[self.CHOICE_TRANSLATOR].keys()):
                    self.OUTPUT_SOURCE_LANG = config["OUTPUT_SOURCE_LANG"]
            if "OUTPUT_TARGET_LANG" in config.keys():
                if config["INPUT_SOURCE_LANG"] in list(translation_lang[self.CHOICE_TRANSLATOR].keys()):
                    self.OUTPUT_TARGET_LANG = config["OUTPUT_TARGET_LANG"]

            # Transcription
            if "CHOICE_MIC_HOST" in config.keys():
                if config["CHOICE_MIC_HOST"] in [host for host in get_input_device_list().keys()]:
                    self.CHOICE_MIC_HOST = config["CHOICE_MIC_HOST"]
            if "CHOICE_MIC_DEVICE" in config.keys():
                if config["CHOICE_MIC_DEVICE"] in [device["name"] for device in get_input_device_list()[self.CHOICE_MIC_HOST]]:
                    self.CHOICE_MIC_DEVICE = config["CHOICE_MIC_DEVICE"]
            if "INPUT_MIC_VOICE_LANGUAGE" in config.keys():
                if config["INPUT_MIC_VOICE_LANGUAGE"] in list(transcription_lang.keys()):
                    self.INPUT_MIC_VOICE_LANGUAGE = config["INPUT_MIC_VOICE_LANGUAGE"]
            if "INPUT_MIC_ENERGY_THRESHOLD" in config.keys():
                if type(config["INPUT_MIC_ENERGY_THRESHOLD"]) is int:
                    self.INPUT_MIC_ENERGY_THRESHOLD = config["INPUT_MIC_ENERGY_THRESHOLD"]
            if "INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD" in config.keys():
                if type(config["INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD"]) is bool:
                    self.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = config["INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD"]
            if "INPUT_MIC_RECORD_TIMEOUT" in config.keys():
                if type(config["INPUT_MIC_RECORD_TIMEOUT"]) is int:
                    self.INPUT_MIC_RECORD_TIMEOUT = config["INPUT_MIC_RECORD_TIMEOUT"]
            if "INPUT_MIC_PHRASE_TIMEOUT" in config.keys():
                if type(config["INPUT_MIC_PHRASE_TIMEOUT"]) is int:
                    self.INPUT_MIC_PHRASE_TIMEOUT = config["INPUT_MIC_PHRASE_TIMEOUT"]
            if "INPUT_MIC_MAX_PHRASES" in config.keys():
                if type(config["INPUT_MIC_MAX_PHRASES"]) is int:
                    self.INPUT_MIC_MAX_PHRASES = config["INPUT_MIC_MAX_PHRASES"]
            if "INPUT_MIC_WORD_FILTER" in config.keys():
                if type(config["INPUT_MIC_WORD_FILTER"]) is list:
                    self.INPUT_MIC_WORD_FILTER = config["INPUT_MIC_WORD_FILTER"]

            if "CHOICE_SPEAKER_DEVICE" in config.keys():
                if config["CHOICE_SPEAKER_DEVICE"] in [device["name"] for device in get_output_device_list()]:
                    speaker_device = [device for device in get_output_device_list() if device["name"] == config["CHOICE_SPEAKER_DEVICE"]][0]
                    if get_default_output_device()["index"] == speaker_device["index"]:
                        self.CHOICE_SPEAKER_DEVICE = config["CHOICE_SPEAKER_DEVICE"]
            if "INPUT_SPEAKER_VOICE_LANGUAGE" in config.keys():
                if config["INPUT_SPEAKER_VOICE_LANGUAGE"] in list(transcription_lang.keys()):
                    self.INPUT_SPEAKER_VOICE_LANGUAGE = config["INPUT_SPEAKER_VOICE_LANGUAGE"]
            if "INPUT_SPEAKER_ENERGY_THRESHOLD" in config.keys():
                if type(config["INPUT_SPEAKER_ENERGY_THRESHOLD"]) is int:
                    self.INPUT_SPEAKER_ENERGY_THRESHOLD = config["INPUT_SPEAKER_ENERGY_THRESHOLD"]
            if "INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD" in config.keys():
                if type(config["INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD"]) is bool:
                    self.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = config["INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD"]
            if "INPUT_SPEAKER_RECORD_TIMEOUT" in config.keys():
                if type(config["INPUT_SPEAKER_RECORD_TIMEOUT"]) is int:
                    self.INPUT_SPEAKER_RECORD_TIMEOUT = config["INPUT_SPEAKER_RECORD_TIMEOUT"]
            if "INPUT_SPEAKER_PHRASE_TIMEOUT" in config.keys():
                if type(config["INPUT_SPEAKER_PHRASE_TIMEOUT"]) is int:
                    self.INPUT_SPEAKER_PHRASE_TIMEOUT = config["INPUT_SPEAKER_PHRASE_TIMEOUT"]
            if "INPUT_SPEAKER_MAX_PHRASES" in config.keys():
                if type(config["INPUT_SPEAKER_MAX_PHRASES"]) is int:
                    self.INPUT_MIC_MAX_PHRASES = config["INPUT_SPEAKER_MAX_PHRASES"]

            # Parameter
            if "OSC_IP_ADDRESS" in config.keys():
                if type(config["OSC_IP_ADDRESS"]) is str:
                    self.OSC_IP_ADDRESS = config["OSC_IP_ADDRESS"]
            if "OSC_PORT" in config.keys():
                if type(config["OSC_PORT"]) is int:
                    self.OSC_PORT = config["OSC_PORT"]
            if "AUTH_KEYS" in config.keys():
                if type(config["AUTH_KEYS"]) is dict:
                    if set(config["AUTH_KEYS"].keys()) == set(self.AUTH_KEYS.keys()):
                        for key, value in config["AUTH_KEYS"].items():
                            if type(value) is str:
                                self.AUTH_KEYS[key] = config["AUTH_KEYS"][key]
            if "MESSAGE_FORMAT" in config.keys():
                if type(config["MESSAGE_FORMAT"]) is str:
                    self.MESSAGE_FORMAT = config["MESSAGE_FORMAT"]

            # Others
            if "ENABLE_AUTO_CLEAR_CHATBOX" in config.keys():
                if type(config["ENABLE_AUTO_CLEAR_CHATBOX"]) is bool:
                    self.ENABLE_AUTO_CLEAR_CHATBOX = config["ENABLE_AUTO_CLEAR_CHATBOX"]
            if "ENABLE_NOTICE_XSOVERLAY" in config.keys():
                if type(config["ENABLE_NOTICE_XSOVERLAY"]) is bool:
                    self.ENABLE_NOTICE_XSOVERLAY = config["ENABLE_NOTICE_XSOVERLAY"]

        with open(self.PATH_CONFIG, 'w') as fp:
            config = {
                # "ENABLE_TRANSLATION": self.ENABLE_TRANSLATION,
                # "ENABLE_TRANSCRIPTION_SEND": self.ENABLE_TRANSCRIPTION_SEND,
                # "ENABLE_TRANSCRIPTION_RECEIVE": self.ENABLE_TRANSCRIPTION_RECEIVE,
                # "ENABLE_FOREGROUND": self.ENABLE_FOREGROUND,
                "TRANSPARENCY": self.TRANSPARENCY,
                "APPEARANCE_THEME": self.APPEARANCE_THEME,
                "UI_SCALING": self.UI_SCALING,
                "UI_LANGUAGE": self.UI_LANGUAGE,
                "FONT_FAMILY": self.FONT_FAMILY,
                "CHOICE_TRANSLATOR": self.CHOICE_TRANSLATOR,
                "INPUT_SOURCE_LANG": self.INPUT_SOURCE_LANG,
                "INPUT_TARGET_LANG": self.INPUT_TARGET_LANG,
                "OUTPUT_SOURCE_LANG": self.OUTPUT_SOURCE_LANG,
                "OUTPUT_TARGET_LANG": self.OUTPUT_TARGET_LANG,
                "CHOICE_MIC_HOST": self.CHOICE_MIC_HOST,
                "CHOICE_MIC_DEVICE": self.CHOICE_MIC_DEVICE,
                "INPUT_MIC_VOICE_LANGUAGE": self.INPUT_MIC_VOICE_LANGUAGE,
                "INPUT_MIC_ENERGY_THRESHOLD": self.INPUT_MIC_ENERGY_THRESHOLD,
                "INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD": self.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD,
                "INPUT_MIC_RECORD_TIMEOUT": self.INPUT_MIC_RECORD_TIMEOUT,
                "INPUT_MIC_PHRASE_TIMEOUT": self.INPUT_MIC_PHRASE_TIMEOUT,
                "INPUT_MIC_MAX_PHRASES": self.INPUT_MIC_MAX_PHRASES,
                "INPUT_MIC_WORD_FILTER": self.INPUT_MIC_WORD_FILTER,
                "CHOICE_SPEAKER_DEVICE": self.CHOICE_SPEAKER_DEVICE,
                "INPUT_SPEAKER_VOICE_LANGUAGE": self.INPUT_SPEAKER_VOICE_LANGUAGE,
                "INPUT_SPEAKER_ENERGY_THRESHOLD": self.INPUT_SPEAKER_ENERGY_THRESHOLD,
                "INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD": self.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD,
                "INPUT_SPEAKER_RECORD_TIMEOUT": self.INPUT_SPEAKER_RECORD_TIMEOUT,
                "INPUT_SPEAKER_PHRASE_TIMEOUT": self.INPUT_SPEAKER_PHRASE_TIMEOUT,
                "INPUT_SPEAKER_MAX_PHRASES": self.INPUT_SPEAKER_MAX_PHRASES,
                "OSC_IP_ADDRESS": self.OSC_IP_ADDRESS,
                "OSC_PORT": self.OSC_PORT,
                "AUTH_KEYS": self.AUTH_KEYS,
                "MESSAGE_FORMAT": self.MESSAGE_FORMAT,
                "ENABLE_AUTO_CLEAR_CHATBOX": self.ENABLE_AUTO_CLEAR_CHATBOX,
                "ENABLE_NOTICE_XSOVERLAY": self.ENABLE_NOTICE_XSOVERLAY,
            }
            json_dump(config, fp, indent=4)

        ## set UI theme
        customtkinter.set_appearance_mode(self.APPEARANCE_THEME)
        customtkinter.set_default_color_theme("blue")

        # init main window
        self.iconbitmap(os_path.join(os_path.dirname(__file__), "img", "app.ico"))
        self.title("VRCT")
        self.geometry(f"{400}x{175}")
        self.minsize(400, 175)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # add sidebar left
        self.sidebar_frame = CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        init_lang_text = "Loading..."

        # add checkbox translation
        self.checkbox_translation = CTkCheckBox(
            self.sidebar_frame,
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_translation_callback,
            font=CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_translation.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="we")

        # add checkbox transcription send
        self.checkbox_transcription_send = CTkCheckBox(
            self.sidebar_frame,
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_transcription_send_callback,
            font=CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_transcription_send.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="we")

        # add checkbox transcription receive
        self.checkbox_transcription_receive = CTkCheckBox(
            self.sidebar_frame,
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_transcription_receive_callback,
            font=CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_transcription_receive.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="we")

        # add checkbox foreground
        self.checkbox_foreground = CTkCheckBox(
            self.sidebar_frame,
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_foreground_callback,
            font=CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_foreground.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="we")

        # add button information
        self.button_information = CTkButton(
            self.sidebar_frame,
            text="",
            width=25,
            command=self.button_information_callback,
            image=CTkImage(Image_open(os_path.join(os_path.dirname(__file__), "img", "info-icon-white.png")))
        )
        self.button_information.grid(row=5, column=0, padx=(10, 5), pady=(5, 5), sticky="wse")
        self.information_window = None

        # add button config
        self.button_config = CTkButton(
            self.sidebar_frame,
            text="",
            width=25,
            command=self.button_config_callback,
            image=CTkImage(Image_open(os_path.join(os_path.dirname(__file__), "img", "config-icon-white.png")))
        )
        self.button_config.grid(row=5, column=1, padx=(5, 10), pady=(5, 5), sticky="wse")

        # load ui language data
        language_yaml_data = get_localized_text(f"{self.UI_LANGUAGE}")
        # add tabview textbox
        self.add_tabview_logs(language_yaml_data)

        # add entry message box
        self.entry_message_box = CTkEntry(
            self,
            placeholder_text="message",
            font=CTkFont(family=self.FONT_FAMILY),
        )
        self.entry_message_box.grid(row=1, column=1, columnspan=2, padx=5, pady=(5, 10), sticky="nsew")

        # set default values
        ## set translator
        if self.translator.authentication(self.CHOICE_TRANSLATOR, self.AUTH_KEYS[self.CHOICE_TRANSLATOR]) is False:
            # error update Auth key
            print_textbox(self.textbox_message_log, "Auth Key or language setting is incorrect", "ERROR")
            print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")

        # ## set checkbox enable translation
        # if self.ENABLE_TRANSLATION:
        #     self.checkbox_translation.select()
        #     self.checkbox_translation_callback()
        # else:
        #     self.checkbox_translation.deselect()

        # ## set checkbox enable transcription send
        # if self.ENABLE_TRANSCRIPTION_SEND:
        #     self.checkbox_transcription_send.select()
        #     self.checkbox_transcription_send_callback()
        # else:
        #     self.checkbox_transcription_send.deselect()

        # ## set checkbox enable transcription receive
        # if self.ENABLE_TRANSCRIPTION_RECEIVE:
        #     self.checkbox_transcription_receive.select()
        #     self.checkbox_transcription_receive_callback()
        # else:
        #     self.checkbox_transcription_receive.deselect()

        # ## set set checkbox enable foreground
        # if self.ENABLE_FOREGROUND:
        #     self.checkbox_foreground.select()
        #     self.checkbox_foreground_callback()
        # else:
        #     self.checkbox_foreground.deselect()

        ## set word filter
        for f in self.INPUT_MIC_WORD_FILTER:
            self.keyword_processor.add_keyword(f)

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

        self.config_window = ToplevelWindowConfig(self)
        self.information_window = ToplevelWindowInformation(self)

        # start receive osc
        th_receive_osc_parameters = Thread(target=receive_osc_parameters, args=(self.check_osc_receive,))
        th_receive_osc_parameters.daemon = True
        th_receive_osc_parameters.start()

        # check osc started
        send_test_action()

    def button_config_callback(self):
        self.foreground_stop()
        self.transcription_stop()
        self.checkbox_translation.configure(state="disabled")
        self.checkbox_transcription_send.configure(state="disabled")
        self.checkbox_transcription_receive.configure(state="disabled")
        self.checkbox_foreground.configure(state="disabled")
        self.tabview_logs.configure(state="disabled")
        self.textbox_message_log.configure(state="disabled")
        self.textbox_message_send_log.configure(state="disabled")
        self.textbox_message_receive_log.configure(state="disabled")
        self.textbox_message_system_log.configure(state="disabled")
        self.entry_message_box.configure(state="disabled")
        self.button_config.configure(state="disabled", fg_color=["gray92", "gray14"])
        self.button_information.configure(state="disabled", fg_color=["gray92", "gray14"])
        self.config_window.deiconify()
        self.config_window.focus_set()
        self.config_window.focus()
        self.config_window.grab_set()

    def button_information_callback(self):
        self.information_window.deiconify()
        self.information_window.focus_set()
        self.information_window.focus()

    def checkbox_translation_callback(self):
        self.ENABLE_TRANSLATION = self.checkbox_translation.get()
        if self.ENABLE_TRANSLATION is True:
            print_textbox(self.textbox_message_log, "Start translation", "INFO")
            print_textbox(self.textbox_message_system_log, "Start translation", "INFO")
        else:
            print_textbox(self.textbox_message_log, "Stop translation", "INFO")
            print_textbox(self.textbox_message_system_log, "Stop translation", "INFO")

    def transcription_send_start(self):
        self.mic_audio_queue = Queue()
        mic_device = [device for device in get_input_device_list()[self.CHOICE_MIC_HOST] if device["name"] == self.CHOICE_MIC_DEVICE][0]
        self.mic_audio_recorder = SelectedMicRecorder(
            mic_device,
            self.INPUT_MIC_ENERGY_THRESHOLD,
            self.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD,
            self.INPUT_MIC_RECORD_TIMEOUT,
        )
        self.mic_audio_recorder.record_into_queue(self.mic_audio_queue)
        self.mic_transcriber = AudioTranscriber(
            speaker=False,
            source=self.mic_audio_recorder.source,
            language=transcription_lang[self.INPUT_MIC_VOICE_LANGUAGE],
            phrase_timeout=self.INPUT_MIC_PHRASE_TIMEOUT,
            max_phrases=self.INPUT_MIC_MAX_PHRASES,
        )
        def mic_transcript_to_chatbox():
            self.mic_transcriber.transcribe_audio_queue(self.mic_audio_queue)
            message = self.mic_transcriber.get_transcript()
            if len(message) > 0:
                # word filter
                if len(self.keyword_processor.extract_keywords(message)) != 0:
                    print_textbox(self.textbox_message_log, f"Detect WordFilter :{message}", "INFO")
                    print_textbox(self.textbox_message_system_log, f"Detect WordFilter :{message}", "INFO")
                    return

                # translate
                if self.checkbox_translation.get() is False:
                    voice_message = f"{message}"
                elif self.translator.translator_status[self.CHOICE_TRANSLATOR] is False:
                    print_textbox(self.textbox_message_log,  "Auth Key or language setting is incorrect", "ERROR")
                    print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
                    voice_message = f"{message}"
                else:
                    result = self.translator.translate(
                        translator_name=self.CHOICE_TRANSLATOR,
                        source_language=self.INPUT_SOURCE_LANG,
                        target_language=self.INPUT_TARGET_LANG,
                        message=message
                    )
                    voice_message = self.MESSAGE_FORMAT.replace("[message]", message).replace("[translation]", result)

                if self.checkbox_transcription_send.get() is True:
                    if self.ENABLE_OSC is True:
                        # send OSC message
                        send_message(voice_message, self.OSC_IP_ADDRESS, self.OSC_PORT)
                    else:
                        print_textbox(self.textbox_message_log, "OSC is not enabled, please enable OSC and rejoin.", "ERROR")
                        print_textbox(self.textbox_message_system_log, "OSC is not enabled, please enable OSC and rejoin.", "ERROR")
                    # update textbox message log
                    print_textbox(self.textbox_message_log,  f"{voice_message}", "SEND")
                    print_textbox(self.textbox_message_send_log, f"{voice_message}", "SEND")

        self.mic_print_transcript = thread_fnc(mic_transcript_to_chatbox)
        self.mic_print_transcript.daemon = True
        self.mic_print_transcript.start()
        print_textbox(self.textbox_message_log, "Start voice2chatbox", "INFO")
        print_textbox(self.textbox_message_system_log, "Start voice2chatbox", "INFO")
        self.checkbox_transcription_send.configure(state="normal")
        self.checkbox_transcription_receive.configure(state="normal")
        self.button_config.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])

    def transcription_send_stop(self):
        if isinstance(self.mic_print_transcript, thread_fnc):
            self.mic_print_transcript.stop()
        if self.mic_audio_recorder.stop != None:
            self.mic_audio_recorder.stop()
            self.mic_audio_recorder.stop = None

        print_textbox(self.textbox_message_log, "Stop voice2chatbox", "INFO")
        print_textbox(self.textbox_message_system_log, "Stop voice2chatbox", "INFO")
        self.checkbox_transcription_send.configure(state="normal")
        self.checkbox_transcription_receive.configure(state="normal")
        self.button_config.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])

    def transcription_send_stop_for_config(self):
        if isinstance(self.mic_print_transcript, thread_fnc):
            self.mic_print_transcript.stop()
        if self.mic_audio_recorder.stop != None:
            self.mic_audio_recorder.stop()
            self.mic_audio_recorder.stop = None

        print_textbox(self.textbox_message_log, "Stop voice2chatbox", "INFO")
        print_textbox(self.textbox_message_system_log, "Stop voice2chatbox", "INFO")

    def checkbox_transcription_send_callback(self):
        self.checkbox_transcription_send.configure(state="disabled")
        self.checkbox_transcription_receive.configure(state="disabled")
        self.button_config.configure(state="disabled", fg_color=["gray92", "gray14"])
        if self.checkbox_transcription_send.get() is True:
            th_transcription_send_start = Thread(target=self.transcription_send_start)
            th_transcription_send_start.daemon = True
            th_transcription_send_start.start()
        else:
            th_transcription_send_stop = Thread(target=self.transcription_send_stop)
            th_transcription_send_stop.daemon = True
            th_transcription_send_stop.start()

    def transcription_receive_start(self):
            self.spk_audio_queue = Queue()
            spk_device = [device for device in get_output_device_list() if device["name"] == self.CHOICE_SPEAKER_DEVICE][0]
            self.spk_audio_recorder = SelectedSpeakerRecorder(
                spk_device,
                self.INPUT_SPEAKER_ENERGY_THRESHOLD,
                self.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD,
                self.INPUT_SPEAKER_RECORD_TIMEOUT,
            )
            self.spk_audio_recorder.record_into_queue(self.spk_audio_queue)
            self.spk_transcriber = AudioTranscriber(
                speaker=True,
                source=self.spk_audio_recorder.source,
                language=transcription_lang[self.INPUT_SPEAKER_VOICE_LANGUAGE],
                phrase_timeout=self.INPUT_SPEAKER_PHRASE_TIMEOUT,
                max_phrases=self.INPUT_SPEAKER_MAX_PHRASES,
            )

            def spk_transcript_to_textbox():
                self.spk_transcriber.transcribe_audio_queue(self.spk_audio_queue)
                message = self.spk_transcriber.get_transcript()
                if len(message) > 0:
                    # translate
                    if self.checkbox_translation.get() is False:
                        voice_message = f"{message}"
                    elif self.translator.translator_status[self.CHOICE_TRANSLATOR] is False:
                        print_textbox(self.textbox_message_log, "Auth Key or language setting is incorrect", "ERROR")
                        print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
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
                    # send_message(voice_message, self.OSC_IP_ADDRESS, self.OSC_PORT)

                    if self.checkbox_transcription_receive.get() is True:
                        # update textbox message receive log
                        print_textbox(self.textbox_message_log,  f"{voice_message}", "RECEIVE")
                        print_textbox(self.textbox_message_receive_log, f"{voice_message}", "RECEIVE")
                        if self.ENABLE_NOTICE_XSOVERLAY is True:
                            notification_xsoverlay_for_vrct(content=f"{voice_message}")

            self.spk_print_transcript = thread_fnc(spk_transcript_to_textbox)
            self.spk_print_transcript.daemon = True
            self.spk_print_transcript.start()
            print_textbox(self.textbox_message_log,  "Start speaker2log", "INFO")
            print_textbox(self.textbox_message_system_log, "Start speaker2log", "INFO")
            self.checkbox_transcription_send.configure(state="normal")
            self.checkbox_transcription_receive.configure(state="normal")

    def transcription_receive_stop(self):
        if isinstance(self.spk_print_transcript, thread_fnc):
            self.spk_print_transcript.stop()
        if self.spk_audio_recorder.stop != None:
            self.spk_audio_recorder.stop()
            self.spk_audio_recorder.stop = None

        print_textbox(self.textbox_message_log,  "Stop speaker2log", "INFO")
        print_textbox(self.textbox_message_system_log, "Stop speaker2log", "INFO")
        self.checkbox_transcription_send.configure(state="normal")
        self.checkbox_transcription_receive.configure(state="normal")
        self.button_config.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])

    def transcription_receive_stop_for_config(self):
        if isinstance(self.spk_print_transcript, thread_fnc):
            self.spk_print_transcript.stop()
        if self.spk_audio_recorder.stop != None:
            self.spk_audio_recorder.stop()
            self.spk_audio_recorder.stop = None

        print_textbox(self.textbox_message_log,  "Stop speaker2log", "INFO")
        print_textbox(self.textbox_message_system_log, "Stop speaker2log", "INFO")

    def checkbox_transcription_receive_callback(self):
        self.checkbox_transcription_send.configure(state="disabled")
        self.checkbox_transcription_receive.configure(state="disabled")
        self.button_config.configure(state="disabled", fg_color=["gray92", "gray14"])
        if self.checkbox_transcription_receive.get() is True:
            th_transcription_receive_start = Thread(target=self.transcription_receive_start)
            th_transcription_receive_start.daemon = True
            th_transcription_receive_start.start()
        else:
            th_transcription_receive_stop = Thread(target=self.transcription_receive_stop)
            th_transcription_receive_stop.daemon = True
            th_transcription_receive_stop.start()

    def transcription_start(self):
        if self.checkbox_transcription_send.get() is True:
            th_transcription_send_start = Thread(target=self.transcription_send_start)
            th_transcription_send_start.daemon = True
            th_transcription_send_start.start()
            sleep(2)
        if self.checkbox_transcription_receive.get() is True:
            th_transcription_receive_start = Thread(target=self.transcription_receive_start)
            th_transcription_receive_start.daemon = True
            th_transcription_receive_start.start()

    def transcription_stop(self):
        if self.checkbox_transcription_send.get() is True:
            th_transcription_send_stop = Thread(target=self.transcription_send_stop_for_config)
            th_transcription_send_stop.daemon = True
            th_transcription_send_stop.start()
        if self.checkbox_transcription_receive.get() is True:
            th_transcription_receive_stop = Thread(target=self.transcription_receive_stop_for_config)
            th_transcription_receive_stop.daemon = True
            th_transcription_receive_stop.start()

    def checkbox_foreground_callback(self):
        self.ENABLE_FOREGROUND = self.checkbox_foreground.get()
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)
            print_textbox(self.textbox_message_log,  "Start foreground", "INFO")
            print_textbox(self.textbox_message_system_log, "Start foreground", "INFO")
        else:
            self.attributes("-topmost", False)
            print_textbox(self.textbox_message_log,  "Stop foreground", "INFO")
            print_textbox(self.textbox_message_system_log, "Stop foreground", "INFO")

    def foreground_start(self):
        self.ENABLE_FOREGROUND = self.checkbox_foreground.get()
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)
            print_textbox(self.textbox_message_log,  "Start foreground", "INFO")
            print_textbox(self.textbox_message_system_log, "Start foreground", "INFO")

    def foreground_stop(self):
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", False)
            print_textbox(self.textbox_message_log,  "Stop foreground", "INFO")
            print_textbox(self.textbox_message_system_log, "Stop foreground", "INFO")
            self.ENABLE_FOREGROUND = False

    def entry_message_box_press_key_enter(self, event):
        # send OSC typing
        send_typing(False, self.OSC_IP_ADDRESS, self.OSC_PORT)

        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)

        message = self.entry_message_box.get()
        if len(message) > 0:
            # translate
            if self.checkbox_translation.get() is False:
                chat_message = f"{message}"
            elif self.translator.translator_status[self.CHOICE_TRANSLATOR] is False:
                print_textbox(self.textbox_message_log,  "Auth Key or language setting is incorrect", "ERROR")
                print_textbox(self.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
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
            if self.ENABLE_OSC is True:
                send_message(chat_message, self.OSC_IP_ADDRESS, self.OSC_PORT)
            else:
                print_textbox(self.textbox_message_log, "OSC is not enabled, please enable OSC and rejoin.", "ERROR")
                print_textbox(self.textbox_message_system_log, "OSC is not enabled, please enable OSC and rejoin.", "ERROR")

            # update textbox message log
            print_textbox(self.textbox_message_log,  f"{chat_message}", "SEND")
            print_textbox(self.textbox_message_send_log, f"{chat_message}", "SEND")

            # delete message in entry message box
            if self.ENABLE_AUTO_CLEAR_CHATBOX is True:
                self.entry_message_box.delete(0, customtkinter.END)

    BREAK_KEYSYM_LIST = [
        "Delete", "Select", "Up", "Down", "Next", "End", "Print",
        "Prior","Insert","Home", "Left", "Clear", "Right", "Linefeed"
    ]
    def entry_message_box_press_key_any(self, event):
        # send OSC typing
        send_typing(True, self.OSC_IP_ADDRESS, self.OSC_PORT)
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", False)

        if event.keysym != "??":
            if len(event.char) != 0 and event.keysym in self.BREAK_KEYSYM_LIST:
                self.entry_message_box.insert("end", event.char)
                return "break"

    def entry_message_box_leave(self, event):
        # send OSC typing
        send_typing(False, self.OSC_IP_ADDRESS, self.OSC_PORT)
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)

    def delete_window(self):
        self.quit()
        self.destroy()

    def delete_tabview_logs(self, pre_language_yaml_data):
        self.tabview_logs.delete(pre_language_yaml_data["main_tab_title_log"])
        self.tabview_logs.delete(pre_language_yaml_data["main_tab_title_send"])
        self.tabview_logs.delete(pre_language_yaml_data["main_tab_title_receive"])
        self.tabview_logs.delete(pre_language_yaml_data["main_tab_title_system"])

    def add_tabview_logs(self, language_yaml_data):
        main_tab_title_log = language_yaml_data["main_tab_title_log"]
        main_tab_title_send = language_yaml_data["main_tab_title_send"]
        main_tab_title_receive = language_yaml_data["main_tab_title_receive"]
        main_tab_title_system = language_yaml_data["main_tab_title_system"]

        # add tabview textbox
        self.tabview_logs = CTkTabview(master=self)
        self.tabview_logs.add(main_tab_title_log)
        self.tabview_logs.add(main_tab_title_send)
        self.tabview_logs.add(main_tab_title_receive)
        self.tabview_logs.add(main_tab_title_system)
        self.tabview_logs.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        self.tabview_logs._segmented_button.configure(font=CTkFont(family=self.FONT_FAMILY))
        self.tabview_logs._segmented_button.grid(sticky="W")
        self.tabview_logs.tab(main_tab_title_log).grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_log).grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_send).grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_send).grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_receive).grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_receive).grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_system).grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab(main_tab_title_system).grid_columnconfigure(0, weight=1)
        self.tabview_logs.configure(fg_color="transparent")

        # add textbox message log
        self.textbox_message_log = CTkTextbox(
            self.tabview_logs.tab(main_tab_title_log),
            font=CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_log.configure(state='disabled')

        # add textbox message send log
        self.textbox_message_send_log = CTkTextbox(
            self.tabview_logs.tab(main_tab_title_send),
            font=CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_send_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_send_log.configure(state='disabled')

        # add textbox message receive log
        self.textbox_message_receive_log = CTkTextbox(
            self.tabview_logs.tab(main_tab_title_receive),
            font=CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_receive_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_receive_log.configure(state='disabled')

        # add textbox message system log
        self.textbox_message_system_log = CTkTextbox(
            self.tabview_logs.tab(main_tab_title_system),
            font=CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_system_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_system_log.configure(state='disabled')

        widget_main_window_label_setter(self, language_yaml_data)

    def check_osc_receive(self, address, osc_arguments):
        if self.ENABLE_OSC is False:
            self.ENABLE_OSC = True
        # print(address, osc_arguments)

if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        import traceback
        with open('error.log', 'a') as f:
            traceback.print_exc(file=f)