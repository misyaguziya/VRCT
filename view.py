from types import SimpleNamespace

from customtkinter import StringVar, END as CTK_END
from vrct_gui import vrct_gui

from config import config

class View():
    def __init__(self):
        self.settings = SimpleNamespace()
        self.settings.config_window = SimpleNamespace()
        self.settings.config_window = SimpleNamespace(
            is_config_window_compact_mode=config.IS_CONFIG_WINDOW_COMPACT_MODE
        )
        pass


    def initializer(self, sidebar_features, language_presets, entry_message_box, entry_message_box_bind_Return, entry_message_box_bind_Any_KeyPress, config_window):

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
        # entry_message_box.bind("<Return>", lambda e: entry_message_box["bind_Return"](e))
        # entry_message_box.bind("<Any-KeyPress>", lambda e: entry_message_box["bind_Any_KeyPress"](e))
        entry_message_box.bind("<Return>", entry_message_box_bind_Return)
        entry_message_box.bind("<Any-KeyPress>", entry_message_box_bind_Any_KeyPress)

        entry_message_box.bind("<FocusIn>", self._foregroundOffForcefully)
        entry_message_box.bind("<FocusOut>", self._foregroundOnForcefully)


        vrct_gui.config_window.CALLBACK_ENABLE_CONFIG_WINDOW_COMPACT_MODE = config_window["callback_disable_config_window_compact_mode"]
        vrct_gui.config_window.CALLBACK_DISABLE_CONFIG_WINDOW_COMPACT_MODE = config_window["callback_enable_config_window_compact_mode"]






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