from os import path as os_path
from typing import Union
from types import SimpleNamespace
from tkinter import font as tk_font
import webbrowser
import i18n

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

        i18n.load_path.append(os_path.join(os_path.dirname(__file__), "locales"))
        i18n.set("fallback", "en") # The fallback language is English.
        i18n.set("skip_locale_root_data", True)
        i18n.set("filename_format", "{locale}.{format}")
        i18n.set("enable_memoization", True)

        i18n.set("locale", config.UI_LANGUAGE)

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
            **common_args
        )

        self.settings.selectable_language_window = SimpleNamespace(
            ctm=all_ctm.selectable_language_window,
            uism=all_uism.config_window,
            **common_args
        )

        self.view_variable = SimpleNamespace(
            # Open Config Window
            CALLBACK_OPEN_CONFIG_WINDOW=None,
            CALLBACK_CLOSE_CONFIG_WINDOW=None,

            # Open Help and Information Page
            CALLBACK_CLICKED_HELP_AND_INFO=self.openWebPage_Booth,

            # Open Update Page
            CALLBACK_CLICKED_UPDATE_AVAILABLE=self.openWebPage_VrctDocuments,


            # Main Window
            # Sidebar
            # Sidebar Compact Mode
            IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE=config.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE,
            CALLBACK_TOGGLE_MAIN_WINDOW_SIDEBAR_COMPACT_MODE=None,

            # Sidebar Features
            VAR_LABEL_TRANSLATION=StringVar(value=i18n.t("main_window.translation")),
            CALLBACK_TOGGLE_TRANSLATION=None,

            VAR_LABEL_TRANSCRIPTION_SEND=StringVar(value=i18n.t("main_window.transcription_send")),
            CALLBACK_TOGGLE_TRANSCRIPTION_SEND=None,

            VAR_LABEL_TRANSCRIPTION_RECEIVE=StringVar(value=i18n.t("main_window.transcription_receive")),
            CALLBACK_TOGGLE_TRANSCRIPTION_RECEIVE=None,

            VAR_LABEL_FOREGROUND=StringVar(value=i18n.t("main_window.foreground")),
            CALLBACK_TOGGLE_FOREGROUND=None,

            # Sidebar Language Settings
            VAR_LABEL_LANGUAGE_SETTINGS=StringVar(value=i18n.t("main_window.language_settings")),
            LIST_SELECTABLE_LANGUAGES=[],
            CALLBACK_SELECTED_LANGUAGE_PRESET_TAB=None,

            VAR_LABEL_YOUR_LANGUAGE=StringVar(value=i18n.t("main_window.your_language")),
            VAR_YOUR_LANGUAGE = StringVar(value="Japanese\n(Japan)"),
            CALLBACK_OPEN_SELECTABLE_YOUR_LANGUAGE_WINDOW=None,
            IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW=False,
            CALLBACK_SELECTED_YOUR_LANGUAGE=None,

            VAR_LABEL_BOTH_DIRECTION_DESC=StringVar(value=i18n.t("main_window.both_direction_desc")),

            VAR_LABEL_TARGET_LANGUAGE=StringVar(value=i18n.t("main_window.target_language")),
            VAR_TARGET_LANGUAGE = StringVar(value="English\n(United States)"),
            CALLBACK_OPEN_SELECTABLE_TARGET_LANGUAGE_WINDOW=None,
            IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW=False,
            CALLBACK_SELECTED_TARGET_LANGUAGE=None,


            VAR_LABEL_TEXTBOX_ALL=StringVar(value=i18n.t("main_window.textbox_tab_all")),
            VAR_LABEL_TEXTBOX_SENT=StringVar(value=i18n.t("main_window.textbox_tab_sent")),
            VAR_LABEL_TEXTBOX_RECEIVED=StringVar(value=i18n.t("main_window.textbox_tab_received")),
            VAR_LABEL_TEXTBOX_SYSTEM=StringVar(value=i18n.t("main_window.textbox_tab_system")),

            VAR_UPDATE_AVAILABLE=StringVar(value=i18n.t("main_window.update_available")),


            # Selectable Language Window
            VAR_TITLE_LABEL_SELECTABLE_LANGUAGE=StringVar(value=""),
            VAR_GO_BACK_LABEL_SELECTABLE_LANGUAGE=StringVar(value=i18n.t("selectable_language_window.go_back_button")),



            # Config Window
            ACTIVE_SETTING_BOX_TAB_ATTR_NAME="side_menu_tab_appearance",
            CALLBACK_SELECTED_SETTING_BOX_TAB=None,
            IS_CONFIG_WINDOW_COMPACT_MODE=config.IS_CONFIG_WINDOW_COMPACT_MODE,

            # Side Menu Labels
            VAR_SIDE_MENU_LABEL_APPEARANCE=StringVar(value=i18n.t("config_window.side_menu_labels.appearance")),
            VAR_SIDE_MENU_LABEL_TRANSLATION=StringVar(value=i18n.t("config_window.side_menu_labels.translation")),
            VAR_SIDE_MENU_LABEL_TRANSCRIPTION=StringVar(value=i18n.t("config_window.side_menu_labels.transcription")),
            VAR_SECOND_TITLE_TRANSCRIPTION_MIC=StringVar(value=i18n.t("config_window.side_menu_labels.transcription_mic")),
            VAR_SECOND_TITLE_TRANSCRIPTION_SPEAKER=StringVar(value=i18n.t("config_window.side_menu_labels.transcription_speaker")),
            VAR_SIDE_MENU_LABEL_OTHERS=StringVar(value=i18n.t("config_window.side_menu_labels.others")),
            VAR_SIDE_MENU_LABEL_ADVANCED_SETTINGS=StringVar(value=i18n.t("config_window.side_menu_labels.advanced_settings")),

            VAR_CURRENT_ACTIVE_CONFIG_TITLE=StringVar(value=""),

            VAR_LABEL_TRANSPARENCY=StringVar(value=i18n.t("config_window.transparency.label")),
            VAR_DESC_TRANSPARENCY=StringVar(value=i18n.t("config_window.transparency.desc")),
            SLIDER_RANGE_TRANSPARENCY=(50, 100),
            CALLBACK_SET_TRANSPARENCY=None,
            VAR_TRANSPARENCY=IntVar(value=config.TRANSPARENCY),

            VAR_LABEL_APPEARANCE_THEME=StringVar(value=i18n.t("config_window.appearance_theme.label")),
            VAR_DESC_APPEARANCE_THEME=StringVar(value=i18n.t("config_window.appearance_theme.desc")),
            LIST_APPEARANCE_THEME=["Light", "Dark", "System"],
            CALLBACK_SET_APPEARANCE_THEME=None,
            VAR_APPEARANCE_THEME=StringVar(value=config.APPEARANCE_THEME),

            VAR_LABEL_UI_SCALING=StringVar(value=i18n.t("config_window.ui_size.label")),
            VAR_DESC_UI_SCALING=None,
            LIST_UI_SCALING=["80%", "90%", "100%", "110%", "120%"],
            CALLBACK_SET_UI_SCALING=None,
            VAR_UI_SCALING=StringVar(value=config.UI_SCALING),

            VAR_LABEL_FONT_FAMILY=StringVar(value=i18n.t("config_window.font_family.label")),
            VAR_DESC_FONT_FAMILY=None,
            LIST_FONT_FAMILY=self.getAvailableFonts(),
            CALLBACK_SET_FONT_FAMILY=None,
            VAR_FONT_FAMILY=StringVar(value=config.FONT_FAMILY),

            VAR_LABEL_UI_LANGUAGE=StringVar(value=i18n.t("config_window.ui_language.label")),
            VAR_DESC_UI_LANGUAGE=None,
            LIST_UI_LANGUAGE=list(selectable_languages.values()),
            CALLBACK_SET_UI_LANGUAGE=None,
            VAR_UI_LANGUAGE=StringVar(value=selectable_languages[config.UI_LANGUAGE]),



            VAR_LABEL_DEEPL_AUTH_KEY=StringVar(value=i18n.t("config_window.deepl_auth_key.label")),
            VAR_DESC_DEEPL_AUTH_KEY=None,
            CALLBACK_SET_DEEPL_AUTH_KEY=None,
            VAR_DEEPL_AUTH_KEY=StringVar(value=config.AUTH_KEYS["DeepL(auth)"]),


            # Transcription Tab (Mic)
            VAR_TAB_SECOND_LABEL_TRANSCRIPTION_MIC=StringVar(value=i18n.t("config_window.tab_transcription.label")),
            VAR_LABEL_MIC_HOST=StringVar(value=i18n.t("config_window.mic_host.label")),
            VAR_DESC_MIC_HOST=None,
            LIST_MIC_HOST=[],
            CALLBACK_SET_MIC_HOST=None,
            VAR_MIC_HOST=StringVar(value=config.CHOICE_MIC_HOST),

            VAR_LABEL_MIC_DEVICE=StringVar(value=i18n.t("config_window.mic_device.label")),
            VAR_DESC_MIC_DEVICE=None,
            LIST_MIC_DEVICE=[],
            CALLBACK_SET_MIC_DEVICE=None,
            VAR_MIC_DEVICE=StringVar(value=config.CHOICE_MIC_DEVICE),

            VAR_LABEL_MIC_ENERGY_THRESHOLD=StringVar(value=i18n.t("config_window.mic_energy_threshold.label")),
            VAR_DESC_MIC_ENERGY_THRESHOLD=StringVar(value=i18n.t("config_window.mic_energy_threshold.desc")),
            SLIDER_RANGE_MIC_ENERGY_THRESHOLD=(0, config.MAX_MIC_ENERGY_THRESHOLD),
            CALLBACK_CHECK_MIC_THRESHOLD=None,
            VAR_MIC_ENERGY_THRESHOLD__SLIDER=IntVar(value=config.INPUT_MIC_ENERGY_THRESHOLD),
            VAR_MIC_ENERGY_THRESHOLD__ENTRY=StringVar(value=config.INPUT_MIC_ENERGY_THRESHOLD),

            VAR_LABEL_MIC_DYNAMIC_ENERGY_THRESHOLD=StringVar(value=i18n.t("config_window.mic_dynamic_energy_threshold.label")),
            VAR_DESC_MIC_DYNAMIC_ENERGY_THRESHOLD=StringVar(value=i18n.t("config_window.mic_dynamic_energy_threshold.desc")),
            CALLBACK_SET_MIC_DYNAMIC_ENERGY_THRESHOLD=None,
            VAR_MIC_DYNAMIC_ENERGY_THRESHOLD=BooleanVar(value=config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD),

            VAR_LABEL_MIC_RECORD_TIMEOUT=StringVar(value=i18n.t("config_window.mic_record_timeout.label")),
            VAR_DESC_MIC_RECORD_TIMEOUT=None,
            CALLBACK_SET_MIC_RECORD_TIMEOUT=None,
            VAR_MIC_RECORD_TIMEOUT=StringVar(value=config.INPUT_MIC_RECORD_TIMEOUT),

            VAR_LABEL_MIC_PHRASE_TIMEOUT=StringVar(value=i18n.t("config_window.mic_phrase_timeout.label")),
            VAR_DESC_MIC_PHRASE_TIMEOUT=None,
            CALLBACK_SET_MIC_PHRASE_TIMEOUT=None,
            VAR_MIC_PHRASE_TIMEOUT=StringVar(value=config.INPUT_MIC_PHRASE_TIMEOUT),

            VAR_LABEL_MIC_MAX_PHRASES=StringVar(value=i18n.t("config_window.mic_max_phrase.label")),
            VAR_DESC_MIC_MAX_PHRASES=StringVar(value=i18n.t("config_window.mic_max_phrase.desc")),
            CALLBACK_SET_MIC_MAX_PHRASES=None,
            VAR_MIC_MAX_PHRASES=StringVar(value=config.INPUT_MIC_MAX_PHRASES),

            VAR_LABEL_MIC_WORD_FILTER=StringVar(value=i18n.t("config_window.mic_word_filter.label")),
            VAR_DESC_MIC_WORD_FILTER=StringVar(value=i18n.t("config_window.mic_word_filter.desc")),
            CALLBACK_SET_MIC_WORD_FILTER=None,
            VAR_MIC_WORD_FILTER=StringVar(value=",".join(config.INPUT_MIC_WORD_FILTER) if len(config.INPUT_MIC_WORD_FILTER) > 0 else ""),


            # Transcription Tab (Speaker)
            VAR_LABEL_SPEAKER_DEVICE=StringVar(value=i18n.t("config_window.speaker_device.label")),
            VAR_DESC_SPEAKER_DEVICE=None,
            LIST_SPEAKER_DEVICE=[],
            CALLBACK_SET_SPEAKER_DEVICE=None,
            VAR_SPEAKER_DEVICE=StringVar(value=config.CHOICE_SPEAKER_DEVICE),

            VAR_LABEL_SPEAKER_ENERGY_THRESHOLD=StringVar(value=i18n.t("config_window.speaker_energy_threshold.label")),
            VAR_DESC_SPEAKER_ENERGY_THRESHOLD=StringVar(value=i18n.t("config_window.speaker_energy_threshold.desc")),
            SLIDER_RANGE_SPEAKER_ENERGY_THRESHOLD=(0, config.MAX_SPEAKER_ENERGY_THRESHOLD),
            CALLBACK_CHECK_SPEAKER_THRESHOLD=None,
            VAR_SPEAKER_ENERGY_THRESHOLD__SLIDER=IntVar(value=config.INPUT_SPEAKER_ENERGY_THRESHOLD),
            VAR_SPEAKER_ENERGY_THRESHOLD__ENTRY=StringVar(value=config.INPUT_SPEAKER_ENERGY_THRESHOLD),

            VAR_LABEL_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=StringVar(value=i18n.t("config_window.speaker_dynamic_energy_threshold.label")),
            VAR_DESC_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=StringVar(value=i18n.t("config_window.speaker_dynamic_energy_threshold.desc")),
            CALLBACK_SET_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=None,
            VAR_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=BooleanVar(value=config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD),

            VAR_LABEL_SPEAKER_RECORD_TIMEOUT=StringVar(value=i18n.t("config_window.speaker_record_timeout.label")),
            VAR_DESC_SPEAKER_RECORD_TIMEOUT=None,
            CALLBACK_SET_SPEAKER_RECORD_TIMEOUT=None,
            VAR_SPEAKER_RECORD_TIMEOUT=StringVar(value=config.INPUT_SPEAKER_RECORD_TIMEOUT),

            VAR_LABEL_SPEAKER_PHRASE_TIMEOUT=StringVar(value=i18n.t("config_window.speaker_phrase_timeout.label")),
            VAR_DESC_SPEAKER_PHRASE_TIMEOUT=None,
            CALLBACK_SET_SPEAKER_PHRASE_TIMEOUT=None,
            VAR_SPEAKER_PHRASE_TIMEOUT=StringVar(value=config.INPUT_SPEAKER_PHRASE_TIMEOUT),

            VAR_LABEL_SPEAKER_MAX_PHRASES=StringVar(value=i18n.t("config_window.speaker_max_phrase.label")),
            VAR_DESC_SPEAKER_MAX_PHRASES=StringVar(value=i18n.t("config_window.speaker_max_phrase.desc")),
            CALLBACK_SET_SPEAKER_MAX_PHRASES=None,
            VAR_SPEAKER_MAX_PHRASES=StringVar(value=config.INPUT_SPEAKER_MAX_PHRASES),


            # Others Tab
            VAR_LABEL_ENABLE_AUTO_CLEAR_MESSAGE_BOX=StringVar(value=i18n.t("config_window.auto_clear_the_message_box.label")),
            VAR_DESC_ENABLE_AUTO_CLEAR_MESSAGE_BOX=None,
            CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX=None,
            VAR_ENABLE_AUTO_CLEAR_MESSAGE_BOX=BooleanVar(value=config.ENABLE_AUTO_CLEAR_MESSAGE_BOX),

            VAR_LABEL_ENABLE_NOTICE_XSOVERLAY=StringVar(value=i18n.t("config_window.notice_xsoverlay.label")),
            VAR_DESC_ENABLE_NOTICE_XSOVERLAY=StringVar(value=i18n.t("config_window.notice_xsoverlay.desc")),
            CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY=None,
            VAR_ENABLE_NOTICE_XSOVERLAY=BooleanVar(value=config.ENABLE_NOTICE_XSOVERLAY),

            VAR_LABEL_ENABLE_AUTO_EXPORT_MESSAGE_LOGS=StringVar(value=i18n.t("config_window.auto_export_message_logs.label")),
            VAR_DESC_ENABLE_AUTO_EXPORT_MESSAGE_LOGS=StringVar(value=i18n.t("config_window.auto_export_message_logs.desc")),
            CALLBACK_SET_ENABLE_AUTO_EXPORT_MESSAGE_LOGS=None,
            VAR_ENABLE_AUTO_EXPORT_MESSAGE_LOGS=BooleanVar(value=config.ENABLE_LOGGER),


            VAR_LABEL_MESSAGE_FORMAT=StringVar(value=i18n.t("config_window.message_format.label")),
            VAR_DESC_MESSAGE_FORMAT=StringVar(value=i18n.t("config_window.message_format.desc")),
            CALLBACK_SET_MESSAGE_FORMAT=None,
            VAR_MESSAGE_FORMAT=StringVar(value=config.MESSAGE_FORMAT),


            VAR_LABEL_ENABLE_SEND_MESSAGE_TO_VRC=StringVar(value=i18n.t("config_window.send_message_to_vrc.label")),
            VAR_DESC_ENABLE_SEND_MESSAGE_TO_VRC=StringVar(value=i18n.t("config_window.send_message_to_vrc.desc")),
            CALLBACK_SET_ENABLE_SEND_MESSAGE_TO_VRC=None,
            VAR_ENABLE_SEND_MESSAGE_TO_VRC=BooleanVar(value=config.ENABLE_SEND_MESSAGE_TO_VRC),

            VAR_LABEL_STARTUP_OSC_ENABLED_CHECK=StringVar(value=i18n.t("config_window.startup_osc_enabled_check.label")),
            VAR_DESC_STARTUP_OSC_ENABLED_CHECK=StringVar(value=i18n.t("config_window.startup_osc_enabled_check.desc")),
            CALLBACK_SET_STARTUP_OSC_ENABLED_CHECK=None,
            VAR_STARTUP_OSC_ENABLED_CHECK=BooleanVar(value=config.STARTUP_OSC_ENABLED_CHECK),




            # Advanced Settings Tab
            VAR_LABEL_OSC_IP_ADDRESS=StringVar(value=i18n.t("config_window.osc_ip_address.label")),
            VAR_DESC_OSC_IP_ADDRESS=None,
            CALLBACK_SET_OSC_IP_ADDRESS=None,
            VAR_OSC_IP_ADDRESS=StringVar(value=config.OSC_IP_ADDRESS),

            VAR_LABEL_OSC_PORT=StringVar(value=i18n.t("config_window.osc_port.label")),
            VAR_DESC_OSC_PORT=None,
            CALLBACK_SET_OSC_PORT=None,
            VAR_OSC_PORT=StringVar(value=config.OSC_PORT),
        )



    def register(
            self,
            window_action_registers=None,
            main_window_registers=None,
            config_window_registers=None
        ):


        # Open Config Window
        if window_action_registers is not None:
            self.view_variable.CALLBACK_OPEN_CONFIG_WINDOW=window_action_registers.get("callback_open_config_window", None)
            self.view_variable.CALLBACK_CLOSE_CONFIG_WINDOW=window_action_registers.get("callback_close_config_window", None)




        if main_window_registers is not None:
            self.view_variable.CALLBACK_ENABLE_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = main_window_registers.get("callback_enable_main_window_sidebar_compact_mode", None)
            self.view_variable.CALLBACK_DISABLE_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = main_window_registers.get("callback_disable_main_window_sidebar_compact_mode", None)


            self.view_variable.CALLBACK_TOGGLE_TRANSLATION = main_window_registers.get("callback_toggle_translation", None)
            self.view_variable.CALLBACK_TOGGLE_TRANSCRIPTION_SEND = main_window_registers.get("callback_toggle_transcription_send", None)
            self.view_variable.CALLBACK_TOGGLE_TRANSCRIPTION_RECEIVE = main_window_registers.get("callback_toggle_transcription_receive", None)
            self.view_variable.CALLBACK_TOGGLE_FOREGROUND = main_window_registers.get("callback_toggle_foreground", None)

            self.view_variable.CALLBACK_SELECTED_YOUR_LANGUAGE = main_window_registers.get("callback_your_language", None)
            self.view_variable.CALLBACK_SELECTED_TARGET_LANGUAGE = main_window_registers.get("callback_target_language", None)
            main_window_registers.get("values", None) and self.updateList_selectableLanguages(main_window_registers["values"])

            self.view_variable.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB = main_window_registers.get("callback_selected_language_preset_tab", None)


            entry_message_box = getattr(vrct_gui, "entry_message_box")
            entry_message_box.bind("<Return>", main_window_registers.get("bind_Return"))
            entry_message_box.bind("<Any-KeyPress>", main_window_registers.get("bind_Any_KeyPress"))


            entry_message_box.bind("<FocusIn>", self._foregroundOffForcefully)
            entry_message_box.bind("<FocusOut>", self._foregroundOnForcefully)

        self.updateGuiVariableByPresetTabNo(config.SELECTED_TAB_NO)
        vrct_gui.setDefaultActiveLanguagePresetTab(tab_no=config.SELECTED_TAB_NO)

        # Config Window
        self.view_variable.CALLBACK_SELECTED_SETTING_BOX_TAB=self._updateActiveSettingBoxTabNo

        # Compact Mode Switch
        if config_window_registers is not None:

            self.view_variable.CALLBACK_ENABLE_CONFIG_WINDOW_COMPACT_MODE = config_window_registers.get("callback_disable_config_window_compact_mode", None)
            self.view_variable.CALLBACK_DISABLE_CONFIG_WINDOW_COMPACT_MODE = config_window_registers.get("callback_enable_config_window_compact_mode", None)


            # Appearance Tab
            self.view_variable.CALLBACK_SET_TRANSPARENCY = config_window_registers.get("callback_set_transparency", None)

            self.view_variable.CALLBACK_SET_APPEARANCE = config_window_registers.get("callback_set_appearance", None)
            self.view_variable.CALLBACK_SET_UI_SCALING = config_window_registers.get("callback_set_ui_scaling", None)
            self.view_variable.CALLBACK_SET_FONT_FAMILY = config_window_registers.get("callback_set_font_family", None)
            self.view_variable.CALLBACK_SET_UI_LANGUAGE = config_window_registers.get("callback_set_ui_language", None)


            # Translation Tab
            self.view_variable.CALLBACK_SET_DEEPL_AUTHKEY = config_window_registers.get("callback_set_deepl_authkey", None)

            # Transcription Tab (Mic)
            self.view_variable.CALLBACK_SET_MIC_HOST = config_window_registers.get("callback_set_mic_host", None)
            config_window_registers.get("list_mic_host", None) and self.updateList_MicHost(config_window_registers["list_mic_host"])

            self.view_variable.CALLBACK_SET_MIC_DEVICE = config_window_registers.get("callback_set_mic_device", None)
            config_window_registers.get("list_mic_device", None) and self.updateList_MicDevice(config_window_registers["list_mic_device"])

            self.view_variable.CALLBACK_SET_MIC_ENERGY_THRESHOLD = config_window_registers.get("callback_set_mic_energy_threshold", None)
            self.view_variable.CALLBACK_SET_MIC_DYNAMIC_ENERGY_THRESHOLD = config_window_registers.get("callback_set_mic_dynamic_energy_threshold", None)
            self.view_variable.CALLBACK_CHECK_MIC_THRESHOLD = config_window_registers.get("callback_check_mic_threshold", None)
            self.view_variable.CALLBACK_SET_MIC_RECORD_TIMEOUT = config_window_registers.get("callback_set_mic_record_timeout", None)
            self.view_variable.CALLBACK_SET_MIC_PHRASE_TIMEOUT = config_window_registers.get("callback_set_mic_phrase_timeout", None)
            self.view_variable.CALLBACK_SET_MIC_MAX_PHRASES = config_window_registers.get("callback_set_mic_max_phrases", None)
            self.view_variable.CALLBACK_SET_MIC_WORD_FILTER = config_window_registers.get("callback_set_mic_word_filter", None)

            # Transcription Tab (Speaker)
            self.view_variable.CALLBACK_SET_SPEAKER_DEVICE = config_window_registers.get("callback_set_speaker_device", None)
            config_window_registers.get("list_speaker_device", None) and self.updateList_SpeakerDevice(config_window_registers["list_speaker_device"])

            self.view_variable.CALLBACK_SET_SPEAKER_ENERGY_THRESHOLD = config_window_registers.get("callback_set_speaker_energy_threshold", None)
            self.view_variable.CALLBACK_SET_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = config_window_registers.get("callback_set_speaker_dynamic_energy_threshold", None)
            self.view_variable.CALLBACK_CHECK_SPEAKER_THRESHOLD = config_window_registers.get("callback_check_speaker_threshold", None)
            self.view_variable.CALLBACK_SET_SPEAKER_RECORD_TIMEOUT = config_window_registers.get("callback_set_speaker_record_timeout", None)
            self.view_variable.CALLBACK_SET_SPEAKER_PHRASE_TIMEOUT = config_window_registers.get("callback_set_speaker_phrase_timeout", None)
            self.view_variable.CALLBACK_SET_SPEAKER_MAX_PHRASES = config_window_registers.get("callback_set_speaker_max_phrases", None)

            # Others Tab
            self.view_variable.CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX = config_window_registers.get("callback_set_enable_auto_clear_chatbox", None)
            self.view_variable.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY = config_window_registers.get("callback_set_enable_notice_xsoverlay", None)
            self.view_variable.CALLBACK_SET_ENABLE_AUTO_EXPORT_MESSAGE_LOGS =  config_window_registers.get("callback_set_enable_auto_export_message_logs", None)
            self.view_variable.CALLBACK_SET_MESSAGE_FORMAT = config_window_registers.get("callback_set_message_format", None)

            self.view_variable.CALLBACK_SET_ENABLE_SEND_MESSAGE_TO_VRC = config_window_registers.get("callback_set_enable_send_message_to_vrc", None)
            self.view_variable.CALLBACK_SET_STARTUP_OSC_ENABLED_CHECK = config_window_registers.get("callback_set_startup_osc_enabled_check", None)

            # Advanced Settings Tab
            self.view_variable.CALLBACK_SET_OSC_IP_ADDRESS = config_window_registers.get("callback_set_osc_ip_address", None)
            self.view_variable.CALLBACK_SET_OSC_PORT = config_window_registers.get("callback_set_osc_port", None)

        # Insert sample conversation for testing.
        # self._insertSampleConversationToTextbox()


    @staticmethod
    def getAvailableFonts():
        available_fonts = list(tk_font.families())
        available_fonts.sort()
        filtered_available_fonts = list(filter(lambda x: x.startswith("@") is False, available_fonts))
        return filtered_available_fonts

    @staticmethod
    def openWebPage(url:str):
        webbrowser.open_new_tab(url)

    def openWebPage_Booth(self):
        self.openWebPage(config.BOOTH_URL)
        self._printToTextbox_Info("Opened Booth page in your web browser.")

    def openWebPage_VrctDocuments(self):
        self.openWebPage(config.DOCUMENTS_URL)
        self._printToTextbox_Info("Opened the VRCT Documents page in your web browser.")

    @staticmethod
    def showUpdateAvailableButton():
        vrct_gui.update_available_container.grid()

    @staticmethod
    def setMainWindowAllWidgetsStatusToNormal():
        vrct_gui.changeMainWindowWidgetsStatus("normal", "All")

    @staticmethod
    def setMainWindowAllWidgetsStatusToDisabled():
        vrct_gui.changeMainWindowWidgetsStatus("disabled", "All")



    def _foregroundOnForcefully(self, _e):
        if config.ENABLE_FOREGROUND:
            self.foregroundOn()

    def _foregroundOffForcefully(self, _e):
        if config.ENABLE_FOREGROUND:
            self.foregroundOff()


    @staticmethod
    def foregroundOn():
        vrct_gui.attributes("-topmost", True)

    @staticmethod
    def foregroundOff():
        vrct_gui.attributes("-topmost", False)


    def enableMainWindowSidebarCompactMode(self):
        self.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
        vrct_gui.enableMainWindowSidebarCompactMode()

    def disableMainWindowSidebarCompactMode(self):
        self.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
        vrct_gui.disableMainWindowSidebarCompactMode()

    def openSelectableLanguagesWindow_YourLanguage(self, _e):
        self.view_variable.VAR_TITLE_LABEL_SELECTABLE_LANGUAGE.set(i18n.t("selectable_language_window.title_your_language"))
        vrct_gui.openSelectableLanguagesWindow("your_language")

    def openSelectableLanguagesWindow_TargetLanguage(self, _e):
        self.view_variable.VAR_TITLE_LABEL_SELECTABLE_LANGUAGE.set(i18n.t("selectable_language_window.title_target_language"))
        vrct_gui.openSelectableLanguagesWindow("target_language")


    def updateGuiVariableByPresetTabNo(self, tab_no:str):
        self.view_variable.VAR_YOUR_LANGUAGE.set(config.SELECTED_TAB_YOUR_LANGUAGES[tab_no])
        self.view_variable.VAR_TARGET_LANGUAGE.set(config.SELECTED_TAB_TARGET_LANGUAGES[tab_no])


    def updateList_selectableLanguages(self, new_selectable_language_list:list):
        self.view_variable.LIST_SELECTABLE_LANGUAGES = new_selectable_language_list


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
        self._printToTextbox_Info("Auth Key is incorrect or Usage limit reached")

    def printToTextbox_OSCError(self):
        self._printToTextbox_Info("OSC is not enabled, please enable OSC and rejoin. or turn off the \"Send Message To VRChat\" setting")

    def printToTextbox_DetectedByWordFilter(self, detected_message):
        self._printToTextbox_Info(f"Detect WordFilter :{detected_message}")



    def printToTextbox_selectedYourLanguages(self, selected_your_language):
        your_language = selected_your_language.replace("\n", " ")
        self._printToTextbox_Info(f"Your Language has changed : {your_language}")

    def printToTextbox_selectedTargetLanguages(self, selected_target_language):
        target_language = selected_target_language.replace("\n", " ")
        self._printToTextbox_Info(f"Target Language has changed : {target_language}")

    def printToTextbox_latestSelectedLanguages(self):
        your_language = self.view_variable.VAR_YOUR_LANGUAGE.get().replace("\n", " ")
        target_language = self.view_variable.VAR_TARGET_LANGUAGE.get().replace("\n", " ")
        self._printToTextbox_Info(f"Your Language : {your_language} -- Target Language : {target_language}")

    def printToTextbox_changedLanguagePresetTab(self, tab_no:str):
        your_language = config.SELECTED_TAB_YOUR_LANGUAGES[tab_no].replace("\n", " ")
        target_language = config.SELECTED_TAB_TARGET_LANGUAGES[tab_no].replace("\n", " ")
        self._printToTextbox_Info(f"Switched Language Preset. No.{tab_no}\nYour Language : {your_language} -- Target Language : {target_language}")


    @staticmethod
    def _printToTextbox_Info(info_message):
        vrct_gui.printToTextbox(
            target_type="SYSTEM",
            original_message=info_message,
            # translated_message="",
        )



    def printToTextbox_SentMessage(self, original_message, translated_message):
        self._printToTextbox_Sent(original_message, translated_message)

    @staticmethod
    def _printToTextbox_Sent(original_message, translated_message):
        vrct_gui.printToTextbox(
            target_type="SENT",
            original_message=original_message,
            translated_message=translated_message,
        )


    def printToTextbox_ReceivedMessage(self, original_message, translated_message):
        self._printToTextbox_Received(original_message, translated_message)

    @staticmethod
    def _printToTextbox_Received(original_message, translated_message):
        vrct_gui.printToTextbox(
            target_type="RECEIVED",
            original_message=original_message,
            translated_message=translated_message,
        )


    @staticmethod
    def getTextFromMessageBox():
        return vrct_gui.entry_message_box.get()

    @staticmethod
    def clearMessageBox():
        vrct_gui.entry_message_box.delete(0, CTK_END)

    @staticmethod
    def setMainWindowTransparency(transparency:float):
        vrct_gui.wm_attributes("-alpha", transparency)



    def createGUI(self):
        vrct_gui.createGUI(settings=self.settings, view_variable=self.view_variable)

    @staticmethod
    def startMainLoop():
        vrct_gui.startMainLoop()


    # Config Window
    def _updateActiveSettingBoxTabNo(self, active_setting_box_tab_attr_name:str):
        self.view_variable.ACTIVE_SETTING_BOX_TAB_ATTR_NAME = active_setting_box_tab_attr_name

    @staticmethod
    def setWidgetsStatus_ConfigWindowCompactModeSwitch_Disabled():
        vrct_gui.config_window.setting_box_compact_mode_switch_box.configure(state="disabled")

    @staticmethod
    def setWidgetsStatus_ConfigWindowCompactModeSwitch_Normal():
        vrct_gui.config_window.setting_box_compact_mode_switch_box.configure(state="normal")

    @staticmethod
    def setWidgetsStatus_ThresholdCheckButton_Disabled():
        vrct_gui.changeConfigWindowWidgetsStatus(
            status="disabled",
            target_names=[
                "mic_energy_threshold_check_button",
                "speaker_energy_threshold_check_button",
            ]
        )

    @staticmethod
    def setWidgetsStatus_ThresholdCheckButton_Normal():
        vrct_gui.changeConfigWindowWidgetsStatus(
            status="normal",
            target_names=[
                "mic_energy_threshold_check_button",
                "speaker_energy_threshold_check_button",
            ]
        )

    @staticmethod
    def replaceMicThresholdCheckButton_Active():
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_mic_energy_threshold.grid()

    @staticmethod
    def replaceMicThresholdCheckButton_Passive():
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_mic_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold.grid()



    @staticmethod
    def replaceSpeakerThresholdCheckButton_Active():
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_speaker_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_speaker_energy_threshold.grid()

    @staticmethod
    def replaceSpeakerThresholdCheckButton_Passive():
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_speaker_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_speaker_energy_threshold.grid()



    def reloadConfigWindowSettingBoxContainer(self):
        self.view_variable.IS_CONFIG_WINDOW_COMPACT_MODE = config.IS_CONFIG_WINDOW_COMPACT_MODE
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


    @staticmethod
    def updateSetProgressBar_MicEnergy(new_mic_energy):
        vrct_gui.config_window.sb__progressbar_x_slider__progressbar_mic_energy_threshold.set(new_mic_energy/config.MAX_MIC_ENERGY_THRESHOLD)

    @staticmethod
    def initProgressBar_MicEnergy():
        vrct_gui.config_window.sb__progressbar_x_slider__progressbar_mic_energy_threshold.set(0)


    def updateList_SpeakerDevice(self, new_speaker_device_list):
        self.view_variable.LIST_SPEAKER_DEVICE = new_speaker_device_list
        vrct_gui.config_window.sb__optionmenu_speaker_device.configure(values=new_speaker_device_list)

    @staticmethod
    def updateSetProgressBar_SpeakerEnergy(new_speaker_energy):
        vrct_gui.config_window.sb__progressbar_x_slider__progressbar_speaker_energy_threshold.set(new_speaker_energy/config.MAX_SPEAKER_ENERGY_THRESHOLD)

    @staticmethod
    def initProgressBar_SpeakerEnergy():
        vrct_gui.config_window.sb__progressbar_x_slider__progressbar_speaker_energy_threshold.set(0)



    def setGuiVariable_MicEnergyThreshold(self, slider_value:int, entry_value:Union[None, str]=None):
        self.view_variable.VAR_MIC_ENERGY_THRESHOLD__SLIDER.set(slider_value)
        if entry_value is None:
            self._clearEntryBox(vrct_gui.config_window.sb__progressbar_x_slider__entry_mic_energy_threshold)
        else:
            self.view_variable.VAR_MIC_ENERGY_THRESHOLD__ENTRY.set(entry_value)

    def setGuiVariable_SpeakerEnergyThreshold(self, slider_value:int, entry_value:Union[None, str]=None):
        self.view_variable.VAR_SPEAKER_ENERGY_THRESHOLD__SLIDER.set(slider_value)
        if entry_value is None:
            self._clearEntryBox(vrct_gui.config_window.sb__progressbar_x_slider__entry_speaker_energy_threshold)
        else:
            self.view_variable.VAR_SPEAKER_ENERGY_THRESHOLD__ENTRY.set(entry_value)



    def setGuiVariable_MicRecordTimeout(self, value:str="", delete=False):
        if delete is True: self._clearEntryBox(vrct_gui.config_window.sb__entry_mic_record_timeout)
        self.view_variable.VAR_MIC_RECORD_TIMEOUT.set(value)

    def setGuiVariable_MicPhraseTimeout(self, value:str="", delete=False):
        if delete is True: self._clearEntryBox(vrct_gui.config_window.sb__entry_mic_phrase_timeout)
        self.view_variable.VAR_MIC_PHRASE_TIMEOUT.set(value)

    def setGuiVariable_MicMaxPhrases(self, value:str="", delete=False):
        if delete is True: self._clearEntryBox(vrct_gui.config_window.sb__entry_mic_max_phrases)
        self.view_variable.VAR_MIC_MAX_PHRASES.set(value)



    def setGuiVariable_SpeakerRecordTimeout(self, value:str="", delete=False):
        if delete is True: self._clearEntryBox(vrct_gui.config_window.sb__entry_speaker_record_timeout)
        self.view_variable.VAR_SPEAKER_RECORD_TIMEOUT.set(value)

    def setGuiVariable_SpeakerPhraseTimeout(self, value:str="", delete=False):
        if delete is True: self._clearEntryBox(vrct_gui.config_window.sb__entry_speaker_phrase_timeout)
        self.view_variable.VAR_SPEAKER_PHRASE_TIMEOUT.set(value)

    def setGuiVariable_SpeakerMaxPhrases(self, value:str="", delete=False):
        if delete is True: self._clearEntryBox(vrct_gui.config_window.sb__entry_speaker_max_phrases)
        self.view_variable.VAR_SPEAKER_MAX_PHRASES.set(value)


    @staticmethod
    def _clearEntryBox(entry_widget):
        entry_widget.delete(0, CTK_END)




    # These conversations are generated by ChatGPT
    def _insertSampleConversationToTextbox(self):

        self.printToTextbox_enableTranscriptionSend()
        self.printToTextbox_enableTranscriptionReceive()

        conversation_data_without_translation = [
            {
                "me": "おはよう。",
            },
            {
                "me": "おはよう。",
                "target": "やぁ。",
            },
            {
                "me": "今日の天気はどうかな？",
                "target": "天気予報を見てないけど、晴れるといいね。",
            },
            {
                "me": "そうだね。昨日は雨だったから。",
                "target": "それで、今日の予定は？",
            },
        ]

        for data in conversation_data_without_translation:
            if data.get("me", None) is not None:
                self.printToTextbox_SentMessage(data.get("me", None), data.get("me_t", None))
            if data.get("target", None) is not None:
                self.printToTextbox_ReceivedMessage(data.get("target", None), data.get("target_t", None))

        self.printToTextbox_enableTranslation()

        conversation_data = [
            {
                "me": "I have work in the morning, but I'm meeting friends for dinner in the evening.",
                "me_t": "아침에 일이 있지만 저녁에 친구들과 만나 저녁 식사할 예정이에요.",
                "target": "재미있어 보여요! 무엇을 먹을 예정이에요?",
                "target_t": "Sounds fun! What are you planning to eat?"
            },
            {
                "me": "We're going to an Italian restaurant, and I'm going to have pizza.",
                "me_t": "우리는 이탈리안 레스토랑에 가서 피자를 먹을 거에요.",
                "target": "그걸 듣자마자 배가 고파져요. 언젠가 함께하고 싶어요.",
                "target_t": "Just hearing that makes me hungry. I'd love to join you sometime."
            },
            {
                "me": "Let's plan it for next time!",
                "me_t": "다음 번에 계획해 봐요!",
                "target": "그래요!",
                "target_t": "Sure!"
            },
            {
                "me": "When would be a good time for you?",
                "me_t": "너에게 언제가 좋을까?",
                "target": "나는 주말이 가장 좋을 것 같아요. 토요일은 어때요?",
                "target_t": "I think the weekend works best for me. How about Saturday?"
            },
            {
                "me": "Saturday sounds perfect. What time would be convenient?",
                "me_t": "토요일이 완벽해 보여. 편한 시간은 언제인가요?",
                "target": "저는 저녁이 괜찮아요. 7시쯤 괜찮을까요?",
                "target_t": "Evening works for me. Is around 7 PM okay?"
            },
            {
                "me": "7 PM works great. Do you have any preferences for food other than Italian?",
                "me_t": "7시가 아주 적당해. 이탈리안 음식 이외에 어떤 음식을 좋아하세요?",
                "target": "특별한 선호도는 없어요. 무엇이든 괜찮아요. 추천 디저트가 있다면 알려주세요.",
                "target_t": "I don't have any particular preferences, so anything is fine. If there's a recommended dessert, let me know."
            },


            {
                "me": "朝は仕事があるけど、夜は友達と食事に行く予定だよ。",
                "me_t": "I have work in the morning, but I'm meeting friends for dinner in the evening.",
                "target": "Sounds fun! What are you planning to eat?",
                "target_t": "楽しそう！何を食べる予定？",
            },
            {
                "me": "イタリアンレストランに行って、ピザを食べるつもりだよ。",
                "me_t": "We're going to an Italian restaurant, and I'm going to have pizza.",
                "target": "Just hearing that makes me hungry. I'd love to join you sometime.",
                "target_t": "それ聞いただけでおなかすいたよ。私も一緒に行きたいな。",
            },
            {
                "me": "次回にぜひ一緒に行こう！",
                "me_t": "Let's plan it for next time!",
                "target": "Sure!",
                "target_t": "そうだね！",
            },
            {
                "me": "次回はいつがいいかな？",
                "me_t": "When would be a good time for you?",
                "target": "I think the weekend works best for me. How about Saturday?",
                "target_t": "私は週末が一番いいかな。土曜日はどう？"
            },
            {
                "me": "土曜日はちょうどいいね。何時ごろが良いかな？",
                "me_t": "Saturday sounds perfect. What time would be convenient?",
                "target": "Evening works for me. Is around 7 PM okay?",
                "target_t": "夜がいいかな。7時くらいからがちょうど良いかな。"
            },
            {
                "me": "7時からはちょうどいいよ。イタリアン以外の食べ物について何か好みがある？",
                "me_t": "7 PM works great. Do you have any preferences for food other than Italian?",
                "target": "I don't have any particular preferences, so anything is fine. If there's a recommended dessert, let me know.",
                "target_t": "特に好みはないから、何でも大丈夫。おすすめのデザートがあれば教えてね。"
            },
        ]
        for data in conversation_data:
            if data.get("me", None) is not None:
                self.printToTextbox_SentMessage(data.get("me", None), data.get("me_t", None))
            if data.get("target", None) is not None:
                self.printToTextbox_ReceivedMessage(data.get("target", None), data.get("target_t", None))


view = View()