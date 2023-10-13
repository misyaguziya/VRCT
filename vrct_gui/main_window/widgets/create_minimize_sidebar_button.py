
from customtkinter import CTkFrame, CTkLabel, CTkImage

from ...ui_utils import bindEnterAndLeaveColor, bindButtonPressColor, bindButtonReleaseFunction

from utils import callFunctionIfCallable

def createMinimizeSidebarButton(settings, main_window, view_variable):

    def enableCompactMode(e):
        callFunctionIfCallable(view_variable.CALLBACK_ENABLE_MAIN_WINDOW_SIDEBAR_COMPACT_MODE)

    def disableCompactMode(e):
        callFunctionIfCallable(view_variable.CALLBACK_DISABLE_MAIN_WINDOW_SIDEBAR_COMPACT_MODE)



    main_window.minimize_sidebar_button_container__for_closing = CTkFrame(main_window.main_topbar_container, corner_radius=0, fg_color=settings.ctm.MINIMIZE_SIDEBAR_BUTTON_BG_COLOR, cursor="hand2", width=0, height=0)
    main_window.minimize_sidebar_button_container__for_opening = CTkFrame(main_window.main_topbar_container, corner_radius=0, fg_color=settings.ctm.MINIMIZE_SIDEBAR_BUTTON_BG_COLOR, cursor="hand2", width=0, height=0)




    # For Closing [<]
    main_window.minimize_sidebar_button__for_closing = CTkLabel(
        main_window.minimize_sidebar_button_container__for_closing,
        text=None,
        corner_radius=0,
        height=0,
        image=CTkImage((settings.image_file.ARROW_LEFT),size=(settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_X,settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_Y))
    )

    main_window.minimize_sidebar_button_container__for_closing.grid_rowconfigure((0,2), weight=1)
    main_window.minimize_sidebar_button__for_closing.grid(row=1, column=0, padx=0, pady=0)


    bindEnterAndLeaveColor([main_window.minimize_sidebar_button__for_closing, main_window.minimize_sidebar_button_container__for_closing], settings.ctm.MINIMIZE_SIDEBAR_BUTTON_HOVERED_BG_COLOR, settings.ctm.MINIMIZE_SIDEBAR_BUTTON_BG_COLOR)
    bindButtonPressColor([main_window.minimize_sidebar_button__for_closing, main_window.minimize_sidebar_button_container__for_closing], settings.ctm.MINIMIZE_SIDEBAR_BUTTON_CLICKED_BG_COLOR, settings.ctm.MINIMIZE_SIDEBAR_BUTTON_BG_COLOR)
    bindButtonReleaseFunction([main_window.minimize_sidebar_button_container__for_closing, main_window.minimize_sidebar_button__for_closing], enableCompactMode)




# For Opening [>]
    main_window.minimize_sidebar_button__for_opening = CTkLabel(
        main_window.minimize_sidebar_button_container__for_opening,
        text=None,
        corner_radius=0,
        height=0,
        image=CTkImage((settings.image_file.ARROW_LEFT).rotate(180),size=(settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_X,settings.uism.MINIMIZE_SIDEBAR_BUTTON_ICON_SIZE_Y))
    )




    main_window.minimize_sidebar_button_container__for_opening.grid_rowconfigure((0,2), weight=1)
    main_window.minimize_sidebar_button__for_opening.grid(row=1, column=0, padx=0, pady=0)


    bindEnterAndLeaveColor([main_window.minimize_sidebar_button__for_opening, main_window.minimize_sidebar_button_container__for_opening], settings.ctm.MINIMIZE_SIDEBAR_BUTTON_HOVERED_BG_COLOR, settings.ctm.MINIMIZE_SIDEBAR_BUTTON_BG_COLOR)
    bindButtonPressColor([main_window.minimize_sidebar_button__for_opening, main_window.minimize_sidebar_button_container__for_opening], settings.ctm.MINIMIZE_SIDEBAR_BUTTON_CLICKED_BG_COLOR, settings.ctm.MINIMIZE_SIDEBAR_BUTTON_BG_COLOR)
    bindButtonReleaseFunction([main_window.minimize_sidebar_button_container__for_opening, main_window.minimize_sidebar_button__for_opening], disableCompactMode)





    main_window.minimize_sidebar_button_container__for_opening.grid(row=0, column=0, sticky="nsw")
    main_window.minimize_sidebar_button_container__for_closing.grid(row=0, column=0, sticky="nsw")
    main_window.minimize_sidebar_button_container__for_opening.grid_remove()