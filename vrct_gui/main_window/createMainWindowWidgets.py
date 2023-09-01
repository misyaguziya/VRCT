from .widgets import createSidebar, createMinimizeSidebarButton, createTextbox, createEntryMessageBox

from customtkinter import CTkFrame

from ..ui_utils import createButtonWithImage, getImagePath


def createMainWindowWidgets(vrct_gui, settings, view_variable):
    vrct_gui.protocol("WM_DELETE_WINDOW", vrct_gui.quitVRCT)

    # self.IS_DEVELOPER_MODE = False
    # self.IS_DEVELOPER_MODE = True




    # self.YOUR_LANGUAGE = "Japanese\n(Japan)"
    # self.TARGET_LANGUAGE = "English\n(United States)"

    vrct_gui.iconbitmap(getImagePath("app.ico"))
    vrct_gui.title("VRCT")
    vrct_gui.geometry(f"{880}x{640}")
    vrct_gui.minsize(400, 175)


    # Main Container
    vrct_gui.grid_columnconfigure(1, weight=1)

    vrct_gui.configure(fg_color="#ff7f50")
    # return


    # Main Container
    vrct_gui.main_bg_container = CTkFrame(vrct_gui, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    vrct_gui.main_bg_container.grid(row=0, column=1, sticky="nsew")


    # top bar
    vrct_gui.main_bg_container.grid_columnconfigure(0, weight=1)
    vrct_gui.main_topbar_container = CTkFrame(vrct_gui.main_bg_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    vrct_gui.main_topbar_container.grid(row=0, column=0, sticky="ew")





    vrct_gui.main_topbar_container.columnconfigure(1,weight=1)
    vrct_gui.main_topbar_center_container = CTkFrame(vrct_gui.main_topbar_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    vrct_gui.main_topbar_center_container.grid(row=0, column=1, sticky="nsew")




    # Help and Info button
    vrct_gui.help_and_info_button_container = createButtonWithImage(
        parent_widget=vrct_gui.main_topbar_container,
        button_fg_color=settings.ctm.HELP_AND_INFO_BUTTON_BG_COLOR,
        button_enter_color=settings.ctm.HELP_AND_INFO_BUTTON_HOVERED_BG_COLOR,
        button_clicked_color=settings.ctm.HELP_AND_INFO_BUTTON_CLICKED_BG_COLOR,
        button_image_filename=settings.image_filename.HELP_ICON,
        button_image_size=settings.uism.HELP_AND_INFO_BUTTON_SIZE,
        button_ipadxy=settings.uism.HELP_AND_INFO_BUTTON_IPADXY,
        button_command=vrct_gui.openHelpAndInfoWindow,
        corner_radius=settings.uism.HELP_AND_INFO_BUTTON_CORNER_RADIUS,
    )
    vrct_gui.help_and_info_button_container.grid(row=0, column=3, padx=settings.uism.HELP_AND_INFO_BUTTON_PADX, pady=settings.uism.HELP_AND_INFO_BUTTON_PADY, sticky="e")

    createSidebar(settings, vrct_gui)

    createMinimizeSidebarButton(settings, vrct_gui)

    createTextbox(settings, vrct_gui)

    createEntryMessageBox(settings, vrct_gui)





    # def delete_window(self):
    #     self.vrct_gui.quit()
    #     self.vrct_gui.destroy()

    # def openConfigWindow(self, e):
    #     self.config_window.deiconify()
    #     self.config_window.focus_set()
    #     self.config_window.focus()
    #     self.config_window.grab_set()

    # def openHelpAndInfoWindow(self, e):
    #     self.information_window.deiconify()
    #     self.information_window.focus_set()
    #     self.information_window.focus()