from customtkinter import CTkOptionMenu, CTkFont, CTkFrame, CTkLabel, CTkSwitch, CTkImage, StringVar

from ...ui_utils import getImageFileFromUiUtils, openImageKeepAspectRatio, retag, getLatestHeight, bindEnterAndLeaveColor, bindButtonPressColor, bindEnterAndLeaveFunction, bindButtonReleaseFunction, bindButtonPressAndReleaseFunction, bindButtonFunctionAndColor, switchActiveTabAndPassiveTab, switchTabsColor

from utils import callFunctionIfCallable

from ._create_sidebar import createSidebarFeatures, createSidebarLanguagesSettings

def createSidebar(settings, main_window):
    #  Side Bar Container
    main_window.sidebar_bg_container = CTkFrame(main_window, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)
    main_window.sidebar_bg_container.grid(row=0, column=0, sticky="nsew")


    createSidebarFeatures(settings, main_window)
    createSidebarLanguagesSettings(settings, main_window)