from utils import callFunctionIfCallable, floatToPctStr

from customtkinter import CTkImage, CTkLabel, CTkToplevel, CTkProgressBar, CTkFrame, CTkSlider
from ..ui_utils import getImagePath, setGeometryToCenterOfScreen, fadeInAnimation, createLabelButton

from ._CreateQuickSettingBox import _CreateQuickSettingBox

class QuickSettingsWindow(CTkToplevel):
    def __init__(self, vrct_gui, settings, view_variable):
        super().__init__()
        self.withdraw()
        self.title("Overlay Settings")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self.after(200, lambda: self.iconbitmap(getImagePath("vrct_logo_mark_black.ico")))


        self.settings = settings

        self.configure(fg_color=self.settings.ctm.SB__BG_COLOR)

        BG_HEX_COLOR = "#292a2d"

        self.qsw_background = CTkFrame(self, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        self.qsw_background.grid(row=0, column=0, pady=0, sticky="ew")
        self.qsw_background.grid_columnconfigure(0, weight=1, minsize=400)


        self.qsw_background__overlay = CTkFrame(self.qsw_background, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        self.qsw_background__overlay.grid(row=0, column=0, pady=(0,18), sticky="ew")
        self.qsw_background__overlay.grid_columnconfigure(0, weight=1)


        self.qsw_setting_box__overlay = CTkFrame(self.qsw_background__overlay, corner_radius=0, fg_color=BG_HEX_COLOR)
        self.qsw_setting_box__overlay.grid(row=0, column=0, sticky="ew")
        self.qsw_setting_box__overlay.grid_columnconfigure(0, weight=1)

        cqsb = _CreateQuickSettingBox(self.qsw_setting_box__overlay, vrct_gui, settings, view_variable)
        createSettingBoxSlider = cqsb.createSettingBoxSlider
        createSettingBoxSwitch = cqsb.createSettingBoxSwitch





        # Overlay General Settings
        row=0
        def overlaySmallLogSwitchCallback(switch_widget):
            callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_OVERLAY_SMALL_LOG, switch_widget.get())

        self.qsb__enable_overlay_small_log = createSettingBoxSwitch(
            for_var_label_text=view_variable.VAR_LABEL_ENABLE_OVERLAY_SMALL_LOG,
            switch_attr_name="qsb__enable_overlay_small_log_switch",
            command=lambda: overlaySmallLogSwitchCallback(vrct_gui.qsb__enable_overlay_small_log_switch),
            variable=view_variable.VAR_ENABLE_OVERLAY_SMALL_LOG,
        )
        self.qsb__enable_overlay_small_log.grid(row=row)


        row+=1
        def overlayOpacitySliderCallback(e):
            value = round(e,2)
            callFunctionIfCallable(view_variable.CALLBACK_SET_OVERLAY_SETTINGS, value, "opacity")
            view_variable.VAR_CURRENT_VALUE_OVERLAY_OPACITY.set(floatToPctStr(value))

        self.qsb__overlay_opacity = createSettingBoxSlider(
            for_var_label_text=view_variable.VAR_LABEL_OVERLAY_OPACITY,
            for_var_current_value=view_variable.VAR_CURRENT_VALUE_OVERLAY_OPACITY,
            slider_attr_name="qsb__overlay_opacity_slider",
            slider_range=view_variable.SLIDER_RANGE_OVERLAY_OPACITY,
            slider_number_of_steps=view_variable.NUMBER_OF_STEPS_OVERLAY_OPACITY,
            command=overlayOpacitySliderCallback,
            variable=view_variable.VAR_OVERLAY_OPACITY,
        )
        self.qsb__overlay_opacity.grid(row=row)


        row+=1
        def overlayUiScalingSliderCallback(e):
            value = round(e,2)
            callFunctionIfCallable(view_variable.CALLBACK_SET_OVERLAY_SETTINGS, value, "ui_scaling")
            view_variable.VAR_CURRENT_VALUE_OVERLAY_UI_SCALING.set(floatToPctStr(value))

        self.qsb__overlay_ui_scaling = createSettingBoxSlider(
            for_var_label_text=view_variable.VAR_LABEL_OVERLAY_UI_SCALING,
            for_var_current_value=view_variable.VAR_CURRENT_VALUE_OVERLAY_UI_SCALING,
            slider_attr_name="qsb__overlay_ui_scaling_slider",
            slider_range=view_variable.SLIDER_RANGE_OVERLAY_UI_SCALING,
            slider_number_of_steps=view_variable.NUMBER_OF_STEPS_OVERLAY_UI_SCALING,
            command=overlayUiScalingSliderCallback,
            variable=view_variable.VAR_OVERLAY_UI_SCALING,
        )
        self.qsb__overlay_ui_scaling.grid(row=row)



        # Overlay Small Log Settings

        # row+=1
        # def switchCallback(switch_widget):
        #     callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_OVERLAY_SMALL_LOG, switch_widget.get())

        # self.qsb__enable_overlay_small_log = createSettingBoxSwitch(
        #     for_var_label_text=view_variable.VAR_LABEL_ENABLE_OVERLAY_SMALL_LOG,
        #     switch_attr_name="qsb__enable_overlay_small_log_switch",
        #     command=lambda: switchCallback(vrct_gui.qsb__enable_overlay_small_log_switch),
        #     variable=view_variable.VAR_ENABLE_OVERLAY_SMALL_LOG,
        # )
        # self.qsb__enable_overlay_small_log.grid(row=row)



        row+=1
        def overlaySmallLogSettingsXPosSliderCallback(e):
            value = round(e,2)
            callFunctionIfCallable(view_variable.CALLBACK_SET_OVERLAY_SMALL_LOG_SETTINGS, value, "x_pos")
            view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_X_POS.set(str(value))

        self.qsb__overlay_small_log_settings_x_pos = createSettingBoxSlider(
            for_var_label_text=view_variable.VAR_LABEL_OVERLAY_SMALL_LOG_X_POS,
            for_var_current_value=view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_X_POS,
            slider_attr_name="qsb__overlay_small_log_settings_x_pos_slider",
            slider_range=view_variable.SLIDER_RANGE_OVERLAY_SMALL_LOG_X_POS,
            slider_number_of_steps=view_variable.NUMBER_OF_STEPS_OVERLAY_SMALL_LOG_X_POS,
            command=overlaySmallLogSettingsXPosSliderCallback,
            variable=view_variable.VAR_OVERLAY_SMALL_LOG_X_POS,
        )
        self.qsb__overlay_small_log_settings_x_pos.grid(row=row)


        row+=1
        def overlaySmallLogSettingsYPosSliderCallback(e):
            value = round(e,2)
            callFunctionIfCallable(view_variable.CALLBACK_SET_OVERLAY_SMALL_LOG_SETTINGS, value, "y_pos")
            view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_Y_POS.set(str(value))

        self.qsb__overlay_small_log_settings_y_pos = createSettingBoxSlider(
            for_var_label_text=view_variable.VAR_LABEL_OVERLAY_SMALL_LOG_Y_POS,
            for_var_current_value=view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_Y_POS,
            slider_attr_name="qsb__overlay_small_log_settings_y_pos_slider",
            slider_range=view_variable.SLIDER_RANGE_OVERLAY_SMALL_LOG_Y_POS,
            slider_number_of_steps=view_variable.NUMBER_OF_STEPS_OVERLAY_SMALL_LOG_Y_POS,
            command=overlaySmallLogSettingsYPosSliderCallback,
            variable=view_variable.VAR_OVERLAY_SMALL_LOG_Y_POS,
        )
        self.qsb__overlay_small_log_settings_y_pos.grid(row=row)


        row+=1
        def overlaySmallLogSettingsDepthSliderCallback(e):
            value = round(e,2)
            callFunctionIfCallable(view_variable.CALLBACK_SET_OVERLAY_SMALL_LOG_SETTINGS, value, "depth")
            view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_DEPTH.set(str(value))

        self.qsb__overlay_small_log_settings_depth = createSettingBoxSlider(
            for_var_label_text=view_variable.VAR_LABEL_OVERLAY_SMALL_LOG_DEPTH,
            for_var_current_value=view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_DEPTH,
            slider_attr_name="qsb__overlay_small_log_settings_depth_slider",
            slider_range=view_variable.SLIDER_RANGE_OVERLAY_SMALL_LOG_DEPTH,
            slider_number_of_steps=view_variable.NUMBER_OF_STEPS_OVERLAY_SMALL_LOG_DEPTH,
            command=overlaySmallLogSettingsDepthSliderCallback,
            variable=view_variable.VAR_OVERLAY_SMALL_LOG_DEPTH,
        )
        self.qsb__overlay_small_log_settings_depth.grid(row=row)


        row+=1
        def overlaySmallLogSettingsDisplayDurationSliderCallback(e):
            value = int(e)
            callFunctionIfCallable(view_variable.CALLBACK_SET_OVERLAY_SMALL_LOG_SETTINGS, value, "display_duration")
            view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_DISPLAY_DURATION.set(f"{value} second(s)")

        self.qsb__overlay_small_log_settings_display_duration = createSettingBoxSlider(
            for_var_label_text=view_variable.VAR_LABEL_OVERLAY_SMALL_LOG_DISPLAY_DURATION,
            for_var_current_value=view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_DISPLAY_DURATION,
            slider_attr_name="qsb__overlay_small_log_settings_display_duration_slider",
            slider_range=view_variable.SLIDER_RANGE_OVERLAY_SMALL_LOG_DISPLAY_DURATION,
            slider_number_of_steps=view_variable.NUMBER_OF_STEPS_OVERLAY_SMALL_LOG_DISPLAY_DURATION,
            command=overlaySmallLogSettingsDisplayDurationSliderCallback,
            variable=view_variable.VAR_OVERLAY_SMALL_LOG_DISPLAY_DURATION,
        )
        self.qsb__overlay_small_log_settings_display_duration.grid(row=row)



        row+=1
        def overlaySmallLogSettingsFadeoutDurationSliderCallback(e):
            value = int(e)
            callFunctionIfCallable(view_variable.CALLBACK_SET_OVERLAY_SMALL_LOG_SETTINGS, value, "fadeout_duration")
            view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_FADEOUT_DURATION.set(f"{value} second(s)")

        self.qsb__overlay_small_log_settings_fadeout_duration = createSettingBoxSlider(
            for_var_label_text=view_variable.VAR_LABEL_OVERLAY_SMALL_LOG_FADEOUT_DURATION,
            for_var_current_value=view_variable.VAR_CURRENT_VALUE_OVERLAY_SMALL_LOG_FADEOUT_DURATION,
            slider_attr_name="qsb__overlay_small_log_settings_fadeout_duration_slider",
            slider_range=view_variable.SLIDER_RANGE_OVERLAY_SMALL_LOG_FADEOUT_DURATION,
            slider_number_of_steps=view_variable.NUMBER_OF_STEPS_OVERLAY_SMALL_LOG_FADEOUT_DURATION,
            command=overlaySmallLogSettingsFadeoutDurationSliderCallback,
            variable=view_variable.VAR_OVERLAY_SMALL_LOG_FADEOUT_DURATION,
        )
        self.qsb__overlay_small_log_settings_fadeout_duration.grid(row=row)









        self.qsw_setting_box_bottom = CTkFrame(self.qsw_background__overlay, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        self.qsw_setting_box_bottom.grid(row=1, column=0, sticky="nsew")

        self.qsw_setting_box_bottom.grid_columnconfigure((0,2), weight=1)
        self.qsw_setting_box_bottom.grid_rowconfigure((0,2), weight=1)

        self.qsw_setting_box_bottom_restore_default_button = CTkFrame(self.qsw_setting_box_bottom, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        self.qsw_setting_box_bottom_restore_default_button.grid(row=1, column=1, sticky="nsew")


        def toDefaultOverlaySettingsCallback(_e):
            callFunctionIfCallable(view_variable.CALLBACK_SET_TO_DEFAULT_OVERLAY_SETTINGS)



        (restore_default_settings_button, label_button_label_widget) = createLabelButton(
            parent_widget=self.qsw_setting_box_bottom_restore_default_button,
            label_button_bg_color=self.settings.ctm.SB__BUTTON_COLOR,
            label_button_hovered_bg_color=self.settings.ctm.SB__BUTTON_HOVERED_COLOR,
            label_button_clicked_bg_color=self.settings.ctm.SB__BUTTON_CLICKED_COLOR,
            label_button_ipadx=self.settings.uism.SB__AUTHKEY_WEBPAGE_BUTTON_IPADX,
            label_button_ipady=self.settings.uism.SB__AUTHKEY_WEBPAGE_BUTTON_IPADY,
            variable=view_variable.VAR_TO_DEFAULT_OVERLAY_SETTINGS,
            font_family=self.settings.FONT_FAMILY,
            font_size=self.settings.uism.SB__AUTHKEY_WEBPAGE_BUTTON_LABEL_FONT_SIZE,
            text_color=self.settings.ctm.LABELS_TEXT_COLOR,
            label_button_clicked_command=toDefaultOverlaySettingsCallback,

            label_button_position="center",
        )
        restore_default_settings_button.grid(row=0, column=0, pady=self.settings.uism.QSB__RESTORE_DEFAULT_SETTINGS_BUTTON_PADY)

        self.qsw_background__overlay.grid_remove()














        # VRChat mic mute sync
        self.qsw_background__vrc_mic_mute_sync = CTkFrame(self.qsw_background, corner_radius=0, fg_color=self.settings.ctm.SB__BG_COLOR)
        self.qsw_background__vrc_mic_mute_sync.grid(row=0, column=0, pady=(0,18), sticky="ew")
        self.qsw_background__vrc_mic_mute_sync.grid_columnconfigure(0, weight=1)


        self.qsw_setting_box__vrc_mic_mute_sync = CTkFrame(self.qsw_background__vrc_mic_mute_sync, corner_radius=0, fg_color=BG_HEX_COLOR)
        self.qsw_setting_box__vrc_mic_mute_sync.grid(row=0, column=0, sticky="ew")
        self.qsw_setting_box__vrc_mic_mute_sync.grid_columnconfigure(0, weight=1)









        cqsb = _CreateQuickSettingBox(self.qsw_setting_box__vrc_mic_mute_sync, vrct_gui, settings, view_variable)
        createSettingBoxSlider = cqsb.createSettingBoxSlider
        createSettingBoxSwitch = cqsb.createSettingBoxSwitch


        row=0
        def enableVrcMicMuteSyncSwitchCallback(switch_widget):
            callFunctionIfCallable(view_variable.CALLBACK_SET_ENABLE_VRC_MIC_MUTE_SYNC, switch_widget.get())

        self.qsb__enable_vrc_mic_mute_sync = createSettingBoxSwitch(
            for_var_label_text=view_variable.VAR_LABEL_ENABLE_VRC_MIC_MUTE_SYNC,
            switch_attr_name="qsb__enable_vrc_mic_mute_sync_switch",
            command=lambda: enableVrcMicMuteSyncSwitchCallback(vrct_gui.qsb__enable_vrc_mic_mute_sync_switch),
            variable=view_variable.VAR_ENABLE_VRC_MIC_MUTE_SYNC,
        )
        self.qsb__enable_vrc_mic_mute_sync.grid(row=row)


        self.qsw_background__vrc_mic_mute_sync.grid_remove()







    def show(self, target:str):
        if target == "overlay":
            self.qsw_background__vrc_mic_mute_sync.grid_remove()
            self.qsw_background__overlay.grid()
        elif target == "vrc_mic_mute_sync":
            self.qsw_background__overlay.grid_remove()
            self.qsw_background__vrc_mic_mute_sync.grid()

        self.attributes("-alpha", 0)
        self.deiconify()

        self.qsw_background.update()
        self.geometry("{}x{}".format(self.qsw_background.winfo_width(), self.qsw_background.winfo_height()))



        setGeometryToCenterOfScreen(root_widget=self)
        fadeInAnimation(self, steps=5, interval=0.02)