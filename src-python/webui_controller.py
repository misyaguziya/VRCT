from typing import Callable, Union
from time import sleep
from subprocess import Popen
from threading import Thread
from config import config
from model import model
# from view import view
from utils import getKeyByValue, isUniqueStrings, strPctToInt
import argparse

# Common
def callbackUpdateSoftware(func=None):
    setMainWindowGeometry()
    model.updateSoftware(restart=True, func=func)

def callbackRestartSoftware():
    setMainWindowGeometry()
    model.reStartSoftware()

def callbackFilepathLogs():
    print("[LOG]", "callbackFilepathLogs", config.PATH_LOGS.replace('/', '\\'))
    Popen(['explorer', config.PATH_LOGS.replace('/', '\\')], shell=True)
    return "Success", 200

def callbackFilepathConfigFile():
    print("[LOG]","callbackFilepathConfigFile", config.PATH_LOCAL.replace('/', '\\'))
    Popen(['explorer', config.PATH_LOCAL.replace('/', '\\')], shell=True)
    return "Success", 200

def callbackQuitVrct():
    setMainWindowGeometry()

def callbackEnableEasterEgg():
    config.IS_EASTER_EGG_ENABLED = True
    config.OVERLAY_UI_TYPE = "sakura"
    # view.printToTextbox_enableEasterEgg()

def setMainWindowGeometry():
    # PRE_SCALING_INT = strPctToInt(view.getPreUiScaling())
    # NEW_SCALING_INT = strPctToInt(config.UI_SCALING)
    # MULTIPLY_FLOAT = (NEW_SCALING_INT / PRE_SCALING_INT)
    # main_window_geometry = view.getMainWindowGeometry(return_int=True)
    # main_window_geometry["width"] = str(int(main_window_geometry["width"] * MULTIPLY_FLOAT))
    # main_window_geometry["height"] = str(int(main_window_geometry["height"] * MULTIPLY_FLOAT))
    # main_window_geometry["x_pos"] = str(main_window_geometry["x_pos"])
    # main_window_geometry["y_pos"] = str(main_window_geometry["y_pos"])
    # config.MAIN_WINDOW_GEOMETRY = main_window_geometry
    pass

def messageFormatter(format_type:str, translation, message):
    if format_type == "RECEIVED":
        FORMAT_WITH_T = config.RECEIVED_MESSAGE_FORMAT_WITH_T
        FORMAT = config.RECEIVED_MESSAGE_FORMAT
    elif format_type == "SEND":
        FORMAT_WITH_T = config.SEND_MESSAGE_FORMAT_WITH_T
        FORMAT = config.SEND_MESSAGE_FORMAT
    else:
        raise ValueError("format_type is not found", format_type)

    if len(translation) > 0:
        osc_message = FORMAT_WITH_T.replace("[message]", message)
        osc_message = osc_message.replace("[translation]", translation)
    else:
        osc_message = FORMAT.replace("[message]", message)
    return osc_message

def changeToCTranslate2Process():
    if config.CHOICE_INPUT_TRANSLATOR != "CTranslate2" or config.CHOICE_OUTPUT_TRANSLATOR != "CTranslate2":
        config.CHOICE_INPUT_TRANSLATOR = "CTranslate2"
        config.CHOICE_OUTPUT_TRANSLATOR = "CTranslate2"
        updateTranslationEngineAndEngineList()
        # view.printToTextbox_TranslationEngineLimitError()

# func transcription send message
class MicMessage:
    def __init__(self, action:Callable[[dict], None]) -> None:
        self.action = action

    def send(self, message: Union[str, bool]) -> None:
        if isinstance(message, bool) and message is False:
            self.action({"status":"error", "message":"No mic device detected."})
        elif isinstance(message, str) and len(message) > 0:
            addSentMessageLog(message)
            translation = ""
            if model.checkKeywords(message):
                self.action("mic", {"status":"error", "message":f"Detected by word filter:{message}"})
                return
            elif model.detectRepeatSendMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                translation, success = model.getInputTranslate(message)
                if success is False:
                    changeToCTranslate2Process()

            if config.ENABLE_TRANSCRIPTION_SEND is True:
                if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
                    if config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES is True:
                        if config.ENABLE_TRANSLATION is False:
                            osc_message = messageFormatter("SEND", "", message)
                        else:
                            osc_message = messageFormatter("SEND", "", translation)
                    else:
                        osc_message = messageFormatter("SEND", translation, message)
                    model.oscSendMessage(osc_message)

                self.action("mic", {"status":"success", "message":message, "translation":translation})
                if config.ENABLE_LOGGER is True:
                    if len(translation) > 0:
                        translation = f" ({translation})"
                    model.logger.info(f"[SENT] {message}{translation}")

                # if config.ENABLE_OVERLAY_SMALL_LOG is True:
                #     overlay_image = model.createOverlayImageShort(message, translation)
                #     model.updateOverlay(overlay_image)
                #     overlay_image = model.createOverlayImageLong("send", message, translation)
                #     model.updateOverlay(overlay_image)

def startTranscriptionSendMessage(action:Callable[[dict], None]) -> None:
    mic_message = MicMessage(action)
    model.startMicTranscript(mic_message.send)

def stopTranscriptionSendMessage(action:Callable[[dict], None]) -> None:
    model.stopMicTranscript()
    action("mic", {"status":"success", "message":"Stopped sending messages"})

def startThreadingTranscriptionSendMessage(action:Callable[[dict], None]) -> None:
    th_startTranscriptionSendMessage = Thread(target=startTranscriptionSendMessage, args=(action,))
    th_startTranscriptionSendMessage.daemon = True
    th_startTranscriptionSendMessage.start()

def stopThreadingTranscriptionSendMessage(action:Callable[[dict], None]) -> None:
    th_stopTranscriptionSendMessage = Thread(target=stopTranscriptionSendMessage, args=(action,))
    th_stopTranscriptionSendMessage.daemon = True
    th_stopTranscriptionSendMessage.start()

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
            self.action("speaker", {"status":"error", "message":"No mic device detected."})
        elif isinstance(message, str) and len(message) > 0:
            translation = ""
            if model.detectRepeatReceiveMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                translation, success = model.getOutputTranslate(message)
                if success is False:
                    changeToCTranslate2Process()

            if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
                if config.ENABLE_NOTICE_XSOVERLAY is True:
                    xsoverlay_message = messageFormatter("RECEIVED", translation, message)
                    model.notificationXSOverlay(xsoverlay_message)

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
                        osc_message = messageFormatter("RECEIVED", translation, message)
                        model.oscSendMessage(osc_message)
                # ------------Speaker2Chatbox------------

                # update textbox message log (Received)
                self.action("speaker",{"status":"success", "message":message, "translation":translation})
                if config.ENABLE_LOGGER is True:
                    if len(translation) > 0:
                        translation = f" ({translation})"
                    model.logger.info(f"[RECEIVED] {message}{translation}")

def startTranscriptionReceiveMessage(action:Callable[[dict], None]) -> None:
    speaker_message = SpeakerMessage(action)
    model.startSpeakerTranscript(speaker_message.receive)

def stopTranscriptionReceiveMessage(action:Callable[[dict], None]) -> None:
    model.stopSpeakerTranscript()
    action({"status":"success", "message":"Stopped receiving messages"})

def startThreadingTranscriptionReceiveMessage(action:Callable[[dict], None]) -> None:
    th_startTranscriptionReceiveMessage = Thread(target=startTranscriptionReceiveMessage, args=(action,))
    th_startTranscriptionReceiveMessage.daemon = True
    th_startTranscriptionReceiveMessage.start()

def stopThreadingTranscriptionReceiveMessage(action:Callable[[dict], None]) -> None:
    th_stopTranscriptionReceiveMessage = Thread(target=stopTranscriptionReceiveMessage, args=(action,))
    th_stopTranscriptionReceiveMessage.daemon = True
    th_stopTranscriptionReceiveMessage.start()

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
def sendChatMessage(message):
    if len(message) > 0:
        addSentMessageLog(message)
        translation = ""
        if config.ENABLE_TRANSLATION is False:
            pass
        else:
            translation, success = model.getInputTranslate(message)
            if success is False:
                changeToCTranslate2Process()

        # send OSC message
        if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
            if config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES is True:
                if config.ENABLE_TRANSLATION is False:
                    osc_message = messageFormatter("SEND", "", message)
                else:
                    osc_message = messageFormatter("SEND", "", translation)
            else:
                osc_message = messageFormatter("SEND", translation, message)
            model.oscSendMessage(osc_message)

        # if config.ENABLE_OVERLAY_SMALL_LOG is True:
        #     overlay_image = model.createOverlayImageShort(message, translation)
        #     model.updateOverlay(overlay_image)
        #     overlay_image = model.createOverlayImageLong("send", message, translation)
        #     model.updateOverlay(overlay_image)

        # update textbox message log (Sent)
        # view.printToTextbox_SentMessage(message, translation)
        if config.ENABLE_LOGGER is True:
            if len(translation) > 0:
                translation = f" ({translation})"
            model.logger.info(f"[SENT] {message}{translation}")

        # delete message in entry message box
        if config.ENABLE_AUTO_CLEAR_MESSAGE_BOX is True:
            # view.clearMessageBox()
            pass

def messageBoxPressKeyEnter():
    # model.oscStopSendTyping()
    # message = view.getTextFromMessageBox()
    # sendChatMessage(message)
    pass

def messageBoxPressKeyAny(e):
    if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
        model.oscStartSendTyping()
    else:
        model.oscStopSendTyping()

def messageBoxFocusIn(e):
    # view.foregroundOffIfForegroundEnabled()
    pass

def messageBoxFocusOut(e):
    # view.foregroundOnIfForegroundEnabled()
    if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
        model.oscStopSendTyping()

def addSentMessageLog(sent_message):
    config.SENT_MESSAGES_LOG.append(sent_message)
    config.CURRENT_SENT_MESSAGES_LOG_INDEX = len(config.SENT_MESSAGES_LOG)

def updateMessageBox(index_offset):
    if len(config.SENT_MESSAGES_LOG) == 0:
        return
    try:
        new_index = config.CURRENT_SENT_MESSAGES_LOG_INDEX + index_offset
        target_message_text = config.SENT_MESSAGES_LOG[new_index]
        # view.replaceMessageBox(target_message_text)
        config.CURRENT_SENT_MESSAGES_LOG_INDEX = new_index
    except IndexError:
        pass

def messageBoxUpKeyPress():
    if config.CURRENT_SENT_MESSAGES_LOG_INDEX > 0:
        updateMessageBox(-1)

def messageBoxDownKeyPress():
    if config.CURRENT_SENT_MESSAGES_LOG_INDEX < len(config.SENT_MESSAGES_LOG) - 1:
        updateMessageBox(1)

def updateTranslationEngineAndEngineList():
    engine = config.CHOICE_INPUT_TRANSLATOR
    engines = model.findTranslationEngines(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)
    if engine not in engines:
        engine = engines[0]
    config.CHOICE_INPUT_TRANSLATOR = engine
    config.CHOICE_OUTPUT_TRANSLATOR = engine

def initSetTranslateEngine():
    engine = config.SELECTED_TAB_YOUR_TRANSLATOR_ENGINES[config.SELECTED_TAB_NO]
    config.CHOICE_INPUT_TRANSLATOR = engine
    engine = config.SELECTED_TAB_TARGET_TRANSLATOR_ENGINES[config.SELECTED_TAB_NO]
    config.CHOICE_OUTPUT_TRANSLATOR = engine

def initSetLanguageAndCountry():
    select = config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
    config.SOURCE_LANGUAGE = select["language"]
    config.SOURCE_COUNTRY = select["country"]
    select = config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
    config.TARGET_LANGUAGE = select["language"]
    config.TARGET_COUNTRY = select["country"]

def setYourTranslateEngine(select):
    engines = config.SELECTED_TAB_YOUR_TRANSLATOR_ENGINES
    engines[config.SELECTED_TAB_NO] = select
    config.SELECTED_TAB_YOUR_TRANSLATOR_ENGINES = engines
    config.CHOICE_INPUT_TRANSLATOR = select

def setTargetTranslateEngine(select):
    engines = config.SELECTED_TAB_TARGET_TRANSLATOR_ENGINES
    engines[config.SELECTED_TAB_NO] = select
    config.SELECTED_TAB_TARGET_TRANSLATOR_ENGINES = engines
    config.CHOICE_OUTPUT_TRANSLATOR = select

def setYourLanguageAndCountry(select:dict, *args, **kwargs) -> dict:
    print("setYourLanguageAndCountry", select)
    languages = config.SELECTED_TAB_YOUR_LANGUAGES
    languages[config.SELECTED_TAB_NO] = select
    config.SELECTED_TAB_YOUR_LANGUAGES = languages
    config.SOURCE_LANGUAGE = select["language"]
    config.SOURCE_COUNTRY = select["country"]
    updateTranslationEngineAndEngineList()
    return {"status":"success",
            "data":{
                "your":{
                    "language":config.SOURCE_LANGUAGE,
                    "country":config.SOURCE_COUNTRY
                }
            }
        }

def setTargetLanguageAndCountry(select:dict, *args, **kwargs) -> dict:
    print("setTargetLanguageAndCountry", select)
    languages = config.SELECTED_TAB_TARGET_LANGUAGES
    languages[config.SELECTED_TAB_NO] = select
    config.SELECTED_TAB_TARGET_LANGUAGES = languages
    config.TARGET_LANGUAGE = select["language"]
    config.TARGET_COUNTRY = select["country"]
    updateTranslationEngineAndEngineList()
    return {"status":"success",
            "data":{
                "target":{
                    "language":config.TARGET_LANGUAGE,
                    "country":config.TARGET_COUNTRY
                },
            }
        }

def swapYourLanguageAndTargetLanguage(*args, **kwargs) -> dict:
    print("swapYourLanguageAndTargetLanguage")
    your_language = config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
    target_language = config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
    setYourLanguageAndCountry(target_language)
    setTargetLanguageAndCountry(your_language)
    return {"status":"success",
            "data":{
                "your":{"language":config.SOURCE_LANGUAGE,
                        "country":config.SOURCE_COUNTRY,
                        },
                "target":{
                    "language":config.TARGET_LANGUAGE,
                    "country":config.TARGET_COUNTRY,
                    },
                },
            }

def callbackSelectedLanguagePresetTab(selected_tab_no:str, *args, **kwargs) -> dict:
    print("callbackSelectedLanguagePresetTab", selected_tab_no)
    config.SELECTED_TAB_NO = selected_tab_no

    engines = config.SELECTED_TAB_YOUR_TRANSLATOR_ENGINES
    engine = engines[config.SELECTED_TAB_NO]
    config.CHOICE_INPUT_TRANSLATOR = engine

    engines = config.SELECTED_TAB_TARGET_TRANSLATOR_ENGINES
    engine = engines[config.SELECTED_TAB_NO]
    config.CHOICE_OUTPUT_TRANSLATOR = engine

    languages = config.SELECTED_TAB_YOUR_LANGUAGES
    select = languages[config.SELECTED_TAB_NO]
    config.SOURCE_LANGUAGE = select["language"]
    config.SOURCE_COUNTRY = select["country"]

    languages = config.SELECTED_TAB_TARGET_LANGUAGES
    select = languages[config.SELECTED_TAB_NO]
    config.TARGET_LANGUAGE = select["language"]
    config.TARGET_COUNTRY = select["country"]
    updateTranslationEngineAndEngineList()
    return {"status":"success", "data":config.SELECTED_TAB_NO}

def callbackSelectedTranslationEngine(selected_translation_engine:str, *args, **kwargs) -> dict:
    print("callbackSelectedTranslationEngine", selected_translation_engine)
    setYourTranslateEngine(selected_translation_engine)
    setTargetTranslateEngine(selected_translation_engine)
    return {"status":"success", "data":selected_translation_engine}

# command func
def callbackEnableTranslation(*args, **kwargs) -> dict:
    print("callbackEnableTranslation")
    config.ENABLE_TRANSLATION = True
    if model.isLoadedCTranslate2Model() is False:
        model.changeTranslatorCTranslate2Model()
    return {"status":"success", "data":config.ENABLE_TRANSLATION}

def callbackDisableTranslation(*args, **kwargs) -> dict:
    print("callbackDisableTranslation")
    config.ENABLE_TRANSLATION = False
    return {"status":"success", "data":config.ENABLE_TRANSLATION}

def callbackEnableTranscriptionSend(data, action, *args, **kwargs) -> dict:
    print("callbackEnableTranscriptionSend")
    config.ENABLE_TRANSCRIPTION_SEND = True
    startThreadingTranscriptionSendMessage(action)
    return {"status":"success", "data":config.ENABLE_TRANSCRIPTION_SEND}

def callbackDisableTranscriptionSend(data, action, *args, **kwargs) -> dict:
    config.ENABLE_TRANSCRIPTION_SEND = False
    stopThreadingTranscriptionSendMessage(action)
    return {"status":"success", "data":config.ENABLE_TRANSCRIPTION_SEND}

def callbackEnableTranscriptionReceive(data, action, *args, **kwargs) -> dict:
    config.ENABLE_TRANSCRIPTION_RECEIVE = True
    startThreadingTranscriptionReceiveMessage(action)

    if config.ENABLE_OVERLAY_SMALL_LOG is True:
        if model.overlay.initialized is False and model.overlay.checkSteamvrRunning() is True:
            model.startOverlay()
    return {"status":"success", "data":config.ENABLE_TRANSCRIPTION_RECEIVE}

def callbackDisableTranscriptionReceive(data, action, *args, **kwargs) -> dict:
    config.ENABLE_TRANSCRIPTION_RECEIVE = False
    stopThreadingTranscriptionReceiveMessage(action)
    return {"status":"success", "data":config.ENABLE_TRANSCRIPTION_RECEIVE}

def callbackEnableForeground(*args, **kwargs) -> dict:
    config.ENABLE_FOREGROUND = True
    return {"status":"success", "data":config.ENABLE_FOREGROUND}

def callbackDisableForeground(*args, **kwargs) -> dict:
    config.ENABLE_FOREGROUND = False
    return {"status":"success", "data":config.ENABLE_FOREGROUND}

def callbackEnableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
    config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
    return {"status":"success", "data":config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

def callbackDisableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
    config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
    return {"status":"success", "data":config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

# Config Window
def callbackOpenConfigWindow(*args, **kwargs) -> dict:
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        stopThreadingTranscriptionSendMessageOnOpenConfigWindow()
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        stopThreadingTranscriptionReceiveMessageOnOpenConfigWindow()
    return {"status":"success"}

def callbackCloseConfigWindow(data, action, *args, **kwargs) -> dict:
    model.stopCheckMicEnergy()
    model.stopCheckSpeakerEnergy()

    if config.ENABLE_TRANSCRIPTION_SEND is True:
        startThreadingTranscriptionSendMessageOnCloseConfigWindow(action)
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            sleep(2)
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        startThreadingTranscriptionReceiveMessageOnCloseConfigWindow(action)
    return {"status":"success"}

# Compact Mode Switch
def callbackEnableConfigWindowCompactMode(*args, **kwargs) -> dict:
    config.IS_CONFIG_WINDOW_COMPACT_MODE = True
    model.stopCheckMicEnergy()
    model.stopCheckSpeakerEnergy()
    return {"status":"success", "data":config.IS_CONFIG_WINDOW_COMPACT_MODE}

def callbackDisableConfigWindowCompactMode(*args, **kwargs) -> dict:
    config.IS_CONFIG_WINDOW_COMPACT_MODE = False
    model.stopCheckMicEnergy()
    model.stopCheckSpeakerEnergy()
    return {"status":"success", "data":config.IS_CONFIG_WINDOW_COMPACT_MODE}

# Appearance Tab
def callbackSetTransparency(data, *args, **kwargs) -> dict:
    print("callbackSetTransparency", int(data))
    config.TRANSPARENCY = int(data)
    return {"status":"success", "data":config.TRANSPARENCY}

def callbackSetAppearance(data, *args, **kwargs) -> dict:
    print("callbackSetAppearance", data)
    config.APPEARANCE_THEME = data
    return {"status":"success", "data":config.APPEARANCE_THEME}

def callbackSetUiScaling(data, *args, **kwargs) -> dict:
    print("callbackSetUiScaling", data)
    config.UI_SCALING = data
    return {"status":"success", "data":config.UI_SCALING}

def callbackSetTextboxUiScaling(data, *args, **kwargs) -> dict:
    print("callbackSetTextboxUiScaling", int(data))
    config.TEXTBOX_UI_SCALING = int(data)
    return {"status":"success", "data":config.TEXTBOX_UI_SCALING}

def callbackSetMessageBoxRatio(data, *args, **kwargs) -> dict:
    print("callbackSetMessageBoxRatio", int(data))
    config.MESSAGE_BOX_RATIO = int(data)
    return {"status":"success", "data":config.MESSAGE_BOX_RATIO}

def callbackSetFontFamily(data, *args, **kwargs) -> dict:
    print("callbackSetFontFamily", data)
    config.FONT_FAMILY = data
    return {"status":"success", "data":config.FONT_FAMILY}

def callbackSetUiLanguage(data, *args, **kwargs) -> dict:
    print("callbackSetUiLanguage", data)
    data = getKeyByValue(config.SELECTABLE_UI_LANGUAGES_DICT, data)
    print("callbackSetUiLanguage__after_getKeyByValue", data)
    config.UI_LANGUAGE = data
    return {"status":"success", "data":config.UI_LANGUAGE}

def callbackSetEnableRestoreMainWindowGeometry(data, *args, **kwargs) -> dict:
    print("callbackSetEnableRestoreMainWindowGeometry", data)
    config.ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY = data
    return {"status":"success", "data":config.ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY}

# Translation Tab
def callbackSetUseTranslationFeature(data, *args, **kwargs) -> dict:
    print("callbackSetUseTranslationFeature", data)
    config.USE_TRANSLATION_FEATURE = data
    if config.USE_TRANSLATION_FEATURE is True:
        if model.checkCTranslatorCTranslate2ModelWeight():
            config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = False
            def callback():
                model.changeTranslatorCTranslate2Model()
            th_callback = Thread(target=callback)
            th_callback.daemon = True
            th_callback.start()
        else:
            config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = True
    else:
        config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION = False
    return {"status":"success",
            "data":{
                "feature":config.USE_TRANSLATION_FEATURE,
                "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION,
                },
            }

def callbackSetCtranslate2WeightType(data, *args, **kwargs) -> dict:
    print("callbackSetCtranslate2WeightType", data)
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
    return {"status":"success",
            "data":{
                "feature":config.CTRANSLATE2_WEIGHT_TYPE,
                "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION,
                },
            }

def callbackSetDeeplAuthKey(data, *args, **kwargs) -> dict:
    status = "error"
    print("callbackSetDeeplAuthKey", str(data))
    if len(data) == 36 or len(data) == 39:
        result = model.authenticationTranslatorDeepLAuthKey(auth_key=data)
        if result is True:
            key = data
            status = "success"
        else:
            key = None
        auth_keys = config.AUTH_KEYS
        auth_keys["DeepL_API"] = key
        config.AUTH_KEYS = auth_keys
        updateTranslationEngineAndEngineList()
    return {"status":status, "data":config.AUTH_KEYS["DeepL_API"]}

def callbackClearDeeplAuthKey(*args, **kwargs) -> dict:
    auth_keys = config.AUTH_KEYS
    auth_keys["DeepL_API"] = None
    config.AUTH_KEYS = auth_keys
    updateTranslationEngineAndEngineList()
    return {"status":"success", "data":config.AUTH_KEYS["DeepL_API"]}

# Transcription Tab
# Transcription (Mic)
def callbackSetMicHost(data, *args, **kwargs) -> dict:
    print("callbackSetMicHost", data)
    config.CHOICE_MIC_HOST = data
    config.CHOICE_MIC_DEVICE = model.getInputDefaultDevice()
    model.stopCheckMicEnergy()
    return {"status":"success",
            "data":{
                "host":config.CHOICE_MIC_HOST,
                "device":config.CHOICE_MIC_DEVICE,
                },
            }

def callbackSetMicDevice(data, *args, **kwargs) -> dict:
    print("callbackSetMicDevice", data)
    config.CHOICE_MIC_DEVICE = data
    model.stopCheckMicEnergy()
    return {"status":"success",
            "data":{
                "host":config.CHOICE_MIC_HOST,
                },
            }

def callbackSetMicEnergyThreshold(data, *args, **kwargs) -> dict:
    status = "error"
    print("callbackSetMicEnergyThreshold", data)
    data = int(data)
    if 0 <= data <= config.MAX_MIC_ENERGY_THRESHOLD:
        config.INPUT_MIC_ENERGY_THRESHOLD = data
        status = "success"
    return {"status": status, "data": config.INPUT_MIC_ENERGY_THRESHOLD}

def callbackSetMicDynamicEnergyThreshold(data, *args, **kwargs) -> dict:
    print("callbackSetMicDynamicEnergyThreshold", data)
    config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = data
    return {"status":"success", "data":config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD}

class ProgressBarEnergy:
    def __init__(self, action):
        self.action = action

    def set(self, energy) -> None:
        self.action("energy", {"status":"success", "energy":energy})

def callbackEnableCheckMicThreshold(data, action, *args, **kwargs) -> dict:
    print("callbackEnableCheckMicThreshold")
    progressbar_mic_energy = ProgressBarEnergy(action)
    model.startCheckMicEnergy(progressbar_mic_energy.set)
    return {"status":"success"}

def callbackDisableCheckMicThreshold(*args, **kwargs) -> dict:
    print("callbackDisableCheckMicThreshold")
    model.stopCheckMicEnergy()
    return {"status":"success"}

def callbackSetMicRecordTimeout(data, *args, **kwargs) -> dict:
    print("callbackSetMicRecordTimeout", data)
    try:
        data = int(data)
        if 0 <= data <= config.INPUT_MIC_PHRASE_TIMEOUT:
            config.INPUT_MIC_RECORD_TIMEOUT = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":"error", "message":"Error Mic Record Timeout"}
    else:
        response = {"status":"success", "data":config.INPUT_MIC_RECORD_TIMEOUT}
    return response

def callbackSetMicPhraseTimeout(data, *args, **kwargs) -> dict:
    print("callbackSetMicPhraseTimeout", data)
    try:
        data = int(data)
        if data >= config.INPUT_MIC_RECORD_TIMEOUT:
            config.INPUT_MIC_PHRASE_TIMEOUT = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":"error", "message":"Error Mic Phrase Timeout"}
    else:
        response = {"status":"success", "data":config.INPUT_MIC_PHRASE_TIMEOUT}
    return response

def callbackSetMicMaxPhrases(data, *args, **kwargs) -> dict:
    print("callbackSetMicMaxPhrases", data)
    try:
        data = int(data)
        if 0 <= data:
            config.INPUT_MIC_MAX_PHRASES = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":"error", "message":"Error Mic Max Phrases"}
    else:
        response = {"status":"success", "data":config.INPUT_MIC_MAX_PHRASES}
    return response

def callbackSetMicWordFilter(data, *args, **kwargs) -> dict:
    print("callbackSetMicWordFilter", data)
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
    return {"status":"success", "data":config.INPUT_MIC_WORD_FILTER}

def callbackDeleteMicWordFilter(data, *args, **kwargs) -> dict:
    print("callbackDeleteMicWordFilter", data)
    try:
        new_input_mic_word_filter_list = config.INPUT_MIC_WORD_FILTER
        new_input_mic_word_filter_list.remove(str(data))
        config.INPUT_MIC_WORD_FILTER = new_input_mic_word_filter_list
        model.resetKeywordProcessor()
        model.addKeywords()
    except Exception:
        print("There was no the target word in config.INPUT_MIC_WORD_FILTER")
    return {"status":"success", "data":config.INPUT_MIC_WORD_FILTER}

# Transcription (Speaker)
def callbackSetSpeakerDevice(data, *args, **kwargs) -> dict:
    print("callbackSetSpeakerDevice", data)
    config.CHOICE_SPEAKER_DEVICE = data
    model.stopCheckSpeakerEnergy()
    return {"status":"success", "data":config.CHOICE_SPEAKER_DEVICE}

def callbackSetSpeakerEnergyThreshold(data, *args, **kwargs) -> dict:
    print("callbackSetSpeakerEnergyThreshold", data)
    try:
        data = int(data)
        if 0 <= data <= config.MAX_SPEAKER_ENERGY_THRESHOLD:
            # view.clearNotificationMessage()
            config.INPUT_SPEAKER_ENERGY_THRESHOLD = data
            # view.setGuiVariable_SpeakerEnergyThreshold(config.INPUT_SPEAKER_ENERGY_THRESHOLD)
        else:
            raise ValueError()
    except Exception:
        response = {"status":"error", "message":"Error Set Speaker Energy Threshold"}
    else:
        response = {"status":"success", "data":config.INPUT_SPEAKER_ENERGY_THRESHOLD}
    return response

def callbackSetSpeakerDynamicEnergyThreshold(data, *args, **kwargs) -> dict:
    print("callbackSetSpeakerDynamicEnergyThreshold", data)
    config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = data
    return {"status":"success", "data":config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD}

def callbackEnableCheckSpeakerThreshold(data, action, *args, **kwargs) -> dict:
    print("callbackEnableCheckSpeakerThreshold")
    progressbar_speaker_energy = ProgressBarEnergy(action)
    model.startCheckSpeakerEnergy(progressbar_speaker_energy.set)
    return {"status":"success"}

def callbackDisableCheckSpeakerThreshold(*args, **kwargs) -> dict:
    print("callbackDisableCheckSpeakerThreshold")
    model.stopCheckSpeakerEnergy()
    return {"status":"success"}

def callbackSetSpeakerRecordTimeout(data, *args, **kwargs) -> dict:
    print("callbackSetSpeakerRecordTimeout", data)
    try:
        data = int(data)
        if 0 <= data <= config.INPUT_SPEAKER_PHRASE_TIMEOUT:
            config.INPUT_SPEAKER_RECORD_TIMEOUT = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":"error", "message":"Error Speaker Record Timeout"}
    else:
        response = {"status":"success", "data":config.INPUT_SPEAKER_RECORD_TIMEOUT}
    return response

def callbackSetSpeakerPhraseTimeout(data, *args, **kwargs) -> dict:
    print("callbackSetSpeakerPhraseTimeout", data)
    try:
        data = int(data)
        if 0 <= data and data >= config.INPUT_SPEAKER_RECORD_TIMEOUT:
            config.INPUT_SPEAKER_PHRASE_TIMEOUT = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":"error", "message":"Error Speaker Phrase Timeout"}
    else:
        response = {"status":"success", "data":config.INPUT_SPEAKER_PHRASE_TIMEOUT}
    return response

def callbackSetSpeakerMaxPhrases(data, *args, **kwargs) -> dict:
    print("callbackSetSpeakerMaxPhrases", data)
    try:
        data = int(data)
        if 0 <= data:
            config.INPUT_SPEAKER_MAX_PHRASES = data
        else:
            raise ValueError()
    except Exception:
        response = {"status":"error", "message":"Error Speaker Max Phrases"}
    else:
        response = {"status":"success", "data":config.INPUT_SPEAKER_MAX_PHRASES}
    return response

# Transcription (Internal AI Model)
def callbackSetUserWhisperFeature(data, *args, **kwargs) -> dict:
    print("callbackSetUserWhisperFeature", data)
    config.USE_WHISPER_FEATURE = data
    if config.USE_WHISPER_FEATURE is True:
        if model.checkTranscriptionWhisperModelWeight() is True:
            config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = False
            config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        else:
            config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = True
            config.SELECTED_TRANSCRIPTION_ENGINE = "Google"
    else:
        config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = False
        config.SELECTED_TRANSCRIPTION_ENGINE = "Google"
    return {"status":"success",
            "data":{
                "feature":config.USE_WHISPER_FEATURE,
                "transcription_engine":config.SELECTED_TRANSCRIPTION_ENGINE,
                "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER,
                },
            }

def callbackSetWhisperWeightType(data, *args, **kwargs) -> dict:
    print("callbackSetWhisperWeightType", data)
    config.WHISPER_WEIGHT_TYPE = str(data)
    if model.checkTranscriptionWhisperModelWeight() is True:
        config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = False
        config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
    else:
        config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER = True
        config.SELECTED_TRANSCRIPTION_ENGINE = "Google"
    return {"status":"success",
            "data":{
                "weight_type":config.WHISPER_WEIGHT_TYPE,
                "transcription_engine":config.SELECTED_TRANSCRIPTION_ENGINE,
                "reset":config.IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER,
            }
        }

# VR Tab
def callbackSetOverlaySettingsOpacity(data, *args, **kwargs) -> dict:
    print("callbackSetOverlaySettingsOpacity", data)
    pre_settings = config.OVERLAY_SETTINGS
    pre_settings["opacity"] = data
    config.OVERLAY_SETTINGS = pre_settings
    model.updateOverlayImageOpacity()
    return {"status":"success", "data":config.OVERLAY_SETTINGS["opacity"]}

def callbackSetOverlaySettingsUiScaling(data, *args, **kwargs) -> dict:
    print("callbackSetOverlaySettingsUiScaling", data)
    pre_settings = config.OVERLAY_SETTINGS
    pre_settings["ui_scaling"] = data
    config.OVERLAY_SETTINGS = pre_settings
    model.updateOverlayImageUiScaling()
    return {"status":"success", "data":config.OVERLAY_SETTINGS["ui_scaling"]}

def callbackEnableOverlaySmallLog(data, *args, **kwargs) -> dict:
    print("callbackEnableOverlaySmallLog", data)
    config.ENABLE_OVERLAY_SMALL_LOG = data

    if config.ENABLE_OVERLAY_SMALL_LOG is True and config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        if model.overlay.initialized is False and model.overlay.checkSteamvrRunning() is True:
            model.startOverlay()
    return {"status":"success", "data":config.ENABLE_OVERLAY_SMALL_LOG}

def callbackDisableOverlaySmallLog(data, *args, **kwargs) -> dict:
    print("callbackDisableOverlaySmallLog", data)
    config.ENABLE_OVERLAY_SMALL_LOG = data
    if config.ENABLE_OVERLAY_SMALL_LOG is False:
        model.clearOverlayImage()
        model.shutdownOverlay()
    return {"status":"success", "data":config.ENABLE_OVERLAY_SMALL_LOG}

def callbackSetOverlaySmallLogSettings(value, set_type:str):
    print("callbackSetOverlaySmallLogSettings", value, set_type)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings[set_type] = value
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    match (set_type):
        case "x_pos" | "y_pos" | "z_pos" | "x_rotation" | "y_rotation" | "z_rotation":
            model.updateOverlayPosition()
        case "display_duration" | "fadeout_duration":
            model.updateOverlayTimes()

def callbackSetOverlaySmallLogSettingsXPos(data, *args, **kwargs) -> dict:
    print("callbackSetOverlaySmallLogSettingsXPos", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["x_pos"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":"success", "data":config.OVERLAY_SMALL_LOG_SETTINGS["x_pos"]}

def callbackSetOverlaySmallLogSettingsYPos(data, *args, **kwargs) -> dict:
    print("callbackSetOverlaySmallLogSettingsYPos", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["y_pos"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":"success", "data":config.OVERLAY_SMALL_LOG_SETTINGS["y_pos"]}

def callbackSetOverlaySmallLogSettingsZPos(data, *args, **kwargs) -> dict:
    print("callbackSetOverlaySmallLogSettingsZPos", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["z_pos"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":"success", "data":config.OVERLAY_SMALL_LOG_SETTINGS["z_pos"]}

def callbackSetOverlaySmallLogSettingsXRotation(data, *args, **kwargs) -> dict:
    print("callbackSetOverlaySmallLogSettingsXRotation", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["x_rotation"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":"success", "data":config.OVERLAY_SMALL_LOG_SETTINGS["x_rotation"]}

def callbackSetOverlaySmallLogSettingsYRotation(data, *args, **kwargs) -> dict:
    print("callbackSetOverlaySmallLogSettingsYRotation", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["y_rotation"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":"success", "data":config.OVERLAY_SMALL_LOG_SETTINGS["y_rotation"]}

def callbackSetOverlaySmallLogSettingsZRotation(data, *args, **kwargs) -> dict:
    print("callbackSetOverlaySmallLogSettingsZRotation", data)
    pre_settings = config.OVERLAY_SMALL_LOG_SETTINGS
    pre_settings["z_rotation"] = data
    config.OVERLAY_SMALL_LOG_SETTINGS = pre_settings
    model.updateOverlayPosition()
    return {"status":"success", "data":config.OVERLAY_SMALL_LOG_SETTINGS["z_rotation"]}

# Others Tab
def callbackSetEnableAutoClearMessageBox(data, *args, **kwargs) -> dict:
    print("callbackSetEnableAutoClearMessageBox", data)
    config.ENABLE_AUTO_CLEAR_MESSAGE_BOX = data
    return {"status":"success", "data":config.ENABLE_AUTO_CLEAR_MESSAGE_BOX}

def callbackSetEnableSendOnlyTranslatedMessages(data, *args, **kwargs) -> dict:
    print("callbackSetEnableSendOnlyTranslatedMessages", data)
    config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES = data
    return {"status":"success", "data":config.ENABLE_SEND_ONLY_TRANSLATED_MESSAGES}

def callbackSetSendMessageButtonType(data, *args, **kwargs) -> dict:
    print("callbackSetSendMessageButtonType", data)
    config.SEND_MESSAGE_BUTTON_TYPE = data
    return {"status":"success", "data":config.SEND_MESSAGE_BUTTON_TYPE}

def callbackEnableNoticeXsoverlay(*args, **kwargs) -> dict:
    print("callbackEnableNoticeXsoverlay")
    config.ENABLE_NOTICE_XSOVERLAY = True
    return {"status":"success", "data":config.ENABLE_NOTICE_XSOVERLAY}

def callbackDisableNoticeXsoverlay(*args, **kwargs) -> dict:
    print("callbackDisableNoticeXsoverlay")
    config.ENABLE_NOTICE_XSOVERLAY = False
    return {"status":"success", "data":config.ENABLE_NOTICE_XSOVERLAY}

def callbackEnableAutoExportMessageLogs(*args, **kwargs) -> dict:
    print("callbackEnableAutoExportMessageLogs")
    config.ENABLE_LOGGER = True
    model.startLogger()

def callbackDisableAutoExportMessageLogs(*args, **kwargs) -> dict:
    print("callbackDisableAutoExportMessageLogs")
    config.ENABLE_LOGGER = False
    model.stopLogger()

def callbackEnableVrcMicMuteSync(*args, **kwargs) -> dict:
    print("callbackEnableVrcMicMuteSync")
    config.ENABLE_VRC_MIC_MUTE_SYNC = True
    model.startCheckMuteSelfStatus()
    model.changeMicTranscriptStatus()

def callbackDisableVrcMicMuteSync(*args, **kwargs) -> dict:
    print("callbackDisableVrcMicMuteSync")
    config.ENABLE_VRC_MIC_MUTE_SYNC = False
    model.stopCheckMuteSelfStatus()
    model.changeMicTranscriptStatus()

def callbackEnableSendMessageToVrc(*args, **kwargs) -> dict:
    print("callbackEnableSendMessageToVrc")
    config.ENABLE_SEND_MESSAGE_TO_VRC = True
    return {"status":"success", "data":config.ENABLE_SEND_MESSAGE_TO_VRC}

def callbackDisableSendMessageToVrc(*args, **kwargs) -> dict:
    print("callbackSetEnableSendMessageToVrc")
    config.ENABLE_SEND_MESSAGE_TO_VRC = False
    return {"status":"success", "data":config.ENABLE_SEND_MESSAGE_TO_VRC}

# Others (Message Formats(Send)
def callbackSetSendMessageFormat(data, *args, **kwargs) -> dict:
    print("callbackSetSendMessageFormat", data)
    if isUniqueStrings(["[message]"], data) is True:
        config.SEND_MESSAGE_FORMAT = data
    return {"status":"success", "data":config.SEND_MESSAGE_FORMAT}

def callbackSetSendMessageFormatWithT(data, *args, **kwargs) -> dict:
    print("callbackSetSendMessageFormatWithT", data)
    if len(data) > 0:
        if isUniqueStrings(["[message]", "[translation]"], data) is True:
            config.SEND_MESSAGE_FORMAT_WITH_T = data
    return {"status":"success", "data":config.SEND_MESSAGE_FORMAT_WITH_T}

# Others (Message Formats(Received)
def callbackSetReceivedMessageFormat(data, *args, **kwargs) -> dict:
    print("callbackSetReceivedMessageFormat", data)
    if isUniqueStrings(["[message]"], data) is True:
        config.RECEIVED_MESSAGE_FORMAT = data
    return {"status":"success", "data":config.RECEIVED_MESSAGE_FORMAT}

def callbackSetReceivedMessageFormatWithT(data, *args, **kwargs) -> dict:
    print("callbackSetReceivedMessageFormatWithT", data)
    if len(data) > 0:
        if isUniqueStrings(["[message]", "[translation]"], data) is True:
            config.RECEIVED_MESSAGE_FORMAT_WITH_T = data
    return {"status":"success", "data":config.RECEIVED_MESSAGE_FORMAT_WITH_T}

# ---------------------Speaker2Chatbox---------------------
def callbackEnableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
    print("callbackEnableSendReceivedMessageToVrc")
    config.ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC = True
    return {"status":"success", "data":config.ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC}

def callbackDisableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
    print("callbackDisableSendReceivedMessageToVrc")
    config.ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC = False
    return {"status":"success", "data":config.ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC}
# ---------------------Speaker2Chatbox---------------------

# Advanced Settings Tab
def callbackSetOscIpAddress(data, *args, **kwargs) -> dict:
    print("callbackSetOscIpAddress", str(data))
    config.OSC_IP_ADDRESS = str(data)
    return {"status":"success", "data":config.OSC_IP_ADDRESS}

def callbackSetOscPort(data, *args, **kwargs) -> dict:
    print("callbackSetOscPort", int(data))
    config.OSC_PORT = int(data)
    return {"status":"success", "data":config.OSC_PORT}

def getListLanguageAndCountry():
    return model.getListLanguageAndCountry()

def getListInputHost():
    return model.getListInputHost()

def getListInputDevice():
    return model.getListInputDevice()

def getListOutputDevice():
    return model.getListOutputDevice()

def init():
    initSetTranslateEngine()
    initSetLanguageAndCountry()

    if config.AUTH_KEYS["DeepL_API"] is not None:
        if model.authenticationTranslatorDeepLAuthKey(auth_key=config.AUTH_KEYS["DeepL_API"]) is False:
            # error update Auth key
            auth_keys = config.AUTH_KEYS
            auth_keys["DeepL_API"] = None
            config.AUTH_KEYS = auth_keys

    # set Translation Engine
    updateTranslationEngineAndEngineList()

    # set Transcription Engine
    if config.USE_WHISPER_FEATURE is True:
        config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
    else:
        config.SELECTED_TRANSCRIPTION_ENGINE = "Google"

    # set word filter
    model.addKeywords()

    # check Software Updated
    if model.checkSoftwareUpdated() is True:
        # view.showUpdateAvailableButton()
        pass

    # init logger
    if config.ENABLE_LOGGER is True:
        model.startLogger()

    # init OSC receive
    model.startReceiveOSC()
    if config.ENABLE_VRC_MIC_MUTE_SYNC is True:
        model.startCheckMuteSelfStatus()

# def initSetConfigByExeArguments():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--ip")
#     parser.add_argument("--port")
#     args = parser.parse_args()
#     if args.ip is not None:
#         config.OSC_IP_ADDRESS = str(args.ip)
#         # view.setGuiVariable_OscIpAddress(config.OSC_IP_ADDRESS)
#     if args.port is not None:
#         config.OSC_PORT = int(args.port)
#         # view.setGuiVariable_OscPort(config.OSC_PORT)

# def createMainWindow(splash):
#     splash.toProgress(1)
#     # create GUI
#     # view.createGUI()
#     splash.toProgress(2)

#     # init config
#     initSetConfigByExeArguments()
#     initSetTranslateEngine()
#     initSetLanguageAndCountry()

#     if config.AUTH_KEYS["DeepL_API"] is not None:
#         if model.authenticationTranslatorDeepLAuthKey(auth_key=config.AUTH_KEYS["DeepL_API"]) is False:
#             # error update Auth key
#             auth_keys = config.AUTH_KEYS
#             auth_keys["DeepL_API"] = None
#             config.AUTH_KEYS = auth_keys
#             # view.printToTextbox_AuthenticationError()

#     # set Translation Engine
#     updateTranslationEngineAndEngineList()

#     # set Transcription Engine
#     if config.USE_WHISPER_FEATURE is True:
#         config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
#     else:
#         config.SELECTED_TRANSCRIPTION_ENGINE = "Google"

#     # set word filter
#     model.addKeywords()

#     # check Software Updated
#     if model.checkSoftwareUpdated() is True:
#         # view.showUpdateAvailableButton()
#         pass

#     # init logger
#     if config.ENABLE_LOGGER is True:
#         model.startLogger()

#     # init OSC receive
#     model.startReceiveOSC()
#     if config.ENABLE_VRC_MIC_MUTE_SYNC is True:
#         model.startCheckMuteSelfStatus()

#     splash.toProgress(3) # Last one.

    # set UI and callback
    # view.register(
    #     common_registers={
    #         "callback_enable_easter_egg": callbackEnableEasterEgg,

    #         "callback_update_software": callbackUpdateSoftware,
    #         "callback_restart_software": callbackRestartSoftware,
    #         "callback_filepath_logs": callbackFilepathLogs,
    #         "callback_filepath_config_file": callbackFilepathConfigFile,
    #         "callback_quit_vrct": callbackQuitVrct,
    #     },

    #     window_action_registers={
    #         "callback_open_config_window": callbackOpenConfigWindow,
    #         "callback_close_config_window": callbackCloseConfigWindow,
    #     },

    #     main_window_registers={
    #         "callback_enable_main_window_sidebar_compact_mode": callbackEnableMainWindowSidebarCompactMode,
    #         "callback_disable_main_window_sidebar_compact_mode": callbackDisableMainWindowSidebarCompactMode,

    #         "callback_toggle_translation": callbackToggleTranslation,
    #         "callback_toggle_transcription_send": callbackToggleTranscriptionSend,
    #         "callback_toggle_transcription_receive": callbackToggleTranscriptionReceive,
    #         "callback_toggle_foreground": callbackToggleForeground,

    #         "callback_your_language": setYourLanguageAndCountry,
    #         "callback_target_language": setTargetLanguageAndCountry,
    #         "values": model.getListLanguageAndCountry(),
    #         "callback_swap_languages": swapYourLanguageAndTargetLanguage,

    #         "callback_selected_language_preset_tab": callbackSelectedLanguagePresetTab,

    #         "callback_selected_translation_engine": callbackSelectedTranslationEngine,

    #         "message_box_bind_Return": messageBoxPressKeyEnter,
    #         "message_box_bind_Any_KeyPress": messageBoxPressKeyAny,
    #         "message_box_bind_FocusIn": messageBoxFocusIn,
    #         "message_box_bind_FocusOut": messageBoxFocusOut,
    #         "message_box_bind_Up_KeyPress": messageBoxUpKeyPress,
    #         "message_box_bind_Down_KeyPress": messageBoxDownKeyPress,
    #     },

    #     config_window_registers={
    #         # Compact Mode Switch
    #         "callback_disable_config_window_compact_mode": callbackEnableConfigWindowCompactMode,
    #         "callback_enable_config_window_compact_mode": callbackDisableConfigWindowCompactMode,

    #         # Appearance Tab
    #         "callback_set_transparency": callbackSetTransparency,
    #         "callback_set_appearance": callbackSetAppearance,
    #         "callback_set_ui_scaling": callbackSetUiScaling,
    #         "callback_set_textbox_ui_scaling": callbackSetTextboxUiScaling,
    #         "callback_set_message_box_ratio": callbackSetMessageBoxRatio,
    #         "callback_set_font_family": callbackSetFontFamily,
    #         "callback_set_ui_language": callbackSetUiLanguage,
    #         "callback_set_enable_restore_main_window_geometry": callbackSetEnableRestoreMainWindowGeometry,

    #         # Translation Tab
    #         "callback_set_use_translation_feature": callbackSetUseTranslationFeature,
    #         "callback_set_ctranslate2_weight_type": callbackSetCtranslate2WeightType,
    #         "callback_set_deepl_auth_key": callbackSetDeeplAuthKey,

    #         # Transcription Tab (Mic)
    #         "callback_set_mic_host": callbackSetMicHost,
    #         "list_mic_host": model.getListInputHost(),
    #         "callback_set_mic_device": callbackSetMicDevice,
    #         "list_mic_device": model.getListInputDevice(),
    #         "callback_set_mic_energy_threshold": callbackSetMicEnergyThreshold,
    #         "callback_set_mic_dynamic_energy_threshold": callbackSetMicDynamicEnergyThreshold,
    #         "callback_check_mic_threshold": callbackCheckMicThreshold,
    #         "callback_set_mic_record_timeout": callbackSetMicRecordTimeout,
    #         "callback_set_mic_phrase_timeout": callbackSetMicPhraseTimeout,
    #         "callback_set_mic_max_phrases": callbackSetMicMaxPhrases,
    #         "callback_set_mic_word_filter": callbackSetMicWordFilter,
    #         "callback_delete_mic_word_filter": callbackDeleteMicWordFilter,

    #         # Transcription Tab (Speaker)
    #         "callback_set_speaker_device": callbackSetSpeakerDevice,
    #         "list_speaker_device": model.getListOutputDevice(),
    #         "callback_set_speaker_energy_threshold": callbackSetSpeakerEnergyThreshold,
    #         "callback_set_speaker_dynamic_energy_threshold": callbackSetSpeakerDynamicEnergyThreshold,
    #         "callback_check_speaker_threshold": callbackCheckSpeakerThreshold,
    #         "callback_set_speaker_record_timeout": callbackSetSpeakerRecordTimeout,
    #         "callback_set_speaker_phrase_timeout": callbackSetSpeakerPhraseTimeout,
    #         "callback_set_speaker_max_phrases": callbackSetSpeakerMaxPhrases,

    #         # Transcription Tab (Internal AI Model)
    #         "callback_set_use_whisper_feature": callbackSetUserWhisperFeature,
    #         "callback_set_whisper_weight_type": callbackSetWhisperWeightType,

    #         # VR Tab
    #         "callback_set_overlay_settings": callbackSetOverlaySettings,
    #         "callback_set_enable_overlay_small_log": callbackSetEnableOverlaySmallLog,
    #         "callback_set_overlay_small_log_settings": callbackSetOverlaySmallLogSettings,

    #         # Others Tab
    #         "callback_set_enable_auto_clear_chatbox": callbackSetEnableAutoClearMessageBox,
    #         "callback_set_send_only_translated_messages": callbackSetEnableSendOnlyTranslatedMessages,
    #         "callback_set_send_message_button_type": callbackSetSendMessageButtonType,
    #         "callback_set_enable_notice_xsoverlay": callbackSetEnableNoticeXsoverlay,
    #         "callback_set_enable_auto_export_message_logs": callbackSetEnableAutoExportMessageLogs,
    #         "callback_set_enable_vrc_mic_mute_sync": callbackSetEnableVrcMicMuteSync,
    #         "callback_set_enable_send_message_to_vrc": callbackSetEnableSendMessageToVrc,
    #         # Others(Message Formats(Send)
    #         "callback_set_send_message_format": callbackSetSendMessageFormat,
    #         "callback_set_send_message_format_with_t": callbackSetSendMessageFormatWithT,
    #         # Others(Message Formats(Received)
    #         "callback_set_received_message_format": callbackSetReceivedMessageFormat,
    #         "callback_set_received_message_format_with_t": callbackSetReceivedMessageFormatWithT,

    #         # Speaker2Chatbox----------------
    #         "callback_set_enable_send_received_message_to_vrc": callbackSetEnableSendReceivedMessageToVrc,
    #         # Speaker2Chatbox----------------

    #         # Advanced Settings Tab
    #         "callback_set_osc_ip_address": callbackSetOscIpAddress,
    #         "callback_set_osc_port": callbackSetOscPort,
    #     },
    # )

# def showMainWindow():
#     view.startMainLoop()