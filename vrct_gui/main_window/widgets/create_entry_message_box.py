from customtkinter import CTkFont, CTkFrame, CTkTextbox

def createEntryMessageBox(settings, main_window):
    main_window.main_entry_message_container = CTkFrame(main_window.main_bg_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    main_window.main_entry_message_container.grid(row=2, column=0, sticky="nsew")


    main_window.main_entry_message_container.grid_columnconfigure(0, weight=1)
    main_window.main_entry_message_container.grid_rowconfigure(0, weight=1)
    main_window.entry_message_box = CTkTextbox(
        main_window.main_entry_message_container,
        border_color=settings.ctm.TEXTBOX_ENTRY_BORDER_COLOR,
        fg_color=settings.ctm.TEXTBOX_ENTRY_BG_COLOR,
        text_color=settings.ctm.TEXTBOX_ENTRY_TEXT_COLOR,
        border_width=settings.uism.TEXTBOX_ENTRY_BORDER_SIZE,
        height=0,
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TEXTBOX_ENTRY_FONT_SIZE, weight="normal"),
    )
    main_window.entry_message_box.grid(row=0, column=0, padx=settings.uism.TEXTBOX_ENTRY_PADX, pady=settings.uism.TEXTBOX_ENTRY_PADY, sticky="nsew")


    def messageBoxAnyKeyPress(e):
        BREAK_KEYSYM_LIST = [
            "Delete", "Select", "Up", "Down", "Next", "End", "Print",
            "Prior","Insert","Home", "Left", "Clear", "Right", "Linefeed"
        ]
        if e.keysym != "??":
            if len(e.char) != 0 and e.keysym in BREAK_KEYSYM_LIST:
                main_window.entry_message_box.insert("end", e.char)
                return "break"

    main_window.entry_message_box.bind("<Any-KeyPress>", messageBoxAnyKeyPress)

