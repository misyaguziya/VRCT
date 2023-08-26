
from customtkinter import CTkFrame, CTkLabel, CTkImage

from ...ui_utils import getImageFileFromUiUtils, bindEnterAndLeaveColor, bindButtonPressColor, bindButtonReleaseFunction

from .create_sidebar import createSidebar


def createMinimizeSidebarButton(settings, main_window):

    def enableCompactMode(e):
        settings.IS_SIDEBAR_COMPACT_MODE = True
        main_window.minimize_sidebar_button_container.destroy()
        createMinimizeSidebarButton(settings, main_window)
        main_window.sidebar_bg_container.destroy()
        createSidebar(settings, main_window)

    def disableCompactMode(e):
        settings.IS_SIDEBAR_COMPACT_MODE = False
        main_window.minimize_sidebar_button_container.destroy()
        createMinimizeSidebarButton(settings, main_window)
        main_window.sidebar_bg_container.destroy()
        createSidebar(settings, main_window)


    main_window.minimize_sidebar_button_container = CTkFrame(main_window.main_topbar_container, corner_radius=0, fg_color=settings.ctm.MINIMIZE_SIDEBAR_BUTTON_BG_COLOR, cursor="hand2", width=0, height=0)



    main_window.minimize_sidebar_button = CTkLabel(
        main_window.minimize_sidebar_button_container,
        text=None,
        corner_radius=0,
        height=0,
        image=CTkImage(getImageFileFromUiUtils(settings.image_filename.ARROW_LEFT),size=(settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_X,settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_Y))
    )


    if settings.IS_SIDEBAR_COMPACT_MODE is True:
        image_file = CTkImage(getImageFileFromUiUtils(settings.image_filename.ARROW_LEFT).rotate(180),size=(settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_X,settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_Y))
        bindButtonReleaseFunction([main_window.minimize_sidebar_button_container, main_window.minimize_sidebar_button], disableCompactMode)

    else:
        image_file = CTkImage(getImageFileFromUiUtils(settings.image_filename.ARROW_LEFT),size=(settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_X,settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_Y))
        bindButtonReleaseFunction([main_window.minimize_sidebar_button_container, main_window.minimize_sidebar_button], enableCompactMode)

    main_window.minimize_sidebar_button_container.grid_rowconfigure((0,2), weight=1)
    main_window.minimize_sidebar_button.configure(image=image_file)
    main_window.minimize_sidebar_button_container.grid(row=0, column=0, sticky="nsw")
    main_window.minimize_sidebar_button.grid(row=1, column=0, padx=0, pady=0)


    bindEnterAndLeaveColor([main_window.minimize_sidebar_button, main_window.minimize_sidebar_button_container], settings.ctm.MINIMIZE_SIDEBAR_BUTTON_HOVERED_BG_COLOR, settings.ctm.MINIMIZE_SIDEBAR_BUTTON_BG_COLOR)
    bindButtonPressColor([main_window.minimize_sidebar_button, main_window.minimize_sidebar_button_container], settings.ctm.MINIMIZE_SIDEBAR_BUTTON_CLICKED_BG_COLOR, settings.ctm.MINIMIZE_SIDEBAR_BUTTON_BG_COLOR)




