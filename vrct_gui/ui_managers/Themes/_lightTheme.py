from types import SimpleNamespace
from ...ui_utils import getImageFileFromUiUtils

def _lightTheme(base_color):
    theme_settings = SimpleNamespace(
        main = SimpleNamespace(
            # Common
            BASIC_TEXT_COLOR = base_color.LIGHT_100_COLOR,
            LABELS_TEXT_COLOR = base_color.LIGHT_100_COLOR,

            # Main
            MAIN_BG_COLOR = base_color.DARK_888_COLOR,
        ),

        config_window = SimpleNamespace(
            # Common
            BASIC_TEXT_COLOR = base_color.LIGHT_100_COLOR,
        ),


        image_file = SimpleNamespace(
            VRCT_LOGO = getImageFileFromUiUtils("vrct_logo_for_light_mode.png"),
            VRCT_LOGO_MARK = getImageFileFromUiUtils("vrct_logo_mark_black.png"),


            TRANSLATION_ICON = getImageFileFromUiUtils("translation_icon_white.png"),
            TRANSLATION_ICON_DISABLED = getImageFileFromUiUtils("translation_icon_disabled.png"),
            MIC_ICON = getImageFileFromUiUtils("mic_icon_white.png"),
            MIC_ICON_DISABLED = getImageFileFromUiUtils("mic_icon_disabled.png"),
            HEADPHONES_ICON = getImageFileFromUiUtils("headphones_icon_white.png"),
            HEADPHONES_ICON_DISABLED = getImageFileFromUiUtils("headphones_icon_disabled.png"),
            FOREGROUND_ICON = getImageFileFromUiUtils("foreground_icon_white.png"),
            FOREGROUND_ICON_DISABLED = getImageFileFromUiUtils("foreground_icon_disabled.png"),

            NARROW_ARROW_DOWN = getImageFileFromUiUtils("narrow_arrow_down.png"),

            CONFIGURATION_ICON = getImageFileFromUiUtils("configuration_icon_white.png"),
            CONFIGURATION_ICON_DISABLED = getImageFileFromUiUtils("configuration_icon_disabled.png"),

            ARROW_LEFT = getImageFileFromUiUtils("arrow_left_white.png"),
            ARROW_LEFT_DISABLED = getImageFileFromUiUtils("arrow_left_disabled.png"),

            HELP_ICON = getImageFileFromUiUtils("help_icon_white.png"),
        ),
    )

    return theme_settings