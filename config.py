import sys
from json import load, dump
import inspect
from os import path as os_path
from json import load as json_load
from json import dump as json_dump
import tkinter as tk
from tkinter import font
from languages import selectable_languages
from models.translation.translation_languages import translatorEngine, translation_lang
from models.transcription.transcription_languages import transcription_lang
from models.transcription.transcription_utils import getInputDevices, getOutputDevices, getDefaultInputDevice, getDefaultOutputDevice

json_serializable_vars = {}
def json_serializable(var_name):
    def decorator(func):
        json_serializable_vars[var_name] = func
        return func
    return decorator

def saveJson(path, key, value):
    with open(path, "r", encoding="utf-8") as fp:
        json_data = load(fp)
    json_data[key] = value
    with open(path, "w", encoding="utf-8") as fp:
        json_dump(json_data, fp, indent=4, ensure_ascii=False)

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.init_config()
            cls._instance.load_config()
        return cls._instance

    # Read Only
    @property
    def VERSION(self):
        return self._VERSION

    @property
    def PATH_CONFIG(self):
        return self._PATH_CONFIG

    @property
    def GITHUB_URL(self):
        return self._GITHUB_URL

    @property
    def BOOTH_URL(self):
        return self._BOOTH_URL

    @property
    def DOCUMENTS_URL(self):
        return self._DOCUMENTS_URL

    @property
    def MAX_MIC_ENERGY_THRESHOLD(self):
        return self._MAX_MIC_ENERGY_THRESHOLD

    @property
    def MAX_SPEAKER_ENERGY_THRESHOLD(self):
        return self._MAX_SPEAKER_ENERGY_THRESHOLD

    # Read Write
    @property
    def ENABLE_TRANSLATION(self):
        return self._ENABLE_TRANSLATION

    @ENABLE_TRANSLATION.setter
    def ENABLE_TRANSLATION(self, value):
        if type(value) is bool:
            self._ENABLE_TRANSLATION = value

    @property
    def ENABLE_TRANSCRIPTION_SEND(self):
        return self._ENABLE_TRANSCRIPTION_SEND

    @ENABLE_TRANSCRIPTION_SEND.setter
    def ENABLE_TRANSCRIPTION_SEND(self, value):
        if type(value) is bool:
            self._ENABLE_TRANSCRIPTION_SEND = value

    @property
    def ENABLE_TRANSCRIPTION_RECEIVE(self):
        return self._ENABLE_TRANSCRIPTION_RECEIVE

    @ENABLE_TRANSCRIPTION_RECEIVE.setter
    def ENABLE_TRANSCRIPTION_RECEIVE(self, value):
        if type(value) is bool:
            self._ENABLE_TRANSCRIPTION_RECEIVE = value

    @property
    def ENABLE_FOREGROUND(self):
        return self._ENABLE_FOREGROUND

    @ENABLE_FOREGROUND.setter
    def ENABLE_FOREGROUND(self, value):
        if type(value) is bool:
            self._ENABLE_FOREGROUND = value

    @property
    def SOURCE_COUNTRY(self):
        return self._SOURCE_COUNTRY

    @SOURCE_COUNTRY.setter
    def SOURCE_COUNTRY(self, value):
        if type(value) is str:
            self._SOURCE_COUNTRY = value

    @property
    def SOURCE_LANGUAGE(self):
        return self._SOURCE_LANGUAGE

    @SOURCE_LANGUAGE.setter
    def SOURCE_LANGUAGE(self, value):
        if type(value) is str:
            self._SOURCE_LANGUAGE = value

    @property
    def TARGET_COUNTRY(self):
        return self._TARGET_COUNTRY

    @TARGET_COUNTRY.setter
    def TARGET_COUNTRY(self, value):
        if type(value) is str:
            self._TARGET_COUNTRY = value

    @property
    def TARGET_LANGUAGE(self):
        return self._TARGET_LANGUAGE

    @TARGET_LANGUAGE.setter
    def TARGET_LANGUAGE(self, value):
        if type(value) is str:
            self._TARGET_LANGUAGE = value

    @property
    def CHOICE_TRANSLATOR(self):
        return self._CHOICE_TRANSLATOR

    @CHOICE_TRANSLATOR.setter
    def CHOICE_TRANSLATOR(self, value):
        if value in translatorEngine:
            self._CHOICE_TRANSLATOR = value

    # Save Json Data
    ## Main Window
    @property
    @json_serializable('SELECTED_TAB_NO')
    def SELECTED_TAB_NO(self):
        return self._SELECTED_TAB_NO

    @SELECTED_TAB_NO.setter
    def SELECTED_TAB_NO(self, value):
        if type(value) is str:
            self._SELECTED_TAB_NO = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_TAB_YOUR_LANGUAGES')
    def SELECTED_TAB_YOUR_LANGUAGES(self):
        return self._SELECTED_TAB_YOUR_LANGUAGES

    @SELECTED_TAB_YOUR_LANGUAGES.setter
    def SELECTED_TAB_YOUR_LANGUAGES(self, value):
        if type(value) is dict:
            self._SELECTED_TAB_YOUR_LANGUAGES = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_TAB_TARGET_LANGUAGES')
    def SELECTED_TAB_TARGET_LANGUAGES(self):
        return self._SELECTED_TAB_TARGET_LANGUAGES

    @SELECTED_TAB_TARGET_LANGUAGES.setter
    def SELECTED_TAB_TARGET_LANGUAGES(self, value):
        if type(value) is dict:
            self._SELECTED_TAB_TARGET_LANGUAGES = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE')
    def IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE(self):
        return self._IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE

    @IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE.setter
    def IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE(self, value):
        if type(value) is bool:
            self._IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    ## Config Window
    @property
    @json_serializable('TRANSPARENCY')
    def TRANSPARENCY(self):
        return self._TRANSPARENCY

    @TRANSPARENCY.setter
    def TRANSPARENCY(self, value):
        if type(value) is int and 0 <= value <= 100:
            self._TRANSPARENCY = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('APPEARANCE_THEME')
    def APPEARANCE_THEME(self):
        return self._APPEARANCE_THEME

    @APPEARANCE_THEME.setter
    def APPEARANCE_THEME(self, value):
        if value in ["Light", "Dark", "System"]:
            self._APPEARANCE_THEME = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('UI_SCALING')
    def UI_SCALING(self):
        return self._UI_SCALING

    @UI_SCALING.setter
    def UI_SCALING(self, value):
        if value in ["40%", "60%", "80%", "90%", "100%", "110%", "120%", "150%", "200%"]:
            self._UI_SCALING = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('FONT_FAMILY')
    def FONT_FAMILY(self):
        return self._FONT_FAMILY

    @FONT_FAMILY.setter
    def FONT_FAMILY(self, value):
        root = tk.Tk()
        root.withdraw()
        if value in list(font.families()):
            self._FONT_FAMILY = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)
        root.destroy()

    @property
    @json_serializable('UI_LANGUAGE')
    def UI_LANGUAGE(self):
        return self._UI_LANGUAGE

    @UI_LANGUAGE.setter
    def UI_LANGUAGE(self, value):
        if value in list(selectable_languages.keys()):
            self._UI_LANGUAGE = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('CHOICE_MIC_HOST')
    def CHOICE_MIC_HOST(self):
        return self._CHOICE_MIC_HOST

    @CHOICE_MIC_HOST.setter
    def CHOICE_MIC_HOST(self, value):
        if value in [host for host in getInputDevices().keys()]:
            self._CHOICE_MIC_HOST = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('CHOICE_MIC_DEVICE')
    def CHOICE_MIC_DEVICE(self):
        return self._CHOICE_MIC_DEVICE

    @CHOICE_MIC_DEVICE.setter
    def CHOICE_MIC_DEVICE(self, value):
        if value in [device["name"] for device in getInputDevices()[self.CHOICE_MIC_HOST]]:
            self._CHOICE_MIC_DEVICE = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_MIC_ENERGY_THRESHOLD')
    def INPUT_MIC_ENERGY_THRESHOLD(self):
        return self._INPUT_MIC_ENERGY_THRESHOLD

    @INPUT_MIC_ENERGY_THRESHOLD.setter
    def INPUT_MIC_ENERGY_THRESHOLD(self, value):
        if type(value) is int:
            self._INPUT_MIC_ENERGY_THRESHOLD = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD')
    def INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD(self):
        return self._INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD

    @INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD.setter
    def INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD(self, value):
        if type(value) is bool:
            self._INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_MIC_RECORD_TIMEOUT')
    def INPUT_MIC_RECORD_TIMEOUT(self):
        return self._INPUT_MIC_RECORD_TIMEOUT

    @INPUT_MIC_RECORD_TIMEOUT.setter
    def INPUT_MIC_RECORD_TIMEOUT(self, value):
        if type(value) is int:
            self._INPUT_MIC_RECORD_TIMEOUT = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_MIC_PHRASE_TIMEOUT')
    def INPUT_MIC_PHRASE_TIMEOUT(self):
        return self._INPUT_MIC_PHRASE_TIMEOUT

    @INPUT_MIC_PHRASE_TIMEOUT.setter
    def INPUT_MIC_PHRASE_TIMEOUT(self, value):
        if type(value) is int:
            self._INPUT_MIC_PHRASE_TIMEOUT = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_MIC_MAX_PHRASES')
    def INPUT_MIC_MAX_PHRASES(self):
        return self._INPUT_MIC_MAX_PHRASES

    @INPUT_MIC_MAX_PHRASES.setter
    def INPUT_MIC_MAX_PHRASES(self, value):
        if type(value) is int:
            self._INPUT_MIC_MAX_PHRASES = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_MIC_WORD_FILTER')
    def INPUT_MIC_WORD_FILTER(self):
        return self._INPUT_MIC_WORD_FILTER

    @INPUT_MIC_WORD_FILTER.setter
    def INPUT_MIC_WORD_FILTER(self, value):
        if type(value) is list:
            self._INPUT_MIC_WORD_FILTER = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('CHOICE_SPEAKER_DEVICE')
    def CHOICE_SPEAKER_DEVICE(self):
        return self._CHOICE_SPEAKER_DEVICE

    @CHOICE_SPEAKER_DEVICE.setter
    def CHOICE_SPEAKER_DEVICE(self, value):
        if value in [device["name"] for device in getOutputDevices()]:
            speaker_device = [device for device in getOutputDevices() if device["name"] == value][0]
            if getDefaultOutputDevice()["index"] == speaker_device["index"]:
                self._CHOICE_SPEAKER_DEVICE = value
                saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_SPEAKER_ENERGY_THRESHOLD')
    def INPUT_SPEAKER_ENERGY_THRESHOLD(self):
        return self._INPUT_SPEAKER_ENERGY_THRESHOLD

    @INPUT_SPEAKER_ENERGY_THRESHOLD.setter
    def INPUT_SPEAKER_ENERGY_THRESHOLD(self, value):
        if type(value) is int:
            self._INPUT_SPEAKER_ENERGY_THRESHOLD = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD')
    def INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD(self):
        return self._INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD

    @INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD.setter
    def INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD(self, value):
        if type(value) is bool:
            self._INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_SPEAKER_RECORD_TIMEOUT')
    def INPUT_SPEAKER_RECORD_TIMEOUT(self):
        return self._INPUT_SPEAKER_RECORD_TIMEOUT

    @INPUT_SPEAKER_RECORD_TIMEOUT.setter
    def INPUT_SPEAKER_RECORD_TIMEOUT(self, value):
        if type(value) is int:
            self._INPUT_SPEAKER_RECORD_TIMEOUT = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_SPEAKER_PHRASE_TIMEOUT')
    def INPUT_SPEAKER_PHRASE_TIMEOUT(self):
        return self._INPUT_SPEAKER_PHRASE_TIMEOUT

    @INPUT_SPEAKER_PHRASE_TIMEOUT.setter
    def INPUT_SPEAKER_PHRASE_TIMEOUT(self, value):
        if type(value) is int:
            self._INPUT_SPEAKER_PHRASE_TIMEOUT = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('INPUT_SPEAKER_MAX_PHRASES')
    def INPUT_SPEAKER_MAX_PHRASES(self):
        return self._INPUT_SPEAKER_MAX_PHRASES

    @INPUT_SPEAKER_MAX_PHRASES.setter
    def INPUT_SPEAKER_MAX_PHRASES(self, value):
        if type(value) is int:
            self._INPUT_SPEAKER_MAX_PHRASES = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('OSC_IP_ADDRESS')
    def OSC_IP_ADDRESS(self):
        return self._OSC_IP_ADDRESS

    @OSC_IP_ADDRESS.setter
    def OSC_IP_ADDRESS(self, value):
        if type(value) is str:
            self._OSC_IP_ADDRESS = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('OSC_PORT')
    def OSC_PORT(self):
        return self._OSC_PORT

    @OSC_PORT.setter
    def OSC_PORT(self, value):
        if type(value) is int:
            self._OSC_PORT = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('AUTH_KEYS')
    def AUTH_KEYS(self):
        return self._AUTH_KEYS

    @AUTH_KEYS.setter
    def AUTH_KEYS(self, value):
        if type(value) is dict and set(value.keys()) == set(self.AUTH_KEYS.keys()):
            for key, value in value.items():
                if type(value) is str:
                    self._AUTH_KEYS[key] = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, self.AUTH_KEYS)

    @property
    @json_serializable('MESSAGE_FORMAT')
    def MESSAGE_FORMAT(self):
        return self._MESSAGE_FORMAT

    @MESSAGE_FORMAT.setter
    def MESSAGE_FORMAT(self, value):
        if type(value) is str:
            self._MESSAGE_FORMAT = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('ENABLE_AUTO_CLEAR_MESSAGE_BOX')
    def ENABLE_AUTO_CLEAR_MESSAGE_BOX(self):
        return self._ENABLE_AUTO_CLEAR_MESSAGE_BOX

    @ENABLE_AUTO_CLEAR_MESSAGE_BOX.setter
    def ENABLE_AUTO_CLEAR_MESSAGE_BOX(self, value):
        if type(value) is bool:
            self._ENABLE_AUTO_CLEAR_MESSAGE_BOX = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('ENABLE_NOTICE_XSOVERLAY')
    def ENABLE_NOTICE_XSOVERLAY(self):
        return self._ENABLE_NOTICE_XSOVERLAY

    @ENABLE_NOTICE_XSOVERLAY.setter
    def ENABLE_NOTICE_XSOVERLAY(self, value):
        if type(value) is bool:
            self._ENABLE_NOTICE_XSOVERLAY = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('ENABLE_SEND_MESSAGE_TO_VRC')
    def ENABLE_SEND_MESSAGE_TO_VRC(self):
        return self._ENABLE_SEND_MESSAGE_TO_VRC

    @ENABLE_SEND_MESSAGE_TO_VRC.setter
    def ENABLE_SEND_MESSAGE_TO_VRC(self, value):
        if type(value) is bool:
            self._ENABLE_SEND_MESSAGE_TO_VRC = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    # [deprecated]
    # @property
    # @json_serializable('STARTUP_OSC_ENABLED_CHECK')
    # def STARTUP_OSC_ENABLED_CHECK(self):
    #     return self._STARTUP_OSC_ENABLED_CHECK

    # @STARTUP_OSC_ENABLED_CHECK.setter
    # def STARTUP_OSC_ENABLED_CHECK(self, value):
    #     if type(value) is bool:
    #         self._STARTUP_OSC_ENABLED_CHECK = value
    #         saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('ENABLE_LOGGER')
    def ENABLE_LOGGER(self):
        return self._ENABLE_LOGGER

    @ENABLE_LOGGER.setter
    def ENABLE_LOGGER(self, value):
        if type(value) is bool:
            self._ENABLE_LOGGER = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('IS_CONFIG_WINDOW_COMPACT_MODE')
    def IS_CONFIG_WINDOW_COMPACT_MODE(self):
        return self._IS_CONFIG_WINDOW_COMPACT_MODE

    @IS_CONFIG_WINDOW_COMPACT_MODE.setter
    def IS_CONFIG_WINDOW_COMPACT_MODE(self, value):
        if type(value) is bool:
            self._IS_CONFIG_WINDOW_COMPACT_MODE = value
            saveJson(self.PATH_CONFIG, inspect.currentframe().f_code.co_name, value)

    def init_config(self):
        # Read Only
        self._VERSION = "2.0.0 alpha 3"
        self._PATH_CONFIG = os_path.join(os_path.dirname(sys.argv[0]), "config.json")
        self._GITHUB_URL = "https://api.github.com/repos/misyaguziya/VRCT/releases/latest"
        self._BOOTH_URL = "https://misyaguziya.booth.pm/"
        self._DOCUMENTS_URL = "https://mzsoftware.notion.site/VRCT-Documents-be79b7a165f64442ad8f326d86c22246"
        self._MAX_MIC_ENERGY_THRESHOLD = 2000
        self._MAX_SPEAKER_ENERGY_THRESHOLD = 4000

        # Read Write
        self._ENABLE_TRANSLATION = False
        self._ENABLE_TRANSCRIPTION_SEND = False
        self._ENABLE_TRANSCRIPTION_RECEIVE = False
        self._ENABLE_FOREGROUND = False
        self._CHOICE_TRANSLATOR = translatorEngine[0]
        self._SOURCE_LANGUAGE = "Japanese"
        self._SOURCE_COUNTRY = "Japan"
        self._TARGET_LANGUAGE = "English"
        self._TARGET_COUNTRY = "United States"

        # Save Json Data
        ## Main Window
        self._SELECTED_TAB_NO = "1"
        self._SELECTED_TAB_YOUR_LANGUAGES = {
            "1":"Japanese\n(Japan)",
            "2":"Japanese\n(Japan)",
            "3":"Japanese\n(Japan)",
        }
        self._SELECTED_TAB_TARGET_LANGUAGES = {
            "1":"English\n(United States)",
            "2":"English\n(United States)",
            "3":"English\n(United States)",
        }
        self._IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False

        ## Config Window
        self._TRANSPARENCY = 100
        self._APPEARANCE_THEME = "System"
        self._UI_SCALING = "100%"
        self._FONT_FAMILY = "Yu Gothic UI"
        self._UI_LANGUAGE = "en"
        self._CHOICE_MIC_HOST = getDefaultInputDevice()["host"]["name"]
        self._CHOICE_MIC_DEVICE = getDefaultInputDevice()["device"]["name"]
        self._INPUT_MIC_ENERGY_THRESHOLD = 300
        self._INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = False
        self._INPUT_MIC_RECORD_TIMEOUT = 3
        self._INPUT_MIC_PHRASE_TIMEOUT = 3
        self._INPUT_MIC_MAX_PHRASES = 10
        self._INPUT_MIC_WORD_FILTER = []
        self._CHOICE_SPEAKER_DEVICE = getDefaultOutputDevice()["name"]
        self._INPUT_SPEAKER_ENERGY_THRESHOLD = 300
        self._INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = False
        self._INPUT_SPEAKER_RECORD_TIMEOUT = 3
        self._INPUT_SPEAKER_PHRASE_TIMEOUT = 3
        self._INPUT_SPEAKER_MAX_PHRASES = 10
        self._OSC_IP_ADDRESS = "127.0.0.1"
        self._OSC_PORT = 9000
        self._AUTH_KEYS = {
            "DeepL(web)": None,
            "DeepL(auth)": None,
            "Bing(web)": None,
            "Google(web)": None,
        }
        self._MESSAGE_FORMAT = "[message]([translation])"
        self._ENABLE_AUTO_CLEAR_MESSAGE_BOX = True
        self._ENABLE_NOTICE_XSOVERLAY = False
        self._ENABLE_SEND_MESSAGE_TO_VRC = True
        # self._STARTUP_OSC_ENABLED_CHECK = True # [deprecated]
        self._ENABLE_LOGGER = False
        self._IS_CONFIG_WINDOW_COMPACT_MODE = False

    def load_config(self):
        if os_path.isfile(self.PATH_CONFIG) is not False:
            with open(self.PATH_CONFIG, 'r', encoding="utf-8") as fp:
                config = json_load(fp)

            for key in config.keys():
                setattr(self, key, config[key])

        with open(self.PATH_CONFIG, 'w', encoding="utf-8") as fp:
            config = {}
            for var_name, var_func in json_serializable_vars.items():
                config[var_name] = var_func(self)
            json_dump(config, fp, indent=4, ensure_ascii=False)

config = Config()