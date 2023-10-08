from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Translation(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxEntry = sbg.createSettingBoxEntry


    def deepl_authkey_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_DEEPL_AUTHKEY, value)


    row=0
    config_window.sb__deepl_authkey = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_DEEPL_AUTH_KEY,
        for_var_desc_text=view_variable.VAR_DESC_DEEPL_AUTH_KEY,
        entry_attr_name="sb__entry_deepl_authkey",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_300,
        entry_bind__Any_KeyRelease=lambda value: deepl_authkey_callback(value),
        entry_textvariable=view_variable.VAR_DEEPL_AUTH_KEY,
    )
    config_window.sb__deepl_authkey.grid(row=row)
    row+=1