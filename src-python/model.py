import copy
import gc
import asyncio
import json
from subprocess import Popen
from os import makedirs as os_makedirs
from os import path as os_path
from datetime import datetime
from time import sleep
from queue import Queue
from threading import Thread
from requests import get as requests_get
from typing import Callable, Optional, cast
from packaging.version import parse

from flashtext import KeywordProcessor

from device_manager import device_manager
from config import config

from models.translation.translation_translator import Translator
from models.osc.osc import OSCHandler
from models.transcription.transcription_recorder import SelectedMicEnergyAndAudioRecorder, SelectedSpeakerEnergyAndAudioRecorder
from models.transcription.transcription_recorder import SelectedMicEnergyRecorder, SelectedSpeakerEnergyRecorder
from models.transcription.transcription_transcriber import AudioTranscriber
from models.translation.translation_languages import translation_lang
from models.transcription.transcription_languages import transcription_lang
from models.translation.translation_utils import checkCTranslate2Weight, downloadCTranslate2Weight, downloadCTranslate2Tokenizer
from models.transcription.transcription_whisper import checkWhisperWeight, downloadWhisperWeight
from models.transliteration.transliteration_transliterator import Transliterator
from models.overlay.overlay import Overlay
from models.overlay.overlay_image import OverlayImage
from models.watchdog.watchdog import Watchdog
from models.websocket.websocket_server import WebSocketServer
from models.clipboard.clipboard import Clipboard
from utils import errorLogging, setupLogger

class threadFnc(Thread):
    """A tiny Thread wrapper that repeatedly calls a function.

    Usage: threadFnc(fnc, end_fnc=None, daemon=True, *args, **kwargs)
    The target function will be called repeatedly inside run().
    """
    def __init__(self, fnc, end_fnc=None, daemon: bool = True, *args, **kwargs):
        # Do not pass target to super; manage call explicitly so we can
        # store args/kwargs on the instance for later use.
        super(threadFnc, self).__init__(daemon=daemon)
        self.fnc = fnc
        self.end_fnc = end_fnc
        self.loop = True
        self._pause = False
        self._args = args
        self._kwargs = kwargs

    def stop(self) -> None:
        self.loop = False

    def pause(self) -> None:
        self._pause = True

    def resume(self) -> None:
        self._pause = False

    def run(self) -> None:
        try:
            while self.loop:
                try:
                    self.fnc(*self._args, **self._kwargs)
                except Exception:
                    # Protect the thread from terminating on user exceptions
                    errorLogging()
                while self._pause:
                    sleep(0.1)
        finally:
            if callable(self.end_fnc):
                try:
                    self.end_fnc()
                except Exception:
                    errorLogging()
        return

class Model:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Model, cls).__new__(cls)
            # Do NOT call init() here to avoid heavy import-time work.
            # Callers should call `model.init()` explicitly or rely on
            # `ensure_initialized()` which will lazy-initialize on demand.
            cls._instance._inited = False
        return cls._instance

    def init(self):
        """Perform full initialization of resources.

        This method performs heavy construction (models, overlay, threads)
        and is intentionally not called at import time. Call explicitly
        or let `ensure_initialized()` call it lazily.
        """
        if getattr(self, '_inited', False):
            return

        self.logger = None
        self.th_check_device = None
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
        self.translation_history: list[dict] = []
        self.translation_history_max_items = 20
        overlay_small_log_settings = copy.deepcopy(config.OVERLAY_SMALL_LOG_SETTINGS)
        overlay_large_log_settings = copy.deepcopy(config.OVERLAY_LARGE_LOG_SETTINGS)
        overlay_large_log_settings["ui_scaling"] = overlay_large_log_settings["ui_scaling"] * 0.25
        overlay_settings = {
            "small": overlay_small_log_settings,
            "large": overlay_large_log_settings,
        }
        self.overlay = Overlay(overlay_settings)
        self.overlay_image = OverlayImage(config.PATH_LOCAL)
        self.mic_audio_queue = None
        self.mic_mute_status = None
        self.transliterator = None
        self.watchdog = Watchdog(config.WATCHDOG_TIMEOUT, config.WATCHDOG_INTERVAL)
        self.osc_handler = OSCHandler(config.OSC_IP_ADDRESS, config.OSC_PORT)
        self.websocket_server = None
        self.websocket_server_loop = False
        self.websocket_server_alive = False
        self.th_websocket_server = None
        # default no-op callbacks for energy check functions
        self.check_mic_energy_fnc: Callable[[float], None] = lambda v: None
        self.check_speaker_energy_fnc: Callable[[float], None] = lambda v: None
        self.clipboard = Clipboard()
        self._inited = True

    def ensure_initialized(self) -> None:
        """Ensure the model has been initialized. This is safe to call from
        public methods that require initialized resources.
        """
        if not getattr(self, '_inited', False):
            try:
                self.init()
            except Exception:
                # Log and continue; callers should handle missing features.
                errorLogging()

    def checkTranslatorCTranslate2ModelWeight(self, weight_type:str):
        return checkCTranslate2Weight(config.PATH_LOCAL, weight_type)

    def changeTranslatorCTranslate2Model(self):
        self.ensure_initialized()
        self.translator.changeCTranslate2Model(
            path=config.PATH_LOCAL,
            model_type=config.CTRANSLATE2_WEIGHT_TYPE,
            device=config.SELECTED_TRANSLATION_COMPUTE_DEVICE["device"],
            device_index=config.SELECTED_TRANSLATION_COMPUTE_DEVICE["device_index"],
            compute_type=config.SELECTED_TRANSLATION_COMPUTE_TYPE
            )

    def downloadCTranslate2ModelWeight(self, weight_type, callback=None, end_callback=None):
        return downloadCTranslate2Weight(config.PATH_LOCAL, weight_type, callback, end_callback)

    def downloadCTranslate2ModelTokenizer(self, weight_type):
        return downloadCTranslate2Tokenizer(config.PATH_LOCAL, weight_type)

    def isLoadedCTranslate2Model(self):
        self.ensure_initialized()
        return self.translator.isLoadedCTranslate2Model()

    def isChangedTranslatorParameters(self):
        self.ensure_initialized()
        return self.translator.isChangedTranslatorParameters()

    def setChangedTranslatorParameters(self, is_changed):
        self.ensure_initialized()
        self.translator.setChangedTranslatorParameters(is_changed)

    def checkTranscriptionWhisperModelWeight(self, weight_type:str):
        return checkWhisperWeight(config.PATH_LOCAL, weight_type)

    def downloadWhisperModelWeight(self, weight_type, callback=None, end_callback=None):
        return downloadWhisperWeight(config.PATH_LOCAL, weight_type, callback, end_callback)

    def resetKeywordProcessor(self):
        self.ensure_initialized()
        del self.keyword_processor
        self.keyword_processor = KeywordProcessor()

    def authenticationTranslatorDeepLAuthKey(self, auth_key: str) -> bool:
        self.ensure_initialized()
        result = self.translator.authenticationDeepLAuthKey(auth_key)
        return result

    def authenticationTranslatorPlamoAuthKey(self, auth_key: str) -> bool:
        result = self.translator.authenticationPlamoAuthKey(auth_key, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorPlamoModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getPlamoModelList()

    def setTranslatorPlamoModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setPlamoModel(model=model)
        return result

    def updateTranslatorPlamoClient(self) -> None:
        self.ensure_initialized()
        self.translator.updatePlamoClient()

    def authenticationTranslatorGeminiAuthKey(self, auth_key: str) -> bool:
        result = self.translator.authenticationGeminiAuthKey(auth_key, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorGeminiModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getGeminiModelList()

    def setTranslatorGeminiModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setGeminiModel(model=model)
        return result

    def updateTranslatorGeminiClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateGeminiClient()

    def authenticationTranslatorOpenAIAuthKey(self, auth_key: str, base_url: Optional[str] = None) -> bool:
        result = self.translator.authenticationOpenAIAuthKey(auth_key, base_url=base_url, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorOpenAIModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getOpenAIModelList()

    def setTranslatorOpenAIModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setOpenAIModel(model=model)
        return result

    def updateTranslatorOpenAIClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateOpenAIClient()

    def authenticationTranslatorGroqAuthKey(self, auth_key: str) -> bool:
        result = self.translator.authenticationGroqAuthKey(auth_key, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorGroqModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getGroqModelList()

    def setTranslatorGroqModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setGroqModel(model=model)
        return result

    def updateTranslatorGroqClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateGroqClient()

    def authenticationTranslatorOpenRouterAuthKey(self, auth_key: str) -> bool:
        result = self.translator.authenticationOpenRouterAuthKey(auth_key, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorOpenRouterModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getOpenRouterModelList()

    def setTranslatorOpenRouterModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setOpenRouterModel(model=model)
        return result

    def updateTranslatorOpenRouterClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateOpenRouterClient()

    def getTranslatorLMStudioConnected(self) -> bool:
        self.ensure_initialized()
        return self.translator.getLMStudioConnected()

    def authenticationTranslatorLMStudio(self, base_url: str) -> bool:
        result = self.translator.setLMStudioClientURL(base_url=base_url, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorLMStudioModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getLMStudioModelList()

    def setTranslatorLMStudioModel(self, model: str) -> bool:
        self.ensure_initialized()
        return self.translator.setLMStudioModel(model=model)

    def updateTranslatorLMStudioClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateLMStudioClient()

    def getTranslatorOllamaConnected(self) -> bool:
        self.ensure_initialized()
        return self.translator.getOllamaConnected()

    def authenticationTranslatorOllama(self) -> bool:
        result = self.translator.checkOllamaClient(root_path=config.PATH_LOCAL)
        return result

    def getTranslatorOllamaModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getOllamaModelList()

    def setTranslatorOllamaModel(self, model: str) -> bool:
        self.ensure_initialized()
        return self.translator.setOllamaModel(model=model)

    def updateTranslatorOllamaClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateOllamaClient()

    def startLogger(self):
        self.ensure_initialized()
        os_makedirs(config.PATH_LOGS, exist_ok=True)
        file_name = os_path.join(config.PATH_LOGS, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
        self.logger = setupLogger("log", file_name)
        self.logger.disabled = False

    def stopLogger(self):
        self.ensure_initialized()
        self.logger.disabled = True
        self.logger = None

    def getListLanguageAndCountry(self):
        transcription_langs = list(transcription_lang.keys())
        translation_langs = []
        for tl_key in translation_lang.keys():
            if tl_key == "CTranslate2":
                for lang in translation_lang[tl_key][config.CTRANSLATE2_WEIGHT_TYPE]["source"]:
                    translation_langs.append(lang)
            else:
                for lang in translation_lang[tl_key]["source"]:
                    translation_langs.append(lang)
        translation_langs = list(set(translation_langs))
        supported_langs = list(filter(lambda x: x in transcription_langs, translation_langs))

        languages = []
        for language in supported_langs:
            for country in transcription_lang[language]:
                languages.append(
                    {
                        "language" : language,
                        "country" : country,
                    }
                )
        languages = sorted(languages, key=lambda x: x['language'])
        return languages

    def findTranslationEngines(self, source_lang, target_lang, engines_status):
        selectable_engines = [key for key, value in engines_status.items() if value is True]
        compatible_engines = []
        for engine in list(translation_lang.keys()):
            if engine == "CTranslate2":
                languages = translation_lang.get(engine, {}).get(config.CTRANSLATE2_WEIGHT_TYPE, {}).get("source", {})
            else:
                languages = translation_lang.get(engine, {}).get("source", {})
            source_langs = [e["language"] for e in list(source_lang.values()) if e["enable"] is True]
            target_langs = [e["language"] for e in list(target_lang.values()) if e["enable"] is True]
            language_list = list(languages.keys())

            if all(e in language_list for e in source_langs) and all(e in language_list for e in target_langs):
                if engine in selectable_engines:
                    compatible_engines.append(engine)

        return compatible_engines

    def addTranslationHistory(self, source: str, text: str) -> None:
        """Add a message to translation context history.
        
        Args:
            source: "chat" | "mic" | "speaker"
            text: message content
        """
        self.ensure_initialized()
        if not text or not text.strip():
            return
        
        history_item = {
            "source": source,
            "text": text.strip(),
            "timestamp": datetime.now().isoformat(),
        }
        self.translation_history.append(history_item)
        
        # 最大件数を超えた場合は古いものを削除
        if len(self.translation_history) > self.translation_history_max_items:
            self.translation_history = self.translation_history[-self.translation_history_max_items:]
    
    def getTranslationHistory(self, max_items: int = None) -> list[dict]:
        """Get recent translation context history.
        
        Args:
            max_items: Maximum number of items to return (newest first)
        
        Returns:
            List of history items
        """
        self.ensure_initialized()
        if max_items is None or max_items <= 0:
            return self.translation_history
        return self.translation_history[-max_items:]
    
    def clearTranslationHistory(self) -> None:
        """Clear all translation context history."""
        self.ensure_initialized()
        self.translation_history = []

    def getTranslate(self, translator_name, source_language, target_language, target_country, message):
        self.ensure_initialized()
        success_flag = False
        
        # Get context history for LLM-based translators
        history = self.getTranslationHistory()
        
        translation = self.translator.translate(
                        translator_name=translator_name,
                        weight_type=config.CTRANSLATE2_WEIGHT_TYPE,
                        source_language=source_language,
                        target_language=target_language,
                        target_country=target_country,
                        message=message,
                        context_history=history
                )

        # 翻訳失敗時のフェールセーフ処理
        if isinstance(translation, str):
            success_flag = True
        else:
            while True:
                translation = self.translator.translate(
                                    translator_name="CTranslate2",
                                    weight_type=config.CTRANSLATE2_WEIGHT_TYPE,
                                    source_language=source_language,
                                    target_language=target_language,
                                    target_country=target_country,
                                    message=message
                            )
                if translation is not False:
                    break
                sleep(0.1)
        return translation, success_flag

    def getInputTranslate(self, message, source_language=None):
        self.ensure_initialized()
        translator_name=config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO]
        if source_language is None:
            source_language=config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"]
        target_languages=config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]

        translations = []
        success_flags = []
        for value in target_languages.values():
            if value["enable"] is True:
                target_language = value["language"]
                target_country = value["country"]
                if target_language is not None or target_country is not None:
                    translation, success_flag = self.getTranslate(
                        translator_name,
                        source_language,
                        target_language,
                        target_country,
                        message
                        )
                    translations.append(translation)
                    success_flags.append(success_flag)

        return translations, success_flags

    def getOutputTranslate(self, message, source_language=None):
        self.ensure_initialized()
        translator_name=config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO]
        if source_language is None:
            source_language=config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"]
        target_language=config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"]
        target_country=config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["country"]

        translation, success_flag = self.getTranslate(
            translator_name,
            source_language,
            target_language,
            target_country,
            message
            )
        return [translation], [success_flag]

    def addKeywords(self):
        self.ensure_initialized()
        for f in config.MIC_WORD_FILTER:
            self.keyword_processor.add_keyword(f)

    def checkKeywords(self, message):
        self.ensure_initialized()
        return len(self.keyword_processor.extract_keywords(message)) != 0

    def detectRepeatSendMessage(self, message):
        repeat_flag = False
        if self.previous_send_message == message:
            repeat_flag = True
        self.previous_send_message = message
        return repeat_flag

    def detectRepeatReceiveMessage(self, message):
        repeat_flag = False
        if self.previous_receive_message == message:
            repeat_flag = True
        self.previous_receive_message = message
        return repeat_flag

    def startTransliteration(self):
        self.ensure_initialized()
        if self.transliterator is None:
            self.transliterator = Transliterator()

    def stopTransliteration(self):
        self.ensure_initialized()
        if self.transliterator is not None:
            self.transliterator = None

    def convertMessageToTransliteration(self, message: str, hiragana: bool=True, romaji: bool=True) -> list:
        self.ensure_initialized()
        if hiragana is False and romaji is False:
            return []

        keys_to_keep = {"orig"}
        if hiragana:
            keys_to_keep.add("hira")
        if romaji:
            keys_to_keep.add("hepburn")

        if self.transliterator is None:
            self.startTransliteration()

        data_list = self.transliterator.analyze(message, use_macron=False)
        filtered_list = [
            {key: value for key, value in item.items() if key in keys_to_keep}
            for item in data_list
        ]
        return filtered_list

    def setOscIpAddress(self, ip_address):
        self.ensure_initialized()
        self.osc_handler.setOscIpAddress(ip_address)

    def setOscPort(self, port):
        self.ensure_initialized()
        self.osc_handler.setOscPort(port)

    def oscStartSendTyping(self):
        self.ensure_initialized()
        self.osc_handler.sendTyping(flag=True)

    def oscStopSendTyping(self):
        self.ensure_initialized()
        self.osc_handler.sendTyping(flag=False)

    def oscSendMessage(self, message:str):
        self.ensure_initialized()
        self.osc_handler.sendMessage(message=message, notification=config.NOTIFICATION_VRC_SFX)

    def setMuteSelfStatus(self):
        self.ensure_initialized()
        self.mic_mute_status = self.osc_handler.getOSCParameterMuteSelf()

    def startReceiveOSC(self):
        self.ensure_initialized()
        def changeHandlerMute(address, osc_arguments):
            if config.ENABLE_TRANSCRIPTION_SEND is True:
                if osc_arguments is True and self.mic_mute_status is False:
                    self.mic_mute_status = osc_arguments
                    self.changeMicTranscriptStatus()
                elif osc_arguments is False and self.mic_mute_status is True:
                    self.mic_mute_status = osc_arguments
                    self.changeMicTranscriptStatus()

        dict_filter_and_target = {
            self.osc_handler.osc_parameter_muteself: changeHandlerMute,
        }
        self.osc_handler.setDictFilterAndTarget(dict_filter_and_target)
        self.osc_handler.receiveOscParameters()

    def stopReceiveOSC(self):
        self.ensure_initialized()
        self.osc_handler.oscServerStop()

    def getIsOscQueryEnabled(self):
        self.ensure_initialized()
        return self.osc_handler.getIsOscQueryEnabled()

    @staticmethod
    def checkSoftwareUpdated():
        # check update
        update_flag = False
        version = ""
        try:
            response = requests_get(config.GITHUB_URL)
            json_data = response.json()
            version = json_data.get("name", None)
            if isinstance(version, str):
                new_version = parse(version)
                current_version = parse(config.VERSION)
                if new_version > current_version:
                    update_flag = True
        except Exception:
            errorLogging()
        return {
            "is_update_available": update_flag,
            "new_version": version,
        }

    @staticmethod
    def updateSoftware():
        # try to update at most 5 times
        for _ in range(5):
            try:
                program_name = "update.exe"
                current_directory = config.PATH_LOCAL
                res = requests_get(config.UPDATER_URL)
                assets = res.json()['assets']
                url = [i["browser_download_url"] for i in assets if i["name"] == program_name][0]
                res = requests_get(url, stream=True)
                with open(os_path.join(current_directory, program_name), 'wb') as file:
                    for chunk in res.iter_content(chunk_size=1024*5):
                        file.write(chunk)
                break
            except Exception:
                errorLogging()
        # run updater
        Popen(program_name, cwd=current_directory)

    @staticmethod
    def updateCudaSoftware():
        # try to update at most 5 times
        for _ in range(5):
            try:
                program_name = "update.exe"
                current_directory = config.PATH_LOCAL
                res = requests_get(config.UPDATER_URL)
                assets = res.json()['assets']
                url = [i["browser_download_url"] for i in assets if i["name"] == program_name][0]
                res = requests_get(url, stream=True)
                with open(os_path.join(current_directory, program_name), 'wb') as file:
                    for chunk in res.iter_content(chunk_size=1024*5):
                        file.write(chunk)
                break
            except Exception:
                errorLogging()
        # run updater
        Popen([program_name, "--cuda"], cwd=current_directory)

    def getListMicHost(self):
        self.ensure_initialized()
        try:
            dm = device_manager.getMicDevices()
            result = [host for host in dm.keys()]
        except Exception:
            errorLogging()
            result = []
        return result

    def getMicDefaultDevice(self):
        self.ensure_initialized()
        try:
            dm = device_manager.getMicDevices()
            result = dm.get(config.SELECTED_MIC_HOST, [{"name": "NoDevice"}])[0]["name"]
        except Exception:
            errorLogging()
            result = "NoDevice"
        return result

    def getListMicDevice(self):
        self.ensure_initialized()
        try:
            dm = device_manager.getMicDevices()
            result = [device["name"] for device in dm.get(config.SELECTED_MIC_HOST, [{"name": "NoDevice"}])]
        except Exception:
            errorLogging()
            result = ["NoDevice"]
        return result

    def getListSpeakerDevice(self):
        self.ensure_initialized()
        try:
            sd = device_manager.getSpeakerDevices()
            result = [device["name"] for device in sd]
        except Exception:
            errorLogging()
            result = ["NoDevice"]
        return result

    def startMicTranscript(self, fnc):
        self.ensure_initialized()
        mic_host_name = config.SELECTED_MIC_HOST
        mic_device_name = config.SELECTED_MIC_DEVICE

        mic_device_list = device_manager.getMicDevices().get(mic_host_name, [{"name": "NoDevice"}])
        selected_mic_device = [device for device in mic_device_list if device["name"] == mic_device_name]

        if len(selected_mic_device) == 0 or mic_device_name == "NoDevice":
            fnc({"text": False, "language": None})
        else:
            self.mic_audio_queue = Queue()
            # self.mic_energy_queue = Queue()

            mic_device = selected_mic_device[0]
            record_timeout = config.MIC_RECORD_TIMEOUT
            phrase_timeout = config.MIC_PHRASE_TIMEOUT
            if record_timeout > phrase_timeout:
                record_timeout = phrase_timeout

            self.mic_audio_recorder = SelectedMicEnergyAndAudioRecorder(
                device=mic_device,
                energy_threshold=config.MIC_THRESHOLD,
                dynamic_energy_threshold=config.MIC_AUTOMATIC_THRESHOLD,
                phrase_time_limit=record_timeout,
            )
            # self.mic_audio_recorder.recordIntoQueue(self.mic_audio_queue, mic_energy_queue)
            self.mic_audio_recorder.recordIntoQueue(self.mic_audio_queue, None)
            self.mic_transcriber = AudioTranscriber(
                speaker=False,
                source=self.mic_audio_recorder.source,
                phrase_timeout=phrase_timeout,
                max_phrases=config.MIC_MAX_PHRASES,
                transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
                root=config.PATH_LOCAL,
                whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
                device=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device"],
                device_index=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device_index"],
                compute_type=config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE,
            )
            def sendMicTranscript():
                try:
                    selected_your_languages = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
                    languages = [data["language"] for data in selected_your_languages.values() if data["enable"] is True]
                    countries = [data["country"] for data in selected_your_languages.values() if data["enable"] is True]
                    if isinstance(self.mic_transcriber, AudioTranscriber) is True:
                        res = self.mic_transcriber.transcribeAudioQueue(
                            self.mic_audio_queue,
                            languages,
                            countries,
                            config.MIC_AVG_LOGPROB,
                            config.MIC_NO_SPEECH_PROB,
                            config.MIC_NO_REPEAT_NGRAM_SIZE,
                            config.MIC_VAD_FILTER,
                            config.MIC_VAD_PARAMETERS,
                        )
                        if res:
                            result = self.mic_transcriber.getTranscript()
                            fnc(result)
                except Exception:
                    errorLogging()

            def endMicTranscript():
                while not self.mic_audio_queue.empty():
                    self.mic_audio_queue.get()
                # while not self.mic_energy_queue.empty():
                #     self.mic_energy_queue.get()
                self.mic_transcriber = None
                gc.collect()

            # def sendMicEnergy():
            #     if mic_energy_queue.empty() is False:
            #         energy = mic_energy_queue.get()
            #         # print("mic energy:", energy)
            #         try:
            #             fnc(energy)
            #         except Exception:
            #             pass
            #     sleep(0.01)

            self.mic_print_transcript = threadFnc(sendMicTranscript, end_fnc=endMicTranscript)
            self.mic_print_transcript.daemon = True
            self.mic_print_transcript.start()

            # self.mic_get_energy = threadFnc(sendMicEnergy)
            # self.mic_get_energy.daemon = True
            # self.mic_get_energy.start()

            self.changeMicTranscriptStatus()

    def resumeMicTranscript(self):
        self.ensure_initialized()
        # キューをクリア
        if isinstance(self.mic_audio_queue, Queue):
            while not self.mic_audio_queue.empty():
                self.mic_audio_queue.get()

        # 文字起こしを再開
        # if isinstance(self.mic_print_transcript, threadFnc):
        #     self.mic_print_transcript.resume()

        # 音声のレコードを再開
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.resume()

    def pauseMicTranscript(self):
        self.ensure_initialized()
        # 文字起こしを一時停止
        # if isinstance(self.mic_print_transcript, threadFnc):
        #     self.mic_print_transcript.pause()

        # 音声のレコードを一時停止
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.pause()

    # VRAM 不足エラーを検出するメソッドを追加
    def detectVRAMError(self, error):
        error_str = str(error)
        if isinstance(error, ValueError) and len(error.args) > 0 and error.args[0] == "VRAM_OUT_OF_MEMORY":
            return True, error.args[1] if len(error.args) > 1 else "VRAM out of memory"
        if "CUDA out of memory" in error_str or "CUBLAS_STATUS_ALLOC_FAILED" in error_str:
            return True, error_str
        return False, None

    def changeMicTranscriptStatus(self):
        if config.VRC_MIC_MUTE_SYNC is True:
            match self.mic_mute_status:
                case True:
                    self.pauseMicTranscript()
                case False:
                    self.resumeMicTranscript()
                case None:
                    # mute selfの状態が不明な場合は一時停止しない
                    self.resumeMicTranscript()
                case _:
                    pass
        else:
            self.resumeMicTranscript()

    def stopMicTranscript(self):
        self.ensure_initialized()
        if isinstance(self.mic_print_transcript, threadFnc):
            self.mic_print_transcript.stop()
            self.mic_print_transcript.join()
            self.mic_print_transcript = None
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.resume()
            self.mic_audio_recorder.stop()
            self.mic_audio_recorder = None
        # if isinstance(self.mic_get_energy, threadFnc):
        #     self.mic_get_energy.stop()
        #     self.mic_get_energy = None

    def startCheckMicEnergy(self, fnc:Optional[Callable[[float], None]]=None) -> None:
        self.ensure_initialized()
        # fnc may be None or a callable. Use cast after checking for None to satisfy type checker.
        if fnc is not None:
            self.check_mic_energy_fnc = cast(Callable[[float], None], fnc)

        mic_host_name = config.SELECTED_MIC_HOST
        mic_device_name = config.SELECTED_MIC_DEVICE

        mic_device_list = device_manager.getMicDevices().get(mic_host_name, [{"name": "NoDevice"}])
        selected_mic_device = [device for device in mic_device_list if device["name"] == mic_device_name]

        if len(selected_mic_device) == 0 or mic_device_name == "NoDevice":
            self.check_mic_energy_fnc(False)
        else:
            def sendMicEnergy():
                if mic_energy_queue.empty() is False:
                    energy = mic_energy_queue.get()
                    try:
                        self.check_mic_energy_fnc(energy)
                    except Exception:
                        errorLogging()
                sleep(0.01)

            mic_energy_queue: Queue = Queue()
            mic_device = selected_mic_device[0]
            self.mic_energy_recorder = SelectedMicEnergyRecorder(mic_device)
            self.mic_energy_recorder.recordIntoQueue(mic_energy_queue)
            self.mic_energy_plot_progressbar = threadFnc(sendMicEnergy)
            self.mic_energy_plot_progressbar.daemon = True
            self.mic_energy_plot_progressbar.start()

    def stopCheckMicEnergy(self):
        self.ensure_initialized()
        if isinstance(self.mic_energy_plot_progressbar, threadFnc):
            self.mic_energy_plot_progressbar.stop()
            self.mic_energy_plot_progressbar.join()
            self.mic_energy_plot_progressbar = None
        if isinstance(self.mic_energy_recorder, SelectedMicEnergyRecorder):
            self.mic_energy_recorder.resume()
            self.mic_energy_recorder.stop()
            self.mic_energy_recorder = None

    def startSpeakerTranscript(self, fnc:Optional[Callable[[dict], None]]=None) -> None:
        self.ensure_initialized()
        speaker_device_name = config.SELECTED_SPEAKER_DEVICE

        speaker_device_list = device_manager.getSpeakerDevices()
        selected_speaker_device = [device for device in speaker_device_list if device["name"] == speaker_device_name]

        if len(selected_speaker_device) == 0 or speaker_device_name == "NoDevice":
            # fnc may be None; only call if callable
            if callable(fnc):
                fnc({"text": False, "language": None})
        else:
            speaker_audio_queue: Queue = Queue()
            speaker_device = selected_speaker_device[0]
            record_timeout = config.SPEAKER_RECORD_TIMEOUT
            phrase_timeout = config.SPEAKER_PHRASE_TIMEOUT
            if record_timeout > phrase_timeout:
                record_timeout = phrase_timeout

            self.speaker_audio_recorder = SelectedSpeakerEnergyAndAudioRecorder(
                device=speaker_device,
                energy_threshold=config.SPEAKER_THRESHOLD,
                dynamic_energy_threshold=config.SPEAKER_AUTOMATIC_THRESHOLD,
                phrase_time_limit=record_timeout,
            )
            # self.speaker_audio_recorder.recordIntoQueue(speaker_audio_queue, speaker_energy_queue)
            self.speaker_audio_recorder.recordIntoQueue(speaker_audio_queue, None)
            self.speaker_transcriber = AudioTranscriber(
                speaker=True,
                source=self.speaker_audio_recorder.source,
                phrase_timeout=phrase_timeout,
                max_phrases=config.SPEAKER_MAX_PHRASES,
                transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
                root=config.PATH_LOCAL,
                whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
                device=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device"],
                device_index=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device_index"],
                compute_type=config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE,
            )
            def sendSpeakerTranscript():
                try:
                    selected_target_languages = config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
                    languages = [data["language"] for data in selected_target_languages.values() if data["enable"] is True]
                    countries = [data["country"] for data in selected_target_languages.values() if data["enable"] is True]
                    if isinstance(self.speaker_transcriber, AudioTranscriber) is True:
                        res = self.speaker_transcriber.transcribeAudioQueue(
                            speaker_audio_queue,
                            languages,
                            countries,
                            config.SPEAKER_AVG_LOGPROB,
                            config.SPEAKER_NO_SPEECH_PROB,
                            config.SPEAKER_NO_REPEAT_NGRAM_SIZE,
                            config.SPEAKER_VAD_FILTER,
                            config.SPEAKER_VAD_PARAMETERS,
                        )
                        if res:
                            result = self.speaker_transcriber.getTranscript()
                            fnc(result)
                except Exception:
                    errorLogging()

            def endSpeakerTranscript():
                while not speaker_audio_queue.empty():
                    speaker_audio_queue.get()
                # while not speaker_energy_queue.empty():
                #     speaker_energy_queue.get()
                self.speaker_transcriber = None
                gc.collect()

            # def sendSpeakerEnergy():
            #     if speaker_energy_queue.empty() is False:
            #         energy = speaker_energy_queue.get()
            #         # print("speaker energy:", energy)
            #         try:
            #             fnc(energy)
            #         except Exception:
            #             pass
            #     sleep(0.01)

            self.speaker_print_transcript = threadFnc(sendSpeakerTranscript, end_fnc=endSpeakerTranscript)
            self.speaker_print_transcript.daemon = True
            self.speaker_print_transcript.start()

            # self.speaker_get_energy = threadFnc(sendSpeakerEnergy)
            # self.speaker_get_energy.daemon = True
            # self.speaker_get_energy.start()

    def stopSpeakerTranscript(self):
        self.ensure_initialized()
        if isinstance(self.speaker_print_transcript, threadFnc):
            self.speaker_print_transcript.stop()
            self.speaker_print_transcript.join()
            self.speaker_print_transcript = None
        if isinstance(self.speaker_audio_recorder, SelectedSpeakerEnergyAndAudioRecorder):
            self.speaker_audio_recorder.stop()
            self.speaker_audio_recorder = None
        # if isinstance(self.speaker_get_energy, threadFnc):
        #     self.speaker_get_energy.stop()
        #     self.speaker_get_energy = None

    def startCheckSpeakerEnergy(self, fnc:Optional[Callable[[float], None]]=None) -> None:
        self.ensure_initialized()
        # Accept None as default and assign safely with cast after None-check
        if fnc is not None:
            self.check_speaker_energy_fnc = cast(Callable[[float], None], fnc)

        speaker_device_name = config.SELECTED_SPEAKER_DEVICE
        speaker_device_list = device_manager.getSpeakerDevices()
        selected_speaker_device = [device for device in speaker_device_list if device["name"] == speaker_device_name]

        if len(selected_speaker_device) == 0 or speaker_device_name == "NoDevice":
            self.check_speaker_energy_fnc(False)
        else:
            def sendSpeakerEnergy():
                if not speaker_energy_queue.empty():
                    energy = speaker_energy_queue.get()
                    try:
                        self.check_speaker_energy_fnc(energy)
                    except Exception:
                        errorLogging()
                sleep(0.01)

            speaker_energy_queue: Queue = Queue()
            speaker_device = selected_speaker_device[0]
            self.speaker_energy_recorder = SelectedSpeakerEnergyRecorder(speaker_device)
            self.speaker_energy_recorder.recordIntoQueue(speaker_energy_queue)
            self.speaker_energy_plot_progressbar = threadFnc(sendSpeakerEnergy)
            self.speaker_energy_plot_progressbar.daemon = True
            self.speaker_energy_plot_progressbar.start()

    def stopCheckSpeakerEnergy(self):
        self.ensure_initialized()
        if isinstance(self.speaker_energy_plot_progressbar, threadFnc):
            self.speaker_energy_plot_progressbar.stop()
            self.speaker_energy_plot_progressbar.join()
            self.speaker_energy_plot_progressbar = None
        if isinstance(self.speaker_energy_recorder, SelectedSpeakerEnergyRecorder):
            self.speaker_energy_recorder.resume()
            self.speaker_energy_recorder.stop()
            self.speaker_energy_recorder = None

    def createOverlayImageSmallLog(self, message:Optional[str], your_language:Optional[str], translation:list, target_language:Optional[dict], transliteration_message:Optional[dict] = None, transliteration_translation:Optional[list] = None) -> object:
        self.ensure_initialized()
        # Normalize target_language dict -> list
        target_language_list = []
        if isinstance(target_language, dict):
            target_language_list = [data["language"] for data in target_language.values() if data.get("enable") is True]

        # 翻訳行ルビ (任意) が指定されていれば渡す。後方互換のため None / 不正型は空リストに。
        if not isinstance(transliteration_message, list):
            transliteration_message = []
        if not isinstance(transliteration_translation, list):
            transliteration_translation = [[] for _ in translation]

        return self.overlay_image.createOverlayImageSmallLog(
            message,
            your_language,
            translation,
            target_language_list,
            transliteration_message=transliteration_message,
            transliteration_translation=transliteration_translation,
        )

    def createOverlayImageSmallMessage(self, message):
        self.ensure_initialized()
        ui_language = config.UI_LANGUAGE
        convert_languages = {
            "en": "Default",
            "jp": "Japanese",
            "ko":"Korean",
            "zh-Hans":"Chinese Simplified",
            "zh-Hant":"Chinese Traditional",
        }
        language = convert_languages.get(ui_language, "Default")
        return self.overlay_image.createOverlayImageSmallLog(message, language)

    def clearOverlayImageSmallLog(self):
        self.ensure_initialized()
        self.overlay.clearImage("small")

    def updateOverlaySmallLog(self, img):
        self.ensure_initialized()
        self.overlay.updateImage(img, "small")

    def updateOverlaySmallLogSettings(self):
        self.ensure_initialized()
        size = "small"

        if (self.overlay.settings[size]["x_pos"] != config.OVERLAY_SMALL_LOG_SETTINGS["x_pos"] or
            self.overlay.settings[size]["y_pos"] != config.OVERLAY_SMALL_LOG_SETTINGS["y_pos"] or
            self.overlay.settings[size]["z_pos"] != config.OVERLAY_SMALL_LOG_SETTINGS["z_pos"] or
            self.overlay.settings[size]["x_rotation"] != config.OVERLAY_SMALL_LOG_SETTINGS["x_rotation"] or
            self.overlay.settings[size]["y_rotation"] != config.OVERLAY_SMALL_LOG_SETTINGS["y_rotation"] or
            self.overlay.settings[size]["z_rotation"] != config.OVERLAY_SMALL_LOG_SETTINGS["z_rotation"] or
            self.overlay.settings[size]["tracker"] != config.OVERLAY_SMALL_LOG_SETTINGS["tracker"]):
            self.overlay.updatePosition(
                config.OVERLAY_SMALL_LOG_SETTINGS["x_pos"],
                config.OVERLAY_SMALL_LOG_SETTINGS["y_pos"],
                config.OVERLAY_SMALL_LOG_SETTINGS["z_pos"],
                config.OVERLAY_SMALL_LOG_SETTINGS["x_rotation"],
                config.OVERLAY_SMALL_LOG_SETTINGS["y_rotation"],
                config.OVERLAY_SMALL_LOG_SETTINGS["z_rotation"],
                config.OVERLAY_SMALL_LOG_SETTINGS["tracker"],
                size,
            )
        if (self.overlay.settings[size]["display_duration"] != config.OVERLAY_SMALL_LOG_SETTINGS["display_duration"]):
            self.overlay.updateDisplayDuration(config.OVERLAY_SMALL_LOG_SETTINGS["display_duration"], size)
        if (self.overlay.settings[size]["fadeout_duration"] != config.OVERLAY_SMALL_LOG_SETTINGS["fadeout_duration"]):
            self.overlay.updateFadeoutDuration(config.OVERLAY_SMALL_LOG_SETTINGS["fadeout_duration"], size)
        if (self.overlay.settings[size]["opacity"] != config.OVERLAY_SMALL_LOG_SETTINGS["opacity"]):
            self.overlay.updateOpacity(config.OVERLAY_SMALL_LOG_SETTINGS["opacity"], size, True)
        if (self.overlay.settings[size]["ui_scaling"] != config.OVERLAY_SMALL_LOG_SETTINGS["ui_scaling"]):
            self.overlay.updateUiScaling(config.OVERLAY_SMALL_LOG_SETTINGS["ui_scaling"], size)

    def createOverlayImageLargeLog(self, message_type:str, message:Optional[str], your_language:Optional[str],  translation:list, target_language:Optional[dict]=None, transliteration_message:Optional[list]=None, transliteration_translation:Optional[list]=None) -> object:
        self.ensure_initialized()
        # normalize target_language dict -> list of language strings
        target_language_list = []
        if isinstance(target_language, dict):
            target_language_list = [data["language"] for data in target_language.values() if data.get("enable") is True]
        return self.overlay_image.createOverlayImageLargeLog(message_type, message, your_language, translation, target_language_list, transliteration_message, transliteration_translation)

    def createOverlayImageLargeMessage(self, message):
        self.ensure_initialized()
        ui_language = config.UI_LANGUAGE
        convert_languages = {
            "en": "Default",
            "jp": "Japanese",
            "ko":"Korean",
            "zh-Hans":"Chinese Simplified",
            "zh-Hant":"Chinese Traditional",
        }
        language = convert_languages.get(ui_language, "Default")
        overlay_image = OverlayImage(config.PATH_LOCAL)

        for _ in range(2):
            overlay_image.createOverlayImageLargeLog("send", message, language)
            overlay_image.createOverlayImageLargeLog("receive", message, language)
        return overlay_image.createOverlayImageLargeLog("send", message, language)

    def clearOverlayImageLargeLog(self):
        self.ensure_initialized()
        self.overlay.clearImage("large")

    def updateOverlayLargeLog(self, img):
        self.ensure_initialized()
        self.overlay.updateImage(img, "large")

    def updateOverlayLargeLogSettings(self):
        self.ensure_initialized()
        size = "large"
        if (self.overlay.settings[size]["x_pos"] != config.OVERLAY_LARGE_LOG_SETTINGS["x_pos"] or
            self.overlay.settings[size]["y_pos"] != config.OVERLAY_LARGE_LOG_SETTINGS["y_pos"] or
            self.overlay.settings[size]["z_pos"] != config.OVERLAY_LARGE_LOG_SETTINGS["z_pos"] or
            self.overlay.settings[size]["x_rotation"] != config.OVERLAY_LARGE_LOG_SETTINGS["x_rotation"] or
            self.overlay.settings[size]["y_rotation"] != config.OVERLAY_LARGE_LOG_SETTINGS["y_rotation"] or
            self.overlay.settings[size]["z_rotation"] != config.OVERLAY_LARGE_LOG_SETTINGS["z_rotation"] or
            self.overlay.settings[size]["tracker"] != config.OVERLAY_LARGE_LOG_SETTINGS["tracker"]):
            self.overlay.updatePosition(
                config.OVERLAY_LARGE_LOG_SETTINGS["x_pos"],
                config.OVERLAY_LARGE_LOG_SETTINGS["y_pos"],
                config.OVERLAY_LARGE_LOG_SETTINGS["z_pos"],
                config.OVERLAY_LARGE_LOG_SETTINGS["x_rotation"],
                config.OVERLAY_LARGE_LOG_SETTINGS["y_rotation"],
                config.OVERLAY_LARGE_LOG_SETTINGS["z_rotation"],
                config.OVERLAY_LARGE_LOG_SETTINGS["tracker"],
                size,
            )
        if (self.overlay.settings[size]["display_duration"] != config.OVERLAY_LARGE_LOG_SETTINGS["display_duration"]):
            self.overlay.updateDisplayDuration(config.OVERLAY_LARGE_LOG_SETTINGS["display_duration"], size)
        if (self.overlay.settings[size]["fadeout_duration"] != config.OVERLAY_LARGE_LOG_SETTINGS["fadeout_duration"]):
            self.overlay.updateFadeoutDuration(config.OVERLAY_LARGE_LOG_SETTINGS["fadeout_duration"], size)
        if (self.overlay.settings[size]["opacity"] != config.OVERLAY_LARGE_LOG_SETTINGS["opacity"]):
            self.overlay.updateOpacity(config.OVERLAY_LARGE_LOG_SETTINGS["opacity"], size, True)
        if (self.overlay.settings[size]["ui_scaling"] != config.OVERLAY_LARGE_LOG_SETTINGS["ui_scaling"]):
            self.overlay.updateUiScaling(config.OVERLAY_LARGE_LOG_SETTINGS["ui_scaling"] * 0.25, size)

    def startOverlay(self):
        self.ensure_initialized()
        self.overlay.startOverlay()

    def shutdownOverlay(self):
        self.ensure_initialized()
        self.overlay.shutdownOverlay()

    def startWatchdog(self):
        self.ensure_initialized()
        self.th_watchdog = threadFnc(self.watchdog.start)
        self.th_watchdog.daemon = True
        self.th_watchdog.start()

    def feedWatchdog(self):
        self.ensure_initialized()
        self.watchdog.feed()

    def setWatchdogCallback(self, callback):
        self.ensure_initialized()
        self.watchdog.setCallback(callback)

    def stopWatchdog(self):
        self.ensure_initialized()
        if isinstance(self.th_watchdog, threadFnc):
            self.th_watchdog.stop()
            self.th_watchdog.join()
            self.th_watchdog = None

    def message_handler(websocket, message):
        """WebSocketメッセージ受信時の処理"""
        pass

    def startWebSocketServer(self, host, port):
        """WebSocketサーバーを起動し、別スレッドで実行する"""
        self.ensure_initialized()
        if self.websocket_server_alive is True:
            # サーバーが既に起動している場合は何もしない
            return

        self.websocket_server_loop = True
        self.websocket_server_alive = False  # 初期状態を明示

        async def WebSocketServerMain():
            try:
                self.websocket_server = WebSocketServer(
                    host=host,
                    port=port,
                )
                self.websocket_server.set_message_handler(self.message_handler)
                self.websocket_server.start()
                self.websocket_server_alive = True

                # イベントループが終了するまで待機
                while self.websocket_server_loop:
                    # self.websocket_server.send("Server is running...")
                    await asyncio.sleep(0.5)  # 応答性向上のため間隔短縮

            except Exception:
                errorLogging()
                # 具体的なエラー内容をログに残す場合
                # self.logger.error(f"WebSocket server error: {str(e)}")
            finally:
                # 確実にサーバーを停止
                if hasattr(self, 'websocket_server') and self.websocket_server:
                    self.websocket_server.stop()
                self.websocket_server_alive = False

        self.th_websocket_server = Thread(target=lambda: asyncio.run(WebSocketServerMain()))
        self.th_websocket_server.daemon = True
        self.th_websocket_server.start()

    def stopWebSocketServer(self):
        """WebSocketサーバーを停止する"""
        self.ensure_initialized()
        if not hasattr(self, 'th_websocket_server') or self.th_websocket_server is None:
            return

        self.websocket_server_loop = False

        try:
            # 一定時間待機してからタイムアウト
            self.th_websocket_server.join(timeout=2.0)

            if self.th_websocket_server.is_alive():
                # タイムアウト後もスレッドが生きている場合の処理
                self.logger.warning("WebSocket server thread did not terminate properly")
        except Exception:
            errorLogging()
        finally:
            self.th_websocket_server = None
            self.websocket_server = None
            self.websocket_server_alive = False

    def checkWebSocketServerAlive(self):
        """WebSocketサーバーの稼働状態を確認する"""
        self.ensure_initialized()
        return self.websocket_server_alive

    def websocketSendMessage(self, message_dict:dict):
        """
        WebSocketサーバーから全クライアントにメッセージを送信する
        :param message_dict: 送信するメッセージの辞書
        :return: 送信成功したかどうか
        """
        self.ensure_initialized()
        if not self.websocket_server_alive or not self.websocket_server:
            return False
        try:
            message_json = json.dumps(message_dict)
            return self.websocket_server.send(message_json)
        except Exception:
            errorLogging()
            return False

    def setCopyToClipboard(self, text:str) -> bool:
        self.ensure_initialized()
        try:
            if isinstance(self.clipboard, Clipboard):
                self.clipboard.copy(text)
                return True
            else:
                return False
        except Exception:
            errorLogging()
            return False

    def setPasteFromClipboard(self) -> bool:
        self.ensure_initialized()
        try:
            if isinstance(self.clipboard, Clipboard):
                return self.clipboard.paste()
            else:
                return False
        except Exception:
            errorLogging()
            return False

model = Model()