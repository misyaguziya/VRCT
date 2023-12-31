from customtkinter import CTkFrame, CTkLabel, CTkImage

from ...ui_utils import bindButtonFunctionAndColor
from utils import callFunctionIfCallable

from ._create_sidebar import createSidebarFeatures, createSidebarLanguagesSettings

def createSidebar(settings, main_window, view_variable):
    #  Side Bar Container
    main_window.toplevel_wrapper.grid_rowconfigure(0, weight=1)

    main_window.sidebar_bg_container_wrapper = CTkFrame(main_window.toplevel_wrapper, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)
    main_window.sidebar_bg_container_wrapper.grid(row=0, column=0, sticky="nsew")


    main_window.sidebar_bg_container = CTkFrame(main_window.sidebar_bg_container_wrapper, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)
    main_window.sidebar_compact_mode_bg_container = CTkFrame(main_window.sidebar_bg_container_wrapper, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)


    main_window.sidebar_bg_container.grid_columnconfigure(0, weight=1, minsize=settings.uism.SIDEBAR_MIN_WIDTH)
    main_window.sidebar_compact_mode_bg_container.grid_columnconfigure(0, weight=1)


    createSidebarFeatures(settings, main_window, view_variable)
    createSidebarLanguagesSettings(settings, main_window, view_variable)


    main_window.sidebar_bg_container.grid(row=0, column=0, sticky="nsew")
    main_window.sidebar_compact_mode_bg_container.grid(row=0, column=0, sticky="nsew")
    main_window.sidebar_compact_mode_bg_container.grid_remove()


    # Config Button
    main_window.sidebar_bg_container_wrapper.grid_rowconfigure(3, weight=1)

    main_window.sidebar_config_button_container = CTkFrame(main_window.sidebar_bg_container_wrapper, corner_radius=0, fg_color=settings.ctm.CONFIG_BUTTON_BG_COLOR, width=0, height=0)
    main_window.sidebar_config_button_container.grid(row=4, column=0, sticky="sew")


    main_window.sidebar_config_button_container.grid_columnconfigure(0, weight=1)
    main_window.sidebar_config_button_wrapper = CTkFrame(main_window.sidebar_config_button_container, corner_radius=settings.uism.SIDEBAR_CONFIG_BUTTON_CORNER_RADIUS, fg_color=settings.ctm.CONFIG_BUTTON_BG_COLOR, height=0, width=0, cursor="hand2")
    main_window.sidebar_config_button_wrapper.grid(row=0, column=0, padx=settings.uism.SIDEBAR_CONFIG_BUTTON_PADX, pady=settings.uism.SIDEBAR_CONFIG_BUTTON_PADY, sticky="ew")




    main_window.sidebar_config_button_wrapper.grid_columnconfigure(0, weight=1)

    main_window.sidebar_config_button = CTkLabel(
        main_window.sidebar_config_button_wrapper,
        text=None,
        height=0,
        image=CTkImage(settings.image_file.CONFIGURATION_ICON, size=settings.uism.SIDEBAR_CONFIG_BUTTON_IMAGE_SIZE)
    )
    main_window.sidebar_config_button.grid(row=0, column=0, padx=0, pady=settings.uism.SIDEBAR_CONFIG_BUTTON_IPADY)


    bindButtonFunctionAndColor(
        target_widgets=[main_window.sidebar_config_button_wrapper, main_window.sidebar_config_button],
        enter_color=settings.ctm.CONFIG_BUTTON_HOVERED_BG_COLOR,
        leave_color=settings.ctm.CONFIG_BUTTON_BG_COLOR,
        clicked_color=settings.ctm.CONFIG_BUTTON_CLICKED_BG_COLOR,
        buttonReleasedFunction=lambda _e: callFunctionIfCallable(view_variable.CALLBACK_CLICKED_OPEN_CONFIG_WINDOW_BUTTON),
    )