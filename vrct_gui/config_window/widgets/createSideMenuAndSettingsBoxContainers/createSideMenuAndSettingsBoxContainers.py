from customtkinter import CTkFrame

from ....ui_utils import setDefaultActiveTab, applyUiScalingAndFixTheBugScrollBar, CustomizedCTkScrollableFrame

from ._addConfigSideMenuItem import _addConfigSideMenuItem
from ._createSettingBoxContainer import _createSettingBoxContainer


from .setting_box_containers.setting_box_appearance import createSettingBox_Appearance
from .setting_box_containers.setting_box_transcription import createSettingBox_Mic, createSettingBox_Speaker
from .setting_box_containers.setting_box_others import createSettingBox_Others, createSettingBox_Others_SendMessageFormats, createSettingBox_Others_ReceivedMessageFormats, createSettingBox_Others_Additional
from .setting_box_containers.setting_box_advanced_settings import createSettingBox_AdvancedSettings
from .setting_box_containers.setting_box_translation import createSettingBox_Translation


def createSideMenuAndSettingsBoxContainers(config_window, settings, view_variable):

    # Main container
    config_window.main_bg_container = CTkFrame(config_window, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    config_window.main_bg_container.grid(row=1, column=1, sticky="nsew")

    config_window.main_bg_container.grid_columnconfigure(0, weight=1)
    config_window.main_bg_container.grid_rowconfigure(0, weight=0)




    # Side menu Base
    config_window.grid_rowconfigure(1, weight=1)
    config_window.side_menu_bg_container = CTkFrame(config_window, corner_radius=0, fg_color=settings.ctm.SIDE_MENU_BG_COLOR, width=0, height=0)
    config_window.side_menu_bg_container.grid(row=1, column=0, sticky="nsew")
    config_window.side_menu_bg_container.grid_columnconfigure(0, weight=1)

    config_window.side_menu_container = CTkFrame(config_window.side_menu_bg_container, corner_radius=0, fg_color=settings.ctm.SIDE_MENU_LABELS_BG_FOR_FAKE_BORDER_COLOR, width=0, height=0)
    config_window.side_menu_container.grid(row=0, column=0, padx=settings.uism.TOP_BAR_SIDE__TITLE_PADX, pady=(settings.uism.SIDE_MENU_TOP_PADY, 0), sticky="nsew")



    # Setting box container
    config_window.main_bg_container.grid_rowconfigure(1, weight=1)
    config_window.main_setting_box_scrollable_container = CustomizedCTkScrollableFrame(config_window.main_bg_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR)
    config_window.main_setting_box_scrollable_container.grid(row=1, column=0, sticky="nsew")

    applyUiScalingAndFixTheBugScrollBar(
        scrollbar_widget=config_window.main_setting_box_scrollable_container,
        padx=settings.uism.SCROLLBAR_IPADX,
        width=settings.uism.SCROLLBAR_WIDTH,
    )


    config_window.main_setting_box_bg_wrapper = CTkFrame(config_window.main_setting_box_scrollable_container, corner_radius=0, width=0, height=0, fg_color=settings.ctm.MAIN_BG_COLOR)
    config_window.main_setting_box_bg_wrapper.grid(row=0, column=0, pady=settings.uism.SB__BOTTOM_MARGIN, sticky="n")



    side_menu_and_setting_box_containers_settings = [
        {
            "side_menu_tab_attr_name": "side_menu_tab_appearance",
            "label_attr_name": "label_appearance",
            "selected_mark_attr_name": "selected_mark_appearance",
            "textvariable": view_variable.VAR_SIDE_MENU_LABEL_APPEARANCE,
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_appearance",
                "setting_boxes": [
                    { "var_section_title": None, "setting_box": createSettingBox_Appearance },
                ]
            },
        },
        {
            "side_menu_tab_attr_name": "side_menu_tab_translation",
            "label_attr_name": "label_translation",
            "selected_mark_attr_name": "selected_mark_translation",
            "textvariable": view_variable.VAR_SIDE_MENU_LABEL_TRANSLATION,
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_translation",
                "setting_boxes": [
                    { "var_section_title": None, "setting_box": createSettingBox_Translation },
                ]
            },
        },
        {
            "side_menu_tab_attr_name": "side_menu_tab_transcription",
            "label_attr_name": "label_transcription",
            "selected_mark_attr_name": "selected_mark_transcription",
            "textvariable": view_variable.VAR_SIDE_MENU_LABEL_TRANSCRIPTION,
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_transcription",
                "setting_boxes": [
                    {
                        "var_section_title": view_variable.VAR_SECOND_TITLE_TRANSCRIPTION_MIC,
                        "setting_box": createSettingBox_Mic
                    },
                    {
                        "var_section_title": view_variable.VAR_SECOND_TITLE_TRANSCRIPTION_SPEAKER,
                        "setting_box": createSettingBox_Speaker
                    },
                ]
            },
        },
        {
            "side_menu_tab_attr_name": "side_menu_tab_others",
            "label_attr_name": "label_others",
            "selected_mark_attr_name": "selected_mark_others",
            "textvariable": view_variable.VAR_SIDE_MENU_LABEL_OTHERS,
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_others",
                "setting_boxes": [
                    { "var_section_title": None, "setting_box": createSettingBox_Others },
                    { "var_section_title": view_variable.VAR_SECOND_TITLE_OTHERS_SEND_MESSAGE_FORMATS, "setting_box": createSettingBox_Others_SendMessageFormats },
                    { "var_section_title": view_variable.VAR_SECOND_TITLE_OTHERS_RECEIVED_MESSAGE_FORMATS, "setting_box": createSettingBox_Others_ReceivedMessageFormats },
                    { "var_section_title": view_variable.VAR_SECOND_TITLE_OTHERS_SPEAKER2CHATBOX, "setting_box": createSettingBox_Others_Additional },
                ]
            },
        },
        {
            "side_menu_tab_attr_name": "side_menu_tab_advanced",
            "label_attr_name": "label_advanced",
            "selected_mark_attr_name": "selected_mark_advanced",
            "textvariable": view_variable.VAR_SIDE_MENU_LABEL_ADVANCED_SETTINGS,
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_advanced",
                "setting_boxes": [
                    { "var_section_title": None, "setting_box": createSettingBox_AdvancedSettings },
                ]
            },
        },
    ]

    all_side_menu_tab_attr_name = [item["side_menu_tab_attr_name"] for item in side_menu_and_setting_box_containers_settings]

    side_menu_row=0
    for sm_and_sbc_setting in side_menu_and_setting_box_containers_settings:
        _addConfigSideMenuItem(
            config_window=config_window,
            settings=settings,
            view_variable=view_variable,
            side_menu_settings=sm_and_sbc_setting,
            side_menu_row=side_menu_row,
            all_side_menu_tab_attr_name=all_side_menu_tab_attr_name,
        )
        side_menu_row+=1


        _createSettingBoxContainer(
            config_window=config_window,
            settings=settings,
            view_variable=view_variable,
            setting_box_container_settings=sm_and_sbc_setting["setting_box_container_settings"],

        )


        if sm_and_sbc_setting["side_menu_tab_attr_name"] == view_variable.ACTIVE_SETTING_BOX_TAB_ATTR_NAME:
            # Set default active side menu tab
            view_variable.VAR_CURRENT_ACTIVE_CONFIG_TITLE.set(sm_and_sbc_setting["textvariable"].get())
            config_window.current_active_side_menu_tab = getattr(config_window, sm_and_sbc_setting["side_menu_tab_attr_name"])
            setDefaultActiveTab(
                active_tab_widget=config_window.current_active_side_menu_tab,
                active_bg_color=settings.ctm.SIDE_MENU_LABELS_BG_COLOR,
                active_text_color=settings.ctm.SIDE_MENU_LABELS_SELECTED_TEXT_COLOR
            )
            config_window.current_active_side_menu_tab.children["!ctkframe"].place(relx=0)

            # Set default active setting box container
            config_window.current_active_setting_box_container = getattr(config_window, sm_and_sbc_setting["setting_box_container_settings"]["setting_box_container_attr_name"])
            config_window.current_active_setting_box_container.grid()