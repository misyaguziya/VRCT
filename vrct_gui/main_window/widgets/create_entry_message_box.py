
from customtkinter import CTkFont, CTkFrame, CTkEntry

def createEntryMessageBox(settings, main_window):
    main_window.main_entry_message_container = CTkFrame(main_window.main_bg_container, corner_radius=0, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    main_window.main_entry_message_container.grid(row=2, column=0, sticky="ew")


    main_window.main_entry_message_container.columnconfigure(0, weight=1)
    main_window.entry_message_box = CTkEntry(
        main_window.main_entry_message_container,
        border_color=settings.ctm.TEXTBOX_ENTRY_BORDER_COLOR,
        fg_color=settings.ctm.TEXTBOX_ENTRY_BG_COLOR,
        text_color=settings.ctm.TEXTBOX_ENTRY_TEXT_COLOR,
        placeholder_text="Enter your message...",
        placeholder_text_color=settings.ctm.TEXTBOX_ENTRY_PLACEHOLDER_COLOR,
        height=settings.uism.TEXTBOX_ENTRY_HEIGHT,
        font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TEXTBOX_ENTRY_FONT_SIZE, weight="normal"),
    )
    main_window.entry_message_box.grid(row=0, column=0, padx=settings.uism.TEXTBOX_ENTRY_PADX, pady=settings.uism.TEXTBOX_ENTRY_PADY, sticky="nsew")
    main_window.entry_message_box._entry.grid(padx=settings.uism.TEXTBOX_ENTRY_IPADX, pady=settings.uism.TEXTBOX_ENTRY_IPADY)
