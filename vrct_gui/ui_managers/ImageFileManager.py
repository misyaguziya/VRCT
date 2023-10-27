from ..ui_utils import getImageFileFromUiUtils


class ImageFileManager():
    def __init__(self, theme:str ="Dark"):
        self._createDarkModeImages()
        if theme == "Dark":
            pass
        elif theme == "Light":
            self._createLightModeImages()


    def _createDarkModeImages(self):
        self.VRCT_LOGO = getImageFileFromUiUtils("vrct_logo_for_dark_mode.png")
        self.VRCT_LOGO_MARK = getImageFileFromUiUtils("vrct_logo_mark_white.png")

        self.TRANSLATION_ICON = getImageFileFromUiUtils("translation_icon_white.png")
        self.TRANSLATION_ICON_DISABLED = getImageFileFromUiUtils("translation_icon_disabled.png")
        self.MIC_ICON = getImageFileFromUiUtils("mic_icon_white.png")
        self.MIC_ICON_DISABLED = getImageFileFromUiUtils("mic_icon_disabled.png")
        self.HEADPHONES_ICON = getImageFileFromUiUtils("headphones_icon_white.png")
        self.HEADPHONES_ICON_DISABLED = getImageFileFromUiUtils("headphones_icon_disabled.png")
        self.FOREGROUND_ICON = getImageFileFromUiUtils("foreground_icon_white.png")
        self.FOREGROUND_ICON_DISABLED = getImageFileFromUiUtils("foreground_icon_disabled.png")

        self.NARROW_ARROW_DOWN = getImageFileFromUiUtils("narrow_arrow_down.png")

        self.CONFIGURATION_ICON = getImageFileFromUiUtils("configuration_icon_white.png")
        self.CONFIGURATION_ICON_DISABLED = getImageFileFromUiUtils("configuration_icon_disabled.png")

        self.ARROW_LEFT = getImageFileFromUiUtils("arrow_left_white.png")
        self.ARROW_LEFT_DISABLED = getImageFileFromUiUtils("arrow_left_disabled.png")

        self.REFRESH_ICON = getImageFileFromUiUtils("refresh_icon.png")
        self.HELP_ICON = getImageFileFromUiUtils("help_icon_white.png")

    def _createLightModeImages(self):
        self.VRCT_LOGO = getImageFileFromUiUtils("vrct_logo_for_light_mode.png")
        self.VRCT_LOGO_MARK = getImageFileFromUiUtils("vrct_logo_mark_black.png")


        self.TRANSLATION_ICON = getImageFileFromUiUtils("translation_icon_white.png")
        self.TRANSLATION_ICON_DISABLED = getImageFileFromUiUtils("translation_icon_disabled.png")
        self.MIC_ICON = getImageFileFromUiUtils("mic_icon_white.png")
        self.MIC_ICON_DISABLED = getImageFileFromUiUtils("mic_icon_disabled.png")
        self.HEADPHONES_ICON = getImageFileFromUiUtils("headphones_icon_white.png")
        self.HEADPHONES_ICON_DISABLED = getImageFileFromUiUtils("headphones_icon_disabled.png")
        self.FOREGROUND_ICON = getImageFileFromUiUtils("foreground_icon_white.png")
        self.FOREGROUND_ICON_DISABLED = getImageFileFromUiUtils("foreground_icon_disabled.png")

        self.NARROW_ARROW_DOWN = getImageFileFromUiUtils("narrow_arrow_down.png")

        self.CONFIGURATION_ICON = getImageFileFromUiUtils("configuration_icon_white.png")
        self.CONFIGURATION_ICON_DISABLED = getImageFileFromUiUtils("configuration_icon_disabled.png")

        self.ARROW_LEFT = getImageFileFromUiUtils("arrow_left_white.png")
        self.ARROW_LEFT_DISABLED = getImageFileFromUiUtils("arrow_left_disabled.png")

        self.HELP_ICON = getImageFileFromUiUtils("help_icon_white.png")