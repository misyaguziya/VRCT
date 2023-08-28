from .widgets import createConfigWindowTitle, createSettingBoxTitle, createSideMenuAndSettingsBoxContainers

from customtkinter import CTkToplevel

from ..ui_utils import setDefaultActiveTab

from config import config

class ConfigWindow(CTkToplevel):
    def __init__(self, vrct_gui, settings):
        super().__init__()
        self.withdraw()


        # configure window
        self.title("test config_window.py")
        self.geometry(f"{1080}x{680}")


        self.configure(fg_color="#ff7f50")
        self.protocol("WM_DELETE_WINDOW", vrct_gui.closeConfigWindow)




        createConfigWindowTitle(config_window=self, settings=settings)

        createSettingBoxTitle(config_window=self, settings=settings)


        createSideMenuAndSettingsBoxContainers(config_window=self, settings=settings)
