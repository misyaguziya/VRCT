from customtkinter import CTkFont, CTkFrame, CTkLabel, CTkImage

from ....ui_utils import bindEnterAndLeaveColor, bindButtonPressColor, bindButtonReleaseFunction, switchActiveTabAndPassiveTab, switchTabsColor

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
            passive_bg_color=settings.ctm.SLS__PRESETS_TAB_BG_PASSIVE_COLOR,
            passive_text_color=settings.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR_PASSIVE
        )

    def switchPresetTabFunction(target_active_widget):
        switchActiveAndPassivePresetsTabsColor(target_active_widget)
        switchActiveTabAndPassiveTab(target_active_widget, main_window.current_active_preset_tab, main_window.current_active_preset_tab.passive_function, settings.ctm.SLS__PRESETS_TAB_BG_HOVERED_COLOR, settings.ctm.SLS__PRESETS_TAB_BG_CLICKED_COLOR, settings.ctm.SLS__PRESETS_TAB_BG_PASSIVE_COLOR)
        main_window.current_active_preset_tab = target_active_widget



    def switchToPreset1(e):
        callFunctionIfCallable(view_variable.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB, "1")
        target_active_widget = getattr(main_window, "sls__presets_button_1")
        switchPresetTabFunction(target_active_widget)

    def switchToPreset2(e):
        callFunctionIfCallable(view_variable.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB, "2")
        target_active_widget = getattr(main_window, "sls__presets_button_2")
        switchPresetTabFunction(target_active_widget)

    def switchToPreset3(e):
        callFunctionIfCallable(view_variable.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB, "3")
        target_active_widget = getattr(main_window, "sls__presets_button_3")
        switchPresetTabFunction(target_active_widget)



    def createLanguageSettingBox(parent_widget, var_title_text, title_text_attr_name, arrow_img_attr_name, open_selectable_language_window_command, variable):
        sls__box = CTkFrame(parent_widget, corner_radius=0, fg_color=settings.ctm.SLS__BOX_BG_COLOR, width=0, height=0)

        sls__box.columnconfigure((0,2), weight=1)

        sls__box_wrapper = CTkFrame(sls__box, corner_radius=0, fg_color=settings.ctm.SLS__BOX_BG_COLOR, width=0, height=0)
        sls__box_wrapper.grid(row=2, column=1, padx=10, pady=settings.uism.SLS__BOX_IPADY)


        sls__label = CTkLabel(
            sls__box_wrapper,
            textvariable=var_title_text,
            height=0,
            font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SLS__BOX_SECTION_TITLE_FONT_SIZE, weight="normal"),
            text_color=settings.ctm.SLS__BOX_SECTION_TITLE_TEXT_COLOR
        )
        sls__label.grid(row=0, column=0, pady=(0,settings.uism.SLS__BOX_SECTION_TITLE_BOTTOM_PADY))
        setattr(main_window, title_text_attr_name, sls__label)





        sls__selected_language_box = CTkFrame(sls__box_wrapper, corner_radius=4, fg_color=settings.ctm.SLS__DROPDOWN_MENU_BG_COLOR, cursor="hand2")
        sls__selected_language_box.grid(row=1, column=0)


        sls__selected_language_box.columnconfigure(0, minsize=200)
        sls__selected_language_box.rowconfigure(0, minsize=30)
        sls__selected_language_label_frame = CTkFrame(sls__selected_language_box, corner_radius=0, fg_color=settings.ctm.SLS__DROPDOWN_MENU_BG_COLOR)
        sls__selected_language_label_frame.grid(row=0, column=0)

        sls__selected_language_label = CTkLabel(
            sls__selected_language_label_frame,
            textvariable=variable,
            height=0,
            # anchor="center",
            font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SLS__BOX_DROPDOWN_MENU_FONT_SIZE, weight="normal"),
            text_color=settings.ctm.LABELS_TEXT_COLOR
        )
        sls__selected_language_label.grid(row=0, column=0, pady=2)
        setattr(main_window, title_text_attr_name, sls__selected_language_label)


        sls__selected_language_arrow_img = CTkLabel(
            sls__selected_language_box,
            text=None,
            corner_radius=0,
            height=0,
            image=CTkImage((settings.image_file.ARROW_LEFT).rotate(180),size=(20,20))
        )
        setattr(main_window, arrow_img_attr_name, sls__selected_language_arrow_img)



        sls__selected_language_arrow_img.grid(row=0, column=1, padx=0, pady=0)




        bindEnterAndLeaveColor([sls__selected_language_label_frame, sls__selected_language_box, sls__selected_language_label, sls__selected_language_arrow_img], settings.ctm.SLS__DROPDOWN_MENU_HOVERED_BG_COLOR, settings.ctm.SLS__DROPDOWN_MENU_BG_COLOR)
        bindButtonPressColor([sls__selected_language_label_frame, sls__selected_language_box, sls__selected_language_label, sls__selected_language_arrow_img], settings.ctm.SLS__DROPDOWN_MENU_CLICKED_BG_COLOR, settings.ctm.SLS__DROPDOWN_MENU_HOVERED_BG_COLOR)



        bindButtonReleaseFunction([sls__selected_language_label_frame, sls__selected_language_box, sls__selected_language_label, sls__selected_language_arrow_img], open_selectable_language_window_command)

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
                corner_radius=4,
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


    def callbackOpenSelectableYourLanguageWindow(value):
        callFunctionIfCallable(view_variable.CALLBACK_OPEN_SELECTABLE_YOUR_LANGUAGE_WINDOW, value)


    def callbackOpenSelectableTargetLanguageWindow(value):
        callFunctionIfCallable(view_variable.CALLBACK_OPEN_SELECTABLE_TARGET_LANGUAGE_WINDOW, value)

    # Language Settings BOX
    main_window.sls__box_frame = CTkFrame(main_window.sls__container, corner_radius=0, fg_color=settings.ctm.SLS__BG_COLOR, width=0, height=0)
    main_window.sls__box_frame.grid(row=2, column=0, sticky="ew")
    main_window.sls__box_frame.grid_columnconfigure(0, weight=1)

    # Your language
    main_window.sls__box_your_language = createLanguageSettingBox(
        parent_widget=main_window.sls__box_frame,
        var_title_text=view_variable.VAR_LABEL_YOUR_LANGUAGE,
        title_text_attr_name="sls__title_text_your_language",
        arrow_img_attr_name="sls__arrow_img_your_language",
        open_selectable_language_window_command=callbackOpenSelectableYourLanguageWindow,
        variable=view_variable.VAR_YOUR_LANGUAGE
    )
    main_window.sls__box_your_language.grid(row=2, column=0, pady=(settings.uism.SLS__BOX_TOP_PADY,0),sticky="ew")


    # Both direction arrow icon
    main_window.sls__arrow_direction_box = CTkFrame(main_window.sls__box_frame, corner_radius=0, fg_color=settings.ctm.SLS__BG_COLOR, width=0, height=0)
    main_window.sls__arrow_direction_box.grid(row=3, column=0, pady=settings.uism.SLS__BOX_ARROWS_PADY,sticky="ew")

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
    main_window.sls__both_direction_desc.grid(row=0, column=2, padx=settings.uism.SLS__BOX_ARROWS_DESC_PADX)

    main_window.sls__both_direction_label_down = CTkLabel(
        main_window.sls__arrow_direction_box,
        text=None,
        height=0,
        image=CTkImage((settings.image_file.NARROW_ARROW_DOWN).rotate(0),size=settings.uism.SLS__BOX_ARROWS_IMAGE_SIZE)

    )
    main_window.sls__both_direction_label_down.grid(row=0, column=3)



    # Target language
    main_window.sls__box_target_language = createLanguageSettingBox(
        parent_widget=main_window.sls__box_frame,
        var_title_text=view_variable.VAR_LABEL_TARGET_LANGUAGE,
        title_text_attr_name="sls__title_text_target_language",
        arrow_img_attr_name="sls__arrow_img_target_language",
        open_selectable_language_window_command=callbackOpenSelectableTargetLanguageWindow,
        variable=view_variable.VAR_TARGET_LANGUAGE
    )
    main_window.sls__box_target_language.grid(row=4, column=0, sticky="ew")