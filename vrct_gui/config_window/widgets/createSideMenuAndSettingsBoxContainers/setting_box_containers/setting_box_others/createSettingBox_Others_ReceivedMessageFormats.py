from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Others_ReceivedMessageFormats(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBox_Labels = sbg.createSettingBox_Labels
    createSettingBoxMessageFormatEntries = sbg.createSettingBoxMessageFormatEntries
    createSettingBoxMessageFormatEntries_WithTranslation = sbg.createSettingBoxMessageFormatEntries_WithTranslation

    def entryReceivedMessageFormatCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_RECEIVED_MESSAGE_FORMAT, value)


    def entryReceivedMessageFormatWithTCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_RECEIVED_MESSAGE_FORMAT_WITH_T, value)

    def entrySwapReceivedMessageFormatWithTCallback(_e):
        callFunctionIfCallable(view_variable.CALLBACK_SWAP_RECEIVED_MESSAGE_FORMAT_WITH_T_REQUIRED_TEXT)

    row=0
    config_window.sb__received_message_format_labels = createSettingBox_Labels(
        for_var_label_text=view_variable.VAR_LABEL_RECEIVED_MESSAGE_FORMAT,
        for_var_desc_text=view_variable.VAR_DESC_RECEIVED_MESSAGE_FORMAT,
        labels_attr_name="sb__labels_received_message_format",
    )
    config_window.sb__received_message_format_labels.grid(row=row, pady=0)
    row+=1

    config_window.sb__received_message_format = createSettingBoxMessageFormatEntries(
        base_entry_attr_name="sb__entry_received_message_format",
        entry_textvariable_0=view_variable.VAR_ENTRY_0_RECEIVED_MESSAGE_FORMAT,
        entry_textvariable_1=view_variable.VAR_ENTRY_1_RECEIVED_MESSAGE_FORMAT,
        textvariable_0=view_variable.VAR_TEXT_REQUIRED_0_RECEIVED_MESSAGE_FORMAT,
        example_label_textvariable=view_variable.VAR_LABEL_EXAMPLE_TEXT_RECEIVED_MESSAGE_FORMAT,
        entry_bind__Any_KeyRelease=lambda value: entryReceivedMessageFormatCallback(value),
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_RECEIVED_MESSAGE_FORMAT,
    )
    config_window.sb__received_message_format.grid(row=row)
    row+=1



    config_window.sb__received_message_format_with_t_labels = createSettingBox_Labels(
        for_var_label_text=view_variable.VAR_LABEL_RECEIVED_MESSAGE_FORMAT_WITH_T,
        for_var_desc_text=view_variable.VAR_DESC_RECEIVED_MESSAGE_FORMAT_WITH_T,
        labels_attr_name="sb__labels_message_format_with_t",
    )
    config_window.sb__received_message_format_with_t_labels.grid(row=row, pady=0)
    row+=1

    config_window.sb__received_message_format_with_t = createSettingBoxMessageFormatEntries_WithTranslation(
        base_entry_attr_name="sb__entry_received_message_format_with_t",
        entry_textvariable_0=view_variable.VAR_ENTRY_0_RECEIVED_MESSAGE_FORMAT_WITH_T,
        entry_textvariable_1=view_variable.VAR_ENTRY_1_RECEIVED_MESSAGE_FORMAT_WITH_T,
        entry_textvariable_2=view_variable.VAR_ENTRY_2_RECEIVED_MESSAGE_FORMAT_WITH_T,
        textvariable_0=view_variable.VAR_TEXT_REQUIRED_0_RECEIVED_MESSAGE_FORMAT_WITH_T,
        textvariable_1=view_variable.VAR_TEXT_REQUIRED_1_RECEIVED_MESSAGE_FORMAT_WITH_T,
        example_label_textvariable=view_variable.VAR_LABEL_EXAMPLE_TEXT_RECEIVED_MESSAGE_FORMAT_WITH_T,
        entry_bind__Any_KeyRelease=lambda value: entryReceivedMessageFormatWithTCallback(value),
        swap_button_command=entrySwapReceivedMessageFormatWithTCallback,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_RECEIVED_MESSAGE_FORMAT_WITH_T,
    )
    config_window.sb__received_message_format_with_t.grid(row=row, pady=0)
    row+=1