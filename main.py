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
        if config.ENABLE_AUTO_CLEAR_MESSAGE_BOX is True:
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
# Compact Mode Switch
def callbackEnableConfigWindowCompactMode():
    config.IS_CONFIG_WINDOW_COMPACT_MODE = True
    view.reloadConfigWindowSettingBoxContainer()

def callbackDisableConfigWindowCompactMode():
    config.IS_CONFIG_WINDOW_COMPACT_MODE = False
    view.reloadConfigWindowSettingBoxContainer()

# Appearance Tab
def callbackSetTransparency(value):
    print("callbackSetTransparency", int(value))
    config.TRANSPARENCY = int(value)
    # self.parent.wm_attributes("-alpha", int(value/100))

def callbackSetAppearance(value):
    print("callbackSetAppearance", value)
    config.APPEARANCE_THEME = value

def callbackSetUiScaling(value):
    print("callbackSetUiScaling", value)
    config.UI_SCALING = value
    new_scaling_float = int(value.replace("%", "")) / 100
    print("callbackSetUiScaling_new_scaling_float", new_scaling_float)

def callbackSetFontFamily(value):
    print("callbackSetFontFamily", value)
    config.FONT_FAMILY = value

def callbackSetUiLanguage(value):
    print("callbackSetUiLanguage", value)
    config.UI_LANGUAGE = value

# Translation Tab
def callbackSetDeeplAuthkey(value):
    print("callbackSetDeeplAuthkey", str(value))
    # config.AUTH_KEYS["DeepL(auth)"] = str(value)
    # if len(value) > 0:
    #     if model.authenticationTranslator(choice_translator="DeepL(auth)", auth_key=value) is True:
    #         print_textbox(self.parent.textbox_message_log, "Auth key update completed", "INFO")
    #         print_textbox(self.parent.textbox_message_system_log, "Auth key update completed", "INFO")
    #     else:
    #         pass

# Transcription Tab (Mic)
def callbackSetMicHost(value):
    print("callbackSetMicHost", value)
    config.CHOICE_MIC_HOST = value

def callbackSetMicDevice(value):
    print("callbackSetMicDevice", value)
    config.CHOICE_MIC_DEVICE = value

def callbackSetMicEnergyThreshold(value):
    print("callbackSetMicEnergyThreshold", int(value))
    config.INPUT_MIC_ENERGY_THRESHOLD = int(value)

def callbackSetMicDynamicEnergyThreshold(value):
    print("callbackSetMicDynamicEnergyThreshold", value)
    config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = value

def callbackCheckMicThreshold(is_turned_on):
    print("callbackCheckMicThreshold", is_turned_on)
    if is_turned_on is True:
        # UIの処理あり
        pass
    else:
        # UIの処理あり
        pass

def callbackSetMicRecordTimeout(value):
    print("callbackSetMicRecordTimeout", int(value))
    config.INPUT_MIC_RECORD_TIMEOUT = int(value)

def callbackSetMicPhraseTimeout(value):
    print("callbackSetMicPhraseTimeout", int(value))
    config.INPUT_MIC_PHRASE_TIMEOUT = int(value)

def callbackSetMicMaxPhrases(value):
    print("callbackSetMicMaxPhrases", int(value))
    config.INPUT_MIC_MAX_PHRASES = int(value)

def callbackSetMicWordFilter(value):
    print("callbackSetMicWordFilter", value)
    word_filter = str(value)
    word_filter = [w.strip() for w in word_filter.split(",") if len(w.strip()) > 0]
    word_filter = ",".join(word_filter)
    print("callbackSetMicWordFilter_afterSplitting", word_filter)
    if len(word_filter) > 0:
        config.INPUT_MIC_WORD_FILTER = word_filter.split(",")
    else:
        config.INPUT_MIC_WORD_FILTER = []
    # model.resetKeywordProcessor()
    # model.addKeywords()

# Transcription Tab (Speaker)
def callbackSetSpeakerDevice(value):
    print("callbackSetSpeakerDevice", value)
    config.CHOICE_SPEAKER_DEVICE = value

def callbackSetSpeakerEnergyThreshold(value):
    print("callbackSetSpeakerEnergyThreshold", int(value))
    config.INPUT_SPEAKER_ENERGY_THRESHOLD = int(value)

def callbackSetSpeakerDynamicEnergyThreshold(value):
    print("callbackSetSpeakerDynamicEnergyThreshold", value)
    config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = value

def callbackCheckSpeakerThreshold(is_turned_on):
    print("callbackCheckSpeakerThreshold", is_turned_on)
    if is_turned_on is True:
        # UIの処理あり
        pass
    else:
        # UIの処理あり
        pass

def callbackSetSpeakerRecordTimeout(value):
    print("callbackSetSpeakerRecordTimeout", int(value))
    config.INPUT_SPEAKER_RECORD_TIMEOUT = int(value)

def callbackSetSpeakerPhraseTimeout(value):
    print("callbackSetSpeakerPhraseTimeout", int(value))
    config.INPUT_SPEAKER_PHRASE_TIMEOUT = int(value)

def callbackSetSpeakerMaxPhrases(value):
    print("callbackSetSpeakerMaxPhrases", int(value))
    config.INPUT_SPEAKER_MAX_PHRASES = int(value)


# Others Tab
def callbackSetEnableAutoClearMessageBox(value):
    print("callbackSetEnableAutoClearMessageBox", value)
    config.ENABLE_AUTO_CLEAR_MESSAGE_BOX = value

def callbackSetEnableNoticeXsoverlay(value):
    print("callbackSetEnableNoticeXsoverlay", value)
    config.ENABLE_NOTICE_XSOVERLAY = value

def callbackSetMessageFormat(value):
    print("callbackSetMessageFormat", value)
    if len(value) > 0:
        config.MESSAGE_FORMAT = value


# Advanced Settings Tab
def callbackSetOscIpAddress(value):
    print("callbackSetOscIpAddress", value)
    config.OSC_IP_ADDRESS = value

def callbackSetOscPort(value):
    print("callbackSetOscPort", int(value))
    config.OSC_PORT = int(value)



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
view.register(
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

    entry_message_box_commands={
        "bind_Return": messageBoxPressKeyEnter,
        "bind_Any_KeyPress": messageBoxPressKeyAny,
    },

    config_window={
        # Compact Mode Switch
        "callback_disable_config_window_compact_mode": callbackEnableConfigWindowCompactMode,
        "callback_enable_config_window_compact_mode": callbackDisableConfigWindowCompactMode,

        # Appearance Tab
        "callback_set_transparency": callbackSetTransparency,
        "callback_set_appearance": callbackSetAppearance,
        "callback_set_ui_scaling": callbackSetUiScaling,
        "callback_set_font_family": callbackSetFontFamily,
        "callback_set_ui_language": callbackSetUiLanguage,

        # Translation Tab
        "callback_set_deepl_authkey": callbackSetDeeplAuthkey,

        # Transcription Tab (Mic)
        "callback_set_mic_host": callbackSetMicHost,
        "callback_set_mic_device": callbackSetMicDevice,
        "callback_set_mic_energy_threshold": callbackSetMicEnergyThreshold,
        "callback_set_mic_dynamic_energy_threshold": callbackSetMicDynamicEnergyThreshold,
        "callback_check_mic_threshold": callbackCheckMicThreshold,
        "callback_set_mic_record_timeout": callbackSetMicRecordTimeout,
        "callback_set_mic_phrase_timeout": callbackSetMicPhraseTimeout,
        "callback_set_mic_max_phrases": callbackSetMicMaxPhrases,
        "callback_set_mic_word_filter": callbackSetMicWordFilter,

        # Transcription Tab (Speaker)
        "callback_set_speaker_device": callbackSetSpeakerDevice,
        "callback_set_speaker_energy_threshold": callbackSetSpeakerEnergyThreshold,
        "callback_set_speaker_dynamic_energy_threshold": callbackSetSpeakerDynamicEnergyThreshold,
        "callback_check_speaker_threshold": callbackCheckSpeakerThreshold,
        "callback_set_speaker_record_timeout": callbackSetSpeakerRecordTimeout,
        "callback_set_speaker_phrase_timeout": callbackSetSpeakerPhraseTimeout,
        "callback_set_speaker_max_phrases": callbackSetSpeakerMaxPhrases,

        # Others Tab
        "callback_set_enable_auto_clear_chatbox": callbackSetEnableAutoClearMessageBox,
        "callback_set_enable_notice_xsoverlay": callbackSetEnableNoticeXsoverlay,
        "callback_set_message_format": callbackSetMessageFormat,

        # Advanced Settings Tab
        "callback_set_osc_ip_address": callbackSetOscIpAddress,
        "callback_set_osc_port": callbackSetOscPort,
    },
)

if __name__ == "__main__":
    view.startMainLoop()