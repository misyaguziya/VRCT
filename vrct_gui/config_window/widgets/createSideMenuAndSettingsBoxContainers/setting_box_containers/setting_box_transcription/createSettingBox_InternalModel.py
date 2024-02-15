from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_InternalModel(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxSwitch = sbg.createSettingBoxSwitch
    createSettingBoxDropdownMenu = sbg.createSettingBoxDropdownMenu

    def switchUseWhisperFeatureCallback(switch_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_USE_WHISPER_FEATURE, switch_widget.get())

    def optionmenuWhisperWeightTypeCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_WHISPER_WEIGHT_TYPE, value)


    row=0
    config_window.sb__use_whisper_feature = createSettingBoxSwitch(
        for_var_label_text=view_variable.VAR_LABEL_USE_WHISPER_FEATURE,
        for_var_desc_text=view_variable.VAR_DESC_USE_WHISPER_FEATURE,
        switch_attr_name="sb__switch_use_whisper_feature",
        command=lambda: switchUseWhisperFeatureCallback(config_window.sb__switch_use_whisper_feature),
        variable=view_variable.VAR_USE_WHISPER_FEATURE
    )
    config_window.sb__use_whisper_feature.grid(row=row, pady=0)
    row+=1

    config_window.sb__whisper_weight_type = createSettingBoxDropdownMenu(
        for_var_label_text=view_variable.VAR_LABEL_WHISPER_WEIGHT_TYPE,
        for_var_desc_text=view_variable.VAR_DESC_WHISPER_WEIGHT_TYPE,
        optionmenu_attr_name="sb__optionmenu_whisper_weight_type",
        dropdown_menu_values=view_variable.DICT_WHISPER_WEIGHT_TYPE,
        command=lambda value: optionmenuWhisperWeightTypeCallback(value),
        variable=view_variable.VAR_WHISPER_WEIGHT_TYPE,
    )
    config_window.sb__whisper_weight_type.grid(row=row, pady=0)
    row+=1