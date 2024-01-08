from .widgets import createSidebar, createMinimizeSidebarButton, createTextbox, createEntryMessageBox

from customtkinter import CTkFrame, CTkLabel, CTkFont, CTkImage

from utils import callFunctionIfCallable
from ..ui_utils import createButtonWithImage, getImagePath, bindButtonFunctionAndColor

def createMainWindowWidgets(vrct_gui, settings, view_variable):
    vrct_gui.protocol("WM_DELETE_WINDOW", lambda: callFunctionIfCallable(view_variable.CALLBACK_DELETE_MAIN_WINDOW))


    vrct_gui.iconbitmap(getImagePath("vrct_logo_mark_black.ico"))
    vrct_gui.title("VRCT")


    # Main Container
    vrct_gui.grid_columnconfigure(0, weight=1)
    vrct_gui.grid_rowconfigure(0, weight=1)

    vrct_gui.configure(fg_color=settings.ctm.MAIN_BG_COLOR)

    vrct_gui.toplevel_wrapper = CTkFrame(vrct_gui, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    vrct_gui.toplevel_wrapper.grid(row=0, column=0, sticky="nsew")
    vrct_gui.toplevel_wrapper.grid_columnconfigure(1, weight=1)


    # Main Container
    vrct_gui.main_bg_container = CTkFrame(vrct_gui.toplevel_wrapper, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    vrct_gui.main_bg_container.grid(row=0, column=1, sticky="nsew")


    # top bar
    vrct_gui.main_bg_container.grid_columnconfigure(0, weight=1)
    vrct_gui.main_topbar_container = CTkFrame(vrct_gui.main_bg_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    vrct_gui.main_topbar_container.grid(row=0, column=0, sticky="ew")





    vrct_gui.main_topbar_container.grid_columnconfigure(1,weight=1)
    vrct_gui.main_topbar_center_container = CTkFrame(vrct_gui.main_topbar_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    vrct_gui.main_topbar_center_container.grid(row=0, column=1, sticky="nsew")



    # Main Top Bar Container - Right Side
    # start from 3
    main_topbar_column=3
    # Update Available Button
    vrct_gui.update_available_container = CTkFrame(
        vrct_gui.main_topbar_container,
        corner_radius=settings.uism.UPDATE_AVAILABLE_BUTTON_CORNER_RADIUS,
        fg_color=settings.ctm.MAIN_BG_COLOR,
        cursor="hand2",
    )
    vrct_gui.update_available_container.grid(row=0, column=main_topbar_column, padx=settings.uism.UPDATE_AVAILABLE_BUTTON_PADX, pady=settings.uism.TOP_BAR_BUTTON_PADY, sticky="nse")
    vrct_gui.update_available_container.grid_remove()
    main_topbar_column+=1


    vrct_gui.update_available_container.grid_rowconfigure((0,2), weight=1)

    vrct_gui.update_available_icon = CTkLabel(
        vrct_gui.update_available_container,
        text=None,
        corner_radius=0,
        height=0,
        image=CTkImage(settings.image_file.REFRESH_UPDATE_ICON.rotate(25), size=settings.uism.UPDATE_AVAILABLE_BUTTON_SIZE)
    )
    vrct_gui.update_available_icon.grid(row=1, column=0, padx=(settings.uism.UPDATE_AVAILABLE_BUTTON_IPADX, settings.uism.UPDATE_AVAILABLE_PADX_BETWEEN_LABEL_AND_ICON), pady=0)


    vrct_gui.update_available_label = CTkLabel(
        vrct_gui.update_available_container,
        textvariable=view_variable.VAR_UPDATE_AVAILABLE,
        height=0,
        corner_radius=0,
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.UPDATE_AVAILABLE_BUTTON_FONT_SIZE, weight="normal"),
        anchor="e",
        text_color=settings.ctm.UPDATE_AVAILABLE_BUTTON_TEXT_COLOR,
    )
    # This "right padx +1" is for fixing a bug that sticks out from the frame. I don't know why that happens...
    vrct_gui.update_available_label.grid(row=1, column=1, padx=(0,settings.uism.UPDATE_AVAILABLE_BUTTON_IPADX+1), pady=0)


    bindButtonFunctionAndColor(
        target_widgets=[
            vrct_gui.update_available_container,
            vrct_gui.update_available_label,
            vrct_gui.update_available_icon,
        ],
        enter_color=settings.ctm.TOP_BAR_BUTTON_HOVERED_BG_COLOR,
        leave_color=settings.ctm.TOP_BAR_BUTTON_BG_COLOR,
        clicked_color=settings.ctm.TOP_BAR_BUTTON_CLICKED_BG_COLOR,
        buttonReleasedFunction=lambda e: callFunctionIfCallable(view_variable.CALLBACK_CLICKED_UPDATE_AVAILABLE),
    )





    # Help and Info button
    vrct_gui.help_and_info_button_container = createButtonWithImage(
        parent_widget=vrct_gui.main_topbar_container,
        button_fg_color=settings.ctm.TOP_BAR_BUTTON_BG_COLOR,
        button_enter_color=settings.ctm.TOP_BAR_BUTTON_HOVERED_BG_COLOR,
        button_clicked_color=settings.ctm.TOP_BAR_BUTTON_CLICKED_BG_COLOR,
        button_image_file=settings.image_file.HELP_ICON,
        button_image_size=settings.uism.HELP_AND_INFO_BUTTON_SIZE,
        button_ipadxy=settings.uism.HELP_AND_INFO_BUTTON_IPADXY,
        button_command=lambda e: callFunctionIfCallable(view_variable.CALLBACK_CLICKED_HELP_AND_INFO),
        corner_radius=settings.uism.HELP_AND_INFO_BUTTON_CORNER_RADIUS,
    )
    vrct_gui.help_and_info_button_container.grid(row=0, column=main_topbar_column, padx=settings.uism.HELP_AND_INFO_BUTTON_PADX, pady=settings.uism.TOP_BAR_BUTTON_PADY, sticky="e")
    main_topbar_column+=1
    createSidebar(settings, vrct_gui, view_variable)

    createMinimizeSidebarButton(settings, vrct_gui, view_variable)

    createTextbox(settings, vrct_gui, view_variable)

    createEntryMessageBox(settings, vrct_gui, view_variable)