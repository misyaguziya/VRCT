from types import SimpleNamespace

from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkFont, CTkScrollableFrame
from time import sleep

from .ui_utils import bindButtonReleaseFunction, bindEnterAndLeaveColor, bindButtonPressColor, getLatestWidth, getLatestHeight
from functools import partial

class _CreateDropdownMenuWindow(CTkToplevel):
    def __init__(self, settings, view_variable):
        super().__init__()
        self.withdraw()
        self.hide = True

        self.title("")
        self.overrideredirect(True)

        self.wm_attributes("-alpha", 0)
        self.wm_attributes("-toolwindow", True)

        self.resizable(width=False, height=False)


        self.settings = settings
        self.attach_widget = None
        self._view_variable = view_variable
        self.wrapper_widget = None

        self.dropdown_menu_widgets = {}
        self.active_dropdown_menu_widget = None



        self.attach_widget_width = None
        self.attach_widget_height = None
        self.attach_widget_x_pos = None
        self.attach_widget_y_pos = None
        self.x_pos = None
        self.y_pos = None



        # self.rowconfigure(0,weight=1)
        # self.columnconfigure(0,weight=1)

        # The color code [#bb4448] is a mixture of [#a9555c] and [#cc3333] (for a redder shade).

    def updateDropdownMenuValues(self, dropdown_menu_widget_id, dropdown_menu_values):
        self.dropdown_menu_widgets[dropdown_menu_widget_id].widget.destroy()
        self.createDropdownMenuBox(
            dropdown_menu_widget_id=dropdown_menu_widget_id,
            dropdown_menu_values=dropdown_menu_values,
            command=self.dropdown_menu_widgets[dropdown_menu_widget_id].command,
            wrapper_widget=self.dropdown_menu_widgets[dropdown_menu_widget_id].wrapper_widget,
        )


    def createDropdownMenuBox(self, dropdown_menu_widget_id, dropdown_menu_values, command, wrapper_widget):
        self.wrapper_widget = wrapper_widget

        self.dropdown_menu_container = CTkFrame(self, corner_radius=0, fg_color="#bb4448", width=0, height=0)
        self.dropdown_menu_container.grid(row=0, column=0, sticky="nsew")
        self.dropdown_menu_container.grid_remove()

        self.dropdown_menu_widgets[dropdown_menu_widget_id] = SimpleNamespace()

        self.dropdown_menu_widgets[dropdown_menu_widget_id] = SimpleNamespace(
            widget=self.dropdown_menu_container,
            command=command,
            wrapper_widget=wrapper_widget,
        )


        self.scroll_frame_container = CTkScrollableFrame(
            self.dropdown_menu_container,
            corner_radius=0,
            fg_color=self.settings.ctm.SB__DROPDOWN_MENU_WINDOW_BG_COLOR,
            width=0,
            height=0,
            border_color=self.settings.ctm.SB__DROPDOWN_MENU_WINDOW_BORDER_COLOR,
            border_width=1,
        )
        self.scroll_frame_container.grid(row=0, column=0, sticky="nsew")
        self.scroll_frame_container._scrollbar.grid_configure(padx=3)
        self.scroll_frame_container.grid_columnconfigure(0, weight=1)

        self.dropdown_menu_values_box = CTkFrame(self.scroll_frame_container, corner_radius=0, fg_color=self.settings.ctm.SB__DROPDOWN_MENU_WINDOW_BG_COLOR, width=0, height=0)
        self.dropdown_menu_values_box.grid(row=0, column=0, sticky="nsew")
        self.dropdown_menu_values_box.grid_columnconfigure(0, weight=1)

        self._createDropdownMenuValues(dropdown_menu_widget_id, dropdown_menu_values, command)

    def _createDropdownMenuValues(self, dropdown_menu_widget_id, dropdown_menu_values, command):

        # self.dropdown_menu_values_wrapper = CTkFrame(self.scroll_frame_container, corner_radius=0, fg_color="red", width=0, height=0)
        self.dropdown_menu_values_wrapper = CTkFrame(self.scroll_frame_container, corner_radius=0, fg_color=self.settings.ctm.SB__DROPDOWN_MENU_WINDOW_BG_COLOR)
        self.dropdown_menu_values_wrapper.grid(row=0, column=0, sticky="nsew")
        self.dropdown_menu_values_wrapper.grid_columnconfigure(0, weight=1)

        # for get to the height__________________
        __dropdown_menu_value_wrapper = CTkFrame(self.dropdown_menu_values_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__DROPDOWN_MENU_BG_COLOR, width=0, height=0)
        __dropdown_menu_value_wrapper.grid(row=0, column=0, ipadx=6, ipady=6, sticky="nsew")
        setattr(self, f"{dropdown_menu_widget_id}__{0}", __dropdown_menu_value_wrapper)


        __dropdown_menu_value_wrapper.grid_rowconfigure((0,2), weight=1)
        __dropdown_menu_value_wrapper.grid_columnconfigure(0, weight=1)
        __label_widget = CTkLabel(
            __dropdown_menu_value_wrapper,
            text="Aa",
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=14, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.BASIC_TEXT_COLOR,
        )
        # setattr(self, f"l", __label_widget)

        __label_widget.grid(row=1, column=0, padx=(8,0), sticky="w")
        label_height = getLatestHeight(__dropdown_menu_value_wrapper)
        # ______________________________________

        dropdown_menu_values_length = len(dropdown_menu_values)
        if dropdown_menu_values_length <= 3:
            self.scroll_frame_container.configure(width=200, height=int(dropdown_menu_values_length * label_height))
            # self.geometry("{}x{}".format(300, int(dropdown_menu_values_length * label_height)))
            # self.geometry("{}x{}".format(300, int(dropdown_menu_values_length * label_height)))
            # self.scroll_frame_container._parent_canvas.configure(height=20)
        else:
            self.scroll_frame_container.configure(width=200, height=200)
            # self.geometry("{}x{}".format(200, 200))
            # self.scroll_frame_container._parent_canvas.configure(height=20)

        # This is for CustomTkinter's spec change or bug fix.
        self.scroll_frame_container._scrollbar.configure(height=0)



        row=0
        for dropdown_menu_value in dropdown_menu_values:

            dropdown_menu_value_wrapper = CTkFrame(self.dropdown_menu_values_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__DROPDOWN_MENU_BG_COLOR, width=0, height=0)
            dropdown_menu_value_wrapper.grid(row=row, column=0, ipadx=6, ipady=6, sticky="nsew")
            setattr(self, f"{dropdown_menu_widget_id}__{row}", dropdown_menu_value_wrapper)



            dropdown_menu_value_wrapper.grid_rowconfigure((0,2), weight=1)
            dropdown_menu_value_wrapper.grid_columnconfigure(0, weight=1)
            label_widget = CTkLabel(
                dropdown_menu_value_wrapper,
                text=dropdown_menu_value,
                height=0,
                corner_radius=0,
                font=CTkFont(family=self.settings.FONT_FAMILY, size=14, weight="normal"),
                anchor="w",
                text_color=self.settings.ctm.BASIC_TEXT_COLOR,
            )
            # setattr(self, f"l", label_widget)

            label_widget.grid(row=1, column=0, padx=(8,0), sticky="w")



            bindEnterAndLeaveColor([dropdown_menu_value_wrapper, label_widget], self.settings.ctm.SB__DROPDOWN_MENU_HOVERED_BG_COLOR, self.settings.ctm.SB__DROPDOWN_MENU_BG_COLOR)
            bindButtonPressColor([dropdown_menu_value_wrapper, label_widget], self.settings.ctm.SB__DROPDOWN_MENU_CLICKED_BG_COLOR, self.settings.ctm.SB__DROPDOWN_MENU_BG_COLOR)



            def optimizedCommand(value, _e):
                command(value)
                self._withdraw()

            callback = partial(optimizedCommand, dropdown_menu_value)
            bindButtonReleaseFunction([dropdown_menu_value_wrapper, label_widget], callback)

            row+=1



    def show(self, dropdown_menu_widget_id, target_widget):
        if self.hide is False: return
        self.wm_attributes("-alpha", 0)


        self.attach_widget = target_widget

        if self.active_dropdown_menu_widget is not None:
            self.active_dropdown_menu_widget.grid_remove()

        target_Widget = self.dropdown_menu_widgets[dropdown_menu_widget_id].widget
        target_Widget.grid()
        self.active_dropdown_menu_widget = target_Widget

        self.deiconify()
        self._adjustToTargetWidgetGeometry()
        self.BIND_CONFIGURE_FUNC_ID = self.attach_widget.winfo_toplevel().bind("<Configure>", self._adjustToTargetWidgetGeometry, "+")
        self.BIND_UNMAP_FUNC_ID = self.attach_widget.bind("<Unmap>", self._withdraw, "+")

        self.BIND_BUTTON_1_FUNC_ID = self.attach_widget.winfo_toplevel().bind("<Button-1>", self._withdraw, "+")


        self.hide = False



        for i in range(0,91,10):
            if not self.winfo_exists():
                break
            self.attributes("-alpha", i/100)
            self.update()
            sleep(1/100)
        self.wm_attributes("-alpha", 1)
        self.update()



    def _withdraw(self, e=None):
        self.withdraw()
        self.attach_widget.winfo_toplevel().unbind("<Configure>", self.BIND_CONFIGURE_FUNC_ID)
        self.attach_widget.unbind("<Unmap>", self.BIND_UNMAP_FUNC_ID)
        self.attach_widget.winfo_toplevel().unbind("<Button-1>", self.BIND_BUTTON_1_FUNC_ID)
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


