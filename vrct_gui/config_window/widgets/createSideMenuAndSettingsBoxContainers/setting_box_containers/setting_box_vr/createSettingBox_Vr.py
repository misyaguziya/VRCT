from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Vr(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxSwitch = sbg.createSettingBoxSwitch

    def switchEnableOverlayUiCallback(switch_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_OVERLAY_UI, switch_widget.get())


    row=0
    config_window.sb__enable_overlay_ui = createSettingBoxSwitch(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_OVERLAY_UI,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_OVERLAY_UI,
        switch_attr_name="sb__switch_enable_overlay_ui",
        command=lambda: switchEnableOverlayUiCallback(config_window.sb__switch_enable_overlay_ui),
        variable=view_variable.VAR_ENABLE_OVERLAY_UI
    )
    config_window.sb__enable_overlay_ui.grid(row=row, pady=0)
    row+=1