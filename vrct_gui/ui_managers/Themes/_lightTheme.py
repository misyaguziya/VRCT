from types import SimpleNamespace
from ...ui_utils import getImageFileFromUiUtils

def _lightTheme(base_color):
    theme_settings = SimpleNamespace(
        main = SimpleNamespace(
            # Common
            BASIC_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,
            LABELS_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,

            # Main
            MAIN_BG_COLOR = base_color.LIGHT_175_COLOR,


            TEXTBOX_BG_COLOR = base_color.LIGHT_100_COLOR,
            TEXTBOX_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,
            TEXTBOX_TEXT_SUB_COLOR = base_color.LIGHT_600_COLOR,
            TEXTBOX_SYSTEM_TAG_TEXT_COLOR = base_color.PRIMARY_300_COLOR,
            TEXTBOX_SENT_TAG_TEXT_COLOR = base_color.SENT_400_COLOR,
            TEXTBOX_RECEIVED_TAG_TEXT_COLOR = base_color.RECEIVED_300_COLOR,
            # TEXTBOX_ERROR_TAG_TEXT_COLOR = "#c27583",
            TEXTBOX_TIMESTAMP_TEXT_COLOR = base_color.LIGHT_500_COLOR,

            TEXTBOX_TAB_BG_PASSIVE_COLOR = base_color.LIGHT_300_COLOR,
            TEXTBOX_TAB_BG_ACTIVE_COLOR = base_color.LIGHT_125_COLOR,
            TEXTBOX_TAB_BG_HOVERED_COLOR = base_color.LIGHT_250_COLOR,
            TEXTBOX_TAB_BG_CLICKED_COLOR = base_color.LIGHT_100_COLOR,
            TEXTBOX_TAB_TEXT_ACTIVE_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,
            TEXTBOX_TAB_TEXT_PASSIVE_COLOR = base_color.LIGHT_600_COLOR,

            TEXTBOX_ENTRY_TEXT_COLOR = base_color.LIGHT_800_COLOR,
            TEXTBOX_ENTRY_TEXT_DISABLED_COLOR = base_color.LIGHT_500_COLOR,
            TEXTBOX_ENTRY_BG_COLOR = base_color.LIGHT_250_COLOR,
            TEXTBOX_ENTRY_BORDER_COLOR = base_color.LIGHT_400_COLOR,
            TEXTBOX_ENTRY_PLACEHOLDER_COLOR = base_color.LIGHT_600_COLOR,
            TEXTBOX_ENTRY_PLACEHOLDER_DISABLED_COLOR = base_color.LIGHT_400_COLOR,

            SEND_MESSAGE_BUTTON_BG_COLOR = base_color.LIGHT_300_COLOR,
            SEND_MESSAGE_BUTTON_BG_HOVERED_COLOR = base_color.LIGHT_325_COLOR,
            SEND_MESSAGE_BUTTON_BG_CLICKED_COLOR = base_color.LIGHT_350_COLOR,


            # Sidebar
            SIDEBAR_BG_COLOR = base_color.LIGHT_250_COLOR,

            # Sidebar Features
            SF__BG_COLOR = base_color.LIGHT_313_COLOR,
            SF__HOVERED_BG_COLOR = base_color.LIGHT_333_COLOR,
            SF__CLICKED_BG_COLOR = base_color.LIGHT_400_COLOR,
            SF__TEXT_DISABLED_COLOR = base_color.LIGHT_600_COLOR,

            SF__SWITCH_BOX_BG_COLOR = base_color.LIGHT_375_COLOR,
            SF__SWITCH_BOX_HOVERED_BG_COLOR = base_color.LIGHT_400_COLOR,
            SF__SWITCH_BOX_CLICKED_BG_COLOR = base_color.LIGHT_450_COLOR,
            SF__SWITCH_BOX_ACTIVE_BG_COLOR = base_color.PRIMARY_350_COLOR,
            SF__SWITCH_BOX_ACTIVE_HOVERED_BG_COLOR = base_color.PRIMARY_400_COLOR,
            SF__SWITCH_BOX_ACTIVE_CLICKED_BG_COLOR = base_color.PRIMARY_500_COLOR,
            SF__SWITCH_BOX_DISABLE_BG_COLOR = base_color.PRIMARY_200_COLOR,

            SF__SWITCH_BOX_BUTTON_COLOR = base_color.LIGHT_150_COLOR,
            SF__SWITCH_BOX_BUTTON_DISABLED_COLOR = base_color.LIGHT_300_COLOR,
            # It's not working because It overrode internally.
            SF__SWITCH_BOX_BUTTON_HOVERED_COLOR = base_color.LIGHT_300_COLOR,

            SF__SELECTED_MARK_ACTIVE_BG_COLOR = base_color.PRIMARY_350_COLOR,
            SF__SELECTED_MARK_ACTIVE_HOVERED_BG_COLOR = base_color.PRIMARY_400_COLOR,
            SF__SELECTED_MARK_ACTIVE_CLICKED_BG_COLOR = base_color.PRIMARY_500_COLOR,
            SF__SELECTED_MARK_DISABLE_BG_COLOR = base_color.PRIMARY_200_COLOR,


            # Sidebar Languages Settings
            SLS__TITLE_TEXT_COLOR = base_color.LIGHT_800_COLOR,

            SLS__BG_COLOR = base_color.LIGHT_313_COLOR,

            SLS__PRESETS_TAB_BG_HOVERED_COLOR = base_color.LIGHT_300_COLOR,
            SLS__PRESETS_TAB_BG_CLICKED_COLOR = base_color.LIGHT_350_COLOR,
            SLS__PRESETS_TAB_BG_PASSIVE_COLOR = base_color.LIGHT_250_COLOR,
            SLS__PRESETS_TAB_BG_ACTIVE_COLOR = base_color.LIGHT_313_COLOR,
            SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR_PASSIVE = base_color.LIGHT_400_COLOR,
            SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,

            SLS__BOX_BG_COLOR = base_color.LIGHT_333_COLOR,
            SLS__BOX_SECTION_TITLE_TEXT_COLOR = base_color.LIGHT_800_COLOR,
            SLS__BOX_ARROWS_TEXT_COLOR = base_color.LIGHT_700_COLOR,
            SLS__BOX_ARROWS_SWAP_BUTTON_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,
            SLS__BOX_ARROWS_SWAP_BUTTON_HOVERED_COLOR = base_color.LIGHT_200_COLOR,
            SLS__BOX_ARROWS_SWAP_BUTTON_CLICKED_COLOR = base_color.LIGHT_350_COLOR,

            SLS__OPTIONMENU_BG_COLOR = base_color.LIGHT_200_COLOR,
            SLS__OPTIONMENU_HOVERED_BG_COLOR = base_color.LIGHT_250_COLOR,
            SLS__OPTIONMENU_CLICKED_BG_COLOR = base_color.LIGHT_400_COLOR,

            SLS__DROPDOWN_MENU_WINDOW_BG_COLOR = base_color.LIGHT_300_COLOR,
            SLS__DROPDOWN_MENU_WINDOW_BORDER_COLOR = base_color.LIGHT_700_COLOR,
            SLS__DROPDOWN_MENU_BG_COLOR = base_color.LIGHT_300_COLOR,
            SLS__DROPDOWN_MENU_HOVERED_BG_COLOR = base_color.LIGHT_200_COLOR,
            SLS__DROPDOWN_MENU_CLICKED_BG_COLOR = base_color.LIGHT_400_COLOR,

            CONFIG_BUTTON_BG_COLOR = base_color.LIGHT_250_COLOR,
            CONFIG_BUTTON_HOVERED_BG_COLOR = base_color.LIGHT_350_COLOR,
            CONFIG_BUTTON_CLICKED_BG_COLOR = base_color.LIGHT_400_COLOR,

            MINIMIZE_SIDEBAR_BUTTON_BG_COLOR = base_color.LIGHT_250_COLOR,
            MINIMIZE_SIDEBAR_BUTTON_HOVERED_BG_COLOR = base_color.LIGHT_350_COLOR,
            MINIMIZE_SIDEBAR_BUTTON_CLICKED_BG_COLOR = base_color.LIGHT_400_COLOR,



            TOP_BAR_BUTTON_BG_COLOR = base_color.LIGHT_175_COLOR,
            TOP_BAR_BUTTON_HOVERED_BG_COLOR = base_color.LIGHT_300_COLOR,
            TOP_BAR_BUTTON_CLICKED_BG_COLOR = base_color.LIGHT_350_COLOR,

            UPDATE_AVAILABLE_BUTTON_TEXT_COLOR = base_color.PRIMARY_400_COLOR,
        ),


        selectable_language_window = SimpleNamespace(
            # Selectable Language Window
            BASIC_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,

            MAIN_BG_COLOR = base_color.LIGHT_175_COLOR,

            GO_BACK_BUTTON_BG_COLOR = base_color.LIGHT_325_COLOR,
            GO_BACK_BUTTON_BG_HOVERED_COLOR = base_color.LIGHT_400_COLOR,
            GO_BACK_BUTTON_BG_CLICKED_COLOR = base_color.LIGHT_500_COLOR,

            TOP_BG_COLOR = base_color.LIGHT_250_COLOR,
            TITLE_TEXT_COLOR = base_color.LIGHT_700_COLOR,
            LANGUAGE_BUTTON_BG_COLOR = base_color.LIGHT_175_COLOR,
            LANGUAGE_BUTTON_BG_HOVERED_COLOR = base_color.LIGHT_275_COLOR,
            LANGUAGE_BUTTON_BG_CLICKED_COLOR = base_color.LIGHT_325_COLOR,
        ),



        # Modal Window (Main Window)
        main_window_cover = SimpleNamespace(
            TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,
            BG_COLOR = "#fff",
        ),


        confirmation_modal = SimpleNamespace(
            MESSAGE_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,
            FAKE_BORDER_COLOR = base_color.LIGHT_500_COLOR,
            BG_COLOR = base_color.LIGHT_350_COLOR,
            CONFIRMATION_BUTTONS_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,

            ACCEPT_BUTTON_BG_COLOR = base_color.PRIMARY_250_COLOR,
            ACCEPT_BUTTON_HOVERED_BG_COLOR = base_color.PRIMARY_200_COLOR,
            ACCEPT_BUTTON_CLICKED_BG_COLOR = base_color.PRIMARY_300_COLOR,
            DENY_BUTTON_BG_COLOR = base_color.LIGHT_200_COLOR,
            DENY_BUTTON_HOVERED_BG_COLOR = base_color.LIGHT_100_COLOR,
            DENY_BUTTON_CLICKED_BG_COLOR = base_color.LIGHT_300_COLOR,
        ),


        config_window = SimpleNamespace(
            # Common
            BASIC_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,
            LABELS_TEXT_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,
            LABELS_DESC_TEXT_COLOR = base_color.LIGHT_600_COLOR,

            LABELS_TEXT_DISABLED_COLOR = base_color.LIGHT_500_COLOR,

            SB__BUTTON_COLOR = base_color.LIGHT_100_COLOR,
            SB__BUTTON_HOVERED_COLOR = base_color.LIGHT_200_COLOR,
            SB__BUTTON_CLICKED_COLOR = base_color.LIGHT_300_COLOR,


            # Top bar
            TOP_BAR_BG_COLOR = base_color.LIGHT_150_COLOR,

            # Restart Button
            RESTART_BUTTON_BG_COLOR = base_color.PRIMARY_300_COLOR,
            RESTART_BUTTON_HOVERED_BG_COLOR = base_color.PRIMARY_250_COLOR,
            RESTART_BUTTON_CLICKED_BG_COLOR = base_color.PRIMARY_400_COLOR,


            # Compact Mode
            COMPACT_MODE_SWITCH_BOX_BG_COLOR = base_color.LIGHT_500_COLOR,
            COMPACT_MODE_SWITCH_BOX_ACTIVE_BG_COLOR = base_color.PRIMARY_300_COLOR,
            COMPACT_MODE_SWITCH_BOX_BUTTON_COLOR = base_color.LIGHT_300_COLOR,
            COMPACT_MODE_SWITCH_BOX_BUTTON_HOVERED_COLOR = base_color.LIGHT_250_COLOR,

            # Main
            MAIN_BG_COLOR = base_color.LIGHT_300_COLOR,

            # This is for fake border color
            SB__WRAPPER_BG_COLOR = base_color.LIGHT_400_COLOR,

            SB__BG_COLOR = base_color.LIGHT_100_COLOR,

            SB__OPTIONMENU_BG_COLOR = base_color.LIGHT_300_COLOR,
            SB__OPTIONMENU_HOVERED_BG_COLOR = base_color.LIGHT_250_COLOR,
            SB__OPTIONMENU_CLICKED_BG_COLOR = base_color.LIGHT_350_COLOR,
            SB__DROPDOWN_MENU_WINDOW_BG_COLOR = base_color.LIGHT_300_COLOR,
            SB__DROPDOWN_MENU_WINDOW_BORDER_COLOR = base_color.LIGHT_800_COLOR,
            SB__DROPDOWN_MENU_BG_COLOR = base_color.LIGHT_200_COLOR,
            SB__DROPDOWN_MENU_HOVERED_BG_COLOR = base_color.LIGHT_100_COLOR,
            SB__DROPDOWN_MENU_CLICKED_BG_COLOR = base_color.LIGHT_300_COLOR,

            SB__SLIDER_BG_COLOR = base_color.LIGHT_400_COLOR,
            SB__SLIDER_PROGRESS_BG_COLOR = base_color.LIGHT_550_COLOR,
            SB__SLIDER_BUTTON_COLOR = base_color.LIGHT_500_COLOR,
            SB__SLIDER_BUTTON_HOVERED_COLOR = base_color.LIGHT_600_COLOR,
            SB__SLIDER_TOOLTIP_BG_COLOR = base_color.LIGHT_200_COLOR,
            SB__SLIDER_TOOLTIP_TEXT_COLOR = base_color.LIGHT_800_COLOR,

            SB__SWITCH_BOX_BG_COLOR = base_color.LIGHT_400_COLOR,
            SB__SWITCH_BOX_BG_DISABLED_COLOR = base_color.LIGHT_200_COLOR,
            SB__SWITCH_BOX_ACTIVE_BG_COLOR = base_color.PRIMARY_300_COLOR,
            SB__SWITCH_BOX_ACTIVE_BG_DISABLED_COLOR = base_color.PRIMARY_150_COLOR,
            SB__SWITCH_BOX_BUTTON_COLOR = base_color.LIGHT_300_COLOR,
            SB__SWITCH_BOX_BUTTON_DISABLED_COLOR = base_color.LIGHT_150_COLOR,
            SB__SWITCH_BOX_BUTTON_HOVERED_COLOR = base_color.LIGHT_200_COLOR,

            SB__CHECKBOX_BORDER_COLOR = base_color.LIGHT_600_COLOR,
            SB__CHECKBOX_BORDER_DISABLED_COLOR = base_color.LIGHT_300_COLOR,
            SB__CHECKBOX_HOVER_COLOR = base_color.LIGHT_350_COLOR,
            SB__CHECKBOX_CHECKED_COLOR = base_color.PRIMARY_250_COLOR,
            SB__CHECKBOX_CHECKMARK_COLOR = base_color.LIGHT_BASIC_TEXT_COLOR,

            SB__RADIOBUTTON_TEXT_COLOR = base_color.LIGHT_900_COLOR,
            SB__RADIOBUTTON_BORDER_COLOR = base_color.LIGHT_600_COLOR,
            SB__RADIOBUTTON_SELECTED_COLOR = base_color.PRIMARY_400_COLOR,
            SB__RADIOBUTTON_BG_HOVERED_COLOR = base_color.LIGHT_300_COLOR,
            SB__RADIOBUTTON_BG_CLICKED_COLOR = base_color.LIGHT_325_COLOR,

            SB__ENTRY_TEXT_COLOR = base_color.LIGHT_900_COLOR,
            SB__ENTRY_BG_COLOR = base_color.LIGHT_300_COLOR,
            SB__ENTRY_BORDER_COLOR = base_color.LIGHT_400_COLOR,


            SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_BG_COLOR = base_color.LIGHT_350_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_PROGRESS_BG_COLOR = base_color.PRIMARY_500_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_PROGRESS_EXCEED_THRESHOLD_BG_COLOR = base_color.PRIMARY_300_COLOR,

            SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_COLOR = base_color.PRIMARY_300_COLOR,
            SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_HOVERED_COLOR = base_color.PRIMARY_450_COLOR,

            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_COLOR = base_color.LIGHT_300_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_HOVERED_COLOR = base_color.LIGHT_250_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_CLICKED_COLOR = base_color.LIGHT_350_COLOR,
            SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR = base_color.LIGHT_150_COLOR,

            SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_COLOR = base_color.PRIMARY_250_COLOR,
            SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_HOVERED_COLOR = base_color.PRIMARY_300_COLOR,
            SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_CLICKED_COLOR = base_color.PRIMARY_400_COLOR,

            SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_COLOR = base_color.PRIMARY_250_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_HOVERED_COLOR = base_color.PRIMARY_300_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_CLICKED_COLOR = base_color.PRIMARY_400_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST_BG_COLOR = base_color.LIGHT_300_COLOR,

            SB__ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_HOVERED_BG_COLOR = base_color.LIGHT_375_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_CLICKED_BG_COLOR = base_color.LIGHT_450_COLOR,

            SB__ADD_AND_DELETE_ABLE_LIST_DELETED_BG_COLOR = base_color.LIGHT_200_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__VALUES_DELETED_BUTTON_HOVERED_BG_COLOR = base_color.LIGHT_300_COLOR,
            SB__ADD_AND_DELETE_ABLE_LIST__VALUES_DELETED_BUTTON_CLICKED_BG_COLOR = base_color.LIGHT_400_COLOR,


            SB__MESSAGE_FORMAT__EXAMPLE_BG_COLOR = "#5a6b81", # from VRChat' chat display color
            # source #3a4554 (800). and this one is 600 (https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors)
            SB__MESSAGE_FORMAT__EXAMPLE_TEXT_COLOR = base_color.LIGHT_100_COLOR,
            SB__MESSAGE_FORMAT__SWAP_BUTTON_COLOR = base_color.LIGHT_200_COLOR,
            SB__MESSAGE_FORMAT__SWAP_BUTTON_HOVERED_COLOR = base_color.LIGHT_250_COLOR,
            SB__MESSAGE_FORMAT__SWAP_BUTTON_CLICKED_COLOR = base_color.LIGHT_300_COLOR,




            # Side menu
            SIDE_MENU_BG_COLOR = base_color.LIGHT_300_COLOR,

            SIDE_MENU_LABELS_BG_COLOR = base_color.LIGHT_300_COLOR,
            SIDE_MENU_LABELS_BG_FOR_FAKE_BORDER_COLOR = base_color.LIGHT_300_COLOR,
            SIDE_MENU_LABELS_HOVERED_BG_COLOR = base_color.LIGHT_350_COLOR,
            SIDE_MENU_LABELS_CLICKED_BG_COLOR = base_color.PRIMARY_200_COLOR,
            SIDE_MENU_LABELS_SELECTED_TEXT_COLOR = base_color.PRIMARY_350_COLOR,

            SIDE_MENU_SELECTED_MARK_ACTIVE_BG_COLOR = base_color.PRIMARY_350_COLOR,

            NOW_VERSION_TEXT_COLOR = base_color.LIGHT_800_COLOR,

            # Error Message Window for Config Window
            # Check DarkTheme's this part. Based on the color bb4448, used to source, and pick up the number 600 by the generator (https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors)
            SB__ERROR_MESSAGE_BG_COLOR = "#cd4c4f",
            SB__ERROR_MESSAGE_TEXT_COLOR = "#fff",
        ),



        image_file = SimpleNamespace(
            VRCT_LOGO = getImageFileFromUiUtils("vrct_logo_for_light_mode.png"),
            VRCT_LOGO_MARK = getImageFileFromUiUtils("vrct_logo_mark_black.png"),

            TRANSLATION_ICON = getImageFileFromUiUtils("translation_icon_black.png"),
            TRANSLATION_ICON_DISABLED = getImageFileFromUiUtils("translation_icon_disabled.png"),
            MIC_ICON = getImageFileFromUiUtils("mic_icon_black.png"),
            MIC_ICON_DISABLED = getImageFileFromUiUtils("mic_icon_disabled.png"),
            HEADPHONES_ICON = getImageFileFromUiUtils("headphones_icon_black.png"),
            HEADPHONES_ICON_DISABLED = getImageFileFromUiUtils("headphones_icon_disabled.png"),
            FOREGROUND_ICON = getImageFileFromUiUtils("foreground_icon_black.png"),
            FOREGROUND_ICON_DISABLED = getImageFileFromUiUtils("foreground_icon_disabled.png"),

            NARROW_ARROW_DOWN = getImageFileFromUiUtils("narrow_arrow_down_black.png"),

            CONFIGURATION_ICON = getImageFileFromUiUtils("configuration_icon_black.png"),
            CONFIGURATION_ICON_DISABLED = getImageFileFromUiUtils("configuration_icon_disabled.png"),

            ARROW_LEFT = getImageFileFromUiUtils("arrow_left_black.png"),
            ARROW_LEFT_DISABLED = getImageFileFromUiUtils("arrow_left_disabled.png"),

            SEND_MESSAGE_ICON = getImageFileFromUiUtils("send_message_icon_black.png"),
            SEND_MESSAGE_ICON_DISABLED = getImageFileFromUiUtils("send_message_icon_white.png"),
            REFRESH_UPDATE_ICON = getImageFileFromUiUtils("refresh_update_icon.png"),
            REFRESH_ICON = getImageFileFromUiUtils("refresh_icon.png"),
            HELP_ICON = getImageFileFromUiUtils("help_icon_black.png"),

            CANCEL_ICON = getImageFileFromUiUtils("cancel_icon.png"),
            REDO_ICON = getImageFileFromUiUtils("redo_icon_black.png"),
            SWAP_ICON = getImageFileFromUiUtils("swap_icon_black.png"),
            FOLDER_OPEN_ICON = getImageFileFromUiUtils("folder_open_icon_black.png"),
        ),
    )

    return theme_settings