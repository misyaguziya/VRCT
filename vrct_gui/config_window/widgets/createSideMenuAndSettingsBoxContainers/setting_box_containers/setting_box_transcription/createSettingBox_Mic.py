from time import sleep

from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Mic(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(config_window, settings)
    createSettingBoxDropdownMenu = sbg.createSettingBoxDropdownMenu
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox
    createSettingBoxProgressbarXSlider = sbg.createSettingBoxProgressbarXSlider
    createSettingBoxEntry = sbg.createSettingBoxEntry


    def checkbox_input_mic_threshold_check_callback(e, passive_button_wrapper_widget, active_button_wrapper_widget, is_turned_on):
        callFunctionIfCallable(config_window.CALLBACK_CHECK_MIC_THRESHOLD, is_turned_on)

        if is_turned_on is True:
            passive_button_widget = passive_button_wrapper_widget.children["!ctklabel"]
            passive_button_wrapper_widget.configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR)
            passive_button_widget.configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR)
            passive_button_wrapper_widget.update_idletasks()
            sleep(1)

            passive_button_wrapper_widget.grid_remove()
            active_button_wrapper_widget.grid()

        elif is_turned_on is False:
            # active_button_widget = active_button_wrapper_widget.children["!ctklabel"]
            # active_button_wrapper_widget.configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR)
            # active_button_widget.configure(fg_color=settings.ctm.SB__PROGRESSBAR_X_SLIDER__PASSIVE_BUTTON_DISABLED_COLOR)
            # active_button_wrapper_widget.update_idletasks()
            # sleep(3)

            active_button_wrapper_widget.grid_remove()
            passive_button_wrapper_widget.grid()

    def optionmenu_mic_host_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_HOST, value)

    def optionmenu_input_mic_device_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_DEVICE, value)

    def slider_input_mic_energy_threshold_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_ENERGY_THRESHOLD, value)

    def checkbox_input_mic_dynamic_energy_threshold_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_DYNAMIC_ENERGY_THRESHOLD, checkbox_box_widget.get())


    def entry_input_mic_record_timeout_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_RECORD_TIMEOUT, value)

    def entry_input_mic_phrase_timeout_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_PHRASE_TIMEOUT, value)

    def entry_input_mic_max_phrases_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_MAX_PHRASES, value)

    def entry_input_mic_word_filters_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_WORD_FILTER, value)


    row=0
    # Mic Host と Mic Device は一つの項目として引っ付ける予定
    config_window.sb__mic_host = createSettingBoxDropdownMenu(
        parent_widget=setting_box_wrapper,
        for_var_label_text=view_variable.VAR_LABEL_MIC_HOST,
        for_var_desc_text=view_variable.VAR_DESC_MIC_HOST,
        optionmenu_attr_name="sb__optionmenu_mic_host",
        dropdown_menu_attr_name="sb__dropdown_mic_host",
        dropdown_menu_values=view_variable.LIST_MIC_HOST,
        command=lambda value: optionmenu_mic_host_callback(value),
        variable=view_variable.VAR_MIC_HOST,
    )
    config_window.sb__mic_host.grid(row=row)
    row+=1

    config_window.sb__mic_device = createSettingBoxDropdownMenu(
        parent_widget=setting_box_wrapper,
        for_var_label_text=view_variable.VAR_LABEL_MIC_DEVICE,
        for_var_desc_text=view_variable.VAR_DESC_MIC_DEVICE,
        optionmenu_attr_name="sb__optionmenu_mic_device",
        dropdown_menu_attr_name="sb__dropdown_mic_device",
        dropdown_menu_values=view_variable.LIST_MIC_DEVICE,
        command=lambda value: optionmenu_input_mic_device_callback(value),
        variable=view_variable.VAR_MIC_DEVICE,
    )
    config_window.sb__mic_device.grid(row=row)
    row+=1


    config_window.sb__mic_energy_threshold = createSettingBoxProgressbarXSlider(
        parent_widget=setting_box_wrapper,
        for_var_label_text=view_variable.VAR_LABEL_MIC_ENERGY_THRESHOLD,
        for_var_desc_text=view_variable.VAR_DESC_MIC_ENERGY_THRESHOLD,
        command=slider_input_mic_energy_threshold_callback,
        variable=view_variable.VAR_MIC_ENERGY_THRESHOLD,
        entry_attr_name="sb__progressbar_x_slider__entry_mic_energy_threshold",


        slider_attr_name="progressbar_x_slider__slider_mic_energy_threshold",
        slider_range=view_variable.SLIDER_RANGE_MIC_ENERGY_THRESHOLD,

        progressbar_attr_name="sb__progressbar_x_slider__progressbar_mic_energy_threshold",

        passive_button_attr_name="sb__progressbar_x_slider__passive_button_mic_energy_threshold",
        passive_button_command=lambda e: checkbox_input_mic_threshold_check_callback(
            e,
            config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold,
            config_window.sb__progressbar_x_slider__active_button_mic_energy_threshold,
            is_turned_on=True,
        ),
        active_button_attr_name="sb__progressbar_x_slider__active_button_mic_energy_threshold",
        active_button_command=lambda e: checkbox_input_mic_threshold_check_callback(
            e,
            config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold,
            config_window.sb__progressbar_x_slider__active_button_mic_energy_threshold,
            is_turned_on=False,
        ),
        button_image_filename="mic_icon_white.png"
    )
    config_window.sb__mic_energy_threshold.grid(row=row)
    row+=1

    # Mic Dynamic Energy Thresholdも上に引っ付ける予定
    config_window.sb__mic_dynamic_energy_threshold = createSettingBoxCheckbox(
        parent_widget=setting_box_wrapper,
        for_var_label_text=view_variable.VAR_LABEL_MIC_DYNAMIC_ENERGY_THRESHOLD,
        for_var_desc_text=view_variable.VAR_DESC_MIC_DYNAMIC_ENERGY_THRESHOLD,
        checkbox_attr_name="sb__checkbox_mic_dynamic_energy_threshold",
        command=lambda: checkbox_input_mic_dynamic_energy_threshold_callback(config_window.sb__checkbox_mic_dynamic_energy_threshold),
        variable=view_variable.VAR_MIC_DYNAMIC_ENERGY_THRESHOLD
    )
    config_window.sb__mic_dynamic_energy_threshold.grid(row=row)
    row+=1


    # 以下３つも一つの項目にまとめるかもしれない
    config_window.sb__mic_record_timeout = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        for_var_label_text=view_variable.VAR_LABEL_MIC_RECORD_TIMEOUT,
        for_var_desc_text=view_variable.VAR_DESC_MIC_RECORD_TIMEOUT,
        entry_attr_name="sb__entry_mic_record_timeout",
        entry_width=settings.uism.SB__ENTRY_WIDTH_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_mic_record_timeout_callback(value),
        entry_textvariable=view_variable.VAR_MIC_RECORD_TIMEOUT,
    )
    config_window.sb__mic_record_timeout.grid(row=row)
    row+=1

    config_window.sb__mic_phrase_timeout = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        for_var_label_text=view_variable.VAR_LABEL_MIC_PHRASE_TIMEOUT,
        for_var_desc_text=view_variable.VAR_DESC_MIC_PHRASE_TIMEOUT,
        entry_attr_name="sb__entry_mic_phrase_timeout",
        entry_width=settings.uism.SB__ENTRY_WIDTH_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_mic_phrase_timeout_callback(value),
        entry_textvariable=view_variable.VAR_MIC_PHRASE_TIMEOUT,
    )
    config_window.sb__mic_phrase_timeout.grid(row=row)
    row+=1

    config_window.sb__mic_max_phrases = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        for_var_label_text=view_variable.VAR_LABEL_MIC_MAX_PHRASES,
        for_var_desc_text=view_variable.VAR_DESC_MIC_MAX_PHRASES,
        entry_attr_name="sb__entry_mic_max_phrases",
        entry_width=settings.uism.SB__ENTRY_WIDTH_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_mic_max_phrases_callback(value),
        entry_textvariable=view_variable.VAR_MIC_MAX_PHRASES,
    )
    config_window.sb__mic_max_phrases.grid(row=row)
    row+=1
    # # ＿＿＿＿＿＿＿＿＿＿


    config_window.sb__mic_word_filter = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        for_var_label_text=view_variable.VAR_LABEL_MIC_WORD_FILTER,
        for_var_desc_text=view_variable.VAR_DESC_MIC_WORD_FILTER,
        entry_attr_name="sb__entry_mic_word_filter",
        entry_width=settings.uism.SB__ENTRY_WIDTH_300,
        entry_bind__Any_KeyRelease=lambda value: entry_input_mic_word_filters_callback(value),
        entry_textvariable=view_variable.VAR_MIC_WORD_FILTER,
    )
    config_window.sb__mic_word_filter.grid(row=row)
    row+=1