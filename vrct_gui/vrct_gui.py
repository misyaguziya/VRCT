from types import SimpleNamespace

from customtkinter import CTk

# from window_help_and_info import ToplevelWindowInformation

# from .ui_managers import ColorThemeManager, ImageFilenameManager, UiScalingManager
from ._changeMainWindowWidgetsStatus import _changeMainWindowWidgetsStatus
from ._printToTextbox import _printToTextbox

from .main_window import createMainWindowWidgets
from .config_window import ConfigWindow
from .ui_utils import _setDefaultActiveTab


class VRCT_GUI(CTk):
    def __init__(self):
        super().__init__()
        self.settings = SimpleNamespace()
        self.YOUR_LANGUAGE = "Japanese\n(Japan)"
        self.TARGET_LANGUAGE = "English\n(United States)"

        self.CALLBACK_TOGGLE_TRANSLATION = None
        self.CALLBACK_TOGGLE_TRANSCRIPTION_SEND = None
        self.CALLBACK_TOGGLE_TRANSCRIPTION_RECEIVE = None
        self.CALLBACK_TOGGLE_FOREGROUND = None
        self.CALLBACK_SELECTED_TAB_NO_1 = None
        self.CALLBACK_SELECTED_TAB_NO_2 = None
        self.CALLBACK_SELECTED_TAB_NO_3 = None


    def createGUI(self, settings):
        self.settings = settings

        createMainWindowWidgets(vrct_gui=self, settings=self.settings.main)
        self.config_window = ConfigWindow(vrct_gui=self, settings=self.settings.config_window)
        # self.information_window = ToplevelWindowInformation(self)

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

    def setDefaultActiveLanguagePresetTab(self, tab_no:str):
        self.current_active_preset_tab = getattr(self, f"sqls__presets_button_{tab_no}")
        _setDefaultActiveTab(
            active_tab_widget=self.current_active_preset_tab,
            active_bg_color=self.settings.main.ctm.SQLS__PRESETS_TAB_BG_ACTIVE_COLOR,
            active_text_color=self.settings.main.ctm.SQLS__PRESETS_TAB_ACTIVE_TEXT_COLOR
        )



vrct_gui = VRCT_GUI()