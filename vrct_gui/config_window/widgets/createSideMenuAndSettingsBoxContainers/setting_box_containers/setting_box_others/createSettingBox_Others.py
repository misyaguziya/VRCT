from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Others(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox
    createSettingBoxRadioButtons = sbg.createSettingBoxRadioButtons
    createSettingBoxAutoExportMessageLogs = sbg.createSettingBoxAutoExportMessageLogs


    def checkboxAutoClearMessageBoxCallback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_AUTO_CLEAR_MESSAGE_BOX, checkbox_box_widget.get())

    def checkboxSendOnlyTranslatedMessagesCallback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_SEND_ONLY_TRANSLATED_MESSAGES, checkbox_box_widget.get())

    def checkboxSendMessageButtonTypeCallback():
        callFunctionIfCallable(view_variable.CALLBACK_SET_SEND_MESSAGE_BUTTON_TYPE, view_variable.VAR_SEND_MESSAGE_BUTTON_TYPE.get())

    def checkboxNoticeXsoverlayCallback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY, checkbox_box_widget.get())

    def checkboxAutoExportMessageLogsCallback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_AUTO_EXPORT_MESSAGE_LOGS, checkbox_box_widget.get())

    def buttonAutoExportMessageLogsCallback():
        callFunctionIfCallable(view_variable.CALLBACK_OPEN_FILEPATH_LOGS)

    def checkboxEnableSendMessageToVrcCallback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_SEND_MESSAGE_TO_VRC, checkbox_box_widget.get())


    row=0
    config_window.sb__auto_clear_message_box = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_AUTO_CLEAR_MESSAGE_BOX,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_AUTO_CLEAR_MESSAGE_BOX,
        checkbox_attr_name="sb__checkbox_auto_clear_message_box",
        command=lambda: checkboxAutoClearMessageBoxCallback(config_window.sb__checkbox_auto_clear_message_box),
        variable=view_variable.VAR_ENABLE_AUTO_CLEAR_MESSAGE_BOX,
    )
    config_window.sb__auto_clear_message_box.grid(row=row)
    row+=1

    config_window.sb__send_only_translated_messages = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_SEND_ONLY_TRANSLATED_MESSAGES,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_SEND_ONLY_TRANSLATED_MESSAGES,
        checkbox_attr_name="sb__checkbox_send_only_translated_messages",
        command=lambda: checkboxSendOnlyTranslatedMessagesCallback(config_window.sb__checkbox_send_only_translated_messages),
        variable=view_variable.VAR_ENABLE_SEND_ONLY_TRANSLATED_MESSAGES,
    )
    config_window.sb__send_only_translated_messages.grid(row=row)
    row+=1

    config_window.sb__send_message_button_type = createSettingBoxRadioButtons(
        for_var_label_text=view_variable.VAR_LABEL_SEND_MESSAGE_BUTTON_TYPE,
        for_var_desc_text=view_variable.VAR_DESC_SEND_MESSAGE_BUTTON_TYPE,
        radio_button_attr_name="sb__radiobutton_send_message_button_type",
        command=lambda: checkboxSendMessageButtonTypeCallback(),
        variable=view_variable.VAR_SEND_MESSAGE_BUTTON_TYPE,
        radiobutton_keys_values=view_variable.KEYS_VALUES_SEND_MESSAGE_BUTTON_TYPE,
    )
    config_window.sb__send_message_button_type.grid(row=row)
    row+=1

    config_window.sb__notice_xsoverlay = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_NOTICE_XSOVERLAY,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_NOTICE_XSOVERLAY,
        checkbox_attr_name="sb__checkbox_notice_xsoverlay",
        command=lambda: checkboxNoticeXsoverlayCallback(config_window.sb__checkbox_notice_xsoverlay),
        variable=view_variable.VAR_ENABLE_NOTICE_XSOVERLAY,
    )
    config_window.sb__notice_xsoverlay.grid(row=row)
    row+=1


    config_window.sb__auto_export_message_logs = createSettingBoxAutoExportMessageLogs(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_AUTO_EXPORT_MESSAGE_LOGS,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_AUTO_EXPORT_MESSAGE_LOGS,
        checkbox_attr_name="sb__checkbox_auto_export_message_logs",
        checkbox_command=lambda: checkboxAutoExportMessageLogsCallback(config_window.sb__checkbox_auto_export_message_logs),
        button_command=lambda _e: buttonAutoExportMessageLogsCallback(),
        variable=view_variable.VAR_ENABLE_AUTO_EXPORT_MESSAGE_LOGS,
    )
    config_window.sb__auto_export_message_logs.grid(row=row)
    row+=1


    config_window.sb__enable_send_message_to_vrc = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_SEND_MESSAGE_TO_VRC,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_SEND_MESSAGE_TO_VRC,
        checkbox_attr_name="sb__checkbox_enable_send_message_to_vrc",
        command=lambda: checkboxEnableSendMessageToVrcCallback(config_window.sb__checkbox_enable_send_message_to_vrc),
        variable=view_variable.VAR_ENABLE_SEND_MESSAGE_TO_VRC,
    )
    config_window.sb__enable_send_message_to_vrc.grid(row=row, pady=0)
    row+=1