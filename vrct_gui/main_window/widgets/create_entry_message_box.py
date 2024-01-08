from customtkinter import CTkFont, CTkFrame, CTkTextbox, CTkLabel, CTkImage

from ...ui_utils import bindButtonFunctionAndColor
from utils import callFunctionIfCallable

def createEntryMessageBox(settings, main_window, view_variable):
    main_window.main_entry_message_container = CTkFrame(main_window.main_bg_container, corner_radius=settings.uism.TEXTBOX_ENTRY_CORNER_RADIUS, fg_color=settings.ctm.MAIN_BG_COLOR, width=0, height=0)
    main_window.main_entry_message_container.grid(row=2, column=0, sticky="nsew")


    main_window.main_entry_message_container.grid_columnconfigure(0, weight=1)
    main_window.main_entry_message_container.grid_rowconfigure(0, weight=1)
    main_window.entry_message_box = CTkTextbox(
        main_window.main_entry_message_container,
        corner_radius=settings.uism.TEXTBOX_ENTRY_CORNER_RADIUS,
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


    main_window.main_send_message_button_container = CTkFrame(main_window.main_entry_message_container, corner_radius=settings.uism.SEND_MESSAGE_BUTTON_CORNER_RADIUS, fg_color=settings.ctm.SEND_MESSAGE_BUTTON_BG_COLOR, width=0, height=0)
    main_window.main_send_message_button_container.grid(row=0, column=1, padx=(0, settings.uism.TEXTBOX_ENTRY_PADX), pady=settings.uism.TEXTBOX_ENTRY_PADY, sticky="nsew")

    main_window.main_send_message_button_container.grid_columnconfigure(0, weight=0, minsize=settings.uism.SEND_MESSAGE_BUTTON_MIN_WIDTH)
    main_window.main_send_message_button_container.grid_rowconfigure(0, weight=1)




    main_window.main_send_message_button = CTkFrame(main_window.main_send_message_button_container, corner_radius=0, fg_color=settings.ctm.SEND_MESSAGE_BUTTON_BG_COLOR, height=0, width=0)
    main_window.main_send_message_button.grid(row=0, column=0, sticky="nsew")
    main_window.main_send_message_button.configure(cursor="hand2")

    main_window.main_send_message_button.grid_columnconfigure((0,2), weight=1)
    main_window.main_send_message_button.grid_rowconfigure((0,2), weight=1)

    main_window.main_send_message_button_image = CTkLabel(
        main_window.main_send_message_button,
        text=None,
        height=0,
        image=CTkImage((settings.image_file.SEND_MESSAGE_ICON),size=(settings.uism.SEND_MESSAGE_BUTTON_IMAGE_SIZE,settings.uism.SEND_MESSAGE_BUTTON_IMAGE_SIZE)),
    )
    main_window.main_send_message_button_image.grid(row=1, column=1)



    bindButtonFunctionAndColor(
        target_widgets=[main_window.main_send_message_button, main_window.main_send_message_button_image],
        enter_color=settings.ctm.SEND_MESSAGE_BUTTON_BG_HOVERED_COLOR,
        leave_color=settings.ctm.SEND_MESSAGE_BUTTON_BG_COLOR,
        clicked_color=settings.ctm.SEND_MESSAGE_BUTTON_BG_CLICKED_COLOR,
        buttonReleasedFunction=lambda _e: callFunctionIfCallable(view_variable.CALLBACK_CLICKED_SEND_MESSAGE_BUTTON, _e),
    )






    main_window.main_send_message_button__disabled = CTkFrame(main_window.main_send_message_button_container, corner_radius=0, fg_color=settings.ctm.SEND_MESSAGE_BUTTON_BG_COLOR, height=0, width=0)
    main_window.main_send_message_button__disabled.grid(row=0, column=0, sticky="nsew")

    main_window.main_send_message_button__disabled.grid_columnconfigure((0,2), weight=1)
    main_window.main_send_message_button__disabled.grid_rowconfigure((0,2), weight=1)

    main_window.main_send_message_button_image__disabled = CTkLabel(
        main_window.main_send_message_button__disabled,
        text=None,
        height=0,
        image=CTkImage((settings.image_file.SEND_MESSAGE_ICON_DISABLED),size=(settings.uism.SEND_MESSAGE_BUTTON_IMAGE_SIZE,settings.uism.SEND_MESSAGE_BUTTON_IMAGE_SIZE)),
    )
    main_window.main_send_message_button_image__disabled.grid(row=1, column=1)

    main_window.main_send_message_button__disabled.grid_remove()