from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkFont
from time import sleep

from .ui_utils import getLatestWidth, getLatestHeight
from utils import isEven


class _CreateNotificationWindow(CTkToplevel):
    def __init__(
            self,
            settings,
            view_variable,
            wrapper_widget,

            message_ipadx,
            message_ipady,
            message_font_size,

            error_message_bg_color,
            success_message_bg_color,
            message_text_color,
        ):

        super().__init__()
        self.withdraw()
        self.hide = True

        self.settings = settings
        self.attach_widget = None
        self._view_variable = view_variable
        self.wrapper_widget = wrapper_widget


        self.message_ipadx = message_ipadx
        self.message_ipady = message_ipady
        self.message_font_size = message_font_size

        self.error_message_bg_color = error_message_bg_color
        self.success_message_bg_color = success_message_bg_color
        self.message_text_color = message_text_color


        self.attach_widget_width = None
        self.attach_widget_height = None
        self.attach_widget_x_pos = None
        self.attach_widget_y_pos = None
        self.x_pos = None
        self.y_pos = None

        self.title("")
        self.overrideredirect(True)

        self.wm_attributes("-alpha", 0)
        self.wm_attributes("-toolwindow", True)


        self.grid_rowconfigure(0,weight=1)
        self.grid_columnconfigure(0,weight=1)

        self.notification_message_container = CTkFrame(self, corner_radius=0, width=0, height=0)
        self.notification_message_container.grid(row=0, column=0, sticky="nsew")


        self.notification_message_container_label_wrapper = CTkLabel(
            self.notification_message_container,
            # text=message,
            textvariable=self._view_variable.VAR_ERROR_MESSAGE,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.message_font_size, weight="normal"),
            anchor="w",
            justify="left",
            text_color=self.message_text_color,
        )
        self.notification_message_container_label_wrapper.grid(row=0, column=0, padx=self.message_ipadx, pady=self.message_ipady, sticky="nsew")




    def show(self, target_widget, message_type):
        if message_type == "Error":
            self.notification_message_container.configure(fg_color=self.error_message_bg_color)
        elif message_type == "Success":
            self.notification_message_container.configure(fg_color=self.success_message_bg_color)
        else:
            raise ValueError("message_type is not selected")

        if self.hide is False:
            return

        self.attach_widget = target_widget

        self.deiconify()
        self._adjustToTargetWidgetGeometry()
        self.BIND_CONFIGURE_FUNC_ID = self.attach_widget.winfo_toplevel().bind("<Configure>", self._adjustToTargetWidgetGeometry, "+")
        self.BIND_UNMAP_FUNC_ID = self.attach_widget.bind("<Unmap>", self._withdraw, "+")

        self.hide = False

        label_width = getLatestWidth(self.notification_message_container_label_wrapper)
        label_height = getLatestHeight(self.notification_message_container_label_wrapper)

        # for fixing 1px bug
        if isEven(label_width) is False:
            self.notification_message_container_label_wrapper.grid(padx=(self.message_ipadx[0], self.message_ipadx[1]-1))
        else:
            self.notification_message_container_label_wrapper.grid(padx=self.message_ipadx)

        # for fixing 1px bug
        if isEven(label_height) is False:
            self.notification_message_container_label_wrapper.grid(pady=(self.message_ipady[0], self.message_ipady[1]-1))
        else:
            self.notification_message_container_label_wrapper.grid(pady=self.message_ipady)


        # First show animation
        for i in range(0,101,20):
            if not self.winfo_exists():
                break
            self.attributes("-alpha", i/100)
            self.update()
            sleep(1/100)

        sleep(0.1)

        # Blink animation
        if message_type == "Error":
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


