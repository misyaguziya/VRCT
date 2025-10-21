import sys
import copy
import inspect
from os import path as os_path, makedirs as os_makedirs
from json import load as json_load
from json import dump as json_dump
import threading
from typing import Optional, Dict, Any
import torch

# Guard optional, potentially heavy or platform-specific imports so importing
# config.py doesn't raise in environments missing those packages.
try:
    from device_manager import device_manager
except Exception:  # pragma: no cover - optional runtime
    device_manager = None  # type: ignore

try:
    from models.translation.translation_languages import translation_lang, loadTranslationLanguages
except Exception:  # pragma: no cover - optional runtime
    translation_lang = {}  # type: ignore
    def loadTranslationLanguages(path: str, force: bool = False) -> Dict[str, Any]:
        return {}

try:
    from models.translation.translation_utils import ctranslate2_weights
except Exception:  # pragma: no cover - optional runtime
    ctranslate2_weights = {}  # type: ignore

try:
    from models.transcription.transcription_languages import transcription_lang
except Exception:  # pragma: no cover - optional runtime
    transcription_lang = {}  # type: ignore

try:
    from models.transcription.transcription_whisper import _MODELS as whisper_models
except Exception:  # pragma: no cover - optional runtime
    whisper_models = {}  # type: ignore

from utils import errorLogging, validateDictStructure, getComputeDeviceList

json_serializable_vars = {}
def json_serializable(var_name):
    def decorator(func):
        json_serializable_vars[var_name] = func
        return func
    return decorator


# Descriptor for simple managed config properties to reduce repetitive getters/setters.
# It performs optional type validation, optional allowed-values check, and calls
# instance.saveConfig(...) on successful set.
class ManagedProperty:
    def __init__(self, name: str, type_: type = None, allowed=None, immediate_save: bool = False):
        self.name = name
        self.type_ = type_
        self.allowed = allowed
        self.immediate_save = immediate_save
        self.private_name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        # Type check if requested
        if self.type_ is not None and not isinstance(value, self.type_):
            return

        # Allowed-values check: can be an iterable or a callable
        if self.allowed is not None:
            if callable(self.allowed):
                try:
                    ok = self.allowed(value, instance)
                except Exception:
                    ok = False
                if not ok:
                    return
            else:
                if value not in self.allowed:
                    return

        setattr(instance, self.private_name, value)
        # Persist change
        try:
            instance.saveConfig(self.name, value, immediate_save=self.immediate_save)
        except Exception:
            # Keep setter robust during import-time initialization
            pass

class ValidatedProperty:
    """Descriptor for complex validated properties.

    validator(value, instance) -> normalized_value | None
    If returns None (or raises), value is ignored.
    """
    def __init__(self, name: str, validator, immediate_save: bool = False):
        self.name = name
        self.validator = validator
        self.immediate_save = immediate_save
        self.private_name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        try:
            normalized = self.validator(value, instance)
        except Exception:
            return
        if normalized is None:
            return
        setattr(instance, self.private_name, normalized)
        try:
            instance.saveConfig(self.name, normalized, immediate_save=self.immediate_save)
        except Exception:
            pass

class Config:
    """Application configuration singleton.

    Responsibilities:
    - expose read-only and read-write configuration via properties
    - persist selected values to JSON with debounce
    Implementation notes: initialization may depend on optional subsystems; any
    exceptions during init/load are captured and logged to avoid import-time
    crashes.
    """

    _instance = None
    _config_data: Dict[str, Any] = {}
    _timer: Optional[threading.Timer] = None
    _debounce_time: int = 2

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            try:
                cls._instance.init_config()
            except Exception:
                errorLogging()
            try:
                cls._instance.load_config()
            except Exception:
                errorLogging()
        return cls._instance

    def saveConfigToFile(self) -> None:
        with open(self.PATH_CONFIG, "w", encoding="utf-8") as fp:
            json_dump(self._config_data, fp, indent=4, ensure_ascii=False)

    def saveConfig(self, key: str, value: Any, immediate_save: bool = False) -> None:
        self._config_data[key] = value

        if isinstance(self._timer, threading.Timer) and self._timer.is_alive():
            self._timer.cancel()

        if immediate_save:
            self.saveConfigToFile()
        else:
            self._timer = threading.Timer(self._debounce_time, self.saveConfigToFile)
            self._timer.daemon = True
            self._timer.start()

    # Generic helper to validate and set complex properties.
    def _apply_validated_set(self, attr_name: str, value: Any, validator, immediate_save: bool = False):
        """Run validator(value, self) which must return a normalized value or
        raise/return None on invalid input. If valid, set private attribute
        and persist via saveConfig.
        """
        try:
            normalized = validator(value, self)
        except Exception:
            # Validation failed; keep previous value
            return

        if normalized is None:
            return

        setattr(self, f"_{attr_name}", normalized)
        try:
            self.saveConfig(attr_name, normalized, immediate_save=immediate_save)
        except Exception:
            pass

    # Read Only
    @property
    def VERSION(self):
        return self._VERSION

    @property
    def PATH_LOCAL(self):
        return self._PATH_LOCAL

    @property
    def PATH_CONFIG(self):
        return self._PATH_CONFIG

    @property
    def PATH_LOGS(self):
        return self._PATH_LOGS

    @property
    def GITHUB_URL(self):
        return self._GITHUB_URL

    @property
    def UPDATER_URL(self):
        return self._UPDATER_URL

    @property
    def BOOTH_URL(self):
        return self._BOOTH_URL

    @property
    def DOCUMENTS_URL(self):
        return self._DOCUMENTS_URL

    @property
    def DEEPL_AUTH_KEY_PAGE_URL(self):
        return self._DEEPL_AUTH_KEY_PAGE_URL

    @property
    def MAX_MIC_THRESHOLD(self):
        return self._MAX_MIC_THRESHOLD

    @property
    def MAX_SPEAKER_THRESHOLD(self):
        return self._MAX_SPEAKER_THRESHOLD

    @property
    def WATCHDOG_TIMEOUT(self):
        return self._WATCHDOG_TIMEOUT

    @property
    def WATCHDOG_INTERVAL(self):
        return self._WATCHDOG_INTERVAL

    @property
    def SELECTABLE_TAB_NO_LIST(self):
        return self._SELECTABLE_TAB_NO_LIST

    @property
    def SELECTED_TAB_TARGET_LANGUAGES_NO_LIST(self):
        return self._SELECTED_TAB_TARGET_LANGUAGES_NO_LIST

    @property
    def SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST(self):
        return self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST

    @property
    def SELECTABLE_WHISPER_WEIGHT_TYPE_LIST(self):
        return self._SELECTABLE_WHISPER_WEIGHT_TYPE_LIST

    @property
    def SELECTABLE_TRANSLATION_ENGINE_LIST(self):
        return self._SELECTABLE_TRANSLATION_ENGINE_LIST

    @property
    def SELECTABLE_TRANSCRIPTION_ENGINE_LIST(self):
        return self._SELECTABLE_TRANSCRIPTION_ENGINE_LIST

    @property
    def SELECTABLE_UI_LANGUAGE_LIST(self):
        return self._SELECTABLE_UI_LANGUAGE_LIST

    @property
    def COMPUTE_MODE(self):
        return self._COMPUTE_MODE

    @property
    def SELECTABLE_COMPUTE_DEVICE_LIST(self):
        return self._SELECTABLE_COMPUTE_DEVICE_LIST

    @property
    def SEND_MESSAGE_BUTTON_TYPE_LIST(self):
        return self._SEND_MESSAGE_BUTTON_TYPE_LIST

    # Read Write
    # --- Simple boolean flags (managed by descriptor) ---
    ENABLE_TRANSLATION = ManagedProperty('ENABLE_TRANSLATION', type_=bool)
    ENABLE_TRANSCRIPTION_SEND = ManagedProperty('ENABLE_TRANSCRIPTION_SEND', type_=bool)
    ENABLE_TRANSCRIPTION_RECEIVE = ManagedProperty('ENABLE_TRANSCRIPTION_RECEIVE', type_=bool)
    ENABLE_FOREGROUND = ManagedProperty('ENABLE_FOREGROUND', type_=bool)
    ENABLE_CHECK_ENERGY_SEND = ManagedProperty('ENABLE_CHECK_ENERGY_SEND', type_=bool)
    ENABLE_CHECK_ENERGY_RECEIVE = ManagedProperty('ENABLE_CHECK_ENERGY_RECEIVE', type_=bool)

    @property
    def SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT(self):
        return self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT

    @SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT.setter
    def SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT(self, value):
        if isinstance(value, dict):
            self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT = value

    @property
    def SELECTABLE_WHISPER_WEIGHT_TYPE_DICT(self):
        return self._SELECTABLE_WHISPER_WEIGHT_TYPE_DICT

    @SELECTABLE_WHISPER_WEIGHT_TYPE_DICT.setter
    def SELECTABLE_WHISPER_WEIGHT_TYPE_DICT(self, value):
        if isinstance(value, dict):
            self._SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = value

    @property
    def SELECTABLE_TRANSLATION_ENGINE_STATUS(self):
        return self._SELECTABLE_TRANSLATION_ENGINE_STATUS

    @SELECTABLE_TRANSLATION_ENGINE_STATUS.setter
    def SELECTABLE_TRANSLATION_ENGINE_STATUS(self, value):
        if isinstance(value, dict):
            self._SELECTABLE_TRANSLATION_ENGINE_STATUS = value

    @property
    def SELECTABLE_TRANSCRIPTION_ENGINE_STATUS(self):
        return self._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS

    @SELECTABLE_TRANSCRIPTION_ENGINE_STATUS.setter
    def SELECTABLE_TRANSCRIPTION_ENGINE_STATUS(self, value):
        if isinstance(value, dict):
            self._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = value

    @property
    def SELECTABLE_PLAMO_MODEL_LIST(self):
        return self._SELECTABLE_PLAMO_MODEL_LIST

    @SELECTABLE_PLAMO_MODEL_LIST.setter
    def SELECTABLE_PLAMO_MODEL_LIST(self, value):
        if isinstance(value, list):
            self._SELECTABLE_PLAMO_MODEL_LIST = value

    @property
    def SELECTABLE_GEMINI_MODEL_LIST(self):
        return self._SELECTABLE_GEMINI_MODEL_LIST

    @SELECTABLE_GEMINI_MODEL_LIST.setter
    def SELECTABLE_GEMINI_MODEL_LIST(self, value):
        if isinstance(value, list):
            self._SELECTABLE_GEMINI_MODEL_LIST = value

    @property
    def SELECTABLE_OPENAI_MODEL_LIST(self):
        return self._SELECTABLE_OPENAI_MODEL_LIST

    @SELECTABLE_OPENAI_MODEL_LIST.setter
    def SELECTABLE_OPENAI_MODEL_LIST(self, value):
        if isinstance(value, list):
            self._SELECTABLE_OPENAI_MODEL_LIST = value

    @property
    def SELECTABLE_LMSTUDIO_MODEL_LIST(self):
        return self._SELECTABLE_LMSTUDIO_MODEL_LIST

    @SELECTABLE_LMSTUDIO_MODEL_LIST.setter
    def SELECTABLE_LMSTUDIO_MODEL_LIST(self, value):
        if isinstance(value, list):
            self._SELECTABLE_LMSTUDIO_MODEL_LIST = value

    @property
    def SELECTABLE_OLLAMA_MODEL_LIST(self):
        return self._SELECTABLE_OLLAMA_MODEL_LIST

    @SELECTABLE_OLLAMA_MODEL_LIST.setter
    def SELECTABLE_OLLAMA_MODEL_LIST(self, value):
        if isinstance(value, list):
            self._SELECTABLE_OLLAMA_MODEL_LIST = value

    # --- Save Json Data (ManagedProperty-based) ---
    # More simple boolean flags replaced with ManagedProperty
    CONVERT_MESSAGE_TO_ROMAJI = ManagedProperty('CONVERT_MESSAGE_TO_ROMAJI', type_=bool)
    CONVERT_MESSAGE_TO_HIRAGANA = ManagedProperty('CONVERT_MESSAGE_TO_HIRAGANA', type_=bool)
    MAIN_WINDOW_SIDEBAR_COMPACT_MODE = ManagedProperty('MAIN_WINDOW_SIDEBAR_COMPACT_MODE', type_=bool)

    ## Config Window
    TRANSPARENCY = ManagedProperty('TRANSPARENCY', type_=int)
    UI_SCALING = ManagedProperty('UI_SCALING', type_=int)
    TEXTBOX_UI_SCALING = ManagedProperty('TEXTBOX_UI_SCALING', type_=int)
    MESSAGE_BOX_RATIO = ManagedProperty('MESSAGE_BOX_RATIO', type_=(int, float), immediate_save=True)
    SEND_MESSAGE_BUTTON_TYPE = ManagedProperty('SEND_MESSAGE_BUTTON_TYPE', type_=str, allowed=lambda v, inst: v in inst.SEND_MESSAGE_BUTTON_TYPE_LIST)
    SHOW_RESEND_BUTTON = ManagedProperty('SHOW_RESEND_BUTTON', type_=bool)
    FONT_FAMILY = ManagedProperty('FONT_FAMILY', type_=str)
    UI_LANGUAGE = ManagedProperty('UI_LANGUAGE', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_UI_LANGUAGE_LIST)

    # Register json serializable functions for the ManagedProperty-backed attributes
    @json_serializable('TRANSPARENCY')
    def _json_TRANSPARENCY(self):
        return self.TRANSPARENCY

    @json_serializable('UI_SCALING')
    def _json_UI_SCALING(self):
        return self.UI_SCALING

    @json_serializable('TEXTBOX_UI_SCALING')
    def _json_TEXTBOX_UI_SCALING(self):
        return self.TEXTBOX_UI_SCALING

    @json_serializable('MESSAGE_BOX_RATIO')
    def _json_MESSAGE_BOX_RATIO(self):
        return self.MESSAGE_BOX_RATIO

    @json_serializable('SEND_MESSAGE_BUTTON_TYPE')
    def _json_SEND_MESSAGE_BUTTON_TYPE(self):
        return self.SEND_MESSAGE_BUTTON_TYPE

    @json_serializable('SHOW_RESEND_BUTTON')
    def _json_SHOW_RESEND_BUTTON(self):
        return self.SHOW_RESEND_BUTTON

    @json_serializable('FONT_FAMILY')
    def _json_FONT_FAMILY(self):
        return self.FONT_FAMILY

    @json_serializable('UI_LANGUAGE')
    def _json_UI_LANGUAGE(self):
        return self.UI_LANGUAGE

    # Register json serializable functions for mic/speaker and other simple props
    @json_serializable('CONVERT_MESSAGE_TO_ROMAJI')
    def _json_CONVERT_MESSAGE_TO_ROMAJI(self):
        return self.CONVERT_MESSAGE_TO_ROMAJI

    @json_serializable('CONVERT_MESSAGE_TO_HIRAGANA')
    def _json_CONVERT_MESSAGE_TO_HIRAGANA(self):
        return self.CONVERT_MESSAGE_TO_HIRAGANA

    @json_serializable('MAIN_WINDOW_SIDEBAR_COMPACT_MODE')
    def _json_MAIN_WINDOW_SIDEBAR_COMPACT_MODE(self):
        return self.MAIN_WINDOW_SIDEBAR_COMPACT_MODE

    @json_serializable('MIC_THRESHOLD')
    def _json_MIC_THRESHOLD(self):
        return self.MIC_THRESHOLD

    @json_serializable('MIC_AUTOMATIC_THRESHOLD')
    def _json_MIC_AUTOMATIC_THRESHOLD(self):
        return self.MIC_AUTOMATIC_THRESHOLD

    @json_serializable('MIC_RECORD_TIMEOUT')
    def _json_MIC_RECORD_TIMEOUT(self):
        return self.MIC_RECORD_TIMEOUT

    @json_serializable('MIC_PHRASE_TIMEOUT')
    def _json_MIC_PHRASE_TIMEOUT(self):
        return self.MIC_PHRASE_TIMEOUT

    @json_serializable('MIC_MAX_PHRASES')
    def _json_MIC_MAX_PHRASES(self):
        return self.MIC_MAX_PHRASES

    @json_serializable('SPEAKER_THRESHOLD')
    def _json_SPEAKER_THRESHOLD(self):
        return self.SPEAKER_THRESHOLD

    @json_serializable('SPEAKER_AUTOMATIC_THRESHOLD')
    def _json_SPEAKER_AUTOMATIC_THRESHOLD(self):
        return self.SPEAKER_AUTOMATIC_THRESHOLD

    @json_serializable('SPEAKER_RECORD_TIMEOUT')
    def _json_SPEAKER_RECORD_TIMEOUT(self):
        return self.SPEAKER_RECORD_TIMEOUT

    @json_serializable('SPEAKER_PHRASE_TIMEOUT')
    def _json_SPEAKER_PHRASE_TIMEOUT(self):
        return self.SPEAKER_PHRASE_TIMEOUT

    @json_serializable('SPEAKER_MAX_PHRASES')
    def _json_SPEAKER_MAX_PHRASES(self):
        return self.SPEAKER_MAX_PHRASES

    @json_serializable('SPEAKER_AVG_LOGPROB')
    def _json_SPEAKER_AVG_LOGPROB(self):
        return self.SPEAKER_AVG_LOGPROB

    @json_serializable('SPEAKER_NO_SPEECH_PROB')
    def _json_SPEAKER_NO_SPEECH_PROB(self):
        return self.SPEAKER_NO_SPEECH_PROB

    @property
    @json_serializable('MAIN_WINDOW_GEOMETRY')
    def MAIN_WINDOW_GEOMETRY(self):
        return self._MAIN_WINDOW_GEOMETRY

    @MAIN_WINDOW_GEOMETRY.setter
    def MAIN_WINDOW_GEOMETRY(self, value):
        if isinstance(value, dict) and set(value.keys()) == set(self.MAIN_WINDOW_GEOMETRY.keys()):
            for key, value in value.items():
                if isinstance(value, int):
                    self._MAIN_WINDOW_GEOMETRY[key] = value
            self.saveConfig(inspect.currentframe().f_code.co_name, self.MAIN_WINDOW_GEOMETRY, immediate_save=True)

    # --- Mic-related simple properties ---
    MIC_THRESHOLD = ManagedProperty('MIC_THRESHOLD', type_=int)
    MIC_AUTOMATIC_THRESHOLD = ManagedProperty('MIC_AUTOMATIC_THRESHOLD', type_=bool)
    MIC_RECORD_TIMEOUT = ManagedProperty('MIC_RECORD_TIMEOUT', type_=int)
    MIC_PHRASE_TIMEOUT = ManagedProperty('MIC_PHRASE_TIMEOUT', type_=int)
    MIC_MAX_PHRASES = ManagedProperty('MIC_MAX_PHRASES', type_=int)
    MIC_AVG_LOGPROB = ManagedProperty('MIC_AVG_LOGPROB', type_=(int, float))
    MIC_NO_SPEECH_PROB = ManagedProperty('MIC_NO_SPEECH_PROB', type_=(int, float))

    # HOTKEYS validator: dict with identical key set; each value either list or None
    HOTKEYS = ValidatedProperty('HOTKEYS',
        validator=lambda val, inst: (
            {k: (v if (isinstance(v, list) or v is None) else inst.HOTKEYS.get(k))
            for k, v in val.items()} if isinstance(val, dict) and set(val.keys()) == set(inst.HOTKEYS.keys()) else None
        ),
        immediate_save=True
    )

    # --- Speaker-related simple properties (handled by ManagedProperty) ---
    SPEAKER_THRESHOLD = ManagedProperty('SPEAKER_THRESHOLD', type_=int)
    SPEAKER_AUTOMATIC_THRESHOLD = ManagedProperty('SPEAKER_AUTOMATIC_THRESHOLD', type_=bool)
    SPEAKER_RECORD_TIMEOUT = ManagedProperty('SPEAKER_RECORD_TIMEOUT', type_=int)
    SPEAKER_PHRASE_TIMEOUT = ManagedProperty('SPEAKER_PHRASE_TIMEOUT', type_=int)
    SPEAKER_MAX_PHRASES = ManagedProperty('SPEAKER_MAX_PHRASES', type_=int)
    SPEAKER_AVG_LOGPROB = ManagedProperty('SPEAKER_AVG_LOGPROB', type_=(int, float))
    SPEAKER_NO_SPEECH_PROB = ManagedProperty('SPEAKER_NO_SPEECH_PROB', type_=(int, float))

    # --- Auth settings ---
    # AUTH_KEYS with custom validator
    AUTH_KEYS = ValidatedProperty('AUTH_KEYS',
        validator=lambda val, inst: (
            {k: (v if isinstance(v, str) else inst.AUTH_KEYS.get(k)) for k, v in val.items()}
            if isinstance(val, dict) and set(val.keys()) == set(inst.AUTH_KEYS.keys()) else None
        )
    )

    @property
    @json_serializable('SELECTED_TRANSCRIPTION_COMPUTE_TYPE')
    def SELECTED_TRANSCRIPTION_COMPUTE_TYPE(self):
        return self._SELECTED_TRANSCRIPTION_COMPUTE_TYPE

    @SELECTED_TRANSCRIPTION_COMPUTE_TYPE.setter
    def SELECTED_TRANSCRIPTION_COMPUTE_TYPE(self, value):
        if isinstance(value, str):
            if value in self.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["compute_types"]:
                self._SELECTED_TRANSCRIPTION_COMPUTE_TYPE = value
                self.saveConfig(inspect.currentframe().f_code.co_name, value)

    @property
    @json_serializable('LMSTUDIO_URL')
    def LMSTUDIO_URL(self):
        return self._LMSTUDIO_URL

    @LMSTUDIO_URL.setter
    def LMSTUDIO_URL(self, value):
        if isinstance(value, str):
            self._LMSTUDIO_URL = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)

    # --- OVERLAY settings validators ---
    def _overlay_small_validator(val, inst):
        if not (isinstance(val, dict) and set(val.keys()) == set(inst.OVERLAY_SMALL_LOG_SETTINGS.keys())):
            return None
        base = inst.OVERLAY_SMALL_LOG_SETTINGS
        new = dict(base)  # start from existing
        for key, v in val.items():
            if key == 'tracker' and isinstance(v, str) and v in ['HMD', 'LeftHand', 'RightHand']:
                new[key] = v
            elif key in ['x_pos','y_pos','z_pos','x_rotation','y_rotation','z_rotation'] and isinstance(v,(int,float)):
                new[key] = float(v)
            elif key in ['display_duration','fadeout_duration'] and isinstance(v,int):
                new[key] = v
            elif key in ['opacity','ui_scaling'] and isinstance(v,(int,float)):
                new[key] = float(v)
        return new
    OVERLAY_SMALL_LOG_SETTINGS = ValidatedProperty('OVERLAY_SMALL_LOG_SETTINGS', _overlay_small_validator)

    def _overlay_large_validator(val, inst):
        if not (isinstance(val, dict) and set(val.keys()) == set(inst.OVERLAY_LARGE_LOG_SETTINGS.keys())):
            return None
        base = inst.OVERLAY_LARGE_LOG_SETTINGS
        new = dict(base)
        for key, v in val.items():
            if key == 'tracker' and isinstance(v, str) and v in ['HMD', 'LeftHand', 'RightHand']:
                new[key] = v
            elif key in ['x_pos','y_pos','z_pos','x_rotation','y_rotation','z_rotation'] and isinstance(v,(int,float)):
                new[key] = float(v)
            elif key in ['display_duration','fadeout_duration'] and isinstance(v,int):
                new[key] = v
            elif key in ['opacity','ui_scaling'] and isinstance(v,(int,float)):
                new[key] = float(v)
        return new
    OVERLAY_LARGE_LOG_SETTINGS = ValidatedProperty('OVERLAY_LARGE_LOG_SETTINGS', _overlay_large_validator)

    def _format_validator_send(val, inst):
        valid_parts = {
            "message": {"prefix": str, "suffix": str},
            "separator": str,
            "translation": {"prefix": str, "separator": str, "suffix": str},
            "translation_first": bool
        }
        if not isinstance(val, dict):
            return None
        return val if validateDictStructure(val, valid_parts) else None
    SEND_MESSAGE_FORMAT_PARTS = ValidatedProperty('SEND_MESSAGE_FORMAT_PARTS', _format_validator_send)

    def _format_validator_received(val, inst):
        valid_parts = {
            "message": {"prefix": str, "suffix": str},
            "separator": str,
            "translation": {"prefix": str, "separator": str, "suffix": str},
            "translation_first": bool
        }
        if not isinstance(val, dict):
            return None
        return val if validateDictStructure(val, valid_parts) else None
    RECEIVED_MESSAGE_FORMAT_PARTS = ValidatedProperty('RECEIVED_MESSAGE_FORMAT_PARTS', _format_validator_received)

    # Convert remaining simple properties to ManagedProperty to reduce repetition
    WEBSOCKET_SERVER = ManagedProperty('WEBSOCKET_SERVER', type_=bool)
    OSC_IP_ADDRESS = ManagedProperty('OSC_IP_ADDRESS', type_=str)
    OSC_PORT = ManagedProperty('OSC_PORT', type_=int)
    AUTO_CLEAR_MESSAGE_BOX = ManagedProperty('AUTO_CLEAR_MESSAGE_BOX', type_=bool)
    SEND_ONLY_TRANSLATED_MESSAGES = ManagedProperty('SEND_ONLY_TRANSLATED_MESSAGES', type_=bool)
    OVERLAY_SMALL_LOG = ManagedProperty('OVERLAY_SMALL_LOG', type_=bool)
    OVERLAY_LARGE_LOG = ManagedProperty('OVERLAY_LARGE_LOG', type_=bool)
    OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = ManagedProperty('OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES', type_=bool)
    SEND_MESSAGE_TO_VRC = ManagedProperty('SEND_MESSAGE_TO_VRC', type_=bool)
    SEND_RECEIVED_MESSAGE_TO_VRC = ManagedProperty('SEND_RECEIVED_MESSAGE_TO_VRC', type_=bool)
    LOGGER_FEATURE = ManagedProperty('LOGGER_FEATURE', type_=bool)
    VRC_MIC_MUTE_SYNC = ManagedProperty('VRC_MIC_MUTE_SYNC', type_=bool)
    NOTIFICATION_VRC_SFX = ManagedProperty('NOTIFICATION_VRC_SFX', type_=bool)
    WEBSOCKET_HOST = ManagedProperty('WEBSOCKET_HOST', type_=str)
    WEBSOCKET_PORT = ManagedProperty('WEBSOCKET_PORT', type_=int)

    # --- Selection properties with validation (ManagedProperty) ---
    SELECTED_TAB_NO = ManagedProperty('SELECTED_TAB_NO', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_TAB_NO_LIST)
    SELECTED_TRANSCRIPTION_ENGINE = ManagedProperty('SELECTED_TRANSCRIPTION_ENGINE', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_TRANSCRIPTION_ENGINE_LIST)
    USE_EXCLUDE_WORDS = ManagedProperty('USE_EXCLUDE_WORDS', type_=bool)
    CTRANSLATE2_WEIGHT_TYPE = ManagedProperty('CTRANSLATE2_WEIGHT_TYPE', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST)
    WHISPER_WEIGHT_TYPE = ManagedProperty('WHISPER_WEIGHT_TYPE', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_WHISPER_WEIGHT_TYPE_LIST)
    SELECTED_PLAMO_MODEL = ManagedProperty('SELECTED_PLAMO_MODEL', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_PLAMO_MODEL_LIST)
    SELECTED_GEMINI_MODEL = ManagedProperty('SELECTED_GEMINI_MODEL', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_GEMINI_MODEL_LIST)
    SELECTED_OPENAI_MODEL = ManagedProperty('SELECTED_OPENAI_MODEL', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_OPENAI_MODEL_LIST)
    SELECTED_LMSTUDIO_MODEL = ManagedProperty('SELECTED_LMSTUDIO_MODEL', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_LMSTUDIO_MODEL_LIST)
    SELECTED_OLLAMA_MODEL = ManagedProperty('SELECTED_OLLAMA_MODEL', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_OLLAMA_MODEL_LIST)

    # --- Complex properties with custom validators (ValidatedProperty) ---
    # List/Dict validators
    def _mic_word_filter_validator(val, inst):
        if not isinstance(val, list):
            return None
        seen = set()
        result = []
        for item in val:
            if isinstance(item, str) and item not in seen:
                seen.add(item)
                result.append(item)
        return result
    MIC_WORD_FILTER = ValidatedProperty('MIC_WORD_FILTER', _mic_word_filter_validator)

    def _plugins_status_validator(val, inst):
        if not isinstance(val, list):
            return None
        if not all(isinstance(item, dict) for item in val):
            return None
        return [dict(item) for item in val]
    PLUGINS_STATUS = ValidatedProperty('PLUGINS_STATUS', _plugins_status_validator, immediate_save=True)

    def _selected_translation_engines_validator(val, inst):
        if not isinstance(val, dict):
            return None
        old_value = inst.SELECTED_TRANSLATION_ENGINES
        new = {}
        for k, v in val.items():
            if v in inst.SELECTABLE_TRANSLATION_ENGINE_LIST:
                new[k] = v
            else:
                new[k] = old_value.get(k)
        return new
    SELECTED_TRANSLATION_ENGINES = ValidatedProperty('SELECTED_TRANSLATION_ENGINES', _selected_translation_engines_validator)

    def _selected_your_languages_validator(val, inst):
        if not isinstance(val, dict):
            return None
        old = inst.SELECTED_YOUR_LANGUAGES
        new = {}
        for k0, v0 in val.items():
            new[k0] = {}
            for k1, v1 in v0.items():
                language = v1.get("language")
                country = v1.get("country")
                enable = v1.get("enable")
                if (language not in list(transcription_lang.keys()) or
                    country not in list(transcription_lang.get(language, {}).keys()) or
                    not isinstance(enable, bool)):
                    new[k0][k1] = old.get(k0, {}).get(k1)
                else:
                    new[k0][k1] = {"language": language, "country": country, "enable": enable}
        return new
    SELECTED_YOUR_LANGUAGES = ValidatedProperty('SELECTED_YOUR_LANGUAGES', _selected_your_languages_validator)

    def _selected_target_languages_validator(val, inst):
        if not isinstance(val, dict):
            return None
        old = inst.SELECTED_TARGET_LANGUAGES
        new = {}
        for k0, v0 in val.items():
            new[k0] = {}
            for k1, v1 in v0.items():
                language = v1.get("language")
                country = v1.get("country")
                enable = v1.get("enable")
                if (language not in list(transcription_lang.keys()) or
                    country not in list(transcription_lang.get(language, {}).keys()) or
                    not isinstance(enable, bool)):
                    new[k0][k1] = old.get(k0, {}).get(k1)
                else:
                    new[k0][k1] = {"language": language, "country": country, "enable": enable}
        return new
    SELECTED_TARGET_LANGUAGES = ValidatedProperty('SELECTED_TARGET_LANGUAGES', _selected_target_languages_validator)

    def _selected_translation_compute_type_validator(val, inst):
        if not isinstance(val, str):
            return None
        compute_types = inst.SELECTED_TRANSLATION_COMPUTE_DEVICE.get("compute_types", [])
        if val in compute_types:
            return val
        return None
    SELECTED_TRANSLATION_COMPUTE_TYPE = ValidatedProperty('SELECTED_TRANSLATION_COMPUTE_TYPE', _selected_translation_compute_type_validator)

    # Serialization functions for new descriptors
    @json_serializable('SELECTED_TAB_NO')
    def _json_SELECTED_TAB_NO(self):
        return self.SELECTED_TAB_NO
    @json_serializable('SELECTED_TRANSCRIPTION_ENGINE')
    def _json_SELECTED_TRANSCRIPTION_ENGINE(self):
        return self.SELECTED_TRANSCRIPTION_ENGINE
    @json_serializable('USE_EXCLUDE_WORDS')
    def _json_USE_EXCLUDE_WORDS(self):
        return self.USE_EXCLUDE_WORDS
    @json_serializable('CTRANSLATE2_WEIGHT_TYPE')
    def _json_CTRANSLATE2_WEIGHT_TYPE(self):
        return self.CTRANSLATE2_WEIGHT_TYPE
    @json_serializable('WHISPER_WEIGHT_TYPE')
    def _json_WHISPER_WEIGHT_TYPE(self):
        return self.WHISPER_WEIGHT_TYPE
    @json_serializable('SELECTED_PLAMO_MODEL')
    def _json_SELECTED_PLAMO_MODEL(self):
        return self.SELECTED_PLAMO_MODEL
    @json_serializable('SELECTED_GEMINI_MODEL')
    def _json_SELECTED_GEMINI_MODEL(self):
        return self.SELECTED_GEMINI_MODEL
    @json_serializable('SELECTED_OPENAI_MODEL')
    def _json_SELECTED_OPENAI_MODEL(self):
        return self.SELECTED_OPENAI_MODEL
    @json_serializable('SELECTED_LMSTUDIO_MODEL')
    def _json_SELECTED_LMSTUDIO_MODEL(self):
        return self.SELECTED_LMSTUDIO_MODEL
    @json_serializable('SELECTED_OLLAMA_MODEL')
    def _json_SELECTED_OLLAMA_MODEL(self):
        return self.SELECTED_OLLAMA_MODEL
    @json_serializable('MIC_WORD_FILTER')
    def _json_MIC_WORD_FILTER(self):
        return self.MIC_WORD_FILTER
    @json_serializable('PLUGINS_STATUS')
    def _json_PLUGINS_STATUS(self):
        return self.PLUGINS_STATUS
    @json_serializable('SELECTED_TRANSLATION_ENGINES')
    def _json_SELECTED_TRANSLATION_ENGINES(self):
        return self.SELECTED_TRANSLATION_ENGINES
    @json_serializable('SELECTED_YOUR_LANGUAGES')
    def _json_SELECTED_YOUR_LANGUAGES(self):
        return self.SELECTED_YOUR_LANGUAGES
    @json_serializable('SELECTED_TARGET_LANGUAGES')
    def _json_SELECTED_TARGET_LANGUAGES(self):
        return self.SELECTED_TARGET_LANGUAGES
    @json_serializable('SELECTED_TRANSLATION_COMPUTE_TYPE')
    def _json_SELECTED_TRANSLATION_COMPUTE_TYPE(self):
        return self.SELECTED_TRANSLATION_COMPUTE_TYPE

    # --- Device related descriptors & validators ---
    # AUTO_MIC_SELECT simple boolean
    AUTO_MIC_SELECT = ManagedProperty('AUTO_MIC_SELECT', type_=bool)

    def _mic_host_validator(val, inst):
        if device_manager is None:
            return None
        if not isinstance(val, str):
            return None
        hosts = list(device_manager.getMicDevices().keys())
        return val if val in hosts else None
    SELECTED_MIC_HOST = ValidatedProperty('SELECTED_MIC_HOST', _mic_host_validator)

    def _mic_device_validator(val, inst):
        if device_manager is None:
            return None
        if not isinstance(val, str):
            return None
        try:
            devices = device_manager.getMicDevices().get(inst.SELECTED_MIC_HOST, [])
            names = [d.get('name') for d in devices]
            return val if val in names else None
        except Exception:
            return None
    SELECTED_MIC_DEVICE = ValidatedProperty('SELECTED_MIC_DEVICE', _mic_device_validator)

    def _speaker_device_validator(val, inst):
        if device_manager is None:
            return None
        if not isinstance(val, str):
            return None
        try:
            names = [d.get('name') for d in device_manager.getSpeakerDevices()]
            return val if val in names else None
        except Exception:
            return None
    SELECTED_SPEAKER_DEVICE = ValidatedProperty('SELECTED_SPEAKER_DEVICE', _speaker_device_validator)

    def _compute_device_validator(val, inst):
        # Each compute device is a dict; must be exactly one of selectable list entries
        if not isinstance(val, dict):
            return None
        for dev in inst.SELECTABLE_COMPUTE_DEVICE_LIST:
            if dev == val:
                return copy.deepcopy(val)
        return None
    SELECTED_TRANSLATION_COMPUTE_DEVICE = ValidatedProperty('SELECTED_TRANSLATION_COMPUTE_DEVICE', _compute_device_validator)
    SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = ValidatedProperty('SELECTED_TRANSCRIPTION_COMPUTE_DEVICE', _compute_device_validator)

    # JSON serialization helpers for new descriptors
    @json_serializable('AUTO_MIC_SELECT')
    def _json_AUTO_MIC_SELECT(self):
        return self.AUTO_MIC_SELECT

    @json_serializable('SELECTED_MIC_HOST')
    def _json_SELECTED_MIC_HOST(self):
        return self.SELECTED_MIC_HOST

    @json_serializable('SELECTED_MIC_DEVICE')
    def _json_SELECTED_MIC_DEVICE(self):
        return self.SELECTED_MIC_DEVICE

    @json_serializable('SELECTED_SPEAKER_DEVICE')
    def _json_SELECTED_SPEAKER_DEVICE(self):
        return self.SELECTED_SPEAKER_DEVICE

    @json_serializable('SELECTED_TRANSLATION_COMPUTE_DEVICE')
    def _json_SELECTED_TRANSLATION_COMPUTE_DEVICE(self):
        return self.SELECTED_TRANSLATION_COMPUTE_DEVICE

    @json_serializable('SELECTED_TRANSCRIPTION_COMPUTE_DEVICE')
    def _json_SELECTED_TRANSCRIPTION_COMPUTE_DEVICE(self):
        return self.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE

    # Register json serializable functions for the above
    @json_serializable('WEBSOCKET_SERVER')
    def _json_WEBSOCKET_SERVER(self):
        return self.WEBSOCKET_SERVER

    @json_serializable('OSC_IP_ADDRESS')
    def _json_OSC_IP_ADDRESS(self):
        return self.OSC_IP_ADDRESS

    @json_serializable('OSC_PORT')
    def _json_OSC_PORT(self):
        return self.OSC_PORT

    @json_serializable('AUTO_CLEAR_MESSAGE_BOX')
    def _json_AUTO_CLEAR_MESSAGE_BOX(self):
        return self.AUTO_CLEAR_MESSAGE_BOX

    @json_serializable('SEND_ONLY_TRANSLATED_MESSAGES')
    def _json_SEND_ONLY_TRANSLATED_MESSAGES(self):
        return self.SEND_ONLY_TRANSLATED_MESSAGES

    @json_serializable('OVERLAY_SMALL_LOG')
    def _json_OVERLAY_SMALL_LOG(self):
        return self.OVERLAY_SMALL_LOG

    @json_serializable('OVERLAY_LARGE_LOG')
    def _json_OVERLAY_LARGE_LOG(self):
        return self.OVERLAY_LARGE_LOG

    @json_serializable('OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES')
    def _json_OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES(self):
        return self.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES

    @json_serializable('SEND_MESSAGE_TO_VRC')
    def _json_SEND_MESSAGE_TO_VRC(self):
        return self.SEND_MESSAGE_TO_VRC

    @json_serializable('SEND_RECEIVED_MESSAGE_TO_VRC')
    def _json_SEND_RECEIVED_MESSAGE_TO_VRC(self):
        return self.SEND_RECEIVED_MESSAGE_TO_VRC

    @json_serializable('LOGGER_FEATURE')
    def _json_LOGGER_FEATURE(self):
        return self.LOGGER_FEATURE

    @json_serializable('VRC_MIC_MUTE_SYNC')
    def _json_VRC_MIC_MUTE_SYNC(self):
        return self.VRC_MIC_MUTE_SYNC

    @json_serializable('NOTIFICATION_VRC_SFX')
    def _json_NOTIFICATION_VRC_SFX(self):
        return self.NOTIFICATION_VRC_SFX

    @json_serializable('WEBSOCKET_HOST')
    def _json_WEBSOCKET_HOST(self):
        return self.WEBSOCKET_HOST

    @json_serializable('WEBSOCKET_PORT')
    def _json_WEBSOCKET_PORT(self):
        return self.WEBSOCKET_PORT

    def init_config(self):
        # Read Only
        self._VERSION = "3.3.1"
        if getattr(sys, 'frozen', False):
            self._PATH_LOCAL = os_path.dirname(sys.executable)
        else:
            self._PATH_LOCAL = os_path.dirname(os_path.abspath(__file__))
        self._PATH_CONFIG = os_path.join(self._PATH_LOCAL, "config.json")
        self._PATH_LOGS = os_path.join(self._PATH_LOCAL, "logs")
        os_makedirs(self._PATH_LOGS, exist_ok=True)
        self._GITHUB_URL = "https://api.github.com/repos/misyaguziya/VRCT/releases/latest"
        self._UPDATER_URL = "https://api.github.com/repos/misyaguziya/VRCT_updater/releases/latest"
        self._BOOTH_URL = "https://misyaguziya.booth.pm/"
        self._DOCUMENTS_URL = "https://mzsoftware.notion.site/VRCT-Documents-be79b7a165f64442ad8f326d86c22246"
        self._DEEPL_AUTH_KEY_PAGE_URL = "https://www.deepl.com/ja/account/summary"

        self._MAX_MIC_THRESHOLD = 2000
        self._MAX_SPEAKER_THRESHOLD = 4000
        self._WATCHDOG_TIMEOUT = 60
        self._WATCHDOG_INTERVAL = 20

        self._SELECTABLE_TAB_NO_LIST = ["1", "2", "3"]
        # these external mappings may be empty dicts if the optional modules failed to import
        self._SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST = getattr(ctranslate2_weights, 'keys', lambda: [])()
        self._SELECTABLE_WHISPER_WEIGHT_TYPE_LIST = getattr(whisper_models, 'keys', lambda: [])()
        translation_lang = loadTranslationLanguages(self.PATH_LOCAL)
        self._SELECTABLE_TRANSLATION_ENGINE_LIST = getattr(translation_lang, 'keys', lambda: [])()
        try:
            # transcription_lang is nested dict; attempt to extract keys defensively
            first_key = next(iter(transcription_lang))
            self._SELECTABLE_TRANSCRIPTION_ENGINE_LIST = list(transcription_lang[first_key].values())[0].keys()
        except Exception:
            self._SELECTABLE_TRANSCRIPTION_ENGINE_LIST = []
        self._SELECTABLE_UI_LANGUAGE_LIST = ["en", "ja", "ko", "zh-Hant", "zh-Hans"]
        self._COMPUTE_MODE = "cuda" if torch.cuda.is_available() else "cpu"
        self._SELECTABLE_COMPUTE_DEVICE_LIST = getComputeDeviceList()
        self._SEND_MESSAGE_BUTTON_TYPE_LIST = ["show", "hide", "show_and_disable_enter_key"]

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
        self._SELECTABLE_PLAMO_MODEL_LIST = []
        self._SELECTABLE_GEMINI_MODEL_LIST = []
        self._SELECTABLE_OPENAI_MODEL_LIST = []
        self._SELECTABLE_LMSTUDIO_MODEL_LIST = []
        self._SELECTABLE_OLLAMA_MODEL_LIST = []

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
                    "enable": True,
                },
            }
        self._SELECTED_TARGET_LANGUAGES = {}
        self._SELECTED_TAB_TARGET_LANGUAGES_NO_LIST = ["1", "2", "3"]
        for tab_no in self.SELECTABLE_TAB_NO_LIST:
            for tab_target_lang_no in self.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST:
                if tab_no not in self.SELECTED_TARGET_LANGUAGES:
                    self._SELECTED_TARGET_LANGUAGES[tab_no] = {}
                if tab_target_lang_no not in self.SELECTED_TARGET_LANGUAGES[tab_no]:
                    self._SELECTED_TARGET_LANGUAGES[tab_no][tab_target_lang_no] = {
                        "language": "English",
                        "country": "United States",
                        "enable": True if tab_target_lang_no == self.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST[0] else False,
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
        self._SEND_MESSAGE_BUTTON_TYPE = "show"
        self._SHOW_RESEND_BUTTON = False
        self._FONT_FAMILY = "Yu Gothic UI"
        self._UI_LANGUAGE = "en"
        self._MAIN_WINDOW_GEOMETRY = {
            "x_pos": 0,
            "y_pos": 0,
            "width": 870,
            "height": 654,
        }
        self._AUTO_MIC_SELECT = True
        # device_manager may be unavailable or not initialized; use safe defaults
        try:
            if device_manager is not None:
                # getDefaultMicDevice performs lazy init/update if needed
                dm_def = device_manager.getDefaultMicDevice()
                self._SELECTED_MIC_HOST = dm_def.get("host", {}).get("name", "NoHost")
                self._SELECTED_MIC_DEVICE = dm_def.get("device", {}).get("name", "NoDevice")
            else:
                self._SELECTED_MIC_HOST = "NoHost"
                self._SELECTED_MIC_DEVICE = "NoDevice"
        except Exception:
            errorLogging()
            self._SELECTED_MIC_HOST = "NoHost"
            self._SELECTED_MIC_DEVICE = "NoDevice"
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
            "toggle_transcription_receive": None,
        }
        self._PLUGINS_STATUS = []
        self._MIC_AVG_LOGPROB = -0.8
        self._MIC_NO_SPEECH_PROB = 0.6
        self._AUTO_SPEAKER_SELECT = True
        try:
            if device_manager is not None:
                sp_def = device_manager.getDefaultSpeakerDevice()
                self._SELECTED_SPEAKER_DEVICE = sp_def.get("device", {}).get("name", "NoDevice")
            else:
                self._SELECTED_SPEAKER_DEVICE = "NoDevice"
        except Exception:
            errorLogging()
            self._SELECTED_SPEAKER_DEVICE = "NoDevice"
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
            "Plamo_API": None,
            "Gemini_API": None,
            "OpenAI_API": None,
        }
        self._USE_EXCLUDE_WORDS = True
        self._SELECTED_TRANSLATION_COMPUTE_DEVICE = copy.deepcopy(self.SELECTABLE_COMPUTE_DEVICE_LIST[0])
        self._SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = copy.deepcopy(self.SELECTABLE_COMPUTE_DEVICE_LIST[0])
        self._CTRANSLATE2_WEIGHT_TYPE = "m2m100_418M-ct2-int8"
        self._SELECTED_PLAMO_MODEL = None
        self._SELECTED_GEMINI_MODEL = None
        self._SELECTED_OPENAI_MODEL = None
        self._LMSTUDIO_URL = "http://127.0.0.1:1234/v1"
        self._SELECTED_LMSTUDIO_MODEL = None
        self._SELECTED_OLLAMA_MODEL = None
        self._SELECTED_TRANSLATION_COMPUTE_TYPE = "auto"
        self._WHISPER_WEIGHT_TYPE = "base"
        self._SELECTED_TRANSCRIPTION_COMPUTE_TYPE = "auto"
        self._AUTO_CLEAR_MESSAGE_BOX = True
        self._SEND_ONLY_TRANSLATED_MESSAGES = False
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
        self._SEND_MESSAGE_FORMAT_PARTS = {
            "message": {
                "prefix": "",
                "suffix": ""
                },
            "separator": "\n",
            "translation": {
                "prefix": "",
                "separator": "\n",
                "suffix": ""
            },
            "translation_first": False,
        }
        self._RECEIVED_MESSAGE_FORMAT_PARTS = {
            "message": {
                "prefix": "",
                "suffix": ""
                },
            "separator": "\n",
            "translation": {
                "prefix": "",
                "separator": "\n",
                "suffix": ""
            },
            "translation_first": False,
        }
        self._WEBSOCKET_SERVER = False
        self._WEBSOCKET_HOST = "127.0.0.1"
        self._WEBSOCKET_PORT = 2231

    def load_config(self):
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

if __name__ == "__main__":
    print("Test config.py")
    for key, value in config._config_data.items():
        print(f"{key}: {value}")