import sys
import copy
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

# Auto-register descriptors for serialization
def _auto_register_descriptors():
    """Automatically register ManagedProperty and ValidatedProperty descriptors
    for JSON serialization, reducing boilerplate _json_XXX methods.
    """
    for name, obj in Config.__dict__.items():
        if isinstance(obj, (ManagedProperty, ValidatedProperty)):
            # Only register if serialize=True and not already manually registered
            if obj.serialize and name not in json_serializable_vars:
                # Create closure to capture current name
                def make_serializer(attr_name):
                    @json_serializable(attr_name)
                    def _auto_serialize(self):
                        return getattr(self, attr_name)
                    return _auto_serialize
                make_serializer(name)


# Wrapper classes for mutable types that auto-save on modification
class ManagedDict(dict):
    """Dict wrapper that saves changes back to config."""
    def __init__(self, instance, property_name, immediate_save):
        self._instance = instance
        self._property_name = property_name
        self._immediate_save = immediate_save
        self._internal_name = f"_{property_name}"
        # Initialize from internal storage
        super().__init__(getattr(instance, self._internal_name))

    def _get_internal(self):
        """Get reference to internal storage."""
        return getattr(self._instance, self._internal_name)

    def _save(self):
        """Save current state back to config and sync internal storage."""
        try:
            # Update internal storage directly
            internal_dict = self._get_internal()
            internal_dict.clear()
            internal_dict.update(dict.items(self))
            # Trigger config save only if the corresponding property is serializable
            descriptor = getattr(type(self._instance), self._property_name, None)
            if getattr(descriptor, "serialize", True):
                self._instance.saveConfig(self._property_name, dict(self), immediate_save=self._immediate_save)
        except Exception:
            pass

    def __getitem__(self, key):
        # Always read from internal storage to get latest value
        return self._get_internal()[key]

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._save()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._save()

    def __contains__(self, key):
        return key in self._get_internal()

    def get(self, key, default=None):
        return self._get_internal().get(key, default)

    def keys(self):
        return self._get_internal().keys()

    def values(self):
        return self._get_internal().values()

    def items(self):
        return self._get_internal().items()

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._save()

    def pop(self, *args):
        result = super().pop(*args)
        self._save()
        return result

    def popitem(self):
        result = super().popitem()
        self._save()
        return result

    def clear(self):
        super().clear()
        self._save()

    def setdefault(self, key, default=None):
        result = super().setdefault(key, default)
        self._save()
        return result


class ManagedList(list):
    """List wrapper that saves changes back to config."""
    def __init__(self, instance, property_name, immediate_save):
        self._instance = instance
        self._property_name = property_name
        self._immediate_save = immediate_save
        self._internal_name = f"_{property_name}"
        # Initialize from internal storage
        super().__init__(getattr(instance, self._internal_name))

    def _get_internal(self):
        """Get reference to internal storage."""
        return getattr(self._instance, self._internal_name)

    def _save(self):
        """Save current state back to config and sync internal storage."""
        try:
            # Update internal storage directly
            internal_list = self._get_internal()
            internal_list.clear()
            internal_list.extend(list.__iter__(self))
            # Trigger config save only if the corresponding property is serializable
            descriptor = getattr(type(self._instance), self._property_name, None)
            if getattr(descriptor, "serialize", True):
                self._instance.saveConfig(self._property_name, list(self), immediate_save=self._immediate_save)
        except Exception:
            pass

    def __getitem__(self, index):
        # Always read from internal storage to get latest value
        return self._get_internal()[index]

    def __setitem__(self, index, value):
        super().__setitem__(index, value)
        self._save()

    def __delitem__(self, index):
        super().__delitem__(index)
        self._save()

    def __len__(self):
        return len(self._get_internal())

    def __contains__(self, value):
        return value in self._get_internal()

    def __iter__(self):
        return iter(self._get_internal())

    def append(self, value):
        super().append(value)
        self._save()

    def extend(self, iterable):
        super().extend(iterable)
        self._save()

    def insert(self, index, value):
        super().insert(index, value)
        self._save()

    def remove(self, value):
        super().remove(value)
        self._save()

    def pop(self, index=-1):
        result = super().pop(index)
        self._save()
        return result

    def clear(self):
        super().clear()
        self._save()

    def sort(self, *args, **kwargs):
        super().sort(*args, **kwargs)
        self._save()

    def reverse(self):
        super().reverse()
        self._save()


# Descriptor for simple managed config properties to reduce repetitive getters/setters.
# It performs optional type validation, optional allowed-values check, and calls
# instance.saveConfig(...) on successful set.
class ManagedProperty:
    def __init__(self, name: str, type_: type = None, allowed=None, immediate_save: bool = False, serialize: bool = True, readonly: bool = False, mutable_tracking: bool = False):
        self.name = name
        self.type_ = type_
        self.allowed = allowed
        self.immediate_save = immediate_save
        self.serialize = serialize
        self.readonly = readonly
        self.mutable_tracking = mutable_tracking
        self.private_name = f"_{name}"
        self.wrapper_cache_name = f"_wrapper_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        stored = getattr(instance, self.private_name)

        # If mutable_tracking is enabled, return cached wrapper or create new one
        if self.mutable_tracking and isinstance(stored, dict):
            wrapper = getattr(instance, self.wrapper_cache_name, None)
            if wrapper is None or not isinstance(wrapper, ManagedDict):
                wrapper = ManagedDict(instance, self.name, self.immediate_save)
                setattr(instance, self.wrapper_cache_name, wrapper)
            # Wrapper automatically syncs with internal storage on access
            return wrapper
        elif self.mutable_tracking and isinstance(stored, list):
            wrapper = getattr(instance, self.wrapper_cache_name, None)
            if wrapper is None or not isinstance(wrapper, ManagedList):
                wrapper = ManagedList(instance, self.name, self.immediate_save)
                setattr(instance, self.wrapper_cache_name, wrapper)
            # Wrapper automatically syncs with internal storage on access
            return wrapper

        # Return deep copy for mutable types to prevent external modification
        if isinstance(stored, (dict, list)):
            return copy.deepcopy(stored)
        return stored

    def __set__(self, instance, value):
        # Prevent modification of read-only properties
        if self.readonly:
            raise AttributeError(f"Cannot set read-only property '{self.name}'")

        # Type check if requested（Noneは常に許可）
        if self.type_ is not None and value is not None and not isinstance(value, self.type_):
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

        # Deep copy mutable types to prevent external reference issues
        if isinstance(value, (dict, list)):
            value = copy.deepcopy(value)

        setattr(instance, self.private_name, value)
        # Persist change
        try:
            if self.serialize:
                instance.saveConfig(self.name, value, immediate_save=self.immediate_save)
        except Exception:
            # Keep setter robust during import-time initialization
            pass

class ValidatedProperty:
    """Descriptor for complex validated properties.

    validator(value, instance) -> normalized_value | None
    If returns None (or raises), value is ignored.
    """
    def __init__(self, name: str, validator, immediate_save: bool = False, serialize: bool = True):
        self.name = name
        self.validator = validator
        self.immediate_save = immediate_save
        self.serialize = serialize
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
            if self.serialize:
                instance.saveConfig(self.name, normalized, immediate_save=self.immediate_save)
        except Exception:
            pass


# ============================================================================
# Validator Functions for ValidatedProperty
# ============================================================================

def _main_window_geometry_validator(val, inst):
    if not (isinstance(val, dict) and set(val.keys()) == set(inst.MAIN_WINDOW_GEOMETRY.keys())):
        return None
    new = {}
    for key, value in val.items():
        if isinstance(value, int):
            new[key] = value
        else:
            new[key] = inst.MAIN_WINDOW_GEOMETRY[key]
    return new

def _selected_transcription_compute_type_validator(val, inst):
    if not isinstance(val, str):
        return None
    compute_types = inst.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE.get("compute_types", [])
    if val in compute_types:
        return val
    return None

def _overlay_small_validator(val, inst):
    if not (isinstance(val, dict) and set(val.keys()) == set(inst.OVERLAY_SMALL_LOG_SETTINGS.keys())):
        return None
    base = inst.OVERLAY_SMALL_LOG_SETTINGS
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

def _plugins_status_validator(val, inst):
    if not isinstance(val, list):
        return None
    if not all(isinstance(item, dict) for item in val):
        return None
    return [dict(item) for item in val]

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

def _selected_translation_compute_type_validator(val, inst):
    if not isinstance(val, str):
        return None
    compute_types = inst.SELECTED_TRANSLATION_COMPUTE_DEVICE.get("compute_types", [])
    if val in compute_types:
        return val
    return None

def _mic_host_validator(val, inst):
    if device_manager is None:
        return None
    if not isinstance(val, str):
        return None
    hosts = list(device_manager.getMicDevices().keys())
    return val if val in hosts else None

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

def _compute_device_validator(val, inst):
    if not isinstance(val, dict):
        return None
    for dev in inst.SELECTABLE_COMPUTE_DEVICE_LIST:
        if dev == val:
            return copy.deepcopy(val)
    return None

def _allowed_in_populated(list_attr_name: str):
    def _inner(value, inst):
        try:
            lst = getattr(inst, list_attr_name)
        except Exception:
            return True  # インスタンス状態取得失敗時も弾かない
        if not lst:  # 空/未初期化
            return True
        if value is None:
            return True
        return value in lst
    return _inner


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
        # 永続化対象を descriptor 情報 (json_serializable_vars) から再構成
        filtered = {}
        for var_name, var_func in json_serializable_vars.items():
            try:
                filtered[var_name] = var_func(self)
            except Exception:
                pass
        self._config_data = filtered
        with open(self.PATH_CONFIG, "w", encoding="utf-8") as fp:
            json_dump(filtered, fp, indent=4, ensure_ascii=False)

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

    # Read Only
    VERSION = ManagedProperty('VERSION', readonly=True, serialize=False)
    PATH_LOCAL = ManagedProperty('PATH_LOCAL', readonly=True, serialize=False)
    PATH_CONFIG = ManagedProperty('PATH_CONFIG', readonly=True, serialize=False)
    PATH_LOGS = ManagedProperty('PATH_LOGS', readonly=True, serialize=False)
    GITHUB_URL = ManagedProperty('GITHUB_URL', readonly=True, serialize=False)
    UPDATER_URL = ManagedProperty('UPDATER_URL', readonly=True, serialize=False)
    MAX_MIC_THRESHOLD = ManagedProperty('MAX_MIC_THRESHOLD', readonly=True, serialize=False)
    MAX_SPEAKER_THRESHOLD = ManagedProperty('MAX_SPEAKER_THRESHOLD', readonly=True, serialize=False)
    WATCHDOG_TIMEOUT = ManagedProperty('WATCHDOG_TIMEOUT', readonly=True, serialize=False)
    WATCHDOG_INTERVAL = ManagedProperty('WATCHDOG_INTERVAL', readonly=True, serialize=False)
    SELECTABLE_TAB_NO_LIST = ManagedProperty('SELECTABLE_TAB_NO_LIST', readonly=True, serialize=False)
    SELECTED_TAB_TARGET_LANGUAGES_NO_LIST = ManagedProperty('SELECTED_TAB_TARGET_LANGUAGES_NO_LIST', readonly=True, serialize=False)
    SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST = ManagedProperty('SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST', readonly=True, serialize=False)
    SELECTABLE_WHISPER_WEIGHT_TYPE_LIST = ManagedProperty('SELECTABLE_WHISPER_WEIGHT_TYPE_LIST', readonly=True, serialize=False)
    SELECTABLE_TRANSLATION_ENGINE_LIST = ManagedProperty('SELECTABLE_TRANSLATION_ENGINE_LIST', readonly=True, serialize=False)
    SELECTABLE_TRANSCRIPTION_ENGINE_LIST = ManagedProperty('SELECTABLE_TRANSCRIPTION_ENGINE_LIST', readonly=True, serialize=False)
    SELECTABLE_UI_LANGUAGE_LIST = ManagedProperty('SELECTABLE_UI_LANGUAGE_LIST', readonly=True, serialize=False)
    COMPUTE_MODE = ManagedProperty('COMPUTE_MODE', readonly=True, serialize=False)
    SELECTABLE_COMPUTE_DEVICE_LIST = ManagedProperty('SELECTABLE_COMPUTE_DEVICE_LIST', readonly=True, serialize=False)
    SEND_MESSAGE_BUTTON_TYPE_LIST = ManagedProperty('SEND_MESSAGE_BUTTON_TYPE_LIST', readonly=True, serialize=False)

    # Read Write
    # --- Simple boolean flags (managed by descriptor) ---
    ENABLE_TRANSLATION = ManagedProperty('ENABLE_TRANSLATION', type_=bool, serialize=False)
    ENABLE_TRANSCRIPTION_SEND = ManagedProperty('ENABLE_TRANSCRIPTION_SEND', type_=bool, serialize=False)
    ENABLE_TRANSCRIPTION_RECEIVE = ManagedProperty('ENABLE_TRANSCRIPTION_RECEIVE', type_=bool, serialize=False)
    ENABLE_FOREGROUND = ManagedProperty('ENABLE_FOREGROUND', type_=bool, serialize=False)
    ENABLE_CHECK_ENERGY_SEND = ManagedProperty('ENABLE_CHECK_ENERGY_SEND', type_=bool, serialize=False)
    ENABLE_CHECK_ENERGY_RECEIVE = ManagedProperty('ENABLE_CHECK_ENERGY_RECEIVE', type_=bool, serialize=False)

    # --- Selectable dict/list properties (managed by descriptor, not serialized) ---
    # These are dynamically generated in init_config() based on installed packages/APIs
    SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT = ManagedProperty('SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT', type_=dict, serialize=False, mutable_tracking=True)
    SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = ManagedProperty('SELECTABLE_WHISPER_WEIGHT_TYPE_DICT', type_=dict, serialize=False, mutable_tracking=True)
    SELECTABLE_TRANSLATION_ENGINE_STATUS = ManagedProperty('SELECTABLE_TRANSLATION_ENGINE_STATUS', type_=dict, serialize=False, mutable_tracking=True)
    SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = ManagedProperty('SELECTABLE_TRANSCRIPTION_ENGINE_STATUS', type_=dict, serialize=False, mutable_tracking=True)
    SELECTABLE_PLAMO_MODEL_LIST = ManagedProperty('SELECTABLE_PLAMO_MODEL_LIST', type_=list, serialize=False, mutable_tracking=True)
    SELECTABLE_GEMINI_MODEL_LIST = ManagedProperty('SELECTABLE_GEMINI_MODEL_LIST', type_=list, serialize=False, mutable_tracking=True)
    SELECTABLE_OPENAI_MODEL_LIST = ManagedProperty('SELECTABLE_OPENAI_MODEL_LIST', type_=list, serialize=False, mutable_tracking=True)
    SELECTABLE_GROQ_MODEL_LIST = ManagedProperty('SELECTABLE_GROQ_MODEL_LIST', type_=list, serialize=False, mutable_tracking=True)
    SELECTABLE_OPENROUTER_MODEL_LIST = ManagedProperty('SELECTABLE_OPENROUTER_MODEL_LIST', type_=list, serialize=False, mutable_tracking=True)
    SELECTABLE_LMSTUDIO_MODEL_LIST = ManagedProperty('SELECTABLE_LMSTUDIO_MODEL_LIST', type_=list, serialize=False, mutable_tracking=True)
    SELECTABLE_OLLAMA_MODEL_LIST = ManagedProperty('SELECTABLE_OLLAMA_MODEL_LIST', type_=list, serialize=False, mutable_tracking=True)

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
    MAIN_WINDOW_GEOMETRY = ValidatedProperty('MAIN_WINDOW_GEOMETRY', _main_window_geometry_validator, immediate_save=True)

    # --- Mic-related simple properties ---
    MIC_THRESHOLD = ManagedProperty('MIC_THRESHOLD', type_=int)
    MIC_AUTOMATIC_THRESHOLD = ManagedProperty('MIC_AUTOMATIC_THRESHOLD', type_=bool)
    MIC_RECORD_TIMEOUT = ManagedProperty('MIC_RECORD_TIMEOUT', type_=int)
    MIC_PHRASE_TIMEOUT = ManagedProperty('MIC_PHRASE_TIMEOUT', type_=int)
    MIC_MAX_PHRASES = ManagedProperty('MIC_MAX_PHRASES', type_=int)
    MIC_AVG_LOGPROB = ManagedProperty('MIC_AVG_LOGPROB', type_=(int, float))
    MIC_NO_SPEECH_PROB = ManagedProperty('MIC_NO_SPEECH_PROB', type_=(int, float))
    MIC_NO_REPEAT_NGRAM_SIZE = ManagedProperty('MIC_NO_REPEAT_NGRAM_SIZE', type_=int)
    MIC_VAD_FILTER = ManagedProperty('MIC_VAD_FILTER', type_=bool)
    MIC_VAD_PARAMETERS = ManagedProperty('MIC_VAD_PARAMETERS', type_=dict, mutable_tracking=True)
    HOTKEYS = ValidatedProperty('HOTKEYS',
        validator=lambda val, inst: (
            {k: (v if (isinstance(v, list) or v is None) else inst.HOTKEYS.get(k))
            for k, v in val.items()} if isinstance(val, dict) and set(val.keys()) == set(inst.HOTKEYS.keys()) else None
        ),
        immediate_save=True
    )

    # --- Speaker-related simple properties ---
    SPEAKER_THRESHOLD = ManagedProperty('SPEAKER_THRESHOLD', type_=int)
    SPEAKER_AUTOMATIC_THRESHOLD = ManagedProperty('SPEAKER_AUTOMATIC_THRESHOLD', type_=bool)
    SPEAKER_RECORD_TIMEOUT = ManagedProperty('SPEAKER_RECORD_TIMEOUT', type_=int)
    SPEAKER_PHRASE_TIMEOUT = ManagedProperty('SPEAKER_PHRASE_TIMEOUT', type_=int)
    SPEAKER_MAX_PHRASES = ManagedProperty('SPEAKER_MAX_PHRASES', type_=int)
    SPEAKER_AVG_LOGPROB = ManagedProperty('SPEAKER_AVG_LOGPROB', type_=(int, float))
    SPEAKER_NO_SPEECH_PROB = ManagedProperty('SPEAKER_NO_SPEECH_PROB', type_=(int, float))
    SPEAKER_NO_REPEAT_NGRAM_SIZE = ManagedProperty('SPEAKER_NO_REPEAT_NGRAM_SIZE', type_=int)
    SPEAKER_VAD_FILTER = ManagedProperty('SPEAKER_VAD_FILTER', type_=bool)
    SPEAKER_VAD_PARAMETERS = ManagedProperty('SPEAKER_VAD_PARAMETERS', type_=dict, mutable_tracking=True)

    # --- Auth and API settings ---
    AUTH_KEYS = ValidatedProperty('AUTH_KEYS',
        validator=lambda val, inst: (
            {k: (v if isinstance(v, str) else inst.AUTH_KEYS.get(k)) for k, v in val.items()}
            if isinstance(val, dict) and set(val.keys()) == set(inst.AUTH_KEYS.keys()) else None
        )
    )
    LMSTUDIO_URL = ManagedProperty('LMSTUDIO_URL', type_=str)

    # --- Transcription settings ---
    SELECTED_TRANSCRIPTION_COMPUTE_TYPE = ValidatedProperty('SELECTED_TRANSCRIPTION_COMPUTE_TYPE', _selected_transcription_compute_type_validator)

    # --- Overlay settings ---
    OVERLAY_SMALL_LOG_SETTINGS = ValidatedProperty('OVERLAY_SMALL_LOG_SETTINGS', _overlay_small_validator)
    OVERLAY_LARGE_LOG_SETTINGS = ValidatedProperty('OVERLAY_LARGE_LOG_SETTINGS', _overlay_large_validator)

    # --- Message format settings ---
    SEND_MESSAGE_FORMAT_PARTS = ValidatedProperty('SEND_MESSAGE_FORMAT_PARTS', _format_validator_send)
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

    # --- OBS Browser Source (overlay for OBS) ---
    OBS_BROWSER_SOURCE = ManagedProperty('OBS_BROWSER_SOURCE', type_=bool)
    OBS_BROWSER_SOURCE_PORT = ManagedProperty('OBS_BROWSER_SOURCE_PORT', type_=int)
    OBS_BROWSER_SOURCE_MAX_MESSAGES = ManagedProperty('OBS_BROWSER_SOURCE_MAX_MESSAGES', type_=int)
    OBS_BROWSER_SOURCE_DISPLAY_DURATION = ManagedProperty('OBS_BROWSER_SOURCE_DISPLAY_DURATION', type_=int)
    OBS_BROWSER_SOURCE_FADEOUT_DURATION = ManagedProperty('OBS_BROWSER_SOURCE_FADEOUT_DURATION', type_=int)
    OBS_BROWSER_SOURCE_FONT_SIZE = ManagedProperty('OBS_BROWSER_SOURCE_FONT_SIZE', type_=int)
    OBS_BROWSER_SOURCE_FONT_COLOR = ManagedProperty('OBS_BROWSER_SOURCE_FONT_COLOR', type_=str)
    OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS = ManagedProperty('OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS', type_=int)
    OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR = ManagedProperty('OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR', type_=str)
    
    # --- Telemetry Settings ---
    ENABLE_TELEMETRY = ManagedProperty('ENABLE_TELEMETRY', type_=bool)

    # --- Selection properties with validation (ManagedProperty) ---
    SELECTED_TAB_NO = ManagedProperty('SELECTED_TAB_NO', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_TAB_NO_LIST)
    SELECTED_TRANSCRIPTION_ENGINE = ManagedProperty('SELECTED_TRANSCRIPTION_ENGINE', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_TRANSCRIPTION_ENGINE_LIST)
    USE_EXCLUDE_WORDS = ManagedProperty('USE_EXCLUDE_WORDS', type_=bool)
    CTRANSLATE2_WEIGHT_TYPE = ManagedProperty('CTRANSLATE2_WEIGHT_TYPE', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST)
    WHISPER_WEIGHT_TYPE = ManagedProperty('WHISPER_WEIGHT_TYPE', type_=str, allowed=lambda v, inst: v in inst.SELECTABLE_WHISPER_WEIGHT_TYPE_LIST)
    SELECTED_PLAMO_MODEL = ManagedProperty('SELECTED_PLAMO_MODEL', type_=str, allowed=_allowed_in_populated('SELECTABLE_PLAMO_MODEL_LIST'))
    SELECTED_GEMINI_MODEL = ManagedProperty('SELECTED_GEMINI_MODEL', type_=str, allowed=_allowed_in_populated('SELECTABLE_GEMINI_MODEL_LIST'))
    SELECTED_OPENAI_MODEL = ManagedProperty('SELECTED_OPENAI_MODEL', type_=str, allowed=_allowed_in_populated('SELECTABLE_OPENAI_MODEL_LIST'))
    SELECTED_GROQ_MODEL = ManagedProperty('SELECTED_GROQ_MODEL', type_=str, allowed=_allowed_in_populated('SELECTABLE_GROQ_MODEL_LIST'))
    SELECTED_OPENROUTER_MODEL = ManagedProperty('SELECTED_OPENROUTER_MODEL', type_=str, allowed=_allowed_in_populated('SELECTABLE_OPENROUTER_MODEL_LIST'))
    SELECTED_LMSTUDIO_MODEL = ManagedProperty('SELECTED_LMSTUDIO_MODEL', type_=str, allowed=_allowed_in_populated('SELECTABLE_LMSTUDIO_MODEL_LIST'))
    SELECTED_OLLAMA_MODEL = ManagedProperty('SELECTED_OLLAMA_MODEL', type_=str, allowed=_allowed_in_populated('SELECTABLE_OLLAMA_MODEL_LIST'))

    # --- Translation and language settings ---
    MIC_WORD_FILTER = ValidatedProperty('MIC_WORD_FILTER', _mic_word_filter_validator)
    PLUGINS_STATUS = ValidatedProperty('PLUGINS_STATUS', _plugins_status_validator, immediate_save=True)
    SELECTED_TRANSLATION_ENGINES = ValidatedProperty('SELECTED_TRANSLATION_ENGINES', _selected_translation_engines_validator)
    SELECTED_YOUR_LANGUAGES = ValidatedProperty('SELECTED_YOUR_LANGUAGES', _selected_your_languages_validator)
    SELECTED_TARGET_LANGUAGES = ValidatedProperty('SELECTED_TARGET_LANGUAGES', _selected_target_languages_validator)
    SELECTED_TRANSLATION_COMPUTE_TYPE = ValidatedProperty('SELECTED_TRANSLATION_COMPUTE_TYPE', _selected_translation_compute_type_validator)

    # --- Device settings ---
    AUTO_MIC_SELECT = ManagedProperty('AUTO_MIC_SELECT', type_=bool)
    AUTO_SPEAKER_SELECT = ManagedProperty('AUTO_SPEAKER_SELECT', type_=bool)
    SELECTED_MIC_HOST = ValidatedProperty('SELECTED_MIC_HOST', _mic_host_validator)
    SELECTED_MIC_DEVICE = ValidatedProperty('SELECTED_MIC_DEVICE', _mic_device_validator)
    SELECTED_SPEAKER_DEVICE = ValidatedProperty('SELECTED_SPEAKER_DEVICE', _speaker_device_validator)
    SELECTED_TRANSLATION_COMPUTE_DEVICE = ValidatedProperty('SELECTED_TRANSLATION_COMPUTE_DEVICE', _compute_device_validator)
    SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = ValidatedProperty('SELECTED_TRANSCRIPTION_COMPUTE_DEVICE', _compute_device_validator)

    # -- Clipboard control ---
    ENABLE_CLIPBOARD = ManagedProperty('ENABLE_CLIPBOARD', type_=bool)

    def init_config(self):
        # Read Only
        self._VERSION = "3.4.0"
        if getattr(sys, 'frozen', False):
            self._PATH_LOCAL = os_path.dirname(sys.executable)
        else:
            self._PATH_LOCAL = os_path.dirname(os_path.abspath(__file__))
        self._PATH_CONFIG = os_path.join(self._PATH_LOCAL, "config.json")
        self._PATH_LOGS = os_path.join(self._PATH_LOCAL, "logs")
        os_makedirs(self._PATH_LOGS, exist_ok=True)
        self._GITHUB_URL = "https://api.github.com/repos/misyaguziya/VRCT/releases/latest"
        self._UPDATER_URL = "https://api.github.com/repos/misyaguziya/VRCT_updater/releases/latest"

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
        self._SELECTABLE_GROQ_MODEL_LIST = []
        self._SELECTABLE_OPENROUTER_MODEL_LIST = []
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
        self._MIC_NO_REPEAT_NGRAM_SIZE = 0
        self._MIC_VAD_FILTER = False
        self._MIC_VAD_PARAMETERS = {
            "threshold": 0.5,
            "neg_threshold": None,
            "min_speech_duration_ms": 0,
            "max_speech_duration_s": float("inf"),
            "min_silence_duration_ms": 2000,
            "speech_pad_ms": 400,
        }
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
        self._SPEAKER_NO_REPEAT_NGRAM_SIZE = 0
        self._SPEAKER_VAD_FILTER = False
        self._SPEAKER_VAD_PARAMETERS = {
            "threshold": 0.5,
            "neg_threshold": None,
            "min_speech_duration_ms": 0,
            "max_speech_duration_s": float("inf"),
            "min_silence_duration_ms": 2000,
            "speech_pad_ms": 400,
        }
        self._OSC_IP_ADDRESS = "127.0.0.1"
        self._OSC_PORT = 9000
        self._AUTH_KEYS = {
            "DeepL_API": None,
            "Plamo_API": None,
            "Gemini_API": None,
            "OpenAI_API": None,
            "Groq_API": None,
            "OpenRouter_API": None,
        }
        self._USE_EXCLUDE_WORDS = True
        self._SELECTED_TRANSLATION_COMPUTE_DEVICE = copy.deepcopy(self.SELECTABLE_COMPUTE_DEVICE_LIST[0])
        self._SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = copy.deepcopy(self.SELECTABLE_COMPUTE_DEVICE_LIST[0])
        self._CTRANSLATE2_WEIGHT_TYPE = "m2m100_418M-ct2-int8"
        self._SELECTED_PLAMO_MODEL = None
        self._SELECTED_GEMINI_MODEL = None
        self._SELECTED_OPENAI_MODEL = None
        self._SELECTED_GROQ_MODEL = None
        self._SELECTED_OPENROUTER_MODEL = None
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
        self._OBS_BROWSER_SOURCE = False
        self._OBS_BROWSER_SOURCE_PORT = 2232
        self._OBS_BROWSER_SOURCE_MAX_MESSAGES = 14
        self._OBS_BROWSER_SOURCE_DISPLAY_DURATION = 60
        self._OBS_BROWSER_SOURCE_FADEOUT_DURATION = 12
        self._OBS_BROWSER_SOURCE_FONT_SIZE = 40
        self._OBS_BROWSER_SOURCE_FONT_COLOR = "#FFFFFF"
        self._OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS = 3
        self._OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR = "#000000"
        self._ENABLE_CLIPBOARD = False
        self._ENABLE_TELEMETRY = True

    def load_config(self):
        self._config_data = {}
        if os_path.isfile(self.PATH_CONFIG) is not False:
            with open(self.PATH_CONFIG, 'r', encoding="utf-8") as fp:
                if fp.readable() and fp.seek(0, 2) > 0:
                    fp.seek(0)
                    self._config_data = json_load(fp)

                    for key, value in self._config_data.items():
                        # 読み込み時: serialize=True かつ readonlyでない Descriptor のみ反映。
                        # 未知キー（Descriptorなし）は無視して注入を防止。
                        try:
                            descriptor = getattr(type(self), key, None)
                            if isinstance(descriptor, ManagedProperty):
                                if descriptor.readonly or not descriptor.serialize:
                                    continue
                                setattr(self, key, value)
                            elif isinstance(descriptor, ValidatedProperty):
                                if not descriptor.serialize:
                                    continue
                                setattr(self, key, value)
                            else:
                                # 不明キーは破棄（古い/不要/改竄の可能性）
                                continue
                        except Exception:
                            errorLogging()

        self.saveConfigToFile()

    def revalidate_selected_models(self):
        pairs = [
            ('SELECTED_PLAMO_MODEL', 'SELECTABLE_PLAMO_MODEL_LIST'),
            ('SELECTED_GEMINI_MODEL', 'SELECTABLE_GEMINI_MODEL_LIST'),
            ('SELECTED_OPENAI_MODEL', 'SELECTABLE_OPENAI_MODEL_LIST'),
            ('SELECTED_GROQ_MODEL', 'SELECTABLE_GROQ_MODEL_LIST'),
            ('SELECTED_OPENROUTER_MODEL', 'SELECTABLE_OPENROUTER_MODEL_LIST'),
            ('SELECTED_LMSTUDIO_MODEL', 'SELECTABLE_LMSTUDIO_MODEL_LIST'),
            ('SELECTED_OLLAMA_MODEL', 'SELECTABLE_OLLAMA_MODEL_LIST'),
        ]
        for sel_attr, list_attr in pairs:
            try:
                current = getattr(self, sel_attr)
                lst = getattr(self, list_attr)
                if lst and current is not None and current not in lst:
                    if len(lst) > 0:
                        setattr(self, sel_attr, lst[0])
                    else:
                        setattr(self, sel_attr, None)
            except Exception:
                errorLogging()

# Auto-register all descriptors after Config class definition
_auto_register_descriptors()

config = Config()

if __name__ == "__main__":
    print("Test config.py")
    for key, value in config._config_data.items():
        print(f"{key}: {value}")
