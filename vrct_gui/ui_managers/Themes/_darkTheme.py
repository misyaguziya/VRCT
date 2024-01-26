from types import SimpleNamespace
from ...ui_utils import getImageFileFromUiUtils

def _darkTheme(base_color):
    theme_settings = SimpleNamespace(
        main = SimpleNamespace(
            # Common
            BASIC_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,
            LABELS_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,

            # Main
            MAIN_BG_COLOR = base_color.DARK_888_COLOR,


            TEXTBOX_BG_COLOR = base_color.DARK_900_COLOR,
            TEXTBOX_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,
            TEXTBOX_TEXT_SUB_COLOR = base_color.DARK_450_COLOR,
            TEXTBOX_SYSTEM_TAG_TEXT_COLOR = base_color.PRIMARY_300_COLOR,
            TEXTBOX_SENT_TAG_TEXT_COLOR = base_color.SENT_400_COLOR,
            TEXTBOX_RECEIVED_TAG_TEXT_COLOR = base_color.RECEIVED_300_COLOR,
            # TEXTBOX_ERROR_TAG_TEXT_COLOR = "#c27583",
            TEXTBOX_TIMESTAMP_TEXT_COLOR = base_color.DARK_600_COLOR,

            TEXTBOX_TAB_BG_PASSIVE_COLOR = base_color.DARK_850_COLOR,
            TEXTBOX_TAB_BG_ACTIVE_COLOR = base_color.DARK_900_COLOR,
            TEXTBOX_TAB_BG_HOVERED_COLOR = base_color.DARK_800_COLOR,
            TEXTBOX_TAB_BG_CLICKED_COLOR = base_color.DARK_925_COLOR,
            TEXTBOX_TAB_TEXT_ACTIVE_COLOR = base_color.DARK_BASIC_TEXT_COLOR,
            TEXTBOX_TAB_TEXT_PASSIVE_COLOR = base_color.DARK_500_COLOR,

            TEXTBOX_ENTRY_TEXT_COLOR = base_color.DARK_300_COLOR,
            TEXTBOX_ENTRY_TEXT_DISABLED_COLOR = base_color.DARK_500_COLOR,
            TEXTBOX_ENTRY_BG_COLOR = base_color.DARK_875_COLOR,
            TEXTBOX_ENTRY_BORDER_COLOR = base_color.DARK_750_COLOR,
            TEXTBOX_ENTRY_PLACEHOLDER_COLOR = base_color.DARK_500_COLOR,
            TEXTBOX_ENTRY_PLACEHOLDER_DISABLED_COLOR = base_color.DARK_700_COLOR,

            SEND_MESSAGE_BUTTON_BG_COLOR = base_color.DARK_850_COLOR,
            SEND_MESSAGE_BUTTON_BG_HOVERED_COLOR = base_color.DARK_825_COLOR,
            SEND_MESSAGE_BUTTON_BG_CLICKED_COLOR = base_color.DARK_900_COLOR,


            # Sidebar
            SIDEBAR_BG_COLOR = base_color.DARK_850_COLOR,

            # Sidebar Features
            SF__BG_COLOR = base_color.DARK_825_COLOR,
            SF__HOVERED_BG_COLOR = base_color.DARK_800_COLOR,
            SF__CLICKED_BG_COLOR = base_color.DARK_875_COLOR,
            SF__TEXT_DISABLED_COLOR = base_color.DARK_500_COLOR,

            SF__SWITCH_BOX_BG_COLOR = base_color.DARK_775_COLOR,
            SF__SWITCH_BOX_HOVERED_BG_COLOR = base_color.DARK_725_COLOR,
            SF__SWITCH_BOX_CLICKED_BG_COLOR = base_color.DARK_825_COLOR,
            SF__SWITCH_BOX_ACTIVE_BG_COLOR = base_color.PRIMARY_500_COLOR,
            SF__SWITCH_BOX_ACTIVE_HOVERED_BG_COLOR = base_color.PRIMARY_400_COLOR,
            SF__SWITCH_BOX_ACTIVE_CLICKED_BG_COLOR = base_color.PRIMARY_700_COLOR,
            SF__SWITCH_BOX_DISABLE_BG_COLOR = base_color.PRIMARY_800_COLOR,

            SF__SWITCH_BOX_BUTTON_COLOR = base_color.DARK_400_COLOR,
            SF__SWITCH_BOX_BUTTON_DISABLED_COLOR = base_color.DARK_600_COLOR,
            # It's not working because It overrode internally.
            SF__SWITCH_BOX_BUTTON_HOVERED_COLOR = base_color.DARK_350_COLOR,

            SF__SELECTED_MARK_ACTIVE_BG_COLOR = base_color.PRIMARY_500_COLOR,
            SF__SELECTED_MARK_ACTIVE_HOVERED_BG_COLOR = base_color.PRIMARY_400_COLOR,
            SF__SELECTED_MARK_ACTIVE_CLICKED_BG_COLOR = base_color.PRIMARY_700_COLOR,
            SF__SELECTED_MARK_DISABLE_BG_COLOR = base_color.PRIMARY_800_COLOR,


            # Sidebar Languages Settings
            SLS__TITLE_TEXT_COLOR = base_color.DARK_400_COLOR,

            SLS__BG_COLOR = base_color.DARK_800_COLOR,

            SLS__PRESETS_TAB_BG_HOVERED_COLOR = base_color.DARK_825_COLOR,
            SLS__PRESETS_TAB_BG_CLICKED_COLOR = base_color.DARK_875_COLOR,
            SLS__PRESETS_TAB_BG_PASSIVE_COLOR = base_color.DARK_850_COLOR,
            SLS__PRESETS_TAB_BG_ACTIVE_COLOR = base_color.DARK_800_COLOR,
            SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR_PASSIVE = base_color.DARK_600_COLOR,
            SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,

            SLS__BOX_BG_COLOR = base_color.DARK_825_COLOR,
            SLS__BOX_SECTION_TITLE_TEXT_COLOR = base_color.DARK_400_COLOR,
            SLS__BOX_ARROWS_TEXT_COLOR = base_color.DARK_500_COLOR,
            SLS__BOX_ARROWS_SWAP_BUTTON_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,
            SLS__BOX_ARROWS_SWAP_BUTTON_HOVERED_COLOR = base_color.DARK_750_COLOR,
            SLS__BOX_ARROWS_SWAP_BUTTON_CLICKED_COLOR = base_color.DARK_850_COLOR,

            SLS__OPTIONMENU_BG_COLOR = base_color.DARK_888_COLOR,
            SLS__OPTIONMENU_HOVERED_BG_COLOR = base_color.DARK_875_COLOR,
            SLS__OPTIONMENU_CLICKED_BG_COLOR = base_color.DARK_900_COLOR,

            SLS__DROPDOWN_MENU_WINDOW_BG_COLOR = base_color.DARK_888_COLOR,
            SLS__DROPDOWN_MENU_WINDOW_BORDER_COLOR = base_color.DARK_650_COLOR,
            SLS__DROPDOWN_MENU_BG_COLOR = base_color.DARK_888_COLOR,
            SLS__DROPDOWN_MENU_HOVERED_BG_COLOR = base_color.DARK_825_COLOR,
            SLS__DROPDOWN_MENU_CLICKED_BG_COLOR = base_color.DARK_900_COLOR,

            CONFIG_BUTTON_BG_COLOR = base_color.DARK_850_COLOR,
            CONFIG_BUTTON_HOVERED_BG_COLOR = base_color.DARK_800_COLOR,
            CONFIG_BUTTON_CLICKED_BG_COLOR = base_color.DARK_875_COLOR,

            MINIMIZE_SIDEBAR_BUTTON_BG_COLOR = base_color.DARK_850_COLOR,
            MINIMIZE_SIDEBAR_BUTTON_HOVERED_BG_COLOR = base_color.DARK_800_COLOR,
            MINIMIZE_SIDEBAR_BUTTON_CLICKED_BG_COLOR = base_color.DARK_900_COLOR,



            TOP_BAR_BUTTON_BG_COLOR = base_color.DARK_888_COLOR,
            TOP_BAR_BUTTON_HOVERED_BG_COLOR = base_color.DARK_850_COLOR,
            TOP_BAR_BUTTON_CLICKED_BG_COLOR = base_color.DARK_900_COLOR,

            UPDATE_AVAILABLE_BUTTON_BG_COLOR = base_color.DARK_888_COLOR,
            UPDATE_AVAILABLE_BUTTON_HOVERED_BG_COLOR = base_color.DARK_850_COLOR,
            UPDATE_AVAILABLE_BUTTON_CLICKED_BG_COLOR = base_color.DARK_900_COLOR,
            UPDATE_AVAILABLE_BUTTON_TEXT_COLOR = base_color.PRIMARY_300_COLOR,

            HELP_AND_INFO_BUTTON_BG_COLOR = base_color.DARK_888_COLOR,
            HELP_AND_INFO_BUTTON_HOVERED_BG_COLOR = base_color.DARK_850_COLOR,
            HELP_AND_INFO_BUTTON_CLICKED_BG_COLOR = base_color.DARK_900_COLOR,
        ),


        selectable_language_window = SimpleNamespace(
            # Selectable Language Window
            BASIC_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,

            MAIN_BG_COLOR = base_color.DARK_875_COLOR,

            GO_BACK_BUTTON_BG_COLOR = base_color.DARK_800_COLOR,
            GO_BACK_BUTTON_BG_HOVERED_COLOR = base_color.DARK_750_COLOR,
            GO_BACK_BUTTON_BG_CLICKED_COLOR = base_color.DARK_875_COLOR,

            TOP_BG_COLOR = base_color.DARK_850_COLOR,
            TITLE_TEXT_COLOR = base_color.DARK_400_COLOR,
            LANGUAGE_BUTTON_BG_COLOR = base_color.DARK_875_COLOR,
            LANGUAGE_BUTTON_BG_HOVERED_COLOR = base_color.DARK_825_COLOR,
            LANGUAGE_BUTTON_BG_CLICKED_COLOR = base_color.DARK_888_COLOR,
        ),



        # Modal Window (Main Window)
        main_window_cover = SimpleNamespace(
            TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,
            BG_COLOR = "#000",
        ),


        confirmation_modal = SimpleNamespace(
            MESSAGE_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,
            FAKE_BORDER_COLOR = base_color.DARK_600_COLOR,
            BG_COLOR = base_color.DARK_800_COLOR,
            CONFIRMATION_BUTTONS_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,

            ACCEPT_BUTTON_BG_COLOR = base_color.PRIMARY_600_COLOR,
            ACCEPT_BUTTON_HOVERED_BG_COLOR = base_color.PRIMARY_450_COLOR,
            ACCEPT_BUTTON_CLICKED_BG_COLOR = base_color.PRIMARY_750_COLOR,
            DENY_BUTTON_BG_COLOR = base_color.DARK_750_COLOR,
            DENY_BUTTON_HOVERED_BG_COLOR = base_color.DARK_700_COLOR,
            DENY_BUTTON_CLICKED_BG_COLOR = base_color.DARK_825_COLOR,
        ),


        config_window = SimpleNamespace(
            # Common
            BASIC_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,
            LABELS_TEXT_COLOR = base_color.DARK_BASIC_TEXT_COLOR,
            LABELS_DESC_TEXT_COLOR = base_color.DARK_500_COLOR,

            LABELS_TEXT_DISABLED_COLOR = base_color.DARK_600_COLOR,

            SB__BUTTON_COLOR = base_color.DARK_888_COLOR,
            SB__BUTTON_HOVERED_COLOR = base_color.DARK_800_COLOR,
            SB__BUTTON_CLICKED_COLOR = base_color.DARK_900_COLOR,


            # Top bar
            TOP_BAR_BG_COLOR = base_color.DARK_850_COLOR,

            # Restart Button
            RESTART_BUTTON_BG_COLOR = base_color.PRIMARY_600_COLOR,
            RESTART_BUTTON_HOVERED_BG_COLOR = base_color.PRIMARY_500_COLOR,
            RESTART_BUTTON_CLICKED_BG_COLOR = base_color.PRIMARY_700_COLOR,


            # Compact Mode
            COMPACT_MODE_SWITCH_BOX_BG_COLOR = base_color.DARK_775_COLOR,
            COMPACT_MODE_SWITCH_BOX_ACTIVE_BG_COLOR = base_color.PRIMARY_500_COLOR,
            COMPACT_MODE_SWITCH_BOX_BUTTON_COLOR = base_color.DARK_350_COLOR,
            COMPACT_MODE_SWITCH_BOX_BUTTON_HOVERED_COLOR = base_color.DARK_300_COLOR,

            # Main
            MAIN_BG_COLOR = base_color.DARK_950_COLOR,

            # This is for fake border color
            SB__WRAPPER_BG_COLOR = base_color.DARK_750_COLOR,

            SB__BG_COLOR = base_color.DARK_888_COLOR,

            SB__OPTIONMENU_BG_COLOR = base_color.DARK_925_COLOR,
            SB__OPTIONMENU_HOVERED_BG_COLOR = base_color.DARK_850_COLOR,
            SB__OPTIONMENU_CLICKED_BG_COLOR = base_color.DARK_950_COLOR,
            SB__DROPDOWN_MENU_WINDOW_BG_COLOR = base_color.DARK_950_COLOR,
            SB__DROPDOWN_MENU_WINDOW_BORDER_COLOR = base_color.DARK_600_COLOR,
            SB__DROPDOWN_MENU_BG_COLOR = base_color.DARK_875_COLOR,
            SB__DROPDOWN_MENU_HOVERED_BG_COLOR = base_color.DARK_800_COLOR,
            SB__DROPDOWN_MENU_CLICKED_BG_COLOR = base_color.DARK_900_COLOR,

            SB__SLIDER_BG_COLOR = base_color.DARK_700_COLOR,
            SB__SLIDER_PROGRESS_BG_COLOR = base_color.DARK_500_COLOR,
            SB__SLIDER_BUTTON_COLOR = base_color.DARK_700_COLOR,
            SB__SLIDER_BUTTON_HOVERED_COLOR = base_color.DARK_600_COLOR,
            SB__SLIDER_TOOLTIP_BG_COLOR = base_color.DARK_850_COLOR,
            SB__SLIDER_TOOLTIP_TEXT_COLOR = base_color.DARK_200_COLOR,

            SB__SWITCH_BOX_BG_COLOR = base_color.DARK_800_COLOR,
            SB__SWITCH_BOX_BG_DISABLED_COLOR = base_color.DARK_900_COLOR,
            SB__SWITCH_BOX_ACTIVE_BG_COLOR = base_color.PRIMARY_500_COLOR,
            SB__SWITCH_BOX_ACTIVE_BG_DISABLED_COLOR = base_color.PRIMARY_700_COLOR,
            SB__SWITCH_BOX_BUTTON_COLOR = base_color.DARK_400_COLOR,
            SB__SWITCH_BOX_BUTTON_DISABLED_COLOR = base_color.DARK_700_COLOR,
            SB__SWITCH_BOX_BUTTON_HOVERED_COLOR = base_color.DARK_350_COLOR,

            SB__CHECKBOX_BORDER_COLOR = base_color.DARK_600_COLOR,
            SB__CHECKBOX_BORDER_DISABLED_COLOR = base_color.DARK_800_COLOR,
            SB__CHECKBOX_HOVER_COLOR = base_color.DARK_800_COLOR,
            SB__CHECKBOX_CHECKED_COLOR = base_color.PRIMARY_700_COLOR,
            SB__CHECKBOX_CHECKMARK_COLOR = base_color.DARK_BASIC_TEXT_COLOR,

            SB__RADIOBUTTON_TEXT_COLOR = base_color.DARK_300_COLOR,
            SB__RADIOBUTTON_BORDER_COLOR = base_color.DARK_600_COLOR,
            SB__RADIOBUTTON_SELECTED_COLOR = base_color.PRIMARY_400_COLOR,
            SB__RADIOBUTTON_BG_HOVERED_COLOR = base_color.DARK_825_COLOR,
            SB__RADIOBUTTON_BG_CLICKED_COLOR = base_color.DARK_900_COLOR,

            SB__ENTRY_TEXT_COLOR = base_color.DARK_300_COLOR,
            SB__ENTRY_BG_COLOR = base_color.DARK_863_COLOR,
            SB__ENTRY_BORDER_COLOR = base_color.DARK_775_COLOR,


            SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_BG_COLOR = base_color.DARK_800_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_PROGRESS_BG_COLOR = base_color.PRIMARY_750_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_PROGRESS_EXCEED_THRESHOLD_BG_COLOR = base_color.PRIMARY_400_COLOR,

            SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_COLOR = base_color.PRIMARY_600_COLOR,
            SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_HOVERED_COLOR = base_color.PRIMARY_400_COLOR,

            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_COLOR = base_color.DARK_800_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_HOVERED_COLOR = base_color.DARK_700_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_CLICKED_COLOR = base_color.DARK_900_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR = base_color.DARK_850_COLOR,

            SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_COLOR = base_color.PRIMARY_600_COLOR,
            SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_HOVERED_COLOR = base_color.PRIMARY_500_COLOR,
            SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_CLICKED_COLOR = base_color.PRIMARY_800_COLOR,

            SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_COLOR = base_color.PRIMARY_600_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_HOVERED_COLOR = base_color.PRIMARY_500_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_CLICKED_COLOR = base_color.PRIMARY_700_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST_BG_COLOR = base_color.DARK_800_COLOR,

            SB__ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_HOVERED_BG_COLOR = base_color.DARK_750_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_CLICKED_BG_COLOR = base_color.DARK_850_COLOR,

            SB__ADD_AND_DELETE_ABLE_LIST_DELETED_BG_COLOR = base_color.DARK_850_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__VALUES_DELETED_BUTTON_HOVERED_BG_COLOR = base_color.DARK_800_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__VALUES_DELETED_BUTTON_CLICKED_BG_COLOR = base_color.DARK_900_COLOR,


            SB__MESSAGE_FORMAT__EXAMPLE_BG_COLOR = "#3a4554", # from VRChat' chat display color
            SB__MESSAGE_FORMAT__EXAMPLE_TEXT_COLOR = base_color.DARK_100_COLOR,
            SB__MESSAGE_FORMAT__SWAP_BUTTON_COLOR = base_color.DARK_875_COLOR,
            SB__MESSAGE_FORMAT__SWAP_BUTTON_HOVERED_COLOR = base_color.DARK_800_COLOR,
            SB__MESSAGE_FORMAT__SWAP_BUTTON_CLICKED_COLOR = base_color.DARK_888_COLOR,




            # Side menu
            SIDE_MENU_BG_COLOR = base_color.DARK_950_COLOR,

            SIDE_MENU_LABELS_BG_COLOR = base_color.DARK_950_COLOR,
            SIDE_MENU_LABELS_BG_FOR_FAKE_BORDER_COLOR = base_color.DARK_950_COLOR,
            SIDE_MENU_LABELS_HOVERED_BG_COLOR = base_color.DARK_850_COLOR,
            SIDE_MENU_LABELS_CLICKED_BG_COLOR = base_color.PRIMARY_750_COLOR,
            SIDE_MENU_LABELS_SELECTED_TEXT_COLOR = base_color.PRIMARY_200_COLOR,

            SIDE_MENU_SELECTED_MARK_ACTIVE_BG_COLOR = base_color.PRIMARY_500_COLOR,

            NOW_VERSION_TEXT_COLOR = base_color.DARK_300_COLOR,

            # Error Message Window for Config Window
            # The color code [#bb4448] is a mixture of [#a9555c] and [#cc3333] (for a redder shade).
            SB__ERROR_MESSAGE_BG_COLOR = "#bb4448",
            SB__ERROR_MESSAGE_TEXT_COLOR = "#fff",
        ),



        image_file = SimpleNamespace(
            VRCT_LOGO = getImageFileFromUiUtils("vrct_logo_for_dark_mode.png"),
            VRCT_LOGO_MARK = getImageFileFromUiUtils("vrct_logo_mark_white.png"),

            TRANSLATION_ICON = getImageFileFromUiUtils("translation_icon_white.png"),
            TRANSLATION_ICON_DISABLED = getImageFileFromUiUtils("translation_icon_disabled.png"),
            MIC_ICON = getImageFileFromUiUtils("mic_icon_white.png"),
            MIC_ICON_DISABLED = getImageFileFromUiUtils("mic_icon_disabled.png"),
            HEADPHONES_ICON = getImageFileFromUiUtils("headphones_icon_white.png"),
            HEADPHONES_ICON_DISABLED = getImageFileFromUiUtils("headphones_icon_disabled.png"),
            FOREGROUND_ICON = getImageFileFromUiUtils("foreground_icon_white.png"),
            FOREGROUND_ICON_DISABLED = getImageFileFromUiUtils("foreground_icon_disabled.png"),

            NARROW_ARROW_DOWN = getImageFileFromUiUtils("narrow_arrow_down_white.png"),

            CONFIGURATION_ICON = getImageFileFromUiUtils("configuration_icon_white.png"),
            CONFIGURATION_ICON_DISABLED = getImageFileFromUiUtils("configuration_icon_disabled.png"),

            ARROW_LEFT = getImageFileFromUiUtils("arrow_left_white.png"),
            ARROW_LEFT_DISABLED = getImageFileFromUiUtils("arrow_left_disabled.png"),

            SEND_MESSAGE_ICON = getImageFileFromUiUtils("send_message_icon_white.png"),
            SEND_MESSAGE_ICON_DISABLED = getImageFileFromUiUtils("send_message_icon_black.png"),
            REFRESH_UPDATE_ICON = getImageFileFromUiUtils("refresh_update_icon.png"),
            REFRESH_ICON = getImageFileFromUiUtils("refresh_icon.png"),
            HELP_ICON = getImageFileFromUiUtils("help_icon_white.png"),

            CANCEL_ICON = getImageFileFromUiUtils("cancel_icon.png"),
            REDO_ICON = getImageFileFromUiUtils("redo_icon_white.png"),
            SWAP_ICON = getImageFileFromUiUtils("swap_icon_white.png"),
            FOLDER_OPEN_ICON = getImageFileFromUiUtils("folder_open_icon_white.png"),
        ),
    )

    return theme_settings