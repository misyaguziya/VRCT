from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Others(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox
    createSettingBoxAutoExportMessageLogs = sbg.createSettingBoxAutoExportMessageLogs


    def checkbox_auto_clear_message_box_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX, checkbox_box_widget.get())

    def checkbox_send_only_translated_messages_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_SEND_ONLY_TRANSLATED_MESSAGES, checkbox_box_widget.get())

    def checkbox_notice_xsoverlay_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY, checkbox_box_widget.get())

    def checkbox_auto_export_message_logs_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_AUTO_EXPORT_MESSAGE_LOGS, checkbox_box_widget.get())

    def button_auto_export_message_logs_callback():
        callFunctionIfCallable(view_variable.CALLBACK_OPEN_FILEPATH_LOGS)

    def checkbox_enable_send_message_to_vrc_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_SEND_MESSAGE_TO_VRC, checkbox_box_widget.get())


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

    config_window.sb__send_only_translated_messages = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_SEND_ONLY_TRANSLATED_MESSAGES,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_SEND_ONLY_TRANSLATED_MESSAGES,
        checkbox_attr_name="sb__checkbox_send_only_translated_messages",
        command=lambda: checkbox_send_only_translated_messages_callback(config_window.sb__checkbox_send_only_translated_messages),
        variable=view_variable.VAR_ENABLE_SEND_ONLY_TRANSLATED_MESSAGES,
    )
    config_window.sb__send_only_translated_messages.grid(row=row)
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


    config_window.sb__auto_export_message_logs = createSettingBoxAutoExportMessageLogs(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_AUTO_EXPORT_MESSAGE_LOGS,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_AUTO_EXPORT_MESSAGE_LOGS,
        checkbox_attr_name="sb__checkbox_auto_export_message_logs",
        checkbox_command=lambda: checkbox_auto_export_message_logs_callback(config_window.sb__checkbox_auto_export_message_logs),
        button_command=lambda _e: button_auto_export_message_logs_callback(),
        variable=view_variable.VAR_ENABLE_AUTO_EXPORT_MESSAGE_LOGS,
    )
    config_window.sb__auto_export_message_logs.grid(row=row)
    row+=1


    config_window.sb__enable_send_message_to_vrc = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_SEND_MESSAGE_TO_VRC,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_SEND_MESSAGE_TO_VRC,
        checkbox_attr_name="sb__checkbox_enable_send_message_to_vrc",
        command=lambda: checkbox_enable_send_message_to_vrc_callback(config_window.sb__checkbox_enable_send_message_to_vrc),
        variable=view_variable.VAR_ENABLE_SEND_MESSAGE_TO_VRC,
    )
    config_window.sb__enable_send_message_to_vrc.grid(row=row, pady=0)
    row+=1