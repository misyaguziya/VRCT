from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkFont
from time import sleep

class _CreateErrorWindow(CTkToplevel):
    def __init__(self, settings, view_variable, wrapper_widget):
        super().__init__()
        self.withdraw()
        self.hide = True

        self.title("")
        self.overrideredirect(True)

        self.wm_attributes("-alpha", 0)
        self.wm_attributes("-toolwindow", True)

        self.settings = settings
        self.attach_widget = None
        self._view_variable = view_variable
        self.wrapper_widget = wrapper_widget



        self.attach_widget_width = None
        self.attach_widget_height = None
        self.attach_widget_x_pos = None
        self.attach_widget_y_pos = None
        self.x_pos = None
        self.y_pos = None



        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight=1)

        # The color code [#bb4448] is a mixture of [#a9555c] and [#cc3333] (for a redder shade).
        self.modal_container = CTkFrame(self, corner_radius=0, fg_color="#bb4448", width=0, height=0)
        self.modal_container.grid(row=0, column=0, sticky="nsew")


        self.modal_container_label_wrapper = CTkLabel(
            self.modal_container,
            # text=message,
            textvariable=self._view_variable.VAR_ERROR_MESSAGE,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=12, weight="normal"),
            anchor="w",
            text_color="white",
        )
        self.modal_container_label_wrapper.grid(row=0, column=0, padx=10, pady=6, sticky="nsew")



    def show(self, target_widget):
        if self.hide is False: return

        self.attach_widget = target_widget

        self.deiconify()
        self._adjustToTargetWidgetGeometry()
        self.BIND_CONFIGURE_FUNC_ID = self.attach_widget.winfo_toplevel().bind("<Configure>", self._adjustToTargetWidgetGeometry, "+")
        self.BIND_UNMAP_FUNC_ID = self.attach_widget.bind("<Unmap>", self._withdraw, "+")

        self.hide = False


        for i in range(0,101,20):
            if not self.winfo_exists():
                break
            self.attributes("-alpha", i/100)
            self.update()
            sleep(1/100)

        sleep(0.1)

        for i in range(0,91,10):
            if not self.winfo_exists():
                break
            self.attributes("-alpha", i/100)
            self.update()
            sleep(1/80)


    def _withdraw(self, e=None):
        self.withdraw()
        self.attach_widget.winfo_toplevel().unbind("<Configure>", self.BIND_CONFIGURE_FUNC_ID)
        self.attach_widget.unbind("<Unmap>", self.BIND_UNMAP_FUNC_ID)
        self.hide = True



    def _adjustToTargetWidgetGeometry(self, e=None):
        if not self.attach_widget.winfo_exists():
            return
        self.attach_widget.update_idletasks()



        self.update()
        if self.attach_widget_x_pos == self.attach_widget.winfo_rootx() and self.attach_widget_y_pos == self.attach_widget.winfo_rooty():
            self.lift()
            return

        self.wrapper_widget_y_pos = self.wrapper_widget.winfo_rooty()
        self.wrapper_widget_bottom_y_pos = self.wrapper_widget_y_pos + self.wrapper_widget.winfo_height()

        self.attach_widget_width = self.attach_widget.winfo_width()
        self.attach_widget_height = self.attach_widget.winfo_height()
        self.attach_widget_x_pos = self.attach_widget.winfo_rootx()
        self.attach_widget_y_pos = self.attach_widget.winfo_rooty()


        self.y_pos = int(self.attach_widget_y_pos + self.attach_widget_height + 4)

        if self.wrapper_widget_y_pos > self.y_pos or self.y_pos > self.wrapper_widget_bottom_y_pos:
            self.hideTemporarily()
        else:
            if self.winfo_exists():
                self.deiconify()


        if self.winfo_width() >= self.attach_widget_width:
            self.x_pos = int(self.attach_widget_x_pos - (self.winfo_width() - self.attach_widget_width))
        else:
            self.x_pos = self.attach_widget_x_pos

        self.geometry("+{}+{}".format(self.x_pos, self.y_pos))

        self.lift()

    def hideTemporarily(self):
        self.withdraw()


