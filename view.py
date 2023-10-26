from typing import Union
from os import path as os_path
from types import SimpleNamespace
from tkinter import font as tk_font
import webbrowser
import i18n

from languages import selectable_languages

from customtkinter import StringVar, IntVar, BooleanVar, END as CTK_END, get_appearance_mode
from vrct_gui.ui_managers import ColorThemeManager, ImageFileManager, UiScalingManager
from vrct_gui import vrct_gui
from utils import callFunctionIfCallable, generatePercentageStringsList, intToPercentageStringsFormatter

from config import config

class View():
    def __init__(self):
        # Localization
        i18n.load_path.append(os_path.join(os_path.dirname(__file__), "locales"))
        i18n.set("fallback", "en") # The fallback language is English.
        i18n.set("skip_locale_root_data", True)
        i18n.set("filename_format", "{locale}.{format}")
        i18n.set("enable_memoization", True)
        i18n.set("locale", config.UI_LANGUAGE)

        # Save settings at startup for items that require a restart VRCT for the changes to apply
        self.restart_required_configs_pre_data = SimpleNamespace(
            appearance_theme=config.APPEARANCE_THEME,
            ui_scaling=config.UI_SCALING,
            font_family=config.FONT_FAMILY,
            ui_language=config.UI_LANGUAGE,
        )

        self.settings = SimpleNamespace()
        # theme = get_appearance_mode() if config.APPEARANCE_THEME == "System" else config.APPEARANCE_THEME
        theme = "Dark"
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
            **common_args
        )

        self.settings.config_window = SimpleNamespace(
            ctm=all_ctm.config_window,
            uism=all_uism.config_window,
            **common_args
        )

        self.settings.selectable_language_window = SimpleNamespace(
            ctm=all_ctm.selectable_language_window,
            uism=all_uism.selectable_language_window,
            **common_args
        )

        self.settings.main_window_cover = SimpleNamespace(
            ctm=all_ctm.main_window_cover,
            uism=all_uism.main_window_cover,
            **common_args
        )

        self.settings.error_message_window = SimpleNamespace(
            ctm=all_ctm.error_message_window,
            uism=all_uism.error_message_window,
            **common_args
        )

        self.settings.confirmation_modal = SimpleNamespace(
            ctm=all_ctm.confirmation_modal,
            uism=all_uism.confirmation_modal,
            **common_args
        )

        self.view_variable = SimpleNamespace(
            # Common
            CALLBACK_RESTART_SOFTWARE=None,
            CALLBACK_UPDATE_SOFTWARE=None,

            CALLBACK_QUIT_VRCT=vrct_gui._quitVRCT,

            CALLBACK_WHEN_DETECT_WINDOW_OVERED_SIZE=self._showDisplayOverUiSizeConfirmationModal,

            # Confirmation Modal
            CALLBACK_HIDE_CONFIRMATION_MODAL=None,
            CALLBACK_ACCEPTED_CONFIRMATION_MODAL=None,
            CALLBACK_DENIED_CONFIRMATION_MODAL=None,
            VAR_MESSAGE_CONFIRMATION_MODAL=StringVar(value=""),
            VAR_LABEL_CONFIRMATION_MODAL_DENY_BUTTON=StringVar(value=""),
            VAR_LABEL_CONFIRMATION_MODAL_ACCEPT_BUTTON=StringVar(value=""),

            # Window Control (Config Window)
            CALLBACK_CLICKED_OPEN_CONFIG_WINDOW_BUTTON=self._openConfigWindow,
            CALLBACK_CLICKED_CLOSE_CONFIG_WINDOW_BUTTON=self._closeConfigWindow,
            CALLBACK_OPEN_CONFIG_WINDOW=None,
            CALLBACK_CLOSE_CONFIG_WINDOW=None,

            # Open Help and Information Page
            CALLBACK_CLICKED_HELP_AND_INFO=self.openWebPage_VrctDocuments,

            # Open Update Confirmation Modal
            CALLBACK_CLICKED_UPDATE_AVAILABLE=self._showUpdateSoftwareConfirmationModal,



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


            # Main Window Cover
            VAR_LABEL_MAIN_WINDOW_COVER_MESSAGE=StringVar(value=""),

            # Selectable Language Window
            VAR_TITLE_LABEL_SELECTABLE_LANGUAGE=StringVar(value=""),
            VAR_GO_BACK_LABEL_SELECTABLE_LANGUAGE=StringVar(value=i18n.t("selectable_language_window.go_back_button")),



            # Config Window
            ACTIVE_SETTING_BOX_TAB_ATTR_NAME="side_menu_tab_appearance",
            CALLBACK_SELECTED_SETTING_BOX_TAB=None,
            VAR_ERROR_MESSAGE=StringVar(value=""),
            VAR_VERSION=StringVar(value=i18n.t("config_window.version", version=config.VERSION)),
            VAR_CONFIG_WINDOW_TITLE=StringVar(value=i18n.t("config_window.config_title")),
            VAR_CONFIG_WINDOW_COMPACT_MODE_LABEL=StringVar(value=i18n.t("config_window.compact_mode")),
            VAR_CONFIG_WINDOW_RESTART_BUTTON_LABEL=StringVar(value=i18n.t("config_window.restart_message")),

            CALLBACK_SLIDER_TOOLTIP_PERCENTAGE_FORMATTER=intToPercentageStringsFormatter,


            # Side Menu Labels
            VAR_SIDE_MENU_LABEL_APPEARANCE=StringVar(value=i18n.t("config_window.side_menu_labels.appearance")),
            VAR_SIDE_MENU_LABEL_TRANSLATION=StringVar(value=i18n.t("config_window.side_menu_labels.translation")),
            VAR_SIDE_MENU_LABEL_TRANSCRIPTION=StringVar(value=i18n.t("config_window.side_menu_labels.transcription")),
            VAR_SECOND_TITLE_TRANSCRIPTION_MIC=StringVar(value=i18n.t("config_window.side_menu_labels.transcription_mic")),
            VAR_SECOND_TITLE_TRANSCRIPTION_SPEAKER=StringVar(value=i18n.t("config_window.side_menu_labels.transcription_speaker")),
            VAR_SIDE_MENU_LABEL_OTHERS=StringVar(value=i18n.t("config_window.side_menu_labels.others")),
            VAR_SIDE_MENU_LABEL_ADVANCED_SETTINGS=StringVar(value=i18n.t("config_window.side_menu_labels.advanced_settings")),

            VAR_CURRENT_ACTIVE_CONFIG_TITLE=StringVar(value=""),

            # Appearance Tab
            VAR_LABEL_TRANSPARENCY=StringVar(value=i18n.t("config_window.transparency.label")),
            VAR_DESC_TRANSPARENCY=StringVar(value=i18n.t("config_window.transparency.desc")),
            SLIDER_RANGE_TRANSPARENCY=(50, 100),
            CALLBACK_SET_TRANSPARENCY=None,
            VAR_TRANSPARENCY=IntVar(value=config.TRANSPARENCY),
            CALLBACK_BUTTON_PRESS_TRANSPARENCY=self._closeTheCoverOfMainWindow,
            CALLBACK_BUTTON_RELEASE_TRANSPARENCY=self._openTheCoverOfMainWindow,

            VAR_LABEL_APPEARANCE_THEME=StringVar(value=i18n.t("config_window.appearance_theme.label")),
            VAR_DESC_APPEARANCE_THEME=StringVar(value=i18n.t("config_window.appearance_theme.desc")),
            LIST_APPEARANCE_THEME=["Dark"],
            # LIST_APPEARANCE_THEME=["Light", "Dark", "System"],
            CALLBACK_SET_APPEARANCE_THEME=None,
            VAR_APPEARANCE_THEME=StringVar(value="Dark"),
            # VAR_APPEARANCE_THEME=StringVar(value=config.APPEARANCE_THEME),

            VAR_LABEL_UI_SCALING=StringVar(value=i18n.t("config_window.ui_size.label")),
            VAR_DESC_UI_SCALING=None,
            LIST_UI_SCALING=generatePercentageStringsList(start=40,end=200, step=10),
            CALLBACK_SET_UI_SCALING=None,
            VAR_UI_SCALING=StringVar(value=config.UI_SCALING),

            VAR_LABEL_TEXTBOX_UI_SCALING=StringVar(value=i18n.t("config_window.textbox_ui_size.label")),
            VAR_DESC_TEXTBOX_UI_SCALING=StringVar(value=i18n.t("config_window.textbox_ui_size.desc")),
            SLIDER_RANGE_TEXTBOX_UI_SCALING=(50, 200),
            CALLBACK_SET_TEXTBOX_UI_SCALING=None,
            VAR_TEXTBOX_UI_SCALING=IntVar(value=config.TEXTBOX_UI_SCALING),
            CALLBACK_BUTTON_PRESS_TEXTBOX_UI_SCALING=self._closeTheCoverOfMainWindow,
            CALLBACK_BUTTON_RELEASE_TEXTBOX_UI_SCALING=self._openTheCoverOfMainWindow,

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


            # Translation Tab
            VAR_LABEL_DEEPL_AUTH_KEY=StringVar(value=i18n.t("config_window.deepl_auth_key.label")),
            VAR_DESC_DEEPL_AUTH_KEY=None,
            CALLBACK_SET_DEEPL_AUTH_KEY=None,
            VAR_DEEPL_AUTH_KEY=StringVar(value=config.AUTH_KEYS["DeepL_API"]),


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


            VAR_LABEL_MIC_DYNAMIC_ENERGY_THRESHOLD=StringVar(value=""),
            VAR_DESC_MIC_DYNAMIC_ENERGY_THRESHOLD=StringVar(value=""),
            CALLBACK_SET_MIC_DYNAMIC_ENERGY_THRESHOLD=None,
            VAR_MIC_DYNAMIC_ENERGY_THRESHOLD=BooleanVar(value=config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD),

            SLIDER_RANGE_MIC_ENERGY_THRESHOLD=(0, config.MAX_MIC_ENERGY_THRESHOLD),
            CALLBACK_CHECK_MIC_THRESHOLD=None,
            VAR_MIC_ENERGY_THRESHOLD__SLIDER=IntVar(value=config.INPUT_MIC_ENERGY_THRESHOLD),
            VAR_MIC_ENERGY_THRESHOLD__ENTRY=StringVar(value=config.INPUT_MIC_ENERGY_THRESHOLD),
            CALLBACK_FOCUS_OUT_MIC_ENERGY_THRESHOLD=self.callbackBindFocusOut_MicEnergyThreshold,


            VAR_LABEL_MIC_RECORD_TIMEOUT=StringVar(value=i18n.t("config_window.mic_record_timeout.label")),
            VAR_DESC_MIC_RECORD_TIMEOUT=StringVar(value=i18n.t("config_window.mic_record_timeout.desc")),
            CALLBACK_SET_MIC_RECORD_TIMEOUT=None,
            VAR_MIC_RECORD_TIMEOUT=StringVar(value=config.INPUT_MIC_RECORD_TIMEOUT),
            CALLBACK_FOCUS_OUT_MIC_RECORD_TIMEOUT=self.callbackBindFocusOut_MicRecordTimeout,

            VAR_LABEL_MIC_PHRASE_TIMEOUT=StringVar(value=i18n.t("config_window.mic_phrase_timeout.label")),
            VAR_DESC_MIC_PHRASE_TIMEOUT=StringVar(value=i18n.t("config_window.mic_phrase_timeout.desc")),
            CALLBACK_SET_MIC_PHRASE_TIMEOUT=None,
            VAR_MIC_PHRASE_TIMEOUT=StringVar(value=config.INPUT_MIC_PHRASE_TIMEOUT),
            CALLBACK_FOCUS_OUT_MIC_PHRASE_TIMEOUT=self.callbackBindFocusOut_MicPhraseTimeout,

            VAR_LABEL_MIC_MAX_PHRASES=StringVar(value=i18n.t("config_window.mic_max_phrase.label")),
            VAR_DESC_MIC_MAX_PHRASES=StringVar(value=i18n.t("config_window.mic_max_phrase.desc")),
            CALLBACK_SET_MIC_MAX_PHRASES=None,
            VAR_MIC_MAX_PHRASES=StringVar(value=config.INPUT_MIC_MAX_PHRASES),
            CALLBACK_FOCUS_OUT_MIC_MAX_PHRASES=self.callbackBindFocusOut_MicMaxPhrases,

            VAR_LABEL_MIC_WORD_FILTER=StringVar(value=i18n.t("config_window.mic_word_filter.label")),
            VAR_DESC_MIC_WORD_FILTER=StringVar(value=i18n.t("config_window.mic_word_filter.desc")),
            CALLBACK_SET_MIC_WORD_FILTER=None,
            VAR_MIC_WORD_FILTER=StringVar(value=",".join(config.INPUT_MIC_WORD_FILTER) if len(config.INPUT_MIC_WORD_FILTER) > 0 else ""),


            # Transcription Tab (Speaker)
            VAR_LABEL_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=StringVar(value=""),
            VAR_DESC_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=StringVar(value=""),
            CALLBACK_SET_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=None,
            VAR_SPEAKER_DYNAMIC_ENERGY_THRESHOLD=BooleanVar(value=config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD),

            SLIDER_RANGE_SPEAKER_ENERGY_THRESHOLD=(0, config.MAX_SPEAKER_ENERGY_THRESHOLD),
            CALLBACK_CHECK_SPEAKER_THRESHOLD=None,
            VAR_SPEAKER_ENERGY_THRESHOLD__SLIDER=IntVar(value=config.INPUT_SPEAKER_ENERGY_THRESHOLD),
            VAR_SPEAKER_ENERGY_THRESHOLD__ENTRY=StringVar(value=config.INPUT_SPEAKER_ENERGY_THRESHOLD),
            CALLBACK_FOCUS_OUT_SPEAKER_ENERGY_THRESHOLD=self.callbackBindFocusOut_SpeakerEnergyThreshold,


            VAR_LABEL_SPEAKER_RECORD_TIMEOUT=StringVar(value=i18n.t("config_window.speaker_record_timeout.label")),
            VAR_DESC_SPEAKER_RECORD_TIMEOUT=StringVar(value=i18n.t("config_window.speaker_record_timeout.desc")),
            CALLBACK_SET_SPEAKER_RECORD_TIMEOUT=None,
            VAR_SPEAKER_RECORD_TIMEOUT=StringVar(value=config.INPUT_SPEAKER_RECORD_TIMEOUT),
            CALLBACK_FOCUS_OUT_SPEAKER_RECORD_TIMEOUT=self.callbackBindFocusOut_SpeakerRecordTimeout,

            VAR_LABEL_SPEAKER_PHRASE_TIMEOUT=StringVar(value=i18n.t("config_window.speaker_phrase_timeout.label")),
            VAR_DESC_SPEAKER_PHRASE_TIMEOUT=StringVar(value=i18n.t("config_window.speaker_phrase_timeout.desc")),
            CALLBACK_SET_SPEAKER_PHRASE_TIMEOUT=None,
            VAR_SPEAKER_PHRASE_TIMEOUT=StringVar(value=config.INPUT_SPEAKER_PHRASE_TIMEOUT),
            CALLBACK_FOCUS_OUT_SPEAKER_PHRASE_TIMEOUT=self.callbackBindFocusOut_SpeakerPhraseTimeout,

            VAR_LABEL_SPEAKER_MAX_PHRASES=StringVar(value=i18n.t("config_window.speaker_max_phrase.label")),
            VAR_DESC_SPEAKER_MAX_PHRASES=StringVar(value=i18n.t("config_window.speaker_max_phrase.desc")),
            CALLBACK_SET_SPEAKER_MAX_PHRASES=None,
            VAR_SPEAKER_MAX_PHRASES=StringVar(value=config.INPUT_SPEAKER_MAX_PHRASES),
            CALLBACK_FOCUS_OUT_SPEAKER_MAX_PHRASES=self.callbackBindFocusOut_SpeakerMaxPhrases,


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

            # [deprecated]
            # VAR_LABEL_STARTUP_OSC_ENABLED_CHECK=StringVar(value=i18n.t("config_window.startup_osc_enabled_check.label")),
            # VAR_DESC_STARTUP_OSC_ENABLED_CHECK=StringVar(value=i18n.t("config_window.startup_osc_enabled_check.desc")),
            # CALLBACK_SET_STARTUP_OSC_ENABLED_CHECK=None,
            # VAR_STARTUP_OSC_ENABLED_CHECK=BooleanVar(value=config.STARTUP_OSC_ENABLED_CHECK),




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
            common_registers=None,
            window_action_registers=None,
            main_window_registers=None,
            config_window_registers=None
        ):


        if common_registers is not None:
            self.view_variable.CALLBACK_UPDATE_SOFTWARE=common_registers.get("callback_update_software", None)
            self.view_variable.CALLBACK_RESTART_SOFTWARE=common_registers.get("callback_restart_software", None)


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
            entry_message_box.bind("<Return>", main_window_registers.get("message_box_bind_Return"))
            entry_message_box.bind("<Any-KeyPress>", main_window_registers.get("message_box_bind_Any_KeyPress"))


            entry_message_box.bind("<FocusIn>", main_window_registers.get("message_box_bind_FocusIn"))
            entry_message_box.bind("<FocusOut>", main_window_registers.get("message_box_bind_FocusOut"))


        self.updateGuiVariableByPresetTabNo(config.SELECTED_TAB_NO)
        vrct_gui._setDefaultActiveLanguagePresetTab(tab_no=config.SELECTED_TAB_NO)

        self.view_variable.CALLBACK_OPEN_SELECTABLE_YOUR_LANGUAGE_WINDOW = self.openSelectableLanguagesWindow_YourLanguage
        self.view_variable.CALLBACK_OPEN_SELECTABLE_TARGET_LANGUAGE_WINDOW = self.openSelectableLanguagesWindow_TargetLanguage


        # Config Window
        self.view_variable.CALLBACK_SELECTED_SETTING_BOX_TAB=self._updateActiveSettingBoxTabNo


        if config_window_registers is not None:
            # Compact Mode Switch
            self.view_variable.CALLBACK_ENABLE_CONFIG_WINDOW_COMPACT_MODE = config_window_registers.get("callback_disable_config_window_compact_mode", None)
            self.view_variable.CALLBACK_DISABLE_CONFIG_WINDOW_COMPACT_MODE = config_window_registers.get("callback_enable_config_window_compact_mode", None)


            # Appearance Tab
            self.view_variable.CALLBACK_SET_TRANSPARENCY = config_window_registers.get("callback_set_transparency", None)

            self.view_variable.CALLBACK_SET_APPEARANCE = config_window_registers.get("callback_set_appearance", None)
            self.view_variable.CALLBACK_SET_UI_SCALING = config_window_registers.get("callback_set_ui_scaling", None)
            self.view_variable.CALLBACK_SET_TEXTBOX_UI_SCALING = config_window_registers.get("callback_set_textbox_ui_scaling", None)
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
            # self.view_variable.CALLBACK_SET_STARTUP_OSC_ENABLED_CHECK = config_window_registers.get("callback_set_startup_osc_enabled_check", None) #[deprecated]

            # Advanced Settings Tab
            self.view_variable.CALLBACK_SET_OSC_IP_ADDRESS = config_window_registers.get("callback_set_osc_ip_address", None)
            self.view_variable.CALLBACK_SET_OSC_PORT = config_window_registers.get("callback_set_osc_port", None)

        # The initial processing after registration.
        if config.IS_CONFIG_WINDOW_COMPACT_MODE is True:
            self.enableConfigWindowCompactMode()
            vrct_gui.config_window.setting_box_compact_mode_switch_box.select()

        vrct_gui._changeConfigWindowWidgetsStatus(
            status="disabled",
            target_names=[
                "sb__optionmenu_appearance_theme",
            ]
        )


        if config.CHOICE_MIC_HOST == "NoHost":
            self.view_variable.VAR_MIC_HOST.set("No Mic Host Detected")

        if config.CHOICE_MIC_DEVICE == "NoDevice":
            self.view_variable.VAR_MIC_DEVICE.set("No Mic Device Detected")

        if config.CHOICE_MIC_HOST == "NoHost" or config.CHOICE_MIC_DEVICE == "NoDevice":
            vrct_gui._changeConfigWindowWidgetsStatus(
                status="disabled",
                target_names=[
                    "sb__optionmenu_mic_host",
                    "sb__optionmenu_mic_device",
                ]
            )
            self.replaceMicThresholdCheckButton_Disabled()


        if config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD is True:
            self.closeMicEnergyThresholdWidget()
        else:
            self.openMicEnergyThresholdWidget()

        if config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD is True:
            self.closeSpeakerEnergyThresholdWidget()
        else:
            self.openSpeakerEnergyThresholdWidget()


        # Insert sample conversation for testing.
        # self._insertSampleConversationToTextbox()



# GUI process
    def createGUI(self):
        vrct_gui._createGUI(settings=self.settings, view_variable=self.view_variable)

    @staticmethod
    def showGUI():
        vrct_gui._showGUI()

    @staticmethod
    def startMainLoop():
        vrct_gui._showGUI()
        vrct_gui._startMainLoop()



# Common
    @staticmethod
    def getAvailableFonts():
        available_fonts = list(tk_font.families())
        available_fonts.sort()
        filtered_available_fonts = list(filter(lambda x: x.startswith("@") is False, available_fonts))
        return filtered_available_fonts

    @staticmethod
    def openWebPage(url:str):
        webbrowser.open_new_tab(url)


# Open Webpage Functions
    def openWebPage_Booth(self):
        self.openWebPage(config.BOOTH_URL)
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.opened_web_page_booth"))

    def openWebPage_VrctDocuments(self):
        self.openWebPage(config.DOCUMENTS_URL)
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.opened_web_page_vrct_documents"))

# Widget Control
    # Common
    @staticmethod
    def _clearEntryBox(entry_widget):
        entry_widget.delete(0, CTK_END)

    def clearErrorMessage(self):
        vrct_gui._clearErrorMessage()


    @staticmethod
    def showUpdateAvailableButton():
        vrct_gui.update_available_container.grid()

    @staticmethod
    def setMainWindowAllWidgetsStatusToNormal():
        vrct_gui._changeMainWindowWidgetsStatus("normal", "All")

    @staticmethod
    def setMainWindowAllWidgetsStatusToDisabled():
        vrct_gui._changeMainWindowWidgetsStatus("disabled", "All")


    def enableMainWindowSidebarCompactMode(self):
        self.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
        vrct_gui._enableMainWindowSidebarCompactMode()

    def disableMainWindowSidebarCompactMode(self):
        self.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
        vrct_gui._disableMainWindowSidebarCompactMode()


    # Config Window
    def enableConfigWindowCompactMode(self):
        for additional_widget in vrct_gui.config_window.additional_widgets:
            additional_widget.grid_remove()

    def disableConfigWindowCompactMode(self):
        for additional_widget in vrct_gui.config_window.additional_widgets:
            additional_widget.grid()


    def showRestartButtonIfRequired(self, locale:Union[None,str]=None):
        is_restart_required = not (
            self.restart_required_configs_pre_data.appearance_theme == config.APPEARANCE_THEME and
            self.restart_required_configs_pre_data.ui_scaling == config.UI_SCALING and
            self.restart_required_configs_pre_data.font_family == config.FONT_FAMILY and
            self.restart_required_configs_pre_data.ui_language == config.UI_LANGUAGE
        )

        if locale is None:
            locale = config.UI_LANGUAGE

        if is_restart_required is True:
            self._showRestartButton(locale)
        else:
            self._hideRestartButton()


    def _showRestartButton(self, locale:Union[None,str]=None):
        self.view_variable.VAR_CONFIG_WINDOW_RESTART_BUTTON_LABEL.set(i18n.t("config_window.restart_message", locale=locale))
        vrct_gui.config_window.restart_button_container.grid()
    def _hideRestartButton(self):
        vrct_gui.config_window.restart_button_container.grid_remove()



    @staticmethod
    def setWidgetsStatus_ConfigWindowCompactModeSwitch_Disabled():
        vrct_gui.config_window.setting_box_compact_mode_switch_box.configure(state="disabled")

    @staticmethod
    def setWidgetsStatus_ConfigWindowCompactModeSwitch_Normal():
        vrct_gui.config_window.setting_box_compact_mode_switch_box.configure(state="normal")



    def openMicEnergyThresholdWidget(self):
        self.view_variable.VAR_LABEL_MIC_DYNAMIC_ENERGY_THRESHOLD.set(i18n.t("config_window.mic_dynamic_energy_threshold.label_for_manual"))
        self.view_variable.VAR_DESC_MIC_DYNAMIC_ENERGY_THRESHOLD.set(i18n.t("config_window.mic_dynamic_energy_threshold.desc_for_manual"))
        vrct_gui.config_window.sb__mic_dynamic_energy_threshold.grid(pady=0)
        vrct_gui.config_window.sb__mic_energy_threshold.grid()

    def closeMicEnergyThresholdWidget(self):
        self.view_variable.VAR_LABEL_MIC_DYNAMIC_ENERGY_THRESHOLD.set(i18n.t("config_window.mic_dynamic_energy_threshold.label_for_automatic"))
        self.view_variable.VAR_DESC_MIC_DYNAMIC_ENERGY_THRESHOLD.set(i18n.t("config_window.mic_dynamic_energy_threshold.desc_for_automatic"))
        vrct_gui.config_window.sb__mic_dynamic_energy_threshold.grid(pady=(0,1))
        vrct_gui.config_window.sb__mic_energy_threshold.grid_remove()

    def openSpeakerEnergyThresholdWidget(self):
        self.view_variable.VAR_LABEL_SPEAKER_DYNAMIC_ENERGY_THRESHOLD.set(i18n.t("config_window.speaker_dynamic_energy_threshold.label_for_manual"))
        self.view_variable.VAR_DESC_SPEAKER_DYNAMIC_ENERGY_THRESHOLD.set(i18n.t("config_window.speaker_dynamic_energy_threshold.desc_for_manual"))
        vrct_gui.config_window.sb__speaker_dynamic_energy_threshold.grid(pady=0)
        vrct_gui.config_window.sb__speaker_energy_threshold.grid()

    def closeSpeakerEnergyThresholdWidget(self):
        self.view_variable.VAR_LABEL_SPEAKER_DYNAMIC_ENERGY_THRESHOLD.set(i18n.t("config_window.speaker_dynamic_energy_threshold.label_for_automatic"))
        self.view_variable.VAR_DESC_SPEAKER_DYNAMIC_ENERGY_THRESHOLD.set(i18n.t("config_window.speaker_dynamic_energy_threshold.desc_for_automatic"))
        vrct_gui.config_window.sb__speaker_dynamic_energy_threshold.grid(pady=(0,1))
        vrct_gui.config_window.sb__speaker_energy_threshold.grid_remove()



    def initMicThresholdCheckButton(self):
        if config.CHOICE_MIC_HOST == "NoHost" or config.CHOICE_MIC_DEVICE == "NoDevice":
            self.replaceMicThresholdCheckButton_Disabled()
        else:
            self.replaceMicThresholdCheckButton_Passive()

    @staticmethod
    def replaceMicThresholdCheckButton_Active():
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__disabled_button_mic_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_mic_energy_threshold.grid()

    @staticmethod
    def replaceMicThresholdCheckButton_Disabled():
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_mic_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__disabled_button_mic_energy_threshold.grid()

    @staticmethod
    def replaceMicThresholdCheckButton_Passive():
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_mic_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__disabled_button_mic_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold.grid()



    def initSpeakerThresholdCheckButton(self):
        self.replaceSpeakerThresholdCheckButton_Passive()

    @staticmethod
    def replaceSpeakerThresholdCheckButton_Active():
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_speaker_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__disabled_button_speaker_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_speaker_energy_threshold.grid()

    @staticmethod
    def replaceSpeakerThresholdCheckButton_Disabled():
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_speaker_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_speaker_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__disabled_button_speaker_energy_threshold.grid()

    @staticmethod
    def replaceSpeakerThresholdCheckButton_Passive():
        vrct_gui.config_window.sb__progressbar_x_slider__active_button_speaker_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__disabled_button_speaker_energy_threshold.grid_remove()
        vrct_gui.config_window.sb__progressbar_x_slider__passive_button_speaker_energy_threshold.grid()




    def updateList_MicHost(self, new_mic_host_list:list):
        self.view_variable.LIST_MIC_HOST = new_mic_host_list
        vrct_gui.dropdown_menu_window.updateDropdownMenuValues(
            dropdown_menu_widget_id="sb__optionmenu_mic_host",
            dropdown_menu_values=new_mic_host_list,
        )

    def updateSelected_MicHost(self, selected_mic_host_name:str):
        self.view_variable.VAR_MIC_HOST.set(selected_mic_host_name)

    def updateList_MicDevice(self, new_mic_device_list:list):
        self.view_variable.LIST_MIC_DEVICE = new_mic_device_list
        vrct_gui.dropdown_menu_window.updateDropdownMenuValues(
            dropdown_menu_widget_id="sb__optionmenu_mic_device",
            dropdown_menu_values=new_mic_device_list,
        )

    def updateSelected_MicDevice(self, default_selected_mic_device_name:str):
        self.view_variable.VAR_MIC_DEVICE.set(default_selected_mic_device_name)


    def updateSetProgressBar_MicEnergy(self, new_mic_energy):
        self.updateProgressBar(
            target_progressbar_widget=vrct_gui.config_window.sb__progressbar_x_slider__progressbar_mic_energy_threshold,
            new_energy=new_mic_energy,
            max_energy=config.MAX_MIC_ENERGY_THRESHOLD,
            energy_threshold=config.INPUT_MIC_ENERGY_THRESHOLD,
        )


    @staticmethod
    def initProgressBar_MicEnergy():
        vrct_gui.config_window.sb__progressbar_x_slider__progressbar_mic_energy_threshold.set(0)


    def updateSetProgressBar_SpeakerEnergy(self, new_speaker_energy):
        self.updateProgressBar(
            target_progressbar_widget=vrct_gui.config_window.sb__progressbar_x_slider__progressbar_speaker_energy_threshold,
            new_energy=new_speaker_energy,
            max_energy=config.MAX_SPEAKER_ENERGY_THRESHOLD,
            energy_threshold=config.INPUT_SPEAKER_ENERGY_THRESHOLD,
        )

    @staticmethod
    def initProgressBar_SpeakerEnergy():
        vrct_gui.config_window.sb__progressbar_x_slider__progressbar_speaker_energy_threshold.set(0)


    def updateProgressBar(
            self,
            target_progressbar_widget,
            new_energy,
            max_energy,
            energy_threshold,
        ):
        target_progressbar_widget.set(new_energy/max_energy)
        if new_energy >= energy_threshold:
            target_progressbar_widget.configure(progress_color=self.settings.config_window.ctm.SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_PROGRESS_EXCEED_THRESHOLD_BG_COLOR)
        else:
            target_progressbar_widget.configure(progress_color=self.settings.config_window.ctm.SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_PROGRESS_BG_COLOR)



# Widget Control (Whole)
    def foregroundOnIfForegroundEnabled(self):
        if config.ENABLE_FOREGROUND:
            self.foregroundOn()

    def foregroundOffIfForegroundEnabled(self):
        if config.ENABLE_FOREGROUND:
            self.foregroundOff()


    @staticmethod
    def foregroundOn():
        vrct_gui.attributes("-topmost", True)

    @staticmethod
    def foregroundOff():
        vrct_gui.attributes("-topmost", False)


    @staticmethod
    def setMainWindowTransparency(transparency:float):
        vrct_gui.wm_attributes("-alpha", transparency)

    @staticmethod
    def setMainWindowTextboxUiSize(custom_font_size_scale:float):
        vrct_gui.print_to_textbox.setTagsSettings(custom_font_size_scale=custom_font_size_scale)

# Function
    def _adjustUiSizeAndRestart(self):
        current_percentage = int(config.UI_SCALING.replace("%",""))
        target_percentage = current_percentage - 20
        if target_percentage >= 40 and str(target_percentage) + "%" in self.view_variable.LIST_UI_SCALING:
            index = self.view_variable.LIST_UI_SCALING.index(str(target_percentage) + "%")
            callFunctionIfCallable(self.view_variable.CALLBACK_SET_UI_SCALING, self.view_variable.LIST_UI_SCALING[index])
            callFunctionIfCallable(self.view_variable.CALLBACK_RESTART_SOFTWARE)
        else:
            self._hideConfirmationModal()
        # ※Below 40% of the UI size is not supported, and we cannot handle it at this time.



    def translationEngineLimitErrorProcess(self):
        # turn off translation switch.
        vrct_gui.translation_switch_box.deselect()
        vrct_gui.translation_frame.markToggleManually(False)

        # disable translation feature.
        vrct_gui._changeMainWindowWidgetsStatus("disabled", ["translation_switch"], to_hold_state=True)

        # print system message that mention to stopped translation feature.
        view.printToTextbox_TranslationEngineLimitError()
        view.showTheLimitOfTranslationEngineConfirmationModal()




# Show Modal
    def _showDisplayOverUiSizeConfirmationModal(self):
        self.foregroundOffIfForegroundEnabled()

        self.view_variable.VAR_LABEL_MAIN_WINDOW_COVER_MESSAGE.set("")
        vrct_gui.main_window_cover.show()

        self.view_variable.CALLBACK_HIDE_CONFIRMATION_MODAL=self._hideConfirmationModal
        self.view_variable.CALLBACK_ACCEPTED_CONFIRMATION_MODAL=self._adjustUiSizeAndRestart
        self.view_variable.CALLBACK_DENIED_CONFIRMATION_MODAL=self._hideConfirmationModal

        self.view_variable.VAR_MESSAGE_CONFIRMATION_MODAL.set(i18n.t("main_window.confirmation_message.detected_over_ui_size", current_ui_size=config.UI_SCALING))
        self.view_variable.VAR_LABEL_CONFIRMATION_MODAL_DENY_BUTTON.set(i18n.t("main_window.confirmation_message.deny_adjust_ui_size"))
        self.view_variable.VAR_LABEL_CONFIRMATION_MODAL_ACCEPT_BUTTON.set(i18n.t("main_window.confirmation_message.accept_adjust_ui_size"))

        vrct_gui.confirmation_modal.show(hide_title_bar=False, close_when_focusout=False)



    def _showUpdateSoftwareConfirmationModal(self):
        self.foregroundOffIfForegroundEnabled()

        self.view_variable.VAR_LABEL_MAIN_WINDOW_COVER_MESSAGE.set("")
        vrct_gui.main_window_cover.show()

        self.view_variable.CALLBACK_HIDE_CONFIRMATION_MODAL=self._hideConfirmationModal
        self.view_variable.CALLBACK_ACCEPTED_CONFIRMATION_MODAL=self._startUpdateSoftware
        self.view_variable.CALLBACK_DENIED_CONFIRMATION_MODAL=self._hideConfirmationModal

        self.view_variable.VAR_MESSAGE_CONFIRMATION_MODAL.set(i18n.t("main_window.confirmation_message.update_software"))
        self.view_variable.VAR_LABEL_CONFIRMATION_MODAL_DENY_BUTTON.set(i18n.t("main_window.confirmation_message.deny_update_software"))
        self.view_variable.VAR_LABEL_CONFIRMATION_MODAL_ACCEPT_BUTTON.set(i18n.t("main_window.confirmation_message.accept_update_software"))
        vrct_gui.confirmation_modal.show()





    def showTheLimitOfTranslationEngineConfirmationModal(self):
        self.foregroundOffIfForegroundEnabled()

        self.view_variable.VAR_LABEL_MAIN_WINDOW_COVER_MESSAGE.set("")
        vrct_gui.main_window_cover.show()

        self.view_variable.CALLBACK_HIDE_CONFIRMATION_MODAL=self._hideInformationModal
        self.view_variable.CALLBACK_ACCEPTED_CONFIRMATION_MODAL=self._hideInformationModal

        self.view_variable.VAR_MESSAGE_CONFIRMATION_MODAL.set(i18n.t("main_window.confirmation_message.translation_engine_limit_error"))
        self.view_variable.VAR_LABEL_CONFIRMATION_MODAL_ACCEPT_BUTTON.set(i18n.t("main_window.confirmation_message.accept_translation_engine_limit_error"))
        vrct_gui.information_modal.show(hide_title_bar=False, close_when_focusout=False)




# Hide Modal
    def _hideInformationModal(self):
        vrct_gui.information_modal.hide()
        vrct_gui.main_window_cover.hide()
        self.foregroundOnIfForegroundEnabled()


    def _hideConfirmationModal(self):
        vrct_gui.confirmation_modal.hide()
        vrct_gui.main_window_cover.hide()
        self.foregroundOnIfForegroundEnabled()


# Process
    def _startUpdateSoftware(self):
        self.view_variable.VAR_MESSAGE_CONFIRMATION_MODAL.set(i18n.t("main_window.confirmation_message.updating"))
        vrct_gui.confirmation_modal.hide_buttons()
        vrct_gui.update()
        vrct_gui.confirmation_modal.update()
        callFunctionIfCallable(self.view_variable.CALLBACK_UPDATE_SOFTWARE)



# Window Control
    def _openConfigWindow(self):
        self.view_variable.VAR_LABEL_MAIN_WINDOW_COVER_MESSAGE.set(i18n.t("main_window.cover_message"))
        callFunctionIfCallable(self.view_variable.CALLBACK_OPEN_CONFIG_WINDOW)
        vrct_gui._openConfigWindow()

    def _closeConfigWindow(self):
        callFunctionIfCallable(self.view_variable.CALLBACK_CLOSE_CONFIG_WINDOW)
        vrct_gui._closeConfigWindow()

# Window Control (Main Window Cover)
    def _openTheCoverOfMainWindow(self):
        vrct_gui.main_window_cover.show()
        vrct_gui.config_window.lift()

    @staticmethod
    def _closeTheCoverOfMainWindow():
        vrct_gui.main_window_cover.withdraw()

# Window Control (Selectable Languages Window)
    def openSelectableLanguagesWindow_YourLanguage(self, _e):
        self.view_variable.VAR_TITLE_LABEL_SELECTABLE_LANGUAGE.set(i18n.t("selectable_language_window.title_your_language"))
        vrct_gui._openSelectableLanguagesWindow("your_language")

    def openSelectableLanguagesWindow_TargetLanguage(self, _e):
        self.view_variable.VAR_TITLE_LABEL_SELECTABLE_LANGUAGE.set(i18n.t("selectable_language_window.title_target_language"))
        vrct_gui._openSelectableLanguagesWindow("target_language")


# Update GuiVariable (view_variable)
    def updateGuiVariableByPresetTabNo(self, tab_no:str):
        self.view_variable.VAR_YOUR_LANGUAGE.set(config.SELECTED_TAB_YOUR_LANGUAGES[tab_no])
        self.view_variable.VAR_TARGET_LANGUAGE.set(config.SELECTED_TAB_TARGET_LANGUAGES[tab_no])


    def updateList_selectableLanguages(self, new_selectable_language_list:list):
        self.view_variable.LIST_SELECTABLE_LANGUAGES = new_selectable_language_list

    # (Config Window Setting Box Tab)
    def _updateActiveSettingBoxTabNo(self, active_setting_box_tab_attr_name:str):
        self.view_variable.ACTIVE_SETTING_BOX_TAB_ATTR_NAME = active_setting_box_tab_attr_name


# Set GuiVariable (view_variable)
    def setGuiVariable_MicEnergyThreshold(self, value):
        self.view_variable.VAR_MIC_ENERGY_THRESHOLD__SLIDER.set(int(value))
        self.view_variable.VAR_MIC_ENERGY_THRESHOLD__ENTRY.set(str(value))


    def setGuiVariable_SpeakerEnergyThreshold(self, value):
        self.view_variable.VAR_SPEAKER_ENERGY_THRESHOLD__SLIDER.set(int(value))
        self.view_variable.VAR_SPEAKER_ENERGY_THRESHOLD__ENTRY.set(str(value))


    def setGuiVariable_MicRecordTimeout(self, value):
        self.view_variable.VAR_MIC_RECORD_TIMEOUT.set(str(value))


    def setGuiVariable_MicPhraseTimeout(self, value):
        self.view_variable.VAR_MIC_PHRASE_TIMEOUT.set(str(value))


    def setGuiVariable_MicMaxPhrases(self, value):
        self.view_variable.VAR_MIC_MAX_PHRASES.set(str(value))



    def setGuiVariable_SpeakerRecordTimeout(self, value):
        self.view_variable.VAR_SPEAKER_RECORD_TIMEOUT.set(str(value))


    def setGuiVariable_SpeakerPhraseTimeout(self, value):
        self.view_variable.VAR_SPEAKER_PHRASE_TIMEOUT.set(str(value))


    def setGuiVariable_SpeakerMaxPhrases(self, value):
        self.view_variable.VAR_SPEAKER_MAX_PHRASES.set(str(value))






    def setLatestConfigVariable(self, target_name:str):
        match (target_name):
            case "MicEnergyThreshold":
                self.setGuiVariable_MicEnergyThreshold(config.INPUT_MIC_ENERGY_THRESHOLD)
            case "SpeakerEnergyThreshold":
                self.setGuiVariable_SpeakerEnergyThreshold(config.INPUT_SPEAKER_ENERGY_THRESHOLD)
            case "MicRecordTimeout":
                self.setGuiVariable_MicRecordTimeout(config.INPUT_MIC_RECORD_TIMEOUT)
            case "MicPhraseTimeout":
                self.setGuiVariable_MicPhraseTimeout(config.INPUT_MIC_PHRASE_TIMEOUT)
            case "MicMaxPhrases":
                self.setGuiVariable_MicMaxPhrases(config.INPUT_MIC_MAX_PHRASES)
            case "SpeakerRecordTimeout":
                self.setGuiVariable_SpeakerRecordTimeout(config.INPUT_SPEAKER_RECORD_TIMEOUT)
            case "SpeakerPhraseTimeout":
                self.setGuiVariable_SpeakerPhraseTimeout(config.INPUT_SPEAKER_PHRASE_TIMEOUT)
            case "SpeakerMaxPhrases":
                self.setGuiVariable_SpeakerMaxPhrases(config.INPUT_SPEAKER_MAX_PHRASES)

            case _:
                raise ValueError(f"No matching case for target_name: {target_name}")


# Print To Textbox.
    def printToTextbox_enableTranslation(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.enabled_translation"))
    def printToTextbox_disableTranslation(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.disabled_translation"))

    def printToTextbox_enableTranscriptionSend(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.enabled_voice2chatbox"))
    def printToTextbox_disableTranscriptionSend(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.disabled_voice2chatbox"))

    def printToTextbox_enableTranscriptionReceive(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.enabled_speaker2log"))
    def printToTextbox_disableTranscriptionReceive(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.disabled_speaker2log"))

    def printToTextbox_enableForeground(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.enabled_foreground"))
    def printToTextbox_disableForeground(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.disabled_foreground"))

    def printToTextbox_AuthenticationSuccess(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.auth_key_success"))
    def printToTextbox_AuthenticationError(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.auth_key_error"))


    def printToTextbox_TranscriptionSendNoDeviceError(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.no_mic_device_detected_error"))

    def printToTextbox_TranscriptionReceiveNoDeviceError(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.no_speaker_device_detected_error"))


    def printToTextbox_TranslationEngineLimitError(self):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.translation_engine_limit_error"))


    # def printToTextbox_OSCError(self): [Deprecated]
    #     self._printToTextbox_Info("OSC is not enabled, please enable OSC and rejoin. or turn off the \"Send Message To VRChat\" setting")

    def printToTextbox_DetectedByWordFilter(self, detected_message):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.detected_by_word_filter", detected_message=detected_message))



    def printToTextbox_selectedYourLanguages(self, selected_your_language):
        your_language = selected_your_language.replace("\n", " ")
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.selected_your_language", your_language=your_language))

    def printToTextbox_selectedTargetLanguages(self, selected_target_language):
        target_language = selected_target_language.replace("\n", " ")
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.selected_target_language", target_language=target_language))

    def printToTextbox_changedLanguagePresetTab(self, tab_no:str):
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.switched_language_preset_tab", tab_no=tab_no))
        self.printToTextbox_latestSelectedLanguages()

    def printToTextbox_latestSelectedLanguages(self):
        your_language = self.view_variable.VAR_YOUR_LANGUAGE.get().replace("\n", " ")
        target_language = self.view_variable.VAR_TARGET_LANGUAGE.get().replace("\n", " ")
        self._printToTextbox_Info(i18n.t("main_window.textbox_system_message.latest_language_setting", your_language=your_language, target_language=target_language))


    @staticmethod
    def _printToTextbox_Info(info_message, **kwargs):
        vrct_gui._printToTextbox(
            target_type="SYSTEM",
            original_message=info_message,
            **kwargs,
        )



    def printToTextbox_SentMessage(self, original_message, translated_message):
        self._printToTextbox_Sent(original_message, translated_message)

    @staticmethod
    def _printToTextbox_Sent(original_message, translated_message):
        vrct_gui._printToTextbox(
            target_type="SENT",
            original_message=original_message,
            translated_message=translated_message,
        )


    def printToTextbox_ReceivedMessage(self, original_message, translated_message):
        self._printToTextbox_Received(original_message, translated_message)

    @staticmethod
    def _printToTextbox_Received(original_message, translated_message):
        vrct_gui._printToTextbox(
            target_type="RECEIVED",
            original_message=original_message,
            translated_message=translated_message,
        )


# Message Box
    @staticmethod
    def getTextFromMessageBox():
        return vrct_gui.entry_message_box.get()

    def clearMessageBox(self):
        self._clearEntryBox(vrct_gui.entry_message_box)




# Callback Bind FocusOut
    def callbackBindFocusOut_MicEnergyThreshold(self, _e=None):
        self.setLatestConfigVariable("MicEnergyThreshold")
        self.clearErrorMessage()

    def callbackBindFocusOut_SpeakerEnergyThreshold(self, _e=None):
        self.setLatestConfigVariable("SpeakerEnergyThreshold")
        self.clearErrorMessage()


    def callbackBindFocusOut_MicRecordTimeout(self, _e=None):
        self.setLatestConfigVariable("MicRecordTimeout")
        self.clearErrorMessage()

    def callbackBindFocusOut_MicPhraseTimeout(self, _e=None):
        self.setLatestConfigVariable("MicPhraseTimeout")
        self.clearErrorMessage()

    def callbackBindFocusOut_MicMaxPhrases(self, _e=None):
        self.setLatestConfigVariable("MicMaxPhrases")
        self.clearErrorMessage()


    def callbackBindFocusOut_SpeakerRecordTimeout(self, _e=None):
        self.setLatestConfigVariable("SpeakerRecordTimeout")
        self.clearErrorMessage()

    def callbackBindFocusOut_SpeakerPhraseTimeout(self, _e=None):
        self.setLatestConfigVariable("SpeakerPhraseTimeout")
        self.clearErrorMessage()

    def callbackBindFocusOut_SpeakerMaxPhrases(self, _e=None):
        self.setLatestConfigVariable("SpeakerMaxPhrases")
        self.clearErrorMessage()







# Show Error Message (Config Window)
    def showErrorMessage_MicEnergyThreshold(self):
        self._showErrorMessage(
            vrct_gui.config_window.sb__progressbar_x_slider__entry_mic_energy_threshold,
            self._makeInvalidValueErrorMessage(i18n.t("config_window.mic_dynamic_energy_threshold.error_message", max=config.MAX_MIC_ENERGY_THRESHOLD))
        )

    def showErrorMessage_MicRecordTimeout(self):
        self._showErrorMessage(
            vrct_gui.config_window.sb__entry_mic_record_timeout,
            self._makeInvalidValueErrorMessage(
                i18n.t(
                    "config_window.mic_record_timeout.error_message",
                    mic_phrase_timeout_label=i18n.t("config_window.mic_phrase_timeout.label")
                )
            )
        )

    def showErrorMessage_MicPhraseTimeout(self):
        self._showErrorMessage(
            vrct_gui.config_window.sb__entry_mic_phrase_timeout,
            self._makeInvalidValueErrorMessage(
                i18n.t(
                    "config_window.mic_phrase_timeout.error_message",
                    mic_record_timeout_label=i18n.t("config_window.mic_record_timeout.label")
                )
            )
        )

    def showErrorMessage_MicMaxPhrases(self):
        self._showErrorMessage(
            vrct_gui.config_window.sb__entry_mic_max_phrases,
            self._makeInvalidValueErrorMessage(i18n.t("config_window.mic_max_phrase.error_message"))
        )


    def showErrorMessage_SpeakerEnergyThreshold(self):
        self._showErrorMessage(
            vrct_gui.config_window.sb__progressbar_x_slider__entry_speaker_energy_threshold,
            self._makeInvalidValueErrorMessage(i18n.t("config_window.speaker_dynamic_energy_threshold.error_message", max=config.MAX_SPEAKER_ENERGY_THRESHOLD))
        )

    def showErrorMessage_SpeakerRecordTimeout(self):
        self._showErrorMessage(
            vrct_gui.config_window.sb__entry_speaker_record_timeout,
            self._makeInvalidValueErrorMessage(
                i18n.t(
                    "config_window.speaker_record_timeout.error_message",
                    speaker_phrase_timeout_label=i18n.t("config_window.speaker_phrase_timeout.label")
                )
            )
        )

    def showErrorMessage_SpeakerPhraseTimeout(self):
        self._showErrorMessage(
            vrct_gui.config_window.sb__entry_speaker_phrase_timeout,
            self._makeInvalidValueErrorMessage(
                i18n.t(
                    "config_window.speaker_phrase_timeout.error_message",
                    speaker_record_timeout_label=i18n.t("config_window.speaker_record_timeout.label")
                )
            )
        )

    def showErrorMessage_SpeakerMaxPhrases(self):
        self._showErrorMessage(
            vrct_gui.config_window.sb__entry_speaker_max_phrases,
            self._makeInvalidValueErrorMessage(i18n.t("config_window.speaker_max_phrase.error_message"))
        )


    def showErrorMessage_CheckSpeakerThreshold_NoDevice(self):
        self._showErrorMessage(
            vrct_gui.config_window.sb__progressbar_x_slider__active_button_speaker_energy_threshold,
            self._makeInvalidValueErrorMessage(i18n.t("config_window.speaker_dynamic_energy_threshold.no_device_error_message"))
        )

    @staticmethod
    def _makeInvalidValueErrorMessage(error_message):
        return i18n.t("config_window.common_error_message.invalid_value") + "\n" + error_message

    def _showErrorMessage(self, target_widget, message):
        self.view_variable.VAR_ERROR_MESSAGE.set(message)
        vrct_gui._showErrorMessage(target_widget=target_widget)





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