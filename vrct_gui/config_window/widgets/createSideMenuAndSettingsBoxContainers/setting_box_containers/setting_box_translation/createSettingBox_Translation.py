from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Translation(setting_box_wrapper, config_window, settings):
    sbg = _SettingBoxGenerator(config_window, settings)
    createSettingBoxEntry = sbg.createSettingBoxEntry


    def deepl_authkey_callback(value):
        callFunctionIfCallable(config_window.CALLBACK_SET_DEEPL_AUTHKEY, value)


    row=0
    config_window.sb__deepl_authkey = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        for_var_label_text=config_window.view_variable.VAR_LABEL_DEEPL_AUTH_KEY,
        for_var_desc_text=config_window.view_variable.VAR_DESC_DEEPL_AUTH_KEY,
        entry_attr_name="sb__deepl_authkey",
        entry_width=settings.uism.SB__ENTRY_WIDTH_300,
        entry_bind__Any_KeyRelease=lambda value: deepl_authkey_callback(value),
        entry_textvariable=config_window.view_variable.VAR_DEEPL_AUTH_KEY,
    )
    config_window.sb__deepl_authkey.grid(row=row)
    row+=1