from threading import Thread
from config import config
from model import model
from view import view

# func transcription send message
def sendMicMessage(message):
    if len(message) > 0:
        translation = ""
        if model.checkKeywords(message):
            view.printToTextbox_DetectedByWordFilter(detected_message=message)
            return
        elif config.ENABLE_TRANSLATION is False:
            pass
        elif model.getTranslatorStatus() is False:
            view.printToTextbox_AuthenticationError()
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
                view.printToTextbox_OSCError()

            view.printToTextbox_SentMessage(message, translation)

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
            view.printToTextbox_AuthenticationError()
        else:
            translation = model.getOutputTranslate(message)

        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            if config.ENABLE_NOTICE_XSOVERLAY is True:
                xsoverlay_message = config.MESSAGE_FORMAT.replace("[message]", message)
                xsoverlay_message = xsoverlay_message.replace("[translation]", translation)
                model.notificationXSOverlay(xsoverlay_message)
            view.printToTextbox_ReceivedMessage(message, translation)

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
            view.printToTextbox_AuthenticationError()
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
            view.printToTextbox_OSCError()

        # update textbox message log
        view.printToTextbox_SentMessage(message, translation)

        # delete message in entry message box
        if config.ENABLE_AUTO_CLEAR_CHATBOX is True:
            view.clearMessageBox()

def messageBoxPressKeyEnter(e):
    model.oscStopSendTyping()
    message = view.getTextFromMessageBox()
    sendChatMessage(message)

def messageBoxPressKeyAny(e):
    model.oscStartSendTyping()

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
    view.updateGuiVariableByPresetTabNo(config.SELECTED_TAB_NO)
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
    view.updateGuiVariableByPresetTabNo(config.SELECTED_TAB_NO)
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
    view.updateGuiVariableByPresetTabNo(config.SELECTED_TAB_NO)
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
        view.foregroundOn()
    else:
        view.printToTextbox_disableForeground()
        view.foregroundOff()


# Config Window
def callbackEnableConfigWindowCompactMode():
    config.IS_CONFIG_WINDOW_COMPACT_MODE = True
    view.reloadConfigWindowSettingBoxContainer()

def callbackDisableConfigWindowCompactMode():
    config.IS_CONFIG_WINDOW_COMPACT_MODE = False
    view.reloadConfigWindowSettingBoxContainer()

# create GUI
view.createGUI()

# init config
if model.authenticationTranslator() is False:
    # error update Auth key
    view.printToTextbox_AuthenticationError()

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

    # 辞書型で関数を渡しても上手く行かず、仕方なくタプルで渡してる。
    # 本当はコメントアウト（以下とview.py内33,34行目)しているようにできたらいいけど、
    # _tkinter.TclError: unknown option "-bind_Any_KeyPress"みたいにエラーがでる。
    entry_message_box=None,
    # entry_message_box={
    #     "bind_Return": messageBoxPressKeyEnter,
    #     "bind_Any_KeyPress": messageBoxPressKeyAny,
    # },
    entry_message_box_bind_Return=messageBoxPressKeyEnter,
    entry_message_box_bind_Any_KeyPress=messageBoxPressKeyAny,

    config_window={
        "callback_disable_config_window_compact_mode": callbackEnableConfigWindowCompactMode,
        "callback_enable_config_window_compact_mode": callbackDisableConfigWindowCompactMode,
    },
)

if __name__ == "__main__":
    view.startMainLoop()