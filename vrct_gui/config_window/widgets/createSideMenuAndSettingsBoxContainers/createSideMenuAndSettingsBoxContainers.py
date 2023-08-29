from customtkinter import CTkFrame, CTkScrollableFrame

from ....ui_utils import setDefaultActiveTab

from .addConfigSideMenuItem import addConfigSideMenuItem
from .createSettingBoxContainer import createSettingBoxContainer


from .setting_box_containers import createSettingBox_Appearance, createSettingBox_Translation, createSettingBox_Mic, createSettingBox_Speaker, createSettingBox_Others, createSettingBox_AdvancedSettings


def createSideMenuAndSettingsBoxContainers(config_window, settings):

    # Main container
    config_window.main_bg_container = CTkFrame(config_window, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    config_window.main_bg_container.grid(row=1, column=1, sticky="nsew")

    config_window.main_bg_container.grid_columnconfigure(0, weight=1)
    config_window.main_bg_container.grid_rowconfigure(0, weight=0)




    # Side menu Base
    config_window.grid_rowconfigure(1, weight=1)
    config_window.side_menu_bg_container = CTkFrame(config_window, corner_radius=0, fg_color=settings.ctm.SIDE_MENU_BG_COLOR, width=0, height=0)
    config_window.side_menu_bg_container.grid(row=1, column=0, sticky="nsew")


    config_window.side_menu_container = CTkFrame(config_window.side_menu_bg_container, corner_radius=0, fg_color=settings.ctm.SIDE_MENU_LABELS_BG_FOR_FAKE_BORDER_COLOR, width=0, height=0)
    config_window.side_menu_container.grid(row=0, column=0, padx=settings.uism.TOP_BAR_SIDE__TITLE_PADX, pady=(settings.uism.SIDE_MENU_TOP_PADY, 0))



    # Setting box container
    config_window.main_bg_container.grid_rowconfigure(1, weight=1)
    config_window.main_setting_box_scrollable_container = CTkScrollableFrame(config_window.main_bg_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR)
    config_window.main_setting_box_scrollable_container.grid(row=1, column=0, sticky="nsew")


    config_window.main_setting_box_bg_wrapper = CTkFrame(config_window.main_setting_box_scrollable_container, corner_radius=0, width=0, height=0, fg_color=settings.ctm.MAIN_BG_COLOR)
    config_window.main_setting_box_bg_wrapper.grid(row=0, column=0, pady=settings.uism.SB__BOTTOM_MARGIN, sticky="n")



    side_menu_and_setting_box_containers_settings = [
        {
            "side_menu_tab_attr_name": "side_menu_tab_appearance",
            "label_attr_name": "label_appearance",
            "selected_mark_attr_name": "selected_mark_appearance",
            "text": "Appearance",
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_appearance",
                "setting_boxes": [
                    { "section_title": None, "setting_box": createSettingBox_Appearance },
                ]
            },
        },
        {
            "side_menu_tab_attr_name": "side_menu_tab_translation",
            "label_attr_name": "label_translation",
            "selected_mark_attr_name": "selected_mark_translation",
            "text": "Translation",
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_translation",
                "setting_boxes": [
                    { "section_title": None, "setting_box": createSettingBox_Translation },
                ]
            },
        },
        {
            "side_menu_tab_attr_name": "side_menu_tab_transcription",
            "label_attr_name": "label_transcription",
            "selected_mark_attr_name": "selected_mark_transcription",
            "text": "Transcription",
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_transcription",
                "setting_boxes": [
                    { "section_title": "Mic", "setting_box": createSettingBox_Mic },
                    { "section_title": "Speaker", "setting_box": createSettingBox_Speaker },
                ]
            },
        },
        {
            "side_menu_tab_attr_name": "side_menu_tab_others",
            "label_attr_name": "label_others",
            "selected_mark_attr_name": "selected_mark_others",
            "text": "Others",
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_others",
                "setting_boxes": [
                    { "section_title": None, "setting_box": createSettingBox_Others },
                ]
            },
        },
        {
            "side_menu_tab_attr_name": "side_menu_tab_advanced",
            "label_attr_name": "label_advanced",
            "selected_mark_attr_name": "selected_mark_advanced",
            "text": "Advanced Settings",
            "setting_box_container_settings": {
                "setting_box_container_attr_name": "setting_box_container_advanced",
                "setting_boxes": [
                    { "section_title": None, "setting_box": createSettingBox_AdvancedSettings },
                ]
            },
            "activate_by_default": True,
        },
    ]

    all_side_menu_tab_attr_name = [item["side_menu_tab_attr_name"] for item in side_menu_and_setting_box_containers_settings]

    side_menu_row=0
    for sm_and_sbc_setting in side_menu_and_setting_box_containers_settings:
        addConfigSideMenuItem(
            config_window=config_window,
            settings=settings,
            side_menu_settings=sm_and_sbc_setting,
            side_menu_row=side_menu_row,
            all_side_menu_tab_attr_name=all_side_menu_tab_attr_name,
        )
        side_menu_row+=1


        createSettingBoxContainer(
            config_window=config_window,
            settings=settings,
            setting_box_container_settings=sm_and_sbc_setting["setting_box_container_settings"],

        )


        if sm_and_sbc_setting.get("activate_by_default", None) is not None:
            # Set default active side menu tab
            config_window.main_current_active_config_title.configure(text=sm_and_sbc_setting["text"])
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


