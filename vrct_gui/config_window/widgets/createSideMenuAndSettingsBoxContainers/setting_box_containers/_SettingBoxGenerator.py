from functools import partial
from types import SimpleNamespace
from typing import Union

from customtkinter import CTkOptionMenu, CTkFont, CTkFrame, CTkLabel, CTkRadioButton, CTkEntry, CTkSlider, CTkSwitch, CTkCheckBox, CTkProgressBar

from vrct_gui.ui_utils import createButtonWithImage, getLatestWidth, createOptionMenuBox
from vrct_gui import vrct_gui

SETTING_BOX_COLUMN = 1

class _SettingBoxGenerator():
    def __init__(self, parent_widget, config_window, settings, view_variable):
        self.view_variable = view_variable
        self.config_window = config_window
        self.parent_widget = parent_widget
        self.settings = settings

        self.dropdown_menu_window = vrct_gui.vrct_gui.dropdown_menu_window

    def _createSettingBoxFrame(self, sb__attr_name, for_var_label_text=None, for_var_desc_text=None):
        self.config_window.sb__widgets[sb__attr_name] = SimpleNamespace()

        setting_box_frame = CTkFrame(self.parent_widget, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)

        # "pady=(0,1)" is for bottom padding. It can be removed(override) when you do like "self.attr_name.grid(row=row, pady=0)"
        setting_box_frame.grid(column=0, padx=0, pady=self.settings.uism.SB__FAKE_BOTTOM_BORDER_SIZE, sticky="ew")
        setting_box_frame.grid_columnconfigure(0, weight=1)


        setting_box_frame_wrapper = CTkFrame(setting_box_frame, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR, width=0, height=0)
        setting_box_frame_wrapper.grid(row=0, column=0, padx=self.settings.uism.SB__IPADX, pady=self.settings.uism.SB__IPADY, sticky="ew")
        setting_box_frame_wrapper.grid_columnconfigure(0, weight=0, minsize=int(self.settings.uism.MAIN_AREA_MIN_WIDTH / 2))
        setting_box_frame_wrapper.grid_columnconfigure(2, weight=1, minsize=int(self.settings.uism.MAIN_AREA_MIN_WIDTH / 2))

        setting_box_frame_wrapper_fix_border = CTkFrame(setting_box_frame, corner_radius=0, width=0, height=0)
        setting_box_frame_wrapper_fix_border.grid(row=1, column=0, sticky="ew")

        setting_box_frame_wrapper_fix_border2 = CTkFrame(setting_box_frame, corner_radius=0, width=0, height=0)
        setting_box_frame_wrapper_fix_border2.grid(row=0, column=1, sticky="ns")

        if for_var_label_text is not None:
            self._setSettingBoxLabels(sb__attr_name, setting_box_frame_wrapper, for_var_label_text, for_var_desc_text)

        # setting_box_item_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, width=0, height=0, fg_color="red")
        setting_box_item_frame = CTkFrame(setting_box_frame_wrapper, corner_radius=0, width=0, height=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        if for_var_label_text is not None:
            setting_box_item_frame.grid(row=0, column=2, padx=0, sticky="nsew")
        else:
            setting_box_item_frame.grid(row=0, columnspan=3, padx=0, sticky="nsew")
        setting_box_item_frame.grid_rowconfigure((0,2), weight=1)
        setting_box_item_frame.grid_columnconfigure(0, weight=1)

        return (setting_box_frame, setting_box_item_frame)

    def _setSettingBoxLabels(self, sb__attr_name, setting_box_frame_wrapper, for_var_label_text, for_var_desc_text=None):

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
            setting_box_desc.grid(row=2, column=0, padx=0, pady=(self.settings.uism.SB__DESC_TOP_PADY,0), sticky="ew")
            self.config_window.additional_widgets.append(setting_box_desc)
            self.config_window.sb__widgets[sb__attr_name].desc_widget=setting_box_desc
        else:
            self.config_window.sb__widgets[sb__attr_name].desc_widget=None




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
            # bg_color="red",
            progress_color=self.settings.ctm.SB__SWITCH_BOX_ACTIVE_BG_COLOR,
        )
        setattr(self.config_window, switch_attr_name, switch_widget)

        switch_widget.grid(row=1, column=SETTING_BOX_COLUMN, sticky="e")

        return setting_box_frame



    def createSettingBoxCheckbox(self,
            for_var_label_text, for_var_desc_text,
            checkbox_attr_name,
            command,
            variable,
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
            # fg_color=self.settings.ctm.SB__SWITCH_BOX_BG_COLOR,
            # bg_color="red",
            # progress_color=self.settings.ctm.SB__SWITCH_BOX_ACTIVE_BG_COLOR,
        )
        setattr(self.config_window, checkbox_attr_name, checkbox_widget)

        checkbox_widget.grid(row=1, column=SETTING_BOX_COLUMN, sticky="e")

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
            slider_bind__ButtonRelease=None
        ):

        (setting_box_frame, setting_box_item_frame) = self._createSettingBoxFrame(slider_attr_name, for_var_label_text, for_var_desc_text)


        slider_widget = CTkSlider(
            setting_box_item_frame,
            width=self.settings.uism.SB__SLIDER_WIDTH,
            height=self.settings.uism.SB__SLIDER_HEIGHT,
            from_=slider_range[0],
            to=slider_range[1],
            number_of_steps=slider_number_of_steps,
            button_color=self.settings.ctm.SB__SLIDER_BUTTON_COLOR,
            button_hover_color=self.settings.ctm.SB__SLIDER_BUTTON_HOVERED_COLOR,
            command=command,
            variable=variable,
        )
        setattr(self.config_window, slider_attr_name, slider_widget)

        slider_widget.grid(row=1, column=SETTING_BOX_COLUMN, sticky="e")

        if slider_bind__ButtonPress is not None:
            def adjusted_slider_bind__ButtonPress(_e):
                command(_e)
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