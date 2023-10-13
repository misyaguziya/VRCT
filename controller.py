from time import sleep
from threading import Thread
from config import config
from model import model
from view import view
from utils import get_key_by_value
from languages import selectable_languages

# Common
def callbackUpdateSoftware():
    model.updateSoftware()

def callbackRestartSoftware():
    print("callbackRestartSoftware")
    # model.updateSoftware(restart=True)
    model.reStartSoftware()

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

        if translation == None:
            view.printToTextbox_AuthenticationError()
            translation = ""

        if config.ENABLE_TRANSCRIPTION_SEND is True:
            if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
                if len(translation) > 0:
                    osc_message = config.MESSAGE_FORMAT.replace("[message]", message)
                    osc_message = osc_message.replace("[translation]", translation)
                else:
                    osc_message = message
                model.oscSendMessage(osc_message)

            view.printToTextbox_SentMessage(message, translation)
            if config.ENABLE_LOGGER is True:
                if len(translation) > 0:
                    translation = f" ({translation})"
                model.logger.info(f"[SENT] {message}{translation}")

def startTranscriptionSendMessage():
    model.startMicTranscript(sendMicMessage)
    view.setMainWindowAllWidgetsStatusToNormal()

def stopTranscriptionSendMessage():
    model.stopMicTranscript()
    view.setMainWindowAllWidgetsStatusToNormal()

def startThreadingTranscriptionSendMessage():
    view.printToTextbox_enableTranscriptionSend()
    th_startTranscriptionSendMessage = Thread(target=startTranscriptionSendMessage)
    th_startTranscriptionSendMessage.daemon = True
    th_startTranscriptionSendMessage.start()

def stopThreadingTranscriptionSendMessage():
    view.printToTextbox_disableTranscriptionSend()
    th_stopTranscriptionSendMessage = Thread(target=stopTranscriptionSendMessage)
    th_stopTranscriptionSendMessage.daemon = True
    th_stopTranscriptionSendMessage.start()

def startTranscriptionSendMessageOnCloseConfigWindow():
    model.startMicTranscript(sendMicMessage)

def stopTranscriptionSendMessageOnOpenConfigWindow():
    model.stopMicTranscript()

def startThreadingTranscriptionSendMessageOnCloseConfigWindow():
    th_startTranscriptionSendMessage = Thread(target=startTranscriptionSendMessageOnCloseConfigWindow)
    th_startTranscriptionSendMessage.daemon = True
    th_startTranscriptionSendMessage.start()

def stopThreadingTranscriptionSendMessageOnOpenConfigWindow():
    th_stopTranscriptionSendMessage = Thread(target=stopTranscriptionSendMessageOnOpenConfigWindow)
    th_stopTranscriptionSendMessage.daemon = True
    th_stopTranscriptionSendMessage.start()

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

        if translation == None:
            view.printToTextbox_AuthenticationError()
            translation = ""

        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            if config.ENABLE_NOTICE_XSOVERLAY is True:
                xsoverlay_message = config.MESSAGE_FORMAT.replace("[message]", message)
                xsoverlay_message = xsoverlay_message.replace("[translation]", translation)
                model.notificationXSOverlay(xsoverlay_message)
            view.printToTextbox_ReceivedMessage(message, translation)
            if config.ENABLE_LOGGER is True:
                if len(translation) > 0:
                    translation = f" ({translation})"
                model.logger.info(f"[RECEIVED] {message}{translation}")

def startTranscriptionReceiveMessage():
    model.startSpeakerTranscript(receiveSpeakerMessage)
    view.setMainWindowAllWidgetsStatusToNormal()

def stopTranscriptionReceiveMessage():
    model.stopSpeakerTranscript()
    view.setMainWindowAllWidgetsStatusToNormal()

def startThreadingTranscriptionReceiveMessage():
    view.printToTextbox_enableTranscriptionReceive()
    th_startTranscriptionReceiveMessage = Thread(target=startTranscriptionReceiveMessage)
    th_startTranscriptionReceiveMessage.daemon = True
    th_startTranscriptionReceiveMessage.start()

def stopThreadingTranscriptionReceiveMessage():
    view.printToTextbox_disableTranscriptionReceive()
    th_stopTranscriptionReceiveMessage = Thread(target=stopTranscriptionReceiveMessage)
    th_stopTranscriptionReceiveMessage.daemon = True
    th_stopTranscriptionReceiveMessage.start()

def startTranscriptionReceiveMessageOnCloseConfigWindow():
    model.startSpeakerTranscript(receiveSpeakerMessage)

def stopTranscriptionReceiveMessageOnOpenConfigWindow():
    model.stopSpeakerTranscript()

def startThreadingTranscriptionReceiveMessageOnCloseConfigWindow():
    th_startTranscriptionReceiveMessage = Thread(target=startTranscriptionReceiveMessageOnCloseConfigWindow)
    th_startTranscriptionReceiveMessage.daemon = True
    th_startTranscriptionReceiveMessage.start()

def stopThreadingTranscriptionReceiveMessageOnOpenConfigWindow():
    th_stopTranscriptionReceiveMessage = Thread(target=stopTranscriptionReceiveMessageOnOpenConfigWindow)
    th_stopTranscriptionReceiveMessage.daemon = True
    th_stopTranscriptionReceiveMessage.start()

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

        if translation == None:
            view.printToTextbox_AuthenticationError()
            translation = ""

        # send OSC message
        if config.ENABLE_SEND_MESSAGE_TO_VRC is True:
            if len(translation) > 0:
                osc_message = config.MESSAGE_FORMAT.replace("[message]", message)
                osc_message = osc_message.replace("[translation]", translation)
            else:
                osc_message = message
            model.oscSendMessage(osc_message)

        # update textbox message log
        view.printToTextbox_SentMessage(message, translation)
        if config.ENABLE_LOGGER is True:
            if len(translation) > 0:
                translation = f" ({translation})"
            model.logger.info(f"[SENT] {message}{translation}")

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
def initSetLanguageAndCountry():
    select = config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
    language, country = model.getLanguageAndCountry(select)
    config.SOURCE_LANGUAGE = language
    config.SOURCE_COUNTRY = country

    select = config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
    language, country = model.getLanguageAndCountry(select)
    config.TARGET_LANGUAGE = language
    config.TARGET_COUNTRY = country

    config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)
    model.authenticationTranslator(callbackSetAuthKeys)

def setYourLanguageAndCountry(select):
    languages = config.SELECTED_TAB_YOUR_LANGUAGES
    languages[config.SELECTED_TAB_NO] = select
    config.SELECTED_TAB_YOUR_LANGUAGES = languages
    language, country = model.getLanguageAndCountry(select)
    config.SOURCE_LANGUAGE = language
    config.SOURCE_COUNTRY = country
    config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)
    model.authenticationTranslator(callbackSetAuthKeys)
    view.printToTextbox_selectedYourLanguages(select)

def setTargetLanguageAndCountry(select):
    languages = config.SELECTED_TAB_TARGET_LANGUAGES
    languages[config.SELECTED_TAB_NO] = select
    config.SELECTED_TAB_TARGET_LANGUAGES = languages
    language, country = model.getLanguageAndCountry(select)
    config.TARGET_LANGUAGE = language
    config.TARGET_COUNTRY = country
    config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)
    model.authenticationTranslator(callbackSetAuthKeys)
    view.printToTextbox_selectedTargetLanguages(select)

def callbackSelectedLanguagePresetTab(selected_tab_no):
    config.SELECTED_TAB_NO = selected_tab_no
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
    model.authenticationTranslator(callbackSetAuthKeys)
    view.printToTextbox_changedLanguagePresetTab(config.SELECTED_TAB_NO)

def callbackSetAuthKeys(keys):
    config.AUTH_KEYS = keys

# command func
def callbackToggleTranslation(is_turned_on):
    config.ENABLE_TRANSLATION = is_turned_on
    if config.ENABLE_TRANSLATION is True:
        view.printToTextbox_enableTranslation()
    else:
        view.printToTextbox_disableTranslation()

def callbackToggleTranscriptionSend(is_turned_on):
    view.setMainWindowAllWidgetsStatusToDisabled()
    config.ENABLE_TRANSCRIPTION_SEND = is_turned_on
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        startThreadingTranscriptionSendMessage()
    else:
        stopThreadingTranscriptionSendMessage()

def callbackToggleTranscriptionReceive(is_turned_on):
    view.setMainWindowAllWidgetsStatusToDisabled()
    config.ENABLE_TRANSCRIPTION_RECEIVE = is_turned_on
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        startThreadingTranscriptionReceiveMessage()
    else:
        stopThreadingTranscriptionReceiveMessage()

def callbackToggleForeground(is_turned_on):
    config.ENABLE_FOREGROUND = is_turned_on
    if config.ENABLE_FOREGROUND is True:
        view.printToTextbox_enableForeground()
        view.foregroundOn()
    else:
        view.printToTextbox_disableForeground()
        view.foregroundOff()

def callbackEnableMainWindowSidebarCompactMode():
    config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
    view.enableMainWindowSidebarCompactMode()

def callbackDisableMainWindowSidebarCompactMode():
    config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
    view.disableMainWindowSidebarCompactMode()

# Config Window
def callbackOpenConfigWindow():
    view.setMainWindowAllWidgetsStatusToDisabled()
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        stopThreadingTranscriptionSendMessageOnOpenConfigWindow()
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        stopThreadingTranscriptionReceiveMessageOnOpenConfigWindow()
    if config.ENABLE_FOREGROUND is True:
        view.foregroundOff()

def callbackCloseConfigWindow():
    model.stopCheckMicEnergy()
    model.stopCheckSpeakerEnergy()
    view.initMicThresholdCheckButton()
    # view.initProgressBar_MicEnergy() # ProgressBarに0をセットしたい
    view.initSpeakerThresholdCheckButton()
    # view.initProgressBar_SpeakerEnergy() # ProgressBarに0をセットしたい

    if config.ENABLE_TRANSCRIPTION_SEND is True:
        startThreadingTranscriptionSendMessageOnCloseConfigWindow()
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            sleep(2)
    if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
        startThreadingTranscriptionReceiveMessageOnCloseConfigWindow()
    if config.ENABLE_FOREGROUND is True:
        view.foregroundOn()
    view.setMainWindowAllWidgetsStatusToNormal()

# Compact Mode Switch
def callbackEnableConfigWindowCompactMode():
    config.IS_CONFIG_WINDOW_COMPACT_MODE = True
    model.stopCheckMicEnergy()
    view.initMicThresholdCheckButton()
    model.stopCheckSpeakerEnergy()
    view.initSpeakerThresholdCheckButton()

    view.enableConfigWindowCompactMode()

def callbackDisableConfigWindowCompactMode():
    config.IS_CONFIG_WINDOW_COMPACT_MODE = False
    model.stopCheckMicEnergy()
    view.initMicThresholdCheckButton()
    model.stopCheckSpeakerEnergy()
    view.initSpeakerThresholdCheckButton()

    view.disableConfigWindowCompactMode()

# Appearance Tab
def callbackSetTransparency(value):
    print("callbackSetTransparency", int(value))
    config.TRANSPARENCY = int(value)
    view.setMainWindowTransparency(config.TRANSPARENCY/100)

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
    value = get_key_by_value(selectable_languages, value)
    print("callbackSetUiLanguage__after_get_key_by_value", value)
    config.UI_LANGUAGE = value

# Translation Tab
def callbackSetDeeplAuthkey(value):
    print("callbackSetDeeplAuthkey", str(value))
    if len(value) > 0 and model.authenticationTranslator(callbackSetAuthKeys, choice_translator="DeepL(auth)", auth_key=value) is True:
        config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)
        model.authenticationTranslator(callbackSetAuthKeys)
        view.printToTextbox_AuthenticationSuccess()
    elif len(value) == 0:
        auth_keys = config.AUTH_KEYS
        auth_keys["DeepL(auth)"] = None
        config.AUTH_KEYS = auth_keys
        model.authenticationTranslator(callbackSetAuthKeys)
    else:
        view.printToTextbox_AuthenticationError()

# Transcription Tab (Mic)
def callbackSetMicHost(value):
    print("callbackSetMicHost", value)
    config.CHOICE_MIC_HOST = value
    config.CHOICE_MIC_DEVICE = model.getInputDefaultDevice()

    view.updateSelected_MicDevice(config.CHOICE_MIC_DEVICE)
    view.updateList_MicDevice(model.getListInputDevice())

    model.stopCheckMicEnergy()
    view.replaceMicThresholdCheckButton_Passive()

def callbackSetMicDevice(value):
    print("callbackSetMicDevice", value)
    config.CHOICE_MIC_DEVICE = value

    model.stopCheckMicEnergy()
    view.replaceMicThresholdCheckButton_Passive()

def callbackSetMicEnergyThreshold(value):
    print("callbackSetMicEnergyThreshold", value)
    try:
        value = int(value)
        if 0 <= value and value <= config.MAX_MIC_ENERGY_THRESHOLD:
            view.clearErrorMessage()
            config.INPUT_MIC_ENERGY_THRESHOLD = value
            view.setGuiVariable_MicEnergyThreshold(config.INPUT_MIC_ENERGY_THRESHOLD)
        else:
            raise ValueError()
    except:
        view.showErrorMessage_MicEnergyThreshold()

def callbackSetMicDynamicEnergyThreshold(value):
    print("callbackSetMicDynamicEnergyThreshold", value)
    config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = value
    if config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD is True:
        view.closeMicEnergyThresholdWidget()
    else:
        view.openMicEnergyThresholdWidget()

def setProgressBarMicEnergy(energy):
    view.updateSetProgressBar_MicEnergy(energy)

def callbackCheckMicThreshold(is_turned_on):
    print("callbackCheckMicThreshold", is_turned_on)
    if is_turned_on is True:
        view.replaceMicThresholdCheckButton_Disabled()
        model.startCheckMicEnergy(setProgressBarMicEnergy, view.initProgressBar_MicEnergy)
        view.replaceMicThresholdCheckButton_Active()
    else:
        view.replaceMicThresholdCheckButton_Disabled()
        model.stopCheckMicEnergy()
        view.replaceMicThresholdCheckButton_Passive()

def callbackSetMicRecordTimeout(value):
    print("callbackSetMicRecordTimeout", value)
    try:
        value = int(value)
        if 0 <= value and value <= config.INPUT_MIC_PHRASE_TIMEOUT:
            view.clearErrorMessage()
            config.INPUT_MIC_RECORD_TIMEOUT = value
            view.setGuiVariable_MicRecordTimeout(config.INPUT_MIC_RECORD_TIMEOUT)
        else:
            raise ValueError()
    except:
        view.showErrorMessage_MicRecordTimeout()

def callbackSetMicPhraseTimeout(value):
    print("callbackSetMicPhraseTimeout", value)
    try:
        value = int(value)
        if 0 <= value and value >= config.INPUT_MIC_RECORD_TIMEOUT:
            view.clearErrorMessage()
            config.INPUT_MIC_PHRASE_TIMEOUT = value
            view.setGuiVariable_MicPhraseTimeout(config.INPUT_MIC_PHRASE_TIMEOUT)
        else:
            raise ValueError()
    except:
        view.showErrorMessage_MicPhraseTimeout()

def callbackSetMicMaxPhrases(value):
    print("callbackSetMicMaxPhrases", value)
    try:
        value = int(value)
        if 0 <= value:
            view.clearErrorMessage()
            config.INPUT_MIC_MAX_PHRASES = value
            view.setGuiVariable_MicMaxPhrases(config.INPUT_MIC_MAX_PHRASES)
        else:
            raise ValueError()
    except:
        view.showErrorMessage_MicMaxPhrases()

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
    model.resetKeywordProcessor()
    model.addKeywords()

# Transcription Tab (Speaker)
def callbackSetSpeakerDevice(value):
    print("callbackSetSpeakerDevice", value)
    config.CHOICE_SPEAKER_DEVICE = value

    model.stopCheckSpeakerEnergy()
    view.replaceSpeakerThresholdCheckButton_Passive()

def callbackSetSpeakerEnergyThreshold(value):
    print("callbackSetSpeakerEnergyThreshold", value)
    try:
        value = int(value)
        if 0 <= value and value <= config.MAX_SPEAKER_ENERGY_THRESHOLD:
            view.clearErrorMessage()
            config.INPUT_SPEAKER_ENERGY_THRESHOLD = value
            view.setGuiVariable_SpeakerEnergyThreshold(config.INPUT_SPEAKER_ENERGY_THRESHOLD)
        else:
            raise ValueError()
    except:
        view.showErrorMessage_SpeakerEnergyThreshold()

def callbackSetSpeakerDynamicEnergyThreshold(value):
    print("callbackSetSpeakerDynamicEnergyThreshold", value)
    config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = value
    if config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD is True:
        view.closeSpeakerEnergyThresholdWidget()
    else:
        view.openSpeakerEnergyThresholdWidget()


def setProgressBarSpeakerEnergy(energy):
    view.updateSetProgressBar_SpeakerEnergy(energy)

def callbackCheckSpeakerThreshold(is_turned_on):
    print("callbackCheckSpeakerThreshold", is_turned_on)
    if is_turned_on is True:
        view.replaceSpeakerThresholdCheckButton_Disabled()
        model.startCheckSpeakerEnergy(setProgressBarSpeakerEnergy, view.initProgressBar_SpeakerEnergy)
        view.replaceSpeakerThresholdCheckButton_Active()
    else:
        view.replaceSpeakerThresholdCheckButton_Disabled()
        model.stopCheckSpeakerEnergy()
        view.replaceSpeakerThresholdCheckButton_Passive()

def callbackSetSpeakerRecordTimeout(value):
    print("callbackSetSpeakerRecordTimeout", value)
    try:
        value = int(value)
        if 0 <= value and value <= config.INPUT_SPEAKER_PHRASE_TIMEOUT:
            view.clearErrorMessage()
            config.INPUT_SPEAKER_RECORD_TIMEOUT = value
            view.setGuiVariable_SpeakerRecordTimeout(config.INPUT_SPEAKER_RECORD_TIMEOUT)
        else:
            raise ValueError()
    except:
        view.showErrorMessage_SpeakerRecordTimeout()

def callbackSetSpeakerPhraseTimeout(value):
    print("callbackSetSpeakerPhraseTimeout", value)
    try:
        value = int(value)
        if 0 <= value and value >= config.INPUT_SPEAKER_RECORD_TIMEOUT:
            view.clearErrorMessage()
            config.INPUT_SPEAKER_PHRASE_TIMEOUT = value
            view.setGuiVariable_SpeakerPhraseTimeout(config.INPUT_SPEAKER_PHRASE_TIMEOUT)
        else:
            raise ValueError()
    except:
        view.showErrorMessage_SpeakerPhraseTimeout()

def callbackSetSpeakerMaxPhrases(value):
    print("callbackSetSpeakerMaxPhrases", value)
    try:
        value = int(value)
        if 0 <= value:
            view.clearErrorMessage()
            config.INPUT_SPEAKER_MAX_PHRASES = value
            view.setGuiVariable_SpeakerMaxPhrases(config.INPUT_SPEAKER_MAX_PHRASES)
        else:
            raise ValueError()
    except:
        view.showErrorMessage_SpeakerMaxPhrases()


# Others Tab
def callbackSetEnableAutoClearMessageBox(value):
    print("callbackSetEnableAutoClearMessageBox", value)
    config.ENABLE_AUTO_CLEAR_MESSAGE_BOX = value

def callbackSetEnableNoticeXsoverlay(value):
    print("callbackSetEnableNoticeXsoverlay", value)
    config.ENABLE_NOTICE_XSOVERLAY = value

def callbackSetEnableAutoExportMessageLogs(value):
    print("callbackSetEnableAutoExportMessageLogs", value)
    config.ENABLE_LOGGER = value

    if config.ENABLE_LOGGER is True:
        model.startLogger()
    else:
        model.stopLogger()

def callbackSetMessageFormat(value):
    print("callbackSetMessageFormat", value)
    if len(value) > 0:
        config.MESSAGE_FORMAT = value

def callbackSetEnableSendMessageToVrc(value):
    print("callbackSetEnableSendMessageToVrc", value)
    config.ENABLE_SEND_MESSAGE_TO_VRC = value

# [deprecated]
# def callbackSetStartupOscEnabledCheck(value):
#     print("callbackSetStartupOscEnabledCheck", value)
#     config.STARTUP_OSC_ENABLED_CHECK = value

# Advanced Settings Tab
def callbackSetOscIpAddress(value):
    print("callbackSetOscIpAddress", str(value))
    config.OSC_IP_ADDRESS = str(value)

def callbackSetOscPort(value):
    print("callbackSetOscPort", int(value))
    config.OSC_PORT = int(value)

def createMainWindow():
    # create GUI
    view.createGUI()

    # init config
    initSetLanguageAndCountry()

    if model.authenticationTranslator(callbackSetAuthKeys) is False:
        # error update Auth key
        view.printToTextbox_AuthenticationError()
        config.CHOICE_TRANSLATOR = model.findTranslationEngine(config.SOURCE_LANGUAGE, config.TARGET_LANGUAGE)
        model.authenticationTranslator(callbackSetAuthKeys)

    # set word filter
    model.addKeywords()

    # check OSC started [deprecated]
    # if config.STARTUP_OSC_ENABLED_CHECK is True and config.ENABLE_SEND_MESSAGE_TO_VRC is True:
    #     model.checkOSCStarted(view.printToTextbox_OSCError)

    # check Software Updated
    if model.checkSoftwareUpdated() is True:
        view.showUpdateAvailableButton()

    # init logger
    if config.ENABLE_LOGGER is True:
        model.startLogger()

    # set UI and callback
    view.register(
        common_registers={
            "callback_update_software": callbackUpdateSoftware,
            "callback_restart_software": callbackRestartSoftware,
        },

        window_action_registers={
            "callback_open_config_window": callbackOpenConfigWindow,
            "callback_close_config_window": callbackCloseConfigWindow,
        },

        main_window_registers={
            "callback_enable_main_window_sidebar_compact_mode": callbackEnableMainWindowSidebarCompactMode,
            "callback_disable_main_window_sidebar_compact_mode": callbackDisableMainWindowSidebarCompactMode,

            "callback_toggle_translation": callbackToggleTranslation,
            "callback_toggle_transcription_send": callbackToggleTranscriptionSend,
            "callback_toggle_transcription_receive": callbackToggleTranscriptionReceive,
            "callback_toggle_foreground": callbackToggleForeground,

            "callback_your_language": setYourLanguageAndCountry,
            "callback_target_language": setTargetLanguageAndCountry,
            "values": model.getListLanguageAndCountry(),

            "callback_selected_language_preset_tab": callbackSelectedLanguagePresetTab,
            "bind_Return": messageBoxPressKeyEnter,
            "bind_Any_KeyPress": messageBoxPressKeyAny,
        },

        config_window_registers={
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
            "list_mic_host": model.getListInputHost(),
            "callback_set_mic_device": callbackSetMicDevice,
            "list_mic_device": model.getListInputDevice(),
            "callback_set_mic_energy_threshold": callbackSetMicEnergyThreshold,
            "callback_set_mic_dynamic_energy_threshold": callbackSetMicDynamicEnergyThreshold,
            "callback_check_mic_threshold": callbackCheckMicThreshold,
            "callback_set_mic_record_timeout": callbackSetMicRecordTimeout,
            "callback_set_mic_phrase_timeout": callbackSetMicPhraseTimeout,
            "callback_set_mic_max_phrases": callbackSetMicMaxPhrases,
            "callback_set_mic_word_filter": callbackSetMicWordFilter,

            # Transcription Tab (Speaker)
            "callback_set_speaker_device": callbackSetSpeakerDevice,
            "list_speaker_device": model.getListOutputDevice(),
            "callback_set_speaker_energy_threshold": callbackSetSpeakerEnergyThreshold,
            "callback_set_speaker_dynamic_energy_threshold": callbackSetSpeakerDynamicEnergyThreshold,
            "callback_check_speaker_threshold": callbackCheckSpeakerThreshold,
            "callback_set_speaker_record_timeout": callbackSetSpeakerRecordTimeout,
            "callback_set_speaker_phrase_timeout": callbackSetSpeakerPhraseTimeout,
            "callback_set_speaker_max_phrases": callbackSetSpeakerMaxPhrases,

            # Others Tab
            "callback_set_enable_auto_clear_chatbox": callbackSetEnableAutoClearMessageBox,
            "callback_set_enable_notice_xsoverlay": callbackSetEnableNoticeXsoverlay,
            "callback_set_enable_auto_export_message_logs": callbackSetEnableAutoExportMessageLogs,
            "callback_set_message_format": callbackSetMessageFormat,
            "callback_set_enable_send_message_to_vrc": callbackSetEnableSendMessageToVrc,
            # "callback_set_startup_osc_enabled_check": callbackSetStartupOscEnabledCheck, # [deprecated]

            # Advanced Settings Tab
            "callback_set_osc_ip_address": callbackSetOscIpAddress,
            "callback_set_osc_port": callbackSetOscPort,
        },
    )

def showMainWindow():
    view.startMainLoop()