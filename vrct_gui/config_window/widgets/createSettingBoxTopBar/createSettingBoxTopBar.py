from customtkinter import CTkFont, CTkFrame, CTkLabel

from ._createSettingBoxTitle import _createSettingBoxTitle
from ._createSettingBoxCompactModeButton import _createSettingBoxCompactModeButton

def createSettingBoxTopBar(config_window, settings):

    config_window.grid_columnconfigure(1, weight=1)
    config_window.setting_box_top_bar = CTkFrame(config_window, corner_radius=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR, width=0, height=0)
    config_window.setting_box_top_bar.grid(row=0, column=1, sticky="nsew")


    _createSettingBoxTitle(parent_widget=config_window.setting_box_top_bar, config_window=config_window, settings=settings)

    _createSettingBoxCompactModeButton(parent_widget=config_window.setting_box_top_bar, config_window=config_window, settings=settings)