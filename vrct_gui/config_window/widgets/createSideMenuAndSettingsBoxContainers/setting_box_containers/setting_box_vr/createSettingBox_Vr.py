from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Vr(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBox_Overlay = sbg.createSettingBox_Overlay
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox

    def switchEnableOverlayUiCallback(switch_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_OVERLAY_SMALL_LOG, switch_widget.get())

    def buttonOpenOverlaySettingsWindow(_e):
        callFunctionIfCallable(view_variable.CALLBACK_SET_OPEN_OVERLAY_SETTINGS_WINDOW)


    def checkboxNoticeXsoverlayCallback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_NOTICE_XSOVERLAY, checkbox_box_widget.get())


    row=0
    config_window.sb__enable_overlay_small_log = createSettingBox_Overlay(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_OVERLAY_SMALL_LOG,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_OVERLAY_SMALL_LOG,
        switch_attr_name="sb__switch_enable_overlay_small_log",
        command=lambda: switchEnableOverlayUiCallback(config_window.sb__switch_enable_overlay_small_log),
        variable=view_variable.VAR_ENABLE_OVERLAY_SMALL_LOG,
        for_var_button_label=view_variable.VAR_OPEN_OVERLAY_SETTINGS_BUTTON,
        label_button_clicked_command=buttonOpenOverlaySettingsWindow,
    )
    config_window.sb__enable_overlay_small_log.grid(row=row)
    row+=1


    config_window.sb__notice_xsoverlay = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_ENABLE_NOTICE_XSOVERLAY,
        for_var_desc_text=view_variable.VAR_DESC_ENABLE_NOTICE_XSOVERLAY,
        checkbox_attr_name="sb__checkbox_notice_xsoverlay",
        command=lambda: checkboxNoticeXsoverlayCallback(config_window.sb__checkbox_notice_xsoverlay),
        variable=view_variable.VAR_ENABLE_NOTICE_XSOVERLAY,
    )
    config_window.sb__notice_xsoverlay.grid(row=row, pady=0)
    row+=1