from .widgets import createConfigWindowTitle, createSideMenuAndSettingsBoxContainers, createSettingBoxTopBar


from customtkinter import CTkToplevel, CTkFrame

from ..ui_utils import getImagePath, getLatestWidth, getLatestHeight

class ConfigWindow(CTkToplevel):
    def __init__(self, vrct_gui, settings, view_variable):
        super().__init__()
        self.withdraw()


        # configure window
        self.after(200, lambda: self.iconbitmap(getImagePath("vrct_logo_mark_black.ico")))
        self.geometry(f"{settings.uism.DEFAULT_WIDTH}x{settings.uism.DEFAULT_HEIGHT}")


        self.configure(fg_color="#ff7f50")
        self.protocol("WM_DELETE_WINDOW", vrct_gui._closeConfigWindow)

        self.settings = settings
        self._view_variable = view_variable

        self.title(self._view_variable.VAR_CONFIG_WINDOW_TITLE.get())
        # When the configuration window's compact mode is turned on, it will call `grid_remove()` on each widget appended to this array. In the opposite case, `grid()` will be called.
        self.additional_widgets = []

        self.sb__widgets = {}

        createConfigWindowTitle(config_window=self, settings=self.settings, view_variable=self._view_variable)

        createSettingBoxTopBar(config_window=self, settings=self.settings, view_variable=self._view_variable)

        createSideMenuAndSettingsBoxContainers(config_window=self, settings=self.settings, view_variable=self._view_variable)

        # for fixing 1px bug
        sls__box_optionmenu_wrapper_fix_1px_bug = CTkFrame(self.side_menu_bg_container, corner_radius=0, width=0, height=0)
        sls__box_optionmenu_wrapper_fix_1px_bug.grid(row=1, column=0, sticky="ew")


        self.bind_all("<Button-1>", lambda event: event.widget.focus_set(), "+")