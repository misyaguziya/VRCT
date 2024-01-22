from functools import partial
from types import SimpleNamespace
from typing import Union

from customtkinter import CTkFont, CTkFrame, CTkLabel, CTkEntry, CTkSlider, CTkSwitch, CTkCheckBox, CTkProgressBar, CTkImage, CTkRadioButton
from CTkToolTip import *

from vrct_gui.ui_utils import createButtonWithImage, getLatestWidth, createOptionMenuBox, getLatestHeight, bindButtonFunctionAndColor, bindEnterAndLeaveFunction, bindButtonReleaseFunction, bindButtonPressFunction
from vrct_gui import vrct_gui
from utils import isEven, callFunctionIfCallable

SETTING_BOX_COLUMN = 1

class _SettingBoxGenerator():
    def __init__(self, parent_widget, config_window, settings, view_variable):
        self.view_variable = view_variable
        self.config_window = config_window
        self.parent_widget = parent_widget
        self.settings = settings

        self.MAIN_INNER_AREA_MIN_WIDTH = int(self.settings.uism.MAIN_AREA_MIN_WIDTH - self.settings.uism.SB__IPADX)

        self.dropdown_menu_window = vrct_gui.vrct_gui.dropdown_menu_window

    def _createSettingBoxFrame(self, sb__attr_name, for_var_label_text=None, for_var_desc_text=None, expand_label_frame:bool=False):
        self.config_window.sb__widgets[sb__attr_name] = SimpleNamespace()

        setting_box_frame = CTkFrame(self.parent_widget, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)

        # "pady=(0,1)" is for bottom padding. It can be removed(override) when you do like "self.attr_name.grid(row=row, pady=0)"
        setting_box_frame.grid(column=0, padx=0, pady=self.settings.uism.SB__FAKE_BOTTOM_BORDER_SIZE, sticky="ew")
        setting_box_frame.grid_columnconfigure(0, weight=1)


        setting_box_frame_wrapper = CTkFrame(setting_box_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        setting_box_frame_wrapper.grid(row=0, column=0, padx=self.settings.uism.SB__IPADX, pady=self.settings.uism.SB__IPADY, sticky="ew")


        setting_box_frame_wrapper_fix_border = CTkFrame(setting_box_frame, corner_radius=0, width=0, height=0)
        setting_box_frame_wrapper_fix_border.grid(row=1, column=0, sticky="ew")

        setting_box_frame_wrapper_fix_border2 = CTkFrame(setting_box_frame, corner_radius=0, width=0, height=0)
        setting_box_frame_wrapper_fix_border2.grid(row=0, column=1, sticky="ns")



        if for_var_label_text is not None:
            self._setSettingBoxLabels(sb__attr_name, setting_box_frame_wrapper, for_var_label_text, for_var_desc_text, expand_label_frame)
            if expand_label_frame is True:
                setting_box_frame_wrapper.grid_columnconfigure(0, weight=1, minsize=int(self.settings.uism.MAIN_AREA_MIN_WIDTH))
                setting_box_frame_wrapper.grid(columnspan=3)
                return setting_box_frame


        setting_box_frame_wrapper.grid_columnconfigure(0, weight=0, minsize=int(self.settings.uism.MAIN_AREA_MIN_WIDTH / 2))
        setting_box_frame_wrapper.grid_columnconfigure(2, weight=1, minsize=int(self.settings.uism.MAIN_AREA_MIN_WIDTH / 2))




        setting_box_item_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, width=0, height=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        if for_var_label_text is not None:
            setting_box_item_frame.grid(row=0, column=2, padx=0, sticky="nsew")
        else:
            setting_box_item_frame.grid(row=0, columnspan=3, padx=0, sticky="nsew")
        setting_box_item_frame.grid_rowconfigure((0,2), weight=1)
        setting_box_item_frame.grid_columnconfigure(0, weight=1)

        return (setting_box_frame, setting_box_item_frame)

    def _setSettingBoxLabels(self, sb__attr_name, setting_box_frame_wrapper, for_var_label_text, for_var_desc_text=None, expand_label_frame:bool=False):

        setting_box_labels_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        setting_box_labels_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        setting_box_labels_frame.grid_rowconfigure((0,3), weight=1)
        setting_box_label = CTkLabel(
            setting_box_labels_frame,
            textvariable=for_var_label_text,
            anchor="w",
            height=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__LABEL_FONT_SIZE, weight="normal"),
            text_color=self.settings.ctm.LABELS_TEXT_COLOR
        )
        setting_box_label.grid(row=1, column=0, padx=0, pady=0, sticky="ew")
        self.config_window.sb__widgets[sb__attr_name].label_widget = setting_box_label


        if for_var_desc_text is not None:
            setting_box_desc = CTkLabel(
                setting_box_labels_frame,
                textvariable=for_var_desc_text,
                anchor="w",
                justify="left",
                height=0,
                wraplength=int(self.settings.uism.MAIN_AREA_MIN_WIDTH / 2),
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__DESC_FONT_SIZE, weight="normal"),
                text_color=self.settings.ctm.LABELS_DESC_TEXT_COLOR
            )
            if expand_label_frame is True:
                setting_box_desc.configure(wraplength=self.settings.uism.MAIN_AREA_MIN_WIDTH)

            setting_box_desc.grid(row=2, column=0, padx=0, pady=(self.settings.uism.SB__DESC_TOP_PADY,0), sticky="ew")
            self.config_window.additional_widgets.append(setting_box_desc)
            self.config_window.sb__widgets[sb__attr_name].desc_widget=setting_box_desc
        else:
            self.config_window.sb__widgets[sb__attr_name].desc_widget=None


    def createSettingBox_Labels(
            self,
            for_var_label_text,
            labels_attr_name,
            for_var_desc_text=None,
        ):

        setting_box_frame= self._createSettingBoxFrame(labels_attr_name, for_var_label_text, for_var_desc_text, expand_label_frame=True)

        return setting_box_frame



    def createSettingBoxDropdownMenu(
            self,
            for_var_label_text, for_var_desc_text,
            optionmenu_attr_name,
            command,
            dropdown_menu_min_width=None,
            dropdown_menu_values=None,
            variable=None,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(optionmenu_attr_name, for_var_label_text, for_var_desc_text)

        def adjustedCommand(value):
            variable.set(value)
            command(value)


        (option_menu_widget, optionmenu_label_widget, optionmenu_img_widget) = createOptionMenuBox(
            parent_widget=setting_box_item_frame,
            optionmenu_bg_color=self.settings.ctm.SB__OPTIONMENU_BG_COLOR,
            optionmenu_hovered_bg_color=self.settings.ctm.SB__OPTIONMENU_HOVERED_BG_COLOR,
            optionmenu_clicked_bg_color=self.settings.ctm.SB__OPTIONMENU_CLICKED_BG_COLOR,
            optionmenu_ipadx=self.settings.uism.SB__OPTIONMENU_IPADX,
            optionmenu_ipady=self.settings.uism.SB__OPTIONMENU_IPADY,
            optionmenu_padx_between_img=self.settings.uism.SB__OPTIONMENU_IPADX_BETWEEN_IMG,
            optionmenu_min_height=self.settings.uism.SB__OPTIONMENU_MIN_HEIGHT,
            optionmenu_min_width=self.settings.uism.SB__OPTIONMENU_MIN_WIDTH,
            variable=variable,
            font_family=self.settings.FONT_FAMILY,
            font_size=self.settings.uism.SB__OPTION_MENU_FONT_SIZE,
            text_color=self.settings.ctm.LABELS_TEXT_COLOR,
            image_file=self.settings.image_file.ARROW_LEFT.rotate(90),
            image_size=self.settings.uism.SB__OPTIONMENU_IMG_SIZE,
            optionmenu_clicked_command=lambda _e: self.dropdown_menu_window.show(
                dropdown_menu_widget_id=optionmenu_attr_name,
            ),
        )


        self.config_window.sb__widgets[optionmenu_attr_name].optionmenu_box = option_menu_widget
        self.config_window.sb__widgets[optionmenu_attr_name].optionmenu_label_widget = optionmenu_label_widget
        self.config_window.sb__widgets[optionmenu_attr_name].optionmenu_img_widget = optionmenu_img_widget


        option_menu_widget.grid(row=1, column=SETTING_BOX_COLUMN, sticky="e")
        setattr(self.config_window, optionmenu_attr_name, option_menu_widget)

        self.dropdown_menu_window.createDropdownMenuBox(
            dropdown_menu_widget_id=optionmenu_attr_name,
            dropdown_menu_values=dropdown_menu_values,
            command=adjustedCommand,
            wrapper_widget=self.config_window.main_bg_container,
            attach_widget=option_menu_widget,
            dropdown_menu_min_width=dropdown_menu_min_width,
        )

        return setting_box_frame




    def createSettingBoxSwitch(self,
            for_var_label_text, for_var_desc_text,
            switch_attr_name,
            variable,
            command,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(switch_attr_name, for_var_label_text, for_var_desc_text)

        switch_widget = CTkSwitch(
            setting_box_item_frame,
            text=None,
            height=0,
            width=0,
            corner_radius=int(self.settings.uism.SB__SWITCH_BOX_HEIGHT/2),
            border_width=0,
            switch_height=self.settings.uism.SB__SWITCH_BOX_HEIGHT,
            switch_width=self.settings.uism.SB__SWITCH_BOX_WIDTH,
            onvalue=True,
            offvalue=False,
            variable=variable,
            command=command,
            fg_color=self.settings.ctm.SB__SWITCH_BOX_BG_COLOR,
            progress_color=self.settings.ctm.SB__SWITCH_BOX_ACTIVE_BG_COLOR,
            button_color=self.settings.ctm.SB__SWITCH_BOX_BUTTON_COLOR,
            button_hover_color=self.settings.ctm.SB__SWITCH_BOX_BUTTON_HOVERED_COLOR,
        )
        setattr(self.config_window, switch_attr_name, switch_widget)

        self.config_window.sb__widgets[switch_attr_name].switch_box = switch_widget

        switch_widget.grid(row=1, column=SETTING_BOX_COLUMN, sticky="e")

        return setting_box_frame



    def createSettingBoxCheckbox(self,
            for_var_label_text,
            checkbox_attr_name,
            command,
            variable,
            for_var_desc_text=None,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(checkbox_attr_name, for_var_label_text, for_var_desc_text)

        checkbox_widget = CTkCheckBox(
            setting_box_item_frame,
            text=None,
            width=0,
            checkbox_width=self.settings.uism.SB__CHECKBOX_SIZE,
            checkbox_height=self.settings.uism.SB__CHECKBOX_SIZE,
            onvalue=True,
            offvalue=False,
            variable=variable,
            command=command,
            corner_radius=self.settings.uism.SB__CHECKBOX_CORNER_RADIUS,
            border_width=self.settings.uism.SB__CHECKBOX_BORDER_WIDTH,
            border_color=self.settings.ctm.SB__CHECKBOX_BORDER_COLOR,
            hover_color=self.settings.ctm.SB__CHECKBOX_HOVER_COLOR,
            checkmark_color=self.settings.ctm.SB__CHECKBOX_CHECKMARK_COLOR,
            fg_color=self.settings.ctm.SB__CHECKBOX_CHECKED_COLOR,
        )
        setattr(self.config_window, checkbox_attr_name, checkbox_widget)

        self.config_window.sb__widgets[checkbox_attr_name].checkbox = checkbox_widget

        checkbox_widget.grid(row=1, column=SETTING_BOX_COLUMN, sticky="e")

        return setting_box_frame



    # 3 Options
    def createSettingBoxRadioButtons(
            self,
            for_var_label_text, for_var_desc_text,
            radio_button_attr_name,
            variable,
            command,
            radiobutton_keys_values=dict,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(radio_button_attr_name, for_var_label_text, for_var_desc_text)

        row=0
        for key, value in radiobutton_keys_values.items():
            radiobutton_wrapper = CTkFrame(setting_box_item_frame, corner_radius=6, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0, cursor="hand2")
            radiobutton_wrapper.grid(row=row, column=0, sticky="ew")
            row+=1

            radiobutton_wrapper.grid_rowconfigure((0,2), weight=1)
            setting_box_radio_button = CTkRadioButton(
                radiobutton_wrapper,
                textvariable=value,
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__RADIO_BUTTON_FONT_SIZE, weight="normal"),
                variable=variable,
                value=key,
                text_color=self.settings.ctm.SB__RADIOBUTTON_TEXT_COLOR,
                fg_color=self.settings.ctm.SB__RADIOBUTTON_SELECTED_COLOR,
                border_color=self.settings.ctm.SB__RADIOBUTTON_BORDER_COLOR,
                hover=False
            )
            setting_box_radio_button.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

            if key == variable.get():
                setting_box_radio_button.select()

            setting_box_radio_button._canvas.unbind("<Button-1>")
            setting_box_radio_button._text_label.unbind("<Button-1>")
            setting_box_radio_button._text_label.grid(padx=(10,0))


            def buttonPressedFunction(radiobutton_wrapper, radiobutton_widget, _e):
                radiobutton_wrapper.configure(fg_color=self.settings.ctm.SB__RADIOBUTTON_BG_CLICKED_COLOR)

            def buttonReleasedFunction(radiobutton_wrapper, radiobutton_widget, _e):
                radiobutton_wrapper.configure(fg_color=self.settings.ctm.SB__RADIOBUTTON_BG_HOVERED_COLOR)
                radiobutton_widget.select()
                command()

            def enterFunction(radiobutton_wrapper, _e):
                radiobutton_wrapper.configure(fg_color=self.settings.ctm.SB__RADIOBUTTON_BG_HOVERED_COLOR)

            def leaveFunction(radiobutton_wrapper, _e):
                radiobutton_wrapper.configure(fg_color=self.settings.ctm.SB__BG_COLOR)


            bindEnterAndLeaveFunction(
                target_widgets=[radiobutton_wrapper, setting_box_radio_button, setting_box_radio_button._bg_canvas],
                enterFunction=partial(enterFunction, radiobutton_wrapper),
                leaveFunction=partial(leaveFunction, radiobutton_wrapper)
            )

            bindButtonPressFunction(
                target_widgets=[radiobutton_wrapper, setting_box_radio_button, setting_box_radio_button._bg_canvas],
                buttonPressedFunction=partial(buttonPressedFunction, radiobutton_wrapper, setting_box_radio_button)
            )

            bindButtonReleaseFunction(
                target_widgets=[radiobutton_wrapper, setting_box_radio_button, setting_box_radio_button._bg_canvas],
                buttonReleasedFunction=partial(buttonReleasedFunction, radiobutton_wrapper, setting_box_radio_button)
            )


        return setting_box_frame



    def createSettingBoxAutoExportMessageLogs(
            self,
            for_var_label_text, for_var_desc_text,
            checkbox_attr_name,
            checkbox_command,
            button_command,
            variable,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(checkbox_attr_name, for_var_label_text, for_var_desc_text)



        all_wrapper = CTkFrame(setting_box_item_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        all_wrapper.grid(row=1, column=0, sticky="ew")

        all_wrapper.grid_columnconfigure(1, weight=1)




        button_widget = createButtonWithImage(
            parent_widget=all_wrapper,
            button_fg_color=self.settings.ctm.SB__BUTTON_COLOR,
            button_enter_color=self.settings.ctm.SB__BUTTON_HOVERED_COLOR,
            button_clicked_color=self.settings.ctm.SB__BUTTON_CLICKED_COLOR,
            button_image_file=self.settings.image_file.FOLDER_OPEN_ICON,
            button_image_size=self.settings.uism.SB__BUTTON_ICON_SIZE,
            corner_radius=self.settings.uism.SB__BUTTON_CORNER_RADIUS,
            button_ipadxy=self.settings.uism.SB__BUTTON_IPADXY,
            button_command=button_command,
        )
        button_widget.grid(row=0, column=0, padx=0, sticky="w")



        checkbox_widget = CTkCheckBox(
            all_wrapper,
            text=None,
            width=0,
            checkbox_width=self.settings.uism.SB__CHECKBOX_SIZE,
            checkbox_height=self.settings.uism.SB__CHECKBOX_SIZE,
            onvalue=True,
            offvalue=False,
            variable=variable,
            command=checkbox_command,
            corner_radius=self.settings.uism.SB__CHECKBOX_CORNER_RADIUS,
            border_width=self.settings.uism.SB__CHECKBOX_BORDER_WIDTH,
            border_color=self.settings.ctm.SB__CHECKBOX_BORDER_COLOR,
            hover_color=self.settings.ctm.SB__CHECKBOX_HOVER_COLOR,
            checkmark_color=self.settings.ctm.SB__CHECKBOX_CHECKMARK_COLOR,
            fg_color=self.settings.ctm.SB__CHECKBOX_CHECKED_COLOR,
        )
        setattr(self.config_window, checkbox_attr_name, checkbox_widget)

        checkbox_widget.grid(row=0, column=2, sticky="e")

        return setting_box_frame






    def createSettingBoxSlider(
            self,
            for_var_label_text, for_var_desc_text,
            slider_attr_name,
            slider_range,
            command,
            variable,
            slider_number_of_steps: Union[int,
            None] = None,
            slider_bind__ButtonPress=None,
            slider_bind__ButtonRelease=None,
            sliderTooltipFormatter=None,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(slider_attr_name, for_var_label_text, for_var_desc_text)

        if slider_number_of_steps is None:
            slider_number_of_steps = int(slider_range[1] - slider_range[0])

        slider_widget = CTkSlider(
            setting_box_item_frame,
            width=self.settings.uism.SB__SLIDER_WIDTH,
            height=self.settings.uism.SB__SLIDER_HEIGHT,
            from_=slider_range[0],
            to=slider_range[1],
            number_of_steps=slider_number_of_steps,
            fg_color=self.settings.ctm.SB__SLIDER_BG_COLOR,
            progress_color=self.settings.ctm.SB__SLIDER_PROGRESS_BG_COLOR,
            button_color=self.settings.ctm.SB__SLIDER_BUTTON_COLOR,
            button_hover_color=self.settings.ctm.SB__SLIDER_BUTTON_HOVERED_COLOR,
            command=command,
            variable=variable,
        )
        setattr(self.config_window, slider_attr_name, slider_widget)

        def getSliderValueWAfterFormatting():
            return sliderTooltipFormatter(variable.get()) if sliderTooltipFormatter else variable.get()



        slider_tooltip = CTkToolTip(
            slider_widget,
            message=getSliderValueWAfterFormatting(),
            delay=0,
            bg_color=self.settings.ctm.SB__SLIDER_TOOLTIP_BG_COLOR,
            corner_radius=0,
            text_color=self.settings.ctm.SB__SLIDER_TOOLTIP_TEXT_COLOR,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__SLIDER_TOOLTIP_FONT_SIZE, weight="normal"),
        )

        slider_widget.grid(row=1, column=SETTING_BOX_COLUMN, sticky="e")

        if slider_bind__ButtonPress is not None:
            def adjusted_slider_bind__ButtonPress(_e):
                command(_e)
                slider_tooltip.configure(message=getSliderValueWAfterFormatting())
                slider_bind__ButtonPress()
            slider_widget.configure(command=adjusted_slider_bind__ButtonPress)

        if slider_bind__ButtonRelease is not None:
            def adjusted_slider_bind__ButtonRelease(_e):
                slider_bind__ButtonRelease()
            slider_widget.bind("<ButtonRelease>", adjusted_slider_bind__ButtonRelease, "+")

        return setting_box_frame




    def createSettingBoxProgressbarXSlider(
            self,
            command, progressbar_x_slider_attr_name,
            entry_attr_name, entry_bind__FocusOut,
            slider_attr_name, slider_range,
            progressbar_attr_name,
            passive_button_attr_name, passive_button_command,
            active_button_attr_name, active_button_command,
            disabled_button_attr_name, disabled_button_image_file,
            button_image_file,

            entry_variable,
            slider_variable,

            slider_number_of_steps: Union[int, None] = None,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(progressbar_x_slider_attr_name)

        def adjusted_command__for_entry_bind__Any_KeyRelease(e):
            command(e.widget.get())
        def adjusted_command__for_slider(value):
            command(value)

        setting_box_item_frame.grid_columnconfigure((0,2), weight=0)
        setting_box_item_frame.grid_columnconfigure(1, weight=1)
        entry_widget = CTkEntry(
            setting_box_item_frame,
            text_color=self.settings.ctm.SB__ENTRY_TEXT_COLOR,
            fg_color=self.settings.ctm.SB__ENTRY_BG_COLOR,
            border_color=self.settings.ctm.SB__ENTRY_BORDER_COLOR,
            width=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__ENTRY_WIDTH,
            height=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__ENTRY_HEIGHT,
            textvariable=entry_variable,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__ENTRY_FONT_SIZE, weight="normal"),
        )

        entry_widget.bind("<Any-KeyRelease>", adjusted_command__for_entry_bind__Any_KeyRelease)
        if entry_bind__FocusOut is not None:
            entry_widget.bind("<FocusOut>", entry_bind__FocusOut, "+")

        entry_widget.grid(row=1, column=2, padx=0, pady=0, sticky="e")
        setattr(self.config_window, entry_attr_name, entry_widget)



        # at least 2px is needed otherwise the slider button is gonna broken.
        SLIDER_BORDER_WIDTH = max(2,self.settings.uism.SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_LENGTH)
        SLIDER_BUTTON_LENGTH = int(SLIDER_BORDER_WIDTH/2)
        slider_widget = CTkSlider(
            setting_box_item_frame,
            from_=slider_range[0],
            to=slider_range[1],
            number_of_steps=slider_number_of_steps,
            command=adjusted_command__for_slider,
            variable=slider_variable,
            height=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__SLIDER_HEIGHT,
            border_width=0,
            button_length=SLIDER_BORDER_WIDTH,
            button_corner_radius=SLIDER_BUTTON_LENGTH,
            corner_radius=0,
            button_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_COLOR,
            button_hover_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__SLIDER_BUTTON_HOVERED_COLOR,
            fg_color=self.settings.ctm.SB__BG_COLOR,
            progress_color=self.settings.ctm.SB__BG_COLOR,
            border_color=self.settings.ctm.SB__BG_COLOR,
        )
        slider_widget.grid(row=1, column=1, padx=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BAR_PADX, sticky="ew")
        setattr(self.config_window, slider_attr_name, slider_widget)




        progressbar_widget = CTkProgressBar(
            setting_box_item_frame,
            height=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_HEIGHT,
            corner_radius=0,
            fg_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_BG_COLOR,
            progress_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_PROGRESS_BG_COLOR,
        )
        setattr(self.config_window, progressbar_attr_name, progressbar_widget)
        progressbar_widget.grid(row=1, column=1, padx=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BAR_PADX, sticky="ew")
        progressbar_widget.set(0)




        passive_button_wrapper = self._createPassiveButtonForProgressbarXSlider(setting_box_item_frame, passive_button_command, button_image_file)
        setattr(self.config_window, passive_button_attr_name, passive_button_wrapper)

        disabled_button_wrapper = self._createDisabledButtonForProgressbarXSlider(setting_box_item_frame, disabled_button_image_file)
        setattr(self.config_window, disabled_button_attr_name, disabled_button_wrapper)

        active_button_wrapper = self._createActiveButtonForProgressbarXSlider(setting_box_item_frame, active_button_command, button_image_file)
        setattr(self.config_window, active_button_attr_name, active_button_wrapper)

        passive_button_wrapper.grid(row=1, column=0, padx=0, sticky="w")
        passive_button_wrapper.configure(corner_radius=int(getLatestWidth(passive_button_wrapper)/2))

        disabled_button_wrapper.grid(row=1, column=0, padx=0, sticky="w")
        disabled_button_wrapper.configure(corner_radius=int(getLatestWidth(passive_button_wrapper)/2))

        active_button_wrapper.grid(row=1, column=0, padx=0, sticky="w")
        active_button_wrapper.configure(corner_radius=int(getLatestWidth(passive_button_wrapper)/2))

        passive_button_wrapper.grid_remove()
        disabled_button_wrapper.grid_remove()
        active_button_wrapper.grid_remove()

        passive_button_wrapper.grid()
        return setting_box_frame




    def createSettingBoxEntry(self,
            for_var_label_text, for_var_desc_text,
            entry_attr_name,
            entry_width,
            entry_textvariable,
            entry_bind__Any_KeyRelease,
            entry_bind__FocusOut=None,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(entry_attr_name, for_var_label_text, for_var_desc_text)

        def adjusted_command__for_entry_bind__Any_KeyRelease(e):
            entry_bind__Any_KeyRelease(e.widget.get())

        entry_widget = CTkEntry(
            setting_box_item_frame,
            text_color=self.settings.ctm.SB__ENTRY_TEXT_COLOR,
            fg_color=self.settings.ctm.SB__ENTRY_BG_COLOR,
            border_color=self.settings.ctm.SB__ENTRY_BORDER_COLOR,
            width=entry_width,
            height=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__ENTRY_HEIGHT,
            textvariable=entry_textvariable,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__ENTRY_FONT_SIZE, weight="normal"),
        )
        entry_widget.bind("<Any-KeyRelease>", adjusted_command__for_entry_bind__Any_KeyRelease)
        setattr(self.config_window, entry_attr_name, entry_widget)


        entry_widget.grid(row=1, column=SETTING_BOX_COLUMN, sticky="e")

        if entry_bind__FocusOut is not None:
            entry_widget.bind("<FocusOut>", entry_bind__FocusOut, "+")

        return setting_box_frame





    def createSettingBoxMessageFormatEntries_WithTranslation(self,
            base_entry_attr_name,
            entry_textvariable_0,
            entry_textvariable_1,
            entry_textvariable_2,
            textvariable_0,
            textvariable_1,
            example_label_textvariable,
            swap_button_command,
            entry_bind__Any_KeyRelease,
            entry_bind__FocusOut=None,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(base_entry_attr_name)


        all_wrapper = CTkFrame(setting_box_item_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        all_wrapper.grid(row=1, column=0, sticky="ew")

        all_wrapper.grid_columnconfigure(0, weight=1)


        example_box_wrapper = CTkFrame(all_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        example_box_wrapper.grid(row=0, column=0, pady=self.settings.uism.SB__MESSAGE_FORMAT__ENTRIES_BOTTOM_PADY, sticky="ew")

        entries_wrapper = CTkFrame(all_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        entries_wrapper.grid(row=1, column=0, pady=self.settings.uism.SB__MESSAGE_FORMAT__ENTRIES_BOTTOM_PADY, sticky="ew")

        swap_button_wrapper = CTkFrame(all_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        swap_button_wrapper.grid(row=2, column=0, sticky="e")





        example_box_wrapper.grid_columnconfigure((0,2), weight=1)
        example_frame_widget = CTkFrame(example_box_wrapper, corner_radius=self.settings.uism.SB__MESSAGE_FORMAT__EXAMPLE_CORNER_RADIUS, fg_color=self.settings.ctm.SB__MESSAGE_FORMAT__EXAMPLE_BG_COLOR, width=0, height=0)
        example_frame_widget.grid(row=0, column=1)

        example_frame_widget.grid_rowconfigure((0,2), weight=1)
        example_frame_widget.grid_columnconfigure((0,2), weight=1)
        example_label_widget = CTkLabel(
            example_frame_widget,
            textvariable=example_label_textvariable,
            anchor="center",
            justify="center",
            wraplength=self.settings.uism.SB__MESSAGE_FORMAT__EXAMPLE_WRAP_LENGTH,
            height=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__MESSAGE_FORMAT__REQUIRED_TEXT_FONT_SIZE, weight="normal"),
            text_color=self.settings.ctm.SB__MESSAGE_FORMAT__EXAMPLE_TEXT_COLOR,
        )
        example_label_widget.grid(row=1, column=1, padx=self.settings.uism.SB__MESSAGE_FORMAT__EXAMPLE_IPADXY, pady=self.settings.uism.SB__MESSAGE_FORMAT__EXAMPLE_IPADXY, sticky="ew")

        self.config_window.additional_widgets.append(example_box_wrapper)




        entry_textvariables = [entry_textvariable_0, entry_textvariable_1, entry_textvariable_2]
        for i in range(3):
            entry_widget = CTkEntry(
                entries_wrapper,
                text_color=self.settings.ctm.SB__ENTRY_TEXT_COLOR,
                fg_color=self.settings.ctm.SB__ENTRY_BG_COLOR,
                border_color=self.settings.ctm.SB__ENTRY_BORDER_COLOR,
                height=self.settings.uism.SB__MESSAGE_FORMAT__ENTRY_HEIGHT,
                textvariable=entry_textvariables[i],
                justify="center",
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__ENTRY_FONT_SIZE, weight="normal"),
            )
            setattr(self.config_window, base_entry_attr_name + "_" + str(i), entry_widget)



            if entry_bind__FocusOut is not None:
                entry_widget.bind("<FocusOut>", entry_bind__FocusOut, "+")


        label_frame_widget_0 = CTkFrame(entries_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)

        label_frame_widget_0.grid_rowconfigure((0,2), weight=1)
        label_frame_widget_0.grid_columnconfigure(0, weight=1)
        label_widget_0 = CTkLabel(
            label_frame_widget_0,
            textvariable=textvariable_0,
            anchor="center",
            height=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__MESSAGE_FORMAT__REQUIRED_TEXT_FONT_SIZE, weight="normal"),
            text_color=self.settings.ctm.LABELS_TEXT_COLOR
        )
        label_widget_0.grid(row=1, column=0, padx=0, pady=0, sticky="ew")


        label_frame_widget_1 = CTkFrame(entries_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)

        label_frame_widget_1.grid_rowconfigure((0,2), weight=1)
        label_frame_widget_1.grid_columnconfigure(0, weight=1)
        label_widget_1 = CTkLabel(
            label_frame_widget_1,
            textvariable=textvariable_1,
            anchor="center",
            height=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__MESSAGE_FORMAT__REQUIRED_TEXT_FONT_SIZE, weight="normal"),
            text_color=self.settings.ctm.LABELS_TEXT_COLOR
        )
        label_widget_1.grid(row=1, column=0, padx=0, pady=0, sticky="ew")


        entries_wrapper.grid_columnconfigure((0,2,4), weight=1)
        entries_wrapper.grid_columnconfigure((1,3), weight=0, uniform="message_format_fixed_labels")

        entry_widget_0 = getattr(self.config_window, base_entry_attr_name+"_0")
        entry_widget_1 = getattr(self.config_window, base_entry_attr_name+"_1")
        entry_widget_2 = getattr(self.config_window, base_entry_attr_name+"_2")
        entry_widget_0.grid(row=0, column=0, sticky="ew")
        entry_widget_1.grid(row=0, column=2, sticky="ew")
        entry_widget_2.grid(row=0, column=4, sticky="ew")
        label_frame_widget_0.grid(row=0, column=1, padx=self.settings.uism.SB__MESSAGE_FORMAT__REQUIRED_TEXT_PADX, sticky="ew")
        label_frame_widget_1.grid(row=0, column=3, padx=self.settings.uism.SB__MESSAGE_FORMAT__REQUIRED_TEXT_PADX, sticky="ew")

        def adjusted_command__for_entry_bind__Any_KeyRelease(_e):
            message_format = entry_widget_0.get() + textvariable_0.get() + entry_widget_1.get() + textvariable_1.get() + entry_widget_2.get()
            entry_bind__Any_KeyRelease(message_format)


        entry_widget_0.bind("<Any-KeyRelease>", adjusted_command__for_entry_bind__Any_KeyRelease)
        entry_widget_1.bind("<Any-KeyRelease>", adjusted_command__for_entry_bind__Any_KeyRelease)
        entry_widget_2.bind("<Any-KeyRelease>", adjusted_command__for_entry_bind__Any_KeyRelease)






        swap_button = CTkFrame(swap_button_wrapper, corner_radius=self.settings.uism.BUTTONS_CORNER_RADIUS, fg_color=self.settings.ctm.SB__MESSAGE_FORMAT__SWAP_BUTTON_COLOR, cursor="hand2")
        swap_button.grid(row=0, column=2, sticky="ew")


        swap_button.grid_columnconfigure(0, weight=1)
        swap_button_label_wrapper = CTkFrame(swap_button, corner_radius=0, fg_color=self.settings.ctm.SB__MESSAGE_FORMAT__SWAP_BUTTON_COLOR)
        swap_button_label_wrapper.grid(row=0, column=0, padx=self.settings.uism.SB__MESSAGE_FORMAT__SWAP_BUTTON_IPADX, pady=self.settings.uism.SB__MESSAGE_FORMAT__SWAP_BUTTON_IPADY, sticky="ew")


        swap_button_label_wrapper.grid_columnconfigure((0,4), weight=1)
        swap_button_label_wrapper.grid_rowconfigure((0,2), weight=1)

        swap_button_label_0 = CTkLabel(
            swap_button_label_wrapper,
            textvariable=textvariable_0,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__MESSAGE_FORMAT__SWAP_BUTTON_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.LABELS_TEXT_COLOR,
        )
        swap_button_label_0.grid(row=1, column=1)

        swap_button_both_direction_arrow_img = CTkLabel(
            swap_button_label_wrapper,
            text=None,
            height=0,
            corner_radius=0,
            image=CTkImage((self.settings.image_file.SWAP_ICON), size=self.settings.uism.SB__MESSAGE_FORMAT__SWAP_BUTTON_ARROWS_IMG_SIZE),
            anchor="w",
            text_color=self.settings.ctm.LABELS_TEXT_COLOR,
        )
        swap_button_both_direction_arrow_img.grid(row=1, column=2, padx=self.settings.uism.SB__MESSAGE_FORMAT__SWAP_TEXT_PADX)

        swap_button_label_1 = CTkLabel(
            swap_button_label_wrapper,
            textvariable=textvariable_1,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__MESSAGE_FORMAT__SWAP_BUTTON_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.LABELS_TEXT_COLOR,
        )
        swap_button_label_1.grid(row=1, column=3)

        bindButtonFunctionAndColor(
            target_widgets=[
                swap_button,
                swap_button_label_wrapper,
                swap_button_label_0,
                swap_button_both_direction_arrow_img,
                swap_button_label_1,
            ],
            enter_color=self.settings.ctm.SB__MESSAGE_FORMAT__SWAP_BUTTON_HOVERED_COLOR,
            leave_color=self.settings.ctm.SB__MESSAGE_FORMAT__SWAP_BUTTON_COLOR,
            clicked_color=self.settings.ctm.SB__MESSAGE_FORMAT__SWAP_BUTTON_CLICKED_COLOR,
            buttonReleasedFunction=swap_button_command,
        )


        return setting_box_frame




    def createSettingBoxMessageFormatEntries(self,
            base_entry_attr_name,
            entry_textvariable_0,
            entry_textvariable_1,
            textvariable_0,
            example_label_textvariable,
            entry_bind__Any_KeyRelease,
            entry_bind__FocusOut=None,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(base_entry_attr_name)


        all_wrapper = CTkFrame(setting_box_item_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        all_wrapper.grid(row=1, column=0, sticky="ew")

        all_wrapper.grid_columnconfigure(0, weight=1)


        example_box_wrapper = CTkFrame(all_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        example_box_wrapper.grid(row=0, column=0, pady=self.settings.uism.SB__MESSAGE_FORMAT__ENTRIES_BOTTOM_PADY, sticky="ew")

        entries_wrapper = CTkFrame(all_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        entries_wrapper.grid(row=1, column=0, pady=self.settings.uism.SB__MESSAGE_FORMAT__ENTRIES_BOTTOM_PADY, sticky="ew")




        example_box_wrapper.grid_columnconfigure((0,2), weight=1)
        example_frame_widget = CTkFrame(example_box_wrapper, corner_radius=self.settings.uism.SB__MESSAGE_FORMAT__EXAMPLE_CORNER_RADIUS, fg_color=self.settings.ctm.SB__MESSAGE_FORMAT__EXAMPLE_BG_COLOR, width=0, height=0)
        example_frame_widget.grid(row=0, column=1)

        example_frame_widget.grid_rowconfigure((0,2), weight=1)
        example_frame_widget.grid_columnconfigure((0,2), weight=1)
        example_label_widget = CTkLabel(
            example_frame_widget,
            textvariable=example_label_textvariable,
            anchor="center",
            justify="center",
            wraplength=self.settings.uism.SB__MESSAGE_FORMAT__EXAMPLE_WRAP_LENGTH,
            height=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__MESSAGE_FORMAT__REQUIRED_TEXT_FONT_SIZE, weight="normal"),
            text_color=self.settings.ctm.SB__MESSAGE_FORMAT__EXAMPLE_TEXT_COLOR,
        )
        example_label_widget.grid(row=1, column=1, padx=self.settings.uism.SB__MESSAGE_FORMAT__EXAMPLE_IPADXY, pady=self.settings.uism.SB__MESSAGE_FORMAT__EXAMPLE_IPADXY, sticky="ew")

        self.config_window.additional_widgets.append(example_box_wrapper)




        entry_textvariables = [entry_textvariable_0, entry_textvariable_1]
        for i in range(2):
            entry_widget = CTkEntry(
                entries_wrapper,
                text_color=self.settings.ctm.SB__ENTRY_TEXT_COLOR,
                fg_color=self.settings.ctm.SB__ENTRY_BG_COLOR,
                border_color=self.settings.ctm.SB__ENTRY_BORDER_COLOR,
                height=self.settings.uism.SB__MESSAGE_FORMAT__ENTRY_HEIGHT,
                textvariable=entry_textvariables[i],
                justify="center",
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__ENTRY_FONT_SIZE, weight="normal"),
            )
            setattr(self.config_window, base_entry_attr_name + "_" + str(i), entry_widget)



            if entry_bind__FocusOut is not None:
                entry_widget.bind("<FocusOut>", entry_bind__FocusOut, "+")


        label_frame_widget_0 = CTkFrame(entries_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)

        label_frame_widget_0.grid_rowconfigure((0,2), weight=1)
        label_frame_widget_0.grid_columnconfigure(0, weight=1)
        label_widget_0 = CTkLabel(
            label_frame_widget_0,
            textvariable=textvariable_0,
            anchor="center",
            height=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__MESSAGE_FORMAT__REQUIRED_TEXT_FONT_SIZE, weight="normal"),
            text_color=self.settings.ctm.LABELS_TEXT_COLOR
        )
        label_widget_0.grid(row=1, column=0, padx=0, pady=0, sticky="ew")





        entries_wrapper.grid_columnconfigure((0,2), weight=1)
        entries_wrapper.grid_columnconfigure(1, weight=0)

        entry_widget_0 = getattr(self.config_window, base_entry_attr_name+"_0")
        entry_widget_1 = getattr(self.config_window, base_entry_attr_name+"_1")
        entry_widget_0.grid(row=0, column=0, sticky="ew")
        entry_widget_1.grid(row=0, column=2, sticky="ew")
        label_frame_widget_0.grid(row=0, column=1, padx=self.settings.uism.SB__MESSAGE_FORMAT__REQUIRED_TEXT_PADX, sticky="ew")

        def adjusted_command__for_entry_bind__Any_KeyRelease(_e):
            message_format = entry_widget_0.get() + textvariable_0.get() + entry_widget_1.get()
            entry_bind__Any_KeyRelease(message_format)


        entry_widget_0.bind("<Any-KeyRelease>", adjusted_command__for_entry_bind__Any_KeyRelease)
        entry_widget_1.bind("<Any-KeyRelease>", adjusted_command__for_entry_bind__Any_KeyRelease)



        return setting_box_frame



    def createSettingBoxButtonWithImage(
            self,
            for_var_label_text, for_var_desc_text,
            button_attr_name,
            button_image,
            button_command,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(button_attr_name, for_var_label_text, for_var_desc_text)


        button_with_image_widget = createButtonWithImage(
            parent_widget=setting_box_item_frame,
            button_fg_color=self.settings.ctm.SB__BUTTON_COLOR,
            button_enter_color=self.settings.ctm.SB__BUTTON_HOVERED_COLOR,
            button_clicked_color=self.settings.ctm.SB__BUTTON_CLICKED_COLOR,
            button_image_file=button_image,
            button_image_size=self.settings.uism.SB__BUTTON_ICON_SIZE,
            corner_radius=self.settings.uism.SB__BUTTON_CORNER_RADIUS,
            button_ipadxy=self.settings.uism.SB__OPEN_CONFIG_FILE_BUTTON_IPADXY,
            button_command=button_command,
        )
        button_with_image_widget.grid(row=1, column=SETTING_BOX_COLUMN, sticky="e")

        return setting_box_frame




    def createSettingBoxArrowSwitch(
            self,
            for_var_label_text, for_var_desc_text,
            arrow_switch_attr_name,
            open_command,
            close_command,
            var_switch_desc=None,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(arrow_switch_attr_name, for_var_label_text, for_var_desc_text)

        ARROW_BUTTON_COLUMN = SETTING_BOX_COLUMN

        if var_switch_desc is not None:
            label_widget = CTkLabel(
                setting_box_item_frame,
                textvariable=var_switch_desc,
                height=0,
                corner_radius=0,
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__ARROW_SWITCH_DESC_FONT_SIZE, weight="normal"),
                anchor="w",
                text_color=self.settings.ctm.LABELS_DESC_TEXT_COLOR,
            )

            label_widget.grid(row=1, column=SETTING_BOX_COLUMN)
            ARROW_BUTTON_COLUMN = SETTING_BOX_COLUMN + 1


        for_opening_button_wrapper = createButtonWithImage(
            parent_widget=setting_box_item_frame,
            button_fg_color=self.settings.ctm.SB__BUTTON_COLOR,
            button_enter_color=self.settings.ctm.SB__BUTTON_HOVERED_COLOR,
            button_clicked_color=self.settings.ctm.SB__BUTTON_CLICKED_COLOR,
            button_image_file=self.settings.image_file.ARROW_LEFT.rotate(270),
            button_image_size=self.settings.uism.SB__BUTTON_ICON_SIZE,
            corner_radius=self.settings.uism.SB__BUTTON_CORNER_RADIUS,
            button_ipadxy=self.settings.uism.SB__BUTTON_IPADXY,
            button_command=open_command,
        )
        for_opening_button_wrapper.grid(row=1, column=ARROW_BUTTON_COLUMN, padx=self.settings.uism.SB__ARROW_SWITCH_LEFT_PADX, sticky="e")

        self.config_window.sb__widgets[arrow_switch_attr_name].arrow_switch_open = for_opening_button_wrapper

        for_closing_button_wrapper = createButtonWithImage(
            parent_widget=setting_box_item_frame,
            button_fg_color=self.settings.ctm.SB__BUTTON_COLOR,
            button_enter_color=self.settings.ctm.SB__BUTTON_HOVERED_COLOR,
            button_clicked_color=self.settings.ctm.SB__BUTTON_CLICKED_COLOR,
            button_image_file=self.settings.image_file.ARROW_LEFT.rotate(90),
            button_image_size=self.settings.uism.SB__BUTTON_ICON_SIZE,
            corner_radius=self.settings.uism.SB__BUTTON_CORNER_RADIUS,
            button_ipadxy=self.settings.uism.SB__BUTTON_IPADXY,
            button_command=close_command,
        )
        for_closing_button_wrapper.grid(row=1, column=ARROW_BUTTON_COLUMN, padx=self.settings.uism.SB__ARROW_SWITCH_LEFT_PADX, sticky="e")
        for_closing_button_wrapper.grid_remove()

        self.config_window.sb__widgets[arrow_switch_attr_name].arrow_switch_close = for_closing_button_wrapper


        return setting_box_frame



    # I've added it for the word filter, but it's not currently generalized. If you want to use it in the same way elsewhere, it will require refactoring.
    def createSettingBoxAddAndDeleteAbleList(
            self,
            add_and_delete_able_list_attr_name,
            entry_attr_name,
            entry_width,
            mic_word_filter_list,
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(add_and_delete_able_list_attr_name)

        self.config_window.sb__widgets[add_and_delete_able_list_attr_name].items = []


        list_container = CTkFrame(setting_box_item_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        list_container.grid(row=1, column=0, sticky="nsew")


        max_width = int(self.MAIN_INNER_AREA_MIN_WIDTH - (self.settings.uism.SB__IPADX*2))

        def addValues(mic_word_filter_list, mic_word_filter_item_row_wrapper, accumulated_labels_width, row, column):
            for mic_word_filter_item in mic_word_filter_list:
                mic_word_filter_item_wrapper = self._createValue(add_and_delete_able_list_attr_name, mic_word_filter_item_row_wrapper, row, column, mic_word_filter_item)

                if int(accumulated_labels_width + getLatestWidth(mic_word_filter_item_wrapper) + self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_LEFT_PADX[1]) >= max_width:
                    accumulated_labels_width = 0
                    column = 0
                    row += 1
                    mic_word_filter_item_wrapper.destroy()
                    mic_word_filter_item_row_wrapper = self._createRowFrame(list_container, row)
                    mic_word_filter_item_wrapper = self._createValue(add_and_delete_able_list_attr_name, mic_word_filter_item_row_wrapper, row, column, mic_word_filter_item)
                    column += 1
                else:
                    column += 1

                accumulated_labels_width += int(getLatestWidth(mic_word_filter_item_wrapper) + self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_LEFT_PADX[1])



            return mic_word_filter_item_row_wrapper, accumulated_labels_width, row, column

        accumulated_labels_width = 0
        row=0
        column=0
        mic_word_filter_item_row_wrapper = self._createRowFrame(list_container, row)


        mic_word_filter_list = self.view_variable.MIC_WORD_FILTER_LIST

        mic_word_filter_item_row_wrapper, accumulated_labels_width, row, column = addValues(mic_word_filter_list, mic_word_filter_item_row_wrapper, accumulated_labels_width, row, column)


        self.config_window.sb__widgets[add_and_delete_able_list_attr_name].mic_word_filter_item_row_wrapper = mic_word_filter_item_row_wrapper
        self.config_window.sb__widgets[add_and_delete_able_list_attr_name].accumulated_labels_width = accumulated_labels_width
        self.config_window.sb__widgets[add_and_delete_able_list_attr_name].last_row = row
        self.config_window.sb__widgets[add_and_delete_able_list_attr_name].last_column = column
        self.config_window.sb__widgets[add_and_delete_able_list_attr_name].addValues = lambda values, mic_word_filter_item_row_wrapper, accumulated_labels_width, last_row, last_column: addValues(values, mic_word_filter_item_row_wrapper, accumulated_labels_width, last_row, last_column)


        entry_and_add_button_wrapper = CTkFrame(setting_box_item_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        entry_and_add_button_wrapper.grid(row=2, column=0, pady=(self.settings.uism.SB__IPADY, 0), sticky="ew")

        entry_and_add_button_wrapper.grid_columnconfigure((0,3), weight=1)



        entry_widget = CTkEntry(
            entry_and_add_button_wrapper,
            text_color=self.settings.ctm.SB__ENTRY_TEXT_COLOR,
            fg_color=self.settings.ctm.SB__ENTRY_BG_COLOR,
            border_color=self.settings.ctm.SB__ENTRY_BORDER_COLOR,
            width=entry_width,
            placeholder_text="AAA or AAA,BBB,CCC",
            height=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__ENTRY_HEIGHT,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__ENTRY_FONT_SIZE, weight="normal"),
        )
        setattr(self.config_window, entry_attr_name, entry_widget)

        entry_widget.grid(row=0, column=1, sticky="ew")



        add_button = CTkFrame(entry_and_add_button_wrapper, corner_radius=self.settings.uism.BUTTONS_CORNER_RADIUS, fg_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_COLOR, cursor="hand2")
        add_button.grid(row=0, column=2, padx=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_LEFT_PADX, sticky="ew")


        add_button.grid_columnconfigure(0, weight=1)
        add_button_label_wrapper = CTkFrame(add_button, corner_radius=0, fg_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_COLOR)
        add_button_label_wrapper.grid(row=0, column=0, padx=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_IPADX, pady=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_IPADY, sticky="ew")

        add_button_label_wrapper.grid_columnconfigure((0,2), weight=1)
        add_button_label = CTkLabel(
            add_button_label_wrapper,
            textvariable=self.view_variable.VAR_LABEL_MIC_WORD_FILTER_ADD_BUTTON,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.LABELS_TEXT_COLOR,
        )
        add_button_label.grid(row=0, column=1)


        def adjustedCommand():
            callFunctionIfCallable(self.view_variable.CALLBACK_SET_MIC_WORD_FILTER, entry_widget.get())
            entry_widget.focus_set()

        bindButtonFunctionAndColor(
            target_widgets=[
                add_button,
                add_button_label_wrapper,
                add_button_label,
            ],
            enter_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_HOVERED_COLOR,
            leave_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_COLOR,
            clicked_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST__ADD_BUTTON_CLICKED_COLOR,
            buttonReleasedFunction=lambda _e: adjustedCommand(),
        )


        return setting_box_frame


    def _createRowFrame(self, parent_widget, row):
        mic_word_filter_item_row_wrapper = CTkFrame(parent_widget, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        mic_word_filter_item_row_wrapper.grid(row=row, column=0, pady=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_BOTTOM_PADY, sticky="nsew")

        return mic_word_filter_item_row_wrapper



    def _createValue(self, add_and_delete_able_list_attr_name, parent_row_frame, row, column, mic_word_filter_item):
        mic_word_filter_item_wrapper = CTkFrame(parent_row_frame, corner_radius=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_CORNER_RADIUS, fg_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST_BG_COLOR, width=0, height=0)
        mic_word_filter_item_wrapper.grid(row=0, column=column, padx=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_LEFT_PADX, sticky="nsew")
        setattr(self, f"{row}_{column}", mic_word_filter_item_wrapper)



        mic_word_filter_item_wrapper.grid_rowconfigure((0,2), weight=1)
        label_widget = CTkLabel(
            mic_word_filter_item_wrapper,
            text=mic_word_filter_item,
            height=0,
            corner_radius=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=self.settings.ctm.BASIC_TEXT_COLOR,
        )

        label_widget.grid(row=1, column=0, padx=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_IPADX, pady=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_IPADY)


        if isEven(getLatestHeight(label_widget)) is False:
            label_widget.grid(
                pady=(
                    self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_IPADY,
                    self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_IPADY + 1
                )
            )


        if isEven(getLatestWidth(label_widget)) is False:
            label_widget.grid(
                padx=(
                    self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_IPADX[0],
                    self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_IPADX[1] + 1
                )
            )



        def pressedDeleteButtonCommand(_e, delete_button, redo_button):
            # overstrike true
            label_widget.configure(font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_FONT_SIZE, weight="normal", overstrike=True))
            # change fg_color
            mic_word_filter_item_wrapper.configure(fg_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST_DELETED_BG_COLOR)
            # change button img to redo button
            delete_button.grid_remove()
            redo_button.grid()
            # callback delete function
            callFunctionIfCallable(self.view_variable.CALLBACK_DELETE_MIC_WORD_FILTER, mic_word_filter_item)

        def pressedRedoButtonCommand(_e, delete_button, redo_button):
            # overstrike false
            label_widget.configure(font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_TEXT_FONT_SIZE, weight="normal", overstrike=False))
            # change fg_color
            mic_word_filter_item_wrapper.configure(fg_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST_BG_COLOR)
            # change button img to delete button
            redo_button.grid_remove()
            delete_button.grid()
            # callback add function
            callFunctionIfCallable(self.view_variable.CALLBACK_SET_MIC_WORD_FILTER, mic_word_filter_item)



        delete_button = createButtonWithImage(
            parent_widget=mic_word_filter_item_wrapper,
            button_fg_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST_BG_COLOR,
            button_enter_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_HOVERED_BG_COLOR,
            button_clicked_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_CLICKED_BG_COLOR,
            button_image_file=self.settings.image_file.CANCEL_ICON,
            button_image_size=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_IMG_SIZE,
            corner_radius=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_CORNER_RADIUS,
            button_ipadxy=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_IPADXY,
            button_command=lambda _e: pressedDeleteButtonCommand(_e, delete_button, redo_button),
        )
        delete_button.grid(row=1, column=1, padx=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_PADX, sticky="e")

        redo_button = createButtonWithImage(
            parent_widget=mic_word_filter_item_wrapper,
            button_fg_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST_DELETED_BG_COLOR,
            button_enter_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST__VALUES_DELETED_BUTTON_HOVERED_BG_COLOR,
            button_clicked_color=self.settings.ctm.SB__ADD_AND_DELETE_ABLE_LIST__VALUES_DELETED_BUTTON_CLICKED_BG_COLOR,
            button_image_file=self.settings.image_file.REDO_ICON,
            button_image_size=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_IMG_SIZE,
            corner_radius=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_CORNER_RADIUS,
            button_ipadxy=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_IPADXY,
            button_command=lambda _e: pressedRedoButtonCommand(_e, delete_button, redo_button),
        )
        redo_button.grid(row=1, column=1, padx=self.settings.uism.ADD_AND_DELETE_ABLE_LIST__VALUES_ACTION_BUTTON_PADX, sticky="e")
        redo_button.grid_remove()


        partial_pressedRedoButtonCommand = partial(pressedRedoButtonCommand, _e=None, delete_button=delete_button, redo_button=redo_button)
        item_data = SimpleNamespace(
            label = mic_word_filter_item,
            redoFunction = lambda: partial_pressedRedoButtonCommand(),
        )


        items = self.config_window.sb__widgets[add_and_delete_able_list_attr_name].items
        if len(items) == 0:
            items.append(item_data)
        else:
            is_replaced = False
            for i, item in enumerate(items):
                if item.label == mic_word_filter_item:
                    items[i] = item_data
                    is_replaced = True
                    break
            if is_replaced is False:
                items.append(item_data)


        return mic_word_filter_item_wrapper




    def _createPassiveButtonForProgressbarXSlider(self, setting_box_progressbar_x_slider_frame, button_command, button_image_file):
        button_wrapper = createButtonWithImage(
            parent_widget=setting_box_progressbar_x_slider_frame,
            button_fg_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_COLOR,
            button_enter_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_HOVERED_COLOR,
            button_clicked_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_CLICKED_COLOR,
            button_image_file=button_image_file,
            button_image_size=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BUTTON_ICON_SIZE,
            button_ipadxy=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BUTTON_IPADXY,
            button_command=button_command,
        )
        return button_wrapper



    def _createActiveButtonForProgressbarXSlider(self, setting_box_progressbar_x_slider_frame, button_command, button_image_file):
        button_wrapper = createButtonWithImage(
            parent_widget=setting_box_progressbar_x_slider_frame,
            button_fg_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_COLOR,
            button_enter_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_HOVERED_COLOR,
            button_clicked_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__ACTIVE_BUTTON_CLICKED_COLOR,
            button_image_file=button_image_file,
            button_image_size=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BUTTON_ICON_SIZE,
            button_ipadxy=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BUTTON_IPADXY,
            button_command=button_command,
        )
        return button_wrapper



    def _createDisabledButtonForProgressbarXSlider(self, setting_box_progressbar_x_slider_frame, button_image_file):
        button_wrapper = createButtonWithImage(
            parent_widget=setting_box_progressbar_x_slider_frame,
            button_fg_color=self.settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR,
            button_image_file=button_image_file,
            button_image_size=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BUTTON_ICON_SIZE,
            button_ipadxy=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BUTTON_IPADXY,
            no_bind=True,
        )
        return button_wrapper