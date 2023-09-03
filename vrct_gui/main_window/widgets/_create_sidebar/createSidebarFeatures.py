from customtkinter import CTkFont, CTkFrame, CTkLabel, CTkSwitch, CTkImage

from ....ui_utils import getImageFileFromUiUtils, openImageKeepAspectRatio, retag, getLatestHeight, bindEnterAndLeaveFunction, bindButtonReleaseFunction, bindButtonPressAndReleaseFunction

from utils import callFunctionIfCallable


def createSidebarFeatures(settings, main_window):

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
        target_compact_mode_frame_widget = getattr(main_window, "compact_mode_"+ww)
        if event_name == "enter":
            target_frame_widget.configure(fg_color=settings.ctm.SF__HOVERED_BG_COLOR)
            target_frame_widget.children["!ctkswitch"].configure(fg_color=settings.ctm.SF__SWITCH_BOX_HOVERED_BG_COLOR, progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_HOVERED_BG_COLOR)
            target_compact_mode_frame_widget.configure(fg_color=settings.ctm.SF__HOVERED_BG_COLOR)
            target_compact_mode_frame_widget.children["!ctkframe"].configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_HOVERED_BG_COLOR)

        elif event_name == "leave":
            target_frame_widget.configure(fg_color=settings.ctm.SF__BG_COLOR)
            target_frame_widget.children["!ctkswitch"].configure(fg_color=settings.ctm.SF__SWITCH_BOX_BG_COLOR, progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_BG_COLOR)
            target_compact_mode_frame_widget.configure(fg_color=settings.ctm.SF__BG_COLOR)
            target_compact_mode_frame_widget.children["!ctkframe"].configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_BG_COLOR)

        elif event_name == "button_press":
            target_frame_widget.configure(fg_color=settings.ctm.SF__CLICKED_BG_COLOR)
            target_frame_widget.children["!ctkswitch"].configure(fg_color=settings.ctm.SF__SWITCH_BOX_CLICKED_BG_COLOR, progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_CLICKED_BG_COLOR)
            target_compact_mode_frame_widget.configure(fg_color=settings.ctm.SF__CLICKED_BG_COLOR)
            target_compact_mode_frame_widget.children["!ctkframe"].configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_CLICKED_BG_COLOR)

        elif event_name == "button_release":
            target_frame_widget.configure(fg_color=settings.ctm.SF__BG_COLOR)
            target_frame_widget.children["!ctkswitch"].configure(fg_color=settings.ctm.SF__SWITCH_BOX_BG_COLOR, progress_color=settings.ctm.SF__SWITCH_BOX_ACTIVE_BG_COLOR)
            target_compact_mode_frame_widget.configure(fg_color=settings.ctm.SF__BG_COLOR)
            target_compact_mode_frame_widget.children["!ctkframe"].configure(fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_BG_COLOR)









    (img, width, height) = openImageKeepAspectRatio(settings.image_filename.VRCT_LOGO, settings.uism.SF__LOGO_MAX_SIZE)
    main_window.sidebar_logo = CTkLabel(
        main_window.sidebar_bg_container,
        fg_color=settings.ctm.SIDEBAR_BG_COLOR,
        text=None,
        height=0,
        image=CTkImage(img, size=(width,height))
    )
    main_window.sidebar_logo.grid(row=0, column=0, pady=settings.uism.SF__LOGO_PADY)

    # "height-a_s" represents the adjustment in size, and the "pady+a_s/2" indicates a padding increase of 4 pixels to compensate for the reduction.
    a_s = settings.uism.SF__LOGO_HEIGHT_FOR_ADJUSTMENT
    (img, width, height) = openImageKeepAspectRatio(settings.image_filename.VRCT_LOGO_MARK, height-a_s)
    main_window.sidebar_compact_mode_logo = CTkLabel(
        main_window.sidebar_compact_mode_bg_container,
        fg_color=settings.ctm.SIDEBAR_BG_COLOR,
        text=None,
        height=0,
        image=CTkImage(img, size=(width,height))
    )
    main_window.sidebar_compact_mode_logo.grid(row=0, column=0, pady=(
        int(settings.uism.SF__LOGO_PADY[0]+a_s/2),
        int(settings.uism.SF__LOGO_PADY[1]+a_s/2)
    ))

    # Sidebar Features
    main_window.sidebar_features_container = CTkFrame(main_window.sidebar_bg_container, corner_radius=0, fg_color="transparent", width=0, height=0)
    main_window.sidebar_features_container.grid(row=1, column=0, pady=0, sticky="ew")
    main_window.sidebar_features_container.grid_columnconfigure(0, weight=1)



    # Sidebar Features Compact Mode
    main_window.sidebar_compact_mode_features_container = CTkFrame(main_window.sidebar_compact_mode_bg_container, corner_radius=0, fg_color="transparent", width=0, height=0)
    main_window.sidebar_compact_mode_features_container.grid(row=1, column=0, pady=0, sticky="ew")
    main_window.sidebar_compact_mode_features_container.grid_columnconfigure(0, weight=1)



    sidebar_features_settings = [
        {
            "frame_attr_name": "translation_frame",
            "command": toggleTranslationFeature,
            "switch_box_attr_name": "translation_switch_box",
            "toggle_switch_box_command": lambda e: main_window.translation_switch_box.toggle(),
            "label_attr_name": "label_translation",
            "compact_mode_icon_attr_name": "translation_compact_mode_icon",
            "compact_mode_frame_attr_name": "compact_mode_translation_frame",
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
            "compact_mode_frame_attr_name": "compact_mode_transcription_send_frame",
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
            "compact_mode_frame_attr_name": "compact_mode_transcription_receive_frame",
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
            "compact_mode_frame_attr_name": "compact_mode_foreground_frame",
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
        compact_mode_frame_attr_name = sfs["compact_mode_frame_attr_name"]
        selected_mark_attr_name = sfs["selected_mark_attr_name"]
        var_label_text = sfs["var_label_text"]
        icon_file_name = sfs["icon_file_name"]

        frame_widget = CTkFrame(main_window.sidebar_features_container, corner_radius=0, fg_color=settings.ctm.SF__BG_COLOR, cursor="hand2", width=0, height=0)
        setattr(main_window, frame_attr_name, frame_widget)

        frame_widget.grid(row=row, column=0, pady=(0,1), sticky="ew")
        frame_widget.grid_columnconfigure(0, weight=1)

        compact_mode_frame_widget = CTkFrame(main_window.sidebar_compact_mode_features_container, corner_radius=0, fg_color=settings.ctm.SF__BG_COLOR, cursor="hand2", width=0, height=0)
        setattr(main_window, compact_mode_frame_attr_name, compact_mode_frame_widget)

        compact_mode_frame_widget.grid(row=row, column=0, pady=(0,1), sticky="ew")
        compact_mode_frame_widget.grid_columnconfigure(0, weight=1)


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
            compact_mode_frame_widget,
            text=None,
            height=0,
            corner_radius=0,
            image=CTkImage(getImageFileFromUiUtils(icon_file_name),size=(settings.COMPACT_MODE_ICON_SIZE,settings.COMPACT_MODE_ICON_SIZE)),
        )
        setattr(main_window, compact_mode_icon_attr_name, compact_mode_icon_widget)

        selected_mark_widget = CTkFrame(
            compact_mode_frame_widget,
            corner_radius=0,
            fg_color=settings.ctm.SF__SELECTED_MARK_ACTIVE_BG_COLOR,
            width=settings.uism.SF__SELECTED_MARK_WIDTH,
            height=0
        )
        setattr(main_window, selected_mark_attr_name, selected_mark_widget)


        # Arrange
        compact_mode_icon_widget.grid(row=row, column=0, pady=settings.uism.SF__COMPACT_MODE_ICON_PADY)
        selected_mark_widget.place(relx=-1, rely=0.5, relheight=0.75, anchor="center")

        label_widget.grid(row=row, column=0, pady=settings.uism.SF__LABELS_IPADY, padx=(settings.uism.SF__LABEL_LEFT_PAD,0), sticky="ew")
        switch_box_widget.grid(row=row, column=0, padx=(0,settings.uism.SF__SWITCH_BOX_RIGHT_PAD), sticky="e")


        # Unbind the event "<Button-1>" originally set up by the widget to manually control it.
        switch_box_widget._canvas.unbind("<Button-1>")
        switch_box_widget._text_label.unbind("<Button-1>")

        bindButtonReleaseFunction([compact_mode_icon_widget, frame_widget, compact_mode_frame_widget, label_widget, selected_mark_widget, switch_box_widget._canvas, switch_box_widget._bg_canvas], toggle_switch_box_command)

        retag("vrct_"+frame_attr_name, compact_mode_icon_widget, frame_widget, compact_mode_frame_widget, label_widget, selected_mark_widget, switch_box_widget)

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

        bindEnterAndLeaveFunction([compact_mode_icon_widget, frame_widget, compact_mode_frame_widget, label_widget, selected_mark_widget, switch_box_widget._canvas, switch_box_widget._bg_canvas], enterFunction, leaveFunction)

        bindButtonPressAndReleaseFunction([compact_mode_icon_widget, frame_widget, compact_mode_frame_widget, label_widget, selected_mark_widget, switch_box_widget._canvas, switch_box_widget._bg_canvas], buttonPressFunction, buttonReleasedFunction)

        row+=1