import copy
import inspect
from json import load as json_load, dump as json_dump # PEP 8: imports on separate lines if from same module and aliased
from os import path as os_path, makedirs as os_makedirs # PEP 8: imports on separate lines
import sys
import threading
from typing import Any, Callable, Dict, Optional

import torch

from device_manager import device_manager
from models.transcription.transcription_languages import transcription_lang
from models.transcription.transcription_whisper import _MODELS as whisper_models
from models.translation.translation_languages import translation_lang
from models.translation.translation_utils import ctranslate2_weights
from utils import errorLogging


json_serializable_vars: Dict[str, Callable[["Config"], Any]] = {}
def json_serializable(var_name: str) -> Callable[[Callable[["Config"], Any]], Callable[["Config"], Any]]:
    """
    Decorator to mark properties that should be included in the config.json file.

    This decorator populates the `json_serializable_vars` dictionary, which maps
    variable names to their corresponding getter functions.
    """
    def decorator(func: Callable[["Config"], Any]) -> Callable[["Config"], Any]:
        json_serializable_vars[var_name] = func
        return func
    return decorator


class Config:
    """
    Singleton class for managing application settings.

    This class handles loading settings from and saving settings to `config.json`.
    It uses a debouncing mechanism to avoid frequent writes to the configuration file.
    When a setting is changed via a property setter that calls `saveConfig`,
    a timer is started. If another change occurs before the timer expires,
    the timer is reset. The actual save operation (`saveConfigToFile`)
    is performed only after the debounce time has passed without further changes.
    This prevents excessive disk I/O during rapid configuration updates.
    """
    _instance: Optional["Config"] = None
    _config_data: Dict[str, Any] = {}
    _timer: Optional[threading.Timer] = None
    _debounce_time: int = 2

    def __new__(cls, *args: Any, **kwargs: Any) -> "Config":
        """
        Enforces the singleton pattern for the Config class.

        If an instance of Config already exists, it returns that instance.
        Otherwise, it creates a new instance, initializes its default configuration,
        and loads any existing configuration from `config.json`.
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.init_config()  # Initialize first to set up _PATH_CONFIG
            cls._instance.load_config()
        return cls._instance

    def saveConfigToFile(self) -> None:
        """Saves the current `_config_data` to `PATH_CONFIG` in JSON format."""
        with open(self.PATH_CONFIG, "w", encoding="utf-8") as fp:
            json_dump(self._config_data, fp, indent=4, ensure_ascii=False)

    def saveConfig(self, key: str, value: Any, immediate_save: bool = False) -> None:
        """
        Updates a configuration value in `_config_data` and schedules a save.

        If `immediate_save` is True, the configuration is saved immediately.
        Otherwise, a debouncing timer (`_timer`) is used: if multiple calls to
        `saveConfig` occur within `_debounce_time` seconds, the save operation
        is postponed until a quiet period is detected.
        """
        self._config_data[key] = value

        if isinstance(self._timer, threading.Timer) and self._timer.is_alive():
            self._timer.cancel()

        if immediate_save:
            self.saveConfigToFile()
        else:
            self._timer = threading.Timer(self._debounce_time, self.saveConfigToFile)
            self._timer.daemon = True
            self._timer.start()

    # Read Only
    @property
    def VERSION(self) -> str:
        """Application version."""
        return self._VERSION

    @property
    def PATH_LOCAL(self) -> str:
        """Path to the local application directory."""
        return self._PATH_LOCAL

    @property
    def PATH_CONFIG(self) -> str:
        """Path to the configuration file (config.json)."""
        return self._PATH_CONFIG

    @property
    def PATH_LOGS(self) -> str:
        """Path to the logs directory."""
        return self._PATH_LOGS

    @property
    def GITHUB_URL(self) -> str:
        """URL for checking the latest application release on GitHub."""
        return self._GITHUB_URL

    @property
    def UPDATER_URL(self) -> str:
        """URL for checking the latest updater release on GitHub."""
        return self._UPDATER_URL

    @property
    def BOOTH_URL(self) -> str:
        """URL to the application's BOOTH.pm page."""
        return self._BOOTH_URL

    @property
    def DOCUMENTS_URL(self) -> str:
        """URL to the application's documentation page."""
        return self._DOCUMENTS_URL

    @property
    def DEEPL_AUTH_KEY_PAGE_URL(self) -> str:
        """URL to the DeepL authentication key page."""
        return self._DEEPL_AUTH_KEY_PAGE_URL

    @property
    def MAX_MIC_THRESHOLD(self) -> int:
        """Maximum microphone threshold value."""
        return self._MAX_MIC_THRESHOLD

    @property
    def MAX_SPEAKER_THRESHOLD(self) -> int:
        """Maximum speaker threshold value."""
        return self._MAX_SPEAKER_THRESHOLD

    @property
    def WATCHDOG_TIMEOUT(self) -> int:
        """Timeout for the watchdog in seconds."""
        return self._WATCHDOG_TIMEOUT

    @property
    def WATCHDOG_INTERVAL(self) -> int:
        """Interval for the watchdog in seconds."""
        return self._WATCHDOG_INTERVAL

    @property
    def SELECTABLE_TAB_NO_LIST(self) -> list[str]:
        """List of selectable tab numbers."""
        return self._SELECTABLE_TAB_NO_LIST

    @property
    def SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST(self) -> list[str]:
        """List of selectable CTranslate2 weight types."""
        return list(self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST) # Ensure it's a list

    @property
    def SELECTABLE_WHISPER_WEIGHT_TYPE_LIST(self) -> list[str]:
        """List of selectable Whisper weight types."""
        return list(self._SELECTABLE_WHISPER_WEIGHT_TYPE_LIST) # Ensure it's a list

    @property
    def SELECTABLE_TRANSLATION_ENGINE_LIST(self) -> list[str]:
        """List of selectable translation engines."""
        return list(self._SELECTABLE_TRANSLATION_ENGINE_LIST) # Ensure it's a list

    @property
    def SELECTABLE_TRANSCRIPTION_ENGINE_LIST(self) -> list[str]:
        """List of selectable transcription engines."""
        return list(self._SELECTABLE_TRANSCRIPTION_ENGINE_LIST) # Ensure it's a list

    @property
    def SELECTABLE_UI_LANGUAGE_LIST(self) -> list[str]:
        """List of selectable UI languages."""
        return self._SELECTABLE_UI_LANGUAGE_LIST

    @property
    def COMPUTE_MODE(self) -> str:
        """Compute mode ('cuda' or 'cpu')."""
        return self._COMPUTE_MODE

    @property
    def SELECTABLE_COMPUTE_DEVICE_LIST(self) -> list[Dict[str, Any]]:
        """List of selectable compute devices."""
        return self._SELECTABLE_COMPUTE_DEVICE_LIST

    @property
    def SEND_MESSAGE_BUTTON_TYPE_LIST(self) -> list[str]:
        """List of send message button types."""
        return self._SEND_MESSAGE_BUTTON_TYPE_LIST

    @property
    def SEND_MESSAGE_FORMAT(self) -> str:
        """Format for sent messages."""
        return self._SEND_MESSAGE_FORMAT

    @property
    def SEND_MESSAGE_FORMAT_WITH_T(self) -> str:
        """Format for sent messages with translation."""
        return self._SEND_MESSAGE_FORMAT_WITH_T

    @property
    def RECEIVED_MESSAGE_FORMAT(self) -> str:
        """Format for received messages."""
        return self._RECEIVED_MESSAGE_FORMAT

    @property
    def RECEIVED_MESSAGE_FORMAT_WITH_T(self) -> str:
        """Format for received messages with translation."""
        return self._RECEIVED_MESSAGE_FORMAT_WITH_T

    # Read Write
    @property
    def ENABLE_TRANSLATION(self) -> bool:
        """Whether translation is enabled."""
        return self._ENABLE_TRANSLATION

    @ENABLE_TRANSLATION.setter
    def ENABLE_TRANSLATION(self, value: bool) -> None:
        """
        Sets whether translation is enabled.
        Expected type: bool.
        """
        if isinstance(value, bool):
            self._ENABLE_TRANSLATION = value

    @property
    def ENABLE_TRANSCRIPTION_SEND(self) -> bool:
        """Whether sending transcriptions is enabled."""
        return self._ENABLE_TRANSCRIPTION_SEND

    @ENABLE_TRANSCRIPTION_SEND.setter
    def ENABLE_TRANSCRIPTION_SEND(self, value: bool) -> None:
        """
        Sets whether sending transcriptions is enabled.
        Expected type: bool.
        """
        if isinstance(value, bool):
            self._ENABLE_TRANSCRIPTION_SEND = value

    @property
    def ENABLE_TRANSCRIPTION_RECEIVE(self) -> bool:
        """Whether receiving transcriptions is enabled."""
        return self._ENABLE_TRANSCRIPTION_RECEIVE

    @ENABLE_TRANSCRIPTION_RECEIVE.setter
    def ENABLE_TRANSCRIPTION_RECEIVE(self, value: bool) -> None:
        """
        Sets whether receiving transcriptions is enabled.
        Expected type: bool.
        """
        if isinstance(value, bool):
            self._ENABLE_TRANSCRIPTION_RECEIVE = value

    @property
    def ENABLE_FOREGROUND(self) -> bool:
        """Whether the application window stays in the foreground."""
        return self._ENABLE_FOREGROUND

    @ENABLE_FOREGROUND.setter
    def ENABLE_FOREGROUND(self, value: bool) -> None:
        """
        Sets whether the application window stays in the foreground.
        Expected type: bool.
        """
        if isinstance(value, bool):
            self._ENABLE_FOREGROUND = value

    @property
    def ENABLE_CHECK_ENERGY_SEND(self) -> bool:
        """Whether to check audio energy for sending transcriptions."""
        return self._ENABLE_CHECK_ENERGY_SEND

    @ENABLE_CHECK_ENERGY_SEND.setter
    def ENABLE_CHECK_ENERGY_SEND(self, value: bool) -> None:
        """
        Sets whether to check audio energy for sending transcriptions.
        Expected type: bool.
        """
        if isinstance(value, bool):
            self._ENABLE_CHECK_ENERGY_SEND = value

    @property
    def ENABLE_CHECK_ENERGY_RECEIVE(self) -> bool:
        """Whether to check audio energy for receiving transcriptions."""
        return self._ENABLE_CHECK_ENERGY_RECEIVE

    @ENABLE_CHECK_ENERGY_RECEIVE.setter
    def ENABLE_CHECK_ENERGY_RECEIVE(self, value: bool) -> None:
        """
        Sets whether to check audio energy for receiving transcriptions.
        Expected type: bool.
        """
        if isinstance(value, bool):
            self._ENABLE_CHECK_ENERGY_RECEIVE = value

    @property
    def SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT(self) -> Dict[str, bool]:
        """Dictionary of selectable CTranslate2 weight types and their status."""
        return self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT

    @SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT.setter
    def SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT(self, value: Dict[str, bool]) -> None:
        """
        Sets the dictionary of selectable CTranslate2 weight types and their status.
        Expected type: Dict[str, bool].
        """
        if isinstance(value, dict):
            self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT = value

    @property
    def SELECTABLE_WHISPER_WEIGHT_TYPE_DICT(self) -> Dict[str, bool]:
        """Dictionary of selectable Whisper weight types and their status."""
        return self._SELECTABLE_WHISPER_WEIGHT_TYPE_DICT

    @SELECTABLE_WHISPER_WEIGHT_TYPE_DICT.setter
    def SELECTABLE_WHISPER_WEIGHT_TYPE_DICT(self, value: Dict[str, bool]) -> None:
        """
        Sets the dictionary of selectable Whisper weight types and their status.
        Expected type: Dict[str, bool].
        """
        if isinstance(value, dict):
            self._SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = value

    @property
    def SELECTABLE_TRANSLATION_ENGINE_STATUS(self) -> Dict[str, bool]:
        """Dictionary of selectable translation engines and their status."""
        return self._SELECTABLE_TRANSLATION_ENGINE_STATUS

    @SELECTABLE_TRANSLATION_ENGINE_STATUS.setter
    def SELECTABLE_TRANSLATION_ENGINE_STATUS(self, value: Dict[str, bool]) -> None:
        """
        Sets the dictionary of selectable translation engines and their status.
        Expected type: Dict[str, bool].
        """
        if isinstance(value, dict):
            self._SELECTABLE_TRANSLATION_ENGINE_STATUS = value

    @property
    def SELECTABLE_TRANSCRIPTION_ENGINE_STATUS(self) -> Dict[str, bool]:
        """Dictionary of selectable transcription engines and their status."""
        return self._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS

    @SELECTABLE_TRANSCRIPTION_ENGINE_STATUS.setter
    def SELECTABLE_TRANSCRIPTION_ENGINE_STATUS(self, value: Dict[str, bool]) -> None:
        """
        Sets the dictionary of selectable transcription engines and their status.
        Expected type: Dict[str, bool].
        """
        if isinstance(value, dict):
            self._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = value

    # Save Json Data
    ## Main Window
    @property
    @json_serializable('SELECTED_TAB_NO')
    def SELECTED_TAB_NO(self) -> str:
        """Currently selected tab number in the main window."""
        return self._SELECTED_TAB_NO

    @SELECTED_TAB_NO.setter
    def SELECTED_TAB_NO(self, value: str) -> None:
        """
        Sets the currently selected tab number.
        Expected type: str (must be in SELECTABLE_TAB_NO_LIST).
        Saves the configuration when set.
        """
        if isinstance(value, str):
            if value in self.SELECTABLE_TAB_NO_LIST:
                self._SELECTED_TAB_NO = value
                self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_TRANSLATION_ENGINES')
    def SELECTED_TRANSLATION_ENGINES(self) -> Dict[str, str]:
        """Selected translation engines for each tab."""
        return self._SELECTED_TRANSLATION_ENGINES

    @SELECTED_TRANSLATION_ENGINES.setter
    def SELECTED_TRANSLATION_ENGINES(self, value: Dict[str, str]) -> None:
        """
        Sets the selected translation engines for each tab.
        Expected type: Dict[str, str] (engine must be in SELECTABLE_TRANSLATION_ENGINE_LIST).
        Saves the configuration when set.
        """
        if isinstance(value, dict):
            old_value = self.SELECTED_TRANSLATION_ENGINES
            for k, v in value.items():
                if v not in self.SELECTABLE_TRANSLATION_ENGINE_LIST:
                    value[k] = old_value[k]
            self._SELECTED_TRANSLATION_ENGINES = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_YOUR_LANGUAGES')
    def SELECTED_YOUR_LANGUAGES(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Selected 'your' languages for transcription for each tab."""
        return self._SELECTED_YOUR_LANGUAGES

    @SELECTED_YOUR_LANGUAGES.setter
    def SELECTED_YOUR_LANGUAGES(self, value: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
        """
        Sets the selected 'your' languages for transcription.
        Expected type: Dict[str, Dict[str, Dict[str, Any]]] with specific structure.
        Saves the configuration when set.
        """
        if isinstance(value, dict):
            value_old = self.SELECTED_YOUR_LANGUAGES
            for k0, v0 in value.items():
                for k1, v1 in v0.items():
                    language = v1["language"]
                    country = v1["country"]
                    enable = v1["enable"]
                    if (language not in list(transcription_lang.keys()) or
                        country not in list(transcription_lang[language].keys()) or
                        not isinstance(enable, bool)):
                        value[k0][k1] = value_old[k0][k1]
            self._SELECTED_YOUR_LANGUAGES = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_TARGET_LANGUAGES')
    def SELECTED_TARGET_LANGUAGES(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Selected target languages for translation for each tab."""
        return self._SELECTED_TARGET_LANGUAGES

    @SELECTED_TARGET_LANGUAGES.setter
    def SELECTED_TARGET_LANGUAGES(self, value: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
        """
        Sets the selected target languages for translation.
        Expected type: Dict[str, Dict[str, Dict[str, Any]]] with specific structure.
        Saves the configuration when set.
        """
        if isinstance(value, dict):
            value_old = self.SELECTED_TARGET_LANGUAGES
            for k0, v0 in value.items():
                for k1, v1 in v0.items():
                    language = v1["language"]
                    country = v1["country"]
                    enable = v1["enable"]
                    if (language not in list(transcription_lang.keys()) or
                        country not in list(transcription_lang[language].keys()) or
                        not isinstance(enable, bool)):
                        value[k0][k1] = value_old[k0][k1]
            self._SELECTED_TARGET_LANGUAGES = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_TRANSCRIPTION_ENGINE')
    def SELECTED_TRANSCRIPTION_ENGINE(self) -> str:
        """Selected transcription engine."""
        return self._SELECTED_TRANSCRIPTION_ENGINE

    @SELECTED_TRANSCRIPTION_ENGINE.setter
    def SELECTED_TRANSCRIPTION_ENGINE(self, value: str) -> None:
        """
        Sets the selected transcription engine.
        Expected type: str (must be in SELECTABLE_TRANSCRIPTION_ENGINE_LIST).
        Saves the configuration when set.
        """
        if isinstance(value, str):
            if value in self.SELECTABLE_TRANSCRIPTION_ENGINE_LIST:
                self._SELECTED_TRANSCRIPTION_ENGINE = value
                self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('CONVERT_MESSAGE_TO_ROMAJI')
    def CONVERT_MESSAGE_TO_ROMAJI(self) -> bool:
        """Whether to convert messages to Romaji."""
        return self._CONVERT_MESSAGE_TO_ROMAJI

    @CONVERT_MESSAGE_TO_ROMAJI.setter
    def CONVERT_MESSAGE_TO_ROMAJI(self, value: bool) -> None:
        """
        Sets whether to convert messages to Romaji.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._CONVERT_MESSAGE_TO_ROMAJI = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('CONVERT_MESSAGE_TO_HIRAGANA')
    def CONVERT_MESSAGE_TO_HIRAGANA(self) -> bool:
        """Whether to convert messages to Hiragana."""
        return self._CONVERT_MESSAGE_TO_HIRAGANA

    @CONVERT_MESSAGE_TO_HIRAGANA.setter
    def CONVERT_MESSAGE_TO_HIRAGANA(self, value: bool) -> None:
        """
        Sets whether to convert messages to Hiragana.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._CONVERT_MESSAGE_TO_HIRAGANA = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('MAIN_WINDOW_SIDEBAR_COMPACT_MODE')
    def MAIN_WINDOW_SIDEBAR_COMPACT_MODE(self) -> bool:
        """Whether the main window sidebar is in compact mode."""
        return self._MAIN_WINDOW_SIDEBAR_COMPACT_MODE

    @MAIN_WINDOW_SIDEBAR_COMPACT_MODE.setter
    def MAIN_WINDOW_SIDEBAR_COMPACT_MODE(self, value: bool) -> None:
        """
        Sets whether the main window sidebar is in compact mode.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._MAIN_WINDOW_SIDEBAR_COMPACT_MODE = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    ## Config Window
    @property
    @json_serializable('TRANSPARENCY')
    def TRANSPARENCY(self) -> int:
        """UI transparency level (0-100)."""
        return self._TRANSPARENCY

    @TRANSPARENCY.setter
    def TRANSPARENCY(self, value: int) -> None:
        """
        Sets the UI transparency level.
        Expected type: int (0-100).
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._TRANSPARENCY = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('UI_SCALING')
    def UI_SCALING(self) -> int:
        """UI scaling percentage."""
        return self._UI_SCALING

    @UI_SCALING.setter
    def UI_SCALING(self, value: int) -> None:
        """
        Sets the UI scaling percentage.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._UI_SCALING = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('TEXTBOX_UI_SCALING')
    def TEXTBOX_UI_SCALING(self) -> int:
        """Textbox UI scaling percentage."""
        return self._TEXTBOX_UI_SCALING

    @TEXTBOX_UI_SCALING.setter
    def TEXTBOX_UI_SCALING(self, value: int) -> None:
        """
        Sets the textbox UI scaling percentage.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._TEXTBOX_UI_SCALING = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('MESSAGE_BOX_RATIO')
    def MESSAGE_BOX_RATIO(self) -> float: # Changed to float as int|float is not ideal for property
        """Ratio of the message box height."""
        return self._MESSAGE_BOX_RATIO

    @MESSAGE_BOX_RATIO.setter
    def MESSAGE_BOX_RATIO(self, value: float) -> None:
        """
        Sets the ratio of the message box height.
        Expected type: int or float.
        Saves the configuration immediately when set.
        """
        if isinstance(value, (int, float)):
            self._MESSAGE_BOX_RATIO = float(value)
            self.saveConfig(inspect.currentframe().f_code.co_name, float(value), immediate_save=True)

    @property
    @json_serializable('FONT_FAMILY')
    def FONT_FAMILY(self) -> str:
        """Font family for the UI."""
        return self._FONT_FAMILY

    @FONT_FAMILY.setter
    def FONT_FAMILY(self, value: str) -> None:
        """
        Sets the font family for the UI.
        Expected type: str.
        Saves the configuration when set.
        """
        if isinstance(value, str):
            self._FONT_FAMILY = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('UI_LANGUAGE')
    def UI_LANGUAGE(self) -> str:
        """UI language setting."""
        return self._UI_LANGUAGE

    @UI_LANGUAGE.setter
    def UI_LANGUAGE(self, value: str) -> None:
        """
        Sets the UI language.
        Expected type: str (must be in SELECTABLE_UI_LANGUAGE_LIST).
        Saves the configuration when set.
        """
        if isinstance(value, str):
            if value in self.SELECTABLE_UI_LANGUAGE_LIST:
                self._UI_LANGUAGE = value
                self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('MAIN_WINDOW_GEOMETRY')
    def MAIN_WINDOW_GEOMETRY(self) -> Dict[str, int]:
        """Main window geometry (position and size)."""
        return self._MAIN_WINDOW_GEOMETRY

    @MAIN_WINDOW_GEOMETRY.setter
    def MAIN_WINDOW_GEOMETRY(self, value: Dict[str, int]) -> None:
        """
        Sets the main window geometry.
        Expected type: Dict[str, int] with keys 'x_pos', 'y_pos', 'width', 'height'.
        Saves the configuration immediately when set.
        """
        if isinstance(value, dict) and set(value.keys()) == set(self.MAIN_WINDOW_GEOMETRY.keys()):
            for key, val in value.items(): # Use val to avoid conflict with outer value
                if isinstance(val, int):
                    self._MAIN_WINDOW_GEOMETRY[key] = val
            self.saveConfig(inspect.currentframe().f_code.co_name, self.MAIN_WINDOW_GEOMETRY, immediate_save=True)

    @property
    @json_serializable('AUTO_MIC_SELECT')
    def AUTO_MIC_SELECT(self) -> bool:
        """Whether to automatically select the microphone."""
        return self._AUTO_MIC_SELECT

    @AUTO_MIC_SELECT.setter
    def AUTO_MIC_SELECT(self, value: bool) -> None:
        """
        Sets whether to automatically select the microphone.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._AUTO_MIC_SELECT = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_MIC_HOST')
    def SELECTED_MIC_HOST(self) -> str:
        """Selected microphone host API."""
        return self._SELECTED_MIC_HOST

    @SELECTED_MIC_HOST.setter
    def SELECTED_MIC_HOST(self, value: str) -> None:
        """
        Sets the selected microphone host API.
        Expected type: str (must be a valid host from device_manager).
        Saves the configuration when set.
        """
        if value in [host for host in device_manager.getMicDevices().keys()]:
            self._SELECTED_MIC_HOST = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_MIC_DEVICE')
    def SELECTED_MIC_DEVICE(self) -> str:
        """Selected microphone device name."""
        return self._SELECTED_MIC_DEVICE

    @SELECTED_MIC_DEVICE.setter
    def SELECTED_MIC_DEVICE(self, value: str) -> None:
        """
        Sets the selected microphone device name.
        Expected type: str (must be a valid device for the SELECTED_MIC_HOST).
        Saves the configuration when set.
        """
        if value in [device["name"] for device in device_manager.getMicDevices()[self.SELECTED_MIC_HOST]]:
            self._SELECTED_MIC_DEVICE = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('MIC_THRESHOLD')
    def MIC_THRESHOLD(self) -> int:
        """Microphone audio threshold."""
        return self._MIC_THRESHOLD

    @MIC_THRESHOLD.setter
    def MIC_THRESHOLD(self, value: int) -> None:
        """
        Sets the microphone audio threshold.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._MIC_THRESHOLD = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('MIC_AUTOMATIC_THRESHOLD')
    def MIC_AUTOMATIC_THRESHOLD(self) -> bool:
        """Whether automatic microphone threshold adjustment is enabled."""
        return self._MIC_AUTOMATIC_THRESHOLD

    @MIC_AUTOMATIC_THRESHOLD.setter
    def MIC_AUTOMATIC_THRESHOLD(self, value: bool) -> None:
        """
        Sets whether automatic microphone threshold adjustment is enabled.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._MIC_AUTOMATIC_THRESHOLD = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('MIC_RECORD_TIMEOUT')
    def MIC_RECORD_TIMEOUT(self) -> int:
        """Microphone recording timeout in seconds."""
        return self._MIC_RECORD_TIMEOUT

    @MIC_RECORD_TIMEOUT.setter
    def MIC_RECORD_TIMEOUT(self, value: int) -> None:
        """
        Sets the microphone recording timeout.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._MIC_RECORD_TIMEOUT = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('MIC_PHRASE_TIMEOUT')
    def MIC_PHRASE_TIMEOUT(self) -> int:
        """Microphone phrase timeout in seconds."""
        return self._MIC_PHRASE_TIMEOUT

    @MIC_PHRASE_TIMEOUT.setter
    def MIC_PHRASE_TIMEOUT(self, value: int) -> None:
        """
        Sets the microphone phrase timeout.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._MIC_PHRASE_TIMEOUT = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('MIC_MAX_PHRASES')
    def MIC_MAX_PHRASES(self) -> int:
        """Maximum number of phrases to keep for microphone input."""
        return self._MIC_MAX_PHRASES

    @MIC_MAX_PHRASES.setter
    def MIC_MAX_PHRASES(self, value: int) -> None:
        """
        Sets the maximum number of phrases for microphone input.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._MIC_MAX_PHRASES = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('MIC_WORD_FILTER')
    def MIC_WORD_FILTER(self) -> list[str]:
        """List of words to filter from microphone input."""
        return self._MIC_WORD_FILTER

    @MIC_WORD_FILTER.setter
    def MIC_WORD_FILTER(self, value: list[str]) -> None:
        """
        Sets the list of words to filter from microphone input.
        Expected type: list[str].
        Saves the configuration when set.
        """
        if isinstance(value, list):
            self._MIC_WORD_FILTER = sorted(set(value), key=value.index) # Keep original order for unique items
            self.saveConfig(inspect.currentframe().f_code.co_name, self._MIC_WORD_FILTER) # Save the processed list

    @property
    @json_serializable('HOTKEYS')
    def HOTKEYS(self) -> Dict[str, Optional[list[str]]]:
        """Hotkey configurations."""
        return self._HOTKEYS

    @HOTKEYS.setter
    def HOTKEYS(self, value: Dict[str, Optional[list[str]]]) -> None:
        """
        Sets the hotkey configurations.
        Expected type: Dict[str, Optional[list[str]]].
        Saves the configuration immediately when set.
        """
        if isinstance(value, dict) and set(value.keys()) == set(self.HOTKEYS.keys()):
            for key, val in value.items(): # Use val to avoid conflict
                if isinstance(val, list) or val is None:
                    self._HOTKEYS[key] = val
            self.saveConfig(inspect.currentframe().f_code.co_name, self.HOTKEYS, immediate_save=True)

    @property
    @json_serializable('PLUGINS_STATUS')
    def PLUGINS_STATUS(self) -> list[Dict[str, Any]]:
        """Status of installed plugins."""
        return self._PLUGINS_STATUS

    @PLUGINS_STATUS.setter
    def PLUGINS_STATUS(self, value: list[Dict[str, Any]]) -> None:
        """
        Sets the status of installed plugins.
        Expected type: list[Dict[str, Any]].
        Saves the configuration immediately when set.
        """
        if isinstance(value, list):
            if all(isinstance(item, dict) for item in value):
                self._PLUGINS_STATUS = value
                self.saveConfig(inspect.currentframe().f_code.co_name, self.PLUGINS_STATUS, immediate_save=True)

    @property
    @json_serializable('MIC_AVG_LOGPROB')
    def MIC_AVG_LOGPROB(self) -> float:
        """Microphone average log probability threshold."""
        return self._MIC_AVG_LOGPROB

    @MIC_AVG_LOGPROB.setter
    def MIC_AVG_LOGPROB(self, value: float) -> None:
        """
        Sets the microphone average log probability threshold.
        Expected type: int or float.
        Saves the configuration when set.
        """
        if isinstance(value, (int, float)):
            self._MIC_AVG_LOGPROB = float(value)
            self.saveConfig(inspect.currentframe().f_code.co_name, float(value))

    @property
    @json_serializable('MIC_NO_SPEECH_PROB')
    def MIC_NO_SPEECH_PROB(self) -> float:
        """Microphone no speech probability threshold."""
        return self._MIC_NO_SPEECH_PROB

    @MIC_NO_SPEECH_PROB.setter
    def MIC_NO_SPEECH_PROB(self, value: float) -> None:
        """
        Sets the microphone no speech probability threshold.
        Expected type: int or float.
        Saves the configuration when set.
        """
        if isinstance(value, (int, float)):
            self._MIC_NO_SPEECH_PROB = float(value)
            self.saveConfig(inspect.currentframe().f_code.co_name, float(value))

    @property
    @json_serializable('AUTO_SPEAKER_SELECT')
    def AUTO_SPEAKER_SELECT(self) -> bool:
        """Whether to automatically select the speaker device."""
        return self._AUTO_SPEAKER_SELECT

    @AUTO_SPEAKER_SELECT.setter
    def AUTO_SPEAKER_SELECT(self, value: bool) -> None:
        """
        Sets whether to automatically select the speaker device.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._AUTO_SPEAKER_SELECT = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_SPEAKER_DEVICE')
    def SELECTED_SPEAKER_DEVICE(self) -> str:
        """Selected speaker device name."""
        return self._SELECTED_SPEAKER_DEVICE

    @SELECTED_SPEAKER_DEVICE.setter
    def SELECTED_SPEAKER_DEVICE(self, value: str) -> None:
        """
        Sets the selected speaker device name.
        Expected type: str (must be a valid device from device_manager).
        Saves the configuration when set.
        """
        if value in [device["name"] for device in device_manager.getSpeakerDevices()]:
            self._SELECTED_SPEAKER_DEVICE = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SPEAKER_THRESHOLD')
    def SPEAKER_THRESHOLD(self) -> int:
        """Speaker audio threshold."""
        return self._SPEAKER_THRESHOLD

    @SPEAKER_THRESHOLD.setter
    def SPEAKER_THRESHOLD(self, value: int) -> None:
        """
        Sets the speaker audio threshold.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._SPEAKER_THRESHOLD = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SPEAKER_AUTOMATIC_THRESHOLD')
    def SPEAKER_AUTOMATIC_THRESHOLD(self) -> bool:
        """Whether automatic speaker threshold adjustment is enabled."""
        return self._SPEAKER_AUTOMATIC_THRESHOLD

    @SPEAKER_AUTOMATIC_THRESHOLD.setter
    def SPEAKER_AUTOMATIC_THRESHOLD(self, value: bool) -> None:
        """
        Sets whether automatic speaker threshold adjustment is enabled.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._SPEAKER_AUTOMATIC_THRESHOLD = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SPEAKER_RECORD_TIMEOUT')
    def SPEAKER_RECORD_TIMEOUT(self) -> int:
        """Speaker recording timeout in seconds."""
        return self._SPEAKER_RECORD_TIMEOUT

    @SPEAKER_RECORD_TIMEOUT.setter
    def SPEAKER_RECORD_TIMEOUT(self, value: int) -> None:
        """
        Sets the speaker recording timeout.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._SPEAKER_RECORD_TIMEOUT = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SPEAKER_PHRASE_TIMEOUT')
    def SPEAKER_PHRASE_TIMEOUT(self) -> int:
        """Speaker phrase timeout in seconds."""
        return self._SPEAKER_PHRASE_TIMEOUT

    @SPEAKER_PHRASE_TIMEOUT.setter
    def SPEAKER_PHRASE_TIMEOUT(self, value: int) -> None:
        """
        Sets the speaker phrase timeout.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._SPEAKER_PHRASE_TIMEOUT = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SPEAKER_MAX_PHRASES')
    def SPEAKER_MAX_PHRASES(self) -> int:
        """Maximum number of phrases to keep for speaker input."""
        return self._SPEAKER_MAX_PHRASES

    @SPEAKER_MAX_PHRASES.setter
    def SPEAKER_MAX_PHRASES(self, value: int) -> None:
        """
        Sets the maximum number of phrases for speaker input.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._SPEAKER_MAX_PHRASES = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SPEAKER_AVG_LOGPROB')
    def SPEAKER_AVG_LOGPROB(self) -> float:
        """Speaker average log probability threshold."""
        return self._SPEAKER_AVG_LOGPROB

    @SPEAKER_AVG_LOGPROB.setter
    def SPEAKER_AVG_LOGPROB(self, value: float) -> None:
        """
        Sets the speaker average log probability threshold.
        Expected type: int or float.
        Saves the configuration when set.
        """
        if isinstance(value, (int, float)):
            self._SPEAKER_AVG_LOGPROB = float(value)
            self.saveConfig(inspect.currentframe().f_code.co_name, float(value))

    @property
    @json_serializable('SPEAKER_NO_SPEECH_PROB')
    def SPEAKER_NO_SPEECH_PROB(self) -> float:
        """Speaker no speech probability threshold."""
        return self._SPEAKER_NO_SPEECH_PROB

    @SPEAKER_NO_SPEECH_PROB.setter
    def SPEAKER_NO_SPEECH_PROB(self, value: float) -> None:
        """
        Sets the speaker no speech probability threshold.
        Expected type: int or float.
        Saves the configuration when set.
        """
        if isinstance(value, (int, float)):
            self._SPEAKER_NO_SPEECH_PROB = float(value)
            self.saveConfig(inspect.currentframe().f_code.co_name, float(value))

    @property
    @json_serializable('OSC_IP_ADDRESS')
    def OSC_IP_ADDRESS(self) -> str:
        """IP address for OSC communication."""
        return self._OSC_IP_ADDRESS

    @OSC_IP_ADDRESS.setter
    def OSC_IP_ADDRESS(self, value: str) -> None:
        """
        Sets the IP address for OSC communication.
        Expected type: str.
        Saves the configuration when set.
        """
        if isinstance(value, str):
            self._OSC_IP_ADDRESS = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('OSC_PORT')
    def OSC_PORT(self) -> int:
        """Port for OSC communication."""
        return self._OSC_PORT

    @OSC_PORT.setter
    def OSC_PORT(self, value: int) -> None:
        """
        Sets the port for OSC communication.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._OSC_PORT = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('AUTH_KEYS')
    def AUTH_KEYS(self) -> Dict[str, Optional[str]]: # Assuming keys can be None
        """Authentication keys for various services (e.g., DeepL)."""
        return self._AUTH_KEYS

    @AUTH_KEYS.setter
    def AUTH_KEYS(self, value: Dict[str, Optional[str]]) -> None:
        """
        Sets the authentication keys.
        Expected type: Dict[str, Optional[str]].
        Saves the configuration when set.
        """
        if isinstance(value, dict) and set(value.keys()) == set(self.AUTH_KEYS.keys()):
            for key, val in value.items(): # Use val
                if isinstance(val, str) or val is None: # Allow None
                    self._AUTH_KEYS[key] = val
            self.saveConfig(inspect.currentframe().f_code.co_name, self.AUTH_KEYS)

    @property
    @json_serializable('USE_EXCLUDE_WORDS')
    def USE_EXCLUDE_WORDS(self) -> bool:
        """Whether to use the exclude words list."""
        return self._USE_EXCLUDE_WORDS

    @USE_EXCLUDE_WORDS.setter
    def USE_EXCLUDE_WORDS(self, value: bool) -> None:
        """
        Sets whether to use the exclude words list.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._USE_EXCLUDE_WORDS = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_TRANSLATION_COMPUTE_DEVICE')
    def SELECTED_TRANSLATION_COMPUTE_DEVICE(self) -> Dict[str, Any]:
        """Selected compute device for translation."""
        return self._SELECTED_TRANSLATION_COMPUTE_DEVICE

    @SELECTED_TRANSLATION_COMPUTE_DEVICE.setter
    def SELECTED_TRANSLATION_COMPUTE_DEVICE(self, value: Dict[str, Any]) -> None:
        """
        Sets the selected compute device for translation.
        Expected type: Dict[str, Any] (must be in SELECTABLE_COMPUTE_DEVICE_LIST).
        Saves the configuration when set.
        """
        if isinstance(value, dict): # Simplified check, assuming structure is correct if type is dict
            if value in self.SELECTABLE_COMPUTE_DEVICE_LIST:
                self._SELECTED_TRANSLATION_COMPUTE_DEVICE = value
                self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SELECTED_TRANSCRIPTION_COMPUTE_DEVICE')
    def SELECTED_TRANSCRIPTION_COMPUTE_DEVICE(self) -> Dict[str, Any]:
        """Selected compute device for transcription."""
        return self._SELECTED_TRANSCRIPTION_COMPUTE_DEVICE

    @SELECTED_TRANSCRIPTION_COMPUTE_DEVICE.setter
    def SELECTED_TRANSCRIPTION_COMPUTE_DEVICE(self, value: Dict[str, Any]) -> None:
        """
        Sets the selected compute device for transcription.
        Expected type: Dict[str, Any] (must be in SELECTABLE_COMPUTE_DEVICE_LIST).
        Saves the configuration when set.
        """
        if isinstance(value, dict): # Simplified check
            if value in self.SELECTABLE_COMPUTE_DEVICE_LIST:
                self._SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = value
                self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('CTRANSLATE2_WEIGHT_TYPE')
    def CTRANSLATE2_WEIGHT_TYPE(self) -> str:
        """Selected CTranslate2 weight type."""
        return self._CTRANSLATE2_WEIGHT_TYPE

    @CTRANSLATE2_WEIGHT_TYPE.setter
    def CTRANSLATE2_WEIGHT_TYPE(self, value: str) -> None:
        """
        Sets the CTranslate2 weight type.
        Expected type: str (must be in SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST).
        Saves the configuration when set.
        """
        if isinstance(value, str):
            if value in self.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST:
                self._CTRANSLATE2_WEIGHT_TYPE = value
                self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('WHISPER_WEIGHT_TYPE')
    def WHISPER_WEIGHT_TYPE(self) -> str:
        """Selected Whisper weight type."""
        return self._WHISPER_WEIGHT_TYPE

    @WHISPER_WEIGHT_TYPE.setter
    def WHISPER_WEIGHT_TYPE(self, value: str) -> None:
        """
        Sets the Whisper weight type.
        Expected type: str (must be in SELECTABLE_WHISPER_WEIGHT_TYPE_LIST).
        Saves the configuration when set.
        """
        if isinstance(value, str):
            if value in self.SELECTABLE_WHISPER_WEIGHT_TYPE_LIST:
                self._WHISPER_WEIGHT_TYPE = value
                self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('AUTO_CLEAR_MESSAGE_BOX')
    def AUTO_CLEAR_MESSAGE_BOX(self) -> bool:
        """Whether to automatically clear the message box after sending."""
        return self._AUTO_CLEAR_MESSAGE_BOX

    @AUTO_CLEAR_MESSAGE_BOX.setter
    def AUTO_CLEAR_MESSAGE_BOX(self, value: bool) -> None:
        """
        Sets whether to automatically clear the message box.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._AUTO_CLEAR_MESSAGE_BOX = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SEND_ONLY_TRANSLATED_MESSAGES')
    def SEND_ONLY_TRANSLATED_MESSAGES(self) -> bool:
        """Whether to send only translated messages (hiding original)."""
        return self._SEND_ONLY_TRANSLATED_MESSAGES

    @SEND_ONLY_TRANSLATED_MESSAGES.setter
    def SEND_ONLY_TRANSLATED_MESSAGES(self, value: bool) -> None:
        """
        Sets whether to send only translated messages.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._SEND_ONLY_TRANSLATED_MESSAGES = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SEND_MESSAGE_BUTTON_TYPE')
    def SEND_MESSAGE_BUTTON_TYPE(self) -> str:
        """Type of send message button behavior."""
        return self._SEND_MESSAGE_BUTTON_TYPE

    @SEND_MESSAGE_BUTTON_TYPE.setter
    def SEND_MESSAGE_BUTTON_TYPE(self, value: str) -> None:
        """
        Sets the type of send message button behavior.
        Expected type: str (must be in SEND_MESSAGE_BUTTON_TYPE_LIST).
        Saves the configuration when set.
        """
        if isinstance(value, str):
            if value in self.SEND_MESSAGE_BUTTON_TYPE_LIST:
                self._SEND_MESSAGE_BUTTON_TYPE = value
                self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('OVERLAY_SMALL_LOG')
    def OVERLAY_SMALL_LOG(self) -> bool:
        """Whether the small log overlay is enabled."""
        return self._OVERLAY_SMALL_LOG

    @OVERLAY_SMALL_LOG.setter
    def OVERLAY_SMALL_LOG(self, value: bool) -> None:
        """
        Sets whether the small log overlay is enabled.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._OVERLAY_SMALL_LOG = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('OVERLAY_SMALL_LOG_SETTINGS')
    def OVERLAY_SMALL_LOG_SETTINGS(self) -> Dict[str, Any]:
        """Settings for the small log overlay."""
        return self._OVERLAY_SMALL_LOG_SETTINGS

    @OVERLAY_SMALL_LOG_SETTINGS.setter
    def OVERLAY_SMALL_LOG_SETTINGS(self, value: Dict[str, Any]) -> None:
        """
        Sets the settings for the small log overlay.
        Expected type: Dict[str, Any] with specific structure and validation.
        Saves the configuration when set.
        """
        if isinstance(value, dict) and set(value.keys()) == set(self.OVERLAY_SMALL_LOG_SETTINGS.keys()):
            for key, val in value.items(): # Use val
                match (key):
                    case "tracker":
                        if isinstance(val, str):
                            if val in ["HMD", "LeftHand", "RightHand"]:
                                self._OVERLAY_SMALL_LOG_SETTINGS[key] = val
                    case "x_pos" | "y_pos" | "z_pos" | "x_rotation" | "y_rotation" | "z_rotation":
                        if isinstance(val, (int, float)):
                            self._OVERLAY_SMALL_LOG_SETTINGS[key] = float(val)
                    case "display_duration" | "fadeout_duration":
                        if isinstance(val, int):
                            self._OVERLAY_SMALL_LOG_SETTINGS[key] = val
                    case "opacity" | "ui_scaling":
                        if isinstance(val, (int, float)):
                            self._OVERLAY_SMALL_LOG_SETTINGS[key] = float(val)
            self.saveConfig(inspect.currentframe().f_code.co_name, self.OVERLAY_SMALL_LOG_SETTINGS)

    @property
    @json_serializable('OVERLAY_LARGE_LOG')
    def OVERLAY_LARGE_LOG(self) -> bool:
        """Whether the large log overlay is enabled."""
        return self._OVERLAY_LARGE_LOG

    @OVERLAY_LARGE_LOG.setter
    def OVERLAY_LARGE_LOG(self, value: bool) -> None:
        """
        Sets whether the large log overlay is enabled.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._OVERLAY_LARGE_LOG = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('OVERLAY_LARGE_LOG_SETTINGS')
    def OVERLAY_LARGE_LOG_SETTINGS(self) -> Dict[str, Any]:
        """Settings for the large log overlay."""
        return self._OVERLAY_LARGE_LOG_SETTINGS

    @OVERLAY_LARGE_LOG_SETTINGS.setter
    def OVERLAY_LARGE_LOG_SETTINGS(self, value: Dict[str, Any]) -> None:
        """
        Sets the settings for the large log overlay.
        Expected type: Dict[str, Any] with specific structure and validation.
        Saves the configuration when set.
        """
        if isinstance(value, dict) and set(value.keys()) == set(self.OVERLAY_LARGE_LOG_SETTINGS.keys()):
            for key, val in value.items(): # Use val
                match (key):
                    case "tracker":
                        if isinstance(val, str):
                            if val in ["HMD", "LeftHand", "RightHand"]:
                                self._OVERLAY_LARGE_LOG_SETTINGS[key] = val
                    case "x_pos" | "y_pos" | "z_pos" | "x_rotation" | "y_rotation" | "z_rotation":
                        if isinstance(val, (int, float)):
                            self._OVERLAY_LARGE_LOG_SETTINGS[key] = float(val)
                    case "display_duration" | "fadeout_duration":
                        if isinstance(val, int):
                            self._OVERLAY_LARGE_LOG_SETTINGS[key] = val
                    case "opacity" | "ui_scaling":
                        if isinstance(val, (int, float)):
                            self._OVERLAY_LARGE_LOG_SETTINGS[key] = float(val)
            self.saveConfig(inspect.currentframe().f_code.co_name, self.OVERLAY_LARGE_LOG_SETTINGS)

    @property
    @json_serializable('OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES')
    def OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES(self) -> bool:
        """Whether overlays show only translated messages."""
        return self._OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES

    @OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES.setter
    def OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES(self, value: bool) -> None:
        """
        Sets whether overlays show only translated messages.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SEND_MESSAGE_TO_VRC')
    def SEND_MESSAGE_TO_VRC(self) -> bool:
        """Whether to send messages to VRChat chatbox."""
        return self._SEND_MESSAGE_TO_VRC

    @SEND_MESSAGE_TO_VRC.setter
    def SEND_MESSAGE_TO_VRC(self, value: bool) -> None:
        """
        Sets whether to send messages to VRChat chatbox.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._SEND_MESSAGE_TO_VRC = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('SEND_RECEIVED_MESSAGE_TO_VRC')
    def SEND_RECEIVED_MESSAGE_TO_VRC(self) -> bool:
        """Whether to send received (translated) messages to VRChat chatbox."""
        return self._SEND_RECEIVED_MESSAGE_TO_VRC

    @SEND_RECEIVED_MESSAGE_TO_VRC.setter
    def SEND_RECEIVED_MESSAGE_TO_VRC(self, value: bool) -> None:
        """
        Sets whether to send received messages to VRChat chatbox.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._SEND_RECEIVED_MESSAGE_TO_VRC = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('LOGGER_FEATURE')
    def LOGGER_FEATURE(self) -> bool:
        """Whether the logger feature is enabled."""
        return self._LOGGER_FEATURE

    @LOGGER_FEATURE.setter
    def LOGGER_FEATURE(self, value: bool) -> None:
        """
        Sets whether the logger feature is enabled.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._LOGGER_FEATURE = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('VRC_MIC_MUTE_SYNC')
    def VRC_MIC_MUTE_SYNC(self) -> bool:
        """Whether VRChat microphone mute status is synced."""
        return self._VRC_MIC_MUTE_SYNC

    @VRC_MIC_MUTE_SYNC.setter
    def VRC_MIC_MUTE_SYNC(self, value: bool) -> None:
        """
        Sets whether VRChat microphone mute status is synced.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._VRC_MIC_MUTE_SYNC = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('NOTIFICATION_VRC_SFX')
    def NOTIFICATION_VRC_SFX(self) -> bool:
        """Whether VRChat notification sound effects are enabled."""
        return self._NOTIFICATION_VRC_SFX

    @NOTIFICATION_VRC_SFX.setter
    def NOTIFICATION_VRC_SFX(self, value: bool) -> None:
        """
        Sets whether VRChat notification sound effects are enabled.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._NOTIFICATION_VRC_SFX = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    def WEBSOCKET_SERVER(self) -> bool:
        """Whether the WebSocket server is enabled."""
        return self._WEBSOCKET_SERVER

    @WEBSOCKET_SERVER.setter
    def WEBSOCKET_SERVER(self, value: bool) -> None:
        """
        Sets whether the WebSocket server is enabled.
        Expected type: bool.
        Saves the configuration when set.
        """
        if isinstance(value, bool):
            self._WEBSOCKET_SERVER = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value) # This was missing .f_code.co_name

    @property
    @json_serializable('WEBSOCKET_HOST')
    def WEBSOCKET_HOST(self) -> str:
        """Host address for the WebSocket server."""
        return self._WEBSOCKET_HOST

    @WEBSOCKET_HOST.setter
    def WEBSOCKET_HOST(self, value: str) -> None:
        """
        Sets the host address for the WebSocket server.
        Expected type: str.
        Saves the configuration when set.
        """
        if isinstance(value, str):
            self._WEBSOCKET_HOST = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('WEBSOCKET_PORT')
    def WEBSOCKET_PORT(self) -> int:
        """Port for the WebSocket server."""
        return self._WEBSOCKET_PORT

    @WEBSOCKET_PORT.setter
    def WEBSOCKET_PORT(self, value: int) -> None:
        """
        Sets the port for the WebSocket server.
        Expected type: int.
        Saves the configuration when set.
        """
        if isinstance(value, int):
            self._WEBSOCKET_PORT = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)


    def init_config(self) -> None:
        """Initializes all default configuration values (both read-only and read-write)."""
        # Read Only
        self._VERSION = "3.1.2"
        if getattr(sys, 'frozen', False):
            self._PATH_LOCAL = os_path.dirname(sys.executable)
        else:
            self._PATH_LOCAL = os_path.dirname(os_path.abspath(__file__))
        self._PATH_CONFIG = os_path.join(self._PATH_LOCAL, "config.json")
        self._PATH_LOGS = os_path.join(self._PATH_LOCAL, "logs")
        os_makedirs(self._PATH_LOGS, exist_ok=True)

        self._GITHUB_URL = "https://api.github.com/repos/misyaguziya/VRCT/releases/latest"
        self._UPDATER_URL = (
            "https://api.github.com/repos/misyaguziya/VRCT_updater/releases/latest"
        )
        self._BOOTH_URL = "https://misyaguziya.booth.pm/"
        self._DOCUMENTS_URL = (
            "https://mzsoftware.notion.site/VRCT-Documents-be79b7a165f64442ad8f326d86c22246"
        )
        self._DEEPL_AUTH_KEY_PAGE_URL = "https://www.deepl.com/ja/account/summary"

        self._MAX_MIC_THRESHOLD = 2000
        self._MAX_SPEAKER_THRESHOLD = 4000
        self._WATCHDOG_TIMEOUT = 60
        self._WATCHDOG_INTERVAL = 20

        self._SELECTABLE_TAB_NO_LIST = ["1", "2", "3"]
        self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST = list(ctranslate2_weights.keys())
        self._SELECTABLE_WHISPER_WEIGHT_TYPE_LIST = list(whisper_models.keys())
        self._SELECTABLE_TRANSLATION_ENGINE_LIST = list(translation_lang.keys())
        self._SELECTABLE_TRANSCRIPTION_ENGINE_LIST = list(
            transcription_lang[list(transcription_lang.keys())[0]].values()
        )[0].keys()
        self._SELECTABLE_UI_LANGUAGE_LIST = ["en", "ja", "ko", "zh-Hant", "zh-Hans"]
        self._COMPUTE_MODE = "cuda" if torch.cuda.is_available() else "cpu"
        self._SELECTABLE_COMPUTE_DEVICE_LIST = []
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                self._SELECTABLE_COMPUTE_DEVICE_LIST.append({
                    "device": "cuda",
                    "device_index": i,
                    "device_name": torch.cuda.get_device_name(i)
                })
        self._SELECTABLE_COMPUTE_DEVICE_LIST.append({
            "device": "cpu",
            "device_index": 0,
            "device_name": "cpu"
        })
        self._SEND_MESSAGE_BUTTON_TYPE_LIST = [
            "show", "hide", "show_and_disable_enter_key"
        ]
        self._SEND_MESSAGE_FORMAT = "[message]"
        self._SEND_MESSAGE_FORMAT_WITH_T = "[message]\n[translation]"
        self._RECEIVED_MESSAGE_FORMAT = "[message]"
        self._RECEIVED_MESSAGE_FORMAT_WITH_T = "[message]\n[translation]"

        # Read Write

        self._ENABLE_TRANSLATION = False
        self._ENABLE_TRANSCRIPTION_SEND = False
        self._ENABLE_TRANSCRIPTION_RECEIVE = False
        self._ENABLE_FOREGROUND = False
        self._ENABLE_CHECK_ENERGY_SEND = False
        self._ENABLE_CHECK_ENERGY_RECEIVE = False
        self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT = {}
        for weight_type in self.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST:
            self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT[weight_type] = False
        self._SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        for weight_type in self.SELECTABLE_WHISPER_WEIGHT_TYPE_LIST:
            self._SELECTABLE_WHISPER_WEIGHT_TYPE_DICT[weight_type] = False
        self._SELECTABLE_TRANSLATION_ENGINE_STATUS = {}
        for engine in self.SELECTABLE_TRANSLATION_ENGINE_LIST:
            self._SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = False
        self._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {}
        for engine in self.SELECTABLE_TRANSCRIPTION_ENGINE_LIST:
            self._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False

        # Save Json Data

        ## Main Window
        self._SELECTED_TAB_NO = "1"
        self._SELECTED_TRANSLATION_ENGINES = {}
        for tab_no in self.SELECTABLE_TAB_NO_LIST:
            self._SELECTED_TRANSLATION_ENGINES[tab_no] = "CTranslate2"
        self._SELECTED_YOUR_LANGUAGES = {}
        for tab_no in self.SELECTABLE_TAB_NO_LIST:
            self._SELECTED_YOUR_LANGUAGES[tab_no] = {
                "1": {
                    "language": "Japanese",
                    "country": "Japan",
                    "enable": True
                },
            }
        self._SELECTED_TARGET_LANGUAGES = {}
        for tab_no in self.SELECTABLE_TAB_NO_LIST:
            self._SELECTED_TARGET_LANGUAGES[tab_no] = {
                "1": {
                    "language": "English",
                    "country": "United States",
                    "enable": True
                },
                "2": {
                    "language": "English",
                    "country": "United States",
                    "enable": False
                },
                "3": {
                    "language": "English",
                    "country": "United States",
                    "enable": False
                },
            }
        self._SELECTED_TRANSCRIPTION_ENGINE = "Google"
        self._CONVERT_MESSAGE_TO_ROMAJI = False
        self._CONVERT_MESSAGE_TO_HIRAGANA = False
        self._MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False

        ## Config Window

        self._TRANSPARENCY = 100
        self._UI_SCALING = 100
        self._TEXTBOX_UI_SCALING = 100
        self._MESSAGE_BOX_RATIO = 10
        self._FONT_FAMILY = "Yu Gothic UI"
        self._UI_LANGUAGE = "en"
        self._MAIN_WINDOW_GEOMETRY = {
            "x_pos": 0,
            "y_pos": 0,
            "width": 870,
            "height": 654,
        }
        self._AUTO_MIC_SELECT = True
        self._SELECTED_MIC_HOST = device_manager.getDefaultMicDevice()["host"]["name"]
        self._SELECTED_MIC_DEVICE = device_manager.getDefaultMicDevice()["device"]["name"]
        self._MIC_THRESHOLD = 300
        self._MIC_AUTOMATIC_THRESHOLD = False
        self._MIC_RECORD_TIMEOUT = 3
        self._MIC_PHRASE_TIMEOUT = 3
        self._MIC_MAX_PHRASES = 10
        self._MIC_WORD_FILTER = []
        self._HOTKEYS = {
            "toggle_vrct_visibility": None,
            "toggle_translation": None,
            "toggle_transcription_send": None,
            "toggle_transcription_receive": None, # Trailing comma for consistency if more keys are added
        }
        self._PLUGINS_STATUS = []
        self._MIC_AVG_LOGPROB = -0.8
        self._MIC_NO_SPEECH_PROB = 0.6
        self._AUTO_SPEAKER_SELECT = True
        self._SELECTED_SPEAKER_DEVICE = device_manager.getDefaultSpeakerDevice()["device"]["name"]
        self._SPEAKER_THRESHOLD = 300
        self._SPEAKER_AUTOMATIC_THRESHOLD = False
        self._SPEAKER_RECORD_TIMEOUT = 3
        self._SPEAKER_PHRASE_TIMEOUT = 3
        self._SPEAKER_MAX_PHRASES = 10
        self._SPEAKER_AVG_LOGPROB = -0.8
        self._SPEAKER_NO_SPEECH_PROB = 0.6
        self._OSC_IP_ADDRESS = "127.0.0.1"
        self._OSC_PORT = 9000
        self._AUTH_KEYS = {
            "DeepL_API": None,
        }
        self._USE_EXCLUDE_WORDS = True
        self._SELECTED_TRANSLATION_COMPUTE_DEVICE = copy.deepcopy(
            self.SELECTABLE_COMPUTE_DEVICE_LIST[0] # Already well-formatted
        )
        self._SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = copy.deepcopy(
            self.SELECTABLE_COMPUTE_DEVICE_LIST[0]
        )
        self._CTRANSLATE2_WEIGHT_TYPE = "small"
        self._WHISPER_WEIGHT_TYPE = "base"
        self._AUTO_CLEAR_MESSAGE_BOX = True
        self._SEND_ONLY_TRANSLATED_MESSAGES = False
        self._SEND_MESSAGE_BUTTON_TYPE = "show"
        self._OVERLAY_SMALL_LOG = False
        self._OVERLAY_SMALL_LOG_SETTINGS = {
            "x_pos": 0.0,
            "y_pos": 0.0,
            "z_pos": 0.0,
            "x_rotation": 0.0,
            "y_rotation": 0.0,
            "z_rotation": 0.0,
            "display_duration": 5,
            "fadeout_duration": 2,
            "opacity": 1.0,
            "ui_scaling": 1.0,
            "tracker": "HMD",
        }
        self._OVERLAY_LARGE_LOG = False
        self._OVERLAY_LARGE_LOG_SETTINGS = {
            "x_pos": 0.0,
            "y_pos": 0.0,
            "z_pos": 0.0,
            "x_rotation": 0.0,
            "y_rotation": 0.0,
            "z_rotation": 0.0,
            "display_duration": 5,
            "fadeout_duration": 2,
            "opacity": 1.0,
            "ui_scaling": 1.0,
            "tracker": "LeftHand",
        }
        self._OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = False
        self._SEND_MESSAGE_TO_VRC = True
        self._SEND_RECEIVED_MESSAGE_TO_VRC = False
        self._LOGGER_FEATURE = False
        self._VRC_MIC_MUTE_SYNC = False
        self._NOTIFICATION_VRC_SFX = True
        self._WEBSOCKET_SERVER = False
        self._WEBSOCKET_HOST = "127.0.0.1"
        self._WEBSOCKET_PORT = 2231

    def load_config(self) -> None:
        """
        Loads configuration from `PATH_CONFIG` if it exists.

        Updates the instance's attributes with the loaded values and then
        re-saves the configuration. This ensures that any new default values
        defined in `init_config` are added to `config.json` if they were not
        present in a previously saved configuration.
        """
        if os_path.isfile(self.PATH_CONFIG) is not False:
            with open(self.PATH_CONFIG, 'r', encoding="utf-8") as fp:
                if fp.readable() and fp.seek(0, 2) > 0:
                    fp.seek(0)
                    self._config_data = json_load(fp)

                    for key, value in self._config_data.items():
                        try:
                            setattr(self, key, value)
                        except Exception:
                            errorLogging()

        with open(self.PATH_CONFIG, 'w', encoding="utf-8") as fp:
            for var_name, var_func in json_serializable_vars.items():
                self._config_data[var_name] = var_func(self)
            json_dump(self._config_data, fp, indent=4, ensure_ascii=False)


config = Config()