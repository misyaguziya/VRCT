from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkFont

from .ui_utils import fadeInAnimation
from utils import makeEven

class _CreateWindowCover(CTkToplevel):
    def __init__(self, attach_window, settings, view_variable):
        super().__init__()
        self.withdraw()

        self.BIND_CONFIGURE_ADJUSTED_GEOMETRY_FUNC_ID=None
        self.BIND_FOCUS_IN_FUNC_ID=None

        self.attach_window = attach_window
        self.settings = settings
        self._view_variable = view_variable

        self.title("")
        self.overrideredirect(True)
        self.wm_attributes("-toolwindow", True)
        self.configure(fg_color=self.settings.ctm.BG_COLOR)
        self.protocol("WM_DELETE_WINDOW", lambda: self.withdraw())


        self.grid_rowconfigure(0,weight=1)
        self.grid_columnconfigure(0,weight=1)
        self.cover_container = CTkFrame(self, corner_radius=0, fg_color=self.settings.ctm.BG_COLOR, width=0, height=0)
        self.cover_container.grid(row=0, column=0, sticky="nsew")


        self.cover_container_label_wrapper = CTkLabel(
            self.cover_container,
            textvariable=self._view_variable.VAR_LABEL_MAIN_WINDOW_COVER_MESSAGE,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.TEXT_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.TEXT_COLOR,
        )
        self.cover_container_label_wrapper.place(relx=0.5, rely=0.5, anchor="center")


    def show(self, bind_focusin=None):
        self.BIND_CONFIGURE_ADJUSTED_GEOMETRY_FUNC_ID = self.attach_window.bind("<Configure>", self._adjustToMainWindowGeometry, "+")
        if bind_focusin is not None:
            self.BIND_FOCUS_IN_FUNC_ID = self.bind("<FocusIn>", lambda _e: bind_focusin(), "+")
        else:
            self.BIND_FOCUS_IN_FUNC_ID = None


        self.attributes("-alpha", 0)
        self.deiconify()
        self.attach_window.update_idletasks()
        self.x_pos = self.attach_window.winfo_rootx()
        self.y_pos = self.attach_window.winfo_rooty()
        self.width_new = self.attach_window.winfo_width()
        self.height_new = self.attach_window.winfo_height()
        self.geometry("{}x{}+{}+{}".format(self.width_new, self.height_new, self.x_pos, self.y_pos))
        fadeInAnimation(self, steps=5, interval=0.005, max_alpha=0.8)



    def hide(self):
        self.attach_window.unbind("<Configure>", self.BIND_CONFIGURE_ADJUSTED_GEOMETRY_FUNC_ID)
        if self.BIND_FOCUS_IN_FUNC_ID is not None:
            self.unbind("<FocusIn>", self.BIND_FOCUS_IN_FUNC_ID)

        self.withdraw()



    def _adjustToMainWindowGeometry(self, e=None):
        self.attach_window.update_idletasks()
        x_pos = self.attach_window.winfo_rootx()
        y_pos = self.attach_window.winfo_rooty()
        width_new = makeEven(self.attach_window.winfo_width())
        height_new = makeEven(self.attach_window.winfo_height())
        self.geometry("{}x{}+{}+{}".format(width_new, height_new, x_pos, y_pos))

        self.lift()