from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Others(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox
    createSettingBoxEntry = sbg.createSettingBoxEntry


    # 元 checkbox_auto_clear_chatbox_callback
    def checkbox_auto_clear_message_box_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX, checkbox_box_widget.get())

    def checkbox_notice_xsoverlay_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY, checkbox_box_widget.get())

    def checkbox_auto_export_message_logs_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_AUTO_EXPORT_MESSAGE_LOGS, checkbox_box_widget.get())

    def checkbox_enable_send_message_to_vrc_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_SEND_MESSAGE_TO_VRC, checkbox_box_widget.get())

    def checkbox_startup_osc_enabled_check_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_STARTUP_OSC_ENABLED_CHECK, checkbox_box_widget.get())

    def entry_message_format_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MESSAGE_FORMAT, value)


    row=0
    config_window.sb__auto_clear_message_box = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_AUTO_CLEAR_MESSAGE_BOX,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_AUTO_CLEAR_MESSAGE_BOX,
        checkbox_attr_name="sb__checkbox_auto_clear_message_box",
        command=lambda: checkbox_auto_clear_message_box_callback(config_window.sb__checkbox_auto_clear_message_box),
        variable=view_variable.VAR_ENABLE_AUTO_CLEAR_MESSAGE_BOX,
    )
    config_window.sb__auto_clear_message_box.grid(row=row)
    row+=1


    config_window.sb__notice_xsoverlay = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_NOTICE_XSOVERLAY,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_NOTICE_XSOVERLAY,
        checkbox_attr_name="sb__checkbox_notice_xsoverlay",
        command=lambda: checkbox_notice_xsoverlay_callback(config_window.sb__checkbox_notice_xsoverlay),
        variable=view_variable.VAR_ENABLE_NOTICE_XSOVERLAY,
    )
    config_window.sb__notice_xsoverlay.grid(row=row)
    row+=1


    config_window.sb__auto_export_message_logs = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_AUTO_EXPORT_MESSAGE_LOGS,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_AUTO_EXPORT_MESSAGE_LOGS,
        checkbox_attr_name="sb__checkbox_auto_export_message_logs",
        command=lambda: checkbox_auto_export_message_logs_callback(config_window.sb__checkbox_auto_export_message_logs),
        variable=view_variable.VAR_ENABLE_AUTO_EXPORT_MESSAGE_LOGS,
    )
    config_window.sb__auto_export_message_logs.grid(row=row)
    row+=1


    config_window.sb__message_format = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_MESSAGE_FORMAT,
        for_var_desc_text=view_variable.VAR_DESC_MESSAGE_FORMAT,
        entry_attr_name="sb__entry_message_format",
        entry_width=settings.uism.SB__ENTRY_WIDTH_250,
        entry_bind__Any_KeyRelease=lambda value: entry_message_format_callback(value),
        entry_textvariable=view_variable.VAR_MESSAGE_FORMAT,
    )
    config_window.sb__message_format.grid(row=row)
    row+=1


    config_window.sb__enable_send_message_to_vrc = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_SEND_MESSAGE_TO_VRC,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_SEND_MESSAGE_TO_VRC,
        checkbox_attr_name="sb__checkbox_enable_send_message_to_vrc",
        command=lambda: checkbox_enable_send_message_to_vrc_callback(config_window.sb__checkbox_enable_send_message_to_vrc),
        variable=view_variable.VAR_ENABLE_SEND_MESSAGE_TO_VRC,
    )
    config_window.sb__enable_send_message_to_vrc.grid(row=row)
    row+=1

    config_window.sb__startup_osc_enabled_check = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_STARTUP_OSC_ENABLED_CHECK,
        for_var_desc_text=view_variable.VAR_DESC_STARTUP_OSC_ENABLED_CHECK,
        checkbox_attr_name="sb__checkbox_startup_osc_enabled_check",
        command=lambda: checkbox_startup_osc_enabled_check_callback(config_window.sb__checkbox_startup_osc_enabled_check),
        variable=view_variable.VAR_STARTUP_OSC_ENABLED_CHECK,
    )
    config_window.sb__startup_osc_enabled_check.grid(row=row)
    row+=1

