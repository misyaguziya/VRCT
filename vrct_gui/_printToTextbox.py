from datetime import datetime
from customtkinter import CTkFont

def _printToTextbox(settings, target_textbox, original_message, translated_message, tags=None):
    now_raw_data = datetime.now()
    now = now_raw_data.strftime('%H:%M:%S')
    now_hm = now_raw_data.strftime('%H:%M')

    target_textbox.tag_config("NORMAL_TEXT", foreground=settings.ctm.TEXTBOX_TEXT_COLOR)

    target_textbox.tag_config("ERROR", foreground="#FF0000")

    target_textbox.tag_config("INFO", justify="center")
    target_textbox.tag_config("INFO_COLOR", foreground="#1BFF00")

    target_textbox.tag_config("SEND", justify="left")
    target_textbox.tag_config("SEND_COLOR", foreground="#0378e2")

    target_textbox.tag_config("RECEIVE", justify="left")
    target_textbox.tag_config("RECEIVE_COLOR", foreground="#ffa500")

    target_textbox._textbox.tag_configure("START", spacing1=10)

    target_textbox._textbox.tag_configure("LABEL", font=CTkFont(family=settings.FONT_FAMILY, size=12, weight="normal"))
    target_textbox._textbox.tag_configure("TIMESTAMP", font=CTkFont(family=settings.FONT_FAMILY, size=12, weight="normal"))
    target_textbox._textbox.tag_configure("ORIGINAL_MESSAGE", font=CTkFont(family=settings.FONT_FAMILY, size=12, weight="normal"))
    target_textbox._textbox.tag_configure("TRANSLATED_MESSAGE", font=CTkFont(family=settings.FONT_FAMILY, size=16, weight="normal"))

    target_textbox.configure(state='normal')
    target_textbox.insert("end", f"[{tags}]  ", ("START", "LABEL", tags, f"{tags}_COLOR"))
    target_textbox.insert("end", f"{now_hm}  ", ("TIMESTAMP", tags))
    target_textbox.insert("end", f"{original_message}\n", ("ORIGINAL_MESSAGE", "NORMAL_TEXT", tags))
    target_textbox.insert("end", f"{translated_message}\n", ("TRANSLATED_MESSAGE", "NORMAL_TEXT", tags))
    target_textbox.configure(state='disabled')
    target_textbox.see("end")