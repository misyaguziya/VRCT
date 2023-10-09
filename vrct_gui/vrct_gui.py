from customtkinter import CTk, CTkImage

from  ._CreateSelectableLanguagesWindow import _CreateSelectableLanguagesWindow

from ._CreateModalWindow import _CreateModalWindow
from ._CreateErrorWindow import _CreateErrorWindow
from ._CreateDropdownMenuWindow import _CreateDropdownMenuWindow
from ._changeMainWindowWidgetsStatus import _changeMainWindowWidgetsStatus
from ._changeConfigWindowWidgetsStatus import _changeConfigWindowWidgetsStatus
from ._printToTextbox import _printToTextbox

from .main_window import createMainWindowWidgets
from .config_window import ConfigWindow
from .ui_utils import _setDefaultActiveTab

from utils import callFunctionIfCallable

class VRCT_GUI(CTk):
    def __init__(self):
        super().__init__()
        self.adjusted_event=None
        self.BIND_CONFIGURE_ADJUSTED_GEOMETRY_FUNC_ID=None
        self.BIND_FOCUS_IN_MODAL_WINDOW_LIFT_CONFIG_WINDOW_FUNC_ID=None


    def createGUI(self, settings, view_variable):
        self.settings = settings
        self._view_variable = view_variable

        createMainWindowWidgets(
            vrct_gui=self,
            settings=self.settings.main,
            view_variable=self._view_variable
        )

        self.dropdown_menu_window = _CreateDropdownMenuWindow(
            settings=self.settings.config_window,
            view_variable=self._view_variable,

            window_bg_color=self.settings.config_window.ctm.SB__DROPDOWN_MENU_WINDOW_BG_COLOR,
            window_border_color=self.settings.config_window.ctm.SB__DROPDOWN_MENU_WINDOW_BORDER_COLOR,
            values_bg_color=self.settings.config_window.ctm.SB__DROPDOWN_MENU_BG_COLOR,
            values_hovered_bg_color=self.settings.config_window.ctm.SB__DROPDOWN_MENU_HOVERED_BG_COLOR,
            values_clicked_bg_color=self.settings.config_window.ctm.SB__DROPDOWN_MENU_CLICKED_BG_COLOR,
            values_text_color=self.settings.config_window.ctm.BASIC_TEXT_COLOR,
        )

        self.config_window = ConfigWindow(
            vrct_gui=self,
            settings=self.settings.config_window,
            view_variable=self._view_variable
        )

        self.selectable_languages_window = _CreateSelectableLanguagesWindow(
            vrct_gui=self,
            settings=self.settings.selectable_language_window,
            view_variable=self._view_variable
        )

        self.modal_window = _CreateModalWindow(
            attach_window=self,
            settings=self.settings.modal_window,
            view_variable=self._view_variable
        )

        self.error_message_window = _CreateErrorWindow(
            settings=self.settings.modal_window,
            view_variable=self._view_variable,
            wrapper_widget=self.config_window.main_bg_container,
        )



    def startMainLoop(self):
        self.mainloop()


    def quitVRCT(self):
        self.quit()
        self.destroy()


    def openConfigWindow(self, _e):
        callFunctionIfCallable(self._view_variable.CALLBACK_OPEN_CONFIG_WINDOW)

        self.adjustToMainWindowGeometry()
        self.modal_window.deiconify()
        self.BIND_CONFIGURE_ADJUSTED_GEOMETRY_FUNC_ID = self.bind("<Configure>", self.adjustToMainWindowGeometry, "+")
        self.BIND_FOCUS_IN_MODAL_WINDOW_LIFT_CONFIG_WINDOW_FUNC_ID = self.modal_window.bind("<FocusIn>", lambda _e: self.config_window.lift(), "+")

        self.config_window.deiconify()
        self.config_window.focus_set()

    def closeConfigWindow(self):
        callFunctionIfCallable(self._view_variable.CALLBACK_CLOSE_CONFIG_WINDOW)

        self.config_window.withdraw()

        self.modal_window.withdraw()
        self.unbind("<Configure>", self.BIND_CONFIGURE_ADJUSTED_GEOMETRY_FUNC_ID)
        self.modal_window.unbind("<FocusIn>", self.BIND_FOCUS_IN_MODAL_WINDOW_LIFT_CONFIG_WINDOW_FUNC_ID)
        self.adjusted_event=None



    def openSelectableLanguagesWindow(self, selectable_language_window_type):
        # print("___________________________________open____________________________________________________")
        # print("your", self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW)
        # print("target", self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW)
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


        # print("______________________________________close_________________________________________________")
        # print("your", self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW)
        # print("target", self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW)
        if self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW is not False or self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW is not False:
            def callback():
                self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW = False
                self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW = False
            self.after(500,callback)



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

    def printToTextbox(self, target_type, original_message=None, translated_message=None):
        _printToTextbox(
            vrct_gui=self,
            settings=self.settings.main,
            target_type=target_type,
            original_message=original_message,
            translated_message=translated_message,
            tags=target_type,
        )

    def setDefaultActiveLanguagePresetTab(self, tab_no:str):
        self.current_active_preset_tab = getattr(self, f"sls__presets_button_{tab_no}")
        _setDefaultActiveTab(
            active_tab_widget=self.current_active_preset_tab,
            active_bg_color=self.settings.main.ctm.SLS__PRESETS_TAB_BG_ACTIVE_COLOR,
            active_text_color=self.settings.main.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR
        )

    def enableMainWindowSidebarCompactMode(self):
        self.sidebar_bg_container.grid_remove()
        self.sidebar_compact_mode_bg_container.grid()
        self.minimize_sidebar_button_container__for_closing.grid_remove()
        self.minimize_sidebar_button_container__for_opening.grid()

    def disableMainWindowSidebarCompactMode(self):
        self.sidebar_compact_mode_bg_container.grid_remove()
        self.sidebar_bg_container.grid()
        self.minimize_sidebar_button_container__for_opening.grid_remove()
        self.minimize_sidebar_button_container__for_closing.grid()


    def adjustToMainWindowGeometry(self, e=None):
        self.update_idletasks()
        x_pos = self.winfo_rootx()
        y_pos = self.winfo_rooty()
        width_new = self.winfo_width()
        height_new = self.winfo_height()
        self.modal_window.geometry("{}x{}+{}+{}".format(width_new, height_new, x_pos, y_pos))

        self.modal_window.lift()
        if self.adjusted_event == str(e):
            self.after(150, lambda: self.config_window.lift())
        elif self.adjusted_event is None:
            self.after(150, lambda: self.config_window.lift())
        else:
            pass

        self.config_window.focus_set()

        if e is not None:
            self.adjusted_event=str(e)


    def showErrorMessage(self, target_widget):
        self.error_message_window.show(target_widget=target_widget)

    def _clearErrorMessage(self):
        try:
            self.error_message_window._withdraw()
        except:
            pass


vrct_gui = VRCT_GUI()