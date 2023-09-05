from customtkinter import CTkOptionMenu, CTkFont, CTkFrame, CTkLabel, CTkImage

from ....ui_utils import getImageFileFromUiUtils, bindEnterAndLeaveColor, bindButtonPressColor, bindButtonReleaseFunction, bindButtonFunctionAndColor, switchActiveTabAndPassiveTab, switchTabsColor

from utils import callFunctionIfCallable


def createSidebarLanguagesSettings(settings, main_window, view_variable):


    def switchActiveAndPassivePresetsTabsColor(target_active_widget):
        quick_setting_tabs = [
            getattr(main_window, "sls__presets_button_1"),
            getattr(main_window, "sls__presets_button_2"),
            getattr(main_window, "sls__presets_button_3")
        ]

        switchTabsColor(
            target_widget=target_active_widget,
            tab_buttons=quick_setting_tabs,
            active_bg_color=settings.ctm.SLS__PRESETS_TAB_BG_ACTIVE_COLOR,
            active_text_color=settings.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR,
            passive_bg_color=settings.ctm.SIDEBAR_BG_COLOR,
            passive_text_color=settings.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR_PASSIVE
        )

    def switchPresetTabFunction(target_active_widget):
        switchActiveAndPassivePresetsTabsColor(target_active_widget)
        switchActiveTabAndPassiveTab(target_active_widget, main_window.current_active_preset_tab, main_window.current_active_preset_tab.passive_function, settings.ctm.SLS__PRESETS_TAB_BG_HOVERED_COLOR, settings.ctm.SLS__PRESETS_TAB_BG_CLICKED_COLOR, settings.ctm.SLS__PRESETS_TAB_BG_PASSIVE_COLOR)

        main_window.sls__optionmenu_your_language.set(view_variable.VAR_YOUR_LANGUAGE.get())
        main_window.sls__optionmenu_target_language.set(view_variable.VAR_TARGET_LANGUAGE.get())
        main_window.current_active_preset_tab = target_active_widget



    def switchToPreset1(e):
        print("1")
        callFunctionIfCallable(view_variable.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB, "1")
        target_active_widget = getattr(main_window, "sls__presets_button_1")
        switchPresetTabFunction(target_active_widget)

    def switchToPreset2(e):
        print("2")
        callFunctionIfCallable(view_variable.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB, "2")
        target_active_widget = getattr(main_window, "sls__presets_button_2")
        switchPresetTabFunction(target_active_widget)

    def switchToPreset3(e):
        print("3")
        callFunctionIfCallable(view_variable.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB, "3")
        target_active_widget = getattr(main_window, "sls__presets_button_3")
        switchPresetTabFunction(target_active_widget)





    def createOption_DropdownMenu_for_quickSettings(setattr_obj, parent_widget, optionmenu_attr_name, dropdown_menu_attr_name, dropdown_menu_values=None, width:int = 200, font_size:int = 10, text_color="white", command=None, variable=""):
        setattr(setattr_obj, optionmenu_attr_name, CTkOptionMenu(
            parent_widget,
            height=30,
            width=width,
            values=dropdown_menu_values,
            button_color=settings.ctm.SLS__DROPDOWN_MENU_BG_COLOR,
            fg_color=settings.ctm.SLS__DROPDOWN_MENU_BG_COLOR,
            text_color=text_color,
            font=CTkFont(family=settings.FONT_FAMILY, size=font_size, weight="normal"),
            variable=variable,
            anchor="center",
        ))
        target_optionmenu_attr = getattr(setattr_obj, optionmenu_attr_name)
        target_optionmenu_attr.grid(row=0, column=0, sticky="e")




    def createQuickLanguageSettingBox(parent_widget, var_title_text, title_text_attr_name, optionmenu_attr_name, dropdown_menu_attr_name, dropdown_menu_values, variable):
        sls__box = CTkFrame(parent_widget, corner_radius=0, fg_color=settings.ctm.SLS__BOX_BG_COLOR, width=0, height=0)

        sls__box.columnconfigure((0,2), weight=1)

        sls__box_wrapper = CTkFrame(sls__box, corner_radius=0, fg_color=settings.ctm.SLS__BOX_BG_COLOR, width=0, height=0)
        sls__box_wrapper.grid(row=2, column=1, padx=0, pady=settings.uism.SLS__BOX_IPADY)

        sls__label = CTkLabel(
            sls__box_wrapper,
            textvariable=var_title_text,
            height=0,
            font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SLS__BOX_SECTION_TITLE_FONT_SIZE, weight="normal"),
            text_color=settings.ctm.SLS__BOX_SECTION_TITLE_TEXT_COLOR
        )
        sls__label.grid(row=0, column=0, pady=(0,settings.uism.SLS__BOX_SECTION_TITLE_BOTTOM_PADY))
        setattr(main_window, title_text_attr_name, sls__label)




        createOption_DropdownMenu_for_quickSettings(
            main_window,
            sls__box_wrapper,
            optionmenu_attr_name,
            dropdown_menu_attr_name,
            dropdown_menu_values=dropdown_menu_values,
            # command=self.fakeCommand,
            width=settings.uism.SLS__BOX_DROPDOWN_MENU_WIDTH,
            font_size=settings.uism.SLS__BOX_DROPDOWN_MENU_FONT_SIZE,
            text_color=settings.ctm.LABELS_TEXT_COLOR,
            variable=variable,
            # variable=StringVar(value="Chinese, Cantonese\n(Traditional Hong Kong)"),
        )
        getattr(main_window, optionmenu_attr_name).grid(row=1, column=0, padx=0, pady=0)

        return sls__box





    # Sidebar Languages Settings, SLS
    main_window.sls__container = CTkFrame(main_window.sidebar_bg_container, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)

    main_window.sls__container.grid(row=2, column=0, sticky="new")

    main_window.sls__container.grid_columnconfigure(0, weight=1)


    main_window.sls__container_title = CTkLabel(main_window.sls__container,
        textvariable=view_variable.VAR_LABEL_LANGUAGE_SETTINGS,
        height=0,
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SLS__TITLE_FONT_SIZE, weight="normal"),
        text_color=settings.ctm.SLS__TITLE_TEXT_COLOR
    )
    main_window.sls__container_title.grid(row=0, column=0, pady=settings.uism.SLS__TITLE_PADY, sticky="nsew")



    # Presets buttons
    main_window.sidebar_bg_container.grid_rowconfigure(2, weight=1)
    main_window.sls__presets_buttons_box = CTkFrame(main_window.sls__container, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)
    main_window.sls__presets_buttons_box.grid(row=1, column=0, sticky="ew")

    main_window.sls__presets_buttons_box.grid_columnconfigure((0,1,2), weight=1)


    preset_tabs_settings = [
        {
            "preset_tab_attr_name": "sls__presets_button_1",
            "command": switchToPreset1,
            "text": "1",
        },
        {
            "preset_tab_attr_name": "sls__presets_button_2",
            "command": switchToPreset2,
            "text": "2",
        },
        {
            "preset_tab_attr_name": "sls__presets_button_3",
            "command": switchToPreset3,
            "text": "3",
        },
    ]

    column=0
    for preset_tab_settings in preset_tabs_settings:
        preset_tab_attr_name = preset_tab_settings["preset_tab_attr_name"]
        command = preset_tab_settings["command"]
        text = preset_tab_settings["text"]

        setattr(
            main_window,
            preset_tab_attr_name,
            CTkFrame(
                main_window.sls__presets_buttons_box,
                corner_radius=0,
                fg_color=settings.ctm.SLS__PRESETS_TAB_BG_PASSIVE_COLOR,
                width=0,
                height=30,
                cursor="hand2",
            )
        )
        parent_widget = getattr(main_window, preset_tab_attr_name)
        parent_widget.grid(row=0, column=column, sticky="ew")

        label_widget = CTkLabel(
            parent_widget,
            text=text,
            height=0,
            fg_color=settings.ctm.SLS__PRESETS_TAB_BG_PASSIVE_COLOR,
            font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SLS__PRESET_TAB_NUMBER_FONT_SIZE, weight="bold"),
            anchor="center",
            text_color=settings.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR_PASSIVE
        )
        label_widget.place(relx=0.5, rely=0.5, anchor="center")



        bindEnterAndLeaveColor([parent_widget, label_widget], settings.ctm.SLS__PRESETS_TAB_BG_HOVERED_COLOR, settings.ctm.SLS__PRESETS_TAB_BG_PASSIVE_COLOR)
        bindButtonPressColor([parent_widget, label_widget], settings.ctm.SLS__PRESETS_TAB_BG_CLICKED_COLOR, settings.ctm.SLS__PRESETS_TAB_BG_PASSIVE_COLOR)

        parent_widget.passive_function = command
        bindButtonReleaseFunction([parent_widget, label_widget], command)

        column+=1


    # Quick Language settings BOX
    main_window.sls__box_frame = CTkFrame(main_window.sls__container, corner_radius=0, fg_color=settings.ctm.SLS__BG_COLOR, width=0, height=0)
    main_window.sls__box_frame.grid(row=2, column=0, sticky="ew")
    main_window.sls__box_frame.grid_columnconfigure(0, weight=1)

    # Your language
    main_window.sls__box_your_language = createQuickLanguageSettingBox(
        parent_widget=main_window.sls__box_frame,
        var_title_text=view_variable.VAR_LABEL_YOUR_LANGUAGE,
        title_text_attr_name="sls__title_text_your_language",
        optionmenu_attr_name="sls__optionmenu_your_language",
        dropdown_menu_attr_name="sls__dropdown_menu_your_language",
        dropdown_menu_values=["1""2","pppp\npppp"],
        variable=view_variable.VAR_YOUR_LANGUAGE
    )
    main_window.sls__box_your_language.grid(row=2, column=0, padx=0, pady=(settings.uism.SLS__BOX_TOP_PADY,0),sticky="ew")


    # Both direction arrow icon
    main_window.sls__arrow_direction_box = CTkFrame(main_window.sls__box_frame, corner_radius=0, fg_color=settings.ctm.SLS__BG_COLOR, width=0, height=0)
    main_window.sls__arrow_direction_box.grid(row=3, column=0, padx=0, pady=settings.uism.SLS__BOX_ARROWS_PADY,sticky="ew")

    main_window.sls__arrow_direction_box.grid_columnconfigure((0,4), weight=1)

    main_window.sls__both_direction_up = CTkLabel(
        main_window.sls__arrow_direction_box,
        text=None,
        height=0,
        image=CTkImage((settings.image_file.NARROW_ARROW_DOWN).rotate(180),size=settings.uism.SLS__BOX_ARROWS_IMAGE_SIZE)

    )
    main_window.sls__both_direction_up.grid(row=0, column=1, pady=0)

    main_window.sls__both_direction_desc = CTkLabel(
        main_window.sls__arrow_direction_box,
        textvariable=view_variable.VAR_LABEL_BOTH_DIRECTION_DESC,
        height=0,
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SLS__BOX_ARROWS_DESC_FONT_SIZE, weight="normal"),
        text_color=settings.ctm.SLS__BOX_ARROWS_TEXT_COLOR,
    )
    main_window.sls__both_direction_desc.grid(row=0, column=2, padx=settings.uism.SLS__BOX_ARROWS_DESC_PADX, pady=0)

    main_window.sls__both_direction_label_down = CTkLabel(
        main_window.sls__arrow_direction_box,
        text=None,
        height=0,
        image=CTkImage((settings.image_file.NARROW_ARROW_DOWN).rotate(0),size=settings.uism.SLS__BOX_ARROWS_IMAGE_SIZE)

    )
    main_window.sls__both_direction_label_down.grid(row=0, column=3, pady=0)



    # Target language
    main_window.sls__box_target_language = createQuickLanguageSettingBox(
        parent_widget=main_window.sls__box_frame,
        var_title_text=view_variable.VAR_LABEL_TARGET_LANGUAGE,
        title_text_attr_name="sls__title_text_target_language",
        optionmenu_attr_name="sls__optionmenu_target_language",
        dropdown_menu_attr_name="sls__dropdown_menu_target_language",
        dropdown_menu_values=["1""2","pppp\npppp2"],
        variable=view_variable.VAR_TARGET_LANGUAGE
    )
    main_window.sls__box_target_language.grid(row=4, column=0, padx=0, pady=(0,0),sticky="ew")





    # Config Button
    main_window.sidebar_config_button_container = CTkFrame(main_window.sidebar_bg_container, corner_radius=0, fg_color=settings.ctm.CONFIG_BUTTON_BG_COLOR, width=0, height=0)
    main_window.sidebar_config_button_container.grid(row=3, column=0, sticky="ew")


    main_window.sidebar_config_button_container.grid_columnconfigure(0, weight=1)
    main_window.sidebar_config_button_wrapper = CTkFrame(main_window.sidebar_config_button_container, corner_radius=settings.uism.SIDEBAR_CONFIG_BUTTON_CORNER_RADIUS, fg_color=settings.ctm.CONFIG_BUTTON_BG_COLOR, height=0, width=0, cursor="hand2")
    main_window.sidebar_config_button_wrapper.grid(row=0, column=0, padx=settings.uism.SIDEBAR_CONFIG_BUTTON_PADX, pady=settings.uism.SIDEBAR_CONFIG_BUTTON_PADY, sticky="ew")




    main_window.sidebar_config_button_wrapper.grid_columnconfigure(0, weight=1)

    settings.uism.CONFIG_BUTTON_PADX= 0
    main_window.sidebar_config_button = CTkLabel(
        main_window.sidebar_config_button_wrapper,
        text=None,
        height=0,
        image=CTkImage((settings.image_file.CONFIGURATION_ICON),size=(settings.COMPACT_MODE_ICON_SIZE,settings.COMPACT_MODE_ICON_SIZE))
    )
    main_window.sidebar_config_button.grid(row=0, column=0, padx=0, pady=settings.uism.SIDEBAR_CONFIG_BUTTON_IPADY)


    bindButtonFunctionAndColor(
        target_widgets=[main_window.sidebar_config_button_wrapper, main_window.sidebar_config_button],
        enter_color=settings.ctm.CONFIG_BUTTON_HOVERED_BG_COLOR,
        leave_color=settings.ctm.CONFIG_BUTTON_BG_COLOR,
        clicked_color=settings.ctm.CONFIG_BUTTON_CLICKED_BG_COLOR,
        buttonReleasedFunction=main_window.openConfigWindow,
    )

