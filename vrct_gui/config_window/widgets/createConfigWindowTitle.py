from customtkinter import CTkFont, CTkFrame, CTkLabel, CTkImage

def createConfigWindowTitle(config_window, settings):

    config_window.grid_columnconfigure(0, weight=0, minsize=settings.uism.TOP_BAR_SIDE__WIDTH)
    config_window.grid_rowconfigure(0, weight=0, minsize=settings.uism.TOP_BAR__HEIGHT)
    config_window.side_menu_config_window_title_logo_frame = CTkFrame(config_window, corner_radius=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR, width=0, height=0)
    config_window.side_menu_config_window_title_logo_frame.grid(row=0, column=0, sticky="nsew")

    config_window.side_menu_config_window_title_logo_frame.grid_rowconfigure(0,weight=1)
    config_window.side_menu_config_window_title_logo_frame.grid_columnconfigure(0,weight=1)
    config_window.side_menu_config_window_title_logo_wrapper = CTkFrame(config_window.side_menu_config_window_title_logo_frame, corner_radius=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR, width=0, height=0)
    config_window.side_menu_config_window_title_logo_wrapper.grid(row=0, column=0, padx=settings.uism.TOP_BAR_SIDE__TITLE_PADX, pady=settings.uism.TOP_BAR__IPADY, sticky="nsew")




    config_window.side_menu_config_window_title_logo_wrapper.grid_rowconfigure(0,weight=1)
    config_window.side_menu_config_window_title = CTkLabel(
        config_window.side_menu_config_window_title_logo_frame,
        text="Settings",
        height=0,
        anchor="w",
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TOP_BAR_SIDE__CONFIG_TITLE_FONT_SIZE, weight="bold"),
        text_color=settings.ctm.LABELS_TEXT_COLOR,
    )
    config_window.side_menu_config_window_title.place(relx=0.255, rely=0.5, anchor="w")

    config_window.side_menu_config_window_title_logo = CTkLabel(
        config_window.side_menu_config_window_title_logo_frame,
        text=None,
        height=0,
        anchor="w",
        image=CTkImage(settings.image_file.VRCT_LOGO_MARK, size=settings.uism.TOP_BAR_SIDE__CONFIG_LOGO_MARK_SIZE),
    )
    config_window.side_menu_config_window_title_logo.place(relx=0.08, rely=0.58, anchor="w")
