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
        for_var_label_text=config_window.view_variable.VAR_LABEL_ENABLE_AUTO_CLEAR_MESSAGE_BOX,
        for_var_desc_text=config_window.view_variable.VAR_DESC_ENABLE_AUTO_CLEAR_MESSAGE_BOX,
        checkbox_attr_name="sb__checkbox_auto_clear_message_box",
        command=lambda: checkbox_auto_clear_message_box_callback(config_window.sb__checkbox_auto_clear_message_box),
        variable=config_window.view_variable.VAR_ENABLE_AUTO_CLEAR_MESSAGE_BOX,
    )
    config_window.sb__auto_clear_message_box.grid(row=row)
    row+=1


    config_window.sb__notice_xsoverlay = createSettingBoxCheckbox(
        parent_widget=setting_box_wrapper,
        for_var_label_text=config_window.view_variable.VAR_LABEL_ENABLE_NOTICE_XSOVERLAY,
        for_var_desc_text=config_window.view_variable.VAR_DESC_ENABLE_NOTICE_XSOVERLAY,
        checkbox_attr_name="sb__checkbox_notice_xsoverlay",
        command=lambda: checkbox_notice_xsoverlay_callback(config_window.sb__checkbox_notice_xsoverlay),
        variable=config_window.view_variable.VAR_ENABLE_NOTICE_XSOVERLAY,
    )
    config_window.sb__notice_xsoverlay.grid(row=row)
    row+=1


    config_window.sb__message_format = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        for_var_label_text=config_window.view_variable.VAR_LABEL_MESSAGE_FORMAT,
        for_var_desc_text=config_window.view_variable.VAR_DESC_MESSAGE_FORMAT,
        entry_attr_name="sb__entry_message_format",
        entry_width=settings.uism.SB__ENTRY_WIDTH_250,
        entry_bind__Any_KeyRelease=lambda value: entry_message_format_callback(value),
        entry_textvariable=config_window.view_variable.VAR_MESSAGE_FORMAT,
    )
    config_window.sb__message_format.grid(row=row)
    row+=1