from .widgets import createConfigWindowTitle, createSideMenuAndSettingsBoxContainers, createSettingBoxTopBar


from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkFont

from ..ui_utils import getImagePath, getLatestWidth
from utils import isEven

class ConfigWindow(CTkToplevel):
    def __init__(self, vrct_gui, settings, view_variable):
        super().__init__()
        self.withdraw()

        self.settings = settings
        self._view_variable = view_variable

        # configure window
        self.after(200, lambda: self.iconbitmap(getImagePath("vrct_logo_mark_black.ico")))
        self.geometry(f"{self.settings.uism.DEFAULT_WIDTH}x{self.settings.uism.DEFAULT_HEIGHT}")


        self.configure(fg_color=self.settings.ctm.MAIN_BG_COLOR)
        self.protocol("WM_DELETE_WINDOW", self._view_variable.CALLBACK_CLICKED_CLOSE_CONFIG_WINDOW_BUTTON)


        self.title(self._view_variable.VAR_CONFIG_WINDOW_TITLE.get())
        # When the configuration window's compact mode is turned on, it will call `grid_remove()` on each widget appended to this array. In the opposite case, `grid()` will be called.
        self.additional_widgets = []

        self.sb__widgets = {}

        createConfigWindowTitle(config_window=self, settings=self.settings, view_variable=self._view_variable)

        createSettingBoxTopBar(config_window=self, settings=self.settings, view_variable=self._view_variable)

        createSideMenuAndSettingsBoxContainers(config_window=self, settings=self.settings, view_variable=self._view_variable)

        # for fixing 1px bug
        l_width = getLatestWidth(self.side_menu_bg_container)
        if isEven(l_width) is False:
            self.side_menu_bg_container.grid_columnconfigure(0, weight=0, minsize=l_width+1)

        # for fixing 1px bug
        # self.side_menu_bg_container.grid_rowconfigure(2, weight=1)
        # sls__box_optionmenu_wrapper_fix_1px_bug = CTkFrame(self.side_menu_bg_container, corner_radius=0, width=0, height=0)
        # sls__box_optionmenu_wrapper_fix_1px_bug.grid(row=3, column=0, sticky="sew")

        # for fixing 1px bug
        l_width = getLatestWidth(self.side_menu_bg_container)



        # VRCT Now Version Label(Tmp)
        version_label = CTkLabel(
            self.side_menu_bg_container,
            textvariable=self._view_variable.VAR_VERSION,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.NOW_VERSION_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.NOW_VERSION_TEXT_COLOR,
        )
        version_label.place(relx=0.05, rely=0.99, anchor="sw")


        self.bind_all("<Button-1>", lambda event: event.widget.focus_set(), "+")