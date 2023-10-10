from datetime import datetime
from customtkinter import CTkFont

def _printToTextbox(vrct_gui, settings, target_type, original_message=None, translated_message=None, tags=None, disable_print_to_textbox_all:bool=False):
    now_raw_data = datetime.now()
    # now = now_raw_data.strftime("%H:%M:%S")
    now_hm = now_raw_data.strftime("%H:%M")
    # set target textbox widget

    is_only_one_message = True if original_message is None or translated_message is None or translated_message == "" else False

    match (target_type):
        case "SYSTEM":
            target_textbox = vrct_gui.textbox_system
        case "SENT":
            target_textbox = vrct_gui.textbox_sent
        case "RECEIVED":
            target_textbox = vrct_gui.textbox_received
        case (_):
            raise  ValueError(f"No matching case for target_type: {target_type}")


    def printEachTextbox(target_textbox):
        target_textbox.tag_config("JUSTIFY_CENTER", justify="center")
        target_textbox.tag_config("JUSTIFY_RIGHT", justify="right")
        target_textbox.tag_config("JUSTIFY_LEFT", justify="left")

        # common tag settings
        # target_textbox._textbox.tag_configure("START", spacing1=16)
        target_textbox._textbox.tag_configure("LABEL", font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TEXTBOX_FONT_SIZE__LABEL, weight="normal"))
        target_textbox._textbox.tag_configure("TIMESTAMP", font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TEXTBOX_FONT_SIZE__TIMESTAMP, weight="normal"), foreground=settings.ctm.TEXTBOX_TIMESTAMP_TEXT_COLOR)
        target_textbox._textbox.tag_configure("SECONDARY_TEXT_FONT", font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TEXTBOX_FONT_SIZE__SECONDARY_TEXT_FONT, weight="normal"))
        target_textbox._textbox.tag_configure("MAIN_TEXT_FONT", font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TEXTBOX_FONT_SIZE__MAIN_TEXT_FONT, weight="normal"))

        # System Tag Settings
        target_textbox.tag_config("FIRST_INSERT_SPACING", spacing1=settings.uism.TEXTBOX_FIRST_INSERT_SPACING)
        target_textbox.tag_config("SYSTEM_TAG", foreground=settings.ctm.TEXTBOX_SYSTEM_TAG_TEXT_COLOR)
        target_textbox.tag_config("SYSTEM_TEXT", foreground=settings.ctm.TEXTBOX_TEXT_SUB_COLOR)
        target_textbox._textbox.tag_configure("SYSTEM_TEXT_FONT", font=CTkFont(family=settings.FONT_FAMILY, size=settings.uism.TEXTBOX_FONT_SIZE__SYSTEM_TEXT_FONT, weight="normal"))

        # Sent Tag Settings
        target_textbox.tag_config("SENT_TAG", foreground=settings.ctm.TEXTBOX_SENT_TAG_TEXT_COLOR)
        target_textbox.tag_config("SENT_TEXT", foreground=settings.ctm.TEXTBOX_TEXT_COLOR)
        target_textbox.tag_config("SENT_SUB_TEXT", foreground=settings.ctm.TEXTBOX_TEXT_SUB_COLOR)

        # Received Tag Settings
        target_textbox.tag_config("RECEIVED_TAG", foreground=settings.ctm.TEXTBOX_RECEIVED_TAG_TEXT_COLOR)
        target_textbox.tag_config("RECEIVED_TEXT", foreground=settings.ctm.TEXTBOX_TEXT_COLOR)
        target_textbox.tag_config("RECEIVED_SUB_TEXT", foreground=settings.ctm.TEXTBOX_TEXT_SUB_COLOR)

        FAKE_MARGIN = "  "
        # insert
        target_textbox.configure(state="normal")
        target_textbox.insert("end", "\n")
        match (target_type):
            case "SYSTEM":
                target_textbox.insert("end", "System", ("SYSTEM_TAG", "FIRST_INSERT_SPACING", "JUSTIFY_CENTER", "LABEL"))
                target_textbox.insert("end", FAKE_MARGIN+original_message+FAKE_MARGIN, ("SYSTEM_TEXT", "SYSTEM_TEXT_FONT", "JUSTIFY_CENTER"))
                target_textbox.insert("end", now_hm, ("TIMESTAMP", "JUSTIFY_CENTER"))

            case "SENT":
                target_textbox.insert("end", now_hm, ("TIMESTAMP", "FIRST_INSERT_SPACING", "JUSTIFY_RIGHT"))
                target_textbox.insert("end", FAKE_MARGIN+"Sent", ("SENT_TAG", "LABEL"))
                target_textbox.insert("end", "\n")
                if is_only_one_message is False:
                    target_textbox.insert("end", original_message, ("SENT_SUB_TEXT", "SECONDARY_TEXT_FONT", "JUSTIFY_RIGHT"))
                    target_textbox.insert("end", "\n")
                    target_textbox.insert("end", translated_message, ("SENT_TEXT", "MAIN_TEXT_FONT", "JUSTIFY_RIGHT"))
                else:
                    target_textbox.insert("end", original_message, ("SENT_TEXT", "MAIN_TEXT_FONT", "JUSTIFY_RIGHT"))

            case "RECEIVED":
                target_textbox.insert("end", "Received", ("RECEIVED_TAG", "FIRST_INSERT_SPACING", "JUSTIFY_LEFT", "LABEL"))
                target_textbox.insert("end", FAKE_MARGIN+now_hm, ("TIMESTAMP"))
                if is_only_one_message is False:
                    target_textbox.insert("end", "\n")
                    target_textbox.insert("end", original_message, ("RECEIVED_SUB_TEXT", "SECONDARY_TEXT_FONT"))
                    target_textbox.insert("end", "\n")
                    target_textbox.insert("end", translated_message, ("RECEIVED_TEXT", "MAIN_TEXT_FONT", "JUSTIFY_LEFT"))
                else:
                    target_textbox.insert("end", "\n")
                    target_textbox.insert("end", original_message, ("RECEIVED_TEXT", "MAIN_TEXT_FONT", "JUSTIFY_LEFT"))

        target_textbox.configure(state="disabled")
        target_textbox.see("end")

    printEachTextbox(target_textbox)

    # To automatically print the same log to the textbox_all widget as well.
    if disable_print_to_textbox_all is not True: printEachTextbox(vrct_gui.textbox_all)