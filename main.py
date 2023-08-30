from threading import Thread
import customtkinter
from vrct_gui import vrct_gui
from config import config
from model import model
from customtkinter import StringVar
from view import view

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
    view.setMainWindowAllWidgetsStatusToNormal()

def stopTranscriptionSendMessage():
    model.stopMicTranscript()
    view.setMainWindowAllWidgetsStatusToNormal()

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
    view.setMainWindowAllWidgetsStatusToNormal()

def stopTranscriptionReceiveMessage():
    model.stopSpeakerTranscript()
    view.setMainWindowAllWidgetsStatusToNormal()

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
    message = view.getTextFromMessageBox()
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


# command func
def callbackToggleTranslation():
    config.ENABLE_TRANSLATION = view.getTranslationButtonStatus()
    if config.ENABLE_TRANSLATION is True:
        view.printToTextbox_enableTranslation()
    else:
        view.printToTextbox_disableTranslation()

def callbackToggleTranscriptionSend():
    view.setMainWindowAllWidgetsStatusToDisabled()
    config.ENABLE_TRANSCRIPTION_SEND = view.getTranscriptionSendButtonStatus()
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        view.printToTextbox_enableTranscriptionSend()
        th_startTranscriptionSendMessage = Thread(target=startTranscriptionSendMessage)
        th_startTranscriptionSendMessage.daemon = True
        th_startTranscriptionSendMessage.start()
    else:
        view.printToTextbox_disableTranscriptionSend()
        th_stopTranscriptionSendMessage = Thread(target=stopTranscriptionSendMessage)
        th_stopTranscriptionSendMessage.daemon = True
        th_stopTranscriptionSendMessage.start()

def callbackToggleTranscriptionReceive():
    view.setMainWindowAllWidgetsStatusToDisabled()
    config.ENABLE_TRANSCRIPTION_RECEIVE = view.getTranscriptionReceiveButtonStatus()
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        view.printToTextbox_enableTranscriptionReceive()
        th_startTranscriptionReceiveMessage = Thread(target=startTranscriptionReceiveMessage)
        th_startTranscriptionReceiveMessage.daemon = True
        th_startTranscriptionReceiveMessage.start()
    else:
        view.printToTextbox_disableTranscriptionReceive()
        th_stopTranscriptionReceiveMessage = Thread(target=stopTranscriptionReceiveMessage)
        th_stopTranscriptionReceiveMessage.daemon = True
        th_stopTranscriptionReceiveMessage.start()

def callbackToggleForeground():
    config.ENABLE_FOREGROUND = view.getForegroundButtonStatus()
    if config.ENABLE_FOREGROUND is True:
        view.printToTextbox_enableForeground()
        vrct_gui.attributes("-topmost", True)
    else:
        view.printToTextbox_disableForeground()
        vrct_gui.attributes("-topmost", False)

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
view.initializer(
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