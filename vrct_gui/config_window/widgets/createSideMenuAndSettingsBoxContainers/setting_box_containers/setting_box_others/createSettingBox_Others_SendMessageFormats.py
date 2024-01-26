from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Others_SendMessageFormats(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBox_Labels = sbg.createSettingBox_Labels
    createSettingBoxMessageFormatEntries = sbg.createSettingBoxMessageFormatEntries
    createSettingBoxMessageFormatEntries_WithTranslation = sbg.createSettingBoxMessageFormatEntries_WithTranslation

    def entrySendMessageFormatCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_SEND_MESSAGE_FORMAT, value)


    def entrySendMessageFormatWithTCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_SEND_MESSAGE_FORMAT_WITH_T, value)

    def entrySwapMessageFormatWithTCallback(_e):
        callFunctionIfCallable(view_variable.CALLBACK_SWAP_SEND_MESSAGE_FORMAT_WITH_T_REQUIRED_TEXT)


    row=0
    config_window.sb__send_message_format_labels = createSettingBox_Labels(
        for_var_label_text=view_variable.VAR_LABEL_SEND_MESSAGE_FORMAT,
        for_var_desc_text=view_variable.VAR_DESC_SEND_MESSAGE_FORMAT,
        labels_attr_name="sb__labels_send_message_format",
    )
    config_window.sb__send_message_format_labels.grid(row=row, pady=0)
    row+=1

    config_window.sb__message_format = createSettingBoxMessageFormatEntries(
        base_entry_attr_name="sb__entry_send_message_format",
        entry_textvariable_0=view_variable.VAR_ENTRY_0_SEND_MESSAGE_FORMAT,
        entry_textvariable_1=view_variable.VAR_ENTRY_1_SEND_MESSAGE_FORMAT,
        textvariable_0=view_variable.VAR_TEXT_REQUIRED_0_SEND_MESSAGE_FORMAT,
        example_label_textvariable=view_variable.VAR_LABEL_EXAMPLE_TEXT_SEND_MESSAGE_FORMAT,
        entry_bind__Any_KeyRelease=lambda value: entrySendMessageFormatCallback(value),
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_SEND_MESSAGE_FORMAT,
    )
    config_window.sb__message_format.grid(row=row)
    row+=1



    config_window.sb__send_message_format_with_t_labels = createSettingBox_Labels(
        for_var_label_text=view_variable.VAR_LABEL_SEND_MESSAGE_FORMAT_WITH_T,
        for_var_desc_text=view_variable.VAR_DESC_SEND_MESSAGE_FORMAT_WITH_T,
        labels_attr_name="sb__labels_send_message_format_with_t",
    )
    config_window.sb__send_message_format_with_t_labels.grid(row=row, pady=0)
    row+=1

    config_window.sb__message_format_with_t = createSettingBoxMessageFormatEntries_WithTranslation(
        base_entry_attr_name="sb__entry_send_message_format_with_t",
        entry_textvariable_0=view_variable.VAR_ENTRY_0_SEND_MESSAGE_FORMAT_WITH_T,
        entry_textvariable_1=view_variable.VAR_ENTRY_1_SEND_MESSAGE_FORMAT_WITH_T,
        entry_textvariable_2=view_variable.VAR_ENTRY_2_SEND_MESSAGE_FORMAT_WITH_T,
        textvariable_0=view_variable.VAR_TEXT_REQUIRED_0_SEND_MESSAGE_FORMAT_WITH_T,
        textvariable_1=view_variable.VAR_TEXT_REQUIRED_1_SEND_MESSAGE_FORMAT_WITH_T,
        example_label_textvariable=view_variable.VAR_LABEL_EXAMPLE_TEXT_SEND_MESSAGE_FORMAT_WITH_T,
        entry_bind__Any_KeyRelease=lambda value: entrySendMessageFormatWithTCallback(value),
        swap_button_command=entrySwapMessageFormatWithTCallback,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_SEND_MESSAGE_FORMAT_WITH_T,
    )
    config_window.sb__message_format_with_t.grid(row=row, pady=0)
    row+=1