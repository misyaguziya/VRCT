from customtkinter import CTkFont, CTkFrame, CTkLabel


def _createSettingBoxContainer(config_window, settings, view_variable, setting_box_container_settings):


    def createSectionTitle(container_widget, var_section_title):

        setting_box_wrapper_section_title = CTkLabel(
            container_widget,
            textvariable=var_section_title,
            anchor="w",
            height=0,
            font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SB__SECTION_TITLE_FONT_SIZE, weight="normal"),
            text_color=settings.ctm.LABELS_TEXT_COLOR
        )
        setting_box_wrapper_section_title.place(relx=0, rely=0)

        return container_widget


    # Setting box container
    setting_box_container_widget = CTkFrame(config_window.main_setting_box_bg_wrapper, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    setattr(config_window, setting_box_container_settings["setting_box_container_attr_name"], setting_box_container_widget)
    setting_box_container_widget.grid(row=0, pady=settings.uism.SB__BOTTOM_MARGIN)
    setting_box_container_widget.grid_remove()



    setting_box_row=0
    for setting_box_setting in setting_box_container_settings["setting_boxes"]:
        # Top-Padding that can be container the section title
        setting_box_top_padding = CTkFrame(setting_box_container_widget, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=settings.uism.SB__TOP_PADY)
        setting_box_top_padding.grid(row=setting_box_row, column=0, sticky="ew", padx=0, pady=0)
        setting_box_top_padding.grid_columnconfigure(0, weight=1)
        setting_box_row+=1

        if setting_box_setting["var_section_title"] is not None:
            setting_box_wrapper_section_title = CTkLabel(
                setting_box_top_padding,
                textvariable=setting_box_setting["var_section_title"],
                anchor="w",
                height=0,
                font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SB__SECTION_TITLE_FONT_SIZE, weight="normal"),
                text_color=settings.ctm.LABELS_TEXT_COLOR
            )
            setting_box_wrapper_section_title.place(relx=0, rely=0.4, anchor="nw")


        setting_box_wrapper = CTkFrame(setting_box_container_widget, fg_color=settings.ctm.SB__WRAPPER_BG_COLOR, corner_radius=0, width=0, height=0)
        setting_box_wrapper.grid(row=setting_box_row, column=0, sticky="ew")
        setting_box_wrapper.grid_columnconfigure(0, weight=1)
        setting_box_row+=1


        if setting_box_setting["setting_box"] is not None:
            setting_box_setting["setting_box"](
                setting_box_wrapper=setting_box_wrapper,
                config_window=config_window,
                settings=settings,
                view_variable=view_variable,
            )

