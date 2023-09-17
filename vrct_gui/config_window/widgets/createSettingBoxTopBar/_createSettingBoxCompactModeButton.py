from customtkinter import CTkFont, CTkFrame, CTkLabel, CTkSwitch

def _createSettingBoxCompactModeButton(parent_widget, config_window, settings, view_variable):

    def switchConfigWindowCompactMode():
        if config_window.setting_box_compact_mode_switch_box.get() is True:
            if callable(view_variable.CALLBACK_ENABLE_CONFIG_WINDOW_COMPACT_MODE) is True:
                view_variable.CALLBACK_ENABLE_CONFIG_WINDOW_COMPACT_MODE()
        else:
            if callable(view_variable.CALLBACK_DISABLE_CONFIG_WINDOW_COMPACT_MODE) is True:
                view_variable.CALLBACK_DISABLE_CONFIG_WINDOW_COMPACT_MODE()



    config_window.setting_box_compact_mode_button_container = CTkFrame(parent_widget, corner_radius=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR, width=0, height=0)
    config_window.setting_box_compact_mode_button_container.grid(row=0, column=1, padx=(0, 20), sticky="nsw")



    config_window.setting_box_compact_mode_button_container.grid_rowconfigure((0,2), weight=1)
    config_window.setting_box_compact_mode_button_container = CTkFrame(config_window.setting_box_compact_mode_button_container, corner_radius=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR, width=0, height=0)
    config_window.setting_box_compact_mode_button_container.grid(row=1, column=0, sticky="nsew")


    config_window.setting_box_compact_mode_button_container.grid_rowconfigure(0, weight=1)
    config_window.setting_box_compact_mode_label = CTkLabel(
        config_window.setting_box_compact_mode_button_container,
        height=0,
        text="Compact Mode",
        anchor="w",
        font=CTkFont(family=settings.FONT_FAMILY, size=12, weight="normal"),
        text_color=settings.ctm.LABELS_TEXT_COLOR
    )
    config_window.setting_box_compact_mode_label.grid(row=0, column=0, padx=(0,10))








    config_window.setting_box_compact_mode_switch_frame = CTkFrame(config_window.setting_box_compact_mode_button_container, corner_radius=0, width=0, height=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR)
    config_window.setting_box_compact_mode_switch_frame.grid(row=0, column=1, padx=0, sticky="e")

    config_window.setting_box_compact_mode_switch_box = CTkSwitch(
        config_window.setting_box_compact_mode_switch_frame,
        text=None,
        height=0,
        width=0,
        # corner_radius=0,
        border_width=0,
        switch_width=40,
        switch_height=16,
        onvalue=True,
        offvalue=False,
        command=switchConfigWindowCompactMode,
        # fg_color="",
        # bg_color="red",
        progress_color=settings.ctm.SB__SWITCH_BOX_ACTIVE_BG_COLOR, # SB__SWITCH_BOX_ACTIVE_BG_COLOR is for SB. change it later.
    )

    config_window.setting_box_compact_mode_switch_box.select() if settings.IS_CONFIG_WINDOW_COMPACT_MODE else config_window.setting_box_compact_mode_switch_box.deselect()

    config_window.setting_box_compact_mode_switch_box.grid(row=0, column=0)

