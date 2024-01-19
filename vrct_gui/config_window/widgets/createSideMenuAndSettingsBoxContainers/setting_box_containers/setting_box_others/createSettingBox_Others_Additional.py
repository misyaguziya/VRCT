from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Others_Additional(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox

    def checkboxEnableSendReceivedMessageToVrcCallback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC, checkbox_box_widget.get())


    row=0
    config_window.sb__enable_send_received_message_to_vrc = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC,
        checkbox_attr_name="sb__checkbox_enable_send_received_message_to_vrc",
        command=lambda: checkboxEnableSendReceivedMessageToVrcCallback(config_window.sb__checkbox_enable_send_received_message_to_vrc),
        variable=view_variable.VAR_ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC,
    )
    config_window.sb__enable_send_received_message_to_vrc.grid(row=row, pady=0)
    row+=1