from types import SimpleNamespace

from customtkinter import StringVar, END as CTK_END, get_appearance_mode
from vrct_gui.ui_managers import ColorThemeManager, ImageFilenameManager, UiScalingManager
from vrct_gui import vrct_gui

from config import config

class View():
    def __init__(self):
        self.settings = SimpleNamespace()
        theme = get_appearance_mode() if config.APPEARANCE_THEME == "System" else config.APPEARANCE_THEME
        all_ctm = ColorThemeManager(theme)
        all_uism = UiScalingManager(config.UI_SCALING)
        image_filename = ImageFilenameManager(theme)

        common_args = {
            "image_filename": image_filename,
            "FONT_FAMILY": config.FONT_FAMILY,
        }

        self.settings.main = SimpleNamespace(
            ctm=all_ctm.main,
            uism=all_uism.main,
            IS_SIDEBAR_COMPACT_MODE=False,
            COMPACT_MODE_ICON_SIZE=0,
            **common_args
        )

        self.settings.config_window = SimpleNamespace(
            ctm=all_ctm.config_window,
            uism=all_uism.config_window,
            IS_CONFIG_WINDOW_COMPACT_MODE=config.IS_CONFIG_WINDOW_COMPACT_MODE,
            **common_args
        )


    def register(self, sidebar_features, language_presets, entry_message_box_commands, config_window):

        vrct_gui.CALLBACK_TOGGLE_TRANSLATION = sidebar_features["callback_toggle_translation"]
        vrct_gui.CALLBACK_TOGGLE_TRANSCRIPTION_SEND = sidebar_features["callback_toggle_transcription_send"]
        vrct_gui.CALLBACK_TOGGLE_TRANSCRIPTION_RECEIVE = sidebar_features["callback_toggle_transcription_receive"]
        vrct_gui.CALLBACK_TOGGLE_FOREGROUND = sidebar_features["callback_toggle_foreground"]


        vrct_gui.sqls__optionmenu_your_language.configure(values=language_presets["values"])
        vrct_gui.sqls__optionmenu_your_language.configure(command=language_presets["callback_your_language"])
        vrct_gui.sqls__optionmenu_your_language.configure(variable=StringVar(value=config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]))
        vrct_gui.sqls__optionmenu_target_language.configure(values=language_presets["values"])
        vrct_gui.sqls__optionmenu_target_language.configure(command=language_presets["callback_target_language"])
        vrct_gui.sqls__optionmenu_target_language.configure(variable=StringVar(value=config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]))

        vrct_gui.CALLBACK_SELECTED_TAB_NO_1 = language_presets["callback_selected_tab_no_1"]
        vrct_gui.CALLBACK_SELECTED_TAB_NO_2 = language_presets["callback_selected_tab_no_2"]
        vrct_gui.CALLBACK_SELECTED_TAB_NO_3 = language_presets["callback_selected_tab_no_3"]
        vrct_gui.setDefaultActiveLanguagePresetTab(tab_no=config.SELECTED_TAB_NO)


        entry_message_box = getattr(vrct_gui, "entry_message_box")
        entry_message_box.bind("<Return>", entry_message_box_commands["bind_Return"])
        entry_message_box.bind("<Any-KeyPress>", entry_message_box_commands["bind_Any_KeyPress"])

        entry_message_box.bind("<FocusIn>", self._foregroundOffForcefully)
        entry_message_box.bind("<FocusOut>", self._foregroundOnForcefully)


        # Config Window
        # Compact Mode Switch
        vrct_gui.config_window.CALLBACK_ENABLE_CONFIG_WINDOW_COMPACT_MODE = config_window["callback_disable_config_window_compact_mode"]
        vrct_gui.config_window.CALLBACK_DISABLE_CONFIG_WINDOW_COMPACT_MODE = config_window["callback_enable_config_window_compact_mode"]


        # Appearance Tab
        vrct_gui.config_window.CALLBACK_SET_TRANSPARENCY = config_window["callback_set_transparency"]
        vrct_gui.config_window.CALLBACK_SET_APPEARANCE = config_window["callback_set_appearance"]
        vrct_gui.config_window.CALLBACK_SET_UI_SCALING = config_window["callback_set_ui_scaling"]
        vrct_gui.config_window.CALLBACK_SET_FONT_FAMILY = config_window["callback_set_font_family"]
        vrct_gui.config_window.CALLBACK_SET_UI_LANGUAGE = config_window["callback_set_ui_language"]


        # Translation Tab
        vrct_gui.config_window.CALLBACK_SET_DEEPL_AUTHKEY = config_window["callback_set_deepl_authkey"]

        # Transcription Tab (Mic)
        vrct_gui.config_window.CALLBACK_SET_MIC_HOST = config_window["callback_set_mic_host"]
        vrct_gui.config_window.CALLBACK_SET_MIC_DEVICE = config_window["callback_set_mic_device"]
        vrct_gui.config_window.CALLBACK_SET_MIC_ENERGY_THRESHOLD = config_window["callback_set_mic_energy_threshold"]
        vrct_gui.config_window.CALLBACK_SET_MIC_DYNAMIC_ENERGY_THRESHOLD = config_window["callback_set_mic_dynamic_energy_threshold"]
        vrct_gui.config_window.CALLBACK_CHECK_MIC_THRESHOLD = config_window["callback_check_mic_threshold"]
        vrct_gui.config_window.CALLBACK_SET_MIC_RECORD_TIMEOUT = config_window["callback_set_mic_record_timeout"]
        vrct_gui.config_window.CALLBACK_SET_MIC_PHRASE_TIMEOUT = config_window["callback_set_mic_phrase_timeout"]
        vrct_gui.config_window.CALLBACK_SET_MIC_MAX_PHRASES = config_window["callback_set_mic_max_phrases"]
        vrct_gui.config_window.CALLBACK_SET_MIC_WORD_FILTER = config_window["callback_set_mic_word_filter"]

        # Transcription Tab (Speaker)
        vrct_gui.config_window.CALLBACK_SET_SPEAKER_DEVICE = config_window["callback_set_speaker_device"]
        vrct_gui.config_window.CALLBACK_SET_SPEAKER_ENERGY_THRESHOLD = config_window["callback_set_speaker_energy_threshold"]
        vrct_gui.config_window.CALLBACK_SET_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = config_window["callback_set_speaker_dynamic_energy_threshold"]
        vrct_gui.config_window.CALLBACK_CHECK_SPEAKER_THRESHOLD = config_window["callback_check_speaker_threshold"]
        vrct_gui.config_window.CALLBACK_SET_SPEAKER_RECORD_TIMEOUT = config_window["callback_set_speaker_record_timeout"]
        vrct_gui.config_window.CALLBACK_SET_SPEAKER_PHRASE_TIMEOUT = config_window["callback_set_speaker_phrase_timeout"]
        vrct_gui.config_window.CALLBACK_SET_SPEAKER_MAX_PHRASES = config_window["callback_set_speaker_max_phrases"]

        # Others Tab
        vrct_gui.config_window.CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX = config_window["callback_set_enable_auto_clear_chatbox"]
        vrct_gui.config_window.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY = config_window["callback_set_enable_notice_xsoverlay"]
        vrct_gui.config_window.CALLBACK_SET_MESSAGE_FORMAT = config_window["callback_set_message_format"]

        # Advanced Settings Tab
        vrct_gui.config_window.CALLBACK_SET_OSC_IP_ADDRESS = config_window["callback_set_osc_ip_address"]
        vrct_gui.config_window.CALLBACK_SET_OSC_PORT = config_window["callback_set_osc_port"]




    def setMainWindowAllWidgetsStatusToNormal(self):
        vrct_gui.changeMainWindowWidgetsStatus("normal", "All")

    def setMainWindowAllWidgetsStatusToDisabled(self):
        vrct_gui.changeMainWindowWidgetsStatus("disabled", "All")



    def _foregroundOnForcefully(self, _e):
        if config.ENABLE_FOREGROUND:
            self.foregroundOn()

    def _foregroundOffForcefully(self, _e):
        if config.ENABLE_FOREGROUND:
            self.foregroundOff()


    def foregroundOn(self):
        vrct_gui.attributes("-topmost", True)

    def foregroundOff(self):
        vrct_gui.attributes("-topmost", False)


    def updateGuiVariableByPresetTabNo(self, tab_no:str):
        vrct_gui.YOUR_LANGUAGE = config.SELECTED_TAB_YOUR_LANGUAGES[tab_no]
        vrct_gui.TARGET_LANGUAGE = config.SELECTED_TAB_TARGET_LANGUAGES[tab_no]



    def getTranslationButtonStatus(self):
        return vrct_gui.translation_switch_box.get()
    def getTranscriptionSendButtonStatus(self):
        return vrct_gui.transcription_send_switch_box.get()
    def getTranscriptionReceiveButtonStatus(self):
        return vrct_gui.transcription_receive_switch_box.get()
    def getForegroundButtonStatus(self):
        return vrct_gui.foreground_switch_box.get()


    def printToTextbox_enableTranslation(self):
        self._printToTextbox_Info("翻訳機能をONにしました")
    def printToTextbox_disableTranslation(self):
        self._printToTextbox_Info("翻訳機能をOFFにしました")

    def printToTextbox_enableTranscriptionSend(self):
        self._printToTextbox_Info("Voice2chatbox機能をONにしました")
    def printToTextbox_disableTranscriptionSend(self):
        self._printToTextbox_Info("Voice2chatbox機能をOFFにしました")

    def printToTextbox_enableTranscriptionReceive(self):
        self._printToTextbox_Info("Speaker2chatbox機能をONにしました")
    def printToTextbox_disableTranscriptionReceive(self):
        self._printToTextbox_Info("Speaker2chatbox機能をOFFにしました")

    def printToTextbox_enableForeground(self):
        self._printToTextbox_Info("Start foreground")
    def printToTextbox_disableForeground(self):
        self._printToTextbox_Info("Stop foreground")


    def printToTextbox_AuthenticationError(self):
        self._printToTextbox_Info("Auth Key or language setting is incorrect")

    def printToTextbox_OSCError(self):
        self._printToTextbox_Info("OSC is not enabled, please enable OSC and rejoin")

    def printToTextbox_DetectedByWordFilter(self, detected_message):
        self._printToTextbox_Info(f"Detect WordFilter :{detected_message}")


    def _printToTextbox_Info(self, info_message):
        vrct_gui.printToTextbox(vrct_gui.textbox_all, info_message, "", "INFO")
        vrct_gui.printToTextbox(vrct_gui.textbox_system, info_message, "", "INFO")



    def printToTextbox_SentMessage(self, original_message, translated_message):
        self._printToTextbox_Sent(original_message, translated_message)

    def _printToTextbox_Sent(self, original_message, translated_message):
        vrct_gui.printToTextbox(vrct_gui.textbox_all, original_message, translated_message, "SEND")
        vrct_gui.printToTextbox(vrct_gui.textbox_sent, original_message, translated_message, "SEND")


    def printToTextbox_ReceivedMessage(self, original_message, translated_message):
        self._printToTextbox_Received(original_message, translated_message)

    def _printToTextbox_Received(self, original_message, translated_message):
        vrct_gui.printToTextbox(vrct_gui.textbox_all, original_message, translated_message, "RECEIVE")
        vrct_gui.printToTextbox(vrct_gui.textbox_received, original_message, translated_message, "RECEIVE")


    def getTextFromMessageBox(self):
        return vrct_gui.entry_message_box.get()

    def clearMessageBox(self):
        vrct_gui.entry_message_box.delete(0, CTK_END)




    def createGUI(self):
        vrct_gui.createGUI(settings=self.settings)

    def startMainLoop(self):
        vrct_gui.startMainLoop()


    # Config Window
    def reloadConfigWindowSettingBoxContainer(self):
        vrct_gui.config_window.settings.IS_CONFIG_WINDOW_COMPACT_MODE = config.IS_CONFIG_WINDOW_COMPACT_MODE
        vrct_gui.config_window.reloadConfigWindowSettingBoxContainer()

view = View()