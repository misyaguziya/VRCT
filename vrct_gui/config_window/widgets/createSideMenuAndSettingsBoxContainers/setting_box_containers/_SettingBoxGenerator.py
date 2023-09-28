from customtkinter import CTkOptionMenu, CTkFont, CTkFrame, CTkLabel, CTkRadioButton, CTkEntry, CTkSlider, CTkSwitch, CTkCheckBox, CTkProgressBar, END as CTK_END

from vrct_gui.ui_utils import createButtonWithImage, getLatestWidth

from typing import Union

class _SettingBoxGenerator():
    def __init__(self, parent_widget, config_window, settings, view_variable):
        self.view_variable = view_variable
        self.config_window = config_window
        self.parent_widget = parent_widget
        self.settings = settings


    def _createSettingBoxFrame(self, setting_box_item_frame, for_var_label_text, for_var_desc_text):
        setting_box_frame = CTkFrame(self.parent_widget, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        # setting_box_frame = CTkFrame(self.parent_widget, corner_radius=0, fg_color="gray", width=0, height=0)

        # "pady=(0,1)" is for bottom padding. It can be removed(override) when you do like "self.attr_name.grid(row=row, pady=0)"
        # setting_box_frame.grid(column=0, padx=0, pady=0, sticky="ew")
        setting_box_frame.grid(column=0, padx=0, pady=(0,1), sticky="ew")


        # setting_box_frame_wrapper = CTkFrame(setting_box_frame, corner_radius=0, fg_color="gray", width=0, height=0)
        setting_box_frame_wrapper = CTkFrame(setting_box_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=self.settings.uism.SB__MAIN_WIDTH, height=0)
        setting_box_frame_wrapper.grid(row=0, column=0, padx=self.settings.uism.SB__IPADX, pady=self.settings.uism.SB__IPADY, sticky="ew")
        setting_box_frame_wrapper.grid_columnconfigure((0,1), weight=1, minsize=int(self.settings.uism.SB__MAIN_WIDTH / 2), uniform="setting_box")

        # setting_box_frame_wrapper.grid(column=0, padx=0, pady=0)
        setting_box_frame_wrapper.grid(row=0, column=0, padx=self.settings.uism.SB__IPADX, pady=self.settings.uism.SB__IPADY, sticky="nsew")

        setting_box_frame_wrapper_border = CTkFrame(setting_box_frame, corner_radius=0, fg_color="red", width=0, height=0)
        setting_box_frame_wrapper_border.grid(row=1, column=0, sticky="ew")

        self._setSettingBoxLabels(setting_box_frame_wrapper, for_var_label_text, for_var_desc_text)

        # setting_box_item_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, width=0, height=0, fg_color="black")
        setting_box_item_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, width=0, height=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        setting_box_item_frame.grid(row=0, column=1, padx=0, sticky="nsew")
        setting_box_item_frame.rowconfigure((0,2), weight=1)
        setting_box_item_frame.grid_columnconfigure(0, weight=1)

        return (setting_box_frame, setting_box_item_frame)

    def _setSettingBoxLabels(self, setting_box_frame_wrapper, for_var_label_text, for_var_desc_text=None):

        # setting_box_labels_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, fg_color="black", width=0, height=0)
        setting_box_labels_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        setting_box_labels_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        setting_box_label = CTkLabel(
            setting_box_labels_frame,
            textvariable=for_var_label_text,
            anchor="w",
            # height=0,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__LABEL_FONT_SIZE, weight="normal"),
            text_color=self.settings.ctm.LABELS_TEXT_COLOR
        )
        setting_box_label.grid(row=0, column=0, padx=0, pady=0, sticky="ew")

        if for_var_desc_text is not None:
            setting_box_desc = CTkLabel(
                setting_box_labels_frame,
                textvariable=for_var_desc_text,
                anchor="w",
                justify="left",
                # height=0,
                wraplength=int(self.settings.uism.SB__MAIN_WIDTH / 2),
                font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__DESC_FONT_SIZE, weight="normal"),
                text_color=self.settings.ctm.LABELS_DESC_TEXT_COLOR
            )
            setting_box_desc.grid(row=1, column=0, padx=0, pady=(self.settings.uism.SB__DESC_TOP_PADY,0), sticky="ew")
            self.config_window.additional_widgets.append(setting_box_desc)


    def createSettingBoxDropdownMenu(self, for_var_label_text, for_var_desc_text, optionmenu_attr_name, command, variable=None, dropdown_menu_values=None):
        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(self, for_var_label_text, for_var_desc_text)

        option_menu_widget = CTkOptionMenu(
            setting_box_item_frame,
            height=self.settings.uism.SB__OPTIONMENU_HEIGHT,
            width=self.settings.uism.SB__OPTIONMENU_WIDTH,
            values=dropdown_menu_values,
            button_color=self.settings.ctm.SB__OPTIONMENU_BG_COLOR,
            button_hover_color=self.settings.ctm.SB__OPTIONMENU_HOVERED_BG_COLOR,
            fg_color=self.settings.ctm.SB__OPTIONMENU_BG_COLOR,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__OPTION_MENU_FONT_SIZE, weight="normal"),
            variable=variable,
            command=command,
            anchor="w",
        )
        option_menu_widget.grid(row=1, column=1, sticky="e")
        setattr(self.config_window, optionmenu_attr_name, option_menu_widget)

        return setting_box_frame




    def createSettingBoxSwitch(self, for_var_label_text, for_var_desc_text, switch_attr_name, is_checked, command):
        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(self, for_var_label_text, for_var_desc_text)

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
            command=command,
            fg_color=self.settings.ctm.SB__SWITCH_BOX_BG_COLOR,
            # bg_color="red",
            progress_color=self.settings.ctm.SB__SWITCH_BOX_ACTIVE_BG_COLOR,
        )
        setattr(self.config_window, switch_attr_name, switch_widget)

        switch_widget.select() if is_checked else switch_widget.deselect()

        switch_widget.grid(row=1, column=1)

        return setting_box_frame



    def createSettingBoxCheckbox(self, for_var_label_text, for_var_desc_text, checkbox_attr_name, variable, command):
        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(self, for_var_label_text, for_var_desc_text)

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
            # fg_color=self.settings.ctm.SB__SWITCH_BOX_BG_COLOR,
            # bg_color="red",
            # progress_color=self.settings.ctm.SB__SWITCH_BOX_ACTIVE_BG_COLOR,
        )
        setattr(self.config_window, checkbox_attr_name, checkbox_widget)

        # checkbox_widget.select() if is_checked else checkbox_widget.deselect()

        checkbox_widget.grid(row=1, column=1)

        return setting_box_frame






    def createSettingBoxSlider(self, for_var_label_text, for_var_desc_text, slider_attr_name, slider_range, command, variable, slider_number_of_steps: Union[int, None] = None):
        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(self, for_var_label_text, for_var_desc_text)

        slider_widget = CTkSlider(
            setting_box_item_frame,
            from_=slider_range[0],
            to=slider_range[1],
            number_of_steps=slider_number_of_steps,
            button_color=self.settings.ctm.SB__SLIDER_BUTTON_COLOR,
            button_hover_color=self.settings.ctm.SB__SLIDER_BUTTON_HOVERED_COLOR,
            command=command,
            variable=variable,
        )
        setattr(self.config_window, slider_attr_name, slider_widget)

        slider_widget.grid(row=1, column=1)

        return setting_box_frame




    def createSettingBoxProgressbarXSlider(
            self,
            for_var_label_text, for_var_desc_text, command,
            entry_attr_name,
            slider_attr_name, slider_range,
            progressbar_attr_name,
            passive_button_attr_name, passive_button_command,
            active_button_attr_name, active_button_command,
            button_image_file,
            entry_variable,
            slider_variable,

            slider_number_of_steps: Union[int, None] = None,
        ):


        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(self, for_var_label_text, for_var_desc_text)

        ENTRY_WIDTH = self.settings.uism.SB__PROGRESSBAR_X_SLIDER__ENTRY_WIDTH
        BAR_WIDTH = self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BAR_WIDTH

        BAR_PADDING = int(ENTRY_WIDTH + self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BAR_RIGHT_PADX)
        BUTTON_PADDING = int(BAR_WIDTH + BAR_PADDING + self.settings.uism.SB__PROGRESSBAR_X_SLIDER__BUTTON_RIGHT_PADX)

        def adjusted_command__for_entry_bind__Any_KeyRelease(e):
            command(e.widget.get())
        def adjusted_command__for_slider(value):
            command(value)

        entry_widget = CTkEntry(
            setting_box_item_frame,
            width=ENTRY_WIDTH,
            height=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__ENTRY_HEIGHT,
            textvariable=entry_variable,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__ENTRY_FONT_SIZE, weight="normal"),
        )

        entry_widget.bind("<Any-KeyRelease>", adjusted_command__for_entry_bind__Any_KeyRelease)
        entry_widget.grid(row=1, column=1, padx=0, pady=0, sticky="e")
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
            width=BAR_WIDTH,
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
        slider_widget.grid(row=1, column=1, padx=(0, BAR_PADDING), sticky="e")
        setattr(self.config_window, slider_attr_name, slider_widget)




        progressbar_widget = CTkProgressBar(
            setting_box_item_frame,
            width=BAR_WIDTH,
            height=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__PROGRESSBAR_HEIGHT,
            corner_radius=0,
        )
        setattr(self.config_window, progressbar_attr_name, progressbar_widget)
        progressbar_widget.grid(row=1, column=1, padx=(0, BAR_PADDING), sticky="e")
        progressbar_widget.set(0)




        passive_button_wrapper = self._createPassiveButtonForProgressbarXSlider(setting_box_item_frame, passive_button_command, button_image_file)
        setattr(self.config_window, passive_button_attr_name, passive_button_wrapper)

        active_button_wrapper = self._createActiveButtonForProgressbarXSlider(setting_box_item_frame, active_button_command, button_image_file)
        setattr(self.config_window, active_button_attr_name, active_button_wrapper)

        passive_button_wrapper.grid(row=1, column=1, padx=(0,BUTTON_PADDING), sticky="e")
        passive_button_wrapper.configure(corner_radius=int(getLatestWidth(passive_button_wrapper)/2))

        active_button_wrapper.grid(row=1, column=1, padx=(0,BUTTON_PADDING), sticky="e")
        active_button_wrapper.configure(corner_radius=int(getLatestWidth(passive_button_wrapper)/2))

        passive_button_wrapper.grid_remove()
        active_button_wrapper.grid_remove()

        passive_button_wrapper.grid()
        return setting_box_frame




    def createSettingBoxEntry(self, for_var_label_text, for_var_desc_text, entry_attr_name, entry_width, entry_bind__Any_KeyRelease, entry_textvariable):
        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(self, for_var_label_text, for_var_desc_text)

        def adjusted_command__for_entry_bind__Any_KeyRelease(e):
            entry_bind__Any_KeyRelease(e.widget.get())

        entry_widget = CTkEntry(
            setting_box_item_frame,
            width=entry_width,
            height=self.settings.uism.SB__PROGRESSBAR_X_SLIDER__ENTRY_HEIGHT,
            textvariable=entry_textvariable,
            font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__ENTRY_FONT_SIZE, weight="normal"),
        )
        entry_widget.bind("<Any-KeyRelease>", adjusted_command__for_entry_bind__Any_KeyRelease)
        setattr(self.config_window, entry_attr_name, entry_widget)


        entry_widget.grid(row=1, column=1)

        return setting_box_frame



        # if setting_box_type == "dropdown_menu_x_dropdown_menu":
        #     self.setting_box_dropdown_menu_x_dropdown_menu = CTkFrame(self.setting_box, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        #     self.setting_box_dropdown_menu_x_dropdown_menu.grid(row=0, column=1, padx=(0, self.settings.uism.SB__RIGHT_PADX), rowspan=2, sticky="e")



        #     # Labels
        #     self.optionmenu_label_left = CTkLabel(
        #         self.setting_box_dropdown_menu_x_dropdown_menu,
        #         text=kwargs["left_dropdown_menu_label"],
        #         font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__OPTION_MENU_FONT_SIZE, weight="normal"),
        #     )
        #     self.optionmenu_label_left.grid(row=0, column=0)

        #     self.the_space_between_optionmenu = CTkLabel(
        #         self.setting_box_dropdown_menu_x_dropdown_menu,
        #         text=None,
        #     )
        #     self.the_space_between_optionmenu.grid(row=0, column=1)


        #     self.optionmenu_label_right = CTkLabel(
        #         self.setting_box_dropdown_menu_x_dropdown_menu,
        #         text=kwargs["right_dropdown_menu_label"],
        #         font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__OPTION_MENU_FONT_SIZE, weight="normal"),
        #     )
        #     self.optionmenu_label_right.grid(row=0, column=2)



        #     # Option menus
        #     self.createOption_DropdownMenu(
        #         setattr_obj,
        #         self.setting_box_dropdown_menu_x_dropdown_menu,
        #         kwargs["left_optionmenu_attr_name"],
        #         kwargs["left_dropdown_menu_attr_name"],
        #         dropdown_menu_values=kwargs["left_dropdown_menu_values"],
        #         width=150,
        #         command=kwargs["left_dropdown_menu_command"],
        #         variable=kwargs["left_dropdown_menu_variable"],
        #     )
        #     getattr(setattr_obj, kwargs["left_optionmenu_attr_name"]).grid(row=1, column=0)



        #     self.the_label_between_optionmenu = CTkLabel(
        #         self.setting_box_dropdown_menu_x_dropdown_menu,
        #         text="-->",
        #         # anchor="w",
        #         font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__OPTION_MENU_FONT_SIZE, weight="normal"),
        #         text_color=self.settings.ctm.LABELS_TEXT_COLOR
        #     )
        #     self.the_label_between_optionmenu.grid(row=1, column=1, padx=self.settings.uism.SB__RIGHT_PADX/2)


        #     self.createOption_DropdownMenu(
        #         setattr_obj,
        #         self.setting_box_dropdown_menu_x_dropdown_menu,
        #         kwargs["right_optionmenu_attr_name"],
        #         kwargs["right_dropdown_menu_attr_name"],
        #         dropdown_menu_values=kwargs["right_dropdown_menu_values"],
        #         width=150,
        #         command=kwargs["right_dropdown_menu_command"],
        #         variable=kwargs["right_dropdown_menu_variable"],
        #     )
        #     getattr(setattr_obj, kwargs["right_optionmenu_attr_name"]).grid(row=1, column=2)




        # if setting_box_type == "radio_buttons":
        #     self.setting_box_radio_buttons_frame = CTkFrame(self.setting_box, corner_radius=0, width=0, height=0)
        #     self.setting_box_radio_buttons_frame.grid(row=0, column=1, padx=(0, self.settings.uism.SB__RIGHT_PADX), rowspan=2, sticky="e")

        #     RADIO_BUTTON_RIGHT_PAD = 14
        #     self.setting_box_radio_button_1 = CTkRadioButton(
        #         self.setting_box_radio_buttons_frame,
        #         text="lorem ipsum",
        #         font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__RADIO_BUTTON_FONT_SIZE, weight="normal")
        #     )
        #     self.setting_box_radio_button_1.grid(row=0, column=0, padx=(0,RADIO_BUTTON_RIGHT_PAD), sticky="e")

        #     self.setting_box_radio_button_2 = CTkRadioButton(
        #         self.setting_box_radio_buttons_frame,
        #         text="lorem ipsum",
        #         font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__RADIO_BUTTON_FONT_SIZE, weight="normal")
        #     )
        #     self.setting_box_radio_button_2.grid(row=0, column=1, padx=(0,RADIO_BUTTON_RIGHT_PAD), sticky="e")

        #     self.setting_box_radio_button_3 = CTkRadioButton(
        #         self.setting_box_radio_buttons_frame,
        #         text="lorem ipsum",
        #         font=CTkFont(family=self.settings.FONT_FAMILY, size=self.settings.uism.SB__RADIO_BUTTON_FONT_SIZE, weight="normal")
        #     )
        #     self.setting_box_radio_button_3.grid(row=0, column=2, padx=(0,RADIO_BUTTON_RIGHT_PAD), sticky="e")



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