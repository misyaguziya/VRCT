from datetime import datetime
from customtkinter import CTkFont
from .ui_utils import calculateUiSize

class _PrintToTextbox():
    def __init__(
            self,
            vrct_gui,
            settings,
        ):

        self.vrct_gui = vrct_gui
        self.settings = settings

        self._DEFAULT_TEXTBOX_FIRST_INSERT_SPACING = self.settings.uism.TEXTBOX_FIRST_INSERT_SPACING
        self._DEFAULT_TEXTBOX_FONT_SIZE__LABEL = self.settings.uism.TEXTBOX_FONT_SIZE__LABEL
        self._DEFAULT_TEXTBOX_FONT_SIZE__TIMESTAMP = self.settings.uism.TEXTBOX_FONT_SIZE__TIMESTAMP
        self._DEFAULT_TEXTBOX_FONT_SIZE__SYSTEM_TEXT_FONT = self.settings.uism.TEXTBOX_FONT_SIZE__SYSTEM_TEXT_FONT
        self._DEFAULT_TEXTBOX_FONT_SIZE__SECONDARY_TEXT_FONT = self.settings.uism.TEXTBOX_FONT_SIZE__SECONDARY_TEXT_FONT
        self._DEFAULT_TEXTBOX_FONT_SIZE__MAIN_TEXT_FONT = self.settings.uism.TEXTBOX_FONT_SIZE__MAIN_TEXT_FONT



        self.textbox_first_insert_spacing = None
        self.textbox_font_size__label = None
        self.textbox_font_size__timestamp = None
        self.textbox_font_size__system_text_font = None
        self.textbox_font_size__secondary_text_font = None
        self.textbox_font_size__main_text_font = None


        self.all_textbox_widgets = [self.vrct_gui.textbox_all, self.vrct_gui.textbox_system, self.vrct_gui.textbox_sent, self.vrct_gui.textbox_received]


        self.setTagsSettings()


    def printToTextbox(self, target_type, original_message=None, translated_message=None, to_print_to_textbox_all:bool=True):
        self._printEachTextbox(
                target_textbox=self._getTargetTextboxWidget(target_type),
                print_type=target_type,
                original_message=original_message,
                translated_message=translated_message,
            )

        # To automatically print the same log to the textbox_all widget as well.
        if to_print_to_textbox_all is True:
            self._printEachTextbox(
                target_textbox=self._getTargetTextboxWidget("ALL"),
                print_type=target_type,
                original_message=original_message,
                translated_message=translated_message,
            )

    def setTagsSettings(self, custom_font_size_scale:float=1.0):
        # Calculate Textbox's ui size by default size * textbox_ui_scale
        self.textbox_first_insert_spacing = calculateUiSize(self._DEFAULT_TEXTBOX_FIRST_INSERT_SPACING, custom_font_size_scale)
        self.textbox_font_size__label = calculateUiSize(self._DEFAULT_TEXTBOX_FONT_SIZE__LABEL, custom_font_size_scale)
        self.textbox_font_size__timestamp = calculateUiSize(self._DEFAULT_TEXTBOX_FONT_SIZE__TIMESTAMP, custom_font_size_scale)
        self.textbox_font_size__system_text_font = calculateUiSize(self._DEFAULT_TEXTBOX_FONT_SIZE__SYSTEM_TEXT_FONT, custom_font_size_scale)
        self.textbox_font_size__secondary_text_font = calculateUiSize(self._DEFAULT_TEXTBOX_FONT_SIZE__SECONDARY_TEXT_FONT, custom_font_size_scale)
        self.textbox_font_size__main_text_font = calculateUiSize(self._DEFAULT_TEXTBOX_FONT_SIZE__MAIN_TEXT_FONT, custom_font_size_scale)

        for each_textbox_widget in self.all_textbox_widgets:
            self._setTagsSettings(target_textbox=each_textbox_widget)


    def _setTagsSettings(self, target_textbox):
        target_textbox.tag_config("JUSTIFY_CENTER", justify="center")
        target_textbox.tag_config("JUSTIFY_RIGHT", justify="right")
        target_textbox.tag_config("JUSTIFY_LEFT", justify="left")

        # common tag settings
        # target_textbox._textbox.tag_configure("START", spacing1=16)
        target_textbox.tag_config("FIRST_INSERT_SPACING", spacing1=self.textbox_first_insert_spacing)
        target_textbox._textbox.tag_configure("LABEL", font=CTkFont(family=self.settings.FONT_FAMILY, size=self.textbox_font_size__label, weight="normal"))
        target_textbox._textbox.tag_configure("TIMESTAMP", font=CTkFont(family=self.settings.FONT_FAMILY, size=self.textbox_font_size__timestamp, weight="normal"), foreground=self.settings.ctm.TEXTBOX_TIMESTAMP_TEXT_COLOR)
        target_textbox._textbox.tag_configure("SECONDARY_TEXT_FONT", font=CTkFont(family=self.settings.FONT_FAMILY, size=self.textbox_font_size__secondary_text_font, weight="normal"))
        target_textbox._textbox.tag_configure("MAIN_TEXT_FONT", font=CTkFont(family=self.settings.FONT_FAMILY, size=self.textbox_font_size__main_text_font, weight="normal"))

        # System Tag Settings
        target_textbox.tag_config("SYSTEM_TAG", foreground=self.settings.ctm.TEXTBOX_SYSTEM_TAG_TEXT_COLOR)
        target_textbox.tag_config("SYSTEM_TEXT", foreground=self.settings.ctm.TEXTBOX_TEXT_SUB_COLOR)
        target_textbox._textbox.tag_configure("SYSTEM_TEXT_FONT", font=CTkFont(family=self.settings.FONT_FAMILY, size=self.textbox_font_size__system_text_font, weight="normal"))

        # Sent Tag Settings
        target_textbox.tag_config("SENT_TAG", foreground=self.settings.ctm.TEXTBOX_SENT_TAG_TEXT_COLOR)
        target_textbox.tag_config("SENT_TEXT", foreground=self.settings.ctm.TEXTBOX_TEXT_COLOR)
        target_textbox.tag_config("SENT_SUB_TEXT", foreground=self.settings.ctm.TEXTBOX_TEXT_SUB_COLOR)

        # Received Tag Settings
        target_textbox.tag_config("RECEIVED_TAG", foreground=self.settings.ctm.TEXTBOX_RECEIVED_TAG_TEXT_COLOR)
        target_textbox.tag_config("RECEIVED_TEXT", foreground=self.settings.ctm.TEXTBOX_TEXT_COLOR)
        target_textbox.tag_config("RECEIVED_SUB_TEXT", foreground=self.settings.ctm.TEXTBOX_TEXT_SUB_COLOR)


    def _printEachTextbox(
            self,
            target_textbox,
            print_type,
            original_message,
            translated_message,
        ):
        now_raw_data = datetime.now()
        now_hm = now_raw_data.strftime("%H:%M")

        is_only_one_message = True if original_message is None or translated_message is None or translated_message == "" else False

        FAKE_MARGIN = "  "
        # insert
        target_textbox.configure(state="normal")
        target_textbox.insert("end", "\n")
        match (print_type):
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







    def _getTargetTextboxWidget(self, target_type):
        match (target_type):
            case "ALL":
                target_textbox = self.vrct_gui.textbox_all
            case "SYSTEM":
                target_textbox = self.vrct_gui.textbox_system
            case "SENT":
                target_textbox = self.vrct_gui.textbox_sent
            case "RECEIVED":
                target_textbox = self.vrct_gui.textbox_received
            case (_):
                raise  ValueError(f"No matching case for target_type: {target_type}")

        return target_textbox