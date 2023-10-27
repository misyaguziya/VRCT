from types import SimpleNamespace

class ColorThemeManager():
    def __init__(self, theme):
        # self.main = SimpleNamespace()
        # self.config_window = SimpleNamespace()
        # self.selectable_language_window = SimpleNamespace()
        # self.main_window_cover = SimpleNamespace()
        # self.error_message_window = SimpleNamespace()
        # self.confirmation_modal = SimpleNamespace()

        # old one. But leave it here for now.
        # self.PRIMARY_100_COLOR = "#c4eac1"
        # self.PRIMARY_200_COLOR = "#9cdd98"
        # self.PRIMARY_300_COLOR = "#70d16c"
        # self.PRIMARY_400_COLOR = "#49c649"
        # self.PRIMARY_500_COLOR = "#0abb1d"
        # self.PRIMARY_600_COLOR = "#00ac11"
        # self.PRIMARY_650_COLOR = "#00A309"
        # self.PRIMARY_700_COLOR = "#009900"
        # self.PRIMARY_800_COLOR = "#008800"
        # self.PRIMARY_900_COLOR = "#006900"


        # new one.
        self.PRIMARY_100_COLOR = "#b7ded8"
        self.PRIMARY_200_COLOR = "#8acac0"
        self.PRIMARY_300_COLOR = "#61b4a7"
        self.PRIMARY_400_COLOR = "#48a495"
        self.PRIMARY_450_COLOR = "#429c8c"
        self.PRIMARY_500_COLOR = "#3b9483"
        self.PRIMARY_600_COLOR = "#368777"
        self.PRIMARY_650_COLOR = "#347f6f"
        self.PRIMARY_700_COLOR = "#317767"
        self.PRIMARY_750_COLOR = "#2F6F60"
        self.PRIMARY_800_COLOR = "#2c6759"
        self.PRIMARY_900_COLOR = "#214b3f"


        self.DARK_100_COLOR = "#f5f7fb"
        self.DARK_200_COLOR = "#f1f2f6"
        self.DARK_300_COLOR = "#e9eaee"
        self.DARK_350_COLOR = "#d8d9dd"
        self.DARK_400_COLOR = "#c7c8cc"
        self.DARK_450_COLOR = "#b8b9bd"
        self.DARK_500_COLOR = "#a9aaae"
        self.DARK_600_COLOR = "#7f8084"
        self.DARK_650_COLOR = "#75767a"
        self.DARK_700_COLOR = "#6a6c6f"
        self.DARK_725_COLOR = "#636467"
        self.DARK_750_COLOR = "#5b5c5f"
        self.DARK_775_COLOR = "#535457"
        self.DARK_800_COLOR = "#4b4c4f"
        self.DARK_825_COLOR = "#434447"
        self.DARK_850_COLOR = "#3a3b3e"
        self.DARK_863_COLOR = "#36373a"
        self.DARK_875_COLOR = "#323336"
        self.DARK_888_COLOR = "#2e2f32"
        self.DARK_900_COLOR = "#292a2d"
        self.DARK_925_COLOR = "#242528"
        self.DARK_950_COLOR = "#1f2022"
        self.DARK_975_COLOR = "#1a1b1d"
        self.DARK_1000_COLOR = "#151517" # THE DARKEST COLOR


        self.LIGHT_100_COLOR = "#f2f2f2" # THE LIGHTEST COLOR
        self.LIGHT_200_COLOR = "#e9e9e9"
        self.LIGHT_250_COLOR = "#e1e1e1"
        self.LIGHT_300_COLOR = "#d9d9d9"
        self.LIGHT_325_COLOR = "#d0d0d0"
        self.LIGHT_350_COLOR = "#c7c7c7"
        self.LIGHT_375_COLOR = "#bebebe"
        self.LIGHT_400_COLOR = "#b5b5b5"
        self.LIGHT_450_COLOR = "#a5a5a5"
        self.LIGHT_500_COLOR = "#959595"
        self.LIGHT_600_COLOR = "#6d6d6d"
        self.LIGHT_700_COLOR = "#5a5a5a"
        self.LIGHT_750_COLOR = "#515151"
        self.LIGHT_800_COLOR = "#3b3b3b"
        self.LIGHT_850_COLOR = "#323232"
        self.LIGHT_875_COLOR = "#2b2b2b"
        self.LIGHT_900_COLOR = "#1b1b1b"
        # self.LIGHT_925_COLOR = "#121212"
        # self.LIGHT_950_COLOR = "#0c0c0c"
        # self.LIGHT_975_COLOR = "#070707"
        self.LIGHT_1000_COLOR = "#010101"


        if theme == "Dark":
            self._createDarkModeColor()
        # elif theme == "Light":
        #     self._createLightModeColor()


    def _createDarkModeColor(self):
        self.main = SimpleNamespace(
            # Common
            BASIC_TEXT_COLOR = self.LIGHT_100_COLOR,
            LABELS_TEXT_COLOR = self.LIGHT_100_COLOR,

            # Main
            MAIN_BG_COLOR = self.DARK_888_COLOR,


            TEXTBOX_BG_COLOR = self.DARK_900_COLOR,
            TEXTBOX_TEXT_COLOR = self.LIGHT_100_COLOR,
            TEXTBOX_TEXT_SUB_COLOR = self.DARK_450_COLOR,
            TEXTBOX_SYSTEM_TAG_TEXT_COLOR = self.PRIMARY_300_COLOR,
            TEXTBOX_SENT_TAG_TEXT_COLOR = "#6197b4",
            TEXTBOX_RECEIVED_TAG_TEXT_COLOR = "#a861b4",
            TEXTBOX_ERROR_TAG_TEXT_COLOR = "#c27583",
            TEXTBOX_TIMESTAMP_TEXT_COLOR = self.DARK_600_COLOR,

            TEXTBOX_TAB_BG_PASSIVE_COLOR = self.DARK_850_COLOR,
            TEXTBOX_TAB_BG_ACTIVE_COLOR = self.DARK_900_COLOR,
            TEXTBOX_TAB_BG_HOVERED_COLOR = self.DARK_800_COLOR,
            TEXTBOX_TAB_BG_CLICKED_COLOR = self.DARK_925_COLOR,
            TEXTBOX_TAB_TEXT_ACTIVE_COLOR = self.LIGHT_100_COLOR,
            TEXTBOX_TAB_TEXT_PASSIVE_COLOR = self.DARK_500_COLOR,

            TEXTBOX_ENTRY_TEXT_COLOR = self.DARK_300_COLOR,
            TEXTBOX_ENTRY_TEXT_DISABLED_COLOR = self.DARK_500_COLOR,
            TEXTBOX_ENTRY_BG_COLOR = self.DARK_875_COLOR,
            TEXTBOX_ENTRY_BORDER_COLOR = self.DARK_750_COLOR,
            TEXTBOX_ENTRY_PLACEHOLDER_COLOR = self.DARK_500_COLOR,
            TEXTBOX_ENTRY_PLACEHOLDER_DISABLED_COLOR = self.DARK_700_COLOR,


            # Sidebar
            SIDEBAR_BG_COLOR = self.DARK_850_COLOR,

            # Sidebar Features
            SF__BG_COLOR = self.DARK_825_COLOR,
            SF__HOVERED_BG_COLOR = self.DARK_800_COLOR,
            SF__CLICKED_BG_COLOR = self.DARK_875_COLOR,
            SF__TEXT_DISABLED_COLOR = self.DARK_500_COLOR,

            SF__SWITCH_BOX_BG_COLOR = self.DARK_775_COLOR,
            SF__SWITCH_BOX_HOVERED_BG_COLOR = self.DARK_725_COLOR,
            SF__SWITCH_BOX_CLICKED_BG_COLOR = self.DARK_825_COLOR,
            SF__SWITCH_BOX_ACTIVE_BG_COLOR = self.PRIMARY_500_COLOR,
            SF__SWITCH_BOX_ACTIVE_HOVERED_BG_COLOR = self.PRIMARY_400_COLOR,
            SF__SWITCH_BOX_ACTIVE_CLICKED_BG_COLOR = self.PRIMARY_700_COLOR,
            SF__SWITCH_BOX_DISABLE_BG_COLOR = self.PRIMARY_800_COLOR,

            SF__SWITCH_BOX_BUTTON_COLOR = self.DARK_400_COLOR,
            # It's not working because It overrode internally.
            SF__SWITCH_BOX_BUTTON_HOVERED_COLOR = self.DARK_350_COLOR,

            SF__SELECTED_MARK_ACTIVE_BG_COLOR = self.PRIMARY_500_COLOR,
            SF__SELECTED_MARK_ACTIVE_HOVERED_BG_COLOR = self.PRIMARY_400_COLOR,
            SF__SELECTED_MARK_ACTIVE_CLICKED_BG_COLOR = self.PRIMARY_700_COLOR,
            SF__SELECTED_MARK_DISABLE_BG_COLOR = self.PRIMARY_800_COLOR,


            # Sidebar Languages Settings
            SLS__TITLE_TEXT_COLOR = self.DARK_400_COLOR,

            SLS__BG_COLOR = self.DARK_800_COLOR,

            SLS__PRESETS_TAB_BG_HOVERED_COLOR = self.DARK_825_COLOR,
            SLS__PRESETS_TAB_BG_CLICKED_COLOR = self.DARK_875_COLOR,
            SLS__PRESETS_TAB_BG_PASSIVE_COLOR = self.DARK_850_COLOR,
            SLS__PRESETS_TAB_BG_ACTIVE_COLOR = self.DARK_800_COLOR,
            SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR_PASSIVE = self.DARK_600_COLOR,
            SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR = self.LIGHT_100_COLOR,

            SLS__BOX_BG_COLOR = self.DARK_825_COLOR,
            SLS__BOX_SECTION_TITLE_TEXT_COLOR = self.DARK_400_COLOR,
            SLS__BOX_ARROWS_TEXT_COLOR = self.DARK_500_COLOR,

            SLS__OPTIONMENU_BG_COLOR = self.DARK_888_COLOR,
            SLS__OPTIONMENU_HOVERED_BG_COLOR = self.DARK_875_COLOR,
            SLS__OPTIONMENU_CLICKED_BG_COLOR = self.DARK_900_COLOR,


            CONFIG_BUTTON_BG_COLOR = self.DARK_850_COLOR,
            CONFIG_BUTTON_HOVERED_BG_COLOR = self.DARK_800_COLOR,
            CONFIG_BUTTON_CLICKED_BG_COLOR = self.DARK_875_COLOR,

            MINIMIZE_SIDEBAR_BUTTON_BG_COLOR = self.DARK_850_COLOR,
            MINIMIZE_SIDEBAR_BUTTON_HOVERED_BG_COLOR = self.DARK_800_COLOR,
            MINIMIZE_SIDEBAR_BUTTON_CLICKED_BG_COLOR = self.DARK_900_COLOR,



            TOP_BAR_BUTTON_BG_COLOR = self.DARK_888_COLOR,
            TOP_BAR_BUTTON_HOVERED_BG_COLOR = self.DARK_850_COLOR,
            TOP_BAR_BUTTON_CLICKED_BG_COLOR = self.DARK_900_COLOR,

            UPDATE_AVAILABLE_BUTTON_BG_COLOR = self.DARK_888_COLOR,
            UPDATE_AVAILABLE_BUTTON_HOVERED_BG_COLOR = self.DARK_850_COLOR,
            UPDATE_AVAILABLE_BUTTON_CLICKED_BG_COLOR = self.DARK_900_COLOR,
            UPDATE_AVAILABLE_BUTTON_TEXT_COLOR = self.PRIMARY_300_COLOR,

            HELP_AND_INFO_BUTTON_BG_COLOR = self.DARK_888_COLOR,
            HELP_AND_INFO_BUTTON_HOVERED_BG_COLOR = self.DARK_850_COLOR,
            HELP_AND_INFO_BUTTON_CLICKED_BG_COLOR = self.DARK_900_COLOR,
        )


        self.selectable_language_window = SimpleNamespace(
            # Selectable Language Window
            BASIC_TEXT_COLOR = self.LIGHT_100_COLOR,

            MAIN_BG_COLOR = self.DARK_875_COLOR,

            GO_BACK_BUTTON_BG_COLOR = self.DARK_800_COLOR,
            GO_BACK_BUTTON_BG_HOVERED_COLOR = self.DARK_750_COLOR,
            GO_BACK_BUTTON_BG_CLICKED_COLOR = self.DARK_875_COLOR,

            TOP_BG_COLOR = self.DARK_850_COLOR,
            TITLE_TEXT_COLOR = self.DARK_400_COLOR,
            LANGUAGE_BUTTON_BG_COLOR = self.LIGHT_100_COLOR,
            LANGUAGE_BUTTON_BG_HOVERED_COLOR = self.DARK_825_COLOR,
            LANGUAGE_BUTTON_BG_CLICKED_COLOR = self.DARK_888_COLOR,
        )



        # Modal Window (Main Window)
        self.main_window_cover = SimpleNamespace(
            TEXT_COLOR = self.LIGHT_100_COLOR,
        )


        self.confirmation_modal = SimpleNamespace(
            MESSAGE_TEXT_COLOR = self.LIGHT_100_COLOR,
            FAKE_BORDER_COLOR = self.DARK_600_COLOR,
            BG_COLOR = self.DARK_800_COLOR,
            CONFIRMATION_BUTTONS_TEXT_COLOR = self.LIGHT_100_COLOR,

            ACCEPT_BUTTON_BG_COLOR = self.PRIMARY_600_COLOR,
            ACCEPT_BUTTON_HOVERED_BG_COLOR = self.PRIMARY_450_COLOR,
            ACCEPT_BUTTON_CLICKED_BG_COLOR = self.PRIMARY_750_COLOR,
            DENY_BUTTON_BG_COLOR = self.DARK_750_COLOR,
            DENY_BUTTON_HOVERED_BG_COLOR = self.DARK_700_COLOR,
            DENY_BUTTON_CLICKED_BG_COLOR = self.DARK_825_COLOR,
        )


        self.config_window = SimpleNamespace(
            # Common
            BASIC_TEXT_COLOR = self.LIGHT_100_COLOR,
            LABELS_TEXT_COLOR = self.LIGHT_100_COLOR,
            LABELS_DESC_TEXT_COLOR = self.DARK_500_COLOR,

            LABELS_TEXT_DISABLED_COLOR = self.DARK_600_COLOR,


            # Top bar
            TOP_BAR_BG_COLOR = self.DARK_850_COLOR,

            # Restart Button
            RESTART_BUTTON_BG_COLOR = self.PRIMARY_600_COLOR,
            RESTART_BUTTON_HOVERED_BG_COLOR = self.PRIMARY_500_COLOR,
            RESTART_BUTTON_CLICKED_BG_COLOR = self.PRIMARY_700_COLOR,


            # Compact Mode
            COMPACT_MODE_SWITCH_BOX_BG_COLOR = self.DARK_775_COLOR,
            COMPACT_MODE_SWITCH_BOX_ACTIVE_BG_COLOR = self.PRIMARY_500_COLOR,
            COMPACT_MODE_SWITCH_BOX_BUTTON_COLOR = self.DARK_350_COLOR,
            COMPACT_MODE_SWITCH_BOX_BUTTON_HOVERED_COLOR = self.DARK_300_COLOR,

            # Main
            MAIN_BG_COLOR = self.DARK_950_COLOR,

            # This is for fake border color
            SB__WRAPPER_BG_COLOR = self.DARK_750_COLOR,

            SB__BG_COLOR = self.DARK_888_COLOR,

            SB__OPTIONMENU_BG_COLOR = self.DARK_925_COLOR,
            SB__OPTIONMENU_HOVERED_BG_COLOR = self.DARK_850_COLOR,
            SB__OPTIONMENU_CLICKED_BG_COLOR = self.DARK_950_COLOR,
            SB__DROPDOWN_MENU_WINDOW_BG_COLOR = self.DARK_950_COLOR,
            SB__DROPDOWN_MENU_WINDOW_BORDER_COLOR = self.DARK_600_COLOR,
            SB__DROPDOWN_MENU_BG_COLOR = self.DARK_875_COLOR,
            SB__DROPDOWN_MENU_HOVERED_BG_COLOR = self.DARK_800_COLOR,
            SB__DROPDOWN_MENU_CLICKED_BG_COLOR = self.DARK_900_COLOR,

            SB__SLIDER_BG_COLOR = self.DARK_700_COLOR,
            SB__SLIDER_PROGRESS_BG_COLOR = self.DARK_500_COLOR,
            SB__SLIDER_BUTTON_COLOR = self.DARK_700_COLOR,
            SB__SLIDER_BUTTON_HOVERED_COLOR = self.DARK_600_COLOR,
            SB__SLIDER_TOOLTIP_BG_COLOR = self.DARK_850_COLOR,
            SB__SLIDER_TOOLTIP_TEXT_COLOR = self.DARK_200_COLOR,

            SB__SWITCH_BOX_BG_COLOR = self.DARK_800_COLOR,
            SB__SWITCH_BOX_ACTIVE_BG_COLOR = self.PRIMARY_500_COLOR,
            SB__SWITCH_BOX_BUTTON_COLOR = self.DARK_400_COLOR,
            SB__SWITCH_BOX_BUTTON_HOVERED_COLOR = self.DARK_350_COLOR,

            SB__CHECKBOX_BORDER_COLOR = self.DARK_600_COLOR,
            SB__CHECKBOX_HOVER_COLOR = self.DARK_800_COLOR,
            SB__CHECKBOX_CHECKED_COLOR = self.PRIMARY_700_COLOR,
            SB__CHECKBOX_CHECKMARK_COLOR = self.LIGHT_100_COLOR,

            SB__ENTRY_TEXT_COLOR = self.DARK_300_COLOR,
            SB__ENTRY_BG_COLOR = self.DARK_863_COLOR,
            SB__ENTRY_BORDER_COLOR = self.DARK_775_COLOR,


            SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_BG_COLOR = self.DARK_800_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_PROGRESS_BG_COLOR = self.PRIMARY_750_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_PROGRESS_EXCEED_THRESHOLD_BG_COLOR = self.PRIMARY_400_COLOR,

            SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_COLOR = self.PRIMARY_600_COLOR,
            SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_HOVERED_COLOR = self.PRIMARY_400_COLOR,

            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_COLOR = self.DARK_800_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_HOVERED_COLOR = self.DARK_700_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_CLICKED_COLOR = self.DARK_900_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR = self.DARK_850_COLOR,

            SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_COLOR = self.PRIMARY_600_COLOR,
            SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_HOVERED_COLOR = self.PRIMARY_500_COLOR,
            SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_CLICKED_COLOR = self.PRIMARY_800_COLOR,


            # Side menu
            SIDE_MENU_BG_COLOR = self.DARK_950_COLOR,

            SIDE_MENU_LABELS_BG_COLOR = self.DARK_950_COLOR,
            SIDE_MENU_LABELS_BG_FOR_FAKE_BORDER_COLOR = self.DARK_950_COLOR,
            SIDE_MENU_LABELS_HOVERED_BG_COLOR = self.DARK_850_COLOR,
            SIDE_MENU_LABELS_CLICKED_BG_COLOR = self.PRIMARY_750_COLOR,
            SIDE_MENU_LABELS_SELECTED_TEXT_COLOR = self.PRIMARY_200_COLOR,

            SIDE_MENU_SELECTED_MARK_ACTIVE_BG_COLOR = self.PRIMARY_500_COLOR,

            NOW_VERSION_TEXT_COLOR = self.DARK_300_COLOR,

            # Error Message Window for Config Window
            # The color code [#bb4448] is a mixture of [#a9555c] and [#cc3333] (for a redder shade).
            SB__ERROR_MESSAGE_BG_COLOR = "#bb4448",
            SB__ERROR_MESSAGE_TEXT_COLOR = "#fff",
        )