from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkFont

class _CreateModalWindow(CTkToplevel):
    def __init__(self, attach_window, settings, view_variable):
        super().__init__()
        self.withdraw()


        self.title("")
        self.overrideredirect(True)

        self.wm_attributes("-alpha", 0.5)
        self.wm_attributes("-toolwindow", True)

        self.attach_window = attach_window


        self.configure(fg_color="#ff7f50")
        self.protocol("WM_DELETE_WINDOW", lambda e: self.withdraw())

        self.settings = settings
        self._view_variable = view_variable


        self.attach_window.update_idletasks()
        self.x_pos = self.attach_window.winfo_rootx()
        self.y_pos = self.attach_window.winfo_rooty()
        self.width_new = self.attach_window.winfo_width()
        self.height_new = self.attach_window.winfo_height()


        self.geometry('{}x{}+{}+{}'.format(self.width_new, self.height_new, self.x_pos, self.y_pos))

        self.grid_rowconfigure(0,weight=1)
        self.grid_columnconfigure(0,weight=1)
        self.modal_container = CTkFrame(self, corner_radius=0, fg_color="black", width=0, height=0)
        self.modal_container.grid(row=0, column=0, sticky="nsew")


        self.modal_container_label_wrapper = CTkLabel(
            self.modal_container,
            textvariable=self._view_variable.VAR_LABEL_MODAL_MESSAGE_FOR__MAIN_WINDOW,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.TEXT_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.TEXT_COLOR,
        )
        self.modal_container_label_wrapper.place(relx=0.5, rely=0.5, anchor="center")