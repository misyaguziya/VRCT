from customtkinter import CTk, CTkImage

from  ._CreateSelectableLanguagesWindow import _CreateSelectableLanguagesWindow

from ._CreateWindowCover import _CreateWindowCover
from ._CreateErrorWindow import _CreateErrorWindow
from ._CreateDropdownMenuWindow import _CreateDropdownMenuWindow
from ._changeMainWindowWidgetsStatus import _changeMainWindowWidgetsStatus
from ._changeConfigWindowWidgetsStatus import _changeConfigWindowWidgetsStatus
from ._CreateConfirmationModal import _CreateConfirmationModal
from ._PrintToTextbox import _PrintToTextbox

from .main_window import createMainWindowWidgets
from .config_window import ConfigWindow
from .ui_utils import setDefaultActiveTab, setGeometryToCenterOfScreen, fadeInAnimation

from utils import callFunctionIfCallable

class VRCT_GUI(CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.is_config_window_already_opened_once=False
        self.BIND_UNMAP_DETECT_MAIN_WINDOW_STATE_FUNC_ID = None
        self.BIND_MAP_DETECT_MAIN_WINDOW_STATE_FUNC_ID = None

        self.window_state = None

    def detectMainWindowState(self, _e=None):
        self.new_window_state = self.wm_state()
        if self.window_state == self.new_window_state:
            return
        else:
            self.window_state = self.new_window_state

        if self.window_state == "iconic":
            self.main_window_cover.withdraw()
        elif self.window_state == "normal":
            self.main_window_cover.show()



    def _showGUI(self):
        self.attributes("-alpha", 0)
        self.deiconify()
        if self.settings.main.to_restore_main_window_geometry is True:
            self.geometry("{}x{}+{}+{}".format(
                self.settings.main.geometry.width,
                self.settings.main.geometry.height,
                self.settings.main.geometry.x_pos,
                self.settings.main.geometry.y_pos,
            ))
        else:
            self.geometry("{}x{}".format(
                self.settings.main.uism.MAIN_AREA_MIN_WIDTH + self.settings.main.uism.SIDEBAR_MIN_WIDTH,
                self.winfo_height()
            ))
            setGeometryToCenterOfScreen(root_widget=self)


        if self._view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE is True:
            self._enableMainWindowSidebarCompactMode()
        fadeInAnimation(self, steps=5, interval=0.008)


        if self._isOverWindowSizeCheck() is True:
            callFunctionIfCallable(self._view_variable.CALLBACK_WHEN_DETECT_WINDOW_OVERED_SIZE)


    def _createGUI(self, settings, view_variable):
        self.settings = settings
        self._view_variable = view_variable

        self.translation_engine_dropdown_menu_window = _CreateDropdownMenuWindow(
            settings=settings.dropdown_menu_window,
            view_variable=self._view_variable,

            window_additional_y_pos=self.settings.main.uism.SLS__DROPDOWN_MENU_WINDOW_ADDITIONAL_Y_POS,
            window_border_width=self.settings.main.uism.SLS__DROPDOWN_MENU_WINDOW_BORDER_WIDTH,
            scrollbar_ipadx=self.settings.main.uism.SLS__DROPDOWN_MENU_SCROLLBAR_IPADX,
            scrollbar_width=self.settings.main.uism.SLS__DROPDOWN_MENU_SCROLLBAR_WIDTH,
            value_ipadx=self.settings.main.uism.SLS__DROPDOWN_MENU_VALUE_IPADX,
            value_ipady=self.settings.main.uism.SLS__DROPDOWN_MENU_VALUE_IPADY,
            value_pady=self.settings.main.uism.SLS__DROPDOWN_MENU_VALUE_PADY,
            value_font_size=self.settings.main.uism.SLS__DROPDOWN_MENU_VALUE_FONT_SIZE,
            dropdown_menu_default_min_width=self.settings.main.uism.SLS__DROPDOWN_MENU_VALUE_DEFAULT_MIN_WIDTH,

            window_bg_color=self.settings.main.ctm.SLS__DROPDOWN_MENU_WINDOW_BG_COLOR,
            window_border_color=self.settings.main.ctm.SLS__DROPDOWN_MENU_WINDOW_BORDER_COLOR,
            values_bg_color=self.settings.main.ctm.SLS__DROPDOWN_MENU_BG_COLOR,
            values_hovered_bg_color=self.settings.main.ctm.SLS__DROPDOWN_MENU_HOVERED_BG_COLOR,
            values_clicked_bg_color=self.settings.main.ctm.SLS__DROPDOWN_MENU_CLICKED_BG_COLOR,
            values_text_color=self.settings.main.ctm.BASIC_TEXT_COLOR,
        )

        createMainWindowWidgets(
            vrct_gui=self,
            settings=self.settings.main,
            view_variable=self._view_variable
        )

        # For Config Window
        self.dropdown_menu_window = _CreateDropdownMenuWindow(
            settings=self.settings.dropdown_menu_window,
            view_variable=self._view_variable,

            window_additional_y_pos=self.settings.config_window.uism.SB__DROPDOWN_MENU_WINDOW_ADDITIONAL_Y_POS,
            window_border_width=self.settings.config_window.uism.SB__DROPDOWN_MENU_WINDOW_BORDER_WIDTH,
            scrollbar_ipadx=self.settings.config_window.uism.SB__DROPDOWN_MENU_SCROLLBAR_IPADX,
            scrollbar_width=self.settings.config_window.uism.SB__DROPDOWN_MENU_SCROLLBAR_WIDTH,
            value_ipadx=self.settings.config_window.uism.SB__DROPDOWN_MENU_VALUE_IPADX,
            value_ipady=self.settings.config_window.uism.SB__DROPDOWN_MENU_VALUE_IPADY,
            value_pady=self.settings.config_window.uism.SB__DROPDOWN_MENU_VALUE_PADY,
            value_font_size=self.settings.config_window.uism.SB__DROPDOWN_MENU_VALUE_FONT_SIZE,
            dropdown_menu_default_min_width=self.settings.config_window.uism.SB__DROPDOWN_MENU_VALUE_DEFAULT_MIN_WIDTH,

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

        self.main_window_cover = _CreateWindowCover(
            attach_window=self,
            settings=self.settings.main_window_cover,
            view_variable=self._view_variable
        )

        self.error_message_window = _CreateErrorWindow(
            settings=self.settings.error_message_window,
            view_variable=self._view_variable,
            wrapper_widget=self.config_window.main_bg_container,

            message_ipadx=self.settings.config_window.uism.SB__ERROR_MESSAGE_IPADX,
            message_ipady=self.settings.config_window.uism.SB__ERROR_MESSAGE_IPADY,
            message_font_size=self.settings.config_window.uism.SB__ERROR_MESSAGE_FONT_SIZE,

            message_bg_color=self.settings.config_window.ctm.SB__ERROR_MESSAGE_BG_COLOR,
            message_text_color=self.settings.config_window.ctm.SB__ERROR_MESSAGE_TEXT_COLOR,
        )

        self.confirmation_modal = _CreateConfirmationModal(
            attach_window=self.toplevel_wrapper,
            settings=self.settings.confirmation_modal,
            view_variable=self._view_variable
        )

        self.information_modal = _CreateConfirmationModal(
            attach_window=self.toplevel_wrapper,
            settings=self.settings.confirmation_modal,
            view_variable=self._view_variable,
            modal_type="information"
        )

        self.print_to_textbox = _PrintToTextbox(
            vrct_gui=self,
            settings=self.settings.main,
            init_scaling=(self._view_variable.VAR_TEXTBOX_UI_SCALING.get()/100)
        )




    def _startMainLoop(self):
        self.mainloop()


    def _quitVRCT(self):
        self.quit()
        self.destroy()


    def _openConfigWindow(self):
        self.main_window_cover.show(bind_focusin=self.config_window.lift)

        self.BIND_UNMAP_DETECT_MAIN_WINDOW_STATE_FUNC_ID = self.bind("<Unmap>", self.detectMainWindowState, "+")
        self.BIND_MAP_DETECT_MAIN_WINDOW_STATE_FUNC_ID = self.bind("<Map>", self.detectMainWindowState, "+")


        self.config_window.attributes("-alpha", 0)
        self.config_window.deiconify()
        if self.is_config_window_already_opened_once is False:
            setGeometryToCenterOfScreen(self.config_window)
            self.is_config_window_already_opened_once = True
            fadeInAnimation(self.config_window, steps=5, interval=0.005)
        self.config_window.attributes("-alpha", 1)
        self.config_window.focus_set()

    def _closeConfigWindow(self):
        self.config_window.withdraw()

        self.main_window_cover.hide()
        self.unbind("<Unmap>", self.BIND_UNMAP_DETECT_MAIN_WINDOW_STATE_FUNC_ID)
        self.unbind("<Map>", self.BIND_MAP_DETECT_MAIN_WINDOW_STATE_FUNC_ID)
        self.adjusted_event=None



    def _openSelectableLanguagesWindow(self, selectable_language_window_type):
        if selectable_language_window_type == "your_language":
            if self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW is False:
                self.sls__arrow_img_your_language.configure(image=CTkImage(self.settings.main.image_file.ARROW_LEFT, size=self.settings.main.uism.SLS__BOX_OPTION_MENU_ARROW_IMAGE_SIZE))
                self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW = True
                self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW = False
            else:
                self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW = False
                return

        elif selectable_language_window_type == "target_language":
            if self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW is False:
                self.sls__arrow_img_target_language.configure(image=CTkImage(self.settings.main.image_file.ARROW_LEFT, size=self.settings.main.uism.SLS__BOX_OPTION_MENU_ARROW_IMAGE_SIZE))
                self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW = True
                self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW = False
            else:
                self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW = False
                return


        self.selectable_languages_window.createContainer(selectable_language_window_type)
        self.selectable_languages_window.deiconify()
        self.selectable_languages_window.focus_set()
        self.selectable_languages_window.attributes("-topmost", True)


    def _closeSelectableLanguagesWindow(self):
        self.sls__arrow_img_your_language.configure(image=CTkImage(self.settings.main.image_file.ARROW_LEFT.rotate(180), size=self.settings.main.uism.SLS__BOX_OPTION_MENU_ARROW_IMAGE_SIZE))
        self.sls__arrow_img_target_language.configure(image=CTkImage(self.settings.main.image_file.ARROW_LEFT.rotate(180), size=self.settings.main.uism.SLS__BOX_OPTION_MENU_ARROW_IMAGE_SIZE))
        self.selectable_languages_window.withdraw()


        if self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW is not False or self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW is not False:
            def callback():
                self._view_variable.IS_OPENED_SELECTABLE_TARGET_LANGUAGE_WINDOW = False
                self._view_variable.IS_OPENED_SELECTABLE_YOUR_LANGUAGE_WINDOW = False
            self.after(500,callback)



    def _changeMainWindowWidgetsStatus(self, status, target_names, to_lock_state:bool=False, release_locked_state:bool=False):
        _changeMainWindowWidgetsStatus(
            vrct_gui=self,
            settings=self.settings.main,
            view_variable=self._view_variable,
            status=status,
            target_names=target_names,
            to_lock_state=to_lock_state,
            release_locked_state=release_locked_state,
        )

    def _changeConfigWindowWidgetsStatus(self, status, target_names):
        _changeConfigWindowWidgetsStatus(
            config_window=self.config_window,
            settings=self.settings.config_window,
            view_variable=self._view_variable,
            status=status,
            target_names=target_names,
        )

    def _printToTextbox(self, target_type, **kwargs):
        self.print_to_textbox.printToTextbox(
            target_type=target_type,
            **kwargs
        )

    def _setDefaultActiveLanguagePresetTab(self, tab_no:str):
        self.current_active_preset_tab = getattr(self, f"sls__presets_button_{tab_no}")
        setDefaultActiveTab(
            active_tab_widget=self.current_active_preset_tab,
            active_bg_color=self.settings.main.ctm.SLS__PRESETS_TAB_BG_ACTIVE_COLOR,
            active_text_color=self.settings.main.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR
        )

    def _enableMainWindowSidebarCompactMode(self):
        self.sidebar_bg_container.grid_remove()
        self.sidebar_compact_mode_bg_container.grid()
        self.minimize_sidebar_button_container__for_closing.grid_remove()
        self.minimize_sidebar_button_container__for_opening.grid()

    def _disableMainWindowSidebarCompactMode(self):
        self.sidebar_compact_mode_bg_container.grid_remove()
        self.sidebar_bg_container.grid()
        self.minimize_sidebar_button_container__for_opening.grid_remove()
        self.minimize_sidebar_button_container__for_closing.grid()


    def _showErrorMessage(self, target_widget):
        self.error_message_window.show(target_widget=target_widget)

    def _clearErrorMessage(self):
        try:
            self.error_message_window._withdraw()
        except Exception:
            pass


    def _isOverWindowSizeCheck(self):
        self.update()
        screen_height = self.winfo_screenheight()
        window_height = self.winfo_height()
        if screen_height < window_height:
            return True
        else:
            return False

vrct_gui = VRCT_GUI()