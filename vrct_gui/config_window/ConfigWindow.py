from .widgets import createConfigWindowTitle, createSideMenuAndSettingsBoxContainers, createSettingBoxTopBar


from customtkinter import CTkToplevel

class ConfigWindow(CTkToplevel):
    def __init__(self, vrct_gui, settings, view_variable):
        super().__init__()
        self.withdraw()


        # configure window
        self.title("test config_window.py")
        self.geometry(f"{1080}x{680}")


        self.configure(fg_color="#ff7f50")
        self.protocol("WM_DELETE_WINDOW", vrct_gui.closeConfigWindow)

        self.settings = settings
        self.view_variable = view_variable


        createConfigWindowTitle(config_window=self, settings=settings)

        createSettingBoxTopBar(config_window=self, settings=settings)


        createSideMenuAndSettingsBoxContainers(config_window=self, settings=settings)




    def reloadConfigWindowSettingBoxContainer(self):
        self.main_bg_container.destroy()
        createSideMenuAndSettingsBoxContainers(config_window=self, settings=self.settings)