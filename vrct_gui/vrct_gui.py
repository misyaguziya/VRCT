from types import SimpleNamespace

from customtkinter import CTk, get_appearance_mode

# from window_help_and_info import ToplevelWindowInformation

from .ui_managers import ColorThemeManager, ImageFilenameManager, UiScalingManager
from ._changeMainWindowWidgetsStatus import _changeMainWindowWidgetsStatus
from ._printToTextbox import _printToTextbox

from .main_window import createMainWindowWidgets
from .config_window import ConfigWindow

from config import config


class VRCT_GUI(CTk):
    def __init__(self):
        super().__init__()
        self.settings = SimpleNamespace()
        theme = get_appearance_mode() if config.APPEARANCE_THEME == "System" else config.APPEARANCE_THEME
        all_ctm = ColorThemeManager(theme)
        all_uism = UiScalingManager(config.UI_SCALING)
        image_filename = ImageFilenameManager(theme)

        common_args = {
            "image_filename": image_filename,
            "FONT_FAMILY": config.FONT_FAMILY,
        }

        self.settings.main = SimpleNamespace(
            ctm=all_ctm.main,
            uism=all_uism.main,
            IS_SIDEBAR_COMPACT_MODE=False,
            COMPACT_MODE_ICON_SIZE=0,
            **common_args
        )

        self.settings.config_window = SimpleNamespace(
            ctm=all_ctm.config_window,
            uism=all_uism.config_window,
            IS_CONFIG_WINDOW_COMPACT_MODE=False,
            **common_args
        )


        self.YOUR_LANGUAGE = "Japanese\n(Japan)"
        self.TARGET_LANGUAGE = "English\n(United States)"

        self.CALLBACK_SELECTED_TAB_NO_1 = None
        self.CALLBACK_SELECTED_TAB_NO_2 = None
        self.CALLBACK_SELECTED_TAB_NO_3 = None

        self.config_window = ConfigWindow(vrct_gui=self, settings=self.settings.config_window)
        # self.information_window = ToplevelWindowInformation(self)

    def createGUI(self):
        createMainWindowWidgets(vrct_gui=self, settings=self.settings.main)

    def startMainLoop(self):
        self.mainloop()


    def quitVRCT(self):
        self.quit()
        self.destroy()


    def openConfigWindow(self, e):
        self.config_window.deiconify()
        self.config_window.focus_set()
        self.config_window.focus()
        self.config_window.grab_set()

    def closeConfigWindow(self):
        self.config_window.withdraw()
        self.config_window.grab_release()



    def openHelpAndInfoWindow(self, e):
        self.information_window.deiconify()
        self.information_window.focus_set()
        self.information_window.focus()

    def changeMainWindowWidgetsStatus(self, status, target_names):
        _changeMainWindowWidgetsStatus(
            vrct_gui=self,
            settings=self.settings.main,
            status=status,
            target_names=target_names,
        )

    def printToTextbox(self, target_textbox, original_message, translated_message, tags=None):
        _printToTextbox(
            settings=self.settings.main,
            target_textbox=target_textbox,
            original_message=original_message,
            translated_message=translated_message,
            tags=tags,
        )


vrct_gui = VRCT_GUI()