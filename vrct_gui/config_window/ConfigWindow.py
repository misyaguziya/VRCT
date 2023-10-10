from .widgets import createConfigWindowTitle, createSideMenuAndSettingsBoxContainers, createSettingBoxTopBar


from customtkinter import CTkToplevel

from ..ui_utils import getImagePath

class ConfigWindow(CTkToplevel):
    def __init__(self, vrct_gui, settings, view_variable):
        super().__init__()
        self.withdraw()


        # configure window
        self.after(200, lambda: self.iconbitmap(getImagePath("vrct_logo_mark_black.ico")))
        self.title("Settings")
        self.geometry(f"{settings.uism.DEFAULT_WIDTH}x{settings.uism.DEFAULT_HEIGHT}")


        self.configure(fg_color="#ff7f50")
        self.protocol("WM_DELETE_WINDOW", vrct_gui.closeConfigWindow)

        self.settings = settings
        self._view_variable = view_variable

        # When the configuration window's compact mode is turned on, it will call `grid_remove()` on each widget appended to this array. In the opposite case, `grid()` will be called.
        self.additional_widgets = []

        createConfigWindowTitle(config_window=self, settings=self.settings)

        createSettingBoxTopBar(config_window=self, settings=self.settings, view_variable=self._view_variable)


        createSideMenuAndSettingsBoxContainers(config_window=self, settings=self.settings, view_variable=self._view_variable)


        self.bind_all("<Button-1>", lambda event: event.widget.focus_set(), "+")