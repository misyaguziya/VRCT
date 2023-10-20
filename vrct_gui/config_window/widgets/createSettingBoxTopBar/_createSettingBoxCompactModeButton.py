from customtkinter import CTkFont, CTkFrame, CTkLabel, CTkSwitch

def _createSettingBoxCompactModeButton(parent_widget, config_window, settings, view_variable, column_num):

    def switchConfigWindowCompactMode():
        if config_window.setting_box_compact_mode_switch_box.get() is True:
            if callable(view_variable.CALLBACK_ENABLE_CONFIG_WINDOW_COMPACT_MODE) is True:
                view_variable.CALLBACK_ENABLE_CONFIG_WINDOW_COMPACT_MODE()
        else:
            if callable(view_variable.CALLBACK_DISABLE_CONFIG_WINDOW_COMPACT_MODE) is True:
                view_variable.CALLBACK_DISABLE_CONFIG_WINDOW_COMPACT_MODE()



    config_window.setting_box_compact_mode_button_container = CTkFrame(parent_widget, corner_radius=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR, width=0, height=0)
    config_window.setting_box_compact_mode_button_container.grid(row=0, column=column_num, padx=settings.uism.COMPACT_MODE_PADX, sticky="nse")



    config_window.setting_box_compact_mode_button_container.grid_rowconfigure((0,2), weight=1)
    config_window.setting_box_compact_mode_button_container = CTkFrame(config_window.setting_box_compact_mode_button_container, corner_radius=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR, width=0, height=0)
    config_window.setting_box_compact_mode_button_container.grid(row=1, column=0, sticky="nsew")


    config_window.setting_box_compact_mode_button_container.grid_rowconfigure(0, weight=1)
    config_window.setting_box_compact_mode_label = CTkLabel(
        config_window.setting_box_compact_mode_button_container,
        height=0,
        # text="Compact Mode",
        textvariable=view_variable.VAR_CONFIG_WINDOW_COMPACT_MODE_LABEL,
        anchor="w",
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.COMPACT_MODE_LABEL_FONT_SIZE, weight="normal"),
        text_color=settings.ctm.LABELS_TEXT_COLOR
    )
    config_window.setting_box_compact_mode_label.grid(row=0, column=0, padx=settings.uism.COMPACT_MODE_LABEL_PADX)








    config_window.setting_box_compact_mode_switch_frame = CTkFrame(config_window.setting_box_compact_mode_button_container, corner_radius=0, width=0, height=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR)
    config_window.setting_box_compact_mode_switch_frame.grid(row=0, column=1, padx=0, sticky="e")

    config_window.setting_box_compact_mode_switch_box = CTkSwitch(
        config_window.setting_box_compact_mode_switch_frame,
        text=None,
        height=0,
        width=0,
        # corner_radius=0,
        border_width=0,
        switch_width=settings.uism.COMPACT_MODE_SWITCH_WIDTH,
        switch_height=settings.uism.COMPACT_MODE_SWITCH_HEIGHT,
        onvalue=True,
        offvalue=False,
        command=switchConfigWindowCompactMode,
        fg_color=settings.ctm.COMPACT_MODE_SWITCH_BOX_BG_COLOR,
        # bg_color="red",
        progress_color=settings.ctm.COMPACT_MODE_SWITCH_BOX_ACTIVE_BG_COLOR,
        button_color=settings.ctm.COMPACT_MODE_SWITCH_BOX_BUTTON_COLOR,
        button_hover_color=settings.ctm.COMPACT_MODE_SWITCH_BOX_BUTTON_HOVERED_COLOR,
    )

    config_window.setting_box_compact_mode_switch_box.grid(row=0, column=0)