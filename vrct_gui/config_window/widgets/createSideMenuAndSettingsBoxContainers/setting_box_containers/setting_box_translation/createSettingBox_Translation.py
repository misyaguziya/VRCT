from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Translation(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxSwitch = sbg.createSettingBoxSwitch
    createSettingBoxDropdownMenu = sbg.createSettingBoxDropdownMenu
    createSettingBoxEntry = sbg.createSettingBoxEntry

    def switch_use_translation_feature_callback(switch_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_USE_TRANSLATION_FEATURE, switch_widget.get())

    def optionmenu_ctranslate2_weight_type_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_CTRANSLATE2_WEIGHT_TYPE, value)

    def deepl_authkey_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_DEEPL_AUTHKEY, value)


    row=0
    config_window.sb__use_translation_feature = createSettingBoxSwitch(
        for_var_label_text=view_variable.VAR_LABEL_USE_TRANSLATION_FEATURE,
        for_var_desc_text=view_variable.VAR_DESC_USE_TRANSLATION_FEATURE,
        switch_attr_name="sb__switch_use_translation_feature",
        command=lambda: switch_use_translation_feature_callback(config_window.sb__switch_use_translation_feature),
        variable=view_variable.VAR_USE_TRANSLATION_FEATURE
    )
    config_window.sb__use_translation_feature.grid(row=row, pady=0)
    row+=1

    config_window.sb__ctranslate2_weight_type = createSettingBoxDropdownMenu(
        for_var_label_text=view_variable.VAR_LABEL_CTRANSLATE2_WEIGHT_TYPE,
        for_var_desc_text=view_variable.VAR_DESC_CTRANSLATE2_WEIGHT_TYPE,
        optionmenu_attr_name="sb__optionmenu_ctranslate2_weight_type",
        dropdown_menu_values=view_variable.DICT_CTRANSLATE2_WEIGHT_TYPE,
        command=lambda value: optionmenu_ctranslate2_weight_type_callback(value),
        variable=view_variable.VAR_CTRANSLATE2_WEIGHT_TYPE,
    )
    config_window.sb__ctranslate2_weight_type.grid(row=row)
    row+=1


    config_window.sb__deepl_authkey = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_DEEPL_AUTH_KEY,
        for_var_desc_text=view_variable.VAR_DESC_DEEPL_AUTH_KEY,
        entry_attr_name="sb__entry_deepl_authkey",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_300,
        entry_bind__Any_KeyRelease=lambda value: deepl_authkey_callback(value),
        entry_textvariable=view_variable.VAR_DEEPL_AUTH_KEY,
    )
    config_window.sb__deepl_authkey.grid(row=row, pady=0)
    row+=1