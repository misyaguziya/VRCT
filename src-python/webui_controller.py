from typing import Callable, Union
from time import sleep
from subprocess import Popen
from threading import Thread
import re
from config import config
from model import model
from utils import isUniqueStrings, printLog
from models.transcription.transcription_utils import device_manager

# response functions
class DownloadSoftwareProgressBar:
    def __init__(self, action):
        self.action = action

    def set(self, progress) -> None:
        printLog("Software Download Progress", progress)
        self.action("download", {
            "status":200,
            "result":{
                "progress":progress
                }
            })

class UpdateSoftwareProgressBar:
    def __init__(self, action):
        self.action = action

    def set(self, progress) -> None:
        printLog("Software Update Progress", progress)
        self.action("update", {
            "status":200,
            "result":{
                "progress":progress
                }
            })

class UpdateSelectedMicDevice:
    def __init__(self, action):
        self.action = action

    def set(self, host, device) -> None:
        config.SELECTED_MIC_HOST = host
        config.SELECTED_MIC_DEVICE = device
        printLog("Update Host/Mic Device", f"{host}/{device}")
        self.action("mic", {
            "status":200,
            "result":{"host":host, "device":device}
            })

class UpdateSelectedSpeakerDevice:
    def __init__(self, action):
        self.action = action

    def set(self, device) -> None:
        config.SELECTED_SPEAKER_DEVICE = device
        printLog("Update Speaker Device", device)
        self.action("speaker", {
            "status":200,
            "result":device
            })

class ProgressBarMicEnergy:
    def __init__(self, action):
        self.action = action

    def set(self, energy) -> None:
        if energy is False:
            self.action("error_device", {"status":400,"result": {"message":"No mic device detected."}})
        else:
            self.action("mic", {"status":200, "result":energy})

class ProgressBarSpeakerEnergy:
    def __init__(self, action):
        self.action = action

    def set(self, energy) -> None:
        if energy is False:
            self.action("error_device", {"status":400,"result": {"message":"No mic device detected."}})
        else:
            self.action("speaker", {"status":200, "result":energy})

class DownloadWhisperProgressBar:
    def __init__(self, action):
        self.action = action

    def set(self, progress) -> None:
        printLog("Whisper Weight Download Progress", progress)
        self.action("download", {
            "status":200,
            "result":{
                "progress":progress
                }
            })

class MicMessage:
    def __init__(self, action:Callable[[dict], None]) -> None:
        self.action = action

    def send(self, message: Union[str, bool]) -> None:
        if isinstance(message, bool) and message is False:
            self.action("error_device", {
                "status":400,
                "result": {
                    "message":"No mic device detected."
                    }
                })
        elif isinstance(message, str) and len(message) > 0:
            # addSentMessageLog(message)
            translation = []
            transliteration = []
            if model.checkKeywords(message):
                self.action("word_filter", {
                    "status":200,
                    "result": {
                        "message":f"Detected by word filter:{message}"
                        }
                    })
                return
            elif model.detectRepeatSendMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                translation, success = model.getInputTranslate(message)
                if all(success) is not True:
                    changeToCTranslate2Process()
                    self.action("error_translation_engine", {
                        "status":400,
                        "result": {
                            "message":"translation engine limit error"
                            }
                        })

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"] == "Japanese":
                        transliteration = model.convertMessageToTransliteration(translation[0])

            if config.ENABLE_TRANSCRIPTION_SEND is True:
                if config.SEND_MESSAGE_TO_VRC is True:
                    if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                        if config.ENABLE_TRANSLATION is False:
                            osc_message = messageFormatter("SEND", "", [message])
                        else:
                            osc_message = messageFormatter("SEND", "", translation)
                    else:
                        osc_message = messageFormatter("SEND", translation, [message])
                    model.oscSendMessage(osc_message)

                self.action("mic", {
                    "status":200,
                    "result": {
                        "message":message,
                        "translation":translation,
                        "transliteration":transliteration
                        }
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

class SpeakerMessage:
    def __init__(self, action:Callable[[dict], None]) -> None:
        self.action = action

    def receive(self, message):
        if isinstance(message, bool) and message is False:
            self.action("error_device",{
                "status":400,
                "result": {
                    "message":"No mic device detected."
                    },
                })
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
                    changeToCTranslate2Process()
                    self.action("error_translation_engine", {
                        "status":400,
                        "result": {
                            "message":"translation engine limit error"
                            }
                        })

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
                        osc_message = messageFormatter("RECEIVED", translation, [message])
                        model.oscSendMessage(osc_message)
                # ------------Speaker2Chatbox------------

                # update textbox message log (Received)
                self.action("speaker",{
                    "status":200,
                    "result": {
                        "message":message,
                        "translation":translation,
                        "transliteration":transliteration,
                        }
                    })
                if config.LOGGER_FEATURE is True:
                    if len(translation) > 0:
                        translation = " (" + "/".join(translation) + ")"
                    model.logger.info(f"[RECEIVED] {message}{translation}")

class ChatMessage:
    def __init__(self, action:Callable[[dict], None]) -> None:
        self.action = action

    def send(self, data):
        id = data["id"]
        message = data["message"]
        if len(message) > 0:
            # addSentMessageLog(message)
            translation = []
            transliteration = []
            if config.ENABLE_TRANSLATION is False:
                pass
            else:
                if config.USE_EXCLUDE_WORDS is True:
                    replacement_message, replacement_dict = replaceExclamationsWithRandom(message)
                    translation, success = model.getInputTranslate(replacement_message)

                    message = removeExclamations(message)
                    for i in range(len(translation)):
                        translation[i] = restoreText(translation[i], replacement_dict)
                else:
                    translation, success = model.getInputTranslate(message)

                if all(success) is not True:
                    changeToCTranslate2Process()
                    self.action("error_translation_engine", {
                        "status":400,
                        "result":{
                            "message":"translation engine limit error"
                            }
                        })

                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"] == "Japanese":
                        transliteration = model.convertMessageToTransliteration(translation[0])

            # send OSC message
            if config.SEND_MESSAGE_TO_VRC is True:
                if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                    if config.ENABLE_TRANSLATION is False:
                        osc_message = messageFormatter("SEND", "", [message])
                    else:
                        osc_message = messageFormatter("SEND", "", translation)
                else:
                    osc_message = messageFormatter("SEND", translation, [message])
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

class DownloadCTranslate2ProgressBar:
    def __init__(self, action):
        self.action = action

    def set(self, progress) -> None:
        printLog("CTranslate2 Weight Download Progress", progress)
        self.action("download", {
            "status":200,
            "result":{
                "progress":progress
                }
            })

# getter/setter functions

def getVersion(*args, **kwargs) -> dict:
    return {"status":200, "result":config.VERSION}

def getTransparencyRange(*args, **kwargs) -> dict:
    return {"status":200, "result":config.TRANSPARENCY_RANGE}

def getAppearanceThemesList(*args, **kwargs) -> dict:
    return {"status":200, "result":config.APPEARANCE_THEME_LIST}

def getUiScalingList(*args, **kwargs) -> dict:
    return {"status":200, "result":config.UI_SCALING_LIST}

def getTextboxUiScalingRange(*args, **kwargs) -> dict:
    return {"status":200, "result":config.TEXTBOX_UI_SCALING_RANGE}

def getMessageBoxRatioRange(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MESSAGE_BOX_RATIO_RANGE}

def getSelectableCtranslate2WeightTypeDict(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT}

def getSelectableWhisperModelTypeDict(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT}

def getMaxMicEnergyThreshold(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MAX_MIC_THRESHOLD}

def getMaxSpeakerEnergyThreshold(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MAX_SPEAKER_ENERGY_THRESHOLD}

def setEnableTranslation(*args, **kwargs) -> dict:
    config.ENABLE_TRANSLATION = True
    if model.isLoadedCTranslate2Model() is False:
        model.changeTranslatorCTranslate2Model()
    return {"status":200, "result":config.ENABLE_TRANSLATION}

def setDisableTranslation(*args, **kwargs) -> dict:
    config.ENABLE_TRANSLATION = False
    return {"status":200, "result":config.ENABLE_TRANSLATION}

def setEnableForeground(*args, **kwargs) -> dict:
    config.ENABLE_FOREGROUND = True
    return {"status":200, "result":config.ENABLE_FOREGROUND}

def setDisableForeground(*args, **kwargs) -> dict:
    config.ENABLE_FOREGROUND = False
    return {"status":200, "result":config.ENABLE_FOREGROUND}

def setEnableConfigWindow(*args, **kwargs) -> dict:
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        stopThreadingTranscriptionSendMessageOnOpenConfigWindow()
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        stopThreadingTranscriptionReceiveMessageOnOpenConfigWindow()
    return {"status":200, "result":True}

def setDisableConfigWindow(data, action, *args, **kwargs) -> dict:
    model.stopCheckMicEnergy()
    model.stopCheckSpeakerEnergy()

    if config.ENABLE_TRANSCRIPTION_SEND is True:
        startThreadingTranscriptionSendMessageOnCloseConfigWindow(action)
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            sleep(2)
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        startThreadingTranscriptionReceiveMessageOnCloseConfigWindow(action)
    return {"status":200, "result":True}

def getSelectedTabNo(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTED_TAB_NO}

def setSelectedTabNo(selected_tab_no:str, *args, **kwargs) -> dict:
    printLog("setSelectedTabNo", selected_tab_no)
    config.SELECTED_TAB_NO = selected_tab_no
    updateTranslationEngineAndEngineList()
    return {"status":200, "result":config.SELECTED_TAB_NO}

def getTranslationEngines(*args, **kwargs) -> dict:
    engines = model.findTranslationEngines(
        config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
        config.MULTI_LANGUAGE_TRANSLATION,
        )
    return {"status":200, "result":engines}

def getListLanguageAndCountry(*args, **kwargs) -> dict:
    return {"status":200, "result": model.getListLanguageAndCountry()}

def getMicHostList(*args, **kwargs) -> dict:
    return {"status":200, "result": model.getListInputHost()}

def getMicDeviceList(*args, **kwargs) -> dict:
    return {"status":200, "result": model.getListInputDevice()}

def getSpeakerDeviceList(*args, **kwargs) -> dict:
    return {"status":200, "result": model.getListOutputDevice()}

def getSelectedTranslationEngines(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTED_TRANSLATION_ENGINES}

def setSelectedTranslatorEngines(engines:dict, *args, **kwargs) -> dict:
    printLog("setSelectedTranslatorEngines", engines)
    config.SELECTED_TRANSLATION_ENGINES = engines
    return {"status":200,"result":config.SELECTED_TRANSLATION_ENGINES}

def getSelectedYourLanguages(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTED_YOUR_LANGUAGES}

def setSelectedYourLanguages(select:dict, *args, **kwargs) -> dict:
    config.SELECTED_YOUR_LANGUAGES = select
    updateTranslationEngineAndEngineList()
    return {"status":200, "result":config.SELECTED_YOUR_LANGUAGES}

def getSelectedTargetLanguages(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTED_TARGET_LANGUAGES}

def setSelectedTargetLanguages(select:dict, *args, **kwargs) -> dict:
    config.SELECTED_TARGET_LANGUAGES = select
    updateTranslationEngineAndEngineList()
    return {"status":200, "result":config.SELECTED_TARGET_LANGUAGES}

def getSelectedTranscriptionEngine(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTED_TRANSCRIPTION_ENGINE}

def getMultiLanguageTranslation(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MULTI_LANGUAGE_TRANSLATION}

def setEnableMultiLanguageTranslation(*args, **kwargs) -> dict:
    config.MULTI_LANGUAGE_TRANSLATION = True
    return {"status":200, "result":config.MULTI_LANGUAGE_TRANSLATION}

def setDisableMultiLanguageTranslation(*args, **kwargs) -> dict:
    config.MULTI_LANGUAGE_TRANSLATION = False
    return {"status":200, "result":config.MULTI_LANGUAGE_TRANSLATION}

def getConvertMessageToRomaji(*args, **kwargs) -> dict:
    return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

def setEnableConvertMessageToRomaji(*args, **kwargs) -> dict:
    config.CONVERT_MESSAGE_TO_ROMAJI = True
    return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

def setDisableConvertMessageToRomaji(*args, **kwargs) -> dict:
    config.CONVERT_MESSAGE_TO_ROMAJI = False
    return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

def getConvertMessageToHiragana(*args, **kwargs) -> dict:
    return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

def setEnableConvertMessageToHiragana(*args, **kwargs) -> dict:
    config.CONVERT_MESSAGE_TO_HIRAGANA = True
    return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

def setDisableConvertMessageToHiragana(*args, **kwargs) -> dict:
    config.CONVERT_MESSAGE_TO_HIRAGANA = False
    return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

def getMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

def setEnableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
    config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
    return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

def setDisableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
    config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
    return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

def getTransparency(*args, **kwargs) -> dict:
    return {"status":200, "result":config.TRANSPARENCY}

def setTransparency(data, *args, **kwargs) -> dict:
    config.TRANSPARENCY = int(data)
    return {"status":200, "result":config.TRANSPARENCY}

def getAppearanceTheme(*args, **kwargs) -> dict:
    return {"status":200, "result":config.APPEARANCE_THEME}

def setAppearanceTheme(data, *args, **kwargs) -> dict:
    config.APPEARANCE_THEME = data
    return {"status":200, "result":config.APPEARANCE_THEME}

def getUiScaling(*args, **kwargs) -> dict:
    return {"status":200, "result":config.UI_SCALING}

def setUiScaling(data, *args, **kwargs) -> dict:
    config.UI_SCALING = data
    return {"status":200, "result":config.UI_SCALING}

def getTextboxUiScaling(*args, **kwargs) -> dict:
    return {"status":200, "result":config.TEXTBOX_UI_SCALING}

def setTextboxUiScaling(data, *args, **kwargs) -> dict:
    config.TEXTBOX_UI_SCALING = int(data)
    return {"status":200, "result":config.TEXTBOX_UI_SCALING}

def getMessageBoxRatio(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MESSAGE_BOX_RATIO}

def setMessageBoxRatio(data, *args, **kwargs) -> dict:
    config.MESSAGE_BOX_RATIO = int(data)
    return {"status":200, "result":config.MESSAGE_BOX_RATIO}

def getFontFamily(*args, **kwargs) -> dict:
    return {"status":200, "result":config.FONT_FAMILY}

def setFontFamily(data, *args, **kwargs) -> dict:
    config.FONT_FAMILY = data
    return {"status":200, "result":config.FONT_FAMILY}

def getUiLanguage(*args, **kwargs) -> dict:
    return {"status":200, "result":config.UI_LANGUAGE}

def setUiLanguage(data, *args, **kwargs) -> dict:
    config.UI_LANGUAGE = data
    return {"status":200, "result":config.UI_LANGUAGE}

def getRestoreMainWindowGeometry(*args, **kwargs) -> dict:
    return {"status":200, "result":config.RESTORE_MAIN_WINDOW_GEOMETRY}

def setEnableRestoreMainWindowGeometry(*args, **kwargs) -> dict:
    config.RESTORE_MAIN_WINDOW_GEOMETRY = True
    return {"status":200, "result":config.RESTORE_MAIN_WINDOW_GEOMETRY}

def setDisableRestoreMainWindowGeometry(*args, **kwargs) -> dict:
    config.RESTORE_MAIN_WINDOW_GEOMETRY = False
    return {"status":200, "result":config.RESTORE_MAIN_WINDOW_GEOMETRY}

def getMainWindowGeometry(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MAIN_WINDOW_GEOMETRY}

def setMainWindowGeometry(data, *args, **kwargs) -> dict:
    config.MAIN_WINDOW_GEOMETRY = data
    return {"status":200, "result":config.MAIN_WINDOW_GEOMETRY}

def getAutoMicSelect(*args, **kwargs) -> dict:
    return {"status":200, "result":config.AUTO_MIC_SELECT}

def setEnableAutoMicSelect(data, action, *args, **kwargs) -> dict:
    config.AUTO_MIC_SELECT = True
    update_device = UpdateSelectedMicDevice(action)
    device_manager.setCallbackDefaultInputDevice(update_device.set)
    device_manager.noticeDefaultDevice()
    return {"status":200, "result":config.AUTO_MIC_SELECT}

def setDisableAutoMicSelect(*args, **kwargs) -> dict:
    device_manager.clearCallbackDefaultInputDevice()
    config.AUTO_MIC_SELECT = False
    return {"status":200, "result":config.AUTO_MIC_SELECT}

def getSelectedMicHost(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTED_MIC_HOST}

def setSelectedMicHost(data, *args, **kwargs) -> dict:
    config.SELECTED_MIC_HOST = data
    config.SELECTED_MIC_DEVICE = model.getInputDefaultDevice()
    if config.ENABLE_CHECK_ENERGY_SEND is True:
        model.stopCheckMicEnergy()
        model.startCheckMicEnergy()
    return {"status":200,
            "result":{
                "host":config.SELECTED_MIC_HOST,
                "device":config.SELECTED_MIC_DEVICE,
                },
            }

def getSelectedMicDevice(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTED_MIC_DEVICE}

def setSelectedMicDevice(data, *args, **kwargs) -> dict:
    config.SELECTED_MIC_DEVICE = data
    if config.ENABLE_CHECK_ENERGY_SEND is True:
        model.stopCheckMicEnergy()
        model.startCheckMicEnergy()
    return {"status":200, "result": config.SELECTED_MIC_DEVICE}

def getMicThreshold(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MIC_THRESHOLD}

def setMicThreshold(data, *args, **kwargs) -> dict:
    status = 400
    data = int(data)
    if 0 <= data <= config.MAX_MIC_THRESHOLD:
        config.MIC_THRESHOLD = data
        status = 200
    return {"status": status, "result": config.MIC_THRESHOLD}

def getMicAutomaticThreshold(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

def setEnableMicAutomaticThreshold(*args, **kwargs) -> dict:
    config.MIC_AUTOMATIC_THRESHOLD = True
    return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

def setDisableMicAutomaticThreshold(*args, **kwargs) -> dict:
    config.MIC_AUTOMATIC_THRESHOLD = False
    return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

def getMicRecordTimeout(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MIC_RECORD_TIMEOUT}

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

def getMicPhraseTimeout(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MIC_PHRASE_TIMEOUT}

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

def getMicMaxPhrases(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MIC_MAX_PHRASES}

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

def getMicWordFilter(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MIC_WORD_FILTER}

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

def getMicAvgLogprob(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MIC_AVG_LOGPROB}

def setMicAvgLogprob(data, *args, **kwargs) -> dict:
    config.MIC_AVG_LOGPROB = float(data)
    return {"status":200, "result":config.MIC_AVG_LOGPROB}

def getMicNoSpeechProb(*args, **kwargs) -> dict:
    return {"status":200, "result":config.MIC_NO_SPEECH_PROB}

def setMicNoSpeechProb(data, *args, **kwargs) -> dict:
    config.MIC_NO_SPEECH_PROB = float(data)
    return {"status":200, "result":config.MIC_NO_SPEECH_PROB}

def getAutoSpeakerSelect(*args, **kwargs) -> dict:
    return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

def setEnableAutoSpeakerSelect(data, action, *args, **kwargs) -> dict:
    config.AUTO_SPEAKER_SELECT = True
    update_device = UpdateSelectedSpeakerDevice(action)
    device_manager.setCallbackDefaultOutputDevice(update_device.set)
    device_manager.noticeDefaultDevice()
    return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

def setDisableAutoSpeakerSelect(*args, **kwargs) -> dict:
    device_manager.clearCallbackDefaultInputDevice()
    config.AUTO_SPEAKER_SELECT = False
    return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

def getSelectedSpeakerDevice(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SELECTED_SPEAKER_DEVICE}

def setSelectedSpeakerDevice(data, *args, **kwargs) -> dict:
    config.SELECTED_SPEAKER_DEVICE = data
    if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
        model.stopCheckSpeakerEnergy()
        model.startCheckSpeakerEnergy()
    return {"status":200, "result":config.SELECTED_SPEAKER_DEVICE}

def getSpeakerEnergyThreshold(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SPEAKER_ENERGY_THRESHOLD}

def setSpeakerEnergyThreshold(data, *args, **kwargs) -> dict:
    printLog("Set Speaker Energy Threshold", data)
    try:
        data = int(data)
        if 0 <= data <= config.MAX_SPEAKER_ENERGY_THRESHOLD:
            config.SPEAKER_ENERGY_THRESHOLD = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":400, "result":{"message":"Error Set Speaker Energy Threshold"}}
    else:
        response = {"status":200, "result":config.SPEAKER_ENERGY_THRESHOLD}
    return response

def getSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

def setEnableSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
    config.SPEAKER_AUTOMATIC_THRESHOLD = True
    return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

def setDisableSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
    config.SPEAKER_AUTOMATIC_THRESHOLD = False
    return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

def getSpeakerRecordTimeout(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SPEAKER_RECORD_TIMEOUT}

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

def getSpeakerPhraseTimeout(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SPEAKER_PHRASE_TIMEOUT}

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

def getSpeakerMaxPhrases(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SPEAKER_MAX_PHRASES}

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

def getSpeakerAvgLogprob(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SPEAKER_AVG_LOGPROB}

def setSpeakerAvgLogprob(data, *args, **kwargs) -> dict:
    config.SPEAKER_AVG_LOGPROB = float(data)
    return {"status":200, "result":config.SPEAKER_AVG_LOGPROB}

def getSpeakerNoSpeechProb(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SPEAKER_NO_SPEECH_PROB}

def setSpeakerNoSpeechProb(data, *args, **kwargs) -> dict:
    config.SPEAKER_NO_SPEECH_PROB = float(data)
    return {"status":200, "result":config.SPEAKER_NO_SPEECH_PROB}

def getOscIpAddress(*args, **kwargs) -> dict:
    return {"status":200, "result":config.OSC_IP_ADDRESS}

def setOscIpAddress(data, *args, **kwargs) -> dict:
    config.OSC_IP_ADDRESS = data
    return {"status":200, "result":config.OSC_IP_ADDRESS}

def getOscPort(*args, **kwargs) -> dict:
    return {"status":200, "result":config.OSC_PORT}

def setOscPort(data, *args, **kwargs) -> dict:
    config.OSC_PORT = int(data)
    return {"status":200, "result":config.OSC_PORT}

def getDeepLAuthKey(*args, **kwargs) -> dict:
    return {"status":200, "result":config.AUTH_KEYS["DeepL_API"]}

def setDeeplAuthKey(data, *args, **kwargs) -> dict:
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
        updateTranslationEngineAndEngineList()
    return {"status":status, "result":config.AUTH_KEYS["DeepL_API"]}

def delDeeplAuthKey(*args, **kwargs) -> dict:
    auth_keys = config.AUTH_KEYS
    auth_keys["DeepL_API"] = None
    config.AUTH_KEYS = auth_keys
    updateTranslationEngineAndEngineList()
    return {"status":200, "result":config.AUTH_KEYS["DeepL_API"]}

def getUseTranslationFeature(*args, **kwargs) -> dict:
    return {"status":200, "result":config.USE_TRANSLATION_FEATURE}

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

def setDisableUseTranslationFeature(*args, **kwargs) -> dict:
    config.USE_TRANSLATION_FEATURE = False
    config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = False
    return {"status":200,
            "result":{
                "feature":config.USE_TRANSLATION_FEATURE,
                "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION,
                },
            }

def getUseWhisperFeature(*args, **kwargs) -> dict:
    return {"status":200, "result":config.USE_WHISPER_FEATURE}

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

def getCtranslate2WeightType(*args, **kwargs) -> dict:
    return {"status":200, "result":config.CTRANSLATE2_WEIGHT_TYPE}

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

def getWhisperWeightType(*args, **kwargs) -> dict:
    return {"status":200, "result":config.WHISPER_WEIGHT_TYPE}

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

def getAutoClearMessageBox(*args, **kwargs) -> dict:
    return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

def setEnableAutoClearMessageBox(*args, **kwargs) -> dict:
    config.AUTO_CLEAR_MESSAGE_BOX = True
    return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

def setDisableAutoClearMessageBox(*args, **kwargs) -> dict:
    config.AUTO_CLEAR_MESSAGE_BOX = False
    return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

def getSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

def setEnableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
    config.SEND_ONLY_TRANSLATED_MESSAGES = True
    return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

def setDisableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
    config.SEND_ONLY_TRANSLATED_MESSAGES = False
    return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

def getSendMessageButtonType(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}

def setSendMessageButtonType(data, *args, **kwargs) -> dict:
    config.SEND_MESSAGE_BUTTON_TYPE = data
    return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}

def getOverlaySettings(*args, **kwargs) -> dict:
    return {"status":200, "result":config.OVERLAY_SETTINGS}

def setOverlaySettings(data, *args, **kwargs) -> dict:
    config.OVERLAY_SETTINGS = data
    model.updateOverlayImageOpacity()
    model.updateOverlayImageUiScaling()
    return {"status":200, "result":config.OVERLAY_SETTINGS}

def getOverlaySmallLogSettings(*args, **kwargs) -> dict:
    return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS}

def setOverlaySmallLogSettings(data, *args, **kwargs) -> dict:
    config.OVERLAY_SMALL_LOG_SETTINGS = data
    model.updateOverlayPosition()
    return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS}

def getOverlaySmallLog(*args, **kwargs) -> dict:
    return {"status":200, "result":config.OVERLAY_SMALL_LOG}

def setEnableOverlaySmallLog(*args, **kwargs) -> dict:
    config.OVERLAY_SMALL_LOG = True
    if config.OVERLAY_SMALL_LOG is True and config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        if model.overlay.initialized is False and model.overlay.checkSteamvrRunning() is True:
            model.startOverlay()
    return {"status":200, "result":config.OVERLAY_SMALL_LOG}

def setDisableOverlaySmallLog(*args, **kwargs) -> dict:
    config.OVERLAY_SMALL_LOG = False
    if config.OVERLAY_SMALL_LOG is False:
        model.clearOverlayImage()
        model.shutdownOverlay()
    return {"status":200, "result":config.OVERLAY_SMALL_LOG}

def getSendMessageToVrc(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

def setEnableSendMessageToVrc(*args, **kwargs) -> dict:
    config.SEND_MESSAGE_TO_VRC = True
    return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

def setDisableSendMessageToVrc(*args, **kwargs) -> dict:
    config.SEND_MESSAGE_TO_VRC = False
    return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

def getSendMessageFormat(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SEND_MESSAGE_FORMAT}

def setSendMessageFormat(data, *args, **kwargs) -> dict:
    if isUniqueStrings(["[message]"], data) is True:
        config.SEND_MESSAGE_FORMAT = data
    return {"status":200, "result":config.SEND_MESSAGE_FORMAT}

def getSendMessageFormatWithT(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SEND_MESSAGE_FORMAT_WITH_T}

def setSendMessageFormatWithT(data, *args, **kwargs) -> dict:
    if len(data) > 0:
        if isUniqueStrings(["[message]", "[translation]"], data) is True:
            config.SEND_MESSAGE_FORMAT_WITH_T = data
    return {"status":200, "result":config.SEND_MESSAGE_FORMAT_WITH_T}

def getReceivedMessageFormat(*args, **kwargs) -> dict:
    return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT}

def setReceivedMessageFormat(data, *args, **kwargs) -> dict:
    if isUniqueStrings(["[message]"], data) is True:
        config.RECEIVED_MESSAGE_FORMAT = data
    return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT}

def getReceivedMessageFormatWithT(*args, **kwargs) -> dict:
    return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_WITH_T}

def setReceivedMessageFormatWithT(data, *args, **kwargs) -> dict:
    if len(data) > 0:
        if isUniqueStrings(["[message]", "[translation]"], data) is True:
            config.RECEIVED_MESSAGE_FORMAT_WITH_T = data
    return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_WITH_T}

def getSpeaker2ChatboxPass(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SPEAKER2CHATBOX_PASS}

def setSpeaker2ChatboxPass(data, *args, **kwargs) -> dict:
    config.SPEAKER2CHATBOX_PASS = data
    return {"status":200, "result":config.SPEAKER2CHATBOX_PASS}

def getSendReceivedMessageToVrc(*args, **kwargs) -> dict:
    return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

def setEnableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
    config.SEND_RECEIVED_MESSAGE_TO_VRC = True
    return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

def setDisableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
    config.SEND_RECEIVED_MESSAGE_TO_VRC = False
    return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

def getLoggerFeature(*args, **kwargs) -> dict:
    return {"status":200, "result":config.LOGGER_FEATURE}

def setEnableLoggerFeature(*args, **kwargs) -> dict:
    config.LOGGER_FEATURE = True
    model.startLogger()
    return {"status":200, "result":config.LOGGER_FEATURE}

def setDisableLoggerFeature(*args, **kwargs) -> dict:
    model.stopLogger()
    config.LOGGER_FEATURE = False
    return {"status":200, "result":config.LOGGER_FEATURE}

def getVrcMicMuteSync(*args, **kwargs) -> dict:
    return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

def setEnableVrcMicMuteSync(*args, **kwargs) -> dict:
    config.VRC_MIC_MUTE_SYNC = True
    model.startCheckMuteSelfStatus()
    model.changeMicTranscriptStatus()
    return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

def setDisableVrcMicMuteSync(*args, **kwargs) -> dict:
    config.VRC_MIC_MUTE_SYNC = False
    model.stopCheckMuteSelfStatus()
    model.changeMicTranscriptStatus()
    return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

def setEnableCheckSpeakerThreshold(data, action, *args, **kwargs) -> dict:
    progressbar_speaker_energy = ProgressBarSpeakerEnergy(action)
    model.startCheckSpeakerEnergy(
        progressbar_speaker_energy.set,
    )
    config.ENABLE_CHECK_ENERGY_RECEIVE = True
    return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

def setDisableCheckSpeakerThreshold(*args, **kwargs) -> dict:
    model.stopCheckSpeakerEnergy()
    config.ENABLE_CHECK_ENERGY_RECEIVE = False
    return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

def setEnableCheckMicThreshold(data, action, *args, **kwargs) -> dict:
    progressbar_mic_energy = ProgressBarMicEnergy(action)
    model.startCheckMicEnergy(
        progressbar_mic_energy.set,
    )
    config.ENABLE_CHECK_ENERGY_SEND = True
    return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

def setDisableCheckMicThreshold(*args, **kwargs) -> dict:
    model.stopCheckMicEnergy()
    config.ENABLE_CHECK_ENERGY_SEND = False
    return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

# def updateSoftware(data, action, *args, **kwargs) -> dict:
#     printLog("Update callbackUpdateSoftware")
#     download = DownloadSoftwareProgressBar(action)
#     update = UpdateSoftwareProgressBar(action)
#     model.updateSoftware(restart=True, download=download.set, update=update.set)
#     return {"status":200, "result":True}

# def restartSoftware(*args, **kwargs) -> dict:
#     printLog("Restart callbackRestartSoftware")
#     model.reStartSoftware()
#     return {"status":200, "result":True}

def openFilepathLogs(*args, **kwargs) -> dict:
    Popen(['explorer', config.PATH_LOGS.replace('/', '\\')], shell=True)
    return {"status":200, "result":True}

def openFilepathConfigFile(*args, **kwargs) -> dict:
    Popen(['explorer', config.PATH_LOCAL.replace('/', '\\')], shell=True)
    return {"status":200, "result":True}

def setEnableTranscriptionSend(data, action, *args, **kwargs) -> dict:
    startThreadingTranscriptionSendMessage(action)
    config.ENABLE_TRANSCRIPTION_SEND = True
    return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

def setDisableTranscriptionSend(*args, **kwargs) -> dict:
    stopThreadingTranscriptionSendMessage()
    config.ENABLE_TRANSCRIPTION_SEND = False
    return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

def setEnableTranscriptionReceive(data, action, *args, **kwargs) -> dict:
    startThreadingTranscriptionReceiveMessage(action)
    if config.OVERLAY_SMALL_LOG is True:
        if model.overlay.initialized is False and model.overlay.checkSteamvrRunning() is True:
            model.startOverlay()
    config.ENABLE_TRANSCRIPTION_RECEIVE = True
    return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

def setDisableTranscriptionReceive(*args, **kwargs) -> dict:
    printLog("Disable Transcription Receive")
    stopThreadingTranscriptionReceiveMessage()
    config.ENABLE_TRANSCRIPTION_RECEIVE = False
    return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

def sendMessageBox(data, action, *args, **kwargs) -> dict:
    chat = ChatMessage(action)
    response = chat.send(data)
    return response

def typingMessageBox(*args, **kwargs) -> dict:
    if config.SEND_MESSAGE_TO_VRC is True:
        model.oscStartSendTyping()
    return {"status":200, "result":True}

def stopTypingMessageBox(*args, **kwargs) -> dict:
    if config.SEND_MESSAGE_TO_VRC is True:
        model.oscStopSendTyping()
    return {"status":200, "result":True}

def swapYourLanguageAndTargetLanguage(*args, **kwargs) -> dict:
    your_languages = config.SELECTED_YOUR_LANGUAGES
    your_language_primary = your_languages[config.SELECTED_TAB_NO]["primary"]

    target_languages = config.SELECTED_TARGET_LANGUAGES
    target_language_primary = target_languages[config.SELECTED_TAB_NO]["primary"]

    your_languages[config.SELECTED_TAB_NO]["primary"] = target_language_primary
    target_languages[config.SELECTED_TAB_NO]["primary"] = your_language_primary

    setSelectedYourLanguages(your_languages)
    setSelectedTargetLanguages(target_languages)
    return {
        "status":200,
        "result":{
            "your":config.SELECTED_YOUR_LANGUAGES,
            "target":config.SELECTED_TARGET_LANGUAGES,
            }
        }

def downloadCtranslate2Weight(data, action, *args, **kwargs) -> dict:
    download = DownloadCTranslate2ProgressBar(action)
    startThreadingDownloadCtranslate2Weight(download.set)
    return {"status":200}

def downloadWhisperWeight(data, action, *args, **kwargs) -> dict:
    download = DownloadWhisperProgressBar(action)
    startThreadingDownloadWhisperWeight(download.set)
    return {"status":200}

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

def changeToCTranslate2Process() -> None:
    config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO] = "CTranslate2"

def startTranscriptionSendMessage(action:Callable[[dict], None]) -> None:
    mic_message = MicMessage(action)
    model.startMicTranscript(mic_message.send)

def stopTranscriptionSendMessage() -> None:
    model.stopMicTranscript()

def startThreadingTranscriptionSendMessage(action:Callable[[dict], None]) -> None:
    th_startTranscriptionSendMessage = Thread(target=startTranscriptionSendMessage, args=(action,))
    th_startTranscriptionSendMessage.daemon = True
    th_startTranscriptionSendMessage.start()

def stopThreadingTranscriptionSendMessage() -> None:
    th_stopTranscriptionSendMessage = Thread(target=stopTranscriptionSendMessage)
    th_stopTranscriptionSendMessage.daemon = True
    th_stopTranscriptionSendMessage.start()
    th_stopTranscriptionSendMessage.join()

def startTranscriptionSendMessageOnCloseConfigWindow(action:Callable[[dict], None]) -> None:
    mic_message = MicMessage(action)
    model.startMicTranscript(mic_message.send)

def stopTranscriptionSendMessageOnOpenConfigWindow() -> None:
    model.stopMicTranscript()

def startThreadingTranscriptionSendMessageOnCloseConfigWindow(action:Callable[[dict], None]) -> None:
    th_startTranscriptionSendMessage = Thread(target=startTranscriptionSendMessageOnCloseConfigWindow, args=(action,))
    th_startTranscriptionSendMessage.daemon = True
    th_startTranscriptionSendMessage.start()

def stopThreadingTranscriptionSendMessageOnOpenConfigWindow() -> None:
    th_stopTranscriptionSendMessage = Thread(target=stopTranscriptionSendMessageOnOpenConfigWindow)
    th_stopTranscriptionSendMessage.daemon = True
    th_stopTranscriptionSendMessage.start()

def startTranscriptionReceiveMessage(action:Callable[[dict], None]) -> None:
    speaker_message = SpeakerMessage(action)
    model.startSpeakerTranscript(speaker_message.receive)

def stopTranscriptionReceiveMessage() -> None:
    model.stopSpeakerTranscript()

def startThreadingTranscriptionReceiveMessage(action:Callable[[dict], None]) -> None:
    th_startTranscriptionReceiveMessage = Thread(target=startTranscriptionReceiveMessage, args=(action,))
    th_startTranscriptionReceiveMessage.daemon = True
    th_startTranscriptionReceiveMessage.start()

def stopThreadingTranscriptionReceiveMessage() -> None:
    th_stopTranscriptionReceiveMessage = Thread(target=stopTranscriptionReceiveMessage)
    th_stopTranscriptionReceiveMessage.daemon = True
    th_stopTranscriptionReceiveMessage.start()
    th_stopTranscriptionReceiveMessage.join()

def startTranscriptionReceiveMessageOnCloseConfigWindow(action:Callable[[dict], None]) -> None:
    speaker_message = SpeakerMessage(action)
    model.startSpeakerTranscript(speaker_message.receive)

def stopTranscriptionReceiveMessageOnOpenConfigWindow() -> None:
    model.stopSpeakerTranscript()

def startThreadingTranscriptionReceiveMessageOnCloseConfigWindow(action:Callable[[dict], None]) -> None:
    th_startTranscriptionReceiveMessage = Thread(target=startTranscriptionReceiveMessageOnCloseConfigWindow, args=(action,))
    th_startTranscriptionReceiveMessage.daemon = True
    th_startTranscriptionReceiveMessage.start()

def stopThreadingTranscriptionReceiveMessageOnOpenConfigWindow() -> None:
    th_stopTranscriptionReceiveMessage = Thread(target=stopTranscriptionReceiveMessageOnOpenConfigWindow)
    th_stopTranscriptionReceiveMessage.daemon = True
    th_stopTranscriptionReceiveMessage.start()

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

def restoreText(escaped_text, escape_dict):
    # 大文字小文字を無視して置換するために、正規表現を使う
    for escape_seq, char in escape_dict.items():
        # escaped_text の部分を pattern で置換
        pattern = re.escape(f"${escape_seq}") + r"|\$\s+" + re.escape(escape_seq)
        escaped_text = re.sub(pattern, char, escaped_text, flags=re.IGNORECASE)
    return escaped_text

def removeExclamations(text):
    # ![...] を [...] に置換する正規表現
    pattern = r'!\[(.*?)\]'
    # ![...] の部分を [] 内のテキストに置換
    cleaned_text = re.sub(pattern, r'\1', text)
    return cleaned_text

def updateTranslationEngineAndEngineList():
    engine = config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO]
    engines = getTranslationEngines()["result"]
    if engine not in engines:
        engine = engines[0]
    config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO] = engine

def startThreadingDownloadCtranslate2Weight(callback:Callable[[float], None]) -> None:
    th_download = Thread(target=model.downloadCTranslate2ModelWeight, args=(callback,))
    th_download.daemon = True
    th_download.start()

def startThreadingDownloadWhisperWeight(callback:Callable[[float], None]) -> None:
    th_download = Thread(target=model.downloadWhisperModelWeight, args=(callback,))
    th_download.daemon = True
    th_download.start()

def init(actions:dict, *args, **kwargs) -> None:
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
    updateTranslationEngineAndEngineList()

    # check Downloaded CTranslate2 Model Weight
    printLog("Check Downloaded CTranslate2 Model Weight")
    if config.USE_TRANSLATION_FEATURE is True and model.checkCTranslatorCTranslate2ModelWeight() is False:
        download = DownloadCTranslate2ProgressBar(actions["download_ctranslate2"])
        startThreadingDownloadCtranslate2Weight(download.set)

    # set Transcription Engine
    printLog("Set Transcription Engine")
    if config.USE_WHISPER_FEATURE is True:
        config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
    else:
        config.SELECTED_TRANSCRIPTION_ENGINE = "Google"

    # check Downloaded Whisper Model Weight
    printLog("Check Downloaded Whisper Model Weight")
    if config.USE_WHISPER_FEATURE is True and model.checkTranscriptionWhisperModelWeight() is False:
        download = DownloadWhisperProgressBar(actions["download_whisper"])
        startThreadingDownloadWhisperWeight(download.set)

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
        update_mic_device = UpdateSelectedMicDevice(actions["update_selected_mic_device"])
        device_manager.setCallbackDefaultInputDevice(update_mic_device.set)

    if config.AUTO_SPEAKER_SELECT is True:
        update_speaker_device = UpdateSelectedSpeakerDevice(actions["update_selected_speaker_device"])
        device_manager.setCallbackDefaultOutputDevice(update_speaker_device.set)

    printLog("End Initialization")