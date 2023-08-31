from customtkinter import StringVar, IntVar

from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

from config import config

def createSettingBox_Others(setting_box_wrapper, config_window, settings):
    sbg = _SettingBoxGenerator(config_window, settings)
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox
    createSettingBoxEntry = sbg.createSettingBoxEntry


    # 元 checkbox_auto_clear_chatbox_callback
    def checkbox_auto_clear_message_box_callback(checkbox_box_widget):
        callFunctionIfCallable(config_window.CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX, checkbox_box_widget.get())

    def checkbox_notice_xsoverlay_callback(checkbox_box_widget):
        callFunctionIfCallable(config_window.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY, checkbox_box_widget.get())

    def entry_message_format_callback(value):
        callFunctionIfCallable(config_window.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY, value)


    row=0
    config_window.sb__auto_clear_message_box = createSettingBoxCheckbox(
        parent_widget=setting_box_wrapper,
        label_text="Auto Clear The Message Box",
        desc_text="Clear the message box after sending your message.",
        checkbox_attr_name="sb__checkbox_auto_clear_message_box",
        command=lambda: checkbox_auto_clear_message_box_callback(config_window.sb__checkbox_auto_clear_message_box),
        is_checked=False
    )
    config_window.sb__auto_clear_message_box.grid(row=row)
    row+=1


    config_window.sb__notice_xsoverlay = createSettingBoxCheckbox(
        parent_widget=setting_box_wrapper,
        label_text="Notification XSOverlay (VR Only)",
        desc_text="Notify received messages by using XSOverlay's notification feature.",
        checkbox_attr_name="sb__checkbox_notice_xsoverlay",
        command=lambda: checkbox_notice_xsoverlay_callback(config_window.sb__checkbox_notice_xsoverlay),
        is_checked=False
    )
    config_window.sb__notice_xsoverlay.grid(row=row)
    row+=1


    config_window.sb__message_format = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        label_text="Message Format",
        desc_text="You can change the decoration of the message you want to send. (Default: \"[message]([translation])\" )",
        entry_attr_name="sb__entry_message_format",
        entry_width=settings.uism.SB__ENTRY_WIDTH_250,
        entry_bind__Any_KeyRelease=lambda value: entry_message_format_callback(value),
        entry_textvariable=StringVar(value=config.MESSAGE_FORMAT),
    )
    config_window.sb__message_format.grid(row=row)
    row+=1