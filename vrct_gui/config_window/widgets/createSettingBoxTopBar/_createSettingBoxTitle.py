from customtkinter import CTkFont, CTkFrame, CTkLabel

def _createSettingBoxTitle(parent_widget, config_window, settings):

    parent_widget.grid_columnconfigure(0, weight=1)
    config_window.main_current_active_config_title_container = CTkFrame(parent_widget, corner_radius=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR, width=0, height=0)
    config_window.main_current_active_config_title_container.grid(row=0, column=0, sticky="nsew")


    config_window.main_current_active_config_title_container.grid_rowconfigure(0, weight=1)
    config_window.main_current_active_config_title = CTkLabel(
        config_window.main_current_active_config_title_container,
        height=0,
        text=None,
        anchor="w",
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TOP_BAR_MAIN__TITLE_FONT_SIZE, weight="bold"),
        text_color=settings.ctm.LABELS_TEXT_COLOR
    )
    config_window.main_current_active_config_title.grid(row=0, column=0, padx=0, pady=settings.uism.TOP_BAR__IPADY)

