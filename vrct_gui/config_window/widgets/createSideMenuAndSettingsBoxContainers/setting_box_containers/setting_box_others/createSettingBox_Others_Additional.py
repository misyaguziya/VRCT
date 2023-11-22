from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Others_Additional(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox
    createSettingBox_Labels = sbg.createSettingBox_Labels
    createSettingBoxMessageFormatEntries = sbg.createSettingBoxMessageFormatEntries


    def checkbox_enable_send_received_message_to_vrc_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC, checkbox_box_widget.get())

    def entry_received_message_format_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_RECEIVED_MESSAGE_FORMAT, value)

    def entry_swap_received_message_format_callback(_e):
        callFunctionIfCallable(view_variable.CALLBACK_SWAP_RECEIVED_MESSAGE_FORMAT_REQUIRED_TEXT)

    row=0
    config_window.sb__received_message_format_labels = createSettingBox_Labels(
        for_var_label_text=view_variable.VAR_LABEL_RECEIVED_MESSAGE_FORMAT,
        # for_var_desc_text=view_variable.VAR_DESC_RECEIVED_MESSAGE_FORMAT,
        labels_attr_name="sb__labels_message_format",
    )
    config_window.sb__received_message_format_labels.grid(row=row, pady=0)
    row+=1

    config_window.sb__received_message_format = createSettingBoxMessageFormatEntries(
        base_entry_attr_name="sb__entry_received_message_format",
        # entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_150,
        entry_textvariable_0=view_variable.VAR_ENTRY_0_RECEIVED_MESSAGE_FORMAT,
        entry_textvariable_1=view_variable.VAR_ENTRY_1_RECEIVED_MESSAGE_FORMAT,
        entry_textvariable_2=view_variable.VAR_ENTRY_2_RECEIVED_MESSAGE_FORMAT,
        textvariable_0=view_variable.VAR_TEXT_REQUIRED_0_RECEIVED_MESSAGE_FORMAT,
        textvariable_1=view_variable.VAR_TEXT_REQUIRED_1_RECEIVED_MESSAGE_FORMAT,
        example_label_textvariable=view_variable.VAR_LABEL_EXAMPLE_TEXT_RECEIVED_MESSAGE_FORMAT,
        entry_bind__Any_KeyRelease=lambda value: entry_received_message_format_callback(value),
        swap_button_command=entry_swap_received_message_format_callback,
        # entry_textvariable=view_variable.VAR_RECEIVED_MESSAGE_FORMAT,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_RECEIVED_MESSAGE_FORMAT,
    )
    config_window.sb__received_message_format.grid(row=row)
    row+=1


    config_window.sb__enable_send_received_message_to_vrc = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC,
        # for_var_desc_text=view_variable.VAR_DESC_ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC,
        checkbox_attr_name="sb__checkbox_enable_send_received_message_to_vrc",
        command=lambda: checkbox_enable_send_received_message_to_vrc_callback(config_window.sb__checkbox_enable_send_received_message_to_vrc),
        variable=view_variable.VAR_ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC,
    )
    config_window.sb__enable_send_received_message_to_vrc.grid(row=row, pady=0)
    row+=1