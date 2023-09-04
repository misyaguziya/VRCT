from types import SimpleNamespace
from tkinter import font as tk_font
from languages import selectable_languages

from customtkinter import StringVar, IntVar, BooleanVar, END as CTK_END, get_appearance_mode
from vrct_gui.ui_managers import ColorThemeManager, ImageFileManager, UiScalingManager
from vrct_gui import vrct_gui

from config import config

class View():
    def __init__(self):
        self.settings = SimpleNamespace()
        theme = get_appearance_mode() if config.APPEARANCE_THEME == "System" else config.APPEARANCE_THEME
        all_ctm = ColorThemeManager(theme)
        all_uism = UiScalingManager(config.UI_SCALING)
        image_file = ImageFileManager(theme)

        common_args = {
            "image_file": image_file,
            "FONT_FAMILY": config.FONT_FAMILY,
        }

        self.settings.main = SimpleNamespace(
            ctm=all_ctm.main,
            uism=all_uism.main,
            COMPACT_MODE_ICON_SIZE=0,
            **common_args
        )

        self.settings.config_window = SimpleNamespace(
            ctm=all_ctm.config_window,
            uism=all_uism.config_window,
            IS_CONFIG_WINDOW_COMPACT_MODE=config.IS_CONFIG_WINDOW_COMPACT_MODE,
            **common_args
        )

        self.view_variable = SimpleNamespace(
            # Main Window
            # Sidebar Compact Mode
            IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE=False,
            CALLBACK_TOGGLE_MAIN_WINDOW_SIDEBAR_COMPACT_MODE=None,

            # Sidebar Features
            VAR_LABEL_TRANSLATION=StringVar(value="Translation"),
            CALLBACK_TOGGLE_TRANSLATION=None,

            VAR_LABEL_TRANSCRIPTION_SEND=StringVar(value="Voice2Chatbox"),
            CALLBACK_TOGGLE_TRANSCRIPTION_SEND=None,

            VAR_LABEL_TRANSCRIPTION_RECEIVE=StringVar(value="Speaker2Log"),
            CALLBACK_TOGGLE_TRANSCRIPTION_RECEIVE=None,

            VAR_LABEL_FOREGROUND=StringVar(value="Foreground"),
            CALLBACK_TOGGLE_FOREGROUND=None,

            # Language Settings
            CALLBACK_SELECTED_LANGUAGE_PRESET_TAB=None,
            VAR_YOUR_LANGUAGE = StringVar(value="Japanese\n(Japan)"),
            VAR_TARGET_LANGUAGE = StringVar(value="English\n(United States)"),



            # Config Window
            # Appearance Tab
            VAR_LABEL_TRANSPARENCY=StringVar(value="Transparency"),
            VAR_DESC_TRANSPARENCY=StringVar(value="Change the window's transparency. 50% to 100%. (Default: 100%)"),
            SLIDER_RANGE_TRANSPARENCY=(50, 100),
            CALLBACK_SET_TRANSPARENCY=None,
            VAR_TRANSPARENCY=IntVar(value=config.TRANSPARENCY),

            VAR_LABEL_APPEARANCE_THEME=StringVar(value="Theme"),
            VAR_DESC_APPEARANCE_THEME=StringVar(value="Change the color theme from \"Light\" and \"Dark\". If you select \"System\", It will adjust based on your Windows theme. (Default: System)"),
            LIST_APPEARANCE_THEME=["Light", "Dark", "System"],
            CALLBACK_SET_APPEARANCE_THEME=None,
            VAR_APPEARANCE_THEME=StringVar(value=config.APPEARANCE_THEME),

            VAR_LABEL_UI_SCALING=StringVar(value="UI Size"),
            VAR_DESC_UI_SCALING=StringVar(value="(Default: 100%)"),
            LIST_UI_SCALING=["80%", "90%", "100%", "110%", "120%"],
            CALLBACK_SET_UI_SCALING=None,
            VAR_UI_SCALING=StringVar(value=config.UI_SCALING),

            VAR_LABEL_FONT_FAMILY=StringVar(value="Font Family"),
            VAR_DESC_FONT_FAMILY=StringVar(value="(Default: Yu Gothic UI)"),
            LIST_FONT_FAMILY=list(tk_font.families()),
            CALLBACK_SET_FONT_FAMILY=None,
            VAR_FONT_FAMILY=StringVar(value=config.FONT_FAMILY),

            VAR_LABEL_UI_LANGUAGE=StringVar(value="UI Language"),
            VAR_DESC_UI_LANGUAGE=StringVar(value="(Default: English)"),
            LIST_UI_LANGUAGE=list(selectable_languages.values()),
            CALLBACK_SET_UI_LANGUAGE=None,
            VAR_UI_LANGUAGE=StringVar(value=selectable_languages[config.UI_LANGUAGE]),


            # Translation Tab
            VAR_LABEL_DEEPL_AUTH_KEY=StringVar(value="DeepL Auth Key"),
            VAR_DESC_DEEPL_AUTH_KEY=None,
            # VAR_DESC_DEEPL_AUTH_KEY=StringVar(value=""),
            CALLBACK_SET_DEEPL_AUTH_KEY=None,
            VAR_DEEPL_AUTH_KEY=StringVar(value=config.AUTH_KEYS["DeepL(auth)"]),


            # Transcription Tab (Mic)
            VAR_LABEL_MIC_HOST=StringVar(value="Mic Host"),
            VAR_DESC_MIC_HOST=StringVar(value="Select the mic host. (Default: ?)"),
            LIST_MIC_HOST=[],
            CALLBACK_SET_MIC_HOST=None,
            VAR_MIC_HOST=StringVar(value=config.CHOICE_MIC_HOST),

            VAR_LABEL_MIC_DEVICE=StringVar(value="Mic Device"),
            VAR_DESC_MIC_DEVICE=StringVar(value="Select the mic devise. (Default: ?)"),
            LIST_MIC_DEVICE=[],
            CALLBACK_SET_MIC_DEVICE=None,
            VAR_MIC_DEVICE=StringVar(value=config.CHOICE_MIC_DEVICE),

            VAR_LABEL_MIC_ENERGY_THRESHOLD=StringVar(value="Mic Energy Threshold"),
            VAR_DESC_MIC_ENERGY_THRESHOLD=StringVar(value="Slider to modify the threshold for activating voice input.\nPress the microphone button to start input and speak something, so you can adjust it while monitoring the actual volume. 0 to 2000 (Default: 300)"),
            SLIDER_RANGE_MIC_ENERGY_THRESHOLD=(0, config.MAX_MIC_ENERGY_THRESHOLD),
            CALLBACK_CHECK_MIC_THRESHOLD=None,
            VAR_MIC_ENERGY_THRESHOLD=IntVar(value=config.INPUT_MIC_ENERGY_THRESHOLD),

            VAR_LABEL_MIC_DYNAMIC_ENERGY_THRESHOLD=StringVar(value="Mic Dynamic Energy Threshold"),
            VAR_DESC_MIC_DYNAMIC_ENERGY_THRESHOLD=StringVar(value="When this feature is selected, it will automatically adjust in a way that works well, based on the set Mic Energy Threshold."),
            CALLBACK_SET_MIC_DYNAMIC_ENERGY_THRESHOLD=None,
            VAR_MIC_DYNAMIC_ENERGY_THRESHOLD=BooleanVar(value=config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD),

            VAR_LABEL_MIC_RECORD_TIMEOUT=StringVar(value="Mic Record Timeout"),
            VAR_DESC_MIC_RECORD_TIMEOUT=StringVar(value="(Default: 3)"),
            CALLBACK_SET_MIC_RECORD_TIMEOUT=None,
            VAR_MIC_RECORD_TIMEOUT=IntVar(value=config.INPUT_MIC_RECORD_TIMEOUT),

            VAR_LABEL_MIC_PHRASE_TIMEOUT=StringVar(value="Mic Phrase Timeout"),
            VAR_DESC_MIC_PHRASE_TIMEOUT=StringVar(value="(Default: 3)"),
            CALLBACK_SET_MIC_PHRASE_TIMEOUT=None,
            VAR_MIC_PHRASE_TIMEOUT=IntVar(value=config.INPUT_MIC_PHRASE_TIMEOUT),

            VAR_LABEL_MIC_MAX_PHRASES=StringVar(value="Mic Max Phrases"),
            VAR_DESC_MIC_MAX_PHRASES=StringVar(value="It will stop recording and send the recordings when the set count of phrase(s) is reached. (Default: 10)"),
            CALLBACK_SET_MIC_MAX_PHRASES=None,
            VAR_MIC_MAX_PHRASES=IntVar(value=config.INPUT_MIC_MAX_PHRASES),

            VAR_LABEL_MIC_WORD_FILTER=StringVar(value="Mic Word Filter"),
            VAR_DESC_MIC_WORD_FILTER=StringVar(value="It will not send the sentence if the word(s) included in the set list of words.\nHow to set: e.g. AAA,BBB,CCC"),
            CALLBACK_SET_MIC_WORD_FILTER=None,
            VAR_MIC_WORD_FILTER=StringVar(value=",".join(config.INPUT_MIC_WORD_FILTER) if len(config.INPUT_MIC_WORD_FILTER) > 0 else ""),


            # Transcription Tab (Speaker)
            VAR_LABEL_SPEAKER_DEVICE=StringVar(value="Speaker Device"),
            VAR_DESC_SPEAKER_DEVICE=StringVar(value="Select the speaker devise. (Default: ?)"),
            LIST_SPEAKER_DEVICE=[],
            CALLBACK_SET_SPEAKER_DEVICE=None,
            VAR_SPEAKER_DEVICE=StringVar(value=config.CHOICE_SPEAKER_DEVICE),

            VAR_LABEL_SPEAKER_ENERGY_THRESHOLD=StringVar(value="Mic Energy Threshold"),
            VAR_DESC_SPEAKER_ENERGY_THRESHOLD=StringVar(value="Slider to modify the threshold for activating voice input.\nPress the headphones mark button to start input and speak something, so you can adjust it while monitoring the actual volume. 0 to 4000 (Default: 300)"),
            SLIDER_RANGE_SPEAKER_ENERGY_THRESHOLD=(0, config.MAX_SPEAKER_ENERGY_THRESHOLD),
            CALLBACK_CHECK_SPEAKER_THRESHOLD=None,
            VAR_SPEAKER_ENERGY_THRESHOLD=IntVar(value=config.INPUT_SPEAKER_ENERGY_THRESHOLD),

            VAR_LABEL_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=StringVar(value="Speaker Dynamic Energy Threshold"),
            VAR_DESC_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=StringVar(value="When this feature is selected, it will automatically adjust in a way that works well, based on the set Speaker Energy Threshold."),
            CALLBACK_SET_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=None,
            VAR_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=BooleanVar(value=config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD),

            VAR_LABEL_SPEAKER_RECORD_TIMEOUT=StringVar(value="Speaker Record Timeout"),
            VAR_DESC_SPEAKER_RECORD_TIMEOUT=StringVar(value="(Default: 3)"),
            CALLBACK_SET_SPEAKER_RECORD_TIMEOUT=None,
            VAR_SPEAKER_RECORD_TIMEOUT=IntVar(value=config.INPUT_SPEAKER_RECORD_TIMEOUT),

            VAR_LABEL_SPEAKER_PHRASE_TIMEOUT=StringVar(value="Speaker Phrase Timeout"),
            VAR_DESC_SPEAKER_PHRASE_TIMEOUT=StringVar(value="It will stop recording and receive the recordings when the set second(s) is reached. (Default: 3)"),
            CALLBACK_SET_SPEAKER_PHRASE_TIMEOUT=None,
            VAR_SPEAKER_PHRASE_TIMEOUT=IntVar(value=config.INPUT_SPEAKER_PHRASE_TIMEOUT),

            VAR_LABEL_SPEAKER_MAX_PHRASES=StringVar(value="Speaker Max Phrases"),
            VAR_DESC_SPEAKER_MAX_PHRASES=StringVar(value="It will stop recording and receive the recordings when the set count of phrase(s) is reached. (Default: 10)"),
            CALLBACK_SET_SPEAKER_MAX_PHRASES=None,
            VAR_SPEAKER_MAX_PHRASES=IntVar(value=config.INPUT_SPEAKER_MAX_PHRASES),


            # Others Tab
            VAR_LABEL_ENABLE_AUTO_CLEAR_MESSAGE_BOX=StringVar(value="Auto Clear The Message Box"),
            VAR_DESC_ENABLE_AUTO_CLEAR_MESSAGE_BOX=StringVar(value="Clear the message box after sending your message."),
            CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX=None,
            VAR_ENABLE_AUTO_CLEAR_MESSAGE_BOX=BooleanVar(value=config.ENABLE_AUTO_CLEAR_MESSAGE_BOX),

            VAR_LABEL_ENABLE_NOTICE_XSOVERLAY=StringVar(value="Notification XSOverlay (VR Only)"),
            VAR_DESC_ENABLE_NOTICE_XSOVERLAY=StringVar(value="Notify received messages by using XSOverlay's notification feature."),
            CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY=None,
            VAR_ENABLE_NOTICE_XSOVERLAY=BooleanVar(value=config.ENABLE_NOTICE_XSOVERLAY),

            VAR_LABEL_MESSAGE_FORMAT=StringVar(value="Message Format"),
            VAR_DESC_MESSAGE_FORMAT=StringVar(value="You can change the decoration of the message you want to send. (Default: \"[message]([translation])\" )"),
            CALLBACK_SET_MESSAGE_FORMAT=None,
            VAR_MESSAGE_FORMAT=StringVar(value=config.MESSAGE_FORMAT),


            # Advanced Settings Tab
            VAR_LABEL_OSC_IP_ADDRESS=StringVar(value="OSC IP Address"),
            VAR_DESC_OSC_IP_ADDRESS=StringVar(value="(Default: 127.0.0.1)"),
            CALLBACK_SET_OSC_IP_ADDRESS=None,
            VAR_OSC_IP_ADDRESS=StringVar(value=config.OSC_IP_ADDRESS),

            VAR_LABEL_OSC_PORT=StringVar(value="OSC Port"),
            VAR_DESC_OSC_PORT=StringVar(value="(Default: 9000)"),
            CALLBACK_SET_OSC_PORT=None,
            VAR_OSC_PORT=IntVar(value=config.OSC_PORT),
        )



    def register(self, sidebar_features, language_presets, entry_message_box_commands, config_window):

        self.view_variable.CALLBACK_TOGGLE_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = self._toggleMainWindowSidebarCompactMode

        self.view_variable.CALLBACK_TOGGLE_TRANSLATION = sidebar_features["callback_toggle_translation"]
        self.view_variable.CALLBACK_TOGGLE_TRANSCRIPTION_SEND = sidebar_features["callback_toggle_transcription_send"]
        self.view_variable.CALLBACK_TOGGLE_TRANSCRIPTION_RECEIVE = sidebar_features["callback_toggle_transcription_receive"]
        self.view_variable.CALLBACK_TOGGLE_FOREGROUND = sidebar_features["callback_toggle_foreground"]


        vrct_gui.sls__optionmenu_your_language.configure(values=language_presets["values"])
        vrct_gui.sls__optionmenu_your_language.configure(command=language_presets["callback_your_language"])
        vrct_gui.sls__optionmenu_your_language.configure(variable=StringVar(value=config.SELECTED_TAB_YOUR_LANGUAGES[config.SELECTED_TAB_NO]))
        vrct_gui.sls__optionmenu_target_language.configure(values=language_presets["values"])
        vrct_gui.sls__optionmenu_target_language.configure(command=language_presets["callback_target_language"])
        vrct_gui.sls__optionmenu_target_language.configure(variable=StringVar(value=config.SELECTED_TAB_TARGET_LANGUAGES[config.SELECTED_TAB_NO]))

        self.view_variable.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB = language_presets["callback_selected_language_preset_tab"]
        vrct_gui.setDefaultActiveLanguagePresetTab(tab_no=config.SELECTED_TAB_NO)


        entry_message_box = getattr(vrct_gui, "entry_message_box")
        entry_message_box.bind("<Return>", entry_message_box_commands["bind_Return"])
        entry_message_box.bind("<Any-KeyPress>", entry_message_box_commands["bind_Any_KeyPress"])

        entry_message_box.bind("<FocusIn>", self._foregroundOffForcefully)
        entry_message_box.bind("<FocusOut>", self._foregroundOnForcefully)


        # Config Window
        # Compact Mode Switch
        self.view_variable.CALLBACK_ENABLE_CONFIG_WINDOW_COMPACT_MODE = config_window["callback_disable_config_window_compact_mode"]
        self.view_variable.CALLBACK_DISABLE_CONFIG_WINDOW_COMPACT_MODE = config_window["callback_enable_config_window_compact_mode"]


        # Appearance Tab
        self.view_variable.CALLBACK_SET_TRANSPARENCY = config_window["callback_set_transparency"]

        self.view_variable.CALLBACK_SET_APPEARANCE = config_window["callback_set_appearance"]
        self.view_variable.CALLBACK_SET_UI_SCALING = config_window["callback_set_ui_scaling"]
        self.view_variable.CALLBACK_SET_FONT_FAMILY = config_window["callback_set_font_family"]
        self.view_variable.CALLBACK_SET_UI_LANGUAGE = config_window["callback_set_ui_language"]


        # Translation Tab
        self.view_variable.CALLBACK_SET_DEEPL_AUTHKEY = config_window["callback_set_deepl_authkey"]

        # Transcription Tab (Mic)
        self.view_variable.CALLBACK_SET_MIC_HOST = config_window["callback_set_mic_host"]
        self.updateList_MicHost(config_window["list_mic_host"])

        self.view_variable.CALLBACK_SET_MIC_DEVICE = config_window["callback_set_mic_device"]
        self.updateList_MicDevice(config_window["list_mic_device"])

        self.view_variable.CALLBACK_SET_MIC_ENERGY_THRESHOLD = config_window["callback_set_mic_energy_threshold"]
        self.view_variable.CALLBACK_SET_MIC_DYNAMIC_ENERGY_THRESHOLD = config_window["callback_set_mic_dynamic_energy_threshold"]
        self.view_variable.CALLBACK_CHECK_MIC_THRESHOLD = config_window["callback_check_mic_threshold"]
        self.view_variable.CALLBACK_SET_MIC_RECORD_TIMEOUT = config_window["callback_set_mic_record_timeout"]
        self.view_variable.CALLBACK_SET_MIC_PHRASE_TIMEOUT = config_window["callback_set_mic_phrase_timeout"]
        self.view_variable.CALLBACK_SET_MIC_MAX_PHRASES = config_window["callback_set_mic_max_phrases"]
        self.view_variable.CALLBACK_SET_MIC_WORD_FILTER = config_window["callback_set_mic_word_filter"]

        # Transcription Tab (Speaker)
        self.view_variable.CALLBACK_SET_SPEAKER_DEVICE = config_window["callback_set_speaker_device"]
        self.updateList_SpeakerDevice(config_window["list_speaker_device"])

        self.view_variable.CALLBACK_SET_SPEAKER_ENERGY_THRESHOLD = config_window["callback_set_speaker_energy_threshold"]
        self.view_variable.CALLBACK_SET_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = config_window["callback_set_speaker_dynamic_energy_threshold"]
        self.view_variable.CALLBACK_CHECK_SPEAKER_THRESHOLD = config_window["callback_check_speaker_threshold"]
        self.view_variable.CALLBACK_SET_SPEAKER_RECORD_TIMEOUT = config_window["callback_set_speaker_record_timeout"]
        self.view_variable.CALLBACK_SET_SPEAKER_PHRASE_TIMEOUT = config_window["callback_set_speaker_phrase_timeout"]
        self.view_variable.CALLBACK_SET_SPEAKER_MAX_PHRASES = config_window["callback_set_speaker_max_phrases"]

        # Others Tab
        self.view_variable.CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX = config_window["callback_set_enable_auto_clear_chatbox"]
        self.view_variable.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY = config_window["callback_set_enable_notice_xsoverlay"]
        self.view_variable.CALLBACK_SET_MESSAGE_FORMAT = config_window["callback_set_message_format"]

        # Advanced Settings Tab
        self.view_variable.CALLBACK_SET_OSC_IP_ADDRESS = config_window["callback_set_osc_ip_address"]
        self.view_variable.CALLBACK_SET_OSC_PORT = config_window["callback_set_osc_port"]




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


    def _toggleMainWindowSidebarCompactMode(self, is_turned_on):
        self.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = is_turned_on
        vrct_gui.recreateMainWindowSidebar()


    def updateGuiVariableByPresetTabNo(self, tab_no:str):
        self.view_variable.VAR_YOUR_LANGUAGE.set(config.SELECTED_TAB_YOUR_LANGUAGES[tab_no])
        self.view_variable.VAR_TARGET_LANGUAGE.set(config.SELECTED_TAB_TARGET_LANGUAGES[tab_no])


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

    def printToTextbox_AuthenticationSuccess(self):
        self._printToTextbox_Info("Auth key update completed")

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
        vrct_gui.createGUI(settings=self.settings, view_variable=self.view_variable)

    def startMainLoop(self):
        vrct_gui.startMainLoop()


    # Config Window
    def reloadConfigWindowSettingBoxContainer(self):
        vrct_gui.config_window.settings.IS_CONFIG_WINDOW_COMPACT_MODE = config.IS_CONFIG_WINDOW_COMPACT_MODE
        vrct_gui.config_window.reloadConfigWindowSettingBoxContainer()


    def updateList_MicHost(self, new_mic_host_list:list):
        self.view_variable.LIST_MIC_HOST = new_mic_host_list
        vrct_gui.config_window.sb__optionmenu_mic_host.configure(values=new_mic_host_list)

    def updateSelected_MicHost(self, selected_mic_host_name:str):
        self.view_variable.VAR_MIC_HOST.set(selected_mic_host_name)

    def updateList_MicDevice(self, new_mic_device_list):
        self.view_variable.LIST_MIC_DEVICE = new_mic_device_list
        vrct_gui.config_window.sb__optionmenu_mic_device.configure(values=new_mic_device_list)

    def updateSelected_MicDevice(self, default_selected_mic_device_name:str):
        self.view_variable.VAR_MIC_DEVICE.set(default_selected_mic_device_name)



    def updateList_SpeakerDevice(self, new_speaker_device_list):
        self.view_variable.LIST_SPEAKER_DEVICE = new_speaker_device_list
        vrct_gui.config_window.sb__optionmenu_speaker_device.configure(values=new_speaker_device_list)

view = View()