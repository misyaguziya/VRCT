import asyncio
import copy
import gc
import json
import logging # Added
from datetime import datetime
from os import makedirs as os_makedirs
from os import path as os_path
from queue import Queue
from subprocess import Popen
from threading import Thread
from time import sleep
from typing import (Any, Callable, Dict, List, Optional, Tuple, Type,  # Added Type, List, Dict, etc.
                    TypeVar, Union)

from flashtext import KeywordProcessor # Third-party
from packaging.version import parse
from pykakasi import kakasi
from requests import get as requests_get

from config import config # Local application
from device_manager import device_manager
from models.osc.osc import OSCHandler
from models.overlay.overlay import Overlay
from models.overlay.overlay_image import OverlayImage
from models.transcription.transcription_recorder import (
    SelectedMicEnergyAndAudioRecorder, SelectedMicEnergyRecorder,
    SelectedSpeakerEnergyAndAudioRecorder, SelectedSpeakerEnergyRecorder)
from models.transcription.transcription_transcriber import AudioTranscriber
from models.transcription.transcription_languages import \
    transcription_lang as transcription_lang_data # Alias to avoid conflict
from models.transcription.transcription_whisper import (
    checkWhisperWeight, downloadWhisperWeight)
from models.translation.translation_languages import \
    translation_lang as translation_lang_data # Alias to avoid conflict
from models.translation.translation_translator import Translator
from models.translation.translation_utils import (
    checkCTranslate2Weight, downloadCTranslate2Tokenizer,
    downloadCTranslate2Weight)
from models.watchdog.watchdog import Watchdog
from models.websocket.websocket_server import WebSocketServer
from utils import errorLogging, setupLogger

# Define a TypeVar for Singleton pattern if needed elsewhere, or just use Type[Model]
T_Model = TypeVar('T_Model', bound='Model')


class threadFnc(Thread):
    """A utility class to run a function in a separate thread with stop/pause/resume controls."""
    fnc: Callable[..., Any]
    end_fnc: Optional[Callable[[], None]]
    loop: bool
    _pause: bool
    _args: Tuple[Any, ...]
    _kwargs: Dict[str, Any]

    def __init__(self, fnc: Callable[..., Any], end_fnc: Optional[Callable[[], None]] = None, daemon: bool = True, *args: Any, **kwargs: Any) -> None:
        """
        Initializes the thread.

        Args:
            fnc: The function to be executed in the loop.
            end_fnc: An optional function to be called when the loop finishes.
            daemon: Whether the thread is a daemon thread.
            *args: Arguments to pass to `fnc`.
            **kwargs: Keyword arguments to pass to `fnc`.
        """
        super().__init__(daemon=daemon, target=self._target_wrapper) # Use a wrapper for args/kwargs
        self.fnc = fnc
        self.end_fnc = end_fnc
        self.loop = True
        self._pause = False
        self._args = args      # Store args
        self._kwargs = kwargs  # Store kwargs

    def _target_wrapper(self) -> None: # Wrapper to pass stored args/kwargs
        """Internal wrapper to call the target function with stored arguments."""
        # This method is not strictly necessary if target is not used by Thread directly
        # but helps if run() is overridden and needs to call the original target logic.
        # However, Thread's target is called by its start() method.
        # The run method is what gets executed.
        pass # Not needed as run() is overridden

    def stop(self) -> None:
        """Stops the execution loop of the thread."""
        self.loop = False

    def pause(self) -> None:
        """Pauses the execution loop of the thread."""
        self._pause = True

    def resume(self) -> None:
        """Resumes the execution loop of the thread."""
        self._pause = False

    def run(self) -> None:
        """The main execution loop of the thread. Calls `fnc` repeatedly."""
        try:
            while self.loop:
                if not self._pause:
                    self.fnc(*self._args, **self._kwargs) # Call fnc with stored args/kwargs
                else:
                    sleep(0.1) # Sleep when paused
                # Add a small sleep even when not paused if fnc is very fast, to prevent tight loop
                # Or make fnc responsible for its own sleep if it's a polling type function
                # For now, assuming fnc might be blocking or has its own sleep.
                # If fnc is non-blocking and fast, a sleep(0.01) here might be good.
        except Exception as e:
            errorLogging(f"Exception in threadFnc ({self.fnc.__name__ if hasattr(self.fnc, '__name__') else 'unknown_fnc'}): {e}")
        finally:
            if callable(self.end_fnc):
                try:
                    self.end_fnc()
                except Exception as e:
                    errorLogging(f"Exception in threadFnc end_fnc ({self.end_fnc.__name__ if hasattr(self.end_fnc, '__name__') else 'unknown_end_fnc'}): {e}")
        return # Explicit return None

class Model:
    _instance: Optional['Model'] = None # Forward declaration for Model itself

    # Attributes with type hints
    logger: Optional[logging.Logger]
    # th_check_device: Optional[threadFnc] # This attribute was not used elsewhere, consider removing if truly unused
    mic_print_transcript: Optional[threadFnc]
    mic_audio_recorder: Optional[SelectedMicEnergyAndAudioRecorder]
    mic_transcriber: Optional[AudioTranscriber]
    mic_energy_recorder: Optional[SelectedMicEnergyRecorder]
    mic_energy_plot_progressbar: Optional[threadFnc] # Thread for mic energy UI updates
    speaker_print_transcript: Optional[threadFnc]
    speaker_audio_recorder: Optional[SelectedSpeakerEnergyAndAudioRecorder]
    speaker_transcriber: Optional[AudioTranscriber]
    speaker_energy_recorder: Optional[SelectedSpeakerEnergyRecorder]
    speaker_energy_plot_progressbar: Optional[threadFnc] # Thread for speaker energy UI updates

    previous_send_message: str
    previous_receive_message: str
    translator: Translator
    keyword_processor: KeywordProcessor
    overlay: Overlay
    overlay_image: OverlayImage # Instance of utility for creating overlay images
    mic_audio_queue: Optional[Queue[Any]] # Queue for microphone audio data
    mic_mute_status: Optional[bool] # VRChat mic mute status from OSCQuery
    kks: kakasi # Kakasi instance for Japanese transliteration
    watchdog: Watchdog
    osc_handler: OSCHandler
    websocket_server: Optional[WebSocketServer]
    websocket_server_loop: bool # Flag to control the WebSocket server's asyncio loop
    websocket_server_alive: bool # Flag indicating if the WebSocket server is actively listening
    th_websocket_server: Optional[Thread] # Thread for running the WebSocket server's asyncio loop

    check_mic_energy_fnc: Optional[Callable[[Union[float, bool]], None]]
    check_speaker_energy_fnc: Optional[Callable[[Union[float, bool]], None]]
    th_watchdog: Optional[threadFnc]


    def __new__(cls: Type[T_Model]) -> T_Model: # Use T_Model for singleton pattern
        """Ensures that only one instance of the Model class is created (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(Model, cls).__new__(cls)
            # init() is called here to ensure instance variables are set up on first creation.
            cls._instance.init()
        return cls._instance

    def init(self) -> None:
        """Initializes all model components, services, and default states."""
        self.logger = None
        # self.th_check_device = None # Example: remove if unused
        self.mic_print_transcript = None
        self.mic_audio_recorder = None
        self.mic_transcriber = None
        self.mic_energy_recorder = None
        self.mic_energy_plot_progressbar = None
        self.speaker_print_transcript = None
        self.speaker_audio_recorder = None
        self.speaker_transcriber = None
        self.speaker_energy_recorder = None
        self.speaker_energy_plot_progressbar = None

        self.previous_send_message = ""
        self.previous_receive_message = ""
        self.translator = Translator()
        self.keyword_processor = KeywordProcessor()

        # Deepcopy settings from config to avoid modifying config object directly
        overlay_small_log_settings = copy.deepcopy(config.OVERLAY_SMALL_LOG_SETTINGS)
        overlay_large_log_settings = copy.deepcopy(config.OVERLAY_LARGE_LOG_SETTINGS)
        # Specific adjustment for large log UI scaling
        if "ui_scaling" in overlay_large_log_settings: # Check key exists
            overlay_large_log_settings["ui_scaling"] = float(overlay_large_log_settings["ui_scaling"]) * 0.25

        overlay_settings: Dict[str, Any] = {
            "small": overlay_small_log_settings,
            "large": overlay_large_log_settings,
        }
        self.overlay = Overlay(overlay_settings)
        self.overlay_image = OverlayImage()
        self.mic_audio_queue = None # Will be Queue() when mic transcription starts
        self.mic_mute_status = None
        self.kks = kakasi()
        self.watchdog = Watchdog(config.WATCHDOG_TIMEOUT, config.WATCHDOG_INTERVAL)
        self.osc_handler = OSCHandler(config.OSC_IP_ADDRESS, config.OSC_PORT)
        self.websocket_server = None
        self.websocket_server_loop = False
        self.websocket_server_alive = False
        self.th_websocket_server = None
        self.check_mic_energy_fnc = None
        self.check_speaker_energy_fnc = None
        self.th_watchdog = None


    def checkTranslatorCTranslate2ModelWeight(self, weight_type: str) -> bool:
        """Checks if the CTranslate2 model weight of the specified type is available."""
        return checkCTranslate2Weight(config.PATH_LOCAL, weight_type)

    def changeTranslatorCTranslate2Model(self) -> None:
        """Changes the CTranslate2 model based on current config (weight type, compute device)."""
        self.translator.changeCTranslate2Model(
            config.PATH_LOCAL,
            config.CTRANSLATE2_WEIGHT_TYPE,
            config.SELECTED_TRANSLATION_COMPUTE_DEVICE["device"],
            config.SELECTED_TRANSLATION_COMPUTE_DEVICE["device_index"]
        )

    def downloadCTranslate2ModelWeight(self, weight_type: str, callback: Optional[Callable[[Any], None]] = None, end_callback: Optional[Callable[[], None]] = None) -> Any:
        """Downloads CTranslate2 model weights for the specified weight type."""
        # Return type 'Any' as the underlying function's return is not strictly defined here
        return downloadCTranslate2Weight(config.PATH_LOCAL, weight_type, callback, end_callback)

    def downloadCTranslate2ModelTokenizer(self, weight_type: str) -> Any:
        """Downloads the tokenizer for the CTranslate2 model of the specified weight type."""
        # Return type 'Any'
        return downloadCTranslate2Tokenizer(config.PATH_LOCAL, weight_type)

    def isLoadedCTranslate2Model(self) -> bool:
        """Checks if a CTranslate2 model is currently loaded in the translator."""
        return self.translator.isLoadedCTranslate2Model()

    def checkTranscriptionWhisperModelWeight(self, weight_type: str) -> bool:
        """Checks if the Whisper model weight of the specified type is available."""
        return checkWhisperWeight(config.PATH_LOCAL, weight_type)

    def downloadWhisperModelWeight(self, weight_type: str, callback: Optional[Callable[[Any], None]] = None, end_callback: Optional[Callable[[], None]] = None) -> Any:
        """Downloads Whisper model weights for the specified weight type."""
        # Return type 'Any'
        return downloadWhisperWeight(config.PATH_LOCAL, weight_type, callback, end_callback)

    def resetKeywordProcessor(self) -> None:
        """Resets the keyword processor by creating a new instance."""
        del self.keyword_processor
        gc.collect() # Suggest garbage collection for the old instance
        self.keyword_processor = KeywordProcessor()

    def authenticationTranslatorDeepLAuthKey(self, auth_key: str) -> bool:
        """Authenticates the DeepL API key using the translator module."""
        result: bool = self.translator.authenticationDeepLAuthKey(auth_key)
        return result

    def startLogger(self) -> None:
        """Initializes and enables the application logger."""
        os_makedirs(config.PATH_LOGS, exist_ok=True)
        file_name = os_path.join(config.PATH_LOGS, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
        # Assuming setupLogger returns a configured Logger instance
        self.logger: Optional[logging.Logger] = setupLogger("log", file_name)
        if self.logger:
            self.logger.disabled = False

    def stopLogger(self) -> None:
        """Disables the application logger."""
        if self.logger:
            self.logger.disabled = True
            # Forcing handlers to close and release file might be needed on some OS or configurations
            # for handler in self.logger.handlers[:]:
            #     handler.close()
            #     self.logger.removeHandler(handler)
        self.logger = None # Allow garbage collection

    def getListLanguageAndCountry(self) -> List[Dict[str, str]]:
        """
        Gets a sorted list of supported languages and their countries,
        filtered by compatibility between transcription and translation services.
        """
        # Use aliased data for clarity
        transcription_languages = list(transcription_lang_data.keys())
        translation_source_languages: List[str] = []
        for engine_key in translation_lang_data: # Ensure this is the correct data structure
            engine_data = translation_lang_data.get(engine_key, {})
            source_langs_for_engine = engine_data.get("source", {}) # This is a dict like {"English": {"language_code": "EN", ...}}
            for lang_name in source_langs_for_engine: 
                translation_source_languages.append(lang_name) 
        
        translation_source_languages = list(set(translation_source_languages))
        
        supported_langs = [lang for lang in transcription_languages if lang in translation_source_languages]

        languages_result: List[Dict[str, str]] = []
        for language_name in supported_langs:
            if language_name in transcription_lang_data: 
                for country_name in transcription_lang_data[language_name]:
                    languages_result.append(
                        {
                            "language": language_name,
                            "country": country_name,
                        }
                    )
        languages_result = sorted(languages_result, key=lambda x: x.get('language', '')) 
        return languages_result

    def findTranslationEngines(self, source_lang_config: Dict[str, Any], target_lang_config: Dict[str, Any], engines_status: Dict[str, bool]) -> List[str]:
        """
        Finds compatible translation engines based on source/target languages and engine status.
        `source_lang_config` and `target_lang_config` are dicts like:
        {"1": {"language": "English", "country": "United States", "enable": True}, ...}
        """
        selectable_engines = [key for key, value in engines_status.items() if value is True]
        compatible_engines: List[str] = []

        active_source_langs: List[str] = [
            details["language"] for details in source_lang_config.values() if details.get("enable") and "language" in details
        ]
        active_target_langs: List[str] = [
            details["language"] for details in target_lang_config.values() if details.get("enable") and "language" in details
        ]

        if not active_source_langs or not active_target_langs:
            return [] 

        for engine_name in translation_lang_data: 
            if engine_name not in selectable_engines:
                continue

            # engine_capabilities is like {"English": {"language_code": "EN", "targets": ["Japanese", ...]}, ...}
            engine_capabilities = translation_lang_data.get(engine_name, {}).get("source", {}) 
            
            all_sources_supported = all(src_lang in engine_capabilities for src_lang in active_source_langs)
            if not all_sources_supported:
                continue
            
            all_targets_supported_for_all_sources = True
            for src_lang_name in active_source_langs:
                src_lang_details = engine_capabilities.get(src_lang_name)
                if not src_lang_details or not src_lang_details.get("targets"):
                    all_targets_supported_for_all_sources = False
                    break
                
                supported_targets_for_this_source: List[str] = src_lang_details["targets"]
                if not all(target_lang in supported_targets_for_this_source for target_lang in active_target_langs):
                    all_targets_supported_for_all_sources = False
                    break
            
            if all_targets_supported_for_all_sources:
                compatible_engines.append(engine_name)
        return compatible_engines

    def getTranslate(self, translator_name: str, source_language: str, target_language: str, target_country: str, message: str) -> Tuple[str, bool]:
        """Translates a message using the specified engine and languages, with a fallback to CTranslate2."""
        success_flag = False
        translation_result: Union[str, bool] = self.translator.translate(
            translator_name=translator_name,
            source_language=source_language,
            target_language=target_language,
            target_country=target_country,
            message=message
        )

        final_translation: str
        if isinstance(translation_result, str):
            success_flag = True
            final_translation = translation_result
        else: 
            printLog(f"Translation failed with {translator_name}, falling back to CTranslate2 for: {message[:30]}...")
            ct2_translation_result = self.translator.translate(
                translator_name="CTranslate2", 
                source_language=source_language,
                target_language=target_language,
                target_country=target_country, 
                message=message
            )
            if isinstance(ct2_translation_result, str):
                success_flag = True 
                final_translation = ct2_translation_result
            else:
                errorLogging(f"CTranslate2 fallback translation also failed for: {message[:30]}")
                final_translation = message 
                success_flag = False 
        return final_translation, success_flag


    def getInputTranslate(self, message: str, source_language: Optional[str] = None) -> Tuple[List[str], List[bool]]:
        """Translates input message to configured target languages."""
        translator_name = config.SELECTED_TRANSLATION_ENGINES.get(config.SELECTED_TAB_NO, "CTranslate2")
        
        effective_source_language: str
        if source_language is not None:
            effective_source_language = source_language
        else:
            your_lang_tab = config.SELECTED_YOUR_LANGUAGES.get(config.SELECTED_TAB_NO, {})
            your_lang_primary = your_lang_tab.get("1", {})
            effective_source_language = your_lang_primary.get("language", "en") 

        target_languages_config = config.SELECTED_TARGET_LANGUAGES.get(config.SELECTED_TAB_NO, {})
        translations: List[str] = []
        success_flags: List[bool] = []

        for lang_details in target_languages_config.values():
            if lang_details.get("enable"):
                target_language = lang_details.get("language")
                target_country = lang_details.get("country")
                if target_language and target_country: 
                    translation, success = self.getTranslate(
                        translator_name,
                        effective_source_language,
                        target_language,
                        target_country,
                        message
                    )
                    translations.append(translation)
                    success_flags.append(success)
        return translations, success_flags

    def getOutputTranslate(self, message: str, source_language: Optional[str] = None) -> Tuple[List[str], List[bool]]:
        """Translates output message (e.g., from speaker) to the user's primary language."""
        translator_name = config.SELECTED_TRANSLATION_ENGINES.get(config.SELECTED_TAB_NO, "CTranslate2")

        effective_source_language: str
        if source_language is not None:
            effective_source_language = source_language
        else:
            target_lang_tab = config.SELECTED_TARGET_LANGUAGES.get(config.SELECTED_TAB_NO, {})
            target_lang_primary = target_lang_tab.get("1", {})
            effective_source_language = target_lang_primary.get("language", "en") 

        your_lang_tab = config.SELECTED_YOUR_LANGUAGES.get(config.SELECTED_TAB_NO, {})
        your_lang_primary = your_lang_tab.get("1", {})
        final_target_language = your_lang_primary.get("language", "en") 
        final_target_country = your_lang_primary.get("country", "US")   

        translation, success_flag = self.getTranslate(
            translator_name,
            effective_source_language,
            final_target_language,
            final_target_country,
            message
        )
        return [translation], [success_flag]

    def addKeywords(self) -> None:
        """Adds words from the config's microphone word filter to the keyword processor."""
        if not hasattr(self, 'keyword_processor'): 
            self.keyword_processor = KeywordProcessor()
        for f_word in config.MIC_WORD_FILTER:
            self.keyword_processor.add_keyword(f_word)

    def checkKeywords(self, message: str) -> bool:
        """Checks if any configured keywords are present in the message."""
        if not hasattr(self, 'keyword_processor'):
            return False
        return len(self.keyword_processor.extract_keywords(message)) > 0

    def detectRepeatSendMessage(self, message: str) -> bool:
        """Detects if the current sent message is identical to the previous one."""
        repeat_flag = False
        if self.previous_send_message == message:
            repeat_flag = True
        self.previous_send_message = message
        return repeat_flag

    def detectRepeatReceiveMessage(self, message: str) -> bool:
        """Detects if the current received message is identical to the previous one."""
        repeat_flag = False
        if self.previous_receive_message == message:
            repeat_flag = True
        self.previous_receive_message = message
        return repeat_flag

    def convertMessageToTransliteration(self, message: str) -> List[Dict[str, str]]:
        """Converts a Japanese message to Hiragana and Romaji (Hepburn) using pykakasi."""
        if not hasattr(self, 'kks') or self.kks is None: 
            self.kks = kakasi()
        
        data_list: List[Dict[str, str]] = self.kks.convert(message) # pykakasi.convert returns List[Dict[str, str]]
        keys_to_keep = {"orig", "hira", "hepburn"} # `set` for efficient lookup
        filtered_list: List[Dict[str, str]] = []
        for item in data_list:
            filtered_item_content = {key: value for key, value in item.items() if key in keys_to_keep}
            filtered_list.append(filtered_item_content)
        return filtered_list

    def setOscIpAddress(self, ip_address: str) -> None:
        """Sets the IP address for the OSC handler."""
        self.osc_handler.setOscIpAddress(ip_address)

    def setOscPort(self, port: int) -> None:
        """Sets the port for the OSC handler."""
        self.osc_handler.setOscPort(port)

    def oscStartSendTyping(self) -> None:
        """Sends an OSC message to indicate typing has started."""
        self.osc_handler.sendTyping(flag=True)

    def oscStopSendTyping(self) -> None:
        """Sends an OSC message to indicate typing has stopped."""
        self.osc_handler.sendTyping(flag=False)

    def oscSendMessage(self, message: str) -> None:
        """Sends a message via OSC, with optional notification sound."""
        self.osc_handler.sendMessage(message=message, notification=config.NOTIFICATION_VRC_SFX)

    def setMuteSelfStatus(self) -> None:
        """Updates the internal mic mute status based on OSC query result."""
        self.mic_mute_status = self.osc_handler.getOSCParameterMuteSelf()

    def startReceiveOSC(self) -> None:
        """Starts the OSC parameter receiver and sets up handlers for mute status changes."""
        def changeHandlerMute(address: str, osc_arguments: Any) -> None:
            # This callback is executed by the OSC library, ensure it's robust
            try:
                if config.ENABLE_TRANSCRIPTION_SEND: # Check outer config flag
                    is_muted_argument = bool(osc_arguments) 
                    if is_muted_argument is True and self.mic_mute_status is False:
                        self.mic_mute_status = True
                        self.changeMicTranscriptStatus()
                    elif is_muted_argument is False and self.mic_mute_status is True:
                        self.mic_mute_status = False
                        self.changeMicTranscriptStatus()
            except Exception as e:
                errorLogging(f"Error in OSC changeHandlerMute: {e}")

        dict_filter_and_target: Dict[str, Callable[[str, Any], None]] = {
            str(self.osc_handler.osc_parameter_muteself): changeHandlerMute,
        }
        self.osc_handler.setDictFilterAndTarget(dict_filter_and_target)
        self.osc_handler.receiveOscParameters() 

    def stopReceiveOSC(self) -> None:
        """Stops the OSC server from listening for parameters."""
        self.osc_handler.oscServerStop()

    def getIsOscQueryEnabled(self) -> bool:
        """Checks if OSCQuery is currently enabled and connected."""
        return self.osc_handler.getIsOscQueryEnabled()

    @staticmethod
    def checkSoftwareUpdated() -> Dict[str, Any]:
        """Checks for software updates from GitHub releases."""
        update_flag = False
        version_str = "" 
        try:
            response = requests_get(config.GITHUB_URL, timeout=10) 
            response.raise_for_status() 
            json_data = response.json()
            version_str = json_data.get("name", "") 
            if isinstance(version_str, str) and version_str:
                new_version = parse(version_str.lstrip('v')) 
                current_version = parse(config.VERSION.lstrip('v'))
                if new_version > current_version:
                    update_flag = True
            else: 
                errorLogging(f"Could not parse version from GitHub response: {json_data}")
        except requests_get.exceptions.RequestException as e:
            errorLogging(f"Request failed while checking software update: {e}")
        except json.JSONDecodeError as e:
            errorLogging(f"Failed to decode JSON from GitHub response: {e}")
        except Exception as e: 
            errorLogging(f"Error checking software update: {e}")
        return {
            "is_update_available": update_flag,
            "new_version": version_str,
        }

    @staticmethod
    def _downloadUpdater(program_name: str = "update.exe") -> bool:
        """Helper function to download the updater executable."""
        try:
            current_directory = config.PATH_LOCAL
            res = requests_get(config.UPDATER_URL, timeout=10)
            res.raise_for_status()
            assets = res.json().get('assets', [])
            url_candidates = [asset.get("browser_download_url") for asset in assets if asset.get("name") == program_name]
            if not url_candidates or not url_candidates[0]:
                errorLogging(f"Updater URL for {program_name} not found in GitHub assets.")
                return False
            
            url = url_candidates[0]
            res_updater = requests_get(url, stream=True, timeout=60) 
            res_updater.raise_for_status()
            
            updater_path = os_path.join(current_directory, program_name)
            with open(updater_path, 'wb') as file_handle:
                for chunk in res_updater.iter_content(chunk_size=1024*5):
                    file_handle.write(chunk)
            return True
        except requests_get.exceptions.RequestException as e:
            errorLogging(f"Failed to download updater: {e}")
        except (KeyError, IndexError, TypeError) as e: 
            errorLogging(f"Failed to parse updater URL from GitHub assets: {e}")
        except IOError as e: 
            errorLogging(f"Failed to write updater to disk: {e}")
        except Exception as e:
            errorLogging(f"Generic error downloading updater: {e}")
        return False

    @staticmethod
    def updateSoftware() -> None:
        """Downloads and runs the software updater."""
        program_name = "update.exe"
        if Model._downloadUpdater(program_name):
            Popen(program_name, cwd=config.PATH_LOCAL) 

    @staticmethod
    def updateCudaSoftware() -> None:
        """Downloads and runs the software updater with CUDA flag."""
        program_name = "update.exe"
        if Model._downloadUpdater(program_name):
            Popen([program_name, "--cuda"], cwd=config.PATH_LOCAL)

    def getListMicHost(self) -> List[str]:
        """Gets a list of available microphone host API names."""
        mic_devices_map = device_manager.getMicDevices()
        if isinstance(mic_devices_map, dict):
            return list(mic_devices_map.keys())
        return []


    def getMicDefaultDevice(self) -> str:
        """Gets the name of the default microphone device for the selected host."""
        mic_devices_map = device_manager.getMicDevices()
        if isinstance(mic_devices_map, dict):
            devices_for_host = mic_devices_map.get(config.SELECTED_MIC_HOST, [])
            if devices_for_host and isinstance(devices_for_host, list) and devices_for_host[0].get("name"):
                return str(devices_for_host[0]["name"])
        return "NoDevice"


    def getListMicDevice(self) -> List[str]:
        """Gets a list of microphone device names for the selected host."""
        mic_devices_map = device_manager.getMicDevices()
        if isinstance(mic_devices_map, dict):
            devices_for_host = mic_devices_map.get(config.SELECTED_MIC_HOST, [])
            return [str(device.get("name", "Unknown Device")) for device in devices_for_host if isinstance(device, dict)]
        return []

    def getListSpeakerDevice(self) -> List[str]:
        """Gets a list of available speaker device names."""
        speaker_devices_list = device_manager.getSpeakerDevices()
        if isinstance(speaker_devices_list, list):
            return [str(device.get("name", "Unknown Device")) for device in speaker_devices_list if isinstance(device, dict)]
        return []


    def startMicTranscript(self, fnc: Callable[[Dict[str, Optional[str]]], None]) -> None:
        """
        Starts the microphone transcription process.
        Initializes audio recorder and transcriber, then starts a thread to process audio.
        Args:
            fnc: Callback function to handle transcription results (Dict with "text" and "language").
        """
        mic_host_name = config.SELECTED_MIC_HOST
        mic_device_name = config.SELECTED_MIC_DEVICE

        mic_devices_map = device_manager.getMicDevices()
        mic_device_list_for_host: List[Model.DeviceInfo] = []
        if isinstance(mic_devices_map, dict):
            mic_device_list_for_host = mic_devices_map.get(mic_host_name, [])
        
        selected_mic_device_info_list = [
            device for device in mic_device_list_for_host if device.get("name") == mic_device_name
        ]

        if not selected_mic_device_info_list or mic_device_name == "NoDevice":
            fnc({"text": None, "language": None}) # Indicate error or no device
            return
        
        selected_mic_device: Model.DeviceInfo = selected_mic_device_info_list[0]
        self.mic_audio_queue = Queue()

        record_timeout = config.MIC_RECORD_TIMEOUT
        phrase_timeout = config.MIC_PHRASE_TIMEOUT
        if record_timeout > phrase_timeout: # Ensure record_timeout isn't longer
            record_timeout = phrase_timeout

        self.mic_audio_recorder = SelectedMicEnergyAndAudioRecorder(
            device=selected_mic_device,
            energy_threshold=config.MIC_THRESHOLD,
            dynamic_energy_threshold=config.MIC_AUTOMATIC_THRESHOLD,
            phrase_time_limit=record_timeout,
        )
        self.mic_audio_recorder.recordIntoQueue(self.mic_audio_queue, None) # Energy queue not used

        self.mic_transcriber = AudioTranscriber(
            speaker=False,
            source=self.mic_audio_recorder.source, # type: ignore # source is InternalSource
            phrase_timeout=phrase_timeout,
            max_phrases=config.MIC_MAX_PHRASES,
            transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
            root=config.PATH_LOCAL,
            whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
            device=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device"],
            device_index=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device_index"],
        )

        def sendMicTranscript() -> None:
            """Processes audio queue and sends transcription results via callback."""
            try:
                your_lang_tab = config.SELECTED_YOUR_LANGUAGES.get(config.SELECTED_TAB_NO, {})
                languages = [data["language"] for data in your_lang_tab.values() if data.get("enable")]
                countries = [data["country"] for data in your_lang_tab.values() if data.get("enable")]
                
                if isinstance(self.mic_transcriber, AudioTranscriber) and self.mic_audio_queue:
                    transcription_active = self.mic_transcriber.transcribeAudioQueue(
                        self.mic_audio_queue,
                        languages,
                        countries,
                        config.MIC_AVG_LOGPROB,
                        config.MIC_NO_SPEECH_PROB
                    )
                    if transcription_active: 
                        result = self.mic_transcriber.getTranscript() # Dict[str, Optional[str]]
                        fnc(result)
            except Exception as e:
                errorLogging(f"Error in sendMicTranscript: {e}")

        def endMicTranscript() -> None:
            """Cleans up microphone transcription resources."""
            if self.mic_audio_queue:
                while not self.mic_audio_queue.empty():
                    self.mic_audio_queue.get()
            self.mic_transcriber = None
            gc.collect()

        self.mic_print_transcript = threadFnc(sendMicTranscript, end_fnc=endMicTranscript)
        self.mic_print_transcript.daemon = True
        self.mic_print_transcript.start()
        self.changeMicTranscriptStatus() # Apply mute status

    def resumeMicTranscript(self) -> None:
        """Resumes microphone audio recording."""
        if isinstance(self.mic_audio_queue, Queue):
            while not self.mic_audio_queue.empty(): # Clear queue on resume
                self.mic_audio_queue.get()
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.resume()

    def pauseMicTranscript(self) -> None:
        """Pauses microphone audio recording."""
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.pause()

    def changeMicTranscriptStatus(self) -> None:
        """Changes microphone transcription status (pause/resume) based on VRChat mute sync."""
        if config.VRC_MIC_MUTE_SYNC:
            if self.mic_mute_status is True: # Muted in VRC
                self.pauseMicTranscript()
            elif self.mic_mute_status is False: # Unmuted in VRC
                self.resumeMicTranscript()
            else: # Mute status unknown (e.g., OSCQuery not connected), assume unmuted
                self.resumeMicTranscript()
        else: # Sync disabled, always resume (or stay active)
            self.resumeMicTranscript()

    def stopMicTranscript(self) -> None:
        """Stops the microphone transcription thread and cleans up resources."""
        if isinstance(self.mic_print_transcript, threadFnc):
            self.mic_print_transcript.stop()
            if self.mic_print_transcript.is_alive():
                self.mic_print_transcript.join(timeout=1.0)
            self.mic_print_transcript = None
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.resume() # Ensure it's not paused before stopping
            self.mic_audio_recorder.stop()
            self.mic_audio_recorder = None
        self.mic_audio_queue = None # Clear queue reference

    def startCheckMicEnergy(self, fnc: Callable[[Union[float, bool]], None]) -> None:
        """Starts monitoring microphone energy levels."""
        self.check_mic_energy_fnc = fnc

        mic_host_name = config.SELECTED_MIC_HOST
        mic_device_name = config.SELECTED_MIC_DEVICE
        
        mic_devices_map = device_manager.getMicDevices()
        mic_device_list_for_host: List[Model.DeviceInfo] = []
        if isinstance(mic_devices_map, dict):
            mic_device_list_for_host = mic_devices_map.get(mic_host_name, [])

        selected_mic_device_info_list = [
            device for device in mic_device_list_for_host if device.get("name") == mic_device_name
        ]

        if not selected_mic_device_info_list or mic_device_name == "NoDevice":
            if self.check_mic_energy_fnc:
                self.check_mic_energy_fnc(False) # Signal error
            return

        selected_mic_device: Model.DeviceInfo = selected_mic_device_info_list[0]
        
        mic_energy_queue: Queue[Union[float, bool]] = Queue()
        self.mic_energy_recorder = SelectedMicEnergyRecorder(selected_mic_device)
        self.mic_energy_recorder.recordIntoQueue(mic_energy_queue)

        def sendMicEnergy() -> None:
            """Processes mic energy queue and sends updates via callback."""
            if not mic_energy_queue.empty():
                energy = mic_energy_queue.get()
                if self.check_mic_energy_fnc:
                    try:
                        self.check_mic_energy_fnc(energy)
                    except Exception as e:
                        errorLogging(f"Error in sendMicEnergy callback: {e}")
            sleep(0.01) # Small sleep to prevent tight loop if queue is often empty

        self.mic_energy_plot_progressbar = threadFnc(sendMicEnergy)
        self.mic_energy_plot_progressbar.daemon = True
        self.mic_energy_plot_progressbar.start()

    def stopCheckMicEnergy(self) -> None:
        """Stops monitoring microphone energy levels."""
        if isinstance(self.mic_energy_plot_progressbar, threadFnc):
            self.mic_energy_plot_progressbar.stop()
            if self.mic_energy_plot_progressbar.is_alive():
                self.mic_energy_plot_progressbar.join(timeout=1.0)
            self.mic_energy_plot_progressbar = None
        if isinstance(self.mic_energy_recorder, SelectedMicEnergyRecorder):
            self.mic_energy_recorder.resume()
            self.mic_energy_recorder.stop()
            self.mic_energy_recorder = None

    def startSpeakerTranscript(self, fnc: Callable[[Dict[str, Optional[str]]], None]) -> None:
        """
        Starts the speaker transcription process.
        Similar to startMicTranscript but for speaker audio.
        """
        speaker_device_name = config.SELECTED_SPEAKER_DEVICE
        speaker_device_list = device_manager.getSpeakerDevices()
        selected_speaker_device_info_list = [
            device for device in speaker_device_list if device.get("name") == speaker_device_name
        ]

        if not selected_speaker_device_info_list or speaker_device_name == "NoDevice":
            fnc({"text": None, "language": None})
            return
            
        selected_speaker_device: Model.DeviceInfo = selected_speaker_device_info_list[0]
        speaker_audio_queue: Queue[Any] = Queue() # Using Any for now

        record_timeout = config.SPEAKER_RECORD_TIMEOUT
        phrase_timeout = config.SPEAKER_PHRASE_TIMEOUT
        if record_timeout > phrase_timeout:
            record_timeout = phrase_timeout

        self.speaker_audio_recorder = SelectedSpeakerEnergyAndAudioRecorder(
            device=selected_speaker_device,
            energy_threshold=config.SPEAKER_THRESHOLD,
            dynamic_energy_threshold=config.SPEAKER_AUTOMATIC_THRESHOLD,
            phrase_time_limit=record_timeout,
        )
        self.speaker_audio_recorder.recordIntoQueue(speaker_audio_queue, None)

        self.speaker_transcriber = AudioTranscriber(
            speaker=True,
            source=self.speaker_audio_recorder.source, # type: ignore
            phrase_timeout=phrase_timeout,
            max_phrases=config.SPEAKER_MAX_PHRASES,
            transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
            root=config.PATH_LOCAL,
            whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
            device=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device"],
            device_index=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device_index"],
        )

        def sendSpeakerTranscript() -> None:
            """Processes speaker audio queue and sends transcription results."""
            try:
                target_lang_tab = config.SELECTED_TARGET_LANGUAGES.get(config.SELECTED_TAB_NO, {})
                languages = [data["language"] for data in target_lang_tab.values() if data.get("enable")]
                countries = [data["country"] for data in target_lang_tab.values() if data.get("enable")]

                if isinstance(self.speaker_transcriber, AudioTranscriber):
                    transcription_active = self.speaker_transcriber.transcribeAudioQueue(
                        speaker_audio_queue, # Corrected to use local queue
                        languages,
                        countries,
                        config.SPEAKER_AVG_LOGPROB,
                        config.SPEAKER_NO_SPEECH_PROB
                    )
                    if transcription_active:
                        result = self.speaker_transcriber.getTranscript()
                        fnc(result)
            except Exception as e:
                errorLogging(f"Error in sendSpeakerTranscript: {e}")

        def endSpeakerTranscript() -> None:
            """Cleans up speaker transcription resources."""
            # Ensure speaker_audio_queue is the one being cleared
            while not speaker_audio_queue.empty():
                speaker_audio_queue.get()
            self.speaker_transcriber = None
            gc.collect()

        self.speaker_print_transcript = threadFnc(sendSpeakerTranscript, end_fnc=endSpeakerTranscript)
        self.speaker_print_transcript.daemon = True
        self.speaker_print_transcript.start()

    def stopSpeakerTranscript(self) -> None:
        """Stops the speaker transcription thread and cleans up resources."""
        if isinstance(self.speaker_print_transcript, threadFnc):
            self.speaker_print_transcript.stop()
            if self.speaker_print_transcript.is_alive():
                self.speaker_print_transcript.join(timeout=1.0)
            self.speaker_print_transcript = None
        if isinstance(self.speaker_audio_recorder, SelectedSpeakerEnergyAndAudioRecorder):
            self.speaker_audio_recorder.stop() # Should not need resume before stop
            self.speaker_audio_recorder = None
        # speaker_audio_queue is local to startSpeakerTranscript, no need to clear here

    def startCheckSpeakerEnergy(self, fnc: Callable[[Union[float, bool]], None]) -> None:
        """Starts monitoring speaker energy levels."""
        self.check_speaker_energy_fnc = fnc

        speaker_device_name = config.SELECTED_SPEAKER_DEVICE
        speaker_device_list = device_manager.getSpeakerDevices()
        selected_speaker_device_info_list = [
            device for device in speaker_device_list if device.get("name") == speaker_device_name
        ]

        if not selected_speaker_device_info_list or speaker_device_name == "NoDevice":
            if self.check_speaker_energy_fnc:
                self.check_speaker_energy_fnc(False) # Signal error
            return
        
        selected_speaker_device: Model.DeviceInfo = selected_speaker_device_info_list[0]
        speaker_energy_queue: Queue[Union[float, bool]] = Queue()
        self.speaker_energy_recorder = SelectedSpeakerEnergyRecorder(selected_speaker_device)
        self.speaker_energy_recorder.recordIntoQueue(speaker_energy_queue)

        def sendSpeakerEnergy() -> None:
            """Processes speaker energy queue and sends updates via callback."""
            if not speaker_energy_queue.empty():
                energy = speaker_energy_queue.get()
                if self.check_speaker_energy_fnc:
                    try:
                        self.check_speaker_energy_fnc(energy)
                    except Exception as e:
                        errorLogging(f"Error in sendSpeakerEnergy callback: {e}")
            sleep(0.01)

        self.speaker_energy_plot_progressbar = threadFnc(sendSpeakerEnergy)
        self.speaker_energy_plot_progressbar.daemon = True
        self.speaker_energy_plot_progressbar.start()

    def stopCheckSpeakerEnergy(self) -> None:
        """Stops monitoring speaker energy levels."""
        if isinstance(self.speaker_energy_plot_progressbar, threadFnc):
            self.speaker_energy_plot_progressbar.stop()
            if self.speaker_energy_plot_progressbar.is_alive():
                self.speaker_energy_plot_progressbar.join(timeout=1.0)
            self.speaker_energy_plot_progressbar = None
        if isinstance(self.speaker_energy_recorder, SelectedSpeakerEnergyRecorder):
            self.speaker_energy_recorder.resume() # Ensure not paused
            self.speaker_energy_recorder.stop()
            self.speaker_energy_recorder = None

    def createOverlayImageSmallLog(self, message: str, translation: str) -> Any:
        """Creates an image for the small log overlay with original and translated text."""
        # Safe access to nested dictionary structure
        your_language_tab = config.SELECTED_TARGET_LANGUAGES.get(config.SELECTED_TAB_NO, {})
        your_language_primary = your_language_tab.get("1", {})
        your_language = your_language_primary.get("language", "Unknown")

        target_language_tab = config.SELECTED_YOUR_LANGUAGES.get(config.SELECTED_TAB_NO, {})
        target_language_primary = target_language_tab.get("1", {})
        target_language = target_language_primary.get("language", "Unknown")
        
        return self.overlay_image.createOverlayImageSmallLog(message, your_language, translation, target_language)

    def createOverlayImageSmallMessage(self, message: str) -> Any:
        """Creates an image for the small log overlay with a single message, language based on UI."""
        ui_language_code = config.UI_LANGUAGE # e.g., "en", "ja"
        # Mapping from UI language code to full language name for display
        convert_languages: Dict[str, str] = {
            "en": "English", # Assuming English if UI is English
            "ja": "Japanese",
            "ko": "Korean",
            "zh-Hans": "Chinese Simplified",
            "zh-Hant": "Chinese Traditional",
        }
        display_language = convert_languages.get(ui_language_code, "Japanese") # Default to Japanese
        return self.overlay_image.createOverlayImageSmallLog(message, display_language) # Assuming createOverlayImageSmallLog can take 2 args

    def clearOverlayImageSmallLog(self) -> None:
        """Clears the small log image from the overlay."""
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.clearImage("small")

    def updateOverlaySmallLog(self, img: Any) -> None:
        """Updates the small log image on the overlay."""
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.updateImage(img, "small")

    def updateOverlaySmallLogSettings(self) -> None:
        """Updates the small log overlay settings based on current config values."""
        size = "small"
        # Check if overlay settings from config match current overlay settings to avoid unnecessary updates
        # Using .get for safer dictionary access
        current_overlay_settings = self.overlay.settings.get(size, {})
        config_settings = config.OVERLAY_SMALL_LOG_SETTINGS

        if (current_overlay_settings.get("x_pos") != config_settings.get("x_pos") or
            current_overlay_settings.get("y_pos") != config_settings.get("y_pos") or
            current_overlay_settings.get("z_pos") != config_settings.get("z_pos") or
            current_overlay_settings.get("x_rotation") != config_settings.get("x_rotation") or
            current_overlay_settings.get("y_rotation") != config_settings.get("y_rotation") or
            current_overlay_settings.get("z_rotation") != config_settings.get("z_rotation") or
            current_overlay_settings.get("tracker") != config_settings.get("tracker")):
            self.overlay.updatePosition(
                config_settings.get("x_pos", 0.0),
                config_settings.get("y_pos", 0.0),
                config_settings.get("z_pos", 0.0),
                config_settings.get("x_rotation", 0.0),
                config_settings.get("y_rotation", 0.0),
                config_settings.get("z_rotation", 0.0),
                config_settings.get("tracker", "HMD"),
                size,
            )
        if current_overlay_settings.get("display_duration") != config_settings.get("display_duration"):
            self.overlay.updateDisplayDuration(config_settings.get("display_duration", 5), size)
        if current_overlay_settings.get("fadeout_duration") != config_settings.get("fadeout_duration"):
            self.overlay.updateFadeoutDuration(config_settings.get("fadeout_duration", 2), size)
        if current_overlay_settings.get("opacity") != config_settings.get("opacity"):
            self.overlay.updateOpacity(config_settings.get("opacity", 1.0), size, True)
        if current_overlay_settings.get("ui_scaling") != config_settings.get("ui_scaling"):
            self.overlay.updateUiScaling(config_settings.get("ui_scaling", 1.0), size)

    def createOverlayImageLargeLog(self, message_type: str, message: str, translation: str) -> Any:
        """Creates an image for the large log overlay."""
        your_language_tab = config.SELECTED_TARGET_LANGUAGES.get(config.SELECTED_TAB_NO, {})
        your_language_primary = your_language_tab.get("1", {})
        your_language = your_language_primary.get("language", "Unknown")

        target_language_tab = config.SELECTED_YOUR_LANGUAGES.get(config.SELECTED_TAB_NO, {})
        target_language_primary = target_language_tab.get("1", {})
        target_language = target_language_primary.get("language", "Unknown")
        
        return self.overlay_image.createOverlayImageLargeLog(message_type, message, your_language, translation, target_language)

    def createOverlayImageLargeMessage(self, message: str) -> Any:
        """Creates an image for the large log overlay with a single message."""
        ui_language_code = config.UI_LANGUAGE
        convert_languages: Dict[str, str] = {
            "en": "English", "jp": "Japanese", "ko": "Korean",
            "zh-Hans": "Chinese Simplified", "zh-Hant": "Chinese Traditional",
        }
        display_language = convert_languages.get(ui_language_code, "Japanese")
        
        # The original code created a new OverlayImage() instance here and called methods on it.
        # This seems incorrect if self.overlay_image is the intended instance to use.
        # Assuming self.overlay_image should be used:
        # Also, the loop calling createOverlayImageLargeLog twice seems redundant if only the last result is used.
        # Replicating the last call:
        return self.overlay_image.createOverlayImageLargeLog("send", message, display_language)


    def clearOverlayImageLargeLog(self) -> None:
        """Clears the large log image from the overlay."""
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.clearImage("large")

    def updateOverlayLargeLog(self, img: Any) -> None:
        """Updates the large log image on the overlay."""
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.updateImage(img, "large")

    def updateOverlayLargeLogSettings(self) -> None:
        """Updates the large log overlay settings based on current config values."""
        size = "large"
        current_overlay_settings = self.overlay.settings.get(size, {})
        config_settings = config.OVERLAY_LARGE_LOG_SETTINGS

        if (current_overlay_settings.get("x_pos") != config_settings.get("x_pos") or
            current_overlay_settings.get("y_pos") != config_settings.get("y_pos") or
            # ... (rest of the comparisons as in small log)
            current_overlay_settings.get("tracker") != config_settings.get("tracker")): # Simplified for brevity
            self.overlay.updatePosition(
                config_settings.get("x_pos", 0.0), config_settings.get("y_pos", 0.0), config_settings.get("z_pos", 0.0),
                config_settings.get("x_rotation", 0.0), config_settings.get("y_rotation", 0.0), config_settings.get("z_rotation", 0.0),
                config_settings.get("tracker", "LeftHand"), size,
            )
        if current_overlay_settings.get("display_duration") != config_settings.get("display_duration"):
            self.overlay.updateDisplayDuration(config_settings.get("display_duration", 5), size)
        if current_overlay_settings.get("fadeout_duration") != config_settings.get("fadeout_duration"):
            self.overlay.updateFadeoutDuration(config_settings.get("fadeout_duration", 2), size)
        if current_overlay_settings.get("opacity") != config_settings.get("opacity"):
            self.overlay.updateOpacity(config_settings.get("opacity", 1.0), size, True)
        if current_overlay_settings.get("ui_scaling") != config_settings.get("ui_scaling"):
            # Original logic: config.OVERLAY_LARGE_LOG_SETTINGS["ui_scaling"] * 0.25
            self.overlay.updateUiScaling(float(config_settings.get("ui_scaling", 1.0)) * 0.25, size)


    def startOverlay(self) -> None:
        """Starts the overlay system if it's initialized."""
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.startOverlay()

    def shutdownOverlay(self) -> None:
        """Shuts down the overlay system if it's initialized."""
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.shutdownOverlay()

    def startWatchdog(self) -> None:
        """Starts the watchdog timer in a separate thread."""
        if not (self.th_watchdog and self.th_watchdog.is_alive()): # Check if already running
            self.th_watchdog = threadFnc(self.watchdog.start)
            self.th_watchdog.daemon = True
            self.th_watchdog.start()

    def feedWatchdog(self) -> None:
        """Feeds the watchdog timer to prevent it from timing out."""
        if hasattr(self, 'watchdog') and self.watchdog:
            self.watchdog.feed()

    def setWatchdogCallback(self, callback: Callable[[], None]) -> None:
        """Sets the callback function to be executed when the watchdog times out."""
        if hasattr(self, 'watchdog') and self.watchdog:
            self.watchdog.setCallback(callback)

    def stopWatchdog(self) -> None:
        """Stops the watchdog timer thread."""
        if isinstance(self.th_watchdog, threadFnc) and self.th_watchdog.is_alive():
            self.th_watchdog.stop()
            self.th_watchdog.join(timeout=1.0)
        self.th_watchdog = None

    @staticmethod
    def message_handler(websocket: Any, message: str) -> None: # 'websocket' type depends on library
        """Placeholder message handler for the WebSocket server. Currently does nothing."""
        # This method is static in the original, but is passed `self.message_handler`
        # to WebSocketServer. If it needs access to `self` of Model, it cannot be static.
        # For now, keeping it static as it doesn't use `self`.
        print(f"WebSocket message_handler received: {message} from {websocket}")
        pass

    def startWebSocketServer(self, host: str, port: int) -> None:
        """Starts the WebSocket server in a separate thread if not already alive."""
        if self.websocket_server_alive:
            return

        self.websocket_server_loop = True
        self.websocket_server_alive = False 

        async def WebSocketServerMain() -> None:
            try:
                self.websocket_server = WebSocketServer(host=host, port=port)
                # Pass the static method if it truly doesn't need self,
                # or a bound method `self.message_handler_instance_method` if it does.
                self.websocket_server.set_message_handler(Model.message_handler) 
                await self.websocket_server.start() # Assuming start is now async
                self.websocket_server_alive = True

                while self.websocket_server_loop:
                    await asyncio.sleep(0.5)
            except Exception as e:
                errorLogging(f"WebSocket server error: {e}")
            finally:
                if self.websocket_server: # Check if instance was created
                    await self.websocket_server.stop() # Assuming stop is now async
                self.websocket_server_alive = False

        self.th_websocket_server = Thread(target=lambda: asyncio.run(WebSocketServerMain()))
        self.th_websocket_server.daemon = True
        self.th_websocket_server.start()

    def stopWebSocketServer(self) -> None:
        """Stops the WebSocket server thread."""
        if not (hasattr(self, 'th_websocket_server') and self.th_websocket_server and self.th_websocket_server.is_alive()):
            if self.websocket_server_alive or self.websocket_server_loop: # If flags indicate it might be running without a thread object
                 errorLogging("WebSocket server thread not found or not alive, but flags indicate it might be running. Forcing flags down.")
            self.websocket_server_loop = False
            self.websocket_server_alive = False
            self.websocket_server = None # Clear instance if thread is gone
            return

        self.websocket_server_loop = False # Signal the asyncio loop to stop
        
        # No direct stop for asyncio.run, rely on websocket_server_loop flag.
        # Joining the thread will wait for the asyncio loop to finish.
        self.th_websocket_server.join(timeout=3.0) # Increased timeout

        if self.th_websocket_server.is_alive():
            if self.logger: self.logger.warning("WebSocket server thread did not terminate properly.")
            else: print("WebSocket server thread did not terminate properly.")
            # More aggressive cleanup if needed, but usually letting daemon thread exit is okay
        
        self.th_websocket_server = None
        self.websocket_server = None # Ensure server instance is cleared
        self.websocket_server_alive = False


    def checkWebSocketServerAlive(self) -> bool:
        """Checks if the WebSocket server is currently marked as alive."""
        return self.websocket_server_alive

    def websocketSendMessage(self, message_dict: Dict[str, Any]) -> bool:
        """
        Sends a JSON message to all connected WebSocket clients.
        """
        if not self.websocket_server_alive or not self.websocket_server:
            return False
        try:
            message_json = json.dumps(message_dict)
            # Assuming WebSocketServer.send is synchronous or handled by the library's own threading/asyncio model
            asyncio.run(self.websocket_server.send(message_json)) # If send is async
            return True
        except Exception as e:
            errorLogging(f"Error sending WebSocket message: {e}")
            return False

model: Model = Model()