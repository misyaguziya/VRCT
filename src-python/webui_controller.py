from typing import Callable, Union, Any
from time import sleep
from subprocess import Popen
from threading import Thread
import re
from config import config
from model import model
from utils import isUniqueStrings, printLog
from models.transcription.transcription_utils import device_manager

class Controller:
    def __init__(self) -> None:
        self.run_mapping = {}
        self.run = None
        self.transcription_access_status = True

    def setRunMapping(self, run_mapping:dict) -> None:
        self.run_mapping = run_mapping

    def setRun(self, run:Callable[[int, str, Any], None]) -> None:
        self.run = run

    # response functions
    def downloadSoftwareProgressBar(self, progress) -> None:
        self.run(
            200,
            self.run_mapping["download_software"],
            progress,
        )

    def updateSoftwareProgressBar(self, progress) -> None:
        self.run(
            200,
            self.run_mapping["update_software"],
            progress,
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

    def restartAccessDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            printLog("Restart Access Devices", "Start Mic Transcript")
            self.startThreadingTranscriptionSendMessage()
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            printLog("Restart Access Devices", "Start Speaker Transcript")
            self.startThreadingTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            printLog("Restart Access Devices", "Start Check Mic Energy")
            model.startCheckMicEnergy(
                self.progressBarMicEnergy,
            )
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            printLog("Restart Access Devices", "Start Check Speaker Energy")
            model.startCheckSpeakerEnergy(
                self.progressBarSpeakerEnergy,
            )

    def stopAccessDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            model.stopMicTranscript()
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            model.stopSpeakerTranscript()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            model.stopCheckMicEnergy()
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            model.stopCheckSpeakerEnergy()

    def updateSelectedMicDevice(self, host, device) -> None:
        config.SELECTED_MIC_HOST = host
        config.SELECTED_MIC_DEVICE = device
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.startThreadingTranscriptionSendMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            model.startCheckMicEnergy(
                self.progressBarMicEnergy,
            )
        self.run(
            200,
            self.run_mapping["selected_mic_device"],
            {"host":host, "device":device},
        )

    def updateSelectedSpeakerDevice(self, device) -> None:
        config.SELECTED_SPEAKER_DEVICE = device
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.startThreadingTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            model.startCheckSpeakerEnergy(
                self.progressBarSpeakerEnergy,
            )
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
                {"message":"No mic device detected."},
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
                {"message":"No mic device detected."},
            )
        else:
            self.run(
                200,
                self.run_mapping["check_speaker_volume"],
                energy,
            )

    def downloadCTranslate2ProgressBar(self, progress) -> None:
        printLog("CTranslate2 Weight Download Progress", progress)
        self.run(
            200,
            self.run_mapping["download_ctranslate2"],
            progress,
        )

    def downloadWhisperProgressBar(self, progress) -> None:
        printLog("Whisper Weight Download Progress", progress)
        self.run(
            200,
            self.run_mapping["download_whisper"],
            progress,
        )

    def micMessage(self, message: Union[str, bool]) -> None:
        if isinstance(message, bool) and message is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {"message":"No mic device detected."},
            )

        elif isinstance(message, str) and len(message) > 0:
            translation = []
            transliteration = []
            if model.checkKeywords(message):
                self.run(
                    200,
                    self.run_mapping["word_filter"],
                    {"message":f"Detected by word filter:{message}"},
                )
                return
            elif model.detectRepeatSendMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                translation, success = model.getInputTranslate(message)
                if all(success) is not True:
                    self.changeToCTranslate2Process()
                    self.run(
                        400,
                        self.run_mapping["error_translation_engine"],
                        {"message":"translation engine limit error"},
                    )

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"] == "Japanese":
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

                # if config.OVERLAY_SMALL_LOG is True:
                #     overlay_image = model.createOverlayImageShort(message, translation)
                #     model.updateOverlay(overlay_image)
                #     overlay_image = model.createOverlayImageLong("send", message, translation)
                #     model.updateOverlay(overlay_image)

    def speakerMessage(self, message) -> None:
        if isinstance(message, bool) and message is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {"message":"No mic device detected."},
            )
        elif isinstance(message, str) and len(message) > 0:
            translation = []
            transliteration = []
            if model.detectRepeatReceiveMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                translation, success = model.getOutputTranslate(message)
                if all(success) is not True:
                    self.changeToCTranslate2Process()
                    self.run(
                        400,
                        self.run_mapping["error_translation_engine"],
                        {"message":"translation engine limit error"},
                    )

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"] == "Japanese":
                        transliteration = model.convertMessageToTransliteration(message)

            if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
                if config.OVERLAY_SMALL_LOG is True:
                    if model.overlay.initialized is True:
                        overlay_image = model.createOverlayImageShort(message, translation)
                        model.updateOverlay(overlay_image)
                    # overlay_image = model.createOverlayImageLong("receive", message, translation)
                    # model.updateOverlay(overlay_image)

                # ------------Speaker2Chatbox------------
                if config.ENABLE_SPEAKER2CHATBOX is True:
                    # send OSC message
                    if config.SEND_RECEIVED_MESSAGE_TO_VRC is True:
                        osc_message = self.messageFormatter("RECEIVED", translation, [message])
                        model.oscSendMessage(osc_message)
                # ------------Speaker2Chatbox------------

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
                        {"message":"translation engine limit error"},
                    )

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"] == "Japanese":
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

            # if config.OVERLAY_SMALL_LOG is True:
            #     overlay_image = model.createOverlayImageShort(message, translation)
            #     model.updateOverlay(overlay_image)
            #     overlay_image = model.createOverlayImageLong("send", message, translation)
            #     model.updateOverlay(overlay_image)

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

    @staticmethod
    def getTransparencyRange(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSPARENCY_RANGE}

    @staticmethod
    def getAppearanceThemesList(*args, **kwargs) -> dict:
        return {"status":200, "result":config.APPEARANCE_THEME_LIST}

    @staticmethod
    def getUiScalingList(*args, **kwargs) -> dict:
        return {"status":200, "result":config.UI_SCALING_LIST}

    @staticmethod
    def getTextboxUiScalingRange(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TEXTBOX_UI_SCALING_RANGE}

    @staticmethod
    def getMessageBoxRatioRange(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MESSAGE_BOX_RATIO_RANGE}

    @staticmethod
    def getSelectableCtranslate2WeightTypeDict(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT}

    @staticmethod
    def getSelectableWhisperModelTypeDict(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT}

    @staticmethod
    def getMaxMicThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MAX_MIC_THRESHOLD}

    @staticmethod
    def getMaxSpeakerThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MAX_SPEAKER_THRESHOLD}

    @staticmethod
    def setEnableTranslation(*args, **kwargs) -> dict:
        config.ENABLE_TRANSLATION = True
        if model.isLoadedCTranslate2Model() is False:
            model.changeTranslatorCTranslate2Model()
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
            config.MULTI_LANGUAGE_TRANSLATION,
            )
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
    def setSelectedTranslationEngines(engines:dict, *args, **kwargs) -> dict:
        printLog("setSelectedTranslationEngines", engines)
        config.SELECTED_TRANSLATION_ENGINES = engines
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
    def getSelectedTranscriptionEngine(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_ENGINE}

    @staticmethod
    def getMultiLanguageTranslation(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MULTI_LANGUAGE_TRANSLATION}

    @staticmethod
    def setEnableMultiLanguageTranslation(*args, **kwargs) -> dict:
        config.MULTI_LANGUAGE_TRANSLATION = True
        return {"status":200, "result":config.MULTI_LANGUAGE_TRANSLATION}

    @staticmethod
    def setDisableMultiLanguageTranslation(*args, **kwargs) -> dict:
        config.MULTI_LANGUAGE_TRANSLATION = False
        return {"status":200, "result":config.MULTI_LANGUAGE_TRANSLATION}

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
    def getAppearanceTheme(*args, **kwargs) -> dict:
        return {"status":200, "result":config.APPEARANCE_THEME}

    @staticmethod
    def setAppearanceTheme(data, *args, **kwargs) -> dict:
        config.APPEARANCE_THEME = data
        return {"status":200, "result":config.APPEARANCE_THEME}

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
        config.MESSAGE_BOX_RATIO = int(data)
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
    def getRestoreMainWindowGeometry(*args, **kwargs) -> dict:
        return {"status":200, "result":config.RESTORE_MAIN_WINDOW_GEOMETRY}

    @staticmethod
    def setEnableRestoreMainWindowGeometry(*args, **kwargs) -> dict:
        config.RESTORE_MAIN_WINDOW_GEOMETRY = True
        return {"status":200, "result":config.RESTORE_MAIN_WINDOW_GEOMETRY}

    @staticmethod
    def setDisableRestoreMainWindowGeometry(*args, **kwargs) -> dict:
        config.RESTORE_MAIN_WINDOW_GEOMETRY = False
        return {"status":200, "result":config.RESTORE_MAIN_WINDOW_GEOMETRY}

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
        device_manager.noticeUpdateDevices()
        device_manager.setMicDefaultDevice()
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
            model.stopCheckMicEnergy()
            model.startCheckMicEnergy(
                self.progressBarMicEnergy,
            )
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
            model.stopCheckMicEnergy()
            model.startCheckMicEnergy(
                self.progressBarMicEnergy,
            )
        return {"status":200, "result": config.SELECTED_MIC_DEVICE}

    @staticmethod
    def getMicThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_THRESHOLD}

    @staticmethod
    def setMicThreshold(data, *args, **kwargs) -> dict:
        status = 400
        data = int(data)
        if 0 <= data <= config.MAX_MIC_THRESHOLD:
            config.MIC_THRESHOLD = data
            status = 200
        return {"status": status, "result": config.MIC_THRESHOLD}

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
            response = {"status":400, "result":{"message":"Error Mic Record Timeout"}}
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
            response = {"status":400, "result":{"message":"Error Mic Phrase Timeout"}}
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
            response = {"status":400, "result":{"message":"Error Mic Max Phrases"}}
        else:
            response = {"status":200, "result":config.MIC_MAX_PHRASES}
        return response

    @staticmethod
    def getMicWordFilter(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_WORD_FILTER}

    @staticmethod
    def setMicWordFilter(data, *args, **kwargs) -> dict:
        data = str(data)
        data = [w.strip() for w in data.split(",") if len(w.strip()) > 0]
        # Copy the list
        new_mic_word_filter_list = config.MIC_WORD_FILTER
        new_added_value = []
        for value in data:
            if value in new_mic_word_filter_list:
                # If the value is already in the list, do nothing.
                pass
            else:
                new_mic_word_filter_list.append(value)
                new_added_value.append(value)
        config.MIC_WORD_FILTER = new_mic_word_filter_list

        model.resetKeywordProcessor()
        model.addKeywords()
        return {"status":200, "result":config.MIC_WORD_FILTER}

    @staticmethod
    def delMicWordFilter(data, *args, **kwargs) -> dict:
        try:
            new_mic_word_filter_list = config.MIC_WORD_FILTER
            new_mic_word_filter_list.remove(str(data))
            config.MIC_WORD_FILTER = new_mic_word_filter_list
            model.resetKeywordProcessor()
            model.addKeywords()
        except Exception:
            printLog("Delete Mic Word Filter", "There was no the target word in config.MIC_WORD_FILTER")
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
        device_manager.noticeUpdateDevices()
        device_manager.setSpeakerDefaultDevice()
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
            model.stopCheckSpeakerEnergy()
            model.startCheckSpeakerEnergy(
                self.progressBarSpeakerEnergy,
            )
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
            response = {"status":400, "result":{"message":"Error Set Speaker Energy Threshold"}}
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
            response = {"status":400, "result":{"message":"Error Speaker Record Timeout"}}
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
            response = {"status":400, "result":{"message":"Error Speaker Phrase Timeout"}}
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
            response = {"status":400, "result":{"message":"Error Speaker Max Phrases"}}
        else:
            response = {"status":200, "result":config.SPEAKER_MAX_PHRASES}
        return response

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
        return {"status":200, "result":config.OSC_IP_ADDRESS}

    @staticmethod
    def getOscPort(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OSC_PORT}

    @staticmethod
    def setOscPort(data, *args, **kwargs) -> dict:
        config.OSC_PORT = int(data)
        return {"status":200, "result":config.OSC_PORT}

    @staticmethod
    def getDeepLAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["DeepL_API"]}

    def setDeeplAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set DeepL Auth Key", data)
        status = 400
        if len(data) == 36 or len(data) == 39:
            result = model.authenticationTranslatorDeepLAuthKey(auth_key=data)
            if result is True:
                key = data
                status = 200
            else:
                key = None
            auth_keys = config.AUTH_KEYS
            auth_keys["DeepL_API"] = key
            config.AUTH_KEYS = auth_keys
            self.updateTranslationEngineAndEngineList()
        return {"status":status, "result":config.AUTH_KEYS["DeepL_API"]}

    def delDeeplAuthKey(self, *args, **kwargs) -> dict:
        auth_keys = config.AUTH_KEYS
        auth_keys["DeepL_API"] = None
        config.AUTH_KEYS = auth_keys
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS["DeepL_API"]}

    @staticmethod
    def getUseTranslationFeature(*args, **kwargs) -> dict:
        return {"status":200, "result":config.USE_TRANSLATION_FEATURE}

    @staticmethod
    def setEnableUseTranslationFeature(*args, **kwargs) -> dict:
        config.USE_TRANSLATION_FEATURE = True
        if model.checkCTranslatorCTranslate2ModelWeight():
            config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = False
            def callback():
                model.changeTranslatorCTranslate2Model()
            th_callback = Thread(target=callback)
            th_callback.daemon = True
            th_callback.start()
        else:
            config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = True
        return {"status":200,
                "result":{
                    "feature":config.USE_TRANSLATION_FEATURE,
                    "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION,
                    },
                }

    @staticmethod
    def setDisableUseTranslationFeature(*args, **kwargs) -> dict:
        config.USE_TRANSLATION_FEATURE = False
        config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = False
        return {"status":200,
                "result":{
                    "feature":config.USE_TRANSLATION_FEATURE,
                    "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION,
                    },
                }

    @staticmethod
    def getUseWhisperFeature(*args, **kwargs) -> dict:
        return {"status":200, "result":config.USE_WHISPER_FEATURE}

    @staticmethod
    def setEnableUseWhisperFeature(*args, **kwargs) -> dict:
        config.USE_WHISPER_FEATURE = True
        if model.checkTranscriptionWhisperModelWeight() is True:
            config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = False
            config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        else:
            config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = True
            config.SELECTED_TRANSCRIPTION_ENGINE = "Google"
        return {"status":200,
                "result":{
                    "feature":config.USE_WHISPER_FEATURE,
                    "transcription_engine":config.SELECTED_TRANSCRIPTION_ENGINE,
                    "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER,
                    },
                }

    @staticmethod
    def setDisableUseWhisperFeature(*args, **kwargs) -> dict:
        config.USE_WHISPER_FEATURE = False
        config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = False
        config.SELECTED_TRANSCRIPTION_ENGINE = "Google"
        return {"status":200,
                "result":{
                    "feature":config.USE_WHISPER_FEATURE,
                    "transcription_engine":config.SELECTED_TRANSCRIPTION_ENGINE,
                    "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER,
                    },
                }

    @staticmethod
    def getCtranslate2WeightType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CTRANSLATE2_WEIGHT_TYPE}

    @staticmethod
    def setCtranslate2WeightType(data, *args, **kwargs) -> dict:
        config.CTRANSLATE2_WEIGHT_TYPE = str(data)
        if model.checkCTranslatorCTranslate2ModelWeight():
            config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = False
            def callback():
                model.changeTranslatorCTranslate2Model()
            th_callback = Thread(target=callback)
            th_callback.daemon = True
            th_callback.start()
        else:
            config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = True
        return {"status":200,
                "result":{
                    "feature":config.CTRANSLATE2_WEIGHT_TYPE,
                    "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION,
                    },
                }

    @staticmethod
    def getWhisperWeightType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.WHISPER_WEIGHT_TYPE}

    @staticmethod
    def setWhisperWeightType(data, *args, **kwargs) -> dict:
        config.WHISPER_WEIGHT_TYPE = str(data)
        if model.checkTranscriptionWhisperModelWeight() is True:
            config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = False
            config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        else:
            config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = True
            config.SELECTED_TRANSCRIPTION_ENGINE = "Google"
        return {"status":200,
                "result":{
                    "weight_type":config.WHISPER_WEIGHT_TYPE,
                    "transcription_engine":config.SELECTED_TRANSCRIPTION_ENGINE,
                    "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER,
                }
            }

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
    def getOverlaySettings(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SETTINGS}

    @staticmethod
    def setOverlaySettings(data, *args, **kwargs) -> dict:
        config.OVERLAY_SETTINGS = data
        model.updateOverlayImageOpacity()
        model.updateOverlayImageUiScaling()
        return {"status":200, "result":config.OVERLAY_SETTINGS}

    @staticmethod
    def getOverlaySmallLogSettings(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS}

    @staticmethod
    def setOverlaySmallLogSettings(data, *args, **kwargs) -> dict:
        config.OVERLAY_SMALL_LOG_SETTINGS = data
        model.updateOverlayPosition()
        return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS}

    @staticmethod
    def getOverlaySmallLog(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setEnableOverlaySmallLog(*args, **kwargs) -> dict:
        config.OVERLAY_SMALL_LOG = True
        if config.OVERLAY_SMALL_LOG is True and config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            if model.overlay.initialized is False and model.overlay.checkSteamvrRunning() is True:
                model.startOverlay()
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setDisableOverlaySmallLog(*args, **kwargs) -> dict:
        config.OVERLAY_SMALL_LOG = False
        if config.OVERLAY_SMALL_LOG is False:
            model.clearOverlayImage()
            model.shutdownOverlay()
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

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
    def getSendMessageFormat(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_FORMAT}

    @staticmethod
    def setSendMessageFormat(data, *args, **kwargs) -> dict:
        if isUniqueStrings(["[message]"], data) is True:
            config.SEND_MESSAGE_FORMAT = data
        return {"status":200, "result":config.SEND_MESSAGE_FORMAT}

    @staticmethod
    def getSendMessageFormatWithT(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_FORMAT_WITH_T}

    @staticmethod
    def setSendMessageFormatWithT(data, *args, **kwargs) -> dict:
        if len(data) > 0:
            if isUniqueStrings(["[message]", "[translation]"], data) is True:
                config.SEND_MESSAGE_FORMAT_WITH_T = data
        return {"status":200, "result":config.SEND_MESSAGE_FORMAT_WITH_T}

    @staticmethod
    def getReceivedMessageFormat(*args, **kwargs) -> dict:
        return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT}

    @staticmethod
    def setReceivedMessageFormat(data, *args, **kwargs) -> dict:
        if isUniqueStrings(["[message]"], data) is True:
            config.RECEIVED_MESSAGE_FORMAT = data
        return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT}

    @staticmethod
    def getReceivedMessageFormatWithT(*args, **kwargs) -> dict:
        return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_WITH_T}

    @staticmethod
    def setReceivedMessageFormatWithT(data, *args, **kwargs) -> dict:
        if len(data) > 0:
            if isUniqueStrings(["[message]", "[translation]"], data) is True:
                config.RECEIVED_MESSAGE_FORMAT_WITH_T = data
        return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_WITH_T}

    @staticmethod
    def getSpeaker2ChatboxPass(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER2CHATBOX_PASS}

    @staticmethod
    def setSpeaker2ChatboxPass(data, *args, **kwargs) -> dict:
        config.SPEAKER2CHATBOX_PASS = data
        return {"status":200, "result":config.SPEAKER2CHATBOX_PASS}

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
        model.startCheckMuteSelfStatus()
        model.changeMicTranscriptStatus()
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    @staticmethod
    def setDisableVrcMicMuteSync(*args, **kwargs) -> dict:
        config.VRC_MIC_MUTE_SYNC = False
        model.stopCheckMuteSelfStatus()
        model.changeMicTranscriptStatus()
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    def setEnableCheckSpeakerThreshold(self, *args, **kwargs) -> dict:
        model.startCheckSpeakerEnergy(
            self.progressBarSpeakerEnergy,
        )
        config.ENABLE_CHECK_ENERGY_RECEIVE = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    @staticmethod
    def setDisableCheckSpeakerThreshold(*args, **kwargs) -> dict:
        model.stopCheckSpeakerEnergy()
        config.ENABLE_CHECK_ENERGY_RECEIVE = False
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setEnableCheckMicThreshold(self, *args, **kwargs) -> dict:
        model.startCheckMicEnergy(
            self.progressBarMicEnergy,
        )
        config.ENABLE_CHECK_ENERGY_SEND = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

    @staticmethod
    def setDisableCheckMicThreshold(*args, **kwargs) -> dict:
        model.stopCheckMicEnergy()
        config.ENABLE_CHECK_ENERGY_SEND = False
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

    # def updateSoftware(*args, **kwargs) -> dict:
    #     printLog("Update callbackUpdateSoftware")
    #     model.updateSoftware(restart=True, download=self.downloadSoftwareProgressBar, update=self.updateSoftwareProgressBar)
    #     return {"status":200, "result":True}

    # def restartSoftware(*args, **kwargs) -> dict:
    #     printLog("Restart callbackRestartSoftware")
    #     model.reStartSoftware()
    #     return {"status":200, "result":True}

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
        if config.OVERLAY_SMALL_LOG is True:
            if model.overlay.initialized is False and model.overlay.checkSteamvrRunning() is True:
                model.startOverlay()
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

    def swapYourLanguageAndTargetLanguage(self, *args, **kwargs) -> dict:
        your_languages = config.SELECTED_YOUR_LANGUAGES
        your_language_primary = your_languages[config.SELECTED_TAB_NO]["primary"]

        target_languages = config.SELECTED_TARGET_LANGUAGES
        target_language_primary = target_languages[config.SELECTED_TAB_NO]["primary"]

        your_languages[config.SELECTED_TAB_NO]["primary"] = target_language_primary
        target_languages[config.SELECTED_TAB_NO]["primary"] = your_language_primary

        self.setSelectedYourLanguages(your_languages)
        self.setSelectedTargetLanguages(target_languages)
        return {
            "status":200,
            "result":{
                "your":config.SELECTED_YOUR_LANGUAGES,
                "target":config.SELECTED_TARGET_LANGUAGES,
                }
            }

    def downloadCtranslate2Weight(self, *args, **kwargs) -> dict:
        self.startThreadingDownloadCtranslate2Weight(self.downloadCTranslate2ProgressBar)
        return {"status":200}

    def downloadWhisperWeight(self, *args, **kwargs) -> dict:
        self.startThreadingDownloadWhisperWeight(self.downloadWhisperProgressBar)
        return {"status":200}

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
            osc_message = FORMAT_WITH_T.replace("[message]", "/".join(message))
            osc_message = osc_message.replace("[translation]", "/".join(translation))
        else:
            osc_message = FORMAT.replace("[message]", "/".join(message))
        return osc_message

    def changeToCTranslate2Process(self) -> None:
        config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO] = "CTranslate2"
        self.run(200, self.run_mapping["translation_engines"], "CTranslate2")

    def startTranscriptionSendMessage(self) -> None:
        while self.transcription_access_status is False:
            sleep(1)
        self.transcription_access_status = False
        model.startMicTranscript(self.micMessage)
        self.transcription_access_status = True

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
        while self.transcription_access_status is False:
            sleep(1)
        self.transcription_access_status = False
        model.startSpeakerTranscript(self.speakerMessage)
        self.transcription_access_status = True

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

    def updateTranslationEngineAndEngineList(self):
        engine = config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO]
        engines = self.getTranslationEngines()["result"]
        if engine not in engines:
            engine = "CTranslate2"
        config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO] = engine
        self.run(200, self.run_mapping["selected_translation_engines"], config.SELECTED_TRANSLATION_ENGINES)
        self.run(200, self.run_mapping["translation_engines"], engines)

    @staticmethod
    def startThreadingDownloadCtranslate2Weight(callback:Callable[[float], None]) -> None:
        th_download = Thread(target=model.downloadCTranslate2ModelWeight, args=(callback,))
        th_download.daemon = True
        th_download.start()

    @staticmethod
    def startThreadingDownloadWhisperWeight(callback:Callable[[float], None]) -> None:
        th_download = Thread(target=model.downloadWhisperModelWeight, args=(callback,))
        th_download.daemon = True
        th_download.start()

    def init(self, *args, **kwargs) -> None:
        printLog("Start Initialization")

        printLog("Start check DeepL API Key")
        if config.AUTH_KEYS["DeepL_API"] is not None:
            if model.authenticationTranslatorDeepLAuthKey(auth_key=config.AUTH_KEYS["DeepL_API"]) is False:
                # error update Auth key
                auth_keys = config.AUTH_KEYS
                auth_keys["DeepL_API"] = None
                config.AUTH_KEYS = auth_keys

        # set Translation Engine
        printLog("Set Translation Engine")
        self.updateTranslationEngineAndEngineList()

        # check Downloaded CTranslate2 Model Weight
        printLog("Check Downloaded CTranslate2 Model Weight")
        if config.USE_TRANSLATION_FEATURE is True and model.checkCTranslatorCTranslate2ModelWeight() is False:
            self.startThreadingDownloadCtranslate2Weight(self.downloadCTranslate2ProgressBar)

        # set Transcription Engine
        printLog("Set Transcription Engine")
        if config.USE_WHISPER_FEATURE is True:
            config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        else:
            config.SELECTED_TRANSCRIPTION_ENGINE = "Google"

        # check Downloaded Whisper Model Weight
        printLog("Check Downloaded Whisper Model Weight")
        if config.USE_WHISPER_FEATURE is True and model.checkTranscriptionWhisperModelWeight() is False:
            self.startThreadingDownloadWhisperWeight(self.downloadWhisperProgressBar)

        # set word filter
        printLog("Set Word Filter")
        model.addKeywords()

        # check Software Updated
        printLog("Check Software Updated")
        if model.checkSoftwareUpdated() is True:
            pass

        # init logger
        printLog("Init Logger")
        if config.LOGGER_FEATURE is True:
            model.startLogger()

        # init OSC receive
        printLog("Init OSC Receive")
        model.startReceiveOSC()
        if config.VRC_MIC_MUTE_SYNC is True:
            model.startCheckMuteSelfStatus()

        # init Auto device selection
        printLog("Init Auto Device Selection")
        if config.AUTO_MIC_SELECT is True:
            self.setEnableAutoMicSelect()

        if config.AUTO_SPEAKER_SELECT is True:
            self.setEnableAutoSpeakerSelect()

        device_manager.setCallbackHostList(self.updateMicHostList)
        device_manager.setCallbackMicDeviceList(self.updateMicDeviceList)
        device_manager.setCallbackSpeakerDeviceList(self.updateSpeakerDeviceList)

        printLog("End Initialization")