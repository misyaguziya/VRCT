from customtkinter import CTkOptionMenu, CTkFont, CTkFrame, CTkLabel, CTkSwitch, CTkImage, StringVar

from ...ui_utils import getImageFileFromUiUtils, openImageKeepAspectRatio, retag, getLatestHeight, bindEnterAndLeaveColor, bindButtonPressColor, bindEnterAndLeaveFunction, bindButtonReleaseFunction, bindButtonPressAndReleaseFunction, bindButtonFunctionAndColor, switchActiveTabAndPassiveTab, switchTabsColor

from utils import callFunctionIfCallable


def createSidebar(settings, main_window):

    def toggleSidebarFeatureSelectedMarkIfTurnedOn(is_turned_on, mark):
        mark.place(relx=0.85) if is_turned_on else mark.place(relx=-1)


    def toggleTranslationFeature():
        is_turned_on = main_window.translation_switch_box.get()
        callFunctionIfCallable(main_window.CALLBACK_TOGGLE_TRANSLATION, is_turned_on)
        toggleSidebarFeatureSelectedMarkIfTurnedOn(is_turned_on, main_window.translation_selected_mark)

    def toggleTranscriptionSendFeature():
        is_turned_on = main_window.transcription_send_switch_box.get()
        callFunctionIfCallable(main_window.CALLBACK_TOGGLE_TRANSCRIPTION_SEND, is_turned_on)
        toggleSidebarFeatureSelectedMarkIfTurnedOn(is_turned_on, main_window.transcription_send_selected_mark)

    def toggleTranscriptionReceiveFeature():
        is_turned_on = main_window.transcription_receive_switch_box.get()
        callFunctionIfCallable(main_window.CALLBACK_TOGGLE_TRANSCRIPTION_RECEIVE, is_turned_on)
        toggleSidebarFeatureSelectedMarkIfTurnedOn(is_turned_on, main_window.transcription_receive_selected_mark)

    def toggleForegroundFeature():
        is_turned_on = main_window.foreground_switch_box.get()
        callFunctionIfCallable(main_window.CALLBACK_TOGGLE_FOREGROUND, is_turned_on)
        toggleSidebarFeatureSelectedMarkIfTurnedOn(is_turned_on, main_window.foreground_selected_mark)




    def changeSidebarFeaturesColorByEvents(ww, event_name):
        target_frame_widget = getattr(main_window, ww)
        if event_name == "enter":
            target_frame_widget.configure(fg_color=settings.ctm.SF__HOVERED_BG_COLOR)
            target_frame_widget.children["!ctkswitch"].configure(fg_color=settings.ctm.SF__SWITCH_BOX_HOVERED_BG_COLOR, progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_HOVERED_BG_COLOR)
            target_frame_widget.children["!ctkframe"].configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_HOVERED_BG_COLOR)

        elif event_name == "leave":
            target_frame_widget.configure(fg_color=settings.ctm.SF__BG_COLOR)
            target_frame_widget.children["!ctkswitch"].configure(fg_color=settings.ctm.SF__SWITCH_BOX_BG_COLOR, progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_BG_COLOR)
            target_frame_widget.children["!ctkframe"].configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_BG_COLOR)

        elif event_name == "button_press":
            target_frame_widget.configure(fg_color=settings.ctm.SF__CLICKED_BG_COLOR)
            target_frame_widget.children["!ctkswitch"].configure(fg_color=settings.ctm.SF__SWITCH_BOX_CLICKED_BG_COLOR, progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_CLICKED_BG_COLOR)
            target_frame_widget.children["!ctkframe"].configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_CLICKED_BG_COLOR)

        elif event_name == "button_release":
            target_frame_widget.configure(fg_color=settings.ctm.SF__BG_COLOR)
            target_frame_widget.children["!ctkswitch"].configure(fg_color=settings.ctm.SF__SWITCH_BOX_BG_COLOR, progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_BG_COLOR)
            target_frame_widget.children["!ctkframe"].configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_BG_COLOR)





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

        main_window.sls__optionmenu_your_language.set(main_window.view_variable.VAR_YOUR_LANGUAGE.get())
        main_window.sls__optionmenu_target_language.set(main_window.view_variable.VAR_TARGET_LANGUAGE.get())
        main_window.current_active_preset_tab = target_active_widget



    def switchToPreset1(e):
        print("1")
        callFunctionIfCallable(main_window.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB, "1")
        target_active_widget = getattr(main_window, "sls__presets_button_1")
        switchPresetTabFunction(target_active_widget)

    def switchToPreset2(e):
        print("2")
        callFunctionIfCallable(main_window.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB, "2")
        target_active_widget = getattr(main_window, "sls__presets_button_2")
        switchPresetTabFunction(target_active_widget)

    def switchToPreset3(e):
        print("3")
        callFunctionIfCallable(main_window.CALLBACK_SELECTED_LANGUAGE_PRESET_TAB, "3")
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




    def createQuickLanguageSettingBox(parent_widget, title_text, title_text_attr_name, optionmenu_attr_name, dropdown_menu_attr_name, dropdown_menu_values, variable):
        sls__box = CTkFrame(parent_widget, corner_radius=0, fg_color=settings.ctm.SLS__BOX_BG_COLOR, width=0, height=0)

        sls__box.columnconfigure((0,2), weight=1)

        sls__box_wrapper = CTkFrame(sls__box, corner_radius=0, fg_color=settings.ctm.SLS__BOX_BG_COLOR, width=0, height=0)
        sls__box_wrapper.grid(row=2, column=1, padx=0, pady=settings.uism.SLS__BOX_IPADY)

        sls__label = CTkLabel(
            sls__box_wrapper,
            text=title_text,
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






    #  Side Bar Container
    main_window.sidebar_bg_container = CTkFrame(main_window, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)
    main_window.sidebar_bg_container.grid(row=0, column=0, sticky="nsew")


    MIN_SIDEBAR_WIDTH = settings.uism.COMPACT_MODE_SIDEBAR_WIDTH if main_window.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE is True else settings.uism.SIDEBAR_WIDTH
    main_window.sidebar_bg_container.grid_columnconfigure(0, weight=0, minsize=MIN_SIDEBAR_WIDTH)
    main_window.grid_rowconfigure(0, weight=1)


    (img, width, height) = openImageKeepAspectRatio(settings.image_filename.VRCT_LOGO, settings.uism.SF__LOGO_MAX_SIZE)
    main_window.sidebar_logo = CTkLabel(
        main_window.sidebar_bg_container,
        fg_color=settings.ctm.SIDEBAR_BG_COLOR,
        text=None,
        height=0,
        image=CTkImage(img, size=(width,height))
    )

    # "height-a_s" represents the adjustment in size, and the "pady+a_s/2" indicates a padding increase of 4 pixels to compensate for the reduction.
    a_s = settings.uism.SF__LOGO_HEIGHT_FOR_ADJUSTMENT
    (img, width, height) = openImageKeepAspectRatio(settings.image_filename.VRCT_LOGO_MARK, height-a_s)
    main_window.sidebar_compact_mode_logo = CTkLabel(
        main_window.sidebar_bg_container,
        fg_color=settings.ctm.SIDEBAR_BG_COLOR,
        text=None,
        height=0,
        image=CTkImage(img, size=(width,height))
    )

    if main_window.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE is True:
        main_window.sidebar_compact_mode_logo.grid(row=0, column=0, pady=(
            int(settings.uism.SF__LOGO_PADY[0]+a_s/2),
            int(settings.uism.SF__LOGO_PADY[1]+a_s/2)
        ))
    else:
        main_window.sidebar_logo.grid(row=0, column=0, pady=settings.uism.SF__LOGO_PADY)

    # Sidebar Features
    main_window.sidebar_features_container = CTkFrame(main_window.sidebar_bg_container, corner_radius=0, fg_color="transparent", width=0, height=0)
    main_window.sidebar_features_container.grid(row=1, column=0, pady=0, sticky="ew")
    main_window.sidebar_features_container.grid_columnconfigure(0, weight=1)



    sidebar_features_settings = [
        {
            "frame_attr_name": "translation_frame",
            "command": toggleTranslationFeature,
            "switch_box_attr_name": "translation_switch_box",
            "toggle_switch_box_command": lambda e: main_window.translation_switch_box.toggle(),
            "label_attr_name": "label_translation",
            "compact_mode_icon_attr_name": "translation_compact_mode_icon",
            "selected_mark_attr_name": "translation_selected_mark",
            "var_label_text": main_window.view_variable.VAR_LABEL_TRANSLATION,
            "icon_file_name": settings.image_filename.TRANSLATION_ICON,
        },
        {
            "frame_attr_name": "transcription_send_frame",
            "command": toggleTranscriptionSendFeature,
            "switch_box_attr_name": "transcription_send_switch_box",
            "toggle_switch_box_command": lambda e: main_window.transcription_send_switch_box.toggle(),
            "label_attr_name": "label_transcription_send",
            "compact_mode_icon_attr_name": "transcription_send_compact_mode_icon",
            "selected_mark_attr_name": "transcription_send_selected_mark",
            "var_label_text": main_window.view_variable.VAR_LABEL_TRANSCRIPTION_SEND,
            "icon_file_name": settings.image_filename.MIC_ICON,
        },
        {
            "frame_attr_name": "transcription_receive_frame",
            "command": toggleTranscriptionReceiveFeature,
            "switch_box_attr_name": "transcription_receive_switch_box",
            "toggle_switch_box_command": lambda e: main_window.transcription_receive_switch_box.toggle(),
            "label_attr_name": "label_transcription_receive",
            "compact_mode_icon_attr_name": "transcription_receive_compact_mode_icon",
            "selected_mark_attr_name": "transcription_receive_selected_mark",
            "var_label_text": main_window.view_variable.VAR_LABEL_TRANSCRIPTION_RECEIVE,
            "icon_file_name": settings.image_filename.HEADPHONES_ICON,
        },
        {
            "frame_attr_name": "foreground_frame",
            "command": toggleForegroundFeature,
            "switch_box_attr_name": "foreground_switch_box",
            "toggle_switch_box_command": lambda e: main_window.foreground_switch_box.toggle(),
            "label_attr_name": "label_foreground",
            "compact_mode_icon_attr_name": "foreground_compact_mode_icon",
            "selected_mark_attr_name": "foreground_selected_mark",
            "var_label_text": main_window.view_variable.VAR_LABEL_FOREGROUND,
            "icon_file_name": settings.image_filename.FOREGROUND_ICON,
        },
    ]



    row=0
    for sfs in sidebar_features_settings:
        frame_attr_name = sfs["frame_attr_name"]
        command = sfs["command"]
        switch_box_attr_name = sfs["switch_box_attr_name"]
        toggle_switch_box_command = sfs["toggle_switch_box_command"]
        label_attr_name = sfs["label_attr_name"]
        compact_mode_icon_attr_name = sfs["compact_mode_icon_attr_name"]
        selected_mark_attr_name = sfs["selected_mark_attr_name"]
        var_label_text = sfs["var_label_text"]
        icon_file_name = sfs["icon_file_name"]

        frame_widget = CTkFrame(main_window.sidebar_features_container, corner_radius=0, fg_color=settings.ctm.SF__BG_COLOR, cursor="hand2", width=0, height=0)
        setattr(main_window, frame_attr_name, frame_widget)

        frame_widget.grid(row=row, column=0, pady=(0,1), sticky="ew")
        frame_widget.grid_columnconfigure(0, weight=1)

        label_widget = CTkLabel(
            frame_widget,
            textvariable=var_label_text,
            height=0,
            corner_radius=0,
            font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SF__LABEL_FONT_SIZE, weight="normal"),
            anchor="w",
            text_color=settings.ctm.LABELS_TEXT_COLOR,
        )
        setattr(main_window, label_attr_name, label_widget)


        switch_box_widget = CTkSwitch(
            frame_widget,
            text=None,
            height=0,
            width=0,
            corner_radius=int(settings.uism.SF__SWITCH_BOX_HEIGHT/2),
            border_width=0,
            switch_height=settings.uism.SF__SWITCH_BOX_HEIGHT,
            switch_width=settings.uism.SF__SWITCH_BOX_WIDTH,
            onvalue=True,
            offvalue=False,
            command=command,
            fg_color=settings.ctm.SF__SWITCH_BOX_BG_COLOR,
            bg_color=settings.ctm.SF__BG_COLOR,
            progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_BG_COLOR,
        )
        # # if sfs["is_checked"] is True:
        # #     target_attr.select()
        # # else:
        # #     target_attr.deselect()
        setattr(main_window, switch_box_attr_name, switch_box_widget)


        if settings.COMPACT_MODE_ICON_SIZE == 0:
            label_widget.grid(row=row, column=0, pady=settings.uism.SF__LABELS_IPADY, padx=(settings.uism.SF__LABEL_LEFT_PAD,0), sticky="ew")
            settings.COMPACT_MODE_ICON_SIZE = int(getLatestHeight(frame_widget)  - settings.uism.SF__COMPACT_MODE_ICON_PADY*2)
            label_widget.grid_remove()


        # for compact mode
        compact_mode_icon_widget = CTkLabel(
            frame_widget,
            text=None,
            height=0,
            corner_radius=0,
            image=CTkImage(getImageFileFromUiUtils(icon_file_name),size=(settings.COMPACT_MODE_ICON_SIZE,settings.COMPACT_MODE_ICON_SIZE)),
        )
        setattr(main_window, compact_mode_icon_attr_name, compact_mode_icon_widget)

        selected_mark_widget = CTkFrame(frame_widget, corner_radius=0, fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_BG_COLOR, width=settings.uism.SF__SELECTED_MARK_WIDTH, height=0)
        setattr(main_window, selected_mark_attr_name, selected_mark_widget)


        # Arrange
        if main_window.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE is True:
            compact_mode_icon_widget.grid(row=row, column=0, pady=settings.uism.SF__COMPACT_MODE_ICON_PADY)
            selected_mark_widget.place(relx=-1, rely=0.5, relheight=0.75, anchor="center")
        else:
            label_widget.grid(row=row, column=0, pady=settings.uism.SF__LABELS_IPADY, padx=(settings.uism.SF__LABEL_LEFT_PAD,0), sticky="ew")
            switch_box_widget.grid(row=row, column=0, padx=(0,settings.uism.SF__SWITCH_BOX_RIGHT_PAD), sticky="e")


        # Unbind the event "<Button-1>" originally set up by the widget to manually control it.
        switch_box_widget._canvas.unbind("<Button-1>")
        switch_box_widget._text_label.unbind("<Button-1>")

        bindButtonReleaseFunction([compact_mode_icon_widget, frame_widget, label_widget, selected_mark_widget, switch_box_widget._canvas, switch_box_widget._bg_canvas], toggle_switch_box_command)

        retag("vrct_"+frame_attr_name, compact_mode_icon_widget, frame_widget, label_widget, selected_mark_widget, switch_box_widget)

        def commonEventFunction(e, event_type):
            for ww in e.widget.master.bindtags():
                if ww.startswith("vrct_"):
                    ww = ww.replace("vrct_", "")
                    changeSidebarFeaturesColorByEvents(ww, event_type)
                    break

        def enterFunction(e):
            commonEventFunction(e, "enter")

        def leaveFunction(e):
            commonEventFunction(e, "leave")

        def buttonPressFunction(e):
            commonEventFunction(e, "button_press")

        def buttonReleasedFunction(e):
            commonEventFunction(e, "button_release")

        bindEnterAndLeaveFunction([compact_mode_icon_widget, frame_widget, label_widget, selected_mark_widget, switch_box_widget._canvas, switch_box_widget._bg_canvas], enterFunction, leaveFunction)

        bindButtonPressAndReleaseFunction([compact_mode_icon_widget, frame_widget, label_widget, selected_mark_widget, switch_box_widget._canvas, switch_box_widget._bg_canvas], buttonPressFunction, buttonReleasedFunction)

        row+=1





    # Sidebar Quick Language Settings, SQLS
    main_window.sls__container = CTkFrame(main_window.sidebar_bg_container, corner_radius=0, fg_color=settings.ctm.SIDEBAR_BG_COLOR, width=0, height=0)

    if main_window.view_variable.IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE is False:
        main_window.sls__container.grid(row=2, column=0, sticky="new")

    main_window.sls__container.grid_columnconfigure(0, weight=1)


    main_window.sls__container_title = CTkLabel(main_window.sls__container,
        # text="言語設定",
        text="Language Settings",
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
        # title_text="あなたの言語",
        title_text="Your Language",
        title_text_attr_name="sls__title_text_your_language",
        optionmenu_attr_name="sls__optionmenu_your_language",
        dropdown_menu_attr_name="sls__dropdown_menu_your_language",
        dropdown_menu_values=["1""2","pppp\npppp"],
        variable=main_window.view_variable.VAR_YOUR_LANGUAGE
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
        image=CTkImage(getImageFileFromUiUtils(settings.image_filename.NARROW_ARROW_DOWN).rotate(180),size=settings.uism.SLS__BOX_ARROWS_IMAGE_SIZE)

    )
    main_window.sls__both_direction_up.grid(row=0, column=1, pady=0)

    main_window.sls__both_direction_desc = CTkLabel(
        main_window.sls__arrow_direction_box,
        # text="双方向に翻訳",
        text="Translate Each Other",
        height=0,
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.SLS__BOX_ARROWS_DESC_FONT_SIZE, weight="normal"),
        text_color=settings.ctm.SLS__BOX_ARROWS_TEXT_COLOR,
    )
    main_window.sls__both_direction_desc.grid(row=0, column=2, padx=settings.uism.SLS__BOX_ARROWS_DESC_PADX, pady=0)

    main_window.sls__both_direction_label_down = CTkLabel(
        main_window.sls__arrow_direction_box,
        text=None,
        height=0,
        image=CTkImage(getImageFileFromUiUtils(settings.image_filename.NARROW_ARROW_DOWN).rotate(0),size=settings.uism.SLS__BOX_ARROWS_IMAGE_SIZE)

    )
    main_window.sls__both_direction_label_down.grid(row=0, column=3, pady=0)



    # Target language
    main_window.sls__box_target_language = createQuickLanguageSettingBox(
        parent_widget=main_window.sls__box_frame,
        # title_text="相手の言語",
        title_text="Target Language",
        title_text_attr_name="sls__title_text_target_language",
        optionmenu_attr_name="sls__optionmenu_target_language",
        dropdown_menu_attr_name="sls__dropdown_menu_target_language",
        dropdown_menu_values=["1""2","pppp\npppp2"],
        variable=main_window.view_variable.VAR_TARGET_LANGUAGE
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
        image=CTkImage(getImageFileFromUiUtils(settings.image_filename.CONFIGURATION_ICON),size=(settings.COMPACT_MODE_ICON_SIZE,settings.COMPACT_MODE_ICON_SIZE))
    )
    main_window.sidebar_config_button.grid(row=0, column=0, padx=0, pady=settings.uism.SIDEBAR_CONFIG_BUTTON_IPADY)


    bindButtonFunctionAndColor(
        target_widgets=[main_window.sidebar_config_button_wrapper, main_window.sidebar_config_button],
        enter_color=settings.ctm.CONFIG_BUTTON_HOVERED_BG_COLOR,
        leave_color=settings.ctm.CONFIG_BUTTON_BG_COLOR,
        clicked_color=settings.ctm.CONFIG_BUTTON_CLICKED_BG_COLOR,
        buttonReleasedFunction=main_window.openConfigWindow,
    )

