import copy
from typing import Callable, Any
from time import sleep
from subprocess import Popen
from threading import Thread
import re
from device_manager import device_manager
from config import config
from model import model
from utils import removeLog, printLog, errorLogging, isConnectedNetwork, isValidIpAddress, isAvailableWebSocketServer

class Controller:
    def __init__(self) -> None:
        self.init_mapping = {}
        self.run_mapping = {}
        self.run = None
        self.device_access_status = True

    def setInitMapping(self, init_mapping:dict) -> None:
        self.init_mapping = init_mapping

    def setRunMapping(self, run_mapping:dict) -> None:
        self.run_mapping = run_mapping

    def setRun(self, run:Callable[[int, str, Any], None]) -> None:
        self.run = run

    # response functions
    def connectedNetwork(self) -> None:
        self.run(
            200,
            self.run_mapping["connected_network"],
            True,
        )

    def disconnectedNetwork(self) -> None:
        self.run(
            200,
            self.run_mapping["connected_network"],
            False,
        )

    def enableAiModels(self) -> None:
        self.run(
            200,
            self.run_mapping["enable_ai_models"],
            True,
        )

    def disableAiModels(self) -> None:
        self.run(
            200,
            self.run_mapping["enable_ai_models"],
            False,
        )

    def updateMicHostList(self) -> None:
        self.run(
            200,
            self.run_mapping["mic_host_list"],
            model.getListMicHost(),
        )

    def updateMicDeviceList(self) -> None:
        self.run(
            200,
            self.run_mapping["mic_device_list"],
            model.getListMicDevice(),
        )

    def updateSpeakerDeviceList(self) -> None:
        self.run(
            200,
            self.run_mapping["speaker_device_list"],
            model.getListSpeakerDevice(),
        )

    def updateConfigSettings(self) -> None:
        settings = {}
        for endpoint, dict_data in self.init_mapping.items():
            response = dict_data["variable"](None)
            result = response.get("result", None)
            settings[endpoint] = result
        self.run(
            200,
            self.run_mapping["initialization_complete"],
            settings,
        )

    def restartAccessMicDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.startThreadingTranscriptionSendMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            model.startCheckMicEnergy(
                self.progressBarMicEnergy,
            )

    def restartAccessSpeakerDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.startThreadingTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            model.startCheckSpeakerEnergy(
                self.progressBarSpeakerEnergy,
            )

    def stopAccessMicDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.stopThreadingTranscriptionSendMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            model.stopCheckMicEnergy()

    def stopAccessSpeakerDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.stopThreadingTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            model.stopCheckSpeakerEnergy()

    def updateSelectedMicDevice(self, host, device) -> None:
        config.SELECTED_MIC_HOST = host
        config.SELECTED_MIC_DEVICE = device
        self.run(
            200,
            self.run_mapping["selected_mic_device"],
            {"host":host, "device":device},
        )

    def updateSelectedSpeakerDevice(self, device) -> None:
        config.SELECTED_SPEAKER_DEVICE = device
        self.run(
            200,
            self.run_mapping["selected_speaker_device"],
            device,
        )

    def progressBarMicEnergy(self, energy) -> None:
        if energy is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {
                    "message":"No mic device detected",
                    "data": None
                },
            )
        else:
            self.run(
                200,
                self.run_mapping["check_mic_volume"],
                energy,
            )

    def progressBarSpeakerEnergy(self, energy) -> None:
        if energy is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {
                    "message":"No speaker device detected",
                    "data": None
                },
            )
        else:
            self.run(
                200,
                self.run_mapping["check_speaker_volume"],
                energy,
            )

    class DownloadCTranslate2:
        def __init__(self, run_mapping:dict,  weight_type:str, run:Callable[[int, str, Any], None]) -> None:
            self.run_mapping = run_mapping
            self.weight_type = weight_type
            self.run = run

        def progressBar(self, progress) -> None:
            printLog("CTranslate2 Weight Download Progress", progress)
            self.run(
                200,
                self.run_mapping["download_progress_ctranslate2_weight"],
                {"weight_type": self.weight_type, "progress": progress},
            )

        def downloaded(self) -> None:
            if model.checkTranslatorCTranslate2ModelWeight(self.weight_type) is True:
                weight_type_dict = config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT
                weight_type_dict[self.weight_type] = True
                config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT = weight_type_dict

                self.run(
                    200,
                    self.run_mapping["downloaded_ctranslate2_weight"],
                    self.weight_type,
                )
            else:
                self.run(
                    400,
                    self.run_mapping["error_ctranslate2_weight"],
                    {
                        "message":"CTranslate2 weight download error",
                        "data": None
                    },
                )

    class DownloadWhisper:
        def __init__(self, run_mapping:dict, weight_type:str, run:Callable[[int, str, Any], None]) -> None:
            self.run_mapping = run_mapping
            self.weight_type = weight_type
            self.run = run

        def progressBar(self, progress) -> None:
            printLog("Whisper Weight Download Progress", progress)
            self.run(
                200,
                self.run_mapping["download_progress_whisper_weight"],
                {"weight_type": self.weight_type, "progress": progress},
            )

        def downloaded(self) -> None:
            if model.checkTranscriptionWhisperModelWeight(self.weight_type) is True:
                weight_type_dict = config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT
                weight_type_dict[self.weight_type] = True
                config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = weight_type_dict

                self.run(
                    200,
                    self.run_mapping["downloaded_whisper_weight"],
                    self.weight_type,
                )
            else:
                self.run(
                    400,
                    self.run_mapping["error_whisper_weight"],
                    {
                        "message":"Whisper weight download error",
                        "data": None
                    },
                )

    def micMessage(self, result: dict) -> None:
        message = result["text"]
        language = result["language"]
        if isinstance(message, bool) and message is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {
                    "message":"No mic device detected",
                    "data": None
                },
            )

        elif isinstance(message, str) and len(message) > 0:
            translation = []
            transliteration_message = []
            transliteration_translation = []
            if model.checkKeywords(message):
                self.run(
                    200,
                    self.run_mapping["word_filter"],
                    {"message":f"Detected by word filter: {message}"},
                )
                return
            elif model.detectRepeatSendMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                try:
                    translation, success = model.getInputTranslate(message, source_language=language)
                    if all(success) is not True:
                        self.changeToCTranslate2Process()
                        self.run(
                            400,
                            self.run_mapping["error_translation_engine"],
                            {
                                "message":"Translation engine limit error",
                                "data": None
                            },
                        )
                except Exception as e:
                    # VRAM不足エラーの検出
                    is_vram_error, error_message = model.detectVRAMError(e)
                    if is_vram_error:
                        self.run(
                            400,
                            self.run_mapping["error_translation_mic_vram_overflow"],
                            {
                                "message":"VRAM out of memory during translation of mic",
                                "data": error_message
                            },
                        )
                        # 翻訳機能をOFFにする
                        self.setDisableTranslation()
                        self.run(
                            400,
                            self.run_mapping["enable_translation"],
                            {
                                "message":"Translation disabled due to VRAM overflow",
                                "data": False
                            },
                        )
                        return
                    else:
                        # その他のエラーは通常通り処理
                        raise

            if config.CONVERT_MESSAGE_TO_HIRAGANA is True or config.CONVERT_MESSAGE_TO_ROMAJI is True:
                if config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese":
                    transliteration_message = model.convertMessageToTransliteration(
                        message,
                        hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                        romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                    )

                for i, no in enumerate(config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST):
                    if (config.ENABLE_TRANSLATION is True and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["language"] == "Japanese" and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["enable"] is True
                        ):
                        transliteration_translation.append(
                            model.convertMessageToTransliteration(
                                translation[i],
                                hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                                romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                            )
                        )
                    else:
                        transliteration_translation.append([])
            else:
                transliteration_translation = [[] for _ in config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST]

            if config.ENABLE_TRANSCRIPTION_SEND is True:
                if config.SEND_MESSAGE_TO_VRC is True:
                    if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                        if config.ENABLE_TRANSLATION is False:
                            osc_message = self.messageFormatter("SEND", [], message)
                        else:
                            osc_message = self.messageFormatter("SEND", translation, "")
                    else:
                        osc_message = self.messageFormatter("SEND", translation, message)
                    model.oscSendMessage(osc_message)

                self.run(
                    200,
                    self.run_mapping["transcription_mic"],
                    {
                        "original": {
                            "message": message,
                            "transliteration": transliteration_message
                        },
                        "translations": [
                            {
                                "message": translation_message,
                                "transliteration": transliteration
                            } for translation_message, transliteration in zip(translation, transliteration_translation)
                        ]
                    })

                if config.OVERLAY_LARGE_LOG is True and model.overlay.initialized is True:
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                        if len(translation) > 0:
                            overlay_image = model.createOverlayImageLargeLog(
                                "send",
                                None,
                                None,
                                translation,
                                config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
                            )
                            model.updateOverlayLargeLog(overlay_image)
                    else:
                        overlay_image = model.createOverlayImageLargeLog(
                            "send",
                            message,
                            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"],
                            translation,
                            config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
                        )
                        model.updateOverlayLargeLog(overlay_image)

                if model.checkWebSocketServerAlive() is True:
                    model.websocketSendMessage(
                        {
                            "type":"SENT",
                            "src_languages":config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            "dst_languages":config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                            "message":message,
                            "translation":translation,
                            "transliteration":transliteration_translation
                        }
                    )

                if config.LOGGER_FEATURE is True:
                    translation_text = f" ({'/'.join(translation)})" if translation else ""
                    model.logger.info(f"[SENT] {message}{translation_text}")

    def speakerMessage(self, result:dict) -> None:
        message = result["text"]
        language = result["language"]
        if isinstance(message, bool) and message is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {
                    "message":"No speaker device detected",
                    "data": None
                },
            )
        elif isinstance(message, str) and len(message) > 0:
            translation = []
            transliteration_message = []
            transliteration_translation = []
            if model.checkKeywords(message):
                self.run(
                    200,
                    self.run_mapping["word_filter"],
                    {"message":f"Detected by word filter: {message}"},
                )
                return
            elif model.detectRepeatReceiveMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                try:
                    translation, success = model.getOutputTranslate(message, source_language=language)
                    if all(success) is not True:
                        self.changeToCTranslate2Process()
                        self.run(
                            400,
                            self.run_mapping["error_translation_engine"],
                            {
                                "message":"Translation engine limit error",
                                "data": None
                            },
                        )
                except Exception as e:
                    # VRAM不足エラーの検出
                    is_vram_error, error_message = model.detectVRAMError(e)
                    if is_vram_error:
                        self.run(
                            400,
                            self.run_mapping["error_translation_speaker_vram_overflow"],
                            {
                                "message":"VRAM out of memory during translation of speaker",
                                "data": error_message
                            },
                        )
                        # 翻訳機能をOFFにする
                        self.setDisableTranslation()
                        self.run(
                            400,
                            self.run_mapping["enable_translation"],
                            {
                                "message":"Translation disabled due to VRAM overflow",
                                "data": False
                            },
                        )
                        return
                    else:
                        # その他のエラーは通常通り処理
                        raise

            if config.CONVERT_MESSAGE_TO_HIRAGANA is True or config.CONVERT_MESSAGE_TO_ROMAJI is True:
                if language == "Japanese":
                    transliteration_message = model.convertMessageToTransliteration(
                        message,
                        hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                        romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                    )

                if (config.ENABLE_TRANSLATION is True and
                    config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese"
                    ):
                    transliteration_translation.append(
                        model.convertMessageToTransliteration(
                            translation[0],
                            hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                            romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                        )
                    )
                else:
                    transliteration_translation.append([])
            else:
                transliteration_translation = [[]]

            if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
                if config.OVERLAY_SMALL_LOG is True and model.overlay.initialized is True:
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                        if len(translation) > 0:
                            overlay_image = model.createOverlayImageSmallLog(
                                None,
                                None,
                                translation,
                                config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            )
                            model.updateOverlaySmallLog(overlay_image)
                    else:
                        overlay_image = model.createOverlayImageSmallLog(
                            message,
                            language,
                            translation,
                            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                        )
                        model.updateOverlaySmallLog(overlay_image)

                if config.OVERLAY_LARGE_LOG is True and model.overlay.initialized is True:
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                        if len(translation) > 0:
                            overlay_image = model.createOverlayImageLargeLog(
                                "receive",
                                None,
                                None,
                                translation,
                            )
                            model.updateOverlayLargeLog(overlay_image)
                    else:
                        overlay_image = model.createOverlayImageLargeLog(
                            "receive",
                            message,
                            language,
                            translation,
                            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
                        )
                        model.updateOverlayLargeLog(overlay_image)

                if config.SEND_RECEIVED_MESSAGE_TO_VRC is True:
                    if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                        if config.ENABLE_TRANSLATION is False:
                            osc_message = self.messageFormatter("RECEIVED", [], message)
                        else:
                            osc_message = self.messageFormatter("RECEIVED", translation, "")
                    else:
                        osc_message = self.messageFormatter("RECEIVED", translation, message)
                    model.oscSendMessage(osc_message)

                # update textbox message log (Received)
                self.run(
                    200,
                    self.run_mapping["transcription_speaker"],
                    {
                        "original": {
                            "message": message,
                            "transliteration": transliteration_message
                        },
                        "translations": [
                            {
                                "message": translation_message,
                                "transliteration": transliteration
                            } for translation_message, transliteration in zip(translation, transliteration_translation)
                        ]
                    })

                if model.checkWebSocketServerAlive() is True:
                    model.websocketSendMessage(
                        {
                            "type":"RECEIVED",
                            "src_languages":config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                            "dst_languages":config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            "message":message,
                            "translation":translation,
                            "transliteration":transliteration_translation
                        }
                    )

                if config.LOGGER_FEATURE is True:
                    translation_text = f" ({'/'.join(translation)})" if translation else ""
                    model.logger.info(f"[RECEIVED] {message}{translation_text}")

    def chatMessage(self, data) -> None:
        id = data["id"]
        message = data["message"]
        if len(message) > 0:
            translation = []
            transliteration_message = []
            transliteration_translation = []
            if config.ENABLE_TRANSLATION is False:
                pass
            else:
                try:
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
                        self.run(
                            400,
                            self.run_mapping["error_translation_engine"],
                            {
                                "message":"Translation engine limit error",
                                "data": None
                            },
                        )
                except Exception as e:
                    # VRAM不足エラーの検出
                    is_vram_error, error_message = model.detectVRAMError(e)
                    if is_vram_error:
                        self.run(
                            400,
                            self.run_mapping["error_translation_chat_vram_overflow"],
                            {
                                "message":"VRAM out of memory during translation of chat",
                                "data": error_message
                            },
                        )
                        # 翻訳機能をOFFにする
                        self.setDisableTranslation()
                        self.run(
                            400,
                            self.run_mapping["enable_translation"],
                            {
                                "message":"Translation disabled due to VRAM overflow",
                                "data": False
                            },
                        )
                        # エラー時は翻訳なしで返す
                        return {"status":200,
                                "result":
                                {
                                    "id":id,
                                    "original": {
                                        "message":message,
                                        "transliteration":[]
                                    },
                                    "translations": [
                                        {
                                            "message": "",
                                            "transliteration": []
                                        } for _ in config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST
                                    ]
                                },
                            }
                    else:
                        # その他のエラーは通常通り処理
                        raise

            if config.CONVERT_MESSAGE_TO_HIRAGANA is True or config.CONVERT_MESSAGE_TO_ROMAJI is True:
                if config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese":
                    transliteration_message = model.convertMessageToTransliteration(
                        message,
                        hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                        romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                    )
                for i, no in enumerate(config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST):
                    if (config.ENABLE_TRANSLATION is True and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["language"] == "Japanese" and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["enable"] is True
                        ):
                        transliteration_translation.append(
                            model.convertMessageToTransliteration(
                                translation[i],
                                hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                                romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                            )
                        )
                    else:
                        transliteration_translation.append([])
            else:
                transliteration_translation = [[] for _ in config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST]

            # send OSC message
            if config.SEND_MESSAGE_TO_VRC is True:
                if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                    if config.ENABLE_TRANSLATION is False:
                        osc_message = self.messageFormatter("SEND", [], message)
                    else:
                        osc_message = self.messageFormatter("SEND", translation, "")
                else:
                    osc_message = self.messageFormatter("SEND", translation, message)
                model.oscSendMessage(osc_message)

            if config.OVERLAY_LARGE_LOG is True:
                if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                    if len(translation) > 0:
                        overlay_image = model.createOverlayImageLargeLog(
                            "send",
                            None,
                            None,
                            translation,
                            config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                        )
                        model.updateOverlayLargeLog(overlay_image)
                else:
                    overlay_image = model.createOverlayImageLargeLog(
                        "send",
                        message,
                        config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"],
                        translation,
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                    )
                    model.updateOverlayLargeLog(overlay_image)

            if model.checkWebSocketServerAlive() is True:
                model.websocketSendMessage(
                    {
                        "type":"CHAT",
                        "src_languages":config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                        "dst_languages":config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                        "message":message,
                        "translation":translation,
                        "transliteration":transliteration_translation
                    }
                )

            if config.LOGGER_FEATURE is True:
                translation_text = f" ({'/'.join(translation)})" if translation else ""
                model.logger.info(f"[CHAT] {message}{translation_text}")

        return {
                "status":200,
                "result":{
                    "id":id,
                    "original": {
                        "message":message,
                        "transliteration":transliteration_message
                    },
                    "translations": [
                        {
                            "message": translation_message,
                            "transliteration": transliteration
                        } for translation_message, transliteration in zip(translation, transliteration_translation)
                    ]
                }}

    @staticmethod
    def getVersion(*args, **kwargs) -> dict:
        return {"status":200, "result":config.VERSION}

    def checkSoftwareUpdated(self) -> dict:
        software_update_info = model.checkSoftwareUpdated()
        self.run(
            200,
            self.run_mapping["software_update_info"],
            software_update_info,
        )

    @staticmethod
    def getComputeMode(*args, **kwargs) -> dict:
        return {"status":200, "result":config.COMPUTE_MODE}

    @staticmethod
    def getComputeDeviceList(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTABLE_COMPUTE_DEVICE_LIST}

    @staticmethod
    def getSelectedTranslationComputeDevice(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSLATION_COMPUTE_DEVICE}

    def setSelectedTranslationComputeDevice(self, device:str, *args, **kwargs) -> dict:
        printLog("setSelectedTranslationComputeDevice", device)
        config.SELECTED_TRANSLATION_COMPUTE_DEVICE = device
        config.SELECTED_TRANSLATION_COMPUTE_TYPE = "auto"
        self.run(200, self.run_mapping["selected_translation_compute_type"], config.SELECTED_TRANSLATION_COMPUTE_TYPE)
        model.setChangedTranslatorParameters(True)
        return {"status":200,"result":config.SELECTED_TRANSLATION_COMPUTE_DEVICE}

    @staticmethod
    def getSelectableCtranslate2WeightTypeDict(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT}

    @staticmethod
    def getSelectedTranscriptionComputeDevice(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE}

    def setSelectedTranscriptionComputeDevice(self, device:str, *args, **kwargs) -> dict:
        printLog("setSelectedTranscriptionComputeDevice", device)
        config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = device
        config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE = "auto"
        self.run(200, self.run_mapping["selected_transcription_compute_type"], config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE)
        return {"status":200,"result":config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE}

    @staticmethod
    def getSelectableWhisperWeightTypeDict(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT}

    # @staticmethod
    # def getMaxMicThreshold(*args, **kwargs) -> dict:
    #     return {"status":200, "result":config.MAX_MIC_THRESHOLD}

    # @staticmethod
    # def getMaxSpeakerThreshold(*args, **kwargs) -> dict:
    #     return {"status":200, "result":config.MAX_SPEAKER_THRESHOLD}

    def setEnableTranslation(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSLATION is False:
            if model.isLoadedCTranslate2Model() is False or model.isChangedTranslatorParameters() is True:
                try:
                    model.changeTranslatorCTranslate2Model()
                    model.setChangedTranslatorParameters(False)
                    config.ENABLE_TRANSLATION = True
                except Exception as e:
                    # VRAM不足エラーの検出（デバイス切り替え時）
                    is_vram_error, error_message = model.detectVRAMError(e)
                    if is_vram_error:
                        # Defaultのデバイス設定に戻す
                        printLog("VRAM error detected, reverting device setting")
                        self.setDisableTranslation()
                        config.SELECTED_TRANSLATION_COMPUTE_DEVICE = copy.deepcopy(config.SELECTABLE_COMPUTE_DEVICE_LIST[0])
                        config.SELECTED_TRANSLATION_COMPUTE_TYPE = "auto"
                        self.run(200, self.run_mapping["selected_translation_compute_device"], config.SELECTED_TRANSLATION_COMPUTE_DEVICE)
                        self.run(200, self.run_mapping["selected_translation_compute_type"], config.SELECTED_TRANSLATION_COMPUTE_TYPE)
                        self.run(
                            400,
                            self.run_mapping["enable_translation"],
                            {
                                "message":"Translation disabled due to VRAM overflow",
                                "data": False
                            },
                        )
                        model.changeTranslatorCTranslate2Model()
                        model.setChangedTranslatorParameters(False)
                    else:
                        # その他のエラーは通常通り処理
                        errorLogging()
            else:
                config.ENABLE_TRANSLATION = True
        return {"status":200, "result":config.ENABLE_TRANSLATION}

    @staticmethod
    def setDisableTranslation(*args, **kwargs) -> dict:
        if config.ENABLE_TRANSLATION is True:
            config.ENABLE_TRANSLATION = False
        return {"status":200, "result":config.ENABLE_TRANSLATION}

    @staticmethod
    def setEnableForeground(*args, **kwargs) -> dict:
        if config.ENABLE_FOREGROUND is False:
            config.ENABLE_FOREGROUND = True
        return {"status":200, "result":config.ENABLE_FOREGROUND}

    @staticmethod
    def setDisableForeground(*args, **kwargs) -> dict:
        if config.ENABLE_FOREGROUND is True:
            config.ENABLE_FOREGROUND = False
        return {"status":200, "result":config.ENABLE_FOREGROUND}

    @staticmethod
    def getSelectedTabNo(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TAB_NO}

    def setSelectedTabNo(self, selected_tab_no:str, *args, **kwargs) -> dict:
        printLog("setSelectedTabNo", selected_tab_no)
        config.SELECTED_TAB_NO = selected_tab_no
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.SELECTED_TAB_NO}

    @staticmethod
    def getTranslationEngines(*args, **kwargs) -> dict:
        engines = model.findTranslationEngines(
            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
            config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS,
            )

        your_language = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]
        for target_language in config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO].values():
            if your_language["language"] == target_language["language"] and target_language["enable"] is True:
                if config.SELECTABLE_TRANSLATION_ENGINE_STATUS["CTranslate2"] is True:
                    engines = ["CTranslate2"]
                else:
                    engines = []

        return {"status":200, "result":engines}

    @staticmethod
    def getListLanguageAndCountry(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListLanguageAndCountry()}

    @staticmethod
    def getMicHostList(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListMicHost()}

    @staticmethod
    def getMicDeviceList(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListMicDevice()}

    @staticmethod
    def getSpeakerDeviceList(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListSpeakerDevice()}

    @staticmethod
    def getSelectedTranslationEngines(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSLATION_ENGINES}

    @staticmethod
    def setSelectedTranslationEngines(data:dict, *args, **kwargs) -> dict:
        config.SELECTED_TRANSLATION_ENGINES = data
        return {"status":200,"result":config.SELECTED_TRANSLATION_ENGINES}

    @staticmethod
    def getSelectedYourLanguages(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_YOUR_LANGUAGES}

    def setSelectedYourLanguages(self, select:dict, *args, **kwargs) -> dict:
        config.SELECTED_YOUR_LANGUAGES = select
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.SELECTED_YOUR_LANGUAGES}

    @staticmethod
    def getSelectedTargetLanguages(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TARGET_LANGUAGES}

    def setSelectedTargetLanguages(self, select:dict, *args, **kwargs) -> dict:
        config.SELECTED_TARGET_LANGUAGES = select
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.SELECTED_TARGET_LANGUAGES}

    @staticmethod
    def getTranscriptionEngines(*args, **kwargs) -> dict:
        engines = [key for key, value in config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS.items() if value is True]
        return {"status":200, "result":engines}

    @staticmethod
    def getSelectedTranscriptionEngine(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_ENGINE}

    @staticmethod
    def setSelectedTranscriptionEngine(data, *args, **kwargs) -> dict:
        config.SELECTED_TRANSCRIPTION_ENGINE = str(data)
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_ENGINE}

    @staticmethod
    def getConvertMessageToRomaji(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def setEnableConvertMessageToRomaji(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_ROMAJI is False:
            if config.CONVERT_MESSAGE_TO_HIRAGANA is False:
                model.startTransliteration()
            config.CONVERT_MESSAGE_TO_ROMAJI = True
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def setDisableConvertMessageToRomaji(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_ROMAJI is True:
            if config.CONVERT_MESSAGE_TO_HIRAGANA is False:
                model.stopTransliteration()
            config.CONVERT_MESSAGE_TO_ROMAJI = False
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def getConvertMessageToHiragana(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def setEnableConvertMessageToHiragana(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_HIRAGANA is False:
            if config.CONVERT_MESSAGE_TO_ROMAJI is False:
                model.startTransliteration()
            config.CONVERT_MESSAGE_TO_HIRAGANA = True
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def setDisableConvertMessageToHiragana(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_HIRAGANA is True:
            if config.CONVERT_MESSAGE_TO_ROMAJI is False:
                model.stopTransliteration()
            config.CONVERT_MESSAGE_TO_HIRAGANA = False
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def getMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def setEnableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        if config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE is False:
            config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def setDisableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        if config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE is True:
            config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def getTransparency(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSPARENCY}

    @staticmethod
    def setTransparency(data, *args, **kwargs) -> dict:
        config.TRANSPARENCY = int(data)
        return {"status":200, "result":config.TRANSPARENCY}

    @staticmethod
    def getUiScaling(*args, **kwargs) -> dict:
        return {"status":200, "result":config.UI_SCALING}

    @staticmethod
    def setUiScaling(data, *args, **kwargs) -> dict:
        config.UI_SCALING = int(data)
        return {"status":200, "result":config.UI_SCALING}

    @staticmethod
    def getTextboxUiScaling(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TEXTBOX_UI_SCALING}

    @staticmethod
    def setTextboxUiScaling(data, *args, **kwargs) -> dict:
        config.TEXTBOX_UI_SCALING = int(data)
        return {"status":200, "result":config.TEXTBOX_UI_SCALING}

    @staticmethod
    def getMessageBoxRatio(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MESSAGE_BOX_RATIO}

    @staticmethod
    def setMessageBoxRatio(data, *args, **kwargs) -> dict:
        config.MESSAGE_BOX_RATIO = data
        return {"status":200, "result":config.MESSAGE_BOX_RATIO}

    @staticmethod
    def getSendMessageButtonType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}

    @staticmethod
    def setSendMessageButtonType(data, *args, **kwargs) -> dict:
        config.SEND_MESSAGE_BUTTON_TYPE = data
        return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}

    @staticmethod
    def getShowResendButton(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SHOW_RESEND_BUTTON}

    @staticmethod
    def setEnableShowResendButton(*args, **kwargs) -> dict:
        if config.SHOW_RESEND_BUTTON is False:
            config.SHOW_RESEND_BUTTON = True
        return {"status":200, "result":config.SHOW_RESEND_BUTTON}

    @staticmethod
    def setDisableShowResendButton(*args, **kwargs) -> dict:
        if config.SHOW_RESEND_BUTTON is True:
            config.SHOW_RESEND_BUTTON = False
        return {"status":200, "result":config.SHOW_RESEND_BUTTON}

    @staticmethod
    def getFontFamily(*args, **kwargs) -> dict:
        return {"status":200, "result":config.FONT_FAMILY}

    @staticmethod
    def setFontFamily(data, *args, **kwargs) -> dict:
        config.FONT_FAMILY = data
        return {"status":200, "result":config.FONT_FAMILY}

    @staticmethod
    def getUiLanguage(*args, **kwargs) -> dict:
        return {"status":200, "result":config.UI_LANGUAGE}

    @staticmethod
    def setUiLanguage(data, *args, **kwargs) -> dict:
        config.UI_LANGUAGE = data
        return {"status":200, "result":config.UI_LANGUAGE}

    @staticmethod
    def getMainWindowGeometry(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MAIN_WINDOW_GEOMETRY}

    @staticmethod
    def setMainWindowGeometry(data, *args, **kwargs) -> dict:
        config.MAIN_WINDOW_GEOMETRY = data
        return {"status":200, "result":config.MAIN_WINDOW_GEOMETRY}

    @staticmethod
    def getAutoMicSelect(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTO_MIC_SELECT}

    def applyAutoMicSelect(self) -> None:
        device_manager.setCallbackProcessBeforeUpdateMicDevices(self.stopAccessMicDevices)
        device_manager.setCallbackDefaultMicDevice(self.updateSelectedMicDevice)
        device_manager.setCallbackProcessAfterUpdateMicDevices(self.restartAccessMicDevices)
        device_manager.forceUpdateAndSetMicDevices()

    def setEnableAutoMicSelect(self, *args, **kwargs) -> dict:
        if config.AUTO_MIC_SELECT is False:
            self.applyAutoMicSelect()
            config.AUTO_MIC_SELECT = True
        return {"status":200, "result":config.AUTO_MIC_SELECT}

    @staticmethod
    def setDisableAutoMicSelect(*args, **kwargs) -> dict:
        if config.AUTO_MIC_SELECT is True:
            device_manager.clearCallbackProcessBeforeUpdateMicDevices()
            device_manager.clearCallbackDefaultMicDevice()
            device_manager.clearCallbackProcessAfterUpdateMicDevices()
            config.AUTO_MIC_SELECT = False
        return {"status":200, "result":config.AUTO_MIC_SELECT}

    @staticmethod
    def getSelectedMicHost(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_MIC_HOST}

    def setSelectedMicHost(self, data, *args, **kwargs) -> dict:
        config.SELECTED_MIC_HOST = data
        config.SELECTED_MIC_DEVICE = model.getMicDefaultDevice()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            self.stopThreadingCheckMicEnergy()
            self.startThreadingTranscriptionSendMessage()
        return {"status":200,
                "result":{
                    "host":config.SELECTED_MIC_HOST,
                    "device":config.SELECTED_MIC_DEVICE,
                    },
                }

    @staticmethod
    def getSelectedMicDevice(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_MIC_DEVICE}

    def setSelectedMicDevice(self, data, *args, **kwargs) -> dict:
        config.SELECTED_MIC_DEVICE = data
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            self.stopThreadingCheckMicEnergy()
            self.startThreadingTranscriptionSendMessage()
        return {"status":200, "result": config.SELECTED_MIC_DEVICE}

    @staticmethod
    def getMicThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_THRESHOLD}

    @staticmethod
    def setMicThreshold(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data <= config.MAX_MIC_THRESHOLD:
                config.MIC_THRESHOLD = data
                status = 200
            else:
                raise ValueError()
        except Exception:
            response = {
                "status":400,
                "result":{
                    "message":"Mic energy threshold value is out of range",
                    "data": config.MIC_THRESHOLD
                }
            }
        else:
            response = {"status":status, "result":config.MIC_THRESHOLD}
        return response

    @staticmethod
    def getMicAutomaticThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setEnableMicAutomaticThreshold(*args, **kwargs) -> dict:
        if config.MIC_AUTOMATIC_THRESHOLD is False:
            config.MIC_AUTOMATIC_THRESHOLD = True
        return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableMicAutomaticThreshold(*args, **kwargs) -> dict:
        if config.MIC_AUTOMATIC_THRESHOLD is True:
            config.MIC_AUTOMATIC_THRESHOLD = False
        return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def getMicRecordTimeout(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_RECORD_TIMEOUT}

    @staticmethod
    def setMicRecordTimeout(data, *args, **kwargs) -> dict:
        printLog("Set Mic Record Timeout", data)
        try:
            data = int(data)
            if 0 <= data <= config.MIC_PHRASE_TIMEOUT:
                config.MIC_RECORD_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = {
                "status":400,
                "result":{
                    "message":"Mic record timeout value is out of range",
                    "data": config.MIC_RECORD_TIMEOUT
                }
            }
        else:
            response = {"status":200, "result":config.MIC_RECORD_TIMEOUT}
        return response

    @staticmethod
    def getMicPhraseTimeout(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_PHRASE_TIMEOUT}

    @staticmethod
    def setMicPhraseTimeout(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if data >= config.MIC_RECORD_TIMEOUT:
                config.MIC_PHRASE_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = {
                "status":400,
                "result":{
                    "message":"Mic phrase timeout value is out of range",
                    "data": config.MIC_PHRASE_TIMEOUT
                }
            }
        else:
            response = {"status":200, "result":config.MIC_PHRASE_TIMEOUT}
        return response

    @staticmethod
    def getMicMaxPhrases(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_MAX_PHRASES}

    @staticmethod
    def setMicMaxPhrases(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data:
                config.MIC_MAX_PHRASES = data
            else:
                raise ValueError()
        except Exception:
            response = {
                "status":400,
                "result":{
                    "message":"Mic max phrases value is out of range",
                    "data": config.MIC_MAX_PHRASES
                }
            }
        else:
            response = {"status":200, "result":config.MIC_MAX_PHRASES}
        return response

    @staticmethod
    def getMicWordFilter(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_WORD_FILTER}

    @staticmethod
    def setMicWordFilter(data, *args, **kwargs) -> dict:
        config.MIC_WORD_FILTER = sorted(set(data), key=data.index)
        model.resetKeywordProcessor()
        model.addKeywords()
        return {"status":200, "result":config.MIC_WORD_FILTER}

    @staticmethod
    def getMicAvgLogprob(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_AVG_LOGPROB}

    @staticmethod
    def setMicAvgLogprob(data, *args, **kwargs) -> dict:
        config.MIC_AVG_LOGPROB = float(data)
        return {"status":200, "result":config.MIC_AVG_LOGPROB}

    @staticmethod
    def getMicNoSpeechProb(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_NO_SPEECH_PROB}

    @staticmethod
    def setMicNoSpeechProb(data, *args, **kwargs) -> dict:
        config.MIC_NO_SPEECH_PROB = float(data)
        return {"status":200, "result":config.MIC_NO_SPEECH_PROB}

    @staticmethod
    def getAutoSpeakerSelect(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

    def applyAutoSpeakerSelect(self) -> None:
        device_manager.setCallbackProcessBeforeUpdateSpeakerDevices(self.stopAccessSpeakerDevices)
        device_manager.setCallbackDefaultSpeakerDevice(self.updateSelectedSpeakerDevice)
        device_manager.setCallbackProcessAfterUpdateSpeakerDevices(self.restartAccessSpeakerDevices)
        device_manager.forceUpdateAndSetSpeakerDevices()

    def setEnableAutoSpeakerSelect(self, *args, **kwargs) -> dict:
        if config.AUTO_SPEAKER_SELECT is False:
            self.applyAutoSpeakerSelect()
            config.AUTO_SPEAKER_SELECT = True
        return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

    @staticmethod
    def setDisableAutoSpeakerSelect(*args, **kwargs) -> dict:
        if config.AUTO_SPEAKER_SELECT is True:
            device_manager.clearCallbackProcessBeforeUpdateSpeakerDevices()
            device_manager.clearCallbackDefaultSpeakerDevice()
            device_manager.clearCallbackProcessAfterUpdateSpeakerDevices()
            config.AUTO_SPEAKER_SELECT = False
        return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

    @staticmethod
    def getSelectedSpeakerDevice(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_SPEAKER_DEVICE}

    def setSelectedSpeakerDevice(self, data, *args, **kwargs) -> dict:
        config.SELECTED_SPEAKER_DEVICE = data
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            self.stopThreadingCheckSpeakerEnergy()
            self.startThreadingTranscriptionReceiveMessage()
        return {"status":200, "result":config.SELECTED_SPEAKER_DEVICE}

    @staticmethod
    def getSpeakerThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_THRESHOLD}

    @staticmethod
    def setSpeakerThreshold(data, *args, **kwargs) -> dict:
        printLog("Set Speaker Energy Threshold", data)
        try:
            data = int(data)
            if 0 <= data <= config.MAX_SPEAKER_THRESHOLD:
                config.SPEAKER_THRESHOLD = data
            else:
                raise ValueError()
        except Exception:
            response = {
                "status":400,
                "result":{
                    "message":"Speaker energy threshold value is out of range",
                    "data": config.SPEAKER_THRESHOLD
                }
            }
        else:
            response = {"status":200, "result":config.SPEAKER_THRESHOLD}
        return response

    @staticmethod
    def getSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setEnableSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
        if config.SPEAKER_AUTOMATIC_THRESHOLD is False:
            config.SPEAKER_AUTOMATIC_THRESHOLD = True
        return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
        if config.SPEAKER_AUTOMATIC_THRESHOLD is True:
            config.SPEAKER_AUTOMATIC_THRESHOLD = False
        return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def getSpeakerRecordTimeout(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_RECORD_TIMEOUT}

    @staticmethod
    def setSpeakerRecordTimeout(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data <= config.SPEAKER_PHRASE_TIMEOUT:
                config.SPEAKER_RECORD_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = {
                "status":400,
                "result":{
                    "message":"Speaker record timeout value is out of range",
                    "data": config.SPEAKER_RECORD_TIMEOUT
                }
            }
        else:
            response = {"status":200, "result":config.SPEAKER_RECORD_TIMEOUT}
        return response

    @staticmethod
    def getSpeakerPhraseTimeout(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_PHRASE_TIMEOUT}

    @staticmethod
    def setSpeakerPhraseTimeout(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data and data >= config.SPEAKER_RECORD_TIMEOUT:
                config.SPEAKER_PHRASE_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = {
                "status":400,
                "result":{
                    "message":"Speaker phrase timeout value is out of range",
                    "data": config.SPEAKER_PHRASE_TIMEOUT
                }
            }
        else:
            response = {"status":200, "result":config.SPEAKER_PHRASE_TIMEOUT}
        return response

    @staticmethod
    def getSpeakerMaxPhrases(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_MAX_PHRASES}

    @staticmethod
    def setSpeakerMaxPhrases(data, *args, **kwargs) -> dict:
        printLog("Set Speaker Max Phrases", data)
        try:
            data = int(data)
            if 0 <= data:
                config.SPEAKER_MAX_PHRASES = data
            else:
                raise ValueError()
        except Exception:
            response = {
                "status":400,
                "result":{
                    "message":"Speaker max phrases value is out of range",
                    "data": config.SPEAKER_MAX_PHRASES
                }
            }
        else:
            response = {"status":200, "result":config.SPEAKER_MAX_PHRASES}
        return response

    @staticmethod
    def getHotkeys(*args, **kwargs) -> dict:
        return {"status":200, "result":config.HOTKEYS}

    @staticmethod
    def setHotkeys(data, *args, **kwargs) -> dict:
        config.HOTKEYS = data
        return {"status":200, "result":config.HOTKEYS}

    @staticmethod
    def getPluginsStatus(*args, **kwargs) -> dict:
        return {"status":200, "result":config.PLUGINS_STATUS}

    @staticmethod
    def setPluginsStatus(data, *args, **kwargs) -> dict:
        config.PLUGINS_STATUS = data
        return {"status":200, "result":config.PLUGINS_STATUS}

    @staticmethod
    def getSpeakerAvgLogprob(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_AVG_LOGPROB}

    @staticmethod
    def setSpeakerAvgLogprob(data, *args, **kwargs) -> dict:
        config.SPEAKER_AVG_LOGPROB = float(data)
        return {"status":200, "result":config.SPEAKER_AVG_LOGPROB}

    @staticmethod
    def getSpeakerNoSpeechProb(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_NO_SPEECH_PROB}

    @staticmethod
    def setSpeakerNoSpeechProb(data, *args, **kwargs) -> dict:
        config.SPEAKER_NO_SPEECH_PROB = float(data)
        return {"status":200, "result":config.SPEAKER_NO_SPEECH_PROB}

    @staticmethod
    def getOscIpAddress(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OSC_IP_ADDRESS}

    def setOscIpAddress(self, data, *args, **kwargs) -> dict:
        if isValidIpAddress(data) is False:
            response = {
                "status":400,
                "result":{
                    "message":"Invalid IP address",
                    "data": config.OSC_IP_ADDRESS
                }
            }
        else:
            try:
                model.setOscIpAddress(data)
                config.OSC_IP_ADDRESS = data
                if model.getIsOscQueryEnabled() is True:
                    self.enableOscQuery()
                else:
                    mute_sync_info_flag = False
                    if config.VRC_MIC_MUTE_SYNC is True:
                        self.setDisableVrcMicMuteSync()
                        mute_sync_info_flag = True
                    self.disableOscQuery(mute_sync_info=mute_sync_info_flag)

                response = {"status":200, "result":config.OSC_IP_ADDRESS}
            except Exception:
                model.setOscIpAddress(config.OSC_IP_ADDRESS)
                response = {
                    "status":400,
                    "result":{
                        "message":"Cannot set IP address",
                        "data": config.OSC_IP_ADDRESS
                    }
                }
        return response

    @staticmethod
    def getOscPort(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OSC_PORT}

    @staticmethod
    def setOscPort(data, *args, **kwargs) -> dict:
        config.OSC_PORT = int(data)
        model.setOscPort(config.OSC_PORT)
        return {"status":200, "result":config.OSC_PORT}

    @staticmethod
    def getNotificationVrcSfx(*args, **kwargs) -> dict:
        return {"status":200, "result":config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def setEnableNotificationVrcSfx(*args, **kwargs) -> dict:
        if config.NOTIFICATION_VRC_SFX is False:
            config.NOTIFICATION_VRC_SFX = True
        return {"status":200, "result":config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def setDisableNotificationVrcSfx(*args, **kwargs) -> dict:
        if config.NOTIFICATION_VRC_SFX is True:
            config.NOTIFICATION_VRC_SFX = False
        return {"status":200, "result":config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def getDeepLAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["DeepL_API"]}

    def setDeeplAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set DeepL Auth Key", data)
        translator_name = "DeepL_API"
        try:
            data = str(data)
            if len(data) == 36 or len(data) == 39:
                result = model.authenticationTranslatorDeepLAuthKey(auth_key=data)
                if result is True:
                    key = data
                    auth_keys = config.AUTH_KEYS
                    auth_keys[translator_name] = key
                    config.AUTH_KEYS = auth_keys
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                    self.updateTranslationEngineAndEngineList()
                    response = {"status":200, "result":config.AUTH_KEYS[translator_name]}
                else:
                    response = {
                        "status":400,
                        "result":{
                            "message":"Authentication failure of deepL auth key",
                            "data": config.AUTH_KEYS[translator_name]
                        }
                    }
            else:
                response = {
                    "status":400,
                    "result":{
                        "message":"DeepL auth key length is not correct",
                        "data": config.AUTH_KEYS[translator_name]
                    }
                }
        except Exception as e:
            errorLogging()
            response = {
                "status":400,
                "result":{
                    "message":f"Error {e}",
                    "data": config.AUTH_KEYS[translator_name]
                }
            }
        return response

    def delDeeplAuthKey(self, *args, **kwargs) -> dict:
        translator_name = "DeepL_API"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}

    @staticmethod
    def getCtranslate2WeightType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CTRANSLATE2_WEIGHT_TYPE}

    @staticmethod
    def setCtranslate2WeightType(data, *args, **kwargs) -> dict:
        config.CTRANSLATE2_WEIGHT_TYPE = str(data)
        model.setChangedTranslatorParameters(True)
        return {"status":200, "result":config.CTRANSLATE2_WEIGHT_TYPE}

    @staticmethod
    def getSelectedTranslationComputeType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSLATION_COMPUTE_TYPE}

    @staticmethod
    def setSelectedTranslationComputeType(data, *args, **kwargs) -> dict:
        config.SELECTED_TRANSLATION_COMPUTE_TYPE = str(data)
        model.setChangedTranslatorParameters(True)
        return {"status":200, "result":config.SELECTED_TRANSLATION_COMPUTE_TYPE}

    @staticmethod
    def getWhisperWeightType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.WHISPER_WEIGHT_TYPE}

    @staticmethod
    def setWhisperWeightType(data, *args, **kwargs) -> dict:
        config.WHISPER_WEIGHT_TYPE = str(data)
        return {"status":200, "result": config.WHISPER_WEIGHT_TYPE}

    @staticmethod
    def getSelectedTranscriptionComputeType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE}

    @staticmethod
    def setSelectedTranscriptionComputeType(data, *args, **kwargs) -> dict:
        config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE = str(data)
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE}

    @staticmethod
    def getSendMessageFormatParts(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_FORMAT_PARTS}

    @staticmethod
    def setSendMessageFormatParts(data, *args, **kwargs) -> dict:
        config.SEND_MESSAGE_FORMAT_PARTS = dict(data)
        return {"status":200, "result":config.SEND_MESSAGE_FORMAT_PARTS}

    @staticmethod
    def getReceivedMessageFormatParts(*args, **kwargs) -> dict:
        return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_PARTS}

    @staticmethod
    def setReceivedMessageFormatParts(data, *args, **kwargs) -> dict:
        config.RECEIVED_MESSAGE_FORMAT_PARTS = dict(data)
        return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_PARTS}

    @staticmethod
    def getAutoClearMessageBox(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def setEnableAutoClearMessageBox(*args, **kwargs) -> dict:
        if config.AUTO_CLEAR_MESSAGE_BOX is False:
            config.AUTO_CLEAR_MESSAGE_BOX = True
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def setDisableAutoClearMessageBox(*args, **kwargs) -> dict:
        if config.AUTO_CLEAR_MESSAGE_BOX is True:
            config.AUTO_CLEAR_MESSAGE_BOX = False
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def getSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setEnableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.SEND_ONLY_TRANSLATED_MESSAGES is False:
            config.SEND_ONLY_TRANSLATED_MESSAGES = True
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
            config.SEND_ONLY_TRANSLATED_MESSAGES = False
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def getOverlaySmallLog(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setEnableOverlaySmallLog(*args, **kwargs) -> dict:
        if config.OVERLAY_SMALL_LOG is False:
            if config.OVERLAY_LARGE_LOG is False:
                model.startOverlay()
            config.OVERLAY_SMALL_LOG = True
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setDisableOverlaySmallLog(*args, **kwargs) -> dict:
        if config.OVERLAY_SMALL_LOG is True:
            model.clearOverlayImageSmallLog()
            if config.OVERLAY_LARGE_LOG is False:
                model.shutdownOverlay()
            config.OVERLAY_SMALL_LOG = False
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def getOverlaySmallLogSettings(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS}

    @staticmethod
    def setOverlaySmallLogSettings(data, *args, **kwargs) -> dict:
        config.OVERLAY_SMALL_LOG_SETTINGS = data
        model.updateOverlaySmallLogSettings()
        return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS}

    @staticmethod
    def getOverlayLargeLog(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_LARGE_LOG}

    @staticmethod
    def setEnableOverlayLargeLog(*args, **kwargs) -> dict:
        if config.OVERLAY_LARGE_LOG is False:
            if config.OVERLAY_SMALL_LOG is False:
                model.startOverlay()
            config.OVERLAY_LARGE_LOG = True
        return {"status":200, "result":config.OVERLAY_LARGE_LOG}

    @staticmethod
    def setDisableOverlayLargeLog(*args, **kwargs) -> dict:
        if config.OVERLAY_LARGE_LOG is True:
            model.clearOverlayImageLargeLog()
            if config.OVERLAY_SMALL_LOG is False:
                model.shutdownOverlay()
            config.OVERLAY_LARGE_LOG = False
        return {"status":200, "result":config.OVERLAY_LARGE_LOG}

    @staticmethod
    def getOverlayLargeLogSettings(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_LARGE_LOG_SETTINGS}

    @staticmethod
    def setOverlayLargeLogSettings(data, *args, **kwargs) -> dict:
        config.OVERLAY_LARGE_LOG_SETTINGS = data
        model.updateOverlayLargeLogSettings()
        return {"status":200, "result":config.OVERLAY_LARGE_LOG_SETTINGS}

    @staticmethod
    def getOverlayShowOnlyTranslatedMessages(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setEnableOverlayShowOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is False:
            config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = True
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableOverlayShowOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
            config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = False
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def getSendMessageToVrc(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def setEnableSendMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is False:
            config.SEND_MESSAGE_TO_VRC = True
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is True:
            config.SEND_MESSAGE_TO_VRC = False
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def getSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def setEnableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_RECEIVED_MESSAGE_TO_VRC is False:
            config.SEND_RECEIVED_MESSAGE_TO_VRC = True
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_RECEIVED_MESSAGE_TO_VRC is True:
            config.SEND_RECEIVED_MESSAGE_TO_VRC = False
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def getLoggerFeature(*args, **kwargs) -> dict:
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def setEnableLoggerFeature(*args, **kwargs) -> dict:
        if config.LOGGER_FEATURE is False:
            model.startLogger()
            config.LOGGER_FEATURE = True
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def setDisableLoggerFeature(*args, **kwargs) -> dict:
        if config.LOGGER_FEATURE is True:
            model.stopLogger()
            config.LOGGER_FEATURE = False
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def getVrcMicMuteSync(*args, **kwargs) -> dict:
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    @staticmethod
    def setEnableVrcMicMuteSync(*args, **kwargs) -> dict:
        if config.VRC_MIC_MUTE_SYNC is False:
            if model.getIsOscQueryEnabled() is True:
                config.VRC_MIC_MUTE_SYNC = True
                model.setMuteSelfStatus()
                model.changeMicTranscriptStatus()
                response = {"status":200, "result":config.VRC_MIC_MUTE_SYNC}
            else:
                response = {
                        "status":400,
                        "result":{
                            "message":"Cannot enable VRC mic mute sync while OSC query is disabled",
                            "data": config.VRC_MIC_MUTE_SYNC
                        }
                }
        else:
            response = {"status":200, "result":config.VRC_MIC_MUTE_SYNC}
        return response

    @staticmethod
    def setDisableVrcMicMuteSync(*args, **kwargs) -> dict:
        if config.VRC_MIC_MUTE_SYNC is True:
            config.VRC_MIC_MUTE_SYNC = False
            model.changeMicTranscriptStatus()
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    def setEnableCheckSpeakerThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_RECEIVE is False:
            self.startThreadingCheckSpeakerEnergy()
            config.ENABLE_CHECK_ENERGY_RECEIVE = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setDisableCheckSpeakerThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            self.stopThreadingCheckSpeakerEnergy()
            config.ENABLE_CHECK_ENERGY_RECEIVE = False
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setEnableCheckMicThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_SEND is False:
            self.startThreadingCheckMicEnergy()
            config.ENABLE_CHECK_ENERGY_SEND = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

    def setDisableCheckMicThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            self.stopThreadingCheckMicEnergy()
            config.ENABLE_CHECK_ENERGY_SEND = False
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

    @staticmethod
    def openFilepathLogs(*args, **kwargs) -> dict:
        Popen(['explorer', config.PATH_LOGS.replace('/', '\\')], shell=True)
        return {"status":200, "result":True}

    @staticmethod
    def openFilepathConfigFile(*args, **kwargs) -> dict:
        Popen(['explorer', config.PATH_LOCAL.replace('/', '\\')], shell=True)
        return {"status":200, "result":True}

    def setEnableTranscriptionSend(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_SEND is False:
            self.startThreadingTranscriptionSendMessage()
            config.ENABLE_TRANSCRIPTION_SEND = True
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

    def setDisableTranscriptionSend(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.stopThreadingTranscriptionSendMessage()
            config.ENABLE_TRANSCRIPTION_SEND = False
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

    def setEnableTranscriptionReceive(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is False:
            self.startThreadingTranscriptionReceiveMessage()
            config.ENABLE_TRANSCRIPTION_RECEIVE = True
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

    def setDisableTranscriptionReceive(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.stopThreadingTranscriptionReceiveMessage()
            config.ENABLE_TRANSCRIPTION_RECEIVE = False
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

    def sendMessageBox(self, data, *args, **kwargs) -> dict:
        response = self.chatMessage(data)
        return response

    @staticmethod
    def typingMessageBox(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is True:
            model.oscStartSendTyping()
        return {"status":200, "result":True}

    @staticmethod
    def stopTypingMessageBox(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is True:
            model.oscStopSendTyping()
        return {"status":200, "result":True}

    @staticmethod
    def sendTextOverlay(data, *args, **kwargs) -> dict:
        if config.OVERLAY_SMALL_LOG is True:
            if model.overlay.initialized is True:
                overlay_image = model.createOverlayImageSmallMessage(data)
                model.updateOverlaySmallLog(overlay_image)

        if config.OVERLAY_LARGE_LOG is True:
            if model.overlay.initialized is True:
                overlay_image = model.createOverlayImageLargeMessage(data)
                model.updateOverlayLargeLog(overlay_image)
        return {"status":200, "result":data}

    def swapYourLanguageAndTargetLanguage(self, *args, **kwargs) -> dict:
        your_languages = config.SELECTED_YOUR_LANGUAGES
        your_language_temp = your_languages[config.SELECTED_TAB_NO]["1"]

        target_languages = config.SELECTED_TARGET_LANGUAGES
        target_language_temp = target_languages[config.SELECTED_TAB_NO]["1"]

        your_languages[config.SELECTED_TAB_NO]["1"] = target_language_temp
        target_languages[config.SELECTED_TAB_NO]["1"] = your_language_temp

        self.setSelectedYourLanguages(your_languages)
        self.setSelectedTargetLanguages(target_languages)
        return {
            "status":200,
            "result":{
                "your":config.SELECTED_YOUR_LANGUAGES,
                "target":config.SELECTED_TARGET_LANGUAGES,
                }
            }

    def updateSoftware(self, *args, **kwargs) -> dict:
        th_start_update_software = Thread(target=model.updateSoftware)
        th_start_update_software.daemon = True
        th_start_update_software.start()
        return {"status":200, "result":True}

    def updateCudaSoftware(self, *args, **kwargs) -> dict:
        th_start_update_cuda_software = Thread(target=model.updateCudaSoftware)
        th_start_update_cuda_software.daemon = True
        th_start_update_cuda_software.start()
        return {"status":200, "result":True}

    def downloadCtranslate2Weight(self, data:str, asynchronous:bool=True, *args, **kwargs) -> dict:
        weight_type = str(data)
        download_ctranslate2 = self.DownloadCTranslate2(
            self.run_mapping,
            weight_type,
            self.run
            )

        if asynchronous is True:
            self.startThreadingDownloadCtranslate2Weight(
                weight_type,
                download_ctranslate2.progressBar,
                download_ctranslate2.downloaded,
                )
        else:
            model.downloadCTranslate2ModelWeight(weight_type, download_ctranslate2.progressBar, download_ctranslate2.downloaded)
        model.downloadCTranslate2ModelTokenizer(weight_type)
        return {"status":200, "result":True}

    def downloadWhisperWeight(self, data:str, asynchronous:bool=True, *args, **kwargs) -> dict:
        weight_type = str(data)
        download_whisper = self.DownloadWhisper(
            self.run_mapping,
            weight_type,
            self.run
        )
        if asynchronous is True:
            self.startThreadingDownloadWhisperWeight(
                weight_type,
                download_whisper.progressBar,
                download_whisper.downloaded,
                )
        else:
            model.downloadWhisperModelWeight(weight_type, download_whisper.progressBar, download_whisper.downloaded)
        return {"status":200, "result":True}

    @staticmethod
    def messageFormatter(format_type:str, translation:list, message:str) -> str:
        if format_type == "RECEIVED":
            format_parts = config.RECEIVED_MESSAGE_FORMAT_PARTS
        elif format_type == "SEND":
            format_parts = config.SEND_MESSAGE_FORMAT_PARTS
        else:
            raise ValueError("format_type is not found", format_type)

        message_part = format_parts["message"]["prefix"] + message + format_parts["message"]["suffix"]
        translation_part = format_parts["translation"]["prefix"] + format_parts["translation"]["separator"].join(translation) + format_parts["translation"]["suffix"]

        if len(translation) > 0 and message != "":
            # 翻訳とメッセージの順序を決定
            if format_parts["translation_first"]:
                osc_message = translation_part + format_parts["separator"] + message_part
            else:
                osc_message = message_part + format_parts["separator"] + translation_part
        elif len(translation) > 0 and message == "":
            osc_message = translation_part
        else:
            osc_message = message_part
        return osc_message

    def changeToCTranslate2Process(self) -> None:
        selected_engines = config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO]
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[selected_engines] = False
        config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO] = "CTranslate2"
        selectable_engines = self.getTranslationEngines()["result"]
        self.run(200, self.run_mapping["selected_translation_engines"], config.SELECTED_TRANSLATION_ENGINES)
        self.run(200, self.run_mapping["translation_engines"], selectable_engines)

    def startTranscriptionSendMessage(self) -> None:
        while self.device_access_status is False:
            sleep(1)
        self.device_access_status = False
        try:
            model.startMicTranscript(self.micMessage)
        except Exception as e:
            # VRAM不足エラーの検出
            is_vram_error, error_message = model.detectVRAMError(e)
            if is_vram_error:
                self.run(
                    400,
                    self.run_mapping["error_transcription_mic_vram_overflow"],
                    {
                        "message":"VRAM out of memory during mic transcription",
                        "data": error_message
                    },
                )
                # ここでマイクの音声認識を停止
                self.stopTranscriptionSendMessage()
                self.run(
                    400,
                    self.run_mapping["enable_transcription_send"],
                    {
                        "message":"Transcription send disabled due to VRAM overflow",
                        "data": False
                    },
                )
            else:
                # その他のエラーは通常通り処理
                errorLogging()
        finally:
            self.device_access_status = True

    @staticmethod
    def stopTranscriptionSendMessage() -> None:
        model.stopMicTranscript()

    def startThreadingTranscriptionSendMessage(self) -> None:
        th_startTranscriptionSendMessage = Thread(target=self.startTranscriptionSendMessage)
        th_startTranscriptionSendMessage.daemon = True
        th_startTranscriptionSendMessage.start()

    def stopThreadingTranscriptionSendMessage(self) -> None:
        th_stopTranscriptionSendMessage = Thread(target=self.stopTranscriptionSendMessage)
        th_stopTranscriptionSendMessage.daemon = True
        th_stopTranscriptionSendMessage.start()
        th_stopTranscriptionSendMessage.join()

    def startTranscriptionReceiveMessage(self) -> None:
        while self.device_access_status is False:
            sleep(1)
        self.device_access_status = False
        try:
            model.startSpeakerTranscript(self.speakerMessage)
        except Exception as e:
            # VRAM不足エラーの検出
            is_vram_error, error_message = model.detectVRAMError(e)
            if is_vram_error:
                self.run(
                    400,
                    self.run_mapping["error_transcription_speaker_vram_overflow"],
                    {
                        "message":"VRAM out of memory during speaker transcription",
                        "data": error_message
                    },
                )
                # ここでスピーカーの音声認識を停止
                self.stopTranscriptionReceiveMessage()
                self.run(
                    400,
                    self.run_mapping["enable_transcription_receive"],
                    {
                        "message":"Transcription receive disabled due to VRAM overflow",
                        "data": False
                    },
                )
            else:
                # その他のエラーは通常通り処理
                errorLogging()
        finally:
            self.device_access_status = True

    @staticmethod
    def stopTranscriptionReceiveMessage() -> None:
        model.stopSpeakerTranscript()

    def startThreadingTranscriptionReceiveMessage(self) -> None:
        th_startTranscriptionReceiveMessage = Thread(target=self.startTranscriptionReceiveMessage)
        th_startTranscriptionReceiveMessage.daemon = True
        th_startTranscriptionReceiveMessage.start()

    def stopThreadingTranscriptionReceiveMessage(self) -> None:
        th_stopTranscriptionReceiveMessage = Thread(target=self.stopTranscriptionReceiveMessage)
        th_stopTranscriptionReceiveMessage.daemon = True
        th_stopTranscriptionReceiveMessage.start()
        th_stopTranscriptionReceiveMessage.join()

    @staticmethod
    def replaceExclamationsWithRandom(text):
        # ![...] にマッチする正規表現
        pattern = r'!\[(.*?)\]'

        # 乱数と置換部分を保存する辞書
        replacement_dict = {}

        num = 4096
        # マッチした部分を4096から始まる整数に置換する。置換毎に4097, 4098, ... と増える
        def replace(match):
            original = match.group(1)
            nonlocal num
            rand_value = hex(num)
            replacement_dict[rand_value] = original
            num += 1
            return f" ${rand_value} "

        # 文章内の ![] の部分を置換
        replaced_text = re.sub(pattern, replace, text)

        return replaced_text, replacement_dict

    @staticmethod
    def restoreText(escaped_text, escape_dict):
        # 大文字小文字を無視して置換するために、正規表現を使う
        for escape_seq, char in escape_dict.items():
            # escaped_text の部分を pattern で置換
            pattern = re.escape(f"${escape_seq}") + r"|\$\s+" + re.escape(escape_seq)
            escaped_text = re.sub(pattern, char, escaped_text, flags=re.IGNORECASE)
        return escaped_text

    @staticmethod
    def removeExclamations(text):
        # ![...] を [...] に置換する正規表現
        pattern = r'!\[(.*?)\]'
        # ![...] の部分を [] 内のテキストに置換
        cleaned_text = re.sub(pattern, r'\1', text)
        return cleaned_text

    def updateDownloadedCTranslate2ModelWeight(self) -> None:
        weight_type_dict = config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT
        for weight_type in weight_type_dict.keys():
            weight_type_dict[weight_type] = model.checkTranslatorCTranslate2ModelWeight(weight_type)
        config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT = weight_type_dict

    def updateTranslationEngineAndEngineList(self):
        engines = config.SELECTED_TRANSLATION_ENGINES
        engine = engines[config.SELECTED_TAB_NO]
        selectable_engines = self.getTranslationEngines()["result"]
        if engine not in selectable_engines:
            engine = "CTranslate2"
        engines[config.SELECTED_TAB_NO] = engine
        config.SELECTED_TRANSLATION_ENGINES = engines

        your_language = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]
        for target_language in config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO].values():
            if your_language["language"] == target_language["language"] and target_language["enable"] is True:
                engines[config.SELECTED_TAB_NO] = "CTranslate2"
                config.SELECTED_TRANSLATION_ENGINES = engines
                break

        self.run(200, self.run_mapping["selected_translation_engines"], config.SELECTED_TRANSLATION_ENGINES)
        self.run(200, self.run_mapping["translation_engines"], selectable_engines)

    def updateDownloadedWhisperModelWeight(self) -> None:
        weight_type_dict = config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT
        for weight_type in weight_type_dict.keys():
            weight_type_dict[weight_type] = model.checkTranscriptionWhisperModelWeight(weight_type)
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = weight_type_dict

    def updateTranscriptionEngine(self):
        weight_type = config.WHISPER_WEIGHT_TYPE
        weight_type_dict = config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT
        weight_available = bool(weight_type_dict.get(weight_type))
        current_engine = config.SELECTED_TRANSCRIPTION_ENGINE
        selected_engines = [key for key, value in config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS.items() if value is True]

        # 選択可能なエンジンがなければ、Whisper に変更
        if current_engine in {"Whisper", "Google"}:
            if current_engine not in selected_engines:
                if weight_available:
                    alternate = "Google" if current_engine == "Whisper" else "Whisper"
                    config.SELECTED_TRANSCRIPTION_ENGINE = alternate if alternate in selected_engines else None
                else:
                    config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        else:
            config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"

    def startCheckMicEnergy(self) -> None:
        while self.device_access_status is False:
            sleep(1)
        self.device_access_status = False
        model.startCheckMicEnergy(self.progressBarMicEnergy)
        self.device_access_status = True

    def startThreadingCheckMicEnergy(self) -> None:
        th_startCheckMicEnergy = Thread(target=self.startCheckMicEnergy)
        th_startCheckMicEnergy.daemon = True
        th_startCheckMicEnergy.start()

    def stopCheckMicEnergy(self) -> None:
        model.stopCheckMicEnergy()

    def stopThreadingCheckMicEnergy(self) -> None:
        th_stopCheckMicEnergy = Thread(target=self.stopCheckMicEnergy)
        th_stopCheckMicEnergy.daemon = True
        th_stopCheckMicEnergy.start()
        th_stopCheckMicEnergy.join()

    def startCheckSpeakerEnergy(self) -> None:
        while self.device_access_status is False:
            sleep(1)
        self.device_access_status = False
        model.startCheckSpeakerEnergy(self.progressBarSpeakerEnergy)
        self.device_access_status = True

    def startThreadingCheckSpeakerEnergy(self) -> None:
        th_startCheckSpeakerEnergy = Thread(target=self.startCheckSpeakerEnergy)
        th_startCheckSpeakerEnergy.daemon = True
        th_startCheckSpeakerEnergy.start()

    def stopCheckSpeakerEnergy(self) -> None:
        model.stopCheckSpeakerEnergy()

    def stopThreadingCheckSpeakerEnergy(self) -> None:
        th_stopCheckSpeakerEnergy = Thread(target=self.stopCheckSpeakerEnergy)
        th_stopCheckSpeakerEnergy.daemon = True
        th_stopCheckSpeakerEnergy.start()
        th_stopCheckSpeakerEnergy.join()

    @staticmethod
    def startThreadingDownloadCtranslate2Weight(weight_type:str, callback:Callable[[float], None], end_callback:Callable[[float], None]) -> None:
        th_download = Thread(target=model.downloadCTranslate2ModelWeight, args=(weight_type, callback, end_callback))
        th_download.daemon = True
        th_download.start()

    @staticmethod
    def startThreadingDownloadWhisperWeight(weight_type:str, callback:Callable[[float], None], end_callback:Callable[[float], None]) -> None:
        th_download = Thread(target=model.downloadWhisperModelWeight, args=(weight_type, callback, end_callback))
        th_download.daemon = True
        th_download.start()

    @staticmethod
    def startWatchdog(*args, **kwargs) -> dict:
        model.startWatchdog()
        return {"status":200, "result":True}

    @staticmethod
    def feedWatchdog(*args, **kwargs) -> dict:
        model.feedWatchdog()
        return {"status":200, "result":True}

    @staticmethod
    def setWatchdogCallback(callback) -> dict:
        model.setWatchdogCallback(callback)

    @staticmethod
    def stopWatchdog(*args, **kwargs) -> dict:
        model.stopWatchdog()
        return {"status":200, "result":True}

    @staticmethod
    def getWebSocketHost(*args, **kwargs) -> dict:
        return {"status":200, "result":config.WEBSOCKET_HOST}

    @staticmethod
    def setWebSocketHost(data, *args, **kwargs) -> dict:
        if isValidIpAddress(data) is False:
            response = {
                "status":400,
                "result":{
                    "message":"Invalid IP address",
                    "data": config.WEBSOCKET_HOST
                }
            }
        else:
            if model.checkWebSocketServerAlive() is False:
                config.WEBSOCKET_HOST = data
                response = {"status":200, "result":config.WEBSOCKET_HOST}
            else:
                if data == config.WEBSOCKET_HOST:
                    response = {"status":200, "result":config.WEBSOCKET_HOST}
                elif isAvailableWebSocketServer(data, config.WEBSOCKET_PORT):
                    model.stopWebSocketServer()
                    model.startWebSocketServer(data, config.WEBSOCKET_PORT)
                    config.WEBSOCKET_HOST = data
                    response = {"status":200, "result":config.WEBSOCKET_HOST}
                else:
                    response = {
                        "status":400,
                        "result":{
                            "message":"WebSocket server host is not available",
                            "data": config.WEBSOCKET_HOST
                        }
                    }

        return response

    @staticmethod
    def getWebSocketPort(*args, **kwargs) -> dict:
        return {"status":200, "result":config.WEBSOCKET_PORT}

    @staticmethod
    def setWebSocketPort(data, *args, **kwargs) -> dict:
        if model.checkWebSocketServerAlive() is False:
            config.WEBSOCKET_PORT = int(data)
            response = {"status":200, "result":config.WEBSOCKET_PORT}
        else:
            if int(data) == config.WEBSOCKET_PORT:
                return {"status":200, "result":config.WEBSOCKET_PORT}
            elif isAvailableWebSocketServer(config.WEBSOCKET_HOST, int(data)) is True:
                model.stopWebSocketServer()
                model.startWebSocketServer(config.WEBSOCKET_HOST, int(data))
                config.WEBSOCKET_PORT = int(data)
                response = {"status":200, "result":config.WEBSOCKET_PORT}
            else:
                response = {
                    "status":400,
                    "result":{
                        "message":"WebSocket server port is not available",
                        "data": config.WEBSOCKET_PORT
                    }
                }
        return response

    @staticmethod
    def getWebSocketServer(*args, **kwargs) -> dict:
        return {"status":200, "result":config.WEBSOCKET_SERVER}

    @staticmethod
    def setEnableWebSocketServer(*args, **kwargs) -> dict:
        if config.WEBSOCKET_SERVER is False:
            if isAvailableWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT) is True:
                model.startWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT)
                config.WEBSOCKET_SERVER = True
                response = {"status":200, "result":config.WEBSOCKET_SERVER}
            else:
                response = {
                    "status":400,
                    "result":{
                        "message":"WebSocket server host or port is not available",
                        "data": config.WEBSOCKET_SERVER
                    }
                }
        else:
            response = {"status":200, "result":config.WEBSOCKET_SERVER}
        return response

    @staticmethod
    def setDisableWebSocketServer(*args, **kwargs) -> dict:
        if config.WEBSOCKET_SERVER is True:
            config.WEBSOCKET_SERVER = False
            model.stopWebSocketServer()
        return {"status":200, "result":config.WEBSOCKET_SERVER}

    def initializationProgress(self, progress):
        self.run(200, self.run_mapping["initialization_progress"], progress)

    def enableOscQuery(self):
        self.run(
            200,
            self.run_mapping["enable_osc_query"],
            {
                "data": True,
                "disabled_functions": []
            }
        )

    def disableOscQuery(self, mute_sync_info:bool=False):
        disabled_functions = []
        if mute_sync_info is True:
            disabled_functions.append("vrc_mic_mute_sync")
        self.run(200, self.run_mapping["enable_osc_query"], {
            "data": False,
            "disabled_functions": disabled_functions
        })

    def init(self, *args, **kwargs) -> None:
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
            match engine:
                case "CTranslate2":
                    if model.checkTranslatorCTranslate2ModelWeight(config.CTRANSLATE2_WEIGHT_TYPE) is True:
                        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = True
                    else:
                        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = False
                case "DeepL_API":
                    printLog("Start check DeepL API Key")
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = False
                    if config.AUTH_KEYS[engine] is not None:
                        if model.authenticationTranslatorDeepLAuthKey(auth_key=config.AUTH_KEYS[engine]) is True:
                            config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = True
                        else:
                            # error update Auth key
                            auth_keys = config.AUTH_KEYS
                            auth_keys[engine] = None
                            config.AUTH_KEYS = auth_keys
                case _:
                    if connected_network is True:
                        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = True
                    else:
                        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = False

        for engine in config.SELECTABLE_TRANSCRIPTION_ENGINE_LIST:
            match engine:
                case "Whisper":
                    if model.checkTranscriptionWhisperModelWeight(config.WHISPER_WEIGHT_TYPE) is True:
                        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = True
                    else:
                        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False
                case _:
                    if connected_network is True:
                        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = True
                    else:
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

        # set Transliteration status
        printLog("Set Transliteration")
        if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
            model.startTransliteration()

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
            if config.VRC_MIC_MUTE_SYNC is True:
                self.setEnableVrcMicMuteSync()
        else:
            # OSC Query is disabled, so disable VRC some features
            mute_sync_info_flag = False
            if config.VRC_MIC_MUTE_SYNC is True:
                self.setDisableVrcMicMuteSync()
                mute_sync_info_flag = True
            self.disableOscQuery(mute_sync_info=mute_sync_info_flag)

        # init Auto device selection
        printLog("Init Device Manager")
        device_manager.setCallbackHostList(self.updateMicHostList)
        device_manager.setCallbackMicDeviceList(self.updateMicDeviceList)
        device_manager.setCallbackSpeakerDeviceList(self.updateSpeakerDeviceList)

        printLog("Init Auto Device Selection")
        if config.AUTO_MIC_SELECT is True:
            self.applyAutoMicSelect()
        if config.AUTO_SPEAKER_SELECT is True:
            self.applyAutoSpeakerSelect()

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