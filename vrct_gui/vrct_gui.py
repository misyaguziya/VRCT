from types import SimpleNamespace

from customtkinter import CTk, CTkImage

# from window_help_and_info import ToplevelWindowInformation

from  ._CreateSelectableLanguagesWindow import _CreateSelectableLanguagesWindow

from ._changeMainWindowWidgetsStatus import _changeMainWindowWidgetsStatus
from ._changeConfigWindowWidgetsStatus import _changeConfigWindowWidgetsStatus
from ._printToTextbox import _printToTextbox

from .main_window import createMainWindowWidgets
from .config_window import ConfigWindow
from .ui_utils import _setDefaultActiveTab

from .main_window.widgets import createSidebar, createMinimizeSidebarButton


class VRCT_GUI(CTk):
    def __init__(self):
        super().__init__()

    def createGUI(self, settings, view_variable):
        self.settings = settings
        self._view_variable = view_variable

        createMainWindowWidgets(
            vrct_gui=self,
            settings=self.settings.main,
            view_variable=self._view_variable
        )

        self.config_window = ConfigWindow(
            vrct_gui=self,
            settings=self.settings.config_window,
            view_variable=self._view_variable
        )
        # self.information_window = ToplevelWindowInformation(self)

        self.selectable_languages_window = _CreateSelectableLanguagesWindow(
            vrct_gui=self,
            settings=self.settings.selectable_language_window,
            view_variable=self._view_variable
        )

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




    def openSelectableLanguagesWindow(self, selectable_language_window_type):
        if selectable_language_window_type == "your_language":
            if self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW is False:
                self.sls__arrow_img_your_language.configure(image=CTkImage((self.settings.main.image_file.ARROW_LEFT),size=(20,20)))
                self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW = True
                self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW = False
            else:
                self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW = False
                return

        elif selectable_language_window_type == "target_language":
            if self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW is False:
                self.sls__arrow_img_target_language.configure(image=CTkImage((self.settings.main.image_file.ARROW_LEFT),size=(20,20)))
                self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW = True
                self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW = False
            else:
                self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW = False
                return


        self.selectable_languages_window.createContainer(selectable_language_window_type)
        self.selectable_languages_window.deiconify()
        self.selectable_languages_window.focus_set()
        self.selectable_languages_window.attributes("-topmost", True)


    def closeSelectableLanguagesWindow(self):
        self.sls__arrow_img_your_language.configure(image=CTkImage((self.settings.main.image_file.ARROW_LEFT).rotate(180),size=(20,20)))
        self.sls__arrow_img_target_language.configure(image=CTkImage((self.settings.main.image_file.ARROW_LEFT).rotate(180),size=(20,20)))
        self.selectable_languages_window.withdraw()
        self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW = False
        self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW = False




    def openHelpAndInfoWindow(self, e):
        self.information_window.deiconify()
        self.information_window.focus_set()
        self.information_window.focus()

    def changeMainWindowWidgetsStatus(self, status, target_names):
        _changeMainWindowWidgetsStatus(
            vrct_gui=self,
            settings=self.settings.main,
            view_variable=self._view_variable,
            status=status,
            target_names=target_names,
        )

    def changeConfigWindowWidgetsStatus(self, status, target_names):
        _changeConfigWindowWidgetsStatus(
            config_window=self.config_window,
            settings=self.settings.config_window,
            view_variable=self._view_variable,
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
        self.current_active_preset_tab = getattr(self, f"sls__presets_button_{tab_no}")
        _setDefaultActiveTab(
            active_tab_widget=self.current_active_preset_tab,
            active_bg_color=self.settings.main.ctm.SLS__PRESETS_TAB_BG_ACTIVE_COLOR,
            active_text_color=self.settings.main.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR
        )

    def recreateMainWindowSidebar(self):
        self.minimize_sidebar_button_container.destroy()
        createMinimizeSidebarButton(self.settings.main, self, view_variable=self._view_variable)

        if self._view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE:
            self.sidebar_bg_container.grid_remove()
            self.sidebar_compact_mode_bg_container.grid()
        else:
            self.sidebar_compact_mode_bg_container.grid_remove()
            self.sidebar_bg_container.grid()


vrct_gui = VRCT_GUI()