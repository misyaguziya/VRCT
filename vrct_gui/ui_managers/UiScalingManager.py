from types import SimpleNamespace

from ..ui_utils import calculateUiSize

class UiScalingManager():
    def __init__(self, scaling_percentage):
        scaling_float = int(scaling_percentage.replace("%", "")) / 100
        self.SCALING_FLOAT = max(scaling_float, 0.4)
        self.common = SimpleNamespace()
        self.main = SimpleNamespace()
        self.config_window = SimpleNamespace()
        self.selectable_language_window = SimpleNamespace()
        self.main_window_cover = SimpleNamespace()
        self.error_message_window = SimpleNamespace()
        self.confirmation_modal = SimpleNamespace()
        self.dropdown_menu_window = SimpleNamespace()

        self._calculatedUiSizes()




    def _calculatedUiSizes(self):
        # Common
        # RESPONSIVE_UI_SIZE_INT_10 ... RESPONSIVE_UI_SIZE_INT_300
        self.common.SCROLLBAR_IPADX = (self._calculateUiSize(2), self._calculateUiSize(2))
        self.common.SCROLLBAR_WIDTH = self._calculateUiSize(16)

        for i in range(10, 501, 10):
            setattr(self.main, f"RESPONSIVE_UI_SIZE_INT_{i}", self._calculateUiSize(i))
            setattr(self.config_window, f"RESPONSIVE_UI_SIZE_INT_{i}", self._calculateUiSize(i))


        # Main
        self.main.MAIN_AREA_MIN_WIDTH = self._calculateUiSize(640)
        self.main.SIDEBAR_MIN_WIDTH = self._calculateUiSize(230)

        self.main.TEXTBOX_PADX = self._calculateUiSize(16)
        self.main.TEXTBOX_CORNER_RADIUS = self._calculateUiSize(6)

        self.main.TEXTBOX_TAB_CORNER_RADIUS = self._calculateUiSize(8)
        self.main.TEXTBOX_TAB_FONT_SIZE = self._calculateUiSize(12)
        self.main.TEXTBOX_TAB_PADX = self._calculateUiSize(10)
        self.main.TEXTBOX_TAB_PADY = (self._calculateUiSize(4), self._calculateUiSize(10))

        self.main.TEXTBOX_FIRST_INSERT_SPACING = self._calculateUiSize(16)
        self.main.TEXTBOX_FONT_SIZE__LABEL = self._calculateUiSize(12)
        self.main.TEXTBOX_FONT_SIZE__TIMESTAMP = self._calculateUiSize(12)
        self.main.TEXTBOX_FONT_SIZE__SYSTEM_TEXT_FONT = self._calculateUiSize(12)
        self.main.TEXTBOX_FONT_SIZE__SECONDARY_TEXT_FONT = self._calculateUiSize(12)
        self.main.TEXTBOX_FONT_SIZE__MAIN_TEXT_FONT = self._calculateUiSize(16)

        self.main.TEXTBOX_ENTRY_FONT_SIZE = self._calculateUiSize(16)
        self.main.TEXTBOX_ENTRY_CORNER_RADIUS = self._calculateUiSize(4)
        self.main.TEXTBOX_ENTRY_BORDER_SIZE = self._calculateUiSize(2, is_allowed_odd=True)
        self.main.TEXTBOX_ENTRY_HEIGHT = self._calculateUiSize(40)
        self.main.TEXTBOX_ENTRY_PADX = self.main.TEXTBOX_PADX
        self.main.TEXTBOX_ENTRY_PADY = self._calculateUiSize(10)

        self.main.SEND_MESSAGE_BUTTON_CORNER_RADIUS = self.main.TEXTBOX_ENTRY_CORNER_RADIUS
        self.main.SEND_MESSAGE_BUTTON_IMAGE_SIZE = self._calculateUiSize(20)
        self.main.SEND_MESSAGE_BUTTON_MIN_WIDTH = self._calculateUiSize(40)
        self.main.SEND_MESSAGE_BUTTON_RATE_WIDTH = self._calculateUiSize(6)
        self.main.SEND_MESSAGE_BUTTON_MAX_WIDTH = self._calculateUiSize(100)


        # Sidebar
        # Sidebar Features
        self.main.SF__LOGO_MAX_SIZE = self._calculateUiSize(120)
        self.main.SF__LOGO_PADY = (self._calculateUiSize(10),self._calculateUiSize(6))
        self.main.SF__LOGO_HEIGHT_FOR_ADJUSTMENT = (self._calculateUiSize(6))

        self.main.SF__LABELS_IPADY = self._calculateUiSize(16)
        self.main.SF__COMPACT_MODE_ICON_PADY = self.main.SF__LABELS_IPADY
        self.main.SF__COMPACT_MODE_ICON_PADX = self.main.SF__COMPACT_MODE_ICON_PADY
        self.main.SF__LABEL_LEFT_PAD = self._calculateUiSize(20)
        self.main.SF__LABEL_FONT_SIZE = self._calculateUiSize(16)
        self.main.SF__COMPACT_MODE_IMAGE_SIZE = (self._calculateUiSize(20), self._calculateUiSize(20))

        self.main.SF__SWITCH_BOX_PADX = (self.main.SF__LABEL_LEFT_PAD, self._calculateUiSize(10))
        self.main.SF__SWITCH_BOX_WIDTH = self._calculateUiSize(40)
        self.main.SF__SWITCH_BOX_HEIGHT = self._calculateUiSize(16)

        self.main.SF__SELECTED_MARK_WIDTH = self._calculateUiSize(3, True)


        # Sidebar Quick Language Settings, SQLS
        self.main.SLS__TITLE_FONT_SIZE = self._calculateUiSize(14)
        self.main.SLS__TITLE_PADY = (self._calculateUiSize(10), self._calculateUiSize(4))

        self.main.SLS__PRESET_TAB_NUMBER_FONT_SIZE = self._calculateUiSize(16)
        self.main.SLS__PRESET_TAB_NUMBER_HEIGHT = self._calculateUiSize(30)
        self.main.SLS__PRESET_TAB_NUMBER_CORNER_RADIUS = self._calculateUiSize(6)
        self.main.SLS__PRESET_TAB_NUMBER_ADJUSTED_HEIGHT = self._calculateUiSize(36)

        self.main.SLS__BOX_TOP_PADY = self._calculateUiSize(12)

        self.main.SLS__BOX_TRANSCRIPTION_STATUS_IMAGE_SIZE = self.dupTuple(self._calculateUiSize(14))

        self.main.SLS__BOX_SECTION_TITLE_FONT_SIZE = self._calculateUiSize(16)
        self.main.SLS__BOX_SECTION_TITLE_BOTTOM_PADY = self._calculateUiSize(10)
        self.main.SLS__BOX_IPADX = self._calculateUiSize(10)
        self.main.SLS__BOX_IPADY = (self._calculateUiSize(8),self._calculateUiSize(14))
        self.main.SLS__BOX_OPTION_MENU_FONT_SIZE = self._calculateUiSize(14)
        self.main.SLS__BOX_OPTION_MENU_IPADY = self._calculateUiSize(2)
        self.main.SLS__BOX_OPTION_MENU_ARROW_IMAGE_SIZE = self.dupTuple(self._calculateUiSize(20))
        # self.main.SLS__BOX_OPTION_MENU_WIDTH = self._calculateUiSize(200)
        self.main.SLS__BOX_ARROWS_PADY = self._calculateUiSize(6)
        self.main.SLS__BOX_ARROWS_SWAP_BUTTON_CORNER_RADIUS = self._calculateUiSize(6)
        self.main.SLS__BOX_ARROWS_SWAP_BUTTON_PADX = self._calculateUiSize(20)
        self.main.SLS__BOX_ARROWS_SWAP_BUTTON_IPADX = self._calculateUiSize(8)
        self.main.SLS__BOX_ARROWS_SWAP_BUTTON_IPADY = self._calculateUiSize(4)
        self.main.SLS__BOX_ARROWS_IMAGE_SIZE = self.dupTuple(self._calculateUiSize(16))
        self.main.SLS__BOX_ARROWS_DESC_FONT_SIZE = self._calculateUiSize(12)
        self.main.SLS__BOX_ARROWS_DESC_PADX = self._calculateUiSize(6)

        self.main.SIDEBAR_CONFIG_BUTTON_CORNER_RADIUS = self._calculateUiSize(6)
        self.main.SIDEBAR_CONFIG_BUTTON_IMAGE_SIZE = self.main.SF__COMPACT_MODE_IMAGE_SIZE
        self.main.SIDEBAR_CONFIG_BUTTON_PADX = self._calculateUiSize(10)
        self.main.SIDEBAR_CONFIG_BUTTON_PADY = self._calculateUiSize(10)
        self.main.SIDEBAR_CONFIG_BUTTON_IPADY = self._calculateUiSize(8)

        self.main.TOP_BAR_BUTTON_PADY = (self._calculateUiSize(6),0)

        self.main.UPDATE_AVAILABLE_BUTTON_CORNER_RADIUS = self._calculateUiSize(6)
        self.main.UPDATE_AVAILABLE_BUTTON_SIZE = (self._calculateUiSize(18), self._calculateUiSize(18))
        self.main.UPDATE_AVAILABLE_BUTTON_FONT_SIZE = self._calculateUiSize(12)
        self.main.UPDATE_AVAILABLE_BUTTON_PADX = (0, self._calculateUiSize(4))
        self.main.UPDATE_AVAILABLE_BUTTON_IPADX = self._calculateUiSize(6)
        self.main.UPDATE_AVAILABLE_ICON_PADX = (self._calculateUiSize(6), self._calculateUiSize(4))
        self.main.UPDATE_AVAILABLE_PADX_BETWEEN_LABEL_AND_ICON = self._calculateUiSize(4)



        self.main.HELP_AND_INFO_BUTTON_CORNER_RADIUS = self._calculateUiSize(6)
        self.main.HELP_AND_INFO_BUTTON_SIZE = self._calculateUiSize(24)
        self.main.HELP_AND_INFO_BUTTON_PADX = (0, self._calculateUiSize(6))
        self.main.HELP_AND_INFO_BUTTON_IPADXY = self._calculateUiSize(6)

        self.main.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_X = int(self.main.TEXTBOX_PADX/2+self.main.TEXTBOX_CORNER_RADIUS*2)
        self.main.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_Y = self._calculateUiSize(26)


        self.main.SLS__SELECTABLE_TRANSLATION_IPADX = self.dupTuple(self._calculateUiSize(10))
        self.main.SLS__SELECTABLE_TRANSLATION_IPADY = self._calculateUiSize(6)
        self.main.SLS__SELECTABLE_TRANSLATION_FONT_SIZE = self._calculateUiSize(12)
        self.main.SLS__SELECTABLE_TRANSLATION_IMAGE_SIZE = self.dupTuple(self._calculateUiSize(10))
        self.main.SLS__SELECTABLE_TRANSLATION_PADY = self._calculateUiSize(4)
        self.main.SLS__SELECTABLE_TRANSLATION_MIN_PADX = self._calculateUiSize(8)


        self.main.SLS__DROPDOWN_MENU_WINDOW_ADDITIONAL_Y_POS = self._calculateUiSize(4)
        self.main.SLS__DROPDOWN_MENU_WINDOW_BORDER_WIDTH = self._calculateUiSize(0, is_allowed_odd=True)
        self.main.SLS__DROPDOWN_MENU_SCROLLBAR_IPADX = self.common.SCROLLBAR_IPADX
        self.main.SLS__DROPDOWN_MENU_SCROLLBAR_WIDTH = self.common.SCROLLBAR_WIDTH
        self.main.SLS__DROPDOWN_MENU_VALUE_IPADX = (self._calculateUiSize(8), 0)
        self.main.SLS__DROPDOWN_MENU_VALUE_IPADY = self.dupTuple(self._calculateUiSize(8))
        self.main.SLS__DROPDOWN_MENU_VALUE_PADY = 0
        self.main.SLS__DROPDOWN_MENU_VALUE_FONT_SIZE = self._calculateUiSize(14)
        self.main.SLS__DROPDOWN_MENU_VALUE_DEFAULT_MIN_WIDTH = self._calculateUiSize(200)


        # Selectable Language Window
        self.selectable_language_window.TOP_BAR_MIN_HEIGHT = self._calculateUiSize(50)
        self.selectable_language_window.SCROLLBAR_IPADX = self.common.SCROLLBAR_IPADX
        self.selectable_language_window.SCROLLBAR_WIDTH = self.common.SCROLLBAR_WIDTH

        self.selectable_language_window.GO_BACK_BUTTON_LABEL_FONT_SIZE = self._calculateUiSize(14)
        self.selectable_language_window.GO_BACK_BUTTON_IPADX = self._calculateUiSize(10)
        self.selectable_language_window.GO_BACK_BUTTON_IPADY = self._calculateUiSize(8)
        self.selectable_language_window.TITLE_FONT_SIZE = self._calculateUiSize(18)

        self.selectable_language_window.VALUES_TEXT_FONT_SIZE = self._calculateUiSize(14)
        self.selectable_language_window.VALUES_TEXT_IPADX = (self._calculateUiSize(8), 0)
        self.selectable_language_window.VALUES_TEXT_IPADY = self._calculateUiSize(8)


        self.main_window_cover.TEXT_FONT_SIZE = self._calculateUiSize(20)


        self.confirmation_modal.FAKE_BORDER_SIZE = self._calculateUiSize(1, is_allowed_odd=True)
        self.confirmation_modal.CONTENTS_WRAPPER = self._calculateUiSize(20)
        self.confirmation_modal.MARGIN_BETWEEN_MESSAGE_AND_BUTTONS = self._calculateUiSize(40)
        self.confirmation_modal.MESSAGE_FONT_SIZE = self._calculateUiSize(20)
        self.confirmation_modal.CONFIRMATION_BUTTONS_TEXT_FONT_SIZE = self._calculateUiSize(18)
        self.confirmation_modal.BUTTONS_BETWEEN_PADDING = self._calculateUiSize(100)
        self.confirmation_modal.BUTTONS_CORNER_RADIUS = self._calculateUiSize(6)
        self.confirmation_modal.BUTTONS_IPADX = self._calculateUiSize(10)
        self.confirmation_modal.BUTTONS_IPADY = self._calculateUiSize(6)

        # Dropdown Menu Window
        self.dropdown_menu_window.MARGIN_WIDTH = self._calculateUiSize(16)

        # Config Window
        self.config_window.DEFAULT_WIDTH = self._calculateUiSize(1080)
        self.config_window.DEFAULT_HEIGHT = self._calculateUiSize(680)

        # Top bar common
        self.config_window.TOP_BAR__MIN_HEIGHT = self._calculateUiSize(40)
        self.config_window.TOP_BAR__IPADY = self._calculateUiSize(12)

        # Top bar Side
        self.config_window.TOP_BAR_SIDE_AREA_MIN_WIDTH = self._calculateUiSize(220)
        self.config_window.TOP_BAR_SIDE__CONFIG_LOGO_MARK_SIZE = self.dupTuple(self._calculateUiSize(28))
        self.config_window.TOP_BAR_SIDE__CONFIG_TITLE_FONT_SIZE = self._calculateUiSize(22)
        self.config_window.TOP_BAR_SIDE__CONFIG_TITLE_LEFT_PADX = int(self.config_window.TOP_BAR_SIDE__CONFIG_TITLE_FONT_SIZE + self._calculateUiSize(16))
        self.config_window.TOP_BAR_SIDE__TITLE_PADX= self._calculateUiSize(30)

        # Restart Button
        self.config_window.RESTART_BUTTON_LABEL_FONT_SIZE = self._calculateUiSize(12)
        self.config_window.RESTART_BUTTON_PADX = (0, self._calculateUiSize(20))
        self.config_window.RESTART_BUTTON_CORNER_RADIUS = self._calculateUiSize(20)
        self.config_window.RESTART_BUTTON_IPADX = self._calculateUiSize(20)
        self.config_window.RESTART_BUTTON_IPADY = self._calculateUiSize(10)

        # Compact Mode
        self.config_window.COMPACT_MODE_PADX = (0, self._calculateUiSize(20))
        self.config_window.COMPACT_MODE_LABEL_FONT_SIZE = self._calculateUiSize(12)
        self.config_window.COMPACT_MODE_LABEL_PADX = (0, self._calculateUiSize(10))
        self.config_window.COMPACT_MODE_SWITCH_WIDTH = self._calculateUiSize(40)
        self.config_window.COMPACT_MODE_SWITCH_HEIGHT = self._calculateUiSize(16)


        # Side menu
        self.config_window.SIDE_MENU_TOP_PADY = self._calculateUiSize(54)
        self.config_window.SIDE_MENU_LABELS_IPADX = self._calculateUiSize(20)
        self.config_window.SIDE_MENU_LABELS_IPADY = self._calculateUiSize(8)
        self.config_window.SIDE_MENU_LABELS_FONT_SIZE = self._calculateUiSize(18)

        self.config_window.NOW_VERSION_FONT_SIZE = self._calculateUiSize(12)

        # Top bar Main
        self.config_window.TOP_BAR_MAIN__TITLE_FONT_SIZE = self._calculateUiSize(22)
        self.config_window.SCROLLBAR_IPADX = self.common.SCROLLBAR_IPADX
        self.config_window.SCROLLBAR_WIDTH = self.common.SCROLLBAR_WIDTH


        # Setting Box
        self.config_window.MAIN_AREA_MIN_WIDTH = self._calculateUiSize(720)
        self.config_window.SB__TOP_PADY = (self._calculateUiSize(60))
        self.config_window.SB__IPADX = self._calculateUiSize(20)
        self.config_window.SB__IPADY = self._calculateUiSize(12)
        self.config_window.SB__BOTTOM_MARGIN = (0, self._calculateUiSize(60))
        self.config_window.SB__FAKE_BOTTOM_BORDER_SIZE = (0, self._calculateUiSize(1, is_allowed_odd=True))

        self.config_window.SB__SECTION_TITLE_FONT_SIZE = self._calculateUiSize(20)
        self.config_window.SB__SECTION_TITLE_BOTTOM_PADY = (0, self._calculateUiSize(10))

        self.config_window.SB__LABEL_FONT_SIZE = self._calculateUiSize(16)
        self.config_window.SB__DESC_FONT_SIZE = self._calculateUiSize(14)
        self.config_window.SB__DESC_TOP_PADY = self._calculateUiSize(2)


        self.config_window.BUTTONS_CORNER_RADIUS = self._calculateUiSize(6)
        # self.config_window.BUTTONS_IPADX = self._calculateUiSize(10)
        # self.config_window.BUTTONS_IPADY = self._calculateUiSize(6)

        self.config_window.SB__ERROR_MESSAGE_IPADX = (self._calculateUiSize(10), self._calculateUiSize(10))
        self.config_window.SB__ERROR_MESSAGE_IPADY = (self._calculateUiSize(6), self._calculateUiSize(6))
        self.config_window.SB__ERROR_MESSAGE_FONT_SIZE = self._calculateUiSize(14)


        self.config_window.SB__SELECTOR_FONT_SIZE = self._calculateUiSize(14)
        self.config_window.SB__RADIO_BUTTON_FONT_SIZE = self.config_window.SB__SELECTOR_FONT_SIZE
        self.config_window.SB__BUTTON_FONT_SIZE = self.config_window.SB__SELECTOR_FONT_SIZE



        self.config_window.SB__OPTION_MENU_FONT_SIZE = self.config_window.SB__SELECTOR_FONT_SIZE
        self.config_window.SB__OPTIONMENU_MIN_HEIGHT = self._calculateUiSize(30)
        self.config_window.SB__OPTIONMENU_MIN_WIDTH = self._calculateUiSize(200)
        self.config_window.SB__OPTIONMENU_IPADX = (self._calculateUiSize(8), self._calculateUiSize(8))
        self.config_window.SB__OPTIONMENU_IPADY = self._calculateUiSize(2)
        self.config_window.SB__OPTIONMENU_IPADX_BETWEEN_IMG = self._calculateUiSize(8)
        self.config_window.SB__OPTIONMENU_IMG_SIZE = (self._calculateUiSize(14), self._calculateUiSize(14))

        self.config_window.SB__DROPDOWN_MENU_WINDOW_ADDITIONAL_Y_POS = self._calculateUiSize(4)
        self.config_window.SB__DROPDOWN_MENU_WINDOW_BORDER_WIDTH = self._calculateUiSize(1, is_allowed_odd=True)
        self.config_window.SB__DROPDOWN_MENU_SCROLLBAR_IPADX = self.common.SCROLLBAR_IPADX
        self.config_window.SB__DROPDOWN_MENU_SCROLLBAR_WIDTH = self.common.SCROLLBAR_WIDTH
        self.config_window.SB__DROPDOWN_MENU_VALUE_IPADX = (self._calculateUiSize(8), 0)
        self.config_window.SB__DROPDOWN_MENU_VALUE_IPADY = (self._calculateUiSize(6), self._calculateUiSize(6))
        self.config_window.SB__DROPDOWN_MENU_VALUE_PADY = (0, self._calculateUiSize(1, is_allowed_odd=True))
        self.config_window.SB__DROPDOWN_MENU_VALUE_FONT_SIZE = self._calculateUiSize(14)
        self.config_window.SB__DROPDOWN_MENU_VALUE_DEFAULT_MIN_WIDTH = self._calculateUiSize(200)


        self.config_window.SB__SWITCH_WIDTH = self._calculateUiSize(50)

        self.config_window.SB__SWITCH_BOX_WIDTH = self._calculateUiSize(40)
        self.config_window.SB__SWITCH_BOX_HEIGHT = self._calculateUiSize(16)

        self.config_window.SB__CHECKBOX_SIZE = self._calculateUiSize(24)
        self.config_window.SB__CHECKBOX_BORDER_WIDTH = self._calculateUiSize(2)
        self.config_window.SB__CHECKBOX_CORNER_RADIUS = self._calculateUiSize(4)

        self.config_window.SB__ENTRY_FONT_SIZE = self.config_window.SB__SELECTOR_FONT_SIZE
        self.config_window.SB__ENTRY_HEIGHT = self._calculateUiSize(30)

        self.config_window.SB__SLIDER_WIDTH = self._calculateUiSize(200)
        self.config_window.SB__SLIDER_HEIGHT = self._calculateUiSize(16)
        self.config_window.SB__SLIDER_TOOLTIP_FONT_SIZE = self._calculateUiSize(16)

        self.config_window.SB__PROGRESSBAR_X_SLIDER__ENTRY_WIDTH = self.config_window.RESPONSIVE_UI_SIZE_INT_50
        self.config_window.SB__PROGRESSBAR_X_SLIDER__ENTRY_HEIGHT = self.config_window.SB__ENTRY_HEIGHT
        self.config_window.SB__PROGRESSBAR_X_SLIDER__SLIDER_HEIGHT = self._calculateUiSize(40)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_HEIGHT = self._calculateUiSize(8)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_LENGTH = self._calculateUiSize(2)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__BAR_PADX = (self._calculateUiSize(30), self._calculateUiSize(30))

        self.config_window.SB__PROGRESSBAR_X_SLIDER__BUTTON_IPADXY = self._calculateUiSize(10)
        self.config_window.SB__PROGRESSBAR_X_SLIDER__BUTTON_ICON_SIZE = self._calculateUiSize(20)

        self.config_window.SB__ARROW_SWITCH_DESC_FONT_SIZE = self._calculateUiSize(16)
        self.config_window.SB__ARROW_SWITCH_LEFT_PADX = (self._calculateUiSize(20), 0)

        self.config_window.ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_IPADX = self._calculateUiSize(16)
        self.config_window.ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_IPADY = self._calculateUiSize(6)

        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_CORNER_RADIUS = self._calculateUiSize(2)
        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_LEFT_PADX = (0, self._calculateUiSize(4))
        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_BOTTOM_PADY = (0, self._calculateUiSize(4))

        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_FONT_SIZE = self._calculateUiSize(14)
        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_IPADX = (self._calculateUiSize(8), 0)
        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_IPADY = self._calculateUiSize(6)
        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_IMG_SIZE = self._calculateUiSize(14)
        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_CORNER_RADIUS = self._calculateUiSize(4)
        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_IPADXY = self._calculateUiSize(6)
        self.config_window.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_PADX = (self._calculateUiSize(6), self._calculateUiSize(8))

        self.config_window.ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_LEFT_PADX = (self._calculateUiSize(20), 0)
        self.config_window.ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_FONT_SIZE = self._calculateUiSize(14)


        self.config_window.SB__MESSAGE_FORMAT__EXAMPLE_CORNER_RADIUS = self._calculateUiSize(16)
        self.config_window.SB__MESSAGE_FORMAT__EXAMPLE_IPADXY = self._calculateUiSize(10)
        self.config_window.SB__MESSAGE_FORMAT__EXAMPLE_WRAP_LENGTH = self._calculateUiSize(300)

        self.config_window.SB__MESSAGE_FORMAT__ENTRY_HEIGHT = self.config_window.SB__ENTRY_HEIGHT
        self.config_window.SB__MESSAGE_FORMAT__REQUIRED_TEXT_PADX = self._calculateUiSize(10)
        self.config_window.SB__MESSAGE_FORMAT__REQUIRED_TEXT_FONT_SIZE = self._calculateUiSize(16)

        self.config_window.SB__MESSAGE_FORMAT__SWAP_BUTTON_ARROWS_IMG_SIZE = self.dupTuple(self._calculateUiSize(20))
        self.config_window.SB__MESSAGE_FORMAT__SWAP_BUTTON_IPADX = self._calculateUiSize(16)
        self.config_window.SB__MESSAGE_FORMAT__SWAP_BUTTON_IPADY = self._calculateUiSize(6)
        self.config_window.SB__MESSAGE_FORMAT__SWAP_BUTTON_FONT_SIZE = self._calculateUiSize(14)
        self.config_window.SB__MESSAGE_FORMAT__SWAP_TEXT_PADX = self._calculateUiSize(10)

        self.config_window.SB__MESSAGE_FORMAT__ENTRIES_BOTTOM_PADY = (0, self._calculateUiSize(14))


        self.config_window.SB__BUTTON_IPADXY = self._calculateUiSize(16)
        self.config_window.SB__BUTTON_ICON_SIZE = self._calculateUiSize(24)
        self.config_window.SB__BUTTON_CORNER_RADIUS = self.config_window.BUTTONS_CORNER_RADIUS

        self.config_window.SB__OPEN_CONFIG_FILE_BUTTON_IPADXY = self._calculateUiSize(10)


    def _calculateUiSize(self, default_size, is_allowed_odd:bool=False, is_zero_allowed:bool=False):
        size = calculateUiSize(default_size, self.SCALING_FLOAT, is_allowed_odd, is_zero_allowed)
        return size

    @staticmethod
    def dupTuple(value):
        return (value, value)