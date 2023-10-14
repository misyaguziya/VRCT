from customtkinter import CTkFrame

from ._createSettingBoxTitle import _createSettingBoxTitle
from ._createRestartButton import _createRestartButton
from ._createSettingBoxCompactModeButton import _createSettingBoxCompactModeButton

from ....ui_utils import getLatestHeight
from utils import isEven

def createSettingBoxTopBar(config_window, settings, view_variable):

    config_window.grid_columnconfigure(1, weight=1)
    config_window.setting_box_top_bar = CTkFrame(config_window, corner_radius=0, fg_color=settings.ctm.TOP_BAR_BG_COLOR, width=0, height=0)
    config_window.setting_box_top_bar.grid(row=0, column=1, sticky="nsew")


    config_window.setting_box_top_bar.grid_rowconfigure(0, weight=1)

    column_num=0
    _createSettingBoxTitle(parent_widget=config_window.setting_box_top_bar, config_window=config_window, settings=settings, view_variable=view_variable, column_num=column_num)
    column_num+=1

    config_window.setting_box_top_bar.grid_columnconfigure(column_num, weight=1)
    column_num+=1

    # Restart Button(Tmp)
    _createRestartButton(parent_widget=config_window.setting_box_top_bar, config_window=config_window, settings=settings, view_variable=view_variable, column_num=column_num)
    column_num+=1

    _createSettingBoxCompactModeButton(parent_widget=config_window.setting_box_top_bar, config_window=config_window, settings=settings, view_variable=view_variable, column_num=column_num)
    column_num+=1


    l_height = getLatestHeight(config_window.side_menu_config_window_title_logo_frame)
    if isEven(l_height) is False:
        config_window.grid_rowconfigure(0, weight=0, minsize=l_height+1)

    # for fixing 1px bug
    setting_box_top_bar_fix_1px_bug = CTkFrame(config_window.setting_box_top_bar, corner_radius=0, width=0, height=0)
    setting_box_top_bar_fix_1px_bug.grid(row=0, column=column_num, sticky="nse")