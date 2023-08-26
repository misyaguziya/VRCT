class ImageFilenameManager():
    def __init__(self, theme:str ="Dark"):
        if theme == "Dark":
            return self._createDarkModeImages()
        elif theme == "Light":
            return self._createLightModeImages()


    def _createDarkModeImages(self):
        self.VRCT_LOGO = "vrct_logo_for_dark_mode.png"
        self.VRCT_LOGO_MARK = "vrct_logo_mark_white.png"

        self.TRANSLATION_ICON = "translation_icon_white.png"
        self.TRANSLATION_ICON_DISABLED = "translation_icon_disabled.png"
        self.MIC_ICON = "mic_icon_white.png"
        self.MIC_ICON_DISABLED = "mic_icon_disabled.png"
        self.HEADPHONES_ICON = "headphones_icon_white.png"
        self.HEADPHONES_ICON_DISABLED = "headphones_icon_disabled.png"
        self.FOREGROUND_ICON = "foreground_icon_white.png"
        self.FOREGROUND_ICON_DISABLED = "foreground_icon_disabled.png"

        self.NARROW_ARROW_DOWN = "narrow_arrow_down.png"

        self.CONFIGURATION_ICON = "configuration_icon_white.png"
        self.CONFIGURATION_ICON_DISABLED = "configuration_icon_disabled.png"

        self.ARROW_LEFT = "arrow_left_white.png"
        self.ARROW_LEFT_DISABLED = "arrow_left_disabled.png"

        self.HELP_ICON = "help_icon_white.png"

    def _createLightModeImages(self):
        self.VRCT_LOGO = "vrct_logo_for_light_mode.png"
        self.VRCT_LOGO_MARK = "vrct_logo_mark_black.png"


        self.TRANSLATION_ICON = "translation_icon_white.png"
        self.TRANSLATION_ICON_DISABLED = "translation_icon_disabled.png"
        self.MIC_ICON = "mic_icon_white.png"
        self.MIC_ICON_DISABLED = "mic_icon_disabled.png"
        self.HEADPHONES_ICON = "headphones_icon_white.png"
        self.HEADPHONES_ICON_DISABLED = "headphones_icon_disabled.png"
        self.FOREGROUND_ICON = "foreground_icon_white.png"
        self.FOREGROUND_ICON_DISABLED = "foreground_icon_disabled.png"

        self.NARROW_ARROW_DOWN = "narrow_arrow_down.png"

        self.CONFIGURATION_ICON = "configuration_icon_white.png"
        self.CONFIGURATION_ICON_DISABLED = "configuration_icon_disabled.png"

        self.ARROW_LEFT = "arrow_left_white.png"
        self.ARROW_LEFT_DISABLED = "arrow_left_disabled.png"

        self.HELP_ICON = "help_icon_white.png"