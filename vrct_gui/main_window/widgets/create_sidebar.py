from customtkinter import CTkFrame

from ._create_sidebar import createSidebarFeatures, createSidebarLanguagesSettings

def createSidebar(settings, main_window):
    #  Side Bar Container
    main_window.grid_rowconfigure(0, weight=1)

    main_window.sidebar_bg_container = CTkFrame(main_window, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)
    main_window.sidebar_compact_mode_bg_container = CTkFrame(main_window, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)


    main_window.sidebar_bg_container.grid_columnconfigure(0, weight=0, minsize=settings.uism.SIDEBAR_WIDTH)
    main_window.sidebar_compact_mode_bg_container.grid_columnconfigure(0, weight=0, minsize=settings.uism.COMPACT_MODE_SIDEBAR_WIDTH)


    createSidebarFeatures(settings, main_window)
    createSidebarLanguagesSettings(settings, main_window)


    main_window.sidebar_bg_container.grid(row=0, column=0, sticky="nsew")
    main_window.sidebar_compact_mode_bg_container.grid(row=0, column=0, sticky="nsew")

    if main_window.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE:
        main_window.sidebar_bg_container.grid_remove()
    else:
        main_window.sidebar_compact_mode_bg_container.grid_remove()