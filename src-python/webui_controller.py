from typing import Callable, Union
from time import sleep
from subprocess import Popen
from threading import Thread
import re
from config import config
from model import model
from utils import isUniqueStrings, printLog
from models.transcription.transcription_utils import device_manager

# Common
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

def callbackUpdateSoftware(data, action, *args, **kwargs) -> dict:
    printLog("Update callbackUpdateSoftware")
    download = DownloadSoftwareProgressBar(action)
    update = UpdateSoftwareProgressBar(action)
    model.updateSoftware(restart=True, download=download.set, update=update.set)
    return {"status":200, "result":True}

def callbackRestartSoftware(*args, **kwargs) -> dict:
    printLog("Restart callbackRestartSoftware")
    model.reStartSoftware()
    return {"status":200, "result":True}

def callbackFilepathLogs(*args, **kwargs) -> dict:
    printLog("Open Logs Folder")
    Popen(['explorer', config.PATH_LOGS.replace('/', '\\')], shell=True)
    return {"status":200, "result":True}

def callbackFilepathConfigFile(*args, **kwargs) -> dict:
    printLog("Open Config File")
    Popen(['explorer', config.PATH_LOCAL.replace('/', '\\')], shell=True)
    return {"status":200, "result":True}

# def callbackEnableEasterEgg():
#     printLog("Enable Easter Egg")
#     config.IS_EASTER_EGG_ENABLED = True
#     config.OVERLAY_UI_TYPE = "sakura"
#     return {"status":200, "result":config.IS_EASTER_EGG_ENABLED}

def messageFormatter(format_type:str, translation:list, message:list):
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

def changeToCTranslate2Process():
    config.SELECTED_TRANSLATOR_ENGINES[config.SELECTED_TAB_NO] = "CTranslate2"

# func transcription send message
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

                if config.ENABLE_CONVERT_MESSAGE_TO_ROMAJI is True or config.ENABLE_CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"] == "Japanese":
                        transliteration = model.convertMessageToTransliteration(translation[0])

            if config.ENABLE_TRANSCRIPTION_SEND is True:
                if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
                    if config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES is True:
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
                if config.ENABLE_LOGGER is True:
                    if len(translation) > 0:
                        translation = " (" + "/".join(translation) + ")"
                    model.logger.info(f"[SENT] {message}{translation}")

                # if config.ENABLE_OVERLAY_SMALL_LOG is True:
                #     overlay_image = model.createOverlayImageShort(message, translation)
                #     model.updateOverlay(overlay_image)
                #     overlay_image = model.createOverlayImageLong("send", message, translation)
                #     model.updateOverlay(overlay_image)

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

def stopTranscriptionSendMessageOnOpenConfigWindow():
    model.stopMicTranscript()

def startThreadingTranscriptionSendMessageOnCloseConfigWindow(action:Callable[[dict], None]) -> None:
    th_startTranscriptionSendMessage = Thread(target=startTranscriptionSendMessageOnCloseConfigWindow, args=(action,))
    th_startTranscriptionSendMessage.daemon = True
    th_startTranscriptionSendMessage.start()

def stopThreadingTranscriptionSendMessageOnOpenConfigWindow() -> None:
    th_stopTranscriptionSendMessage = Thread(target=stopTranscriptionSendMessageOnOpenConfigWindow)
    th_stopTranscriptionSendMessage.daemon = True
    th_stopTranscriptionSendMessage.start()

# func transcription receive message
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

                if config.ENABLE_CONVERT_MESSAGE_TO_ROMAJI is True or config.ENABLE_CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"] == "Japanese":
                        transliteration = model.convertMessageToTransliteration(message)

            if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
                if config.ENABLE_OVERLAY_SMALL_LOG is True:
                    if model.overlay.initialized is True:
                        overlay_image = model.createOverlayImageShort(message, translation)
                        model.updateOverlay(overlay_image)
                    # overlay_image = model.createOverlayImageLong("receive", message, translation)
                    # model.updateOverlay(overlay_image)

                # ------------Speaker2Chatbox------------
                if config.ENABLE_SPEAKER2CHATBOX is True:
                    # send OSC message
                    if config.ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC is True:
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
                if config.ENABLE_LOGGER is True:
                    if len(translation) > 0:
                        translation = " (" + "/".join(translation) + ")"
                    model.logger.info(f"[RECEIVED] {message}{translation}")

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

def stopTranscriptionReceiveMessageOnOpenConfigWindow():
    model.stopSpeakerTranscript()

def startThreadingTranscriptionReceiveMessageOnCloseConfigWindow(action:Callable[[dict], None]) -> None:
    th_startTranscriptionReceiveMessage = Thread(target=startTranscriptionReceiveMessageOnCloseConfigWindow, args=(action,))
    th_startTranscriptionReceiveMessage.daemon = True
    th_startTranscriptionReceiveMessage.start()

def stopThreadingTranscriptionReceiveMessageOnOpenConfigWindow():
    th_stopTranscriptionReceiveMessage = Thread(target=stopTranscriptionReceiveMessageOnOpenConfigWindow)
    th_stopTranscriptionReceiveMessage.daemon = True
    th_stopTranscriptionReceiveMessage.start()

# func message box
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

                if config.ENABLE_CONVERT_MESSAGE_TO_ROMAJI is True or config.ENABLE_CONVERT_MESSAGE_TO_HIRAGANA is True:
                    if config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"] == "Japanese":
                        transliteration = model.convertMessageToTransliteration(translation[0])

            # send OSC message
            if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
                if config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES is True:
                    if config.ENABLE_TRANSLATION is False:
                        osc_message = messageFormatter("SEND", "", [message])
                    else:
                        osc_message = messageFormatter("SEND", "", translation)
                else:
                    osc_message = messageFormatter("SEND", translation, [message])
                model.oscSendMessage(osc_message)

            # if config.ENABLE_OVERLAY_SMALL_LOG is True:
            #     overlay_image = model.createOverlayImageShort(message, translation)
            #     model.updateOverlay(overlay_image)
            #     overlay_image = model.createOverlayImageLong("send", message, translation)
            #     model.updateOverlay(overlay_image)

            # update textbox message log (Sent)
            if config.ENABLE_LOGGER is True:
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

def callbackMessageBoxSend(data, action, *args, **kwargs) -> dict:
    chat = ChatMessage(action)
    response = chat.send(data)
    return response

def callbackMessageBoxTyping(*args, **kwargs) -> dict:
    if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
        model.oscStartSendTyping()
    return {"status":200, "result":True}

def callbackMessageBoxTypingStop(*args, **kwargs) -> dict:
    if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
        model.oscStopSendTyping()
    return {"status":200, "result":True}

# def addSentMessageLog(sent_message):
#     config.SENT_MESSAGES_LOG.append(sent_message)
#     config.CURRENT_SENT_MESSAGES_LOG_INDEX = len(config.SENT_MESSAGES_LOG)

# def updateMessageBox(index_offset):
#     if len(config.SENT_MESSAGES_LOG) == 0:
#         return
#     try:
#         new_index = config.CURRENT_SENT_MESSAGES_LOG_INDEX + index_offset
#         target_message_text = config.SENT_MESSAGES_LOG[new_index]
#         # view.replaceMessageBox(target_message_text)
#         config.CURRENT_SENT_MESSAGES_LOG_INDEX = new_index
#     except IndexError:
#         pass

# def messageBoxUpKeyPress():
#     if config.CURRENT_SENT_MESSAGES_LOG_INDEX > 0:
#         updateMessageBox(-1)

# def messageBoxDownKeyPress():
#     if config.CURRENT_SENT_MESSAGES_LOG_INDEX < len(config.SENT_MESSAGES_LOG) - 1:
#         updateMessageBox(1)

def getTranslationEngines(*args, **kwargs) -> dict:
    engines = model.findTranslationEngines(
        config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
        config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
        config.ENABLE_MULTI_LANGUAGE_TRANSLATION,
        )
    return {"status":200, "result":engines}

def updateTranslationEngineAndEngineList():
    engine = config.SELECTED_TRANSLATOR_ENGINES[config.SELECTED_TAB_NO]
    engines = getTranslationEngines()["result"]
    if engine not in engines:
        engine = engines[0]
    config.SELECTED_TRANSLATOR_ENGINES[config.SELECTED_TAB_NO] = engine

def setYourLanguageAndCountry(select:dict, *args, **kwargs) -> dict:
    printLog("setYourLanguageAndCountry", select)
    config.SELECTED_TAB_YOUR_LANGUAGES = select
    updateTranslationEngineAndEngineList()
    return {"status":200, "result":config.SELECTED_TAB_YOUR_LANGUAGES}

def setTargetLanguageAndCountry(select:dict, *args, **kwargs) -> dict:
    printLog("setTargetLanguageAndCountry", select)
    config.SELECTED_TAB_TARGET_LANGUAGES = select
    updateTranslationEngineAndEngineList()
    return {"status":200, "result":config.SELECTED_TAB_TARGET_LANGUAGES}

def swapYourLanguageAndTargetLanguage(*args, **kwargs) -> dict:
    printLog("swapYourLanguageAndTargetLanguage")
    your_language = config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
    your_language_primary = your_language["primary"]
    target_language = config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
    target_language_primary = target_language["primary"]

    your_language["primary"] = target_language_primary
    target_language["primary"] = your_language_primary
    setYourLanguageAndCountry(your_language)
    setTargetLanguageAndCountry(target_language)
    return {
        "status":200,
        "result":{
            "your":config.SELECTED_TAB_YOUR_LANGUAGES,
            "target":config.SELECTED_TAB_TARGET_LANGUAGES,
            }
        }

def callbackSelectedLanguagePresetTab(selected_tab_no:str, *args, **kwargs) -> dict:
    printLog("callbackSelectedLanguagePresetTab", selected_tab_no)
    config.SELECTED_TAB_NO = selected_tab_no
    updateTranslationEngineAndEngineList()
    return {"status":200, "result":config.SELECTED_TAB_NO}

def callbackSetSelectedTranslationEngines(engines:dict, *args, **kwargs) -> dict:
    printLog("callbackSelectedTranslationEngine", engines)
    config.SELECTED_TRANSLATOR_ENGINES = engines
    return {"status":200,"result":{config.SELECTED_TRANSLATOR_ENGINES}}

# command func
def callbackEnableTranslation(*args, **kwargs) -> dict:
    printLog("Enable Translation")
    config.ENABLE_TRANSLATION = True
    if model.isLoadedCTranslate2Model() is False:
        model.changeTranslatorCTranslate2Model()
    return {"status":200, "result":config.ENABLE_TRANSLATION}

def callbackDisableTranslation(*args, **kwargs) -> dict:
    printLog("Disable Translation")
    config.ENABLE_TRANSLATION = False
    return {"status":200, "result":config.ENABLE_TRANSLATION}

def callbackEnableTranscriptionSend(data, action, *args, **kwargs) -> dict:
    printLog("Enable Transcription Send")
    startThreadingTranscriptionSendMessage(action)
    config.ENABLE_TRANSCRIPTION_SEND = True
    return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

def callbackDisableTranscriptionSend(*args, **kwargs) -> dict:
    printLog("Disable Transcription Send")
    stopThreadingTranscriptionSendMessage()
    config.ENABLE_TRANSCRIPTION_SEND = False
    return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

def callbackEnableTranscriptionReceive(data, action, *args, **kwargs) -> dict:
    printLog("Enable Transcription Receive")

    startThreadingTranscriptionReceiveMessage(action)

    if config.ENABLE_OVERLAY_SMALL_LOG is True:
        if model.overlay.initialized is False and model.overlay.checkSteamvrRunning() is True:
            model.startOverlay()
    config.ENABLE_TRANSCRIPTION_RECEIVE = True
    return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

def callbackDisableTranscriptionReceive(*args, **kwargs) -> dict:
    printLog("Disable Transcription Receive")
    stopThreadingTranscriptionReceiveMessage()
    config.ENABLE_TRANSCRIPTION_RECEIVE = False
    return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

def callbackEnableForeground(*args, **kwargs) -> dict:
    printLog("Enable Foreground")
    config.ENABLE_FOREGROUND = True
    return {"status":200, "result":config.ENABLE_FOREGROUND}

def callbackDisableForeground(*args, **kwargs) -> dict:
    printLog("Disable Foreground")
    config.ENABLE_FOREGROUND = False
    return {"status":200, "result":config.ENABLE_FOREGROUND}

def callbackEnableMultiLanguageTranslation(*args, **kwargs) -> dict:
    printLog("Enable Multi Language Translation")
    config.ENABLE_MULTI_LANGUAGE_TRANSLATION = True
    return {"status":200, "result":config.ENABLE_MULTI_LANGUAGE_TRANSLATION}

def callbackDisableMultiLanguageTranslation(*args, **kwargs) -> dict:
    printLog("Disable Multi Language Translation")
    config.ENABLE_MULTI_LANGUAGE_TRANSLATION = False
    return {"status":200, "result":config.ENABLE_MULTI_LANGUAGE_TRANSLATION}

def callbackEnableConvertMessageToRomaji(*args, **kwargs) -> dict:
    printLog("Enable Convert Message To Romaji")
    config.ENABLE_CONVERT_MESSAGE_TO_ROMAJI = True
    return {"status":200, "result":config.ENABLE_CONVERT_MESSAGE_TO_ROMAJI}

def callbackDisableConvertMessageToRomaji(*args, **kwargs) -> dict:
    printLog("Disable Convert Message To Romaji")
    config.ENABLE_CONVERT_MESSAGE_TO_ROMAJI = False
    return {"status":200, "result":config.ENABLE_CONVERT_MESSAGE_TO_ROMAJI}

def callbackEnableConvertMessageToHiragana(*args, **kwargs) -> dict:
    printLog("Enable Convert Message To Hiragana")
    config.ENABLE_CONVERT_MESSAGE_TO_HIRAGANA = True
    return {"status":200, "result":config.ENABLE_CONVERT_MESSAGE_TO_HIRAGANA}

def callbackDisableConvertMessageToHiragana(*args, **kwargs) -> dict:
    printLog("Disable Convert Message To Hiragana")
    config.ENABLE_CONVERT_MESSAGE_TO_HIRAGANA = False
    return {"status":200, "result":config.ENABLE_CONVERT_MESSAGE_TO_HIRAGANA}

def callbackEnableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
    printLog("Enable MainWindow Sidebar Compact Mode")
    config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
    return {"status":200, "result":config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

def callbackDisableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
    printLog("Disable MainWindow Sidebar Compact Mode")
    config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
    return {"status":200, "result":config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

# Config Window
def callbackOpenConfigWindow(*args, **kwargs) -> dict:
    printLog("Open Config Window")
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        stopThreadingTranscriptionSendMessageOnOpenConfigWindow()
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        stopThreadingTranscriptionReceiveMessageOnOpenConfigWindow()
    return {"status":200, "result":True}

def callbackCloseConfigWindow(data, action, *args, **kwargs) -> dict:
    printLog("Close Config Window")
    model.stopCheckMicEnergy()
    model.stopCheckSpeakerEnergy()

    if config.ENABLE_TRANSCRIPTION_SEND is True:
        startThreadingTranscriptionSendMessageOnCloseConfigWindow(action)
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            sleep(2)
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        startThreadingTranscriptionReceiveMessageOnCloseConfigWindow(action)
    return {"status":200, "result":True}

# Appearance Tab
def callbackSetTransparency(data, *args, **kwargs) -> dict:
    printLog("Set Transparency", data)
    config.TRANSPARENCY = int(data)
    return {"status":200, "result":config.TRANSPARENCY}

def callbackSetAppearance(data, *args, **kwargs) -> dict:
    printLog("Set Appearance", data)
    config.APPEARANCE_THEME = data
    return {"status":200, "result":config.APPEARANCE_THEME}

def callbackSetUiScaling(data, *args, **kwargs) -> dict:
    printLog("Set Ui Scaling", data)
    config.UI_SCALING = data
    return {"status":200, "result":config.UI_SCALING}

def callbackSetTextboxUiScaling(data, *args, **kwargs) -> dict:
    printLog("Set Textbox Ui Scaling", data)
    config.TEXTBOX_UI_SCALING = int(data)
    return {"status":200, "result":config.TEXTBOX_UI_SCALING}

def callbackSetMessageBoxRatio(data, *args, **kwargs) -> dict:
    printLog("Set Message Box Ratio", data)
    config.MESSAGE_BOX_RATIO = int(data)
    return {"status":200, "result":config.MESSAGE_BOX_RATIO}

def callbackSetFontFamily(data, *args, **kwargs) -> dict:
    printLog("Set Font Family", data)
    config.FONT_FAMILY = data
    return {"status":200, "result":config.FONT_FAMILY}

def callbackSetUiLanguage(data, *args, **kwargs) -> dict:
    printLog("Set UI Language", data)
    config.UI_LANGUAGE = data
    return {"status":200, "result":config.UI_LANGUAGE}

def callbackEnableRestoreMainWindowGeometry(*args, **kwargs) -> dict:
    printLog("Enable Restore Main Window Geometry")
    config.ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY = True
    return {"status":200, "result":config.ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY}

def callbackDisableRestoreMainWindowGeometry(*args, **kwargs) -> dict:
    printLog("Disable Restore Main Window Geometry")
    config.ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY = True
    return {"status":200, "result":config.ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY}

# Translation Tab
def callbackEnableUseTranslationFeature(*args, **kwargs) -> dict:
    printLog("Enable Translation Feature")
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

def callbackDisableUseTranslationFeature(*args, **kwargs) -> dict:
    printLog("Disable Translation Feature")
    config.USE_TRANSLATION_FEATURE = False
    config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = False
    return {"status":200,
            "result":{
                "feature":config.USE_TRANSLATION_FEATURE,
                "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION,
                },
            }

def callbackSetCtranslate2WeightType(data, *args, **kwargs) -> dict:
    printLog("Set CTranslate2 Weight Type", data)
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

def startThreadingDownloadCtranslate2Weight(callback:Callable[[float], None]) -> None:
    th_download = Thread(target=model.downloadCTranslate2ModelWeight, args=(callback,))
    th_download.daemon = True
    th_download.start()

def callbackDownloadCtranslate2Weight(data, action, *args, **kwargs) -> dict:
    printLog("Download CTranslate2 Weight")
    download = DownloadCTranslate2ProgressBar(action)
    startThreadingDownloadCtranslate2Weight(download.set)
    return {"status":200}

def callbackSetDeeplAuthKey(data, *args, **kwargs) -> dict:
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

def callbackClearDeeplAuthKey(*args, **kwargs) -> dict:
    printLog("Clear DeepL Auth Key")
    auth_keys = config.AUTH_KEYS
    auth_keys["DeepL_API"] = None
    config.AUTH_KEYS = auth_keys
    updateTranslationEngineAndEngineList()
    return {"status":200, "result":config.AUTH_KEYS["DeepL_API"]}

# Transcription Tab
# Transcription (Mic)
class UpdateSelectedMicDevice:
    def __init__(self, action):
        self.action = action

    def set(self, host, device) -> None:
        config.CHOICE_MIC_HOST = host
        config.CHOICE_MIC_DEVICE = device
        printLog("Update Host/Mic Device", f"{host}/{device}")
        self.action("mic", {
            "status":200,
            "result":{"host":host, "device":device}
            })

class UpdateSelectedSpeakerDevice:
    def __init__(self, action):
        self.action = action

    def set(self, device) -> None:
        config.CHOICE_SPEAKER_DEVICE = device
        printLog("Update Speaker Device", device)
        self.action("speaker", {
            "status":200,
            "result":device
            })

def callbackEnableMicAutomaticSelection(data, action, *args, **kwargs) -> dict:
    printLog("Enable Mic Automatic Selection")
    update_device = UpdateSelectedMicDevice(action)
    device_manager.setCallbackDefaultInputDevice(update_device.set)
    config.ENABLE_MIC_AUTOMATIC_SELECTION = True
    return {"status":200, "result":config.ENABLE_MIC_AUTOMATIC_SELECTION}

def callbackDisableMicAutomaticSelection(*args, **kwargs) -> dict:
    printLog("Disable Mic Automatic Selection")
    device_manager.clearCallbackDefaultInputDevice()
    config.ENABLE_MIC_AUTOMATIC_SELECTION = False
    return {"status":200, "result":config.ENABLE_MIC_AUTOMATIC_SELECTION}

def callbackEnableSpeakerAutomaticSelection(data, action, *args, **kwargs) -> dict:
    printLog("Enable Speaker Automatic Selection")
    update_device = UpdateSelectedSpeakerDevice(action)
    device_manager.setCallbackDefaultOutputDevice(update_device.set)
    config.ENABLE_SPEAKER_AUTOMATIC_SELECTION = True
    return {"status":200, "result":config.ENABLE_SPEAKER_AUTOMATIC_SELECTION}

def callbackDisableSpeakerAutomaticSelection(*args, **kwargs) -> dict:
    printLog("Disable Speaker Automatic Selection")
    device_manager.clearCallbackDefaultInputDevice()
    config.ENABLE_SPEAKER_AUTOMATIC_SELECTION = False
    return {"status":200, "result":config.ENABLE_SPEAKER_AUTOMATIC_SELECTION}

def callbackSetMicHost(data, *args, **kwargs) -> dict:
    printLog("Set Mic Host", data)
    config.CHOICE_MIC_HOST = data
    config.CHOICE_MIC_DEVICE = model.getInputDefaultDevice()
    if config.ENABLE_CHECK_ENERGY_SEND is True:
        model.stopCheckMicEnergy()
        model.startCheckMicEnergy()
    return {"status":200,
            "result":{
                "host":config.CHOICE_MIC_HOST,
                "device":config.CHOICE_MIC_DEVICE,
                },
            }

def callbackSetMicDevice(data, *args, **kwargs) -> dict:
    printLog("Set Mic Device", data)
    config.CHOICE_MIC_DEVICE = data
    if config.ENABLE_CHECK_ENERGY_SEND is True:
        model.stopCheckMicEnergy()
        model.startCheckMicEnergy()
    return {"status":200, "result": config.CHOICE_MIC_DEVICE}

def callbackSetMicEnergyThreshold(data, *args, **kwargs) -> dict:
    printLog("Set Mic Energy Threshold", data)
    status = 400
    data = int(data)
    if 0 <= data <= config.MAX_MIC_ENERGY_THRESHOLD:
        config.INPUT_MIC_ENERGY_THRESHOLD = data
        status = 200
    return {"status": status, "result": config.INPUT_MIC_ENERGY_THRESHOLD}

def callbackEnableMicDynamicEnergyThreshold(*args, **kwargs) -> dict:
    printLog("Enable Mic Dynamic Energy Threshold")
    config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = True
    return {"status":200, "result":config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD}

def callbackDisableMicDynamicEnergyThreshold(*args, **kwargs) -> dict:
    printLog("Disable Mic Dynamic Energy Threshold")
    config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = False
    return {"status":200, "result":config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD}

class ProgressBarMicEnergy:
    def __init__(self, action):
        self.action = action

    def set(self, energy) -> None:
        if energy is False:
            self.action("error_device", {"status":400,"result": {"message":"No mic device detected."}})
        else:
            self.action("mic", {"status":200, "result":energy})

def callbackEnableCheckMicThreshold(data, action, *args, **kwargs) -> dict:
    printLog("Enable Check Mic Threshold")
    progressbar_mic_energy = ProgressBarMicEnergy(action)
    model.startCheckMicEnergy(
        progressbar_mic_energy.set,
    )
    config.ENABLE_CHECK_ENERGY_SEND = True
    return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

def callbackDisableCheckMicThreshold(*args, **kwargs) -> dict:
    printLog("Disable Check Mic Threshold")
    model.stopCheckMicEnergy()
    config.ENABLE_CHECK_ENERGY_SEND = False
    return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

def callbackSetMicRecordTimeout(data, *args, **kwargs) -> dict:
    printLog("Set Mic Record Timeout", data)
    try:
        data = int(data)
        if 0 <= data <= config.INPUT_MIC_PHRASE_TIMEOUT:
            config.INPUT_MIC_RECORD_TIMEOUT = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":400, "result":{"message":"Error Mic Record Timeout"}}
    else:
        response = {"status":200, "result":config.INPUT_MIC_RECORD_TIMEOUT}
    return response

def callbackSetMicPhraseTimeout(data, *args, **kwargs) -> dict:
    printLog("Set Mic Phrase Timeout", data)
    try:
        data = int(data)
        if data >= config.INPUT_MIC_RECORD_TIMEOUT:
            config.INPUT_MIC_PHRASE_TIMEOUT = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":400, "result":{"message":"Error Mic Phrase Timeout"}}
    else:
        response = {"status":200, "result":config.INPUT_MIC_PHRASE_TIMEOUT}
    return response

def callbackSetMicMaxPhrases(data, *args, **kwargs) -> dict:
    printLog("Set Mic Max Phrases", data)
    try:
        data = int(data)
        if 0 <= data:
            config.INPUT_MIC_MAX_PHRASES = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":400, "result":{"message":"Error Mic Max Phrases"}}
    else:
        response = {"status":200, "result":config.INPUT_MIC_MAX_PHRASES}
    return response

def callbackSetMicWordFilter(data, *args, **kwargs) -> dict:
    printLog("Set Mic Word Filter", data)
    data = str(data)
    data = [w.strip() for w in data.split(",") if len(w.strip()) > 0]
    # Copy the list
    new_input_mic_word_filter_list = config.INPUT_MIC_WORD_FILTER
    new_added_value = []
    for value in data:
        if value in new_input_mic_word_filter_list:
            # If the value is already in the list, do nothing.
            pass
        else:
            new_input_mic_word_filter_list.append(value)
            new_added_value.append(value)
    config.INPUT_MIC_WORD_FILTER = new_input_mic_word_filter_list

    model.resetKeywordProcessor()
    model.addKeywords()
    return {"status":200, "result":config.INPUT_MIC_WORD_FILTER}

def callbackDeleteMicWordFilter(data, *args, **kwargs) -> dict:
    printLog("Delete Mic Word Filter", data)
    try:
        new_input_mic_word_filter_list = config.INPUT_MIC_WORD_FILTER
        new_input_mic_word_filter_list.remove(str(data))
        config.INPUT_MIC_WORD_FILTER = new_input_mic_word_filter_list
        model.resetKeywordProcessor()
        model.addKeywords()
    except Exception:
        printLog("Delete Mic Word Filter", "There was no the target word in config.INPUT_MIC_WORD_FILTER")
    return {"status":200, "result":config.INPUT_MIC_WORD_FILTER}

# Transcription (Speaker)
def callbackSetSpeakerDevice(data, *args, **kwargs) -> dict:
    printLog("Set Speaker Device", data)
    config.CHOICE_SPEAKER_DEVICE = data
    if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
        model.stopCheckSpeakerEnergy()
        model.startCheckSpeakerEnergy()
    return {"status":200, "result":config.CHOICE_SPEAKER_DEVICE}

def callbackSetSpeakerEnergyThreshold(data, *args, **kwargs) -> dict:
    printLog("Set Speaker Energy Threshold", data)
    try:
        data = int(data)
        if 0 <= data <= config.MAX_SPEAKER_ENERGY_THRESHOLD:
            config.INPUT_SPEAKER_ENERGY_THRESHOLD = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":400, "result":{"message":"Error Set Speaker Energy Threshold"}}
    else:
        response = {"status":200, "result":config.INPUT_SPEAKER_ENERGY_THRESHOLD}
    return response

def callbackEnableSpeakerDynamicEnergyThreshold(*args, **kwargs) -> dict:
    printLog("Enable Speaker Dynamic Energy Threshold")
    config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = True
    return {"status":200, "result":config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD}

def callbackDisableSpeakerDynamicEnergyThreshold(*args, **kwargs) -> dict:
    printLog("Disable Speaker Dynamic Energy Threshold")
    config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = False
    return {"status":200, "result":config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD}

class ProgressBarSpeakerEnergy:
    def __init__(self, action):
        self.action = action

    def set(self, energy) -> None:
        if energy is False:
            self.action("error_device", {"status":400,"result": {"message":"No mic device detected."}})
        else:
            self.action("speaker", {"status":200, "result":energy})

def callbackEnableCheckSpeakerThreshold(data, action, *args, **kwargs) -> dict:
    printLog("Enable Check Speaker Threshold")
    progressbar_speaker_energy = ProgressBarSpeakerEnergy(action)
    model.startCheckSpeakerEnergy(
        progressbar_speaker_energy.set,
    )
    config.ENABLE_CHECK_ENERGY_RECEIVE = True
    return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

def callbackDisableCheckSpeakerThreshold(*args, **kwargs) -> dict:
    printLog("Disable Check Speaker Threshold")
    model.stopCheckSpeakerEnergy()
    config.ENABLE_CHECK_ENERGY_RECEIVE = False
    return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

def callbackSetSpeakerRecordTimeout(data, *args, **kwargs) -> dict:
    printLog("Set Speaker Record Timeout", data)
    try:
        data = int(data)
        if 0 <= data <= config.INPUT_SPEAKER_PHRASE_TIMEOUT:
            config.INPUT_SPEAKER_RECORD_TIMEOUT = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":400, "result":{"message":"Error Speaker Record Timeout"}}
    else:
        response = {"status":200, "result":config.INPUT_SPEAKER_RECORD_TIMEOUT}
    return response

def callbackSetSpeakerPhraseTimeout(data, *args, **kwargs) -> dict:
    printLog("Set Speaker Phrase Timeout", data)
    try:
        data = int(data)
        if 0 <= data and data >= config.INPUT_SPEAKER_RECORD_TIMEOUT:
            config.INPUT_SPEAKER_PHRASE_TIMEOUT = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":400, "result":{"message":"Error Speaker Phrase Timeout"}}
    else:
        response = {"status":200, "result":config.INPUT_SPEAKER_PHRASE_TIMEOUT}
    return response

def callbackSetSpeakerMaxPhrases(data, *args, **kwargs) -> dict:
    printLog("Set Speaker Max Phrases", data)
    try:
        data = int(data)
        if 0 <= data:
            config.INPUT_SPEAKER_MAX_PHRASES = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":400, "result":{"message":"Error Speaker Max Phrases"}}
    else:
        response = {"status":200, "result":config.INPUT_SPEAKER_MAX_PHRASES}
    return response

# Transcription (Internal AI Model)
def callbackEnableUseWhisperFeature(*args, **kwargs) -> dict:
    printLog("Enable Whisper Feature")
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

def callbackDisableUseWhisperFeature(*args, **kwargs) -> dict:
    printLog("Disable Whisper Feature")
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

def callbackSetWhisperWeightType(data, *args, **kwargs) -> dict:
    printLog("Set Whisper Weight Type", data)
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

def startThreadingDownloadWhisperWeight(callback:Callable[[float], None]) -> None:
    th_download = Thread(target=model.downloadWhisperModelWeight, args=(callback,))
    th_download.daemon = True
    th_download.start()

def callbackDownloadWhisperWeight(data, action, *args, **kwargs) -> dict:
    printLog("Download Whisper Weight")
    download = DownloadWhisperProgressBar(action)
    startThreadingDownloadWhisperWeight(download.set)
    return {"status":200}

# VR Tab
def callbackSetOverlaySettingsOpacity(data, *args, **kwargs) -> dict:
    printLog("Set Overlay Settings Opacity", data)
    pre_settings = config.OVERLAY_SETTINGS
    pre_settings["opacity"] = data
    config.OVERLAY_SETTINGS = pre_settings
    model.updateOverlayImageOpacity()
    return {"status":200, "result":config.OVERLAY_SETTINGS["opacity"]}

def callbackSetOverlaySettingsUiScaling(data, *args, **kwargs) -> dict:
    printLog("Set Overlay Settings Ui Scaling", data)
    pre_settings = config.OVERLAY_SETTINGS
    pre_settings["ui_scaling"] = data
    config.OVERLAY_SETTINGS = pre_settings
    model.updateOverlayImageUiScaling()
    return {"status":200, "result":config.OVERLAY_SETTINGS["ui_scaling"]}

def callbackEnableOverlaySmallLog(*args, **kwargs) -> dict:
    printLog("Enable Overlay Small Log")
    config.ENABLE_OVERLAY_SMALL_LOG = True

    if config.ENABLE_OVERLAY_SMALL_LOG is True and config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        if model.overlay.initialized is False and model.overlay.checkSteamvrRunning() is True:
            model.startOverlay()
    return {"status":200, "result":config.ENABLE_OVERLAY_SMALL_LOG}

def callbackDisableOverlaySmallLog(*args, **kwargs) -> dict:
    printLog("Disable Overlay Small Log")
    config.ENABLE_OVERLAY_SMALL_LOG = False
    if config.ENABLE_OVERLAY_SMALL_LOG is False:
        model.clearOverlayImage()
        model.shutdownOverlay()
    return {"status":200, "result":config.ENABLE_OVERLAY_SMALL_LOG}

def callbackSetOverlaySmallLogSettingsXPos(data, *args, **kwargs) -> dict:
    printLog("Set Overlay Small Log Settings X Pos", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["x_pos"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS["x_pos"]}

def callbackSetOverlaySmallLogSettingsYPos(data, *args, **kwargs) -> dict:
    printLog("Set Overlay Small Log Settings Y Pos", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["y_pos"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS["y_pos"]}

def callbackSetOverlaySmallLogSettingsZPos(data, *args, **kwargs) -> dict:
    printLog("Set Overlay Small Log Settings Z Pos", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["z_pos"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS["z_pos"]}

def callbackSetOverlaySmallLogSettingsXRotation(data, *args, **kwargs) -> dict:
    printLog("Set Overlay Small Log Settings X Rotation", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["x_rotation"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS["x_rotation"]}

def callbackSetOverlaySmallLogSettingsYRotation(data, *args, **kwargs) -> dict:
    printLog("Set Overlay Small Log Settings Y Rotation", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["y_rotation"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS["y_rotation"]}

def callbackSetOverlaySmallLogSettingsZRotation(data, *args, **kwargs) -> dict:
    printLog("Set Overlay Small Log Settings Z Rotation", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["z_rotation"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS["z_rotation"]}

# Others Tab
def callbackEnableAutoClearMessageBox(*args, **kwargs) -> dict:
    printLog("Enable Auto Clear Message Box")
    config.ENABLE_AUTO_CLEAR_MESSAGE_BOX = True
    return {"status":200, "result":config.ENABLE_AUTO_CLEAR_MESSAGE_BOX}

def callbackDisableAutoClearMessageBox(*args, **kwargs) -> dict:
    printLog("Disable Auto Clear Message Box")
    config.ENABLE_AUTO_CLEAR_MESSAGE_BOX = False
    return {"status":200, "result":config.ENABLE_AUTO_CLEAR_MESSAGE_BOX}

def callbackEnableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
    printLog("Enable Send Only Translated Messages")
    config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES = True
    return {"status":200, "result":config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES}

def callbackDisableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
    printLog("Disable Send Only Translated Messages")
    config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES = False
    return {"status":200, "result":config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES}

def callbackSetSendMessageButtonType(data, *args, **kwargs) -> dict:
    printLog("Set Send Message Button Type", data)
    config.SEND_MESSAGE_BUTTON_TYPE = data
    return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}

def callbackEnableAutoExportMessageLogs(*args, **kwargs) -> dict:
    printLog("Enable Auto Export Message Logs")
    config.ENABLE_LOGGER = True
    model.startLogger()
    return {"status":200, "result":config.ENABLE_LOGGER}

def callbackDisableAutoExportMessageLogs(*args, **kwargs) -> dict:
    printLog("Disable Auto Export Message Logs")
    config.ENABLE_LOGGER = False
    model.stopLogger()
    return {"status":200, "result":config.ENABLE_LOGGER}

def callbackEnableVrcMicMuteSync(*args, **kwargs) -> dict:
    printLog("Enable VRC Mic Mute Sync")
    config.ENABLE_VRC_MIC_MUTE_SYNC = True
    model.startCheckMuteSelfStatus()
    model.changeMicTranscriptStatus()
    return {"status":200, "result":config.ENABLE_VRC_MIC_MUTE_SYNC}

def callbackDisableVrcMicMuteSync(*args, **kwargs) -> dict:
    printLog("Disable VRC Mic Mute Sync")
    config.ENABLE_VRC_MIC_MUTE_SYNC = False
    model.stopCheckMuteSelfStatus()
    model.changeMicTranscriptStatus()
    return {"status":200, "result":config.ENABLE_VRC_MIC_MUTE_SYNC}

def callbackEnableSendMessageToVrc(*args, **kwargs) -> dict:
    printLog("Enable Send Message To VRC")
    config.ENABLE_SEND_MESSAGE_TO_VRC = True
    return {"status":200, "result":config.ENABLE_SEND_MESSAGE_TO_VRC}

def callbackDisableSendMessageToVrc(*args, **kwargs) -> dict:
    printLog("Disable Send Message To VRC")
    config.ENABLE_SEND_MESSAGE_TO_VRC = False
    return {"status":200, "result":config.ENABLE_SEND_MESSAGE_TO_VRC}

# Others (Message Formats(Send)
def callbackSetSendMessageFormat(data, *args, **kwargs) -> dict:
    printLog("Set Send Message Format", data)
    if isUniqueStrings(["[message]"], data) is True:
        config.SEND_MESSAGE_FORMAT = data
    return {"status":200, "result":config.SEND_MESSAGE_FORMAT}

def callbackSetSendMessageFormatWithT(data, *args, **kwargs) -> dict:
    printLog("Set Send Message Format With Translation", data)
    if len(data) > 0:
        if isUniqueStrings(["[message]", "[translation]"], data) is True:
            config.SEND_MESSAGE_FORMAT_WITH_T = data
    return {"status":200, "result":config.SEND_MESSAGE_FORMAT_WITH_T}

# Others (Message Formats(Received)
def callbackSetReceivedMessageFormat(data, *args, **kwargs) -> dict:
    printLog("Set Received Message Format", data)
    if isUniqueStrings(["[message]"], data) is True:
        config.RECEIVED_MESSAGE_FORMAT = data
    return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT}

def callbackSetReceivedMessageFormatWithT(data, *args, **kwargs) -> dict:
    printLog("Set Received Message Format With Translation", data)
    if len(data) > 0:
        if isUniqueStrings(["[message]", "[translation]"], data) is True:
            config.RECEIVED_MESSAGE_FORMAT_WITH_T = data
    return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_WITH_T}

# ---------------------Speaker2Chatbox---------------------
def callbackEnableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
    printLog("Enable Send Received Message To VRC")
    config.ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC = True
    return {"status":200, "result":config.ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC}

def callbackDisableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
    printLog("Disable Send Received Message To VRC")
    config.ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC = False
    return {"status":200, "result":config.ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC}
# ---------------------Speaker2Chatbox---------------------

def callbackEnableLogger(*args, **kwargs) -> dict:
    printLog("Enable Logger")
    config.ENABLE_LOGGER = True
    model.startLogger()
    return {"status":200, "result":config.ENABLE_LOGGER}

def callbackDisableLogger(*args, **kwargs) -> dict:
    printLog("Disable Logger")
    config.ENABLE_LOGGER = False
    model.stopLogger()
    return {"status":200, "result":config.ENABLE_LOGGER}

# Advanced Settings Tab
def callbackSetOscIpAddress(data, *args, **kwargs) -> dict:
    printLog("Set OSC IP Address", data)
    config.OSC_IP_ADDRESS = str(data)
    return {"status":200, "result":config.OSC_IP_ADDRESS}

def callbackSetOscPort(data, *args, **kwargs) -> dict:
    printLog("Set OSC Port", data)
    config.OSC_PORT = int(data)
    return {"status":200, "result":config.OSC_PORT}

def getListLanguageAndCountry(*args, **kwargs) -> dict:
    return {"status":200, "result": model.getListLanguageAndCountry()}

def getListInputHost(*args, **kwargs) -> dict:
    return {"status":200, "result": model.getListInputHost()}

def getListInputDevice(*args, **kwargs) -> dict:
    return {"status":200, "result": model.getListInputDevice()}

def getListOutputDevice(*args, **kwargs) -> dict:
    return {"status":200, "result": model.getListOutputDevice()}

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
    if config.ENABLE_LOGGER is True:
        model.startLogger()

    # init OSC receive
    printLog("Init OSC Receive")
    model.startReceiveOSC()
    if config.ENABLE_VRC_MIC_MUTE_SYNC is True:
        model.startCheckMuteSelfStatus()

    # init Auto device selection
    printLog("Init Auto Device Selection")
    if config.ENABLE_MIC_AUTOMATIC_SELECTION is True:
        update_mic_device = UpdateSelectedMicDevice(actions["update_selected_mic_device"])
        device_manager.setCallbackDefaultInputDevice(update_mic_device.set)

    if config.ENABLE_SPEAKER_AUTOMATIC_SELECTION is True:
        update_speaker_device = UpdateSelectedSpeakerDevice(actions["update_selected_speaker_device"])
        device_manager.setCallbackDefaultOutputDevice(update_speaker_device.set)

    printLog("End Initialization")