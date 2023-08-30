from threading import Thread
import customtkinter
from vrct_gui import vrct_gui
from config import config
from model import model

from view import viewInitializer

# func transcription send message
def sendMicMessage(message):
    if len(message) > 0:
        translation = ""
        if model.checkKeywords(message):
            logDetectWordFilter(message)
            return
        elif config.ENABLE_TRANSLATION is False:
            pass
        elif model.getTranslatorStatus() is False:
            logAuthenticationError()
        else:
            translation = model.getInputTranslate(message)

        if config.ENABLE_TRANSCRIPTION_SEND is True:
            if config.ENABLE_OSC is True:
                if len(translation) > 0:
                    osc_message = config.MESSAGE_FORMAT.replace("[message]", message)
                    osc_message = osc_message.replace("[translation]", translation)
                else:
                    osc_message = message
                model.oscSendMessage(osc_message)
            else:
                logOSCError()

            logSendMessage(message, translation)

def startTranscriptionSendMessage():
    model.startMicTranscript(sendMicMessage)
    vrct_gui.changeMainWindowWidgetsStatus("normal", "All")

def stopTranscriptionSendMessage():
    model.stopMicTranscript()
    vrct_gui.changeMainWindowWidgetsStatus("normal", "All")

# func transcription receive message
def receiveSpeakerMessage(message):
    if len(message) > 0:
        translation = ""
        if config.ENABLE_TRANSLATION is False:
            pass
        elif model.getTranslatorStatus() is False:
            logAuthenticationError()
        else:
            translation = model.getOutputTranslate(message)

        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            if config.ENABLE_NOTICE_XSOVERLAY is True:
                xsoverlay_message = config.MESSAGE_FORMAT.replace("[message]", message)
                xsoverlay_message = xsoverlay_message.replace("[translation]", translation)
                model.notificationXSOverlay(xsoverlay_message)
            logReceiveMessage(message, translation)

def startTranscriptionReceiveMessage():
    model.startSpeakerTranscript(receiveSpeakerMessage)
    vrct_gui.changeMainWindowWidgetsStatus("normal", "All")

def stopTranscriptionReceiveMessage():
    model.stopSpeakerTranscript()
    vrct_gui.changeMainWindowWidgetsStatus("normal", "All")

# func message box
def sendChatMessage(message):
    if len(message) > 0:
        translation = ""
        if config.ENABLE_TRANSLATION is False:
            pass
        elif model.getTranslatorStatus() is False:
            logAuthenticationError()
        else:
            translation = model.getInputTranslate(message)

        # send OSC message
        if config.ENABLE_OSC is True:
            if len(translation) > 0:
                osc_message = config.MESSAGE_FORMAT.replace("[message]", message)
                osc_message = osc_message.replace("[translation]", translation)
            else:
                osc_message = message
            model.oscSendMessage(osc_message)
        else:
            logOSCError()

        # update textbox message log
        logSendMessage(message, translation)

        # delete message in entry message box
        if config.ENABLE_AUTO_CLEAR_CHATBOX is True:
            entry_message_box = getattr(vrct_gui, "entry_message_box")
            entry_message_box.delete(0, customtkinter.END)

def messageBoxPressKeyEnter(e):
    model.oscStopSendTyping()
    entry_message_box = getattr(vrct_gui, "entry_message_box")
    message = entry_message_box.get()
    sendChatMessage(message)

def messageBoxPressKeyAny(e):
    model.oscStartSendTyping()
    entry_message_box = getattr(vrct_gui, "entry_message_box")
    if e.keysym != "??":
        if len(e.char) != 0 and e.keysym in config.BREAK_KEYSYM_LIST:
            entry_message_box.insert("end", e.char)
            return "break"

# func select languages
def setYourLanguageAndCountry(select):
    languages = config.SELECTED_TAB_YOUR_LANGUAGES
    languages[config.SELECTED_TAB_NO] = select
    config.SELECTED_TAB_YOUR_LANGUAGES = languages
    language, country = model.getLanguageAndCountry(select)
    config.SOURCE_LANGUAGE = language
    config.SOURCE_COUNTRY = country
    config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)

def setTargetLanguageAndCountry(select):
    languages = config.SELECTED_TAB_TARGET_LANGUAGES
    languages[config.SELECTED_TAB_NO] = select
    config.SELECTED_TAB_TARGET_LANGUAGES = languages
    language, country = model.getLanguageAndCountry(select)
    config.TARGET_LANGUAGE = language
    config.TARGET_COUNTRY = country
    config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)

def callbackSelectedTabNo1():
    config.SELECTED_TAB_NO = "1"
    vrct_gui.YOUR_LANGUAGE = config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
    vrct_gui.TARGET_LANGUAGE = config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
    languages = config.SELECTED_TAB_YOUR_LANGUAGES
    select = languages[config.SELECTED_TAB_NO]
    language, country = model.getLanguageAndCountry(select)
    config.SOURCE_LANGUAGE = language
    config.SOURCE_COUNTRY = country
    languages = config.SELECTED_TAB_TARGET_LANGUAGES
    select = languages[config.SELECTED_TAB_NO]
    language, country = model.getLanguageAndCountry(select)
    config.TARGET_LANGUAGE = language
    config.TARGET_COUNTRY = country
    config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)

def callbackSelectedTabNo2():
    config.SELECTED_TAB_NO = "2"
    vrct_gui.YOUR_LANGUAGE = config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
    vrct_gui.TARGET_LANGUAGE = config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
    languages = config.SELECTED_TAB_YOUR_LANGUAGES
    select = languages[config.SELECTED_TAB_NO]
    language, country = model.getLanguageAndCountry(select)
    config.SOURCE_LANGUAGE = language
    config.SOURCE_COUNTRY = country
    languages = config.SELECTED_TAB_TARGET_LANGUAGES
    select = languages[config.SELECTED_TAB_NO]
    language, country = model.getLanguageAndCountry(select)
    config.TARGET_LANGUAGE = language
    config.TARGET_COUNTRY = country
    config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)

def callbackSelectedTabNo3():
    config.SELECTED_TAB_NO = "3"
    vrct_gui.YOUR_LANGUAGE = config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
    vrct_gui.TARGET_LANGUAGE = config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
    languages = config.SELECTED_TAB_YOUR_LANGUAGES
    select = languages[config.SELECTED_TAB_NO]
    language, country = model.getLanguageAndCountry(select)
    config.SOURCE_LANGUAGE = language
    config.SOURCE_COUNTRY = country
    languages = config.SELECTED_TAB_TARGET_LANGUAGES
    select = languages[config.SELECTED_TAB_NO]
    language, country = model.getLanguageAndCountry(select)
    config.TARGET_LANGUAGE = language
    config.TARGET_COUNTRY = country
    config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)

# func print textbox
def logTranslationStatusChange():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    if config.ENABLE_TRANSLATION is True:
        vrct_gui.printToTextbox(textbox_all, "翻訳機能をONにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "翻訳機能をONにしました", "", "INFO")
    else:
        vrct_gui.printToTextbox(textbox_all, "翻訳機能をOFFにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "翻訳機能をOFFにしました", "", "INFO")

def logTranscriptionSendStatusChange():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        vrct_gui.printToTextbox(textbox_all, "Voice2chatbox機能をONにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "Voice2chatbox機能をONにしました", "", "INFO")
    else:
        vrct_gui.printToTextbox(textbox_all, "Voice2chatbox機能をOFFにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "Voice2chatbox機能をOFFにしました", "", "INFO")

def logTranscriptionReceiveStatusChange():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        vrct_gui.printToTextbox(textbox_all, "Speaker2chatbox機能をONにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "Speaker2chatbox機能をONにしました", "", "INFO")
    else:
        vrct_gui.printToTextbox(textbox_all, "Speaker2chatbox機能をOFFにしました", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "Speaker2chatbox機能をOFFにしました", "", "INFO")

def logSendMessage(message, translate):
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_sent = getattr(vrct_gui, "textbox_sent")
    vrct_gui.printToTextbox(textbox_all, message, translate, "SEND")
    vrct_gui.printToTextbox(textbox_sent, message, translate, "SEND")

def logReceiveMessage(message, translate):
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_sent = getattr(vrct_gui, "textbox_received")
    vrct_gui.printToTextbox(textbox_all, message, translate, "RECEIVE")
    vrct_gui.printToTextbox(textbox_sent, message, translate, "RECEIVE")

def logDetectWordFilter(message):
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    vrct_gui.printToTextbox(textbox_all, f"Detect WordFilter :{message}", "", "INFO")
    vrct_gui.printToTextbox(textbox_system, f"Detect WordFilter :{message}", "", "INFO")

def logAuthenticationError():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    vrct_gui.printToTextbox(textbox_all, "Auth Key or language setting is incorrect", "", "INFO")
    vrct_gui.printToTextbox(textbox_system, "Auth Key or language setting is incorrect", "", "INFO")

def logOSCError():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    vrct_gui.printToTextbox(textbox_all, "OSC is not enabled, please enable OSC and rejoin", "", "INFO")
    vrct_gui.printToTextbox(textbox_system, "OSC is not enabled, please enable OSC and rejoin", "", "INFO")

def logForegroundStatusChange():
    textbox_all = getattr(vrct_gui, "textbox_all")
    textbox_system = getattr(vrct_gui, "textbox_system")
    if config.ENABLE_FOREGROUND is True:
        vrct_gui.printToTextbox(textbox_all, "Start foreground", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "Start foreground", "", "INFO")
    else:
        vrct_gui.printToTextbox(textbox_all, "Stop foreground", "", "INFO")
        vrct_gui.printToTextbox(textbox_system, "Stop foreground", "", "INFO")

# command func
def callbackToggleTranslation():
    config.ENABLE_TRANSLATION = getattr(vrct_gui, "translation_switch_box").get()
    logTranslationStatusChange()

def callbackToggleTranscriptionSend():
    vrct_gui.changeMainWindowWidgetsStatus("disabled", "All")
    config.ENABLE_TRANSCRIPTION_SEND = getattr(vrct_gui, "transcription_send_switch_box").get()
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        th_startTranscriptionSendMessage = Thread(target=startTranscriptionSendMessage)
        th_startTranscriptionSendMessage.daemon = True
        th_startTranscriptionSendMessage.start()
    else:
        th_stopTranscriptionSendMessage = Thread(target=stopTranscriptionSendMessage)
        th_stopTranscriptionSendMessage.daemon = True
        th_stopTranscriptionSendMessage.start()
    logTranscriptionSendStatusChange()

def callbackToggleTranscriptionReceive():
    vrct_gui.changeMainWindowWidgetsStatus("disabled", "All")
    config.ENABLE_TRANSCRIPTION_RECEIVE = getattr(vrct_gui, "transcription_receive_switch_box").get()
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        th_startTranscriptionReceiveMessage = Thread(target=startTranscriptionReceiveMessage)
        th_startTranscriptionReceiveMessage.daemon = True
        th_startTranscriptionReceiveMessage.start()
    else:
        th_stopTranscriptionReceiveMessage = Thread(target=stopTranscriptionReceiveMessage)
        th_stopTranscriptionReceiveMessage.daemon = True
        th_stopTranscriptionReceiveMessage.start()
    logTranscriptionReceiveStatusChange()

def callbackToggleForeground():
    config.ENABLE_FOREGROUND = getattr(vrct_gui, "foreground_switch_box").get()
    if config.ENABLE_FOREGROUND is True:
        vrct_gui.attributes("-topmost", True)
    else:
        vrct_gui.attributes("-topmost", False)
    logForegroundStatusChange()

# create GUI
vrct_gui.createGUI()

# init config
if model.authenticationTranslator() is False:
    # error update Auth key
    logAuthenticationError()

# set word filter
model.addKeywords()

# check OSC started
model.checkOSCStarted()

# check Software Updated
model.checkSoftwareUpdated()

# set UI and callback
viewInitializer(
    sidebar_features={
        "callback_toggle_translation": callbackToggleTranslation,
        "callback_toggle_transcription_send": callbackToggleTranscriptionSend,
        "callback_toggle_transcription_receive": callbackToggleTranscriptionReceive,
        "callback_toggle_foreground": callbackToggleForeground,
    },

    language_presets={
        "callback_your_language": setYourLanguageAndCountry,
        "callback_target_language": setTargetLanguageAndCountry,
        "values": model.getListLanguageAndCountry(),

        "callback_selected_tab_no_1": callbackSelectedTabNo1,
        "callback_selected_tab_no_2": callbackSelectedTabNo2,
        "callback_selected_tab_no_3": callbackSelectedTabNo3,
    },

    entry_message_box={
        "bind_Return": messageBoxPressKeyEnter,
        "bind_Any_KeyPress": messageBoxPressKeyAny,
    },
)

if __name__ == "__main__":
    vrct_gui.startMainLoop()