from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_AdvancedSettings(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxEntry = sbg.createSettingBoxEntry
    createSettingBoxButtonWithImage = sbg.createSettingBoxButtonWithImage


    def entryIpAddressCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_OSC_IP_ADDRESS, value)

    def entryPortCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_OSC_PORT, value)

    def openConfigFilepathCallback():
        callFunctionIfCallable(view_variable.CALLBACK_OPEN_FILEPATH_CONFIG_FILE)

    row=0
    config_window.sb__ip_address = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_OSC_IP_ADDRESS,
        for_var_desc_text=view_variable.VAR_DESC_OSC_IP_ADDRESS,
        entry_attr_name="sb__entry_ip_address",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_150,
        entry_bind__Any_KeyRelease=lambda value: entryIpAddressCallback(value),
        entry_textvariable=view_variable.VAR_OSC_IP_ADDRESS,
    )
    config_window.sb__ip_address.grid(row=row)
    row+=1


    config_window.sb__port = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_OSC_PORT,
        for_var_desc_text=view_variable.VAR_DESC_OSC_PORT,
        entry_attr_name="sb__entry_port",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_150,
        entry_bind__Any_KeyRelease=lambda value: entryPortCallback(value),
        entry_textvariable=view_variable.VAR_OSC_PORT,
    )
    config_window.sb__port.grid(row=row)
    row+=1

    config_window.sb__open_config_filepath = createSettingBoxButtonWithImage(
        for_var_label_text=view_variable.VAR_LABEL_OPEN_CONFIG_FILEPATH,
        for_var_desc_text=view_variable.VAR_DESC_OPEN_CONFIG_FILEPATH,
        button_attr_name="sb__button_open_config_filepath",
        button_command=lambda _e: openConfigFilepathCallback(),
        button_image=settings.image_file.FOLDER_OPEN_ICON,
    )
    config_window.sb__open_config_filepath.grid(row=row, pady=0)
    row+=1