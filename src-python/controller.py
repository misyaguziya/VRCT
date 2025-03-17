from typing import Callable, Union, Any
from time import sleep
from subprocess import Popen
from threading import Thread
import re
from device_manager import device_manager
from config import config
from model import model
from utils import removeLog, printLog, errorLogging, isConnectedNetwork

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

    def restartAccessDevices(self) -> None:
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
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.stopThreadingTranscriptionSendMessage()
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.stopThreadingTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            model.stopCheckMicEnergy()
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
                    "message":"No Speaker device detected",
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
            transliteration = []
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

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese":
                        transliteration = model.convertMessageToTransliteration(translation[0])

            if config.ENABLE_TRANSCRIPTION_SEND is True:
                if config.SEND_MESSAGE_TO_VRC is True:
                    if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                        if config.ENABLE_TRANSLATION is False:
                            osc_message = self.messageFormatter("SEND", "", [message])
                        else:
                            osc_message = self.messageFormatter("SEND", "", translation)
                    else:
                        osc_message = self.messageFormatter("SEND", translation, [message])
                    model.oscSendMessage(osc_message)

                self.run(
                    200,
                    self.run_mapping["transcription_mic"],
                    {
                        "message":message,
                        "translation":translation,
                        "transliteration":transliteration
                    })
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
            transliteration = []
            if model.detectRepeatReceiveMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
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

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese":
                        transliteration = model.convertMessageToTransliteration(message)

            if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
                if config.OVERLAY_SMALL_LOG is True and model.overlay.initialized is True:
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True and len(translation) > 0:
                        overlay_image = model.createOverlayImageSmallLog(translation[0], "")
                    else:
                        overlay_image = model.createOverlayImageSmallLog(message, translation[0] if len(translation) > 0 else "")
                    model.updateOverlaySmallLog(overlay_image)

                if config.OVERLAY_LARGE_LOG is True and model.overlay.initialized is True:
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True and len(translation) > 0:
                        overlay_image = model.createOverlayImageLargeLog("receive", translation[0], "")
                    else:
                        overlay_image = model.createOverlayImageLargeLog("receive", message, translation[0] if len(translation) > 0 else "")
                    model.updateOverlayLargeLog(overlay_image)

                if config.SEND_RECEIVED_MESSAGE_TO_VRC is True:
                    osc_message = self.messageFormatter("RECEIVED", translation, [message])
                    model.oscSendMessage(osc_message)

                # update textbox message log (Received)
                self.run(
                    200,
                    self.run_mapping["transcription_speaker"],
                    {
                        "message":message,
                        "translation":translation,
                        "transliteration":transliteration,
                    })
                if config.LOGGER_FEATURE is True:
                    if len(translation) > 0:
                        translation = " (" + "/".join(translation) + ")"
                    model.logger.info(f"[RECEIVED] {message}{translation}")

    def chatMessage(self, data) -> None:
        id = data["id"]
        message = data["message"]
        if len(message) > 0:
            translation = []
            transliteration = []
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
                    self.run(
                        400,
                        self.run_mapping["error_translation_engine"],
                        {
                            "message":"Translation engine limit error",
                            "data": None
                        },
                    )

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese":
                        transliteration = model.convertMessageToTransliteration(translation[0])

            # send OSC message
            if config.SEND_MESSAGE_TO_VRC is True:
                if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                    if config.ENABLE_TRANSLATION is False:
                        osc_message = self.messageFormatter("SEND", "", [message])
                    else:
                        osc_message = self.messageFormatter("SEND", "", translation)
                else:
                    osc_message = self.messageFormatter("SEND", translation, [message])
                model.oscSendMessage(osc_message)

            if config.OVERLAY_LARGE_LOG is True:
                if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True and len(translation) > 0:
                    overlay_image = model.createOverlayImageLargeLog("send", translation[0], "")
                else:
                    overlay_image = model.createOverlayImageLargeLog("send", message, translation[0] if len(translation) > 0 else "")
                model.updateOverlayLargeLog(overlay_image)

            # update textbox message log (Sent)
            if config.LOGGER_FEATURE is True:
                if len(translation) > 0:
                    translation_text = " (" + "/".join(translation) + ")"
                model.logger.info(f"[SENT] {message}{translation_text}")

        return {"status":200,
                "result":{
                    "id":id,
                    "message":message,
                    "translation":translation,
                    "transliteration":transliteration,
                    },
                }

    @staticmethod
    def getVersion(*args, **kwargs) -> dict:
        return {"status":200, "result":config.VERSION}

    def checkSoftwareUpdated(self) -> dict:
        update_flag =  model.checkSoftwareUpdated()
        self.run(
            200,
            self.run_mapping["update_software_flag"],
            update_flag,
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

    @staticmethod
    def setSelectedTranslationComputeDevice(device:str, *args, **kwargs) -> dict:
        printLog("setSelectedTranslationComputeDevice", device)
        config.SELECTED_TRANSLATION_COMPUTE_DEVICE = device
        model.changeTranslatorCTranslate2Model()
        return {"status":200,"result":config.SELECTED_TRANSLATION_COMPUTE_DEVICE}

    @staticmethod
    def getSelectableCtranslate2WeightTypeDict(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT}

    @staticmethod
    def getSelectedTranscriptionComputeDevice(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE}

    @staticmethod
    def setSelectedTranscriptionComputeDevice(device:str, *args, **kwargs) -> dict:
        printLog("setSelectedTranscriptionComputeDevice", device)
        config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = device
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

    @staticmethod
    def setEnableTranslation(*args, **kwargs) -> dict:
        if model.isLoadedCTranslate2Model() is False:
            model.changeTranslatorCTranslate2Model()
        config.ENABLE_TRANSLATION = True
        return {"status":200, "result":config.ENABLE_TRANSLATION}

    @staticmethod
    def setDisableTranslation(*args, **kwargs) -> dict:
        config.ENABLE_TRANSLATION = False
        return {"status":200, "result":config.ENABLE_TRANSLATION}

    @staticmethod
    def setEnableForeground(*args, **kwargs) -> dict:
        config.ENABLE_FOREGROUND = True
        return {"status":200, "result":config.ENABLE_FOREGROUND}

    @staticmethod
    def setDisableForeground(*args, **kwargs) -> dict:
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
        config.CONVERT_MESSAGE_TO_ROMAJI = True
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def setDisableConvertMessageToRomaji(*args, **kwargs) -> dict:
        config.CONVERT_MESSAGE_TO_ROMAJI = False
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def getConvertMessageToHiragana(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def setEnableConvertMessageToHiragana(*args, **kwargs) -> dict:
        config.CONVERT_MESSAGE_TO_HIRAGANA = True
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def setDisableConvertMessageToHiragana(*args, **kwargs) -> dict:
        config.CONVERT_MESSAGE_TO_HIRAGANA = False
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def getMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def setEnableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def setDisableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
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

    def setEnableAutoMicSelect(self, *args, **kwargs) -> dict:
        config.AUTO_MIC_SELECT = True
        device_manager.setCallbackProcessBeforeUpdateDevices(self.stopAccessDevices)
        device_manager.setCallbackDefaultMicDevice(self.updateSelectedMicDevice)
        device_manager.setCallbackProcessAfterUpdateDevices(self.restartAccessDevices)
        device_manager.forceUpdateAndSetMicDevices()
        return {"status":200, "result":config.AUTO_MIC_SELECT}

    @staticmethod
    def setDisableAutoMicSelect(*args, **kwargs) -> dict:
        device_manager.clearCallbackProcessBeforeUpdateDevices()
        device_manager.clearCallbackDefaultMicDevice()
        device_manager.clearCallbackProcessAfterUpdateDevices()
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
            errorLogging()
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
        config.MIC_AUTOMATIC_THRESHOLD = True
        return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableMicAutomaticThreshold(*args, **kwargs) -> dict:
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
            errorLogging()
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
            errorLogging()
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
            errorLogging()
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

    def setEnableAutoSpeakerSelect(self, *args, **kwargs) -> dict:
        config.AUTO_SPEAKER_SELECT = True
        device_manager.setCallbackProcessBeforeUpdateDevices(self.stopAccessDevices)
        device_manager.setCallbackDefaultSpeakerDevice(self.updateSelectedSpeakerDevice)
        device_manager.setCallbackProcessAfterUpdateDevices(self.restartAccessDevices)
        device_manager.forceUpdateAndSetSpeakerDevices()

        return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

    @staticmethod
    def setDisableAutoSpeakerSelect(*args, **kwargs) -> dict:
        device_manager.clearCallbackProcessBeforeUpdateDevices()
        device_manager.clearCallbackDefaultSpeakerDevice()
        device_manager.clearCallbackProcessAfterUpdateDevices()
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
            errorLogging()
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
        config.SPEAKER_AUTOMATIC_THRESHOLD = True
        return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
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
            errorLogging()
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
            errorLogging()
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
            errorLogging()
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

    @staticmethod
    def setOscIpAddress(data, *args, **kwargs) -> dict:
        config.OSC_IP_ADDRESS = data
        model.setOscIpAddress(config.OSC_IP_ADDRESS)
        return {"status":200, "result":config.OSC_IP_ADDRESS}

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
        config.NOTIFICATION_VRC_SFX = True
        return {"status":200, "result":config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def setDisableNotificationVrcSfx(*args, **kwargs) -> dict:
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
                            "message":"DeepL auth key length is not correct",
                            "data": config.AUTH_KEYS[translator_name]
                        }
                    }
            else:
                response = {
                    "status":400,
                    "result":{
                        "message":"Authentication failure of deepL auth key",
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
        if model.checkTranslatorCTranslate2ModelWeight(config.CTRANSLATE2_WEIGHT_TYPE):
            def callback():
                model.changeTranslatorCTranslate2Model()
            th_callback = Thread(target=callback)
            th_callback.daemon = True
            th_callback.start()
            th_callback.join()
        return {"status":200, "result":config.CTRANSLATE2_WEIGHT_TYPE}

    @staticmethod
    def getWhisperWeightType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.WHISPER_WEIGHT_TYPE}

    @staticmethod
    def setWhisperWeightType(data, *args, **kwargs) -> dict:
        config.WHISPER_WEIGHT_TYPE = str(data)
        return {"status":200, "result": config.WHISPER_WEIGHT_TYPE}

    @staticmethod
    def getAutoClearMessageBox(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def setEnableAutoClearMessageBox(*args, **kwargs) -> dict:
        config.AUTO_CLEAR_MESSAGE_BOX = True
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def setDisableAutoClearMessageBox(*args, **kwargs) -> dict:
        config.AUTO_CLEAR_MESSAGE_BOX = False
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def getSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setEnableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        config.SEND_ONLY_TRANSLATED_MESSAGES = True
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        config.SEND_ONLY_TRANSLATED_MESSAGES = False
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def getSendMessageButtonType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}

    @staticmethod
    def setSendMessageButtonType(data, *args, **kwargs) -> dict:
        config.SEND_MESSAGE_BUTTON_TYPE = data
        return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}

    @staticmethod
    def getOverlaySmallLog(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setEnableOverlaySmallLog(*args, **kwargs) -> dict:
        config.OVERLAY_SMALL_LOG = True
        if config.OVERLAY_LARGE_LOG is False:
            model.startOverlay()
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setDisableOverlaySmallLog(*args, **kwargs) -> dict:
        config.OVERLAY_SMALL_LOG = False
        model.clearOverlayImageSmallLog()
        if config.OVERLAY_LARGE_LOG is False:
            model.shutdownOverlay()
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
        config.OVERLAY_LARGE_LOG = True
        if config.OVERLAY_SMALL_LOG is False:
            model.startOverlay()
        return {"status":200, "result":config.OVERLAY_LARGE_LOG}

    @staticmethod
    def setDisableOverlayLargeLog(*args, **kwargs) -> dict:
        config.OVERLAY_LARGE_LOG = False
        model.clearOverlayImageLargeLog()
        if config.OVERLAY_SMALL_LOG is False:
            model.shutdownOverlay()
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
        config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = True
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableOverlayShowOnlyTranslatedMessages(*args, **kwargs) -> dict:
        config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = False
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def getSendMessageToVrc(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def setEnableSendMessageToVrc(*args, **kwargs) -> dict:
        config.SEND_MESSAGE_TO_VRC = True
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendMessageToVrc(*args, **kwargs) -> dict:
        config.SEND_MESSAGE_TO_VRC = False
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def getSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def setEnableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        config.SEND_RECEIVED_MESSAGE_TO_VRC = True
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        config.SEND_RECEIVED_MESSAGE_TO_VRC = False
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def getLoggerFeature(*args, **kwargs) -> dict:
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def setEnableLoggerFeature(*args, **kwargs) -> dict:
        config.LOGGER_FEATURE = True
        model.startLogger()
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def setDisableLoggerFeature(*args, **kwargs) -> dict:
        model.stopLogger()
        config.LOGGER_FEATURE = False
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def getVrcMicMuteSync(*args, **kwargs) -> dict:
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    @staticmethod
    def setEnableVrcMicMuteSync(*args, **kwargs) -> dict:
        config.VRC_MIC_MUTE_SYNC = True
        model.setMuteSelfStatus()
        model.changeMicTranscriptStatus()
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    @staticmethod
    def setDisableVrcMicMuteSync(*args, **kwargs) -> dict:
        config.VRC_MIC_MUTE_SYNC = False
        model.changeMicTranscriptStatus()
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    def setEnableCheckSpeakerThreshold(self, *args, **kwargs) -> dict:
        self.startThreadingCheckSpeakerEnergy()
        config.ENABLE_CHECK_ENERGY_RECEIVE = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setDisableCheckSpeakerThreshold(self, *args, **kwargs) -> dict:
        self.stopThreadingCheckSpeakerEnergy()
        config.ENABLE_CHECK_ENERGY_RECEIVE = False
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setEnableCheckMicThreshold(self, *args, **kwargs) -> dict:
        self.startThreadingCheckMicEnergy()
        config.ENABLE_CHECK_ENERGY_SEND = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

    def setDisableCheckMicThreshold(self, *args, **kwargs) -> dict:
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
        self.startThreadingTranscriptionSendMessage()
        config.ENABLE_TRANSCRIPTION_SEND = True
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

    def setDisableTranscriptionSend(self, *args, **kwargs) -> dict:
        self.stopThreadingTranscriptionSendMessage()
        config.ENABLE_TRANSCRIPTION_SEND = False
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

    def setEnableTranscriptionReceive(self, *args, **kwargs) -> dict:
        self.startThreadingTranscriptionReceiveMessage()
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

    def setDisableTranscriptionReceive(self, *args, **kwargs) -> dict:
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
    def messageFormatter(format_type:str, translation:list, message:list) -> str:
        if format_type == "RECEIVED":
            FORMAT_WITH_T = config.RECEIVED_MESSAGE_FORMAT_WITH_T
            FORMAT = config.RECEIVED_MESSAGE_FORMAT
        elif format_type == "SEND":
            FORMAT_WITH_T = config.SEND_MESSAGE_FORMAT_WITH_T
            FORMAT = config.SEND_MESSAGE_FORMAT
        else:
            raise ValueError("format_type is not found", format_type)

        if len(translation) > 0:
            osc_message = FORMAT_WITH_T.replace("[message]", "\n".join(message))
            osc_message = osc_message.replace("[translation]", "\n".join(translation))
        else:
            osc_message = FORMAT.replace("[message]", "\n".join(message))
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
        model.startMicTranscript(self.micMessage)
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
        model.startSpeakerTranscript(self.speakerMessage)
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

    def initializationProgress(self, progress):
        self.run(200, self.run_mapping["initialization_progress"], progress)

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

        printLog("Update settings")
        self.updateConfigSettings()

        printLog("End Initialization")
        self.startWatchdog()