from types import SimpleNamespace

class UiScalingManager():
    def __init__(self, scaling_percentage):
        scaling_float = int(scaling_percentage.replace("%", "")) / 100
        print(scaling_float)
        self.SCALING_FLOAT = max(scaling_float, 0.4)
        self.main = SimpleNamespace()
        self.config_window = SimpleNamespace()

        self._calculatedUiSizes()




    def _calculatedUiSizes(self):
        # Common

        # Main
        self.main.TEXTBOX_PADX = self._calculateUiSize(16)
        self.main.TEXTBOX_CORNER_RADIUS = self._calculateUiSize(6)

        self.main.TEXTBOX_TAB_CORNER_RADIUS = self._calculateUiSize(8)
        self.main.TEXTBOX_TAB_FONT_SIZE = self._calculateUiSize(12)
        self.main.TEXTBOX_TAB_PADX = self._calculateUiSize(10)
        self.main.TEXTBOX_TAB_PADY = (self._calculateUiSize(4), self._calculateUiSize(10))

        self.main.TEXTBOX_ENTRY_FONT_SIZE = self._calculateUiSize(16)
        self.main.TEXTBOX_ENTRY_HEIGHT = self._calculateUiSize(40)
        self.main.TEXTBOX_ENTRY_PADX = self.main.TEXTBOX_PADX
        self.main.TEXTBOX_ENTRY_PADY = self._calculateUiSize(10)
        self.main.TEXTBOX_ENTRY_IPADX = self._calculateUiSize(14)
        self.main.TEXTBOX_ENTRY_IPADY = (self._calculateUiSize(2, True), self._calculateUiSize(3, True))


        # Sidebar
        self.main.SIDEBAR_WIDTH = self._calculateUiSize(230)
        self.main.COMPACT_MODE_SIDEBAR_WIDTH = self._calculateUiSize(60)

        # Sidebar Features
        self.main.SF__LOGO_MAX_SIZE = self._calculateUiSize(120)
        self.main.SF__LOGO_PADY = (self._calculateUiSize(12),self._calculateUiSize(8))
        self.main.SF__LOGO_HEIGHT_FOR_ADJUSTMENT = (self._calculateUiSize(8))

        self.main.SF__LABELS_IPADY = self._calculateUiSize(16)
        self.main.SF__COMPACT_MODE_ICON_PADY = self.main.SF__LABELS_IPADY
        self.main.SF__LABEL_LEFT_PAD = self._calculateUiSize(20)
        self.main.SF__LABEL_FONT_SIZE = self._calculateUiSize(16)

        self.main.SF__SWITCH_BOX_RIGHT_PAD = self._calculateUiSize(10)
        self.main.SF__SWITCH_BOX_WIDTH = self._calculateUiSize(40)
        self.main.SF__SWITCH_BOX_HEIGHT = self._calculateUiSize(16)

        self.main.SF__SELECTED_MARK_WIDTH = self._calculateUiSize(3, True)


        # Sidebar Quick Language Settings, SQLS
        self.main.SLS__TITLE_FONT_SIZE = self._calculateUiSize(16)
        self.main.SLS__TITLE_PADY = (self._calculateUiSize(12), self._calculateUiSize(6))

        self.main.SLS__PRESET_TAB_NUMBER_FONT_SIZE = self._calculateUiSize(16)

        self.main.SLS__BOX_SECTION_TITLE_FONT_SIZE = self._calculateUiSize(16)
        self.main.SLS__BOX_SECTION_TITLE_BOTTOM_PADY = self._calculateUiSize(10)
        self.main.SLS__BOX_IPADY = (self._calculateUiSize(8),self._calculateUiSize(18))
        self.main.SLS__BOX_DROPDOWN_MENU_FONT_SIZE = self._calculateUiSize(14)
        self.main.SLS__BOX_DROPDOWN_MENU_WIDTH = self._calculateUiSize(200)
        self.main.SLS__BOX_ARROWS_PADY = self._calculateUiSize(10)
        self.main.SLS__BOX_ARROWS_IMAGE_SIZE = self.dupTuple(self._calculateUiSize(16))
        self.main.SLS__BOX_ARROWS_DESC_FONT_SIZE = self._calculateUiSize(12)
        self.main.SLS__BOX_ARROWS_DESC_PADX = self._calculateUiSize(6)
        self.main.SLS__BOX_TOP_PADY = self._calculateUiSize(16)

        self.main.SIDEBAR_CONFIG_BUTTON_CORNER_RADIUS = self._calculateUiSize(6)
        self.main.SIDEBAR_CONFIG_BUTTON_PADX = self._calculateUiSize(10)
        self.main.SIDEBAR_CONFIG_BUTTON_PADY = self._calculateUiSize(10)
        self.main.SIDEBAR_CONFIG_BUTTON_IPADY = self._calculateUiSize(8)


        self.main.HELP_AND_INFO_BUTTON_CORNER_RADIUS = self._calculateUiSize(6)
        self.main.HELP_AND_INFO_BUTTON_SIZE = self._calculateUiSize(24)
        self.main.HELP_AND_INFO_BUTTON_PADX = (0, self._calculateUiSize(6))
        self.main.HELP_AND_INFO_BUTTON_PADY = (self._calculateUiSize(6),0)
        self.main.HELP_AND_INFO_BUTTON_IPADXY = self._calculateUiSize(6)

        self.main.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_X = int(self.main.TEXTBOX_PADX/2+self.main.TEXTBOX_CORNER_RADIUS*2)
        self.main.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_Y = self._calculateUiSize(26)




        # Top bar common
        self.config_window.TOP_BAR__HEIGHT = self._calculateUiSize(40)
        self.config_window.TOP_BAR__IPADY = self._calculateUiSize(12)

        # Top bar Side
        self.config_window.TOP_BAR_SIDE__WIDTH = self._calculateUiSize(220)
        self.config_window.TOP_BAR_SIDE__CONFIG_LOGO_MARK_SIZE = self.dupTuple(self._calculateUiSize(30))
        self.config_window.TOP_BAR_SIDE__CONFIG_TITLE_FONT_SIZE = self._calculateUiSize(22)
        self.config_window.TOP_BAR_SIDE__CONFIG_TITLE_LEFT_PADX = int(self.config_window.TOP_BAR_SIDE__CONFIG_TITLE_FONT_SIZE + self._calculateUiSize(16))
        self.config_window.TOP_BAR_SIDE__TITLE_PADX= self._calculateUiSize(30)

        # Side menu
        self.config_window.SIDE_MENU_TOP_PADY= self._calculateUiSize(54)
        self.config_window.SIDE_MENU_LABELS_IPADX = self._calculateUiSize(20)
        self.config_window.SIDE_MENU_LABELS_IPADY= self._calculateUiSize(8)
        self.config_window.SIDE_MENU_LABELS_FONT_SIZE= self._calculateUiSize(18)


        # Top bar Main
        self.config_window.TOP_BAR_MAIN__TITLE_FONT_SIZE = self._calculateUiSize(22)


        # Setting Box
        self.config_window.SB__MAIN_WIDTH = self._calculateUiSize(720)
        self.config_window.SB__TOP_PADY_IF_WITH_SECTION_TITLE = (self._calculateUiSize(24))
        self.config_window.SB__TOP_PADY_IF_WITHOUT_SECTION_TITLE = (self._calculateUiSize(64))
        self.config_window.SB__BOTTOM_PADY = (self._calculateUiSize(40))
        self.config_window.SB__IPADX = self._calculateUiSize(20)
        self.config_window.SB__IPADY = self._calculateUiSize(12)
        self.config_window.SB__BOTTOM_MARGIN = (0, self._calculateUiSize(60))

        self.config_window.SB__SECTION_TITLE_FONT_SIZE = self._calculateUiSize(20)
        self.config_window.SB__SECTION_TITLE_BOTTOM_PADY = (0, self._calculateUiSize(10))

        self.config_window.SB__LABEL_FONT_SIZE = self._calculateUiSize(16)
        self.config_window.SB__DESC_FONT_SIZE = self._calculateUiSize(14)
        self.config_window.SB__DESC_TOP_PADY = self._calculateUiSize(2)



        self.config_window.SB__SELECTOR_FONT_SIZE = self._calculateUiSize(14)
        self.config_window.SB__RADIO_BUTTON_FONT_SIZE = self.config_window.SB__SELECTOR_FONT_SIZE
        self.config_window.SB__BUTTON_FONT_SIZE = self.config_window.SB__SELECTOR_FONT_SIZE



        self.config_window.SB__OPTION_MENU_FONT_SIZE = self.config_window.SB__SELECTOR_FONT_SIZE
        self.config_window.SB__OPTIONMENU_HEIGHT = self._calculateUiSize(30)
        self.config_window.SB__OPTIONMENU_WIDTH = self._calculateUiSize(200)
        self.config_window.SB__DROPDOWN_MENU_WIDTH = self.config_window.SB__OPTIONMENU_WIDTH
        self.config_window.SB__DROPDOWN_MENU_MAX_BUTTON_HEIGHT = int(self.config_window.SB__OPTION_MENU_FONT_SIZE + self._calculateUiSize(6))
        self.config_window.SB__DROPDOWN_MENU_FRAME_CORNER_RADIUS = self._calculateUiSize(10)
        self.config_window.SB__DROPDOWN_MENU_FRAME_MAX_HEIGHT = self._calculateUiSize(200)


        self.config_window.SB__SWITCH_WIDTH = self._calculateUiSize(50)

        self.config_window.SB__SWITCH_BOX_WIDTH = self._calculateUiSize(40)
        self.config_window.SB__SWITCH_BOX_HEIGHT = self._calculateUiSize(16)

        self.config_window.SB__CHECKBOX_SIZE = self._calculateUiSize(24)
        self.config_window.SB__CHECKBOX_BORDER_WIDTH = self._calculateUiSize(2)
        self.config_window.SB__CHECKBOX_CORNER_RADIUS = self._calculateUiSize(4)

        self.config_window.SB__ENTRY_FONT_SIZE = self.config_window.SB__SELECTOR_FONT_SIZE
        self.config_window.SB__ENTRY_HEIGHT = self._calculateUiSize(30)

        # SB__ENTRY_WIDTH_10 ... SB__ENTRY_WIDTH_200
        for i in range(10, 301, 10):
            setattr(self.config_window, f'SB__ENTRY_WIDTH_{i}', self._calculateUiSize(i))


        self.config_window.SB__PROGRESSBAR_X_SLIDER__ENTRY_WIDTH = self.config_window.SB__ENTRY_WIDTH_50
        self.config_window.SB__PROGRESSBAR_X_SLIDER__ENTRY_HEIGHT = self.config_window.SB__ENTRY_HEIGHT
        self.config_window.SB__PROGRESSBAR_X_SLIDER__SLIDER_HEIGHT = self._calculateUiSize(40)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_LENGTH = self._calculateUiSize(2)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__BAR_WIDTH = self._calculateUiSize(200)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_HEIGHT = self._calculateUiSize(8)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__BAR_RIGHT_PADX = self._calculateUiSize(20)

        self.config_window.SB__PROGRESSBAR_X_SLIDER__BUTTON_RIGHT_PADX = self._calculateUiSize(20)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__BUTTON_IPADXY = self._calculateUiSize(10)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__BUTTON_ICON_SIZE = self._calculateUiSize(20)



    def _calculateUiSize(self, default_size, is_allowed_odd: bool = False):
        size = int(default_size * self.SCALING_FLOAT)
        size += 1 if not is_allowed_odd and size % 2 != 0 else 0
        return size

    def dupTuple(self, value):
        return (value, value)