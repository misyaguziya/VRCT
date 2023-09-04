from customtkinter import CTkFont, CTkFrame, CTkLabel


def _createSettingBoxContainer(config_window, settings, view_variable, setting_box_container_settings):


    def createSectionTitle(container_widget, section_title):
        setting_box_wrapper_section_title_frame = CTkFrame(container_widget, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)

        setting_box_wrapper_section_title = CTkLabel(
            setting_box_wrapper_section_title_frame,
            text=section_title,
            anchor="w",
            height=0,
            font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SB__SECTION_TITLE_FONT_SIZE, weight="normal"),
            text_color=settings.ctm.LABELS_TEXT_COLOR
        )
        setting_box_wrapper_section_title.grid(row=0, column=0, padx=0, pady=settings.uism.SB__SECTION_TITLE_BOTTOM_PADY)

        return setting_box_wrapper_section_title_frame


    # Setting box container
    setting_box_container_widget = CTkFrame(config_window.main_setting_box_bg_wrapper, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    setattr(config_window, setting_box_container_settings["setting_box_container_attr_name"], setting_box_container_widget)




    setting_boxes_length = len(setting_box_container_settings["setting_boxes"])
    setting_box_row = 0
    for i, setting_box_setting in enumerate(setting_box_container_settings["setting_boxes"]):
        SB__TOP_PADY = 0
        SB__BOTTOM_PADY = settings.uism.SB__BOTTOM_PADY

        setting_box_and_section_title_wrapper = CTkFrame(setting_box_container_widget, fg_color=settings.ctm.SB__WRAPPER_BG_COLOR, corner_radius=0, width=0, height=0)

        if setting_box_setting["section_title"] is not None:
            setting_box_wrapper_section_title_frame= createSectionTitle(
                container_widget=setting_box_and_section_title_wrapper,
                section_title=setting_box_setting["section_title"],
            )
            setting_box_wrapper_section_title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
            if i == 0: SB__TOP_PADY = settings.uism.SB__TOP_PADY_IF_WITH_SECTION_TITLE

        # if the first one of setting boxes, adjust top pady
        if i == 0: SB__TOP_PADY = settings.uism.SB__TOP_PADY_IF_WITHOUT_SECTION_TITLE

        # if the last one of setting boxes, remove bottom pady
        if i+1 == setting_boxes_length: SB__BOTTOM_PADY = 0

        setting_box_wrapper = CTkFrame(setting_box_and_section_title_wrapper, fg_color=settings.ctm.SB__WRAPPER_BG_COLOR, corner_radius=0, width=0, height=0)
        setting_box_wrapper.grid(row=1, column=0)
        setting_box_row+=1

        setting_box_and_section_title_wrapper.grid(row=setting_box_row, column=0, sticky="ew", padx=0, pady=(SB__TOP_PADY, SB__BOTTOM_PADY))

        if setting_box_setting["setting_box"] is not None:
            setting_box_setting["setting_box"](
                setting_box_wrapper=setting_box_wrapper,
                config_window=config_window,
                settings=settings,
                view_variable=view_variable,
            )

