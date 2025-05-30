import re
from subprocess import Popen
from threading import Thread
from time import sleep
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from config import config
from device_manager import device_manager
from model import model
from utils import (errorLogging, isAvailableWebSocketServer,
                   isConnectedNetwork, isValidIpAddress, printLog, removeLog)


class Controller:
    init_mapping: Dict[str, Dict[str, Any]]
    run_mapping: Dict[str, str]
    run: Optional[Callable[[int, str, Any], None]]
    device_access_status: bool

    def __init__(self) -> None:
        """Initializes mappings for UI updates and device access status."""
        self.init_mapping: Dict[str, Dict[str, Any]] = {}
        self.run_mapping: Dict[str, str] = {}
        self.run: Optional[Callable[[int, str, Any], None]] = None
        self.device_access_status: bool = True

    def setInitMapping(self, init_mapping: Dict[str, Dict[str, Any]]) -> None:
        """Sets the mapping for initialization functions."""
        self.init_mapping = init_mapping

    def setRunMapping(self, run_mapping: Dict[str, str]) -> None:
        """Sets the mapping for UI update functions via `run`."""
        self.run_mapping = run_mapping

    def setRun(self, run: Callable[[int, str, Any], None]) -> None:
        """Sets the callback function used to send updates to the UI."""
        self.run = run

    # response functions
    def connectedNetwork(self) -> None:
        """Notifies the UI that the network is connected."""
        if self.run and "connected_network" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["connected_network"],
                True,
            )

    def disconnectedNetwork(self) -> None:
        """Notifies the UI that the network is disconnected."""
        if self.run and "connected_network" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["connected_network"],
                False,
            )

    def enableAiModels(self) -> None:
        """Notifies the UI that AI models can be enabled (e.g., weights downloaded)."""
        if self.run and "enable_ai_models" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["enable_ai_models"],
                True,
            )

    def disableAiModels(self) -> None:
        """Notifies the UI that AI models should be disabled (e.g., weights missing)."""
        if self.run and "enable_ai_models" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["enable_ai_models"],
                False,
            )

    def updateMicHostList(self) -> None:
        """Sends the updated microphone host list to the UI."""
        if self.run and "mic_host_list" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["mic_host_list"],
                model.getListMicHost(),
            )

    def updateMicDeviceList(self) -> None:
        """Sends the updated microphone device list to the UI."""
        if self.run and "mic_device_list" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["mic_device_list"],
                model.getListMicDevice(),
            )

    def updateSpeakerDeviceList(self) -> None:
        """Sends the updated speaker device list to the UI."""
        if self.run and "speaker_device_list" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["speaker_device_list"],
                model.getListSpeakerDevice(),
            )

    def updateConfigSettings(self) -> None:
        """Sends all current configuration settings to the UI after initialization."""
        settings: Dict[str, Any] = {}
        for endpoint, dict_data in self.init_mapping.items():
            # Assuming dict_data["variable"] is a callable that might take None or no args
            response: Dict[str, Any] = dict_data["variable"](None)
            result = response.get("result", None)
            settings[endpoint] = result
        if self.run and "initialization_complete" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["initialization_complete"],
                settings,
            )

    def restartAccessDevices(self) -> None:
        """Restarts device access services based on current configuration."""
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.startThreadingTranscriptionSendMessage()
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.startThreadingTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            model.startCheckMicEnergy(
                self.progressBarMicEnergy,
            )
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            model.startCheckSpeakerEnergy(
                self.progressBarSpeakerEnergy,
            )

    def stopAccessDevices(self) -> None:
        """Stops all active device access services."""
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.stopThreadingTranscriptionSendMessage()
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.stopThreadingTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            model.stopCheckMicEnergy()
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            model.stopCheckSpeakerEnergy()

    def updateSelectedMicDevice(self, host: str, device: str) -> None:
        """Updates the selected microphone host and device in config and UI."""
        config.SELECTED_MIC_HOST = host
        config.SELECTED_MIC_DEVICE = device
        if self.run and "selected_mic_device" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["selected_mic_device"],
                {"host": host, "device": device},
            )

    def updateSelectedSpeakerDevice(self, device: str) -> None:
        """Updates the selected speaker device in config and UI."""
        config.SELECTED_SPEAKER_DEVICE = device
        if self.run and "selected_speaker_device" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["selected_speaker_device"],
                device,
            )

    def progressBarMicEnergy(self, energy: Union[float, bool]) -> None:
        """
        Callback for microphone energy updates. Sends energy level or error to UI.
        `energy` is float if successful, False if device error.
        """
        if energy is False:
            if self.run and "error_device" in self.run_mapping:
                self.run(
                    400,
                    self.run_mapping["error_device"],
                    {
                        "message": "No mic device detected",
                        "data": None
                    },
                )
        else:
            if self.run and "check_mic_volume" in self.run_mapping:
                self.run(
                    200,
                    self.run_mapping["check_mic_volume"],
                    energy,
                )

    def progressBarSpeakerEnergy(self, energy: Union[float, bool]) -> None:
        """
        Callback for speaker energy updates. Sends energy level or error to UI.
        `energy` is float if successful, False if device error.
        """
        if energy is False:
            if self.run and "error_device" in self.run_mapping:
                self.run(
                    400,
                    self.run_mapping["error_device"],
                    {
                        "message": "No speaker device detected",
                        "data": None
                    },
                )
        else:
            if self.run and "check_speaker_volume" in self.run_mapping:
                self.run(
                    200,
                    self.run_mapping["check_speaker_volume"],
                    energy,
                )

    class DownloadCTranslate2:
        """Handles download progress and completion for CTranslate2 model weights."""
        def __init__(self, run_mapping: Dict[str, str], weight_type: str, run: Callable[[int, str, Any], None]) -> None:
            """Initializes with UI run mapping, weight type, and run callback."""
            self.run_mapping = run_mapping
            self.weight_type = weight_type
            self.run = run

        def progressBar(self, progress: float) -> None:
            """Callback to report download progress via the run function."""
            printLog(f"CTranslate2 Weight Download Progress ({self.weight_type})", progress)
            if self.run and "download_progress_ctranslate2_weight" in self.run_mapping:
                self.run(
                    200,
                    self.run_mapping["download_progress_ctranslate2_weight"],
                    {"weight_type": self.weight_type, "progress": progress},
                )

        def downloaded(self) -> None:
            """Callback invoked on download completion; updates config and notifies UI."""
            if model.checkTranslatorCTranslate2ModelWeight(self.weight_type) is True:
                weight_type_dict = config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT
                weight_type_dict[self.weight_type] = True
                config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT = weight_type_dict

                if self.run and "downloaded_ctranslate2_weight" in self.run_mapping:
                    self.run(
                        200,
                        self.run_mapping["downloaded_ctranslate2_weight"],
                        self.weight_type,
                    )
            else:
                if self.run and "error_ctranslate2_weight" in self.run_mapping:
                    self.run(
                        400,
                        self.run_mapping["error_ctranslate2_weight"],
                        {
                            "message": f"CTranslate2 weight ({self.weight_type}) download error or validation failed.",
                            "data": None
                        },
                    )

    class DownloadWhisper:
        """Handles download progress and completion for Whisper model weights."""
        def __init__(self, run_mapping: Dict[str, str], weight_type: str, run: Callable[[int, str, Any], None]) -> None:
            """Initializes with UI run mapping, weight type, and run callback."""
            self.run_mapping = run_mapping
            self.weight_type = weight_type
            self.run = run

        def progressBar(self, progress: float) -> None:
            """Callback to report download progress via the run function."""
            printLog(f"Whisper Weight Download Progress ({self.weight_type})", progress)
            if self.run and "download_progress_whisper_weight" in self.run_mapping:
                self.run(
                    200,
                    self.run_mapping["download_progress_whisper_weight"],
                    {"weight_type": self.weight_type, "progress": progress},
                )

        def downloaded(self) -> None:
            """Callback invoked on download completion; updates config and notifies UI."""
            if model.checkTranscriptionWhisperModelWeight(self.weight_type) is True:
                weight_type_dict = config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT
                weight_type_dict[self.weight_type] = True
                config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = weight_type_dict

                if self.run and "downloaded_whisper_weight" in self.run_mapping:
                    self.run(
                        200,
                        self.run_mapping["downloaded_whisper_weight"],
                        self.weight_type,
                    )
            else:
                if self.run and "error_whisper_weight" in self.run_mapping:
                    self.run(
                        400,
                        self.run_mapping["error_whisper_weight"],
                        {
                            "message": f"Whisper weight ({self.weight_type}) download error or validation failed.",
                            "data": None
                        },
                    )

    def micMessage(self, result: Dict[str, Any]) -> None:
        """
        Handles microphone transcription results.

        Processes the transcribed message, performs translation and transliteration if enabled,
        sends OSC messages, updates the UI, logs the message, and updates overlays.
        `result` contains 'text' (str or False for error) and 'language' (str).
        """
        message: Union[str, bool] = result.get("text", False)
        language: Optional[str] = result.get("language")

        if not isinstance(message, str) or len(message) == 0:
            if message is False and self.run and "error_device" in self.run_mapping: # Explicitly False for device error
                self.run(
                    400,
                    self.run_mapping["error_device"],
                    {
                        "message": "No mic device detected or empty message received.",
                        "data": None
                    },
                )
            return # Ignore empty strings or other non-string/False messages

        translation: List[str] = []
        transliteration: List[str] = []

        if model.checkKeywords(message):
            if self.run and "word_filter" in self.run_mapping:
                self.run(
                    200,
                    self.run_mapping["word_filter"],
                    {"message": f"Detected by word filter: {message}"},
                )
            return
        elif model.detectRepeatSendMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                translation, success = model.getInputTranslate(message, source_language=language)
                if all(success) is not True:
                    self.changeToCTranslate2Process()
                    if self.run and "error_translation_engine" in self.run_mapping:
                        self.run(
                            400,
                            self.run_mapping["error_translation_engine"],
                            {
                                "message": "Translation engine limit error",
                                "data": None
                            },
                        )

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    # Ensure translation is not empty and language is Japanese before transliterating
                    if translation and config.SELECTED_TARGET_LANGUAGES.get(config.SELECTED_TAB_NO, {}).get("1", {}).get("language") == "Japanese":
                        transliteration = model.convertMessageToTransliteration(translation[0])

            if config.ENABLE_TRANSCRIPTION_SEND is True:
                if config.SEND_MESSAGE_TO_VRC is True:
                    osc_message_content: str
                    if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                        if config.ENABLE_TRANSLATION is False or not translation: # send original if no translation
                            osc_message_content = self.messageFormatter("SEND", [], [message])
                        else:
                            osc_message_content = self.messageFormatter("SEND", [], translation)
                    else:
                        osc_message_content = self.messageFormatter("SEND", translation, [message])
                    model.oscSendMessage(osc_message_content)

                if self.run and "transcription_mic" in self.run_mapping:
                    self.run(
                        200,
                        self.run_mapping["transcription_mic"],
                        {
                            "message": message,
                            "translation": translation,
                            "transliteration": transliteration
                        })

                if model.checkWebSocketServerAlive() is True:
                    model.websocketSendMessage(
                        {
                            "type":"SENT",
                            "src_languages":config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            "dst_languages":config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                            "message":message,
                            "translation":translation,
                            "transliteration":transliteration
                        }
                    )

                if config.LOGGER_FEATURE is True:
                    if len(translation) > 0:
                        translation = " (" + "/".join(translation) + ")"
                    model.logger.info(f"[SENT] {message}{translation}")

                if config.OVERLAY_LARGE_LOG is True and model.overlay.initialized is True:
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True and len(translation) > 0:
                        overlay_image = model.createOverlayImageLargeLog("send", translation[0], "")
                    else:
                        overlay_image = model.createOverlayImageLargeLog("send", message, translation[0] if len(translation) > 0 else "")
                    model.updateOverlayLargeLog(overlay_image)

    def speakerMessage(self, result: Dict[str, Any]) -> None:
        """
        Handles speaker transcription results.

        Similar to micMessage, but for received audio. Processes transcription,
        translation, transliteration, updates overlays, VRChat chatbox (if enabled),
        UI, WebSocket, and logs.
        `result` contains 'text' (str or False for error) and 'language' (str).
        """
        message: Union[str, bool] = result.get("text", False)
        language: Optional[str] = result.get("language")

        if not isinstance(message, str) or len(message) == 0:
            if message is False and self.run and "error_device" in self.run_mapping: # Explicitly False for device error
                self.run(
                    400,
                    self.run_mapping["error_device"],
                    {
                        "message": "No speaker device detected or empty message received.",
                        "data": None
                    },
                )
            return # Ignore empty strings or other non-string/False messages

        translation: List[str] = []
        transliteration: List[str] = []

        if model.checkKeywords(message):
            if self.run and "word_filter" in self.run_mapping:
                self.run(
                    200,
                    self.run_mapping["word_filter"],
                    {"message": f"Detected by word filter: {message}"},
                )
            return
        elif model.detectRepeatReceiveMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                translation, success = model.getOutputTranslate(message, source_language=language)
                if all(success) is not True:
                    self.changeToCTranslate2Process()
                    if self.run and "error_translation_engine" in self.run_mapping:
                        self.run(
                            400,
                            self.run_mapping["error_translation_engine"],
                            {
                                "message": "Translation engine limit error",
                                "data": None
                            },
                        )

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    # For speaker messages, transliteration is of the original message if target is Japanese
                    if config.SELECTED_TARGET_LANGUAGES.get(config.SELECTED_TAB_NO, {}).get("1", {}).get("language") == "Japanese":
                        transliteration = model.convertMessageToTransliteration(message)

            if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
                overlay_small_image: Optional[Any] = None # Assuming image type, replace Any if known
                overlay_large_image: Optional[Any] = None

                if config.OVERLAY_SMALL_LOG is True and model.overlay.initialized is True:
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True and translation:
                        overlay_small_image = model.createOverlayImageSmallLog(translation[0], "")
                    else:
                        overlay_small_image = model.createOverlayImageSmallLog(message, translation[0] if translation else "")
                    if overlay_small_image:
                        model.updateOverlaySmallLog(overlay_small_image)

                if config.OVERLAY_LARGE_LOG is True and model.overlay.initialized is True:
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True and translation:
                        overlay_large_image = model.createOverlayImageLargeLog("receive", translation[0], "")
                    else:
                        overlay_large_image = model.createOverlayImageLargeLog("receive", message, translation[0] if translation else "")
                    if overlay_large_image:
                        model.updateOverlayLargeLog(overlay_large_image)

                if config.SEND_RECEIVED_MESSAGE_TO_VRC is True:
                    osc_message_content = self.messageFormatter("RECEIVED", translation, [message])
                    model.oscSendMessage(osc_message_content)

                # update textbox message log (Received)
                if self.run and "transcription_speaker" in self.run_mapping:
                    self.run(
                        200,
                        self.run_mapping["transcription_speaker"],
                        {
                            "message": message,
                            "translation": translation,
                            "transliteration": transliteration,
                        })

                if model.checkWebSocketServerAlive() is True:
                    model.websocketSendMessage(
                        {
                            "type":"RECEIVED",
                            "src_languages":config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                            "dst_languages":config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            "message":message,
                            "translation":translation,
                            "transliteration":transliteration
                        }
                    )

                if config.LOGGER_FEATURE is True:
                    if len(translation) > 0:
                        translation = " (" + "/".join(translation) + ")"
                    model.logger.info(f"[RECEIVED] {message}{translation}")

    def chatMessage(self, data: Dict[str, str]) -> Dict[str, Any]:
        """
        Handles messages sent from the application's chat input.

        Processes the message, performs translation (with optional exclamation replacement)
        and transliteration, sends OSC messages, updates overlays, UI, WebSocket, and logs.
        `data` contains 'id' and 'message'.
        Returns a dictionary with processing results.
        """
        message_id: str = data.get("id", "") # Use .get for safety
        message: str = data.get("message", "")

        translation: List[str] = []
        transliteration: List[str] = []

        if len(message) > 0:
            if config.ENABLE_TRANSLATION is False:
                pass
            else:
                if config.USE_EXCLUDE_WORDS is True:
                    replacement_message, replacement_dict = self.replaceExclamationsWithRandom(message)
                    translation, success = model.getInputTranslate(replacement_message)

                    message = self.removeExclamations(message)
                    for i in range(len(translation)):
                        translation[i] = self.restoreText(translation[i], replacement_dict)
                else:
                    translation, success = model.getInputTranslate(message)

                if all(success) is not True:
                    self.changeToCTranslate2Process()
                    if self.run and "error_translation_engine" in self.run_mapping:
                        self.run(
                            400,
                            self.run_mapping["error_translation_engine"],
                            {
                                "message": "Translation engine limit error",
                                "data": None
                            },
                        )

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if translation and config.SELECTED_TARGET_LANGUAGES.get(config.SELECTED_TAB_NO, {}).get("1", {}).get("language") == "Japanese":
                        transliteration = model.convertMessageToTransliteration(translation[0])

            # send OSC message
            if config.SEND_MESSAGE_TO_VRC is True:
                osc_message_content: str
                if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                    if config.ENABLE_TRANSLATION is False or not translation:
                        osc_message_content = self.messageFormatter("SEND", [], [message])
                    else:
                        osc_message_content = self.messageFormatter("SEND", [], translation)
                else:
                    osc_message_content = self.messageFormatter("SEND", translation, [message])
                model.oscSendMessage(osc_message_content)

            if config.OVERLAY_LARGE_LOG is True and model.overlay.initialized is True:
                overlay_large_image: Optional[Any] = None
                if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True and translation:
                    overlay_large_image = model.createOverlayImageLargeLog("send", translation[0], "")
                else:
                    overlay_large_image = model.createOverlayImageLargeLog("send", message, translation[0] if translation else "")
                if overlay_large_image:
                    model.updateOverlayLargeLog(overlay_large_image)

            if model.checkWebSocketServerAlive() is True:
                model.websocketSendMessage(
                    {
                        "type":"CHAT",
                        "src_languages":config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                        "dst_languages":config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                        "message":message,
                        "translation":translation,
                        "transliteration":transliteration
                    }
                )

            # update textbox message log (Chat)
            if config.LOGGER_FEATURE is True:
                if len(translation) > 0:
                    translation_text = " (" + "/".join(translation) + ")"
                model.logger.info(f"[CHAT] {message}{translation_text}")

        return {"status":200,
                "result": {
                    "id": message_id,
                    "message": message,
                    "translation": translation,
                    "transliteration": transliteration,
                },
            }
        # Ensure a dictionary is always returned, even for empty messages
        return {
            "status": 200, # Or appropriate status if empty message is an error
            "result": {
                "id": message_id,
                "message": message, # Original empty message
                "translation": translation,
                "transliteration": transliteration,
            },
        }


    @staticmethod
    def getVersion(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the application version from config."""
        return {"status": 200, "result": config.VERSION}

    def checkSoftwareUpdated(self) -> None:
        """Checks for software updates and notifies the UI."""
        software_update_info: Dict[str, Any] = model.checkSoftwareUpdated()
        if self.run and "software_update_info" in self.run_mapping:
            self.run(
                200,
                self.run_mapping["software_update_info"],
                software_update_info,
            )

    @staticmethod
    def getComputeMode(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the current compute mode (e.g., 'cuda', 'cpu') from config."""
        return {"status": 200, "result": config.COMPUTE_MODE}

    @staticmethod
    def getComputeDeviceList(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the list of available compute devices from config."""
        return {"status": 200, "result": config.SELECTABLE_COMPUTE_DEVICE_LIST}

    @staticmethod
    def getSelectedTranslationComputeDevice(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the selected compute device for translation from config."""
        return {"status": 200, "result": config.SELECTED_TRANSLATION_COMPUTE_DEVICE}

    @staticmethod
    def setSelectedTranslationComputeDevice(device: Dict[str, Any], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the compute device for translation, updates config, and reloads the model."""
        printLog("setSelectedTranslationComputeDevice", device)
        config.SELECTED_TRANSLATION_COMPUTE_DEVICE = device
        model.changeTranslatorCTranslate2Model()
        return {"status": 200, "result": config.SELECTED_TRANSLATION_COMPUTE_DEVICE}

    @staticmethod
    def getSelectableCtranslate2WeightTypeDict(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the dictionary of available CTranslate2 weight types and their status from config."""
        return {"status": 200, "result": config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT}

    @staticmethod
    def getSelectedTranscriptionComputeDevice(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the selected compute device for transcription from config."""
        return {"status": 200, "result": config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE}

    @staticmethod
    def setSelectedTranscriptionComputeDevice(device: Dict[str, Any], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the compute device for transcription in config."""
        # Note: Original code used `device: str`, but config stores a dict. Assuming dict is correct.
        printLog("setSelectedTranscriptionComputeDevice", device)
        config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = device
        # TODO: Consider if model needs reloading like for translation
        return {"status": 200, "result": config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE}

    @staticmethod
    def getSelectableWhisperWeightTypeDict(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the dictionary of available Whisper weight types and their status from config."""
        return {"status": 200, "result": config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT}

    # @staticmethod
    # def getMaxMicThreshold(*args, **kwargs) -> dict:
    #     return {"status":200, "result":config.MAX_MIC_THRESHOLD}

    # @staticmethod
    # def getMaxSpeakerThreshold(*args, **kwargs) -> dict:
    #     return {"status":200, "result":config.MAX_SPEAKER_THRESHOLD}

    @staticmethod
    def setEnableTranslation(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables translation feature and loads the CTranslate2 model if not already loaded."""
        if model.isLoadedCTranslate2Model() is False:
            model.changeTranslatorCTranslate2Model()
        config.ENABLE_TRANSLATION = True
        return {"status": 200, "result": config.ENABLE_TRANSLATION}

    @staticmethod
    def setDisableTranslation(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables the translation feature."""
        config.ENABLE_TRANSLATION = False
        return {"status": 200, "result": config.ENABLE_TRANSLATION}

    @staticmethod
    def setEnableForeground(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables the 'always on top' window mode."""
        config.ENABLE_FOREGROUND = True
        return {"status": 200, "result": config.ENABLE_FOREGROUND}

    @staticmethod
    def setDisableForeground(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables the 'always on top' window mode."""
        config.ENABLE_FOREGROUND = False
        return {"status": 200, "result": config.ENABLE_FOREGROUND}

    @staticmethod
    def getSelectedTabNo(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the currently selected tab number from config."""
        return {"status": 200, "result": config.SELECTED_TAB_NO}

    def setSelectedTabNo(self, selected_tab_no: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the selected tab number, updates related engine lists, and returns the new tab number."""
        printLog("setSelectedTabNo", selected_tab_no)
        config.SELECTED_TAB_NO = selected_tab_no
        self.updateTranslationEngineAndEngineList()
        return {"status": 200, "result": config.SELECTED_TAB_NO}

    @staticmethod
    def getTranslationEngines(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the list of available translation engines based on current language settings."""
        # Type for engines needs to be List[str] based on usage
        engines: List[str] = model.findTranslationEngines(
            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
            config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS,
        )

        your_language = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]
        for target_language_settings in config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO].values():
            if your_language["language"] == target_language_settings["language"] and target_language_settings["enable"] is True:
                if config.SELECTABLE_TRANSLATION_ENGINE_STATUS.get("CTranslate2") is True: # Use .get for safety
                    engines = ["CTranslate2"]
                else:
                    engines = []
                break # Found a matching enabled target language, no need to check further

        return {"status": 200, "result": engines}

    @staticmethod
    def getListLanguageAndCountry(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the list of all supported languages and countries from the model."""
        return {"status": 200, "result": model.getListLanguageAndCountry()}

    @staticmethod
    def getMicHostList(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the list of microphone host APIs from the model."""
        return {"status": 200, "result": model.getListMicHost()}

    @staticmethod
    def getMicDeviceList(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the list of microphone devices from the model."""
        return {"status": 200, "result": model.getListMicDevice()}

    @staticmethod
    def getSpeakerDeviceList(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the list of speaker devices from the model."""
        return {"status": 200, "result": model.getListSpeakerDevice()}

    @staticmethod
    def getSelectedTranslationEngines(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the currently selected translation engines for each tab from config."""
        return {"status": 200, "result": config.SELECTED_TRANSLATION_ENGINES}

    @staticmethod
    def setSelectedTranslationEngines(data: Dict[str, str], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the translation engines for each tab in config."""
        config.SELECTED_TRANSLATION_ENGINES = data
        return {"status": 200, "result": config.SELECTED_TRANSLATION_ENGINES}

    @staticmethod
    def getSelectedYourLanguages(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the selected 'your' languages for transcription for each tab from config."""
        return {"status": 200, "result": config.SELECTED_YOUR_LANGUAGES}

    def setSelectedYourLanguages(self, select: Dict[str, Dict[str, Dict[str, Any]]], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets 'your' languages, updates engine lists, and returns the new selection."""
        config.SELECTED_YOUR_LANGUAGES = select
        self.updateTranslationEngineAndEngineList()
        return {"status": 200, "result": config.SELECTED_YOUR_LANGUAGES}

    @staticmethod
    def getSelectedTargetLanguages(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the selected target languages for translation for each tab from config."""
        return {"status": 200, "result": config.SELECTED_TARGET_LANGUAGES}

    def setSelectedTargetLanguages(self, select: Dict[str, Dict[str, Dict[str, Any]]], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets target languages, updates engine lists, and returns the new selection."""
        config.SELECTED_TARGET_LANGUAGES = select
        self.updateTranslationEngineAndEngineList()
        return {"status": 200, "result": config.SELECTED_TARGET_LANGUAGES}

    @staticmethod
    def getTranscriptionEngines(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the list of currently enabled transcription engines."""
        engines: List[str] = [key for key, value in config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS.items() if value is True]
        return {"status": 200, "result": engines}

    @staticmethod
    def getSelectedTranscriptionEngine(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the currently selected transcription engine from config."""
        return {"status": 200, "result": config.SELECTED_TRANSCRIPTION_ENGINE}

    @staticmethod
    def setSelectedTranscriptionEngine(data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the transcription engine in config."""
        config.SELECTED_TRANSCRIPTION_ENGINE = str(data) # Ensure it's a string
        return {"status": 200, "result": config.SELECTED_TRANSCRIPTION_ENGINE}

    @staticmethod
    def getConvertMessageToRomaji(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the 'convert to Romaji' status from config."""
        return {"status": 200, "result": config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def setEnableConvertMessageToRomaji(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables 'convert to Romaji' in config."""
        config.CONVERT_MESSAGE_TO_ROMAJI = True
        return {"status": 200, "result": config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def setDisableConvertMessageToRomaji(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables 'convert to Romaji' in config."""
        config.CONVERT_MESSAGE_TO_ROMAJI = False
        return {"status": 200, "result": config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def getConvertMessageToHiragana(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the 'convert to Hiragana' status from config."""
        return {"status": 200, "result": config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def setEnableConvertMessageToHiragana(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables 'convert to Hiragana' in config."""
        config.CONVERT_MESSAGE_TO_HIRAGANA = True
        return {"status": 200, "result": config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def setDisableConvertMessageToHiragana(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables 'convert to Hiragana' in config."""
        config.CONVERT_MESSAGE_TO_HIRAGANA = False
        return {"status": 200, "result": config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def getMainWindowSidebarCompactMode(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the main window sidebar compact mode status from config."""
        return {"status": 200, "result": config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def setEnableMainWindowSidebarCompactMode(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables main window sidebar compact mode in config."""
        config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
        return {"status": 200, "result": config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def setDisableMainWindowSidebarCompactMode(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables main window sidebar compact mode in config."""
        config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
        return {"status": 200, "result": config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def getTransparency(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the UI transparency level from config."""
        return {"status": 200, "result": config.TRANSPARENCY}

    @staticmethod
    def setTransparency(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the UI transparency level in config."""
        config.TRANSPARENCY = int(data) # Ensure int
        return {"status": 200, "result": config.TRANSPARENCY}

    @staticmethod
    def getUiScaling(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the UI scaling percentage from config."""
        return {"status": 200, "result": config.UI_SCALING}

    @staticmethod
    def setUiScaling(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the UI scaling percentage in config."""
        config.UI_SCALING = int(data) # Ensure int
        return {"status": 200, "result": config.UI_SCALING}

    @staticmethod
    def getTextboxUiScaling(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the textbox UI scaling percentage from config."""
        return {"status": 200, "result": config.TEXTBOX_UI_SCALING}

    @staticmethod
    def setTextboxUiScaling(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the textbox UI scaling percentage in config."""
        config.TEXTBOX_UI_SCALING = int(data) # Ensure int
        return {"status": 200, "result": config.TEXTBOX_UI_SCALING}

    @staticmethod
    def getMessageBoxRatio(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the message box height ratio from config."""
        return {"status": 200, "result": config.MESSAGE_BOX_RATIO}

    @staticmethod
    def setMessageBoxRatio(data: float, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the message box height ratio in config. Expects float or int."""
        config.MESSAGE_BOX_RATIO = float(data) # Ensure float
        return {"status": 200, "result": config.MESSAGE_BOX_RATIO}

    @staticmethod
    def getFontFamily(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the UI font family from config."""
        return {"status": 200, "result": config.FONT_FAMILY}

    @staticmethod
    def setFontFamily(data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the UI font family in config."""
        config.FONT_FAMILY = data
        return {"status": 200, "result": config.FONT_FAMILY}

    @staticmethod
    def getUiLanguage(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the UI language from config."""
        return {"status": 200, "result": config.UI_LANGUAGE}

    @staticmethod
    def setUiLanguage(data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the UI language in config."""
        config.UI_LANGUAGE = data
        return {"status": 200, "result": config.UI_LANGUAGE}

    @staticmethod
    def getMainWindowGeometry(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the main window geometry (position and size) from config."""
        return {"status": 200, "result": config.MAIN_WINDOW_GEOMETRY}

    @staticmethod
    def setMainWindowGeometry(data: Dict[str, int], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the main window geometry in config."""
        config.MAIN_WINDOW_GEOMETRY = data
        return {"status": 200, "result": config.MAIN_WINDOW_GEOMETRY}

    @staticmethod
    def getAutoMicSelect(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the automatic microphone selection status from config."""
        return {"status": 200, "result": config.AUTO_MIC_SELECT}

    def setEnableAutoMicSelect(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables automatic microphone selection and updates device manager callbacks."""
        config.AUTO_MIC_SELECT = True
        device_manager.setCallbackProcessBeforeUpdateDevices(self.stopAccessDevices)
        device_manager.setCallbackDefaultMicDevice(self.updateSelectedMicDevice)
        device_manager.setCallbackProcessAfterUpdateDevices(self.restartAccessDevices)
        device_manager.forceUpdateAndSetMicDevices()
        return {"status": 200, "result": config.AUTO_MIC_SELECT}

    @staticmethod
    def setDisableAutoMicSelect(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables automatic microphone selection and clears related device manager callbacks."""
        device_manager.clearCallbackProcessBeforeUpdateDevices()
        device_manager.clearCallbackDefaultMicDevice()
        device_manager.clearCallbackProcessAfterUpdateDevices()
        config.AUTO_MIC_SELECT = False
        return {"status": 200, "result": config.AUTO_MIC_SELECT}

    @staticmethod
    def getSelectedMicHost(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the selected microphone host API from config."""
        return {"status": 200, "result": config.SELECTED_MIC_HOST}

    def setSelectedMicHost(self, data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the microphone host API, updates default device, and restarts services if needed."""
        config.SELECTED_MIC_HOST = data
        config.SELECTED_MIC_DEVICE = model.getMicDefaultDevice() # Assumes this returns str
        if config.ENABLE_CHECK_ENERGY_SEND is True: # TODO: Should this be ENABLE_TRANSCRIPTION_SEND?
            self.stopThreadingCheckMicEnergy() # This seems mismatched if goal is to restart transcription
            self.startThreadingTranscriptionSendMessage()
        return {
            "status": 200,
            "result": {
                "host": config.SELECTED_MIC_HOST,
                "device": config.SELECTED_MIC_DEVICE,
            },
        }

    @staticmethod
    def getSelectedMicDevice(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the selected microphone device name from config."""
        return {"status": 200, "result": config.SELECTED_MIC_DEVICE}

    def setSelectedMicDevice(self, data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the microphone device name and restarts services if needed."""
        config.SELECTED_MIC_DEVICE = data
        if config.ENABLE_CHECK_ENERGY_SEND is True: # TODO: Similar to above, check if this is the correct flag
            self.stopThreadingCheckMicEnergy()
            self.startThreadingTranscriptionSendMessage()
        return {"status": 200, "result": config.SELECTED_MIC_DEVICE}

    @staticmethod
    def getMicThreshold(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the microphone audio threshold from config."""
        return {"status": 200, "result": config.MIC_THRESHOLD}

    @staticmethod
    def setMicThreshold(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the microphone audio threshold in config, with validation."""
        response: Dict[str, Any]
        try:
            value = int(data)
            if 0 <= value <= config.MAX_MIC_THRESHOLD:
                config.MIC_THRESHOLD = value
                response = {"status": 200, "result": config.MIC_THRESHOLD}
            else:
                raise ValueError("Mic energy threshold value is out of range")
        except ValueError as e:
            errorLogging(str(e))
            response = {
                "status": 400,
                "result": {
                    "message": str(e),
                    "data": config.MIC_THRESHOLD
                }
            }
        return response

    @staticmethod
    def getMicAutomaticThreshold(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the automatic microphone threshold status from config."""
        return {"status": 200, "result": config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setEnableMicAutomaticThreshold(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables automatic microphone threshold adjustment in config."""
        config.MIC_AUTOMATIC_THRESHOLD = True
        return {"status": 200, "result": config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableMicAutomaticThreshold(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables automatic microphone threshold adjustment in config."""
        config.MIC_AUTOMATIC_THRESHOLD = False
        return {"status": 200, "result": config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def getMicRecordTimeout(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the microphone recording timeout from config."""
        return {"status": 200, "result": config.MIC_RECORD_TIMEOUT}

    @staticmethod
    def setMicRecordTimeout(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the microphone recording timeout in config, with validation."""
        printLog("Set Mic Record Timeout", data)
        response: Dict[str, Any]
        try:
            value = int(data)
            if 0 <= value <= config.MIC_PHRASE_TIMEOUT:
                config.MIC_RECORD_TIMEOUT = value
                response = {"status": 200, "result": config.MIC_RECORD_TIMEOUT}
            else:
                raise ValueError("Mic record timeout value is out of range or greater than phrase timeout")
        except ValueError as e:
            errorLogging(str(e))
            response = {
                "status": 400,
                "result": {
                    "message": str(e),
                    "data": config.MIC_RECORD_TIMEOUT
                }
            }
        return response

    @staticmethod
    def getMicPhraseTimeout(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the microphone phrase timeout from config."""
        return {"status": 200, "result": config.MIC_PHRASE_TIMEOUT}

    @staticmethod
    def setMicPhraseTimeout(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the microphone phrase timeout in config, with validation."""
        response: Dict[str, Any]
        try:
            value = int(data)
            if value >= config.MIC_RECORD_TIMEOUT:
                config.MIC_PHRASE_TIMEOUT = value
                response = {"status": 200, "result": config.MIC_PHRASE_TIMEOUT}
            else:
                raise ValueError("Mic phrase timeout value is out of range or less than record timeout")
        except ValueError as e:
            errorLogging(str(e))
            response = {
                "status": 400,
                "result": {
                    "message": str(e),
                    "data": config.MIC_PHRASE_TIMEOUT
                }
            }
        return response

    @staticmethod
    def getMicMaxPhrases(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the maximum number of microphone phrases from config."""
        return {"status": 200, "result": config.MIC_MAX_PHRASES}

    @staticmethod
    def setMicMaxPhrases(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the maximum number of microphone phrases in config, with validation."""
        response: Dict[str, Any]
        try:
            value = int(data)
            if 0 <= value:
                config.MIC_MAX_PHRASES = value
                response = {"status": 200, "result": config.MIC_MAX_PHRASES}
            else:
                raise ValueError("Mic max phrases value must be non-negative")
        except ValueError as e:
            errorLogging(str(e))
            response = {
                "status": 400,
                "result": {
                    "message": str(e),
                    "data": config.MIC_MAX_PHRASES
                }
            }
        return response

    @staticmethod
    def getMicWordFilter(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the microphone word filter list from config."""
        return {"status": 200, "result": config.MIC_WORD_FILTER}

    @staticmethod
    def setMicWordFilter(data: List[str], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the microphone word filter list, sorts it, and updates the model's keyword processor."""
        # Assuming data is already List[str] from UI, ensure unique and order
        config.MIC_WORD_FILTER = sorted(list(set(data)), key=data.index if data else None)
        model.resetKeywordProcessor()
        model.addKeywords() # Assumes this uses config.MIC_WORD_FILTER
        return {"status": 200, "result": config.MIC_WORD_FILTER}

    @staticmethod
    def getMicAvgLogprob(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the microphone average log probability threshold from config."""
        return {"status": 200, "result": config.MIC_AVG_LOGPROB}

    @staticmethod
    def setMicAvgLogprob(data: float, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the microphone average log probability threshold in config."""
        config.MIC_AVG_LOGPROB = float(data)
        return {"status": 200, "result": config.MIC_AVG_LOGPROB}

    @staticmethod
    def getMicNoSpeechProb(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the microphone no speech probability threshold from config."""
        return {"status": 200, "result": config.MIC_NO_SPEECH_PROB}

    @staticmethod
    def setMicNoSpeechProb(data: float, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the microphone no speech probability threshold in config."""
        config.MIC_NO_SPEECH_PROB = float(data)
        return {"status": 200, "result": config.MIC_NO_SPEECH_PROB}

    @staticmethod
    def getAutoSpeakerSelect(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the automatic speaker selection status from config."""
        return {"status": 200, "result": config.AUTO_SPEAKER_SELECT}

    def setEnableAutoSpeakerSelect(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables automatic speaker selection and updates device manager callbacks."""
        config.AUTO_SPEAKER_SELECT = True
        device_manager.setCallbackProcessBeforeUpdateDevices(self.stopAccessDevices)
        device_manager.setCallbackDefaultSpeakerDevice(self.updateSelectedSpeakerDevice)
        device_manager.setCallbackProcessAfterUpdateDevices(self.restartAccessDevices)
        device_manager.forceUpdateAndSetSpeakerDevices()
        return {"status": 200, "result": config.AUTO_SPEAKER_SELECT}

    @staticmethod
    def setDisableAutoSpeakerSelect(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables automatic speaker selection and clears related device manager callbacks."""
        device_manager.clearCallbackProcessBeforeUpdateDevices()
        device_manager.clearCallbackDefaultSpeakerDevice()
        device_manager.clearCallbackProcessAfterUpdateDevices()
        config.AUTO_SPEAKER_SELECT = False
        return {"status": 200, "result": config.AUTO_SPEAKER_SELECT}

    @staticmethod
    def getSelectedSpeakerDevice(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the selected speaker device name from config."""
        return {"status": 200, "result": config.SELECTED_SPEAKER_DEVICE}

    def setSelectedSpeakerDevice(self, data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the speaker device name and restarts services if needed."""
        config.SELECTED_SPEAKER_DEVICE = data
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True: # TODO: Check if this is the correct flag/logic
            self.stopThreadingCheckSpeakerEnergy()
            self.startThreadingTranscriptionReceiveMessage()
        return {"status": 200, "result": config.SELECTED_SPEAKER_DEVICE}

    @staticmethod
    def getSpeakerThreshold(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the speaker audio threshold from config."""
        return {"status": 200, "result": config.SPEAKER_THRESHOLD}

    @staticmethod
    def setSpeakerThreshold(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the speaker audio threshold in config, with validation."""
        printLog("Set Speaker Energy Threshold", data)
        response: Dict[str, Any]
        try:
            value = int(data)
            if 0 <= value <= config.MAX_SPEAKER_THRESHOLD:
                config.SPEAKER_THRESHOLD = value
                response = {"status": 200, "result": config.SPEAKER_THRESHOLD}
            else:
                raise ValueError("Speaker energy threshold value is out of range")
        except ValueError as e:
            errorLogging(str(e))
            response = {
                "status": 400,
                "result": {
                    "message": str(e),
                    "data": config.SPEAKER_THRESHOLD
                }
            }
        return response

    @staticmethod
    def getSpeakerAutomaticThreshold(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the automatic speaker threshold status from config."""
        return {"status": 200, "result": config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setEnableSpeakerAutomaticThreshold(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables automatic speaker threshold adjustment in config."""
        config.SPEAKER_AUTOMATIC_THRESHOLD = True
        return {"status": 200, "result": config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableSpeakerAutomaticThreshold(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables automatic speaker threshold adjustment in config."""
        config.SPEAKER_AUTOMATIC_THRESHOLD = False
        return {"status": 200, "result": config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def getSpeakerRecordTimeout(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the speaker recording timeout from config."""
        return {"status": 200, "result": config.SPEAKER_RECORD_TIMEOUT}

    @staticmethod
    def setSpeakerRecordTimeout(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the speaker recording timeout in config, with validation."""
        response: Dict[str, Any]
        try:
            value = int(data)
            if 0 <= value <= config.SPEAKER_PHRASE_TIMEOUT:
                config.SPEAKER_RECORD_TIMEOUT = value
                response = {"status": 200, "result": config.SPEAKER_RECORD_TIMEOUT}
            else:
                raise ValueError("Speaker record timeout value is out of range or greater than phrase timeout")
        except ValueError as e:
            errorLogging(str(e))
            response = {
                "status": 400,
                "result": {
                    "message": str(e),
                    "data": config.SPEAKER_RECORD_TIMEOUT
                }
            }
        return response

    @staticmethod
    def getSpeakerPhraseTimeout(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the speaker phrase timeout from config."""
        return {"status": 200, "result": config.SPEAKER_PHRASE_TIMEOUT}

    @staticmethod
    def setSpeakerPhraseTimeout(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the speaker phrase timeout in config, with validation."""
        response: Dict[str, Any]
        try:
            value = int(data)
            if value >= config.SPEAKER_RECORD_TIMEOUT: # Corrected: should be value, not data
                config.SPEAKER_PHRASE_TIMEOUT = value
                response = {"status": 200, "result": config.SPEAKER_PHRASE_TIMEOUT}
            else:
                raise ValueError("Speaker phrase timeout value is out of range or less than record timeout")
        except ValueError as e:
            errorLogging(str(e))
            response = {
                "status": 400,
                "result": {
                    "message": str(e),
                    "data": config.SPEAKER_PHRASE_TIMEOUT
                }
            }
        return response

    @staticmethod
    def getSpeakerMaxPhrases(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the maximum number of speaker phrases from config."""
        return {"status": 200, "result": config.SPEAKER_MAX_PHRASES}

    @staticmethod
    def setSpeakerMaxPhrases(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the maximum number of speaker phrases in config, with validation."""
        printLog("Set Speaker Max Phrases", data)
        response: Dict[str, Any]
        try:
            value = int(data)
            if 0 <= value:
                config.SPEAKER_MAX_PHRASES = value
                response = {"status": 200, "result": config.SPEAKER_MAX_PHRASES}
            else:
                raise ValueError("Speaker max phrases value must be non-negative")
        except ValueError as e:
            errorLogging(str(e))
            response = {
                "status": 400,
                "result": {
                    "message": str(e),
                    "data": config.SPEAKER_MAX_PHRASES
                }
            }
        return response

    @staticmethod
    def getHotkeys(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the hotkey configurations from config."""
        return {"status": 200, "result": config.HOTKEYS}

    @staticmethod
    def setHotkeys(data: Dict[str, Optional[List[str]]], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the hotkey configurations in config."""
        config.HOTKEYS = data
        return {"status": 200, "result": config.HOTKEYS}

    @staticmethod
    def getPluginsStatus(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the status of installed plugins from config."""
        return {"status": 200, "result": config.PLUGINS_STATUS}

    @staticmethod
    def setPluginsStatus(data: List[Dict[str, Any]], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the status of installed plugins in config."""
        config.PLUGINS_STATUS = data
        return {"status": 200, "result": config.PLUGINS_STATUS}

    @staticmethod
    def getSpeakerAvgLogprob(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the speaker average log probability threshold from config."""
        return {"status": 200, "result": config.SPEAKER_AVG_LOGPROB}

    @staticmethod
    def setSpeakerAvgLogprob(data: float, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the speaker average log probability threshold in config."""
        config.SPEAKER_AVG_LOGPROB = float(data)
        return {"status": 200, "result": config.SPEAKER_AVG_LOGPROB}

    @staticmethod
    def getSpeakerNoSpeechProb(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the speaker no speech probability threshold from config."""
        return {"status": 200, "result": config.SPEAKER_NO_SPEECH_PROB}

    @staticmethod
    def setSpeakerNoSpeechProb(data: float, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the speaker no speech probability threshold in config."""
        config.SPEAKER_NO_SPEECH_PROB = float(data)
        return {"status": 200, "result": config.SPEAKER_NO_SPEECH_PROB}

    @staticmethod
    def getOscIpAddress(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the OSC IP address from config."""
        return {"status": 200, "result": config.OSC_IP_ADDRESS}

    @staticmethod
    def setOscIpAddress(data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the OSC IP address in config and model, with validation."""
        response: Dict[str, Any]
        if not isValidIpAddress(data):
            response = {
                "status": 400,
                "result": {
                    "message": "Invalid IP address",
                    "data": config.OSC_IP_ADDRESS
                }
            }
        else:
            try:
                model.setOscIpAddress(data)
                config.OSC_IP_ADDRESS = data
                response = {"status": 200, "result": config.OSC_IP_ADDRESS}
            except Exception as e: # Broad exception, consider if model.setOscIpAddress can raise specific errors
                errorLogging(f"Failed to set OSC IP Address: {e}")
                # Attempt to revert to old IP in model if possible, though config already changed.
                # This part of logic might need review for atomicity or clearer error propagation.
                model.setOscIpAddress(config.OSC_IP_ADDRESS) # Revert if possible
                response = {
                    "status": 400,
                    "result": {
                        "message": "Cannot set IP address in OSC model.",
                        "data": config.OSC_IP_ADDRESS # Return current (potentially new but failed in model) config value
                    }
                }
        return response

    @staticmethod
    def getOscPort(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the OSC port from config."""
        return {"status": 200, "result": config.OSC_PORT}

    @staticmethod
    def setOscPort(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the OSC port in config and model."""
        config.OSC_PORT = int(data) # Ensure int
        model.setOscPort(config.OSC_PORT)
        return {"status": 200, "result": config.OSC_PORT}

    @staticmethod
    def getNotificationVrcSfx(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the VRChat notification sound effect status from config."""
        return {"status": 200, "result": config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def setEnableNotificationVrcSfx(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables VRChat notification sound effects in config."""
        config.NOTIFICATION_VRC_SFX = True
        return {"status": 200, "result": config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def setDisableNotificationVrcSfx(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables VRChat notification sound effects in config."""
        config.NOTIFICATION_VRC_SFX = False
        return {"status": 200, "result": config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def getDeepLAuthKey(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the DeepL API authentication key from config."""
        return {"status": 200, "result": config.AUTH_KEYS.get("DeepL_API")} # Use .get for safety

    def setDeeplAuthKey(self, data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets and validates the DeepL API authentication key."""
        printLog("Set DeepL Auth Key", "********") # Avoid logging the key itself
        translator_name = "DeepL_API"
        response: Dict[str, Any]
        try:
            auth_key_candidate = str(data)
            if not (len(auth_key_candidate) == 36 or len(auth_key_candidate) == 39): # Check length
                raise ValueError("DeepL auth key length is not correct")

            validation_result = model.authenticationTranslatorDeepLAuthKey(auth_key=auth_key_candidate)
            if validation_result is True:
                auth_keys = config.AUTH_KEYS.copy() # Modify a copy
                auth_keys[translator_name] = auth_key_candidate
                config.AUTH_KEYS = auth_keys
                # Assuming SELECTABLE_TRANSLATION_ENGINE_STATUS is Dict[str, bool]
                engine_status = config.SELECTABLE_TRANSLATION_ENGINE_STATUS.copy()
                engine_status[translator_name] = True
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS = engine_status
                self.updateTranslationEngineAndEngineList()
                response = {"status": 200, "result": config.AUTH_KEYS.get(translator_name)}
            else:
                raise ValueError("Authentication failure of DeepL auth key")

        except ValueError as e: # Catch specific validation error
            errorLogging(str(e))
            response = {
                "status": 400,
                "result": {
                    "message": str(e),
                    "data": config.AUTH_KEYS.get(translator_name) # Current key, might be None
                }
            }
        except Exception as e: # Catch other unexpected errors
            errorLogging(f"Unexpected error setting DeepL Auth Key: {e}")
            response = {
                "status": 500, # Internal server error
                "result": {
                    "message": f"An unexpected error occurred: {e}",
                    "data": config.AUTH_KEYS.get(translator_name)
                }
            }
        return response

    def delDeeplAuthKey(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Deletes the DeepL API authentication key from config and updates engine status."""
        translator_name = "DeepL_API"
        auth_keys = config.AUTH_KEYS.copy()
        if translator_name in auth_keys:
            auth_keys[translator_name] = None
            config.AUTH_KEYS = auth_keys

        engine_status = config.SELECTABLE_TRANSLATION_ENGINE_STATUS.copy()
        engine_status[translator_name] = False
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = engine_status

        self.updateTranslationEngineAndEngineList()
        return {"status": 200, "result": config.AUTH_KEYS.get(translator_name)} # Should be None

    @staticmethod
    def getCtranslate2WeightType(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the selected CTranslate2 weight type from config."""
        return {"status": 200, "result": config.CTRANSLATE2_WEIGHT_TYPE}

    @staticmethod
    def setCtranslate2WeightType(data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the CTranslate2 weight type, and reloads the model if the weight is available."""
        config.CTRANSLATE2_WEIGHT_TYPE = str(data)
        if model.checkTranslatorCTranslate2ModelWeight(config.CTRANSLATE2_WEIGHT_TYPE):
            # Consider if join() is appropriate here, might block UI thread if called directly
            # If this is meant to be async, the thread should be managed (e.g., not joined immediately)
            # or this method should be called in a separate thread by the caller.
            def callback() -> None:
                model.changeTranslatorCTranslate2Model()
            th_callback = Thread(target=callback)
            th_callback.daemon = True
            th_callback.start()
            th_callback.join() # This makes the call synchronous regarding model change
        return {"status": 200, "result": config.CTRANSLATE2_WEIGHT_TYPE}

    @staticmethod
    def getWhisperWeightType(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the selected Whisper weight type from config."""
        return {"status": 200, "result": config.WHISPER_WEIGHT_TYPE}

    @staticmethod
    def setWhisperWeightType(data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the Whisper weight type in config."""
        # TODO: Consider if Whisper model needs reloading similar to CTranslate2
        config.WHISPER_WEIGHT_TYPE = str(data)
        return {"status": 200, "result": config.WHISPER_WEIGHT_TYPE}

    @staticmethod
    def getAutoClearMessageBox(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the auto clear message box status from config."""
        return {"status": 200, "result": config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def setEnableAutoClearMessageBox(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables auto clearing the message box in config."""
        config.AUTO_CLEAR_MESSAGE_BOX = True
        return {"status": 200, "result": config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def setDisableAutoClearMessageBox(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables auto clearing the message box in config."""
        config.AUTO_CLEAR_MESSAGE_BOX = False
        return {"status": 200, "result": config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def getSendOnlyTranslatedMessages(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the 'send only translated messages' status from config."""
        return {"status": 200, "result": config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setEnableSendOnlyTranslatedMessages(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables 'send only translated messages' in config."""
        config.SEND_ONLY_TRANSLATED_MESSAGES = True
        return {"status": 200, "result": config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableSendOnlyTranslatedMessages(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables 'send only translated messages' in config."""
        config.SEND_ONLY_TRANSLATED_MESSAGES = False
        return {"status": 200, "result": config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def getSendMessageButtonType(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the send message button type from config."""
        return {"status": 200, "result": config.SEND_MESSAGE_BUTTON_TYPE}

    @staticmethod
    def setSendMessageButtonType(data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the send message button type in config."""
        config.SEND_MESSAGE_BUTTON_TYPE = data
        return {"status": 200, "result": config.SEND_MESSAGE_BUTTON_TYPE}

    @staticmethod
    def getOverlaySmallLog(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the small log overlay enabled status from config."""
        return {"status": 200, "result": config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setEnableOverlaySmallLog(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables the small log overlay and starts the overlay if not already active."""
        config.OVERLAY_SMALL_LOG = True
        if config.OVERLAY_LARGE_LOG is False: # Only start if large log isn't also active
            model.startOverlay()
        return {"status": 200, "result": config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setDisableOverlaySmallLog(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables the small log overlay and shuts down overlay if large log is also inactive."""
        config.OVERLAY_SMALL_LOG = False
        model.clearOverlayImageSmallLog()
        if config.OVERLAY_LARGE_LOG is False: # Only shutdown if large log isn't active
            model.shutdownOverlay()
        return {"status": 200, "result": config.OVERLAY_SMALL_LOG}

    @staticmethod
    def getOverlaySmallLogSettings(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the settings for the small log overlay from config."""
        return {"status": 200, "result": config.OVERLAY_SMALL_LOG_SETTINGS}

    @staticmethod
    def setOverlaySmallLogSettings(data: Dict[str, Any], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the settings for the small log overlay and updates the model."""
        config.OVERLAY_SMALL_LOG_SETTINGS = data
        model.updateOverlaySmallLogSettings()
        return {"status": 200, "result": config.OVERLAY_SMALL_LOG_SETTINGS}

    @staticmethod
    def getOverlayLargeLog(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the large log overlay enabled status from config."""
        return {"status": 200, "result": config.OVERLAY_LARGE_LOG}

    @staticmethod
    def setEnableOverlayLargeLog(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables the large log overlay and starts the overlay if not already active."""
        config.OVERLAY_LARGE_LOG = True
        if config.OVERLAY_SMALL_LOG is False: # Only start if small log isn't also active
            model.startOverlay()
        return {"status": 200, "result": config.OVERLAY_LARGE_LOG}

    @staticmethod
    def setDisableOverlayLargeLog(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables the large log overlay and shuts down overlay if small log is also inactive."""
        config.OVERLAY_LARGE_LOG = False
        model.clearOverlayImageLargeLog()
        if config.OVERLAY_SMALL_LOG is False: # Only shutdown if small log isn't active
            model.shutdownOverlay()
        return {"status": 200, "result": config.OVERLAY_LARGE_LOG}

    @staticmethod
    def getOverlayLargeLogSettings(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the settings for the large log overlay from config."""
        return {"status": 200, "result": config.OVERLAY_LARGE_LOG_SETTINGS}

    @staticmethod
    def setOverlayLargeLogSettings(data: Dict[str, Any], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the settings for the large log overlay and updates the model."""
        config.OVERLAY_LARGE_LOG_SETTINGS = data
        model.updateOverlayLargeLogSettings()
        return {"status": 200, "result": config.OVERLAY_LARGE_LOG_SETTINGS}

    @staticmethod
    def getOverlayShowOnlyTranslatedMessages(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the 'overlay show only translated messages' status from config."""
        return {"status": 200, "result": config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setEnableOverlayShowOnlyTranslatedMessages(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables 'overlay show only translated messages' in config."""
        config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = True
        return {"status": 200, "result": config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableOverlayShowOnlyTranslatedMessages(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables 'overlay show only translated messages' in config."""
        config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = False
        return {"status": 200, "result": config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def getSendMessageToVrc(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the 'send message to VRChat' status from config."""
        return {"status": 200, "result": config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def setEnableSendMessageToVrc(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables sending messages to VRChat in config."""
        config.SEND_MESSAGE_TO_VRC = True
        return {"status": 200, "result": config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendMessageToVrc(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables sending messages to VRChat in config."""
        config.SEND_MESSAGE_TO_VRC = False
        return {"status": 200, "result": config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def getSendReceivedMessageToVrc(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the 'send received message to VRChat' status from config."""
        return {"status": 200, "result": config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def setEnableSendReceivedMessageToVrc(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables sending received messages to VRChat in config."""
        config.SEND_RECEIVED_MESSAGE_TO_VRC = True
        return {"status": 200, "result": config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendReceivedMessageToVrc(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables sending received messages to VRChat in config."""
        config.SEND_RECEIVED_MESSAGE_TO_VRC = False
        return {"status": 200, "result": config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def getLoggerFeature(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the logger feature status from config."""
        return {"status": 200, "result": config.LOGGER_FEATURE}

    @staticmethod
    def setEnableLoggerFeature(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables the logger feature and starts the logger in the model."""
        config.LOGGER_FEATURE = True
        model.startLogger()
        return {"status": 200, "result": config.LOGGER_FEATURE}

    @staticmethod
    def setDisableLoggerFeature(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables the logger feature and stops the logger in the model."""
        model.stopLogger() # Ensure logger is stopped before changing config
        config.LOGGER_FEATURE = False
        return {"status": 200, "result": config.LOGGER_FEATURE}

    @staticmethod
    def getVrcMicMuteSync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the VRChat microphone mute sync status from config."""
        return {"status": 200, "result": config.VRC_MIC_MUTE_SYNC}

    @staticmethod
    def setEnableVrcMicMuteSync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables VRChat microphone mute sync if OSC query is not enabled."""
        # This logic seems a bit inverted: if OSC Query is NOT enabled, then sync is enabled.
        # And if OSC Query IS enabled, sync is set to False.
        if model.getIsOscQueryEnabled() is False:
            config.VRC_MIC_MUTE_SYNC = True
            model.setMuteSelfStatus()
            model.changeMicTranscriptStatus()
        else:
            # If OSC Query is enabled, VRC_MIC_MUTE_SYNC is forced false.
            config.VRC_MIC_MUTE_SYNC = False
        return {"status": 200, "result": config.VRC_MIC_MUTE_SYNC}

    @staticmethod
    def setDisableVrcMicMuteSync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables VRChat microphone mute sync."""
        config.VRC_MIC_MUTE_SYNC = False
        model.changeMicTranscriptStatus()
        return {"status": 200, "result": config.VRC_MIC_MUTE_SYNC}

    def setEnableCheckSpeakerThreshold(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables checking speaker audio energy and starts the checker thread."""
        self.startThreadingCheckSpeakerEnergy()
        config.ENABLE_CHECK_ENERGY_RECEIVE = True
        return {"status": 200, "result": config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setDisableCheckSpeakerThreshold(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables checking speaker audio energy and stops the checker thread."""
        self.stopThreadingCheckSpeakerEnergy()
        config.ENABLE_CHECK_ENERGY_RECEIVE = False
        return {"status": 200, "result": config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setEnableCheckMicThreshold(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables checking microphone audio energy and starts the checker thread."""
        self.startThreadingCheckMicEnergy()
        config.ENABLE_CHECK_ENERGY_SEND = True
        return {"status": 200, "result": config.ENABLE_CHECK_ENERGY_SEND}

    def setDisableCheckMicThreshold(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables checking microphone audio energy and stops the checker thread."""
        self.stopThreadingCheckMicEnergy()
        config.ENABLE_CHECK_ENERGY_SEND = False
        return {"status": 200, "result": config.ENABLE_CHECK_ENERGY_SEND}

    @staticmethod
    def openFilepathLogs(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Opens the logs directory in the system's file explorer."""
        # Popen is okay for fire-and-forget, no specific return type for Popen needed here.
        Popen(['explorer', config.PATH_LOGS.replace('/', '\\')], shell=True)
        return {"status": 200, "result": True}

    @staticmethod
    def openFilepathConfigFile(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Opens the local application directory (containing config.json) in the file explorer."""
        Popen(['explorer', config.PATH_LOCAL.replace('/', '\\')], shell=True)
        return {"status": 200, "result": True}

    def setEnableTranscriptionSend(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables sending transcriptions and starts the transcription thread."""
        self.startThreadingTranscriptionSendMessage()
        config.ENABLE_TRANSCRIPTION_SEND = True
        return {"status": 200, "result": config.ENABLE_TRANSCRIPTION_SEND}

    def setDisableTranscriptionSend(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables sending transcriptions and stops the transcription thread."""
        self.stopThreadingTranscriptionSendMessage()
        config.ENABLE_TRANSCRIPTION_SEND = False
        return {"status": 200, "result": config.ENABLE_TRANSCRIPTION_SEND}

    def setEnableTranscriptionReceive(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables receiving transcriptions and starts the transcription thread."""
        self.startThreadingTranscriptionReceiveMessage()
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        return {"status": 200, "result": config.ENABLE_TRANSCRIPTION_RECEIVE}

    def setDisableTranscriptionReceive(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables receiving transcriptions and stops the transcription thread."""
        self.stopThreadingTranscriptionReceiveMessage()
        config.ENABLE_TRANSCRIPTION_RECEIVE = False
        return {"status": 200, "result": config.ENABLE_TRANSCRIPTION_RECEIVE}

    def sendMessageBox(self, data: Dict[str, str], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sends a message from the message box, processing it via chatMessage."""
        response = self.chatMessage(data)
        return response

    @staticmethod
    def typingMessageBox(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Notifies VRChat that the user is typing if OSC sending is enabled."""
        if config.SEND_MESSAGE_TO_VRC is True:
            model.oscStartSendTyping()
        return {"status": 200, "result": True}

    @staticmethod
    def stopTypingMessageBox(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Notifies VRChat that the user has stopped typing if OSC sending is enabled."""
        if config.SEND_MESSAGE_TO_VRC is True:
            model.oscStopSendTyping()
        return {"status": 200, "result": True}

    @staticmethod
    def sendTextOverlay(data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sends text to be displayed on the game overlay."""
        # Assuming model.createOverlayImage... returns an image object or compatible data
        overlay_image_small: Optional[Any] = None
        overlay_image_large: Optional[Any] = None

        if config.OVERLAY_SMALL_LOG is True and model.overlay.initialized is True:
            overlay_image_small = model.createOverlayImageSmallMessage(data)
            if overlay_image_small:
                model.updateOverlaySmallLog(overlay_image_small)

        if config.OVERLAY_LARGE_LOG is True and model.overlay.initialized is True:
            overlay_image_large = model.createOverlayImageLargeMessage(data)
            if overlay_image_large:
                model.updateOverlayLargeLog(overlay_image_large)
        return {"status": 200, "result": data}

    def swapYourLanguageAndTargetLanguage(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Swaps the 'your' and 'target' languages for the current tab and updates config."""
        # Ensure deep copies if these are mutable dicts to avoid unintended side effects
        your_languages = config.SELECTED_YOUR_LANGUAGES.copy()
        target_languages = config.SELECTED_TARGET_LANGUAGES.copy()

        # It seems like it's always swapping the "1" entry.
        # This logic might need review if multiple your/target languages per tab are truly supported.
        your_language_temp = your_languages.get(config.SELECTED_TAB_NO, {}).get("1")
        target_language_temp = target_languages.get(config.SELECTED_TAB_NO, {}).get("1")

        if your_language_temp and target_language_temp:
            if config.SELECTED_TAB_NO not in your_languages: your_languages[config.SELECTED_TAB_NO] = {}
            if config.SELECTED_TAB_NO not in target_languages: target_languages[config.SELECTED_TAB_NO] = {}

            your_languages[config.SELECTED_TAB_NO]["1"] = target_language_temp
            target_languages[config.SELECTED_TAB_NO]["1"] = your_language_temp

            self.setSelectedYourLanguages(your_languages) # This will call updateTranslationEngineAndEngineList
            self.setSelectedTargetLanguages(target_languages) # This will also call it

        return {
            "status": 200,
            "result": {
                "your": config.SELECTED_YOUR_LANGUAGES,
                "target": config.SELECTED_TARGET_LANGUAGES,
            }
        }

    def updateSoftware(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Initiates a software update in a separate thread."""
        th_start_update_software = Thread(target=model.updateSoftware)
        th_start_update_software.daemon = True
        th_start_update_software.start()
        return {"status": 200, "result": True}

    def updateCudaSoftware(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Initiates a CUDA-specific software update in a separate thread."""
        th_start_update_cuda_software = Thread(target=model.updateCudaSoftware)
        th_start_update_cuda_software.daemon = True
        th_start_update_cuda_software.start()
        return {"status": 200, "result": True}

    def downloadCtranslate2Weight(self, data: str, asynchronous: bool = True, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Downloads CTranslate2 model weights, optionally asynchronously."""
        weight_type = str(data)
        # Ensure self.run is not None if DownloadCTranslate2 relies on it
        if self.run is None:
            # Handle error: self.run is not set
            return {"status": 500, "result": False, "message": "Run callback not set."}

        download_ctranslate2 = self.DownloadCTranslate2(
            self.run_mapping,
            weight_type,
            self.run
        )

        if asynchronous:
            self.startThreadingDownloadCtranslate2Weight(
                weight_type,
                download_ctranslate2.progressBar,
                download_ctranslate2.downloaded,
            )
        else:
            # This part might block if downloadCTranslate2ModelWeight is blocking
            model.downloadCTranslate2ModelWeight(weight_type, download_ctranslate2.progressBar, download_ctranslate2.downloaded)
        # Tokenizer download seems to happen regardless of async main weights
        model.downloadCTranslate2ModelTokenizer(weight_type)
        return {"status": 200, "result": True}

    def downloadWhisperWeight(self, data: str, asynchronous: bool = True, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Downloads Whisper model weights, optionally asynchronously."""
        weight_type = str(data)
        if self.run is None:
            return {"status": 500, "result": False, "message": "Run callback not set."}

        download_whisper = self.DownloadWhisper(
            self.run_mapping,
            weight_type,
            self.run
        )
        if asynchronous:
            self.startThreadingDownloadWhisperWeight(
                weight_type,
                download_whisper.progressBar,
                download_whisper.downloaded,
            )
        else:
            model.downloadWhisperModelWeight(weight_type, download_whisper.progressBar, download_whisper.downloaded)
        return {"status": 200, "result": True}

    @staticmethod
    def messageFormatter(format_type: str, translation: List[str], message: List[str]) -> str:
        """Formats a message string for OSC based on type (SEND/RECEIVED) and translation availability."""
        osc_message: str
        if format_type == "RECEIVED":
            FORMAT_WITH_T = config.RECEIVED_MESSAGE_FORMAT_WITH_T
            FORMAT = config.RECEIVED_MESSAGE_FORMAT
        elif format_type == "SEND":
            FORMAT_WITH_T = config.SEND_MESSAGE_FORMAT_WITH_T
            FORMAT = config.SEND_MESSAGE_FORMAT
        else:
            raise ValueError(f"format_type '{format_type}' is not supported.")

        if translation: # Check if translation list is not empty
            osc_message = FORMAT_WITH_T.replace("[message]", "\n".join(message))
            osc_message = osc_message.replace("[translation]", "\n".join(translation))
        else:
            osc_message = FORMAT.replace("[message]", "\n".join(message))
        return osc_message

    def changeToCTranslate2Process(self) -> None:
        """Switches the translation engine to CTranslate2 if the current one fails or is limited."""
        selected_engines = config.SELECTED_TRANSLATION_ENGINES
        current_engine_for_tab = selected_engines.get(config.SELECTED_TAB_NO)

        if current_engine_for_tab:
            engine_status = config.SELECTABLE_TRANSLATION_ENGINE_STATUS.copy()
            engine_status[current_engine_for_tab] = False
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS = engine_status

        new_selected_engines = selected_engines.copy()
        new_selected_engines[config.SELECTED_TAB_NO] = "CTranslate2"
        config.SELECTED_TRANSLATION_ENGINES = new_selected_engines

        selectable_engines_response = self.getTranslationEngines() # This is Dict[str, Any]
        selectable_engines: List[str] = selectable_engines_response.get("result", [])

        if self.run and "selected_translation_engines" in self.run_mapping and "translation_engines" in self.run_mapping:
            self.run(200, self.run_mapping["selected_translation_engines"], config.SELECTED_TRANSLATION_ENGINES)
            self.run(200, self.run_mapping["translation_engines"], selectable_engines)

    def startTranscriptionSendMessage(self) -> None:
        """Starts microphone transcription if device access is available."""
        while self.device_access_status is False: # Busy wait, consider alternatives if perf issue
            sleep(0.1) # Small sleep to yield execution
        self.device_access_status = False
        try:
            model.startMicTranscript(self.micMessage)
        finally:
            self.device_access_status = True # Ensure status is reset even if startMicTranscript fails

    @staticmethod
    def stopTranscriptionSendMessage() -> None:
        """Stops microphone transcription."""
        model.stopMicTranscript()

    def startThreadingTranscriptionSendMessage(self) -> None:
        """Starts microphone transcription in a new daemon thread."""
        th_startTranscriptionSendMessage = Thread(target=self.startTranscriptionSendMessage)
        th_startTranscriptionSendMessage.daemon = True
        th_startTranscriptionSendMessage.start()

    def stopThreadingTranscriptionSendMessage(self) -> None:
        """Stops microphone transcription via a new daemon thread and waits for it."""
        th_stopTranscriptionSendMessage = Thread(target=self.stopTranscriptionSendMessage)
        th_stopTranscriptionSendMessage.daemon = True
        th_stopTranscriptionSendMessage.start()
        th_stopTranscriptionSendMessage.join() # Consider timeout if stop can hang

    def startTranscriptionReceiveMessage(self) -> None:
        """Starts speaker transcription if device access is available."""
        while self.device_access_status is False: # Busy wait
            sleep(0.1)
        self.device_access_status = False
        try:
            model.startSpeakerTranscript(self.speakerMessage)
        finally:
            self.device_access_status = True

    @staticmethod
    def stopTranscriptionReceiveMessage() -> None:
        """Stops speaker transcription."""
        model.stopSpeakerTranscript()

    def startThreadingTranscriptionReceiveMessage(self) -> None:
        """Starts speaker transcription in a new daemon thread."""
        th_startTranscriptionReceiveMessage = Thread(target=self.startTranscriptionReceiveMessage)
        th_startTranscriptionReceiveMessage.daemon = True
        th_startTranscriptionReceiveMessage.start()

    def stopThreadingTranscriptionReceiveMessage(self) -> None:
        """Stops speaker transcription via a new daemon thread and waits for it."""
        th_stopTranscriptionReceiveMessage = Thread(target=self.stopTranscriptionReceiveMessage)
        th_stopTranscriptionReceiveMessage.daemon = True
        th_stopTranscriptionReceiveMessage.start()
        th_stopTranscriptionReceiveMessage.join() # Consider timeout

    @staticmethod
    def replaceExclamationsWithRandom(text: str) -> Tuple[str, Dict[str, str]]:
        """Replaces content within ![...] with placeholders and returns the modified text and map."""
        pattern = r'!\[(.*?)\]'
        replacement_dict: Dict[str, str] = {}
        current_num = 4096 # Use a different name to avoid conflict if this class were nested

        def replace_func(match: re.Match[str]) -> str:
            nonlocal current_num # Use nonlocal to modify outer scope variable
            original_content = match.group(1)
            placeholder_hex = hex(current_num)
            replacement_dict[placeholder_hex] = original_content
            current_num += 1
            return f" ${placeholder_hex} " # Add spaces for easier restoration

        replaced_text = re.sub(pattern, replace_func, text)
        return replaced_text, replacement_dict

    @staticmethod
    def restoreText(escaped_text: str, escape_dict: Dict[str, str]) -> str:
        """Restores placeholders in text using the provided mapping dictionary."""
        restored_text = escaped_text
        for escape_seq, original_char in escape_dict.items():
            # Pattern to match placeholder with optional spaces around it
            pattern = re.escape(f"${escape_seq}") + r"\s*|\$\s+" + re.escape(escape_seq) + r"\s*"
            # Ensure original_char is escaped if it contains special regex characters
            restored_text = re.sub(pattern, re.escape(original_char), restored_text, flags=re.IGNORECASE)
        return restored_text

    @staticmethod
    def removeExclamations(text: str) -> str:
        """Removes the ![...] wrapper, keeping only the content within the brackets."""
        pattern = r'!\[(.*?)\]'
        cleaned_text = re.sub(pattern, r'\1', text)
        return cleaned_text

    def updateDownloadedCTranslate2ModelWeight(self) -> None:
        """Updates the status of downloaded CTranslate2 model weights in config."""
        weight_type_dict = config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT.copy()
        for weight_type in weight_type_dict.keys(): # Iterate over original keys
            weight_type_dict[weight_type] = model.checkTranslatorCTranslate2ModelWeight(weight_type)
        config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT = weight_type_dict

    def updateTranslationEngineAndEngineList(self) -> None:
        """Updates selected translation engine based on availability and notifies UI."""
        current_engines = config.SELECTED_TRANSLATION_ENGINES.copy()
        engine_for_tab = current_engines.get(config.SELECTED_TAB_NO, "CTranslate2") # Default to CTranslate2

        selectable_engines_response = self.getTranslationEngines() # This is Dict[str, Any]
        selectable_engines: List[str] = selectable_engines_response.get("result", [])

        if engine_for_tab not in selectable_engines:
            engine_for_tab = "CTranslate2" # Fallback if current is not selectable
        current_engines[config.SELECTED_TAB_NO] = engine_for_tab
        config.SELECTED_TRANSLATION_ENGINES = current_engines

        # Special case: if "your" and "target" languages are the same, force CTranslate2
        your_language_settings = config.SELECTED_YOUR_LANGUAGES.get(config.SELECTED_TAB_NO, {}).get("1")
        target_languages_for_tab = config.SELECTED_TARGET_LANGUAGES.get(config.SELECTED_TAB_NO, {})
        if your_language_settings:
            for target_lang_settings in target_languages_for_tab.values():
                if target_lang_settings.get("enable") and your_language_settings.get("language") == target_lang_settings.get("language"):
                    current_engines[config.SELECTED_TAB_NO] = "CTranslate2"
                    config.SELECTED_TRANSLATION_ENGINES = current_engines
                    break # Found matching enabled target language

        if self.run and "selected_translation_engines" in self.run_mapping and "translation_engines" in self.run_mapping:
            self.run(200, self.run_mapping["selected_translation_engines"], config.SELECTED_TRANSLATION_ENGINES)
            self.run(200, self.run_mapping["translation_engines"], selectable_engines)


    def updateDownloadedWhisperModelWeight(self) -> None:
        """Updates the status of downloaded Whisper model weights in config."""
        weight_type_dict = config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT.copy()
        for weight_type in weight_type_dict.keys():
            weight_type_dict[weight_type] = model.checkTranscriptionWhisperModelWeight(weight_type)
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = weight_type_dict

    def updateTranscriptionEngine(self) -> None:
        """Updates the selected transcription engine based on availability and weight status."""
        weight_type = config.WHISPER_WEIGHT_TYPE
        # Ensure SELECTABLE_WHISPER_WEIGHT_TYPE_DICT is correctly populated before this call
        weight_available = bool(config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT.get(weight_type))
        current_engine = config.SELECTED_TRANSCRIPTION_ENGINE
        # Ensure SELECTABLE_TRANSCRIPTION_ENGINE_STATUS is correctly populated
        selectable_engines = [key for key, value in config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS.items() if value is True]

        if current_engine in {"Whisper", "Google"}:
            if current_engine not in selectable_engines: # If current is not even an option
                if weight_available and "Whisper" in selectable_engines: # Try to fall back to Whisper if its weight is there
                    config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
                elif "Google" in selectable_engines: # Then try Google
                    config.SELECTED_TRANSCRIPTION_ENGINE = "Google"
                else: # If neither are available, set to None or a sensible default
                    config.SELECTED_TRANSCRIPTION_ENGINE = None # Or perhaps "Whisper" if it's a primary default
        elif "Whisper" in selectable_engines and weight_available: # If current is something else, prefer Whisper if available
             config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        elif "Google" in selectable_engines: # Then Google
             config.SELECTED_TRANSCRIPTION_ENGINE = "Google"
        else: # Fallback
            config.SELECTED_TRANSCRIPTION_ENGINE = None


    def startCheckMicEnergy(self) -> None:
        """Starts microphone energy checking if device access is available."""
        while self.device_access_status is False:
            sleep(0.1)
        self.device_access_status = False
        try:
            model.startCheckMicEnergy(self.progressBarMicEnergy)
        finally:
            self.device_access_status = True

    def startThreadingCheckMicEnergy(self) -> None:
        """Starts microphone energy checking in a new daemon thread."""
        th_startCheckMicEnergy = Thread(target=self.startCheckMicEnergy)
        th_startCheckMicEnergy.daemon = True
        th_startCheckMicEnergy.start()

    def stopCheckMicEnergy(self) -> None:
        """Stops microphone energy checking."""
        model.stopCheckMicEnergy()

    def stopThreadingCheckMicEnergy(self) -> None:
        """Stops microphone energy checking via a new daemon thread and waits for it."""
        th_stopCheckMicEnergy = Thread(target=self.stopCheckMicEnergy)
        th_stopCheckMicEnergy.daemon = True
        th_stopCheckMicEnergy.start()
        th_stopCheckMicEnergy.join() # Consider timeout

    def startCheckSpeakerEnergy(self) -> None:
        """Starts speaker energy checking if device access is available."""
        while self.device_access_status is False:
            sleep(0.1)
        self.device_access_status = False
        try:
            model.startCheckSpeakerEnergy(self.progressBarSpeakerEnergy)
        finally:
            self.device_access_status = True

    def startThreadingCheckSpeakerEnergy(self) -> None:
        """Starts speaker energy checking in a new daemon thread."""
        th_startCheckSpeakerEnergy = Thread(target=self.startCheckSpeakerEnergy)
        th_startCheckSpeakerEnergy.daemon = True
        th_startCheckSpeakerEnergy.start()

    def stopCheckSpeakerEnergy(self) -> None:
        """Stops speaker energy checking."""
        model.stopCheckSpeakerEnergy()

    def stopThreadingCheckSpeakerEnergy(self) -> None:
        """Stops speaker energy checking via a new daemon thread and waits for it."""
        th_stopCheckSpeakerEnergy = Thread(target=self.stopCheckSpeakerEnergy)
        th_stopCheckSpeakerEnergy.daemon = True
        th_stopCheckSpeakerEnergy.start()
        th_stopCheckSpeakerEnergy.join() # Consider timeout

    @staticmethod
    def startThreadingDownloadCtranslate2Weight(weight_type: str, callback: Callable[[float], None], end_callback: Callable[[], None]) -> None:
        """Starts CTranslate2 weight download in a new daemon thread."""
        # Changed end_callback to Callable[[], None] as it seems to take no args
        th_download = Thread(target=model.downloadCTranslate2ModelWeight, args=(weight_type, callback, end_callback))
        th_download.daemon = True
        th_download.start()

    @staticmethod
    def startThreadingDownloadWhisperWeight(weight_type: str, callback: Callable[[float], None], end_callback: Callable[[], None]) -> None:
        """Starts Whisper weight download in a new daemon thread."""
        # Changed end_callback to Callable[[], None]
        th_download = Thread(target=model.downloadWhisperModelWeight, args=(weight_type, callback, end_callback))
        th_download.daemon = True
        th_download.start()

    @staticmethod
    def startWatchdog(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Starts the application watchdog."""
        model.startWatchdog()
        return {"status": 200, "result": True}

    @staticmethod
    def feedWatchdog(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Feeds the application watchdog to prevent timeout."""
        model.feedWatchdog()
        return {"status": 200, "result": True}

    @staticmethod
    def setWatchdogCallback(callback: Callable[[], None]) -> None: # Return Dict? Kept original which was None
        """Sets the callback function for the watchdog timeout."""
        model.setWatchdogCallback(callback)
        # Original did not return, if it should be consistent:
        # return {"status": 200, "result": True}

    @staticmethod
    def stopWatchdog(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Stops the application watchdog."""
        model.stopWatchdog()
        return {"status": 200, "result": True}

    @staticmethod
    def getWebSocketHost(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the WebSocket server host address from config."""
        return {"status": 200, "result": config.WEBSOCKET_HOST}

    @staticmethod
    def setWebSocketHost(data: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the WebSocket server host, restarting the server if active and address is valid and available."""
        response: Dict[str, Any]
        if not isValidIpAddress(data):
            response = {
                "status": 400,
                "result": {
                    "message": "Invalid IP address",
                    "data": config.WEBSOCKET_HOST
                }
            }
        else:
            if not model.checkWebSocketServerAlive():
                config.WEBSOCKET_HOST = data
                response = {"status": 200, "result": config.WEBSOCKET_HOST}
            else:
                if data == config.WEBSOCKET_HOST:
                    response = {"status": 200, "result": config.WEBSOCKET_HOST}
                elif isAvailableWebSocketServer(data, config.WEBSOCKET_PORT):
                    model.stopWebSocketServer()
                    model.startWebSocketServer(data, config.WEBSOCKET_PORT) # This might raise exceptions
                    config.WEBSOCKET_HOST = data
                    response = {"status": 200, "result": config.WEBSOCKET_HOST}
                else:
                    response = {
                        "status": 400,
                        "result": {
                            "message": "WebSocket server host is not available",
                            "data": config.WEBSOCKET_HOST
                        }
                    }
        return response

    @staticmethod
    def getWebSocketPort(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the WebSocket server port from config."""
        return {"status": 200, "result": config.WEBSOCKET_PORT}

    @staticmethod
    def setWebSocketPort(data: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Sets the WebSocket server port, restarting the server if active and port is available."""
        response: Dict[str, Any]
        port_val = int(data) # Ensure int
        if not model.checkWebSocketServerAlive():
            config.WEBSOCKET_PORT = port_val
            response = {"status": 200, "result": config.WEBSOCKET_PORT}
        else:
            if port_val == config.WEBSOCKET_PORT:
                response = {"status": 200, "result": config.WEBSOCKET_PORT} # No change needed
            elif isAvailableWebSocketServer(config.WEBSOCKET_HOST, port_val):
                model.stopWebSocketServer()
                model.startWebSocketServer(config.WEBSOCKET_HOST, port_val) # Might raise
                config.WEBSOCKET_PORT = port_val
                response = {"status": 200, "result": config.WEBSOCKET_PORT}
            else:
                response = {
                    "status": 400,
                    "result": {
                        "message": "WebSocket server port is not available",
                        "data": config.WEBSOCKET_PORT
                    }
                }
        return response

    @staticmethod
    def getWebSocketServer(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Gets the WebSocket server enabled status from config."""
        return {"status": 200, "result": config.WEBSOCKET_SERVER}

    @staticmethod
    def setEnableWebSocketServer(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Enables and starts the WebSocket server if the configured host/port is available."""
        response: Dict[str, Any]
        if isAvailableWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT):
            model.startWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT) # Might raise
            config.WEBSOCKET_SERVER = True
            response = {"status": 200, "result": config.WEBSOCKET_SERVER}
        else:
            response = {
                "status": 400,
                "result": {
                    "message": "WebSocket server host or port is not available",
                    "data": config.WEBSOCKET_SERVER # Current (False) state
                }
            }
        return response

    @staticmethod
    def setDisableWebSocketServer(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Disables and stops the WebSocket server."""
        config.WEBSOCKET_SERVER = False
        model.stopWebSocketServer()
        return {"status": 200, "result": config.WEBSOCKET_SERVER}

    def initializationProgress(self, progress: Union[int, float]) -> None:
        """Notifies the UI of the current initialization progress."""
        if self.run and "initialization_progress" in self.run_mapping:
            self.run(200, self.run_mapping["initialization_progress"], progress)

    def enableOscQuery(self) -> None:
        """Notifies the UI that OSCQuery is enabled."""
        if self.run and "enable_osc_query" in self.run_mapping:
            self.run(200, self.run_mapping["enable_osc_query"], True)

    def disableOscQuery(self) -> None:
        """Notifies the UI that OSCQuery is disabled."""
        if self.run and "enable_osc_query" in self.run_mapping:
            self.run(200, self.run_mapping["enable_osc_query"], False)

    def init(self, *args: Any, **kwargs: Any) -> None:
        """
        Initializes the application.

        This method performs the following steps:
        1. Clears old logs.
        2. Checks network connectivity and notifies the UI.
        3. Downloads CTranslate2 and Whisper model weights if necessary (conditionally, if network is up).
           - Disables AI models in UI if essential weights are missing.
        4. Initializes translation and transcription engine statuses in config.
        5. Updates and sets the selected translation and transcription engines based on availability.
        6. Initializes the word filter.
        7. Checks for software updates and notifies the UI.
        8. Starts the logger if the feature is enabled.
        9. Initializes OSC receiver and checks OSCQuery status.
        10. Sets up VRChat microphone mute sync if enabled.
        11. Initializes the device manager and sets up callbacks for device list updates.
        12. Enables automatic device selection if configured.
        13. Starts the overlay system if enabled.
        14. Starts the WebSocket server if enabled and host/port are available.
        15. Sends all initial configuration settings to the UI.
        16. Starts the application watchdog.
        """
        removeLog()
        printLog("Start Initialization")
        connected_network = isConnectedNetwork()
        if connected_network is True:
            self.connectedNetwork()
        else:
            self.disconnectedNetwork()
        printLog(f"Connected Network: {connected_network}")

        self.initializationProgress(1)

        if connected_network is True:
            # download CTranslate2 Model Weight
            printLog("Download CTranslate2 Model Weight")
            weight_type = config.CTRANSLATE2_WEIGHT_TYPE
            th_download_ctranslate2 = None
            if model.checkTranslatorCTranslate2ModelWeight(weight_type) is False:
                th_download_ctranslate2 = Thread(target=self.downloadCtranslate2Weight, args=(weight_type, False))
                th_download_ctranslate2.daemon = True
                th_download_ctranslate2.start()

            # download Whisper Model Weight
            printLog("Download Whisper Model Weight")
            weight_type = config.WHISPER_WEIGHT_TYPE
            th_download_whisper = None
            if model.checkTranscriptionWhisperModelWeight(weight_type) is False:
                th_download_whisper = Thread(target=self.downloadWhisperWeight, args=(weight_type, False))
                th_download_whisper.daemon = True
                th_download_whisper.start()

            if isinstance(th_download_ctranslate2, Thread):
                th_download_ctranslate2.join()
            if isinstance(th_download_whisper, Thread):
                th_download_whisper.join()

        if (model.checkTranslatorCTranslate2ModelWeight(config.CTRANSLATE2_WEIGHT_TYPE) is False or
            model.checkTranscriptionWhisperModelWeight(config.WHISPER_WEIGHT_TYPE) is False):
            self.disableAiModels()
        else:
            self.enableAiModels()

        printLog("Init Translation Engine Status")
        for engine in config.SELECTABLE_TRANSLATION_ENGINE_LIST:
            config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False
        self.initializationProgress(2)

        # set Translation Engine
        printLog("Set Translation Engine")
        self.updateDownloadedCTranslate2ModelWeight()
        self.updateTranslationEngineAndEngineList()

        # set Transcription Engine
        printLog("Set Transcription Engine")
        self.updateDownloadedWhisperModelWeight()
        self.updateTranscriptionEngine()

        self.initializationProgress(3)

        # set word filter
        printLog("Set Word Filter")
        model.addKeywords()

        # check Software Updated
        printLog("Check Software Updated")
        self.checkSoftwareUpdated()

        # init logger
        printLog("Init Logger")
        if config.LOGGER_FEATURE is True:
            model.startLogger()

        self.initializationProgress(4)

        # init OSC receive
        printLog("Init OSC Receive")
        model.startReceiveOSC()
        osc_query_enabled = model.getIsOscQueryEnabled()
        if osc_query_enabled is True:
            self.enableOscQuery()
        else:
            self.disableOscQuery()

        if config.VRC_MIC_MUTE_SYNC is True:
            self.setEnableVrcMicMuteSync()

        # init Auto device selection
        printLog("Init Device Manager")
        device_manager.setCallbackHostList(self.updateMicHostList)
        device_manager.setCallbackMicDeviceList(self.updateMicDeviceList)
        device_manager.setCallbackSpeakerDeviceList(self.updateSpeakerDeviceList)

        printLog("Init Auto Device Selection")
        if config.AUTO_MIC_SELECT is True:
            self.setEnableAutoMicSelect()
        if config.AUTO_SPEAKER_SELECT is True:
            self.setEnableAutoSpeakerSelect()

        printLog("Init Overlay")
        if (config.OVERLAY_SMALL_LOG is True or config.OVERLAY_LARGE_LOG is True):
            model.startOverlay()

        printLog("Init WebSocket Server")
        if config.WEBSOCKET_SERVER is True:
            if isAvailableWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT) is True:
                model.startWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT)
            else:
                config.WEBSOCKET_SERVER = False
                model.stopWebSocketServer()
                printLog("WebSocket server host or port is not available")

        printLog("Update settings")
        self.updateConfigSettings()

        printLog("End Initialization")
        self.startWatchdog()