from typing import Union
from types import SimpleNamespace

from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkFont
from time import sleep

from .ui_utils import bindButtonReleaseFunction, bindEnterAndLeaveColor, bindButtonPressColor, getLatestHeight, applyUiScalingAndFixTheBugScrollBar, getLatestWidth, getLongestText,  getLongestText_Dict, CustomizedCTkScrollableFrame
from functools import partial

from utils import isEven, makeEven

class _CreateDropdownMenuWindow(CTkToplevel):
    def __init__(
            self,
            settings,
            view_variable,

            window_additional_y_pos,
            window_border_width,
            scrollbar_ipadx,
            scrollbar_width,
            value_ipadx,
            value_ipady,
            value_pady,
            value_font_size,
            dropdown_menu_default_min_width,

            window_bg_color,
            window_border_color,
            values_bg_color,
            values_hovered_bg_color,
            values_clicked_bg_color,
            values_text_color,
        ):

        super().__init__()
        self.withdraw()
        self.hide = True

        self.window_additional_y_pos=window_additional_y_pos
        self.window_border_width=window_border_width
        self.scrollbar_ipadx=scrollbar_ipadx
        self.scrollbar_width=scrollbar_width
        self.value_ipadx=value_ipadx
        self.value_ipady=value_ipady
        self.value_pady=value_pady
        self.value_font_size=value_font_size
        self.dropdown_menu_default_min_width=dropdown_menu_default_min_width

        self.window_bg_color=window_bg_color
        self.window_border_color=window_border_color
        self.values_bg_color=values_bg_color
        self.values_hovered_bg_color=values_hovered_bg_color
        self.values_clicked_bg_color=values_clicked_bg_color
        self.values_text_color=values_text_color


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

        self.init_height = 200
        self.new_height = self.init_height
        self.init_width = 200
        self.new_width = self.init_width

        self.init_max_display_length = 8
        self.max_display_length = self.init_max_display_length

        self.title("")
        self.overrideredirect(True)

        self.wm_attributes("-alpha", 0)
        self.wm_attributes("-toolwindow", True)

        self.configure(fg_color=self.window_bg_color)
        self.resizable(width=False, height=False)



    def updateDropdownMenuValues(self, dropdown_menu_widget_id, dropdown_menu_values:Union[dict, list],):
        self.dropdown_menu_widgets[dropdown_menu_widget_id].widget.destroy()
        self.createDropdownMenuBox(
            dropdown_menu_widget_id=dropdown_menu_widget_id,
            dropdown_menu_values=dropdown_menu_values,
            command=self.dropdown_menu_widgets[dropdown_menu_widget_id].command,
            wrapper_widget=self.dropdown_menu_widgets[dropdown_menu_widget_id].wrapper_widget,
            attach_widget=self.dropdown_menu_widgets[dropdown_menu_widget_id].attach_widget,

            dropdown_menu_min_width=self.dropdown_menu_widgets[dropdown_menu_widget_id].dropdown_menu_settings.dropdown_menu_min_width,
            dropdown_menu_height=self.dropdown_menu_widgets[dropdown_menu_widget_id].dropdown_menu_settings.dropdown_menu_height,
            max_display_length=self.dropdown_menu_widgets[dropdown_menu_widget_id].dropdown_menu_settings.max_display_length,
        )


    def createDropdownMenuBox(self, dropdown_menu_widget_id, dropdown_menu_values:Union[dict, list], command, wrapper_widget, attach_widget, dropdown_menu_min_width=None, dropdown_menu_height=None, max_display_length=None):

        self.attach_widget = attach_widget
        self.wrapper_widget = wrapper_widget


        self.new_width = dropdown_menu_min_width if dropdown_menu_min_width is not None else self.dropdown_menu_default_min_width
        self.new_height = dropdown_menu_height if dropdown_menu_height is not None else self.init_height
        self.max_display_length = max_display_length if max_display_length is not None else self.init_max_display_length


        self.dropdown_menu_container = CTkFrame(self, corner_radius=0, fg_color=self.window_border_color, width=0, height=0)
        self.dropdown_menu_container.grid(row=0, column=0, sticky="nsew")


        BORDER_WIDTH=self.window_border_width
        self.scroll_frame_container = CustomizedCTkScrollableFrame(
            self.dropdown_menu_container,
            corner_radius=0,
            fg_color=self.window_bg_color,
            width=0,
            height=0,
            border_width=0,
        )
        self.scroll_frame_container.grid(row=0, column=0, padx=BORDER_WIDTH, pady=BORDER_WIDTH, sticky="nsew")
        self.scroll_frame_container.grid_columnconfigure(0, weight=1)



        self._createDropdownMenuValues(dropdown_menu_widget_id, dropdown_menu_values, command)

        applyUiScalingAndFixTheBugScrollBar(
            scrollbar_widget=self.scroll_frame_container,
            padx=self.scrollbar_ipadx,
            width=self.scrollbar_width,
        )

        geometry_width = int(self.new_width + self.scroll_frame_container._scrollbar.winfo_width() + (BORDER_WIDTH*2) + (self.scrollbar_ipadx[0] + self.scrollbar_ipadx[1]))
        geometry_height = int(self.new_height + (BORDER_WIDTH*2))

        self.dropdown_menu_widgets[dropdown_menu_widget_id] = SimpleNamespace()

        self.dropdown_menu_widgets[dropdown_menu_widget_id] = SimpleNamespace(
            widget=self.dropdown_menu_container,
            command=command,
            wrapper_widget=wrapper_widget,
            attach_widget=attach_widget,
            dropdown_menu_settings=SimpleNamespace(
                dropdown_menu_min_width=dropdown_menu_min_width,
                dropdown_menu_height=dropdown_menu_height,
                max_display_length=max_display_length,
            ),
            _settings=SimpleNamespace(
                geometry_width=geometry_width,
                geometry_height=geometry_height,
            ),
        )

        self.dropdown_menu_container.grid_remove()


    def _createDropdownMenuValues(self, dropdown_menu_widget_id, dropdown_menu_values:Union[dict, list], command):
        if isinstance(dropdown_menu_values, list):
            longest_text = getLongestText(dropdown_menu_values)
        elif isinstance(dropdown_menu_values, dict):
            longest_text = getLongestText_Dict(dropdown_menu_values)

        self.dropdown_menu_values_wrapper = CTkFrame(self.scroll_frame_container, corner_radius=0, fg_color=self.window_bg_color)
        self.dropdown_menu_values_wrapper.grid(row=0, column=0, sticky="nsew")
        self.dropdown_menu_values_wrapper.grid_columnconfigure(0, weight=1)

        # for get to the height__________________
        __dropdown_menu_value_wrapper = CTkFrame(self.dropdown_menu_values_wrapper, corner_radius=0, fg_color=self.values_bg_color, width=0, height=0)
        __dropdown_menu_value_wrapper.grid(row=0, column=0, pady=self.value_pady, sticky="nsew")
        setattr(self, f"{dropdown_menu_widget_id}__{0}", __dropdown_menu_value_wrapper)


        __dropdown_menu_value_wrapper.grid_rowconfigure((0,2), weight=1)
        __label_widget = CTkLabel(
            __dropdown_menu_value_wrapper,
            text=longest_text,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.value_font_size, weight="normal"),
            anchor="w",
            text_color=self.values_text_color,
        )

        __label_widget.grid(row=1, column=0, padx=self.value_ipadx, pady=self.value_ipady, sticky="w")

        label_height = getLatestHeight(__dropdown_menu_value_wrapper)
        label_width = getLatestWidth(__label_widget)
        label_width += self.scroll_frame_container._scrollbar.winfo_width() + (self.window_border_width*2) + (self.scrollbar_ipadx[0] + self.scrollbar_ipadx[1])
        if label_width > self.new_width:
            additional_width = int(label_width - self.new_width + self.settings.uism.MARGIN_WIDTH)
            self.new_width += additional_width

        # for fixing 1px bug
        if isEven(label_height) is False:
            self.value_ipady = (self.value_ipady[0], self.value_ipady[1] - 1)

        __dropdown_menu_value_wrapper.destroy()
        # ______________________________________

        dropdown_menu_values_length = len(dropdown_menu_values)
        if dropdown_menu_values_length < self.max_display_length:
            self.new_height = int(dropdown_menu_values_length * label_height)
        else:
            self.new_height = int(self.max_display_length * label_height)


        # for fixing 1px bug
        self.new_height = makeEven(self.new_height)
        self.new_width = makeEven(self.new_width)
        self.scroll_frame_container.configure(width=self.new_width, height=self.new_height)



        IS_LIST_TYPE = False
        if isinstance(dropdown_menu_values, list):
            for_in_values = dropdown_menu_values
            IS_LIST_TYPE = True
        elif isinstance(dropdown_menu_values, dict):
            for_in_values = dropdown_menu_values.keys()
            IS_LIST_TYPE = False

        row=0
        for dropdown_menu_value in for_in_values:
            dropdown_menu_value_wrapper = CTkFrame(self.dropdown_menu_values_wrapper, corner_radius=0, fg_color=self.values_bg_color, width=0, height=0, cursor="hand2")
            dropdown_menu_value_wrapper.grid(row=row, column=0, pady=self.value_pady, sticky="nsew")
            setattr(self, f"{dropdown_menu_widget_id}__{row}", dropdown_menu_value_wrapper)



            if IS_LIST_TYPE is True:
                dropdown_menu_value_text = dropdown_menu_value
            else:
                dropdown_menu_value_text = dropdown_menu_values[dropdown_menu_value]

            dropdown_menu_value_wrapper.grid_rowconfigure((0,2), weight=1)
            label_widget = CTkLabel(
                dropdown_menu_value_wrapper,
                text=dropdown_menu_value_text,
                height=0,
                corner_radius=0,
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.value_font_size, weight="normal"),
                anchor="w",
                text_color=self.values_text_color,
            )

            label_widget.grid(row=1, column=0, padx=self.value_ipadx, pady=self.value_ipady, sticky="w")


            bindEnterAndLeaveColor([dropdown_menu_value_wrapper, label_widget], self.values_hovered_bg_color, self.values_bg_color)
            bindButtonPressColor([dropdown_menu_value_wrapper, label_widget], self.values_clicked_bg_color, self.values_bg_color)



            def optimizedCommand(value, _e):
                command(value)
                self._withdraw()

            if IS_LIST_TYPE is True:
                callback = partial(optimizedCommand, dropdown_menu_value_text)
            else:
                callback = partial(optimizedCommand, dropdown_menu_value)

            bindButtonReleaseFunction([dropdown_menu_value_wrapper, label_widget], callback)

            row+=1



    def show(self, dropdown_menu_widget_id):
        if self.hide is False:
            return
        self.wm_attributes("-alpha", 0)



        if self.active_dropdown_menu_widget is not None:
            try:
                self.active_dropdown_menu_widget.grid_remove()
            except:
                pass

        target_data = self.dropdown_menu_widgets[dropdown_menu_widget_id]
        self.attach_widget = target_data.attach_widget

        target_data.widget.grid()
        self.active_dropdown_menu_widget = target_data.widget

        self.geometry("{}x{}".format(target_data._settings.geometry_width, target_data._settings.geometry_height))


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
        try:
            self.attach_widget.winfo_toplevel().unbind("<Configure>", self.BIND_CONFIGURE_FUNC_ID)
        except Exception:
            pass
        try:
            self.attach_widget.unbind("<Unmap>", self.BIND_UNMAP_FUNC_ID)
        except Exception:
            pass
        try:
            self.attach_widget.winfo_toplevel().unbind("<Button-1>", self.BIND_BUTTON_1_FUNC_ID)
        except Exception:
            pass
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


        self.y_pos = int(self.attach_widget_y_pos + self.attach_widget_height + self.window_additional_y_pos)

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


