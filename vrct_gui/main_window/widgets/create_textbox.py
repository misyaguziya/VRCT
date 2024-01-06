from customtkinter import CTkFont, CTkFrame, CTkLabel, CTkTextbox

from ...ui_utils import bindEnterAndLeaveColor, bindButtonPressColor, bindButtonReleaseFunction, setDefaultActiveTab, switchActiveTabAndPassiveTab, switchTabsColor


def createTextbox(settings, main_window, view_variable):

    def switchTextbox(target_textbox_attr_name):
        main_window.current_active_textbox.grid_remove()
        main_window.current_active_textbox = getattr(main_window, target_textbox_attr_name)
        main_window.current_active_textbox.grid()

    def switchToTextboxAll(e):
        target_active_widget = getattr(main_window, "textbox_tab_all")
        switchTextboxTabFunction(target_active_widget)
        switchTextbox("textbox_all")

    def switchToTextboxSent(e):
        target_active_widget = getattr(main_window, "textbox_tab_sent")
        switchTextboxTabFunction(target_active_widget)
        switchTextbox("textbox_sent")

    def switchToTextboxReceived(e):
        target_active_widget = getattr(main_window, "textbox_tab_received")
        switchTextboxTabFunction(target_active_widget)
        switchTextbox("textbox_received")

    def switchToTextboxSystem(e):
        target_active_widget = getattr(main_window, "textbox_tab_system")
        switchTextboxTabFunction(target_active_widget)
        switchTextbox("textbox_system")


    def switchTextboxTabFunction(target_active_widget):
        switchActiveAndPassiveTextboxTabsColor(target_active_widget)
        switchActiveTabAndPassiveTab(target_active_widget, main_window.current_active_textbox_tab, main_window.current_active_textbox_tab.passive_function, settings.ctm.TEXTBOX_TAB_BG_HOVERED_COLOR, settings.ctm.TEXTBOX_TAB_BG_CLICKED_COLOR, settings.ctm.TEXTBOX_TAB_BG_PASSIVE_COLOR)
        main_window.current_active_textbox_tab = target_active_widget

    def switchActiveAndPassiveTextboxTabsColor(target_active_widget):
        textbox_tabs = [
            getattr(main_window, "textbox_tab_all"),
            getattr(main_window, "textbox_tab_sent"),
            getattr(main_window, "textbox_tab_received"),
            getattr(main_window, "textbox_tab_system")
        ]

        switchTabsColor(
            target_widget=target_active_widget,
            tab_buttons=textbox_tabs,
            active_bg_color=settings.ctm.TEXTBOX_BG_COLOR,
            active_text_color=settings.ctm.SLS__PRESETS_TAB_ACTIVE_TEXT_COLOR,
            passive_bg_color=settings.ctm.TEXTBOX_TAB_BG_PASSIVE_COLOR,
            passive_text_color=settings.ctm.TEXTBOX_TAB_TEXT_PASSIVE_COLOR
        )




    # Text box
    main_window.main_bg_container.grid_rowconfigure(1, weight=1)
    main_window.main_textbox_container = CTkFrame(main_window.main_bg_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    main_window.main_textbox_container.grid(row=1, column=0, columnspan=2, sticky="nsew")

    main_window.main_textbox_container.grid_columnconfigure(0,weight=1)
    main_window.main_textbox_container.grid_rowconfigure(0,weight=1)

    main_window.textbox_switch_tabs_container = CTkFrame(main_window.main_topbar_center_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    main_window.textbox_switch_tabs_container.place(relx=0.07, rely=1.15, anchor="sw")

    main_window.textbox_switch_tabs_container.grid_columnconfigure((0,1,2,3), weight=1, uniform="textbox_tabs")

    textbox_settings = [
        {
            "textbox_tab_attr_name": "textbox_tab_all",
            "command": switchToTextboxAll,
            "textbox_attr_name": "textbox_all",
            "textvariable": view_variable.VAR_LABEL_TEXTBOX_ALL
        },
        {
            "textbox_tab_attr_name": "textbox_tab_sent",
            "command": switchToTextboxSent,
            "textbox_attr_name": "textbox_sent",
            "textvariable": view_variable.VAR_LABEL_TEXTBOX_SENT
        },
        {
            "textbox_tab_attr_name": "textbox_tab_received",
            "command": switchToTextboxReceived,
            "textbox_attr_name": "textbox_received",
            "textvariable": view_variable.VAR_LABEL_TEXTBOX_RECEIVED
        },
        {
            "textbox_tab_attr_name": "textbox_tab_system",
            "command": switchToTextboxSystem,
            "textbox_attr_name": "textbox_system",
            "textvariable": view_variable.VAR_LABEL_TEXTBOX_SYSTEM
        },
    ]


    column=0
    for textbox_setting in textbox_settings:
        setattr(main_window, textbox_setting["textbox_tab_attr_name"],
            CTkFrame(
                main_window.textbox_switch_tabs_container,
                corner_radius=settings.uism.TEXTBOX_TAB_CORNER_RADIUS,
                fg_color=settings.ctm.TEXTBOX_TAB_BG_PASSIVE_COLOR,
                cursor="hand2",
                width=0,
                height=0
            )
        )
        target_widget = getattr(main_window, textbox_setting["textbox_tab_attr_name"])
        target_widget.grid(row=0, column=column, pady=0, padx=(0,2), sticky="ew")



        target_widget.grid_columnconfigure((0,2), weight=1)
        setattr(main_window, "label_widget", CTkLabel(
            target_widget,
            textvariable=textbox_setting["textvariable"],
            corner_radius=0,
            font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TEXTBOX_TAB_FONT_SIZE, weight="normal"),
            height=0,
            width=0,
            anchor="center",
            text_color=settings.ctm.TEXTBOX_TAB_TEXT_PASSIVE_COLOR,
        ))
        label_widget = getattr(main_window, "label_widget")
        label_widget.grid(row=0, column=1, pady=settings.uism.TEXTBOX_TAB_PADY, padx=settings.uism.TEXTBOX_TAB_PADX)

        bindEnterAndLeaveColor([target_widget, label_widget], settings.ctm.TEXTBOX_TAB_BG_HOVERED_COLOR, settings.ctm.TEXTBOX_TAB_BG_PASSIVE_COLOR)
        bindButtonPressColor([target_widget, label_widget], settings.ctm.TEXTBOX_TAB_BG_CLICKED_COLOR, settings.ctm.TEXTBOX_TAB_BG_PASSIVE_COLOR)

        target_widget.passive_function = textbox_setting["command"]
        bindButtonReleaseFunction([target_widget, label_widget], textbox_setting["command"])



        setattr(main_window, textbox_setting["textbox_attr_name"], CTkTextbox(
            main_window.main_textbox_container,
            corner_radius=settings.uism.TEXTBOX_CORNER_RADIUS,
            fg_color=settings.ctm.TEXTBOX_BG_COLOR,
            text_color="lime", # Textbox's text_color is set when printing. so this is for prevent from non-setting text_color like the gloves used in food factories are blue.
            wrap="word",
            height=0,
        ))
        textbox_widget = getattr(main_window, textbox_setting["textbox_attr_name"])
        textbox_widget.grid(row=0, column=0, padx=settings.uism.TEXTBOX_PADX, pady=0, sticky="nsew")
        textbox_widget.grid_remove()
        textbox_widget.configure(state="disabled")

        column+=1

    # Set default active textbox tab
    main_window.current_active_textbox_tab = getattr(main_window, "textbox_tab_all")
    setDefaultActiveTab(
        active_tab_widget=main_window.current_active_textbox_tab,
        active_bg_color=settings.ctm.TEXTBOX_TAB_BG_ACTIVE_COLOR,
        active_text_color=settings.ctm.TEXTBOX_TAB_TEXT_ACTIVE_COLOR
    )

    main_window.current_active_textbox = getattr(main_window, "textbox_all")
    main_window.current_active_textbox.grid()
