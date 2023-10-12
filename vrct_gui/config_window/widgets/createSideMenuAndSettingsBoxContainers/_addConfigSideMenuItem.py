from customtkinter import CTkFont, CTkFrame, CTkLabel

from ....ui_utils import bindEnterAndLeaveColor, bindButtonPressColor, bindButtonReleaseFunction, switchActiveTabAndPassiveTab, switchTabsColor

from utils import callFunctionIfCallable


def _addConfigSideMenuItem(config_window, settings, view_variable, side_menu_settings, side_menu_row, all_side_menu_tab_attr_name):


    def switchActiveAndPassiveSettingBoxContainerTabsColor(target_active_widget):

        setting_box_container_tabs = []
        for tab_attr_name in all_side_menu_tab_attr_name:
            tab_attr = getattr(config_window, tab_attr_name)
            setting_box_container_tabs.append(tab_attr)

        switchTabsColor(
            target_widget=target_active_widget,
            tab_buttons=setting_box_container_tabs,
            active_bg_color=settings.ctm.SIDE_MENU_LABELS_BG_COLOR,
            active_text_color=settings.ctm.SIDE_MENU_LABELS_SELECTED_TEXT_COLOR,
            passive_bg_color=settings.ctm.SIDE_MENU_LABELS_BG_COLOR,
            passive_text_color=settings.ctm.LABELS_TEXT_COLOR
        )

        for setting_box_container_tab in setting_box_container_tabs:
            setting_box_container_tab.children["!ctkframe"].place(relx=-1)

        target_active_widget.children["!ctkframe"].place(relx=0)




    def switchSettingBoxContainerTabFunction(target_active_widget):
        switchActiveAndPassiveSettingBoxContainerTabsColor(target_active_widget)
        switchActiveTabAndPassiveTab(target_active_widget, config_window.current_active_side_menu_tab, config_window.current_active_side_menu_tab.passive_function, settings.ctm.SIDE_MENU_LABELS_HOVERED_BG_COLOR, settings.ctm.SIDE_MENU_LABELS_CLICKED_BG_COLOR, settings.ctm.SIDE_MENU_LABELS_BG_COLOR)
        config_window.current_active_side_menu_tab = target_active_widget






    def switchSettingBoxContainer(target_setting_box_container_attr_name):
        config_window.current_active_setting_box_container.grid_remove()
        config_window.current_active_setting_box_container = getattr(config_window, target_setting_box_container_attr_name)
        config_window.current_active_setting_box_container.grid()

        # Move to the top position when the setting box is switched.
        config_window.main_setting_box_scrollable_container._parent_canvas.yview_moveto("0")


    def switchToTargetSettingBoxContainer(textvariable, target_active_tab_widget_attr_name, target_setting_box_container_attr_name):
        view_variable.VAR_CURRENT_ACTIVE_CONFIG_TITLE.set(textvariable.get())
        target_active_tab_widget = getattr(config_window, target_active_tab_widget_attr_name)
        switchSettingBoxContainerTabFunction(target_active_tab_widget)
        switchSettingBoxContainer(target_setting_box_container_attr_name)
        callFunctionIfCallable(view_variable.CALLBACK_SELECTED_SETTING_BOX_TAB, target_active_tab_widget_attr_name)





    side_menu_tab_attr_name = side_menu_settings["side_menu_tab_attr_name"]
    label_attr_name = side_menu_settings["label_attr_name"]
    selected_mark_attr_name = side_menu_settings["selected_mark_attr_name"]
    textvariable = side_menu_settings["textvariable"]
    setting_box_container_attr_name = side_menu_settings["setting_box_container_settings"]["setting_box_container_attr_name"]
    command = lambda _e: switchToTargetSettingBoxContainer(
        textvariable=textvariable,
        target_active_tab_widget_attr_name=side_menu_tab_attr_name,
        target_setting_box_container_attr_name=setting_box_container_attr_name,
    )


    # Side menu
    frame_widget = CTkFrame(config_window.side_menu_container, corner_radius=0, fg_color=settings.ctm.SIDE_MENU_LABELS_BG_COLOR, cursor="hand2", width=0, height=0)
    setattr(config_window, side_menu_tab_attr_name, frame_widget)

    frame_widget.grid(row=side_menu_row, column=0, pady=(0,1), sticky="ew")
    frame_widget.grid_columnconfigure(0, weight=1)

    label_widget = CTkLabel(
        frame_widget,
        textvariable=textvariable,
        height=0,
        corner_radius=0,
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SIDE_MENU_LABELS_FONT_SIZE, weight="normal"),
        anchor="w",
        text_color=settings.ctm.LABELS_TEXT_COLOR,
    )
    setattr(config_window, label_attr_name, label_widget)

    selected_mark_widget = CTkFrame(frame_widget, corner_radius=0, fg_color=settings.ctm.SIDE_MENU_SELECTED_MARK_ACTIVE_BG_COLOR, width=3, height=0)
    setattr(config_window, selected_mark_attr_name, selected_mark_widget)


    # Arrange
    selected_mark_widget.place(relx=-1, rely=0.5, relheight=1, anchor="w")
    label_widget.grid(row=0, column=0, padx=settings.uism.SIDE_MENU_LABELS_IPADX, pady=settings.uism.SIDE_MENU_LABELS_IPADY, sticky="ew")

    bindEnterAndLeaveColor([frame_widget, label_widget], settings.ctm.SIDE_MENU_LABELS_HOVERED_BG_COLOR, settings.ctm.SIDE_MENU_LABELS_BG_COLOR)
    bindButtonPressColor([frame_widget, label_widget], settings.ctm.SIDE_MENU_LABELS_CLICKED_BG_COLOR, settings.ctm.SIDE_MENU_LABELS_BG_COLOR)

    frame_widget.passive_function = command
    bindButtonReleaseFunction([frame_widget, label_widget], command)
