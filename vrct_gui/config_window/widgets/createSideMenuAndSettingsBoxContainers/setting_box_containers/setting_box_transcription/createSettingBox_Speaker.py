from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Speaker(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxDropdownMenu = sbg.createSettingBoxDropdownMenu
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox
    createSettingBoxProgressbarXSlider = sbg.createSettingBoxProgressbarXSlider
    createSettingBoxEntry = sbg.createSettingBoxEntry


    def checkbox_input_speaker_threshold_check_callback(is_turned_on):
        callFunctionIfCallable(view_variable.CALLBACK_CHECK_SPEAKER_THRESHOLD, is_turned_on)


    def optionmenu_input_speaker_device_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_SPEAKER_DEVICE, value)

    def slider_input_speaker_energy_threshold_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_SPEAKER_ENERGY_THRESHOLD, value)

    def checkbox_input_speaker_dynamic_energy_threshold_callback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_SPEAKER_DYNAMIC_ENERGY_THRESHOLD, checkbox_box_widget.get())


    def entry_input_speaker_record_timeout_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_SPEAKER_RECORD_TIMEOUT, value)

    def entry_input_speaker_phrase_timeout_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_SPEAKER_PHRASE_TIMEOUT, value)

    def entry_input_speaker_max_phrases_callback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_SPEAKER_MAX_PHRASES, value)



    row=0
    config_window.sb__speaker_device = createSettingBoxDropdownMenu(
        for_var_label_text=view_variable.VAR_LABEL_SPEAKER_DEVICE,
        for_var_desc_text=view_variable.VAR_DESC_SPEAKER_DEVICE,
        optionmenu_attr_name="sb__optionmenu_speaker_device",
        dropdown_menu_values=view_variable.LIST_SPEAKER_DEVICE,
        dropdown_menu_width=settings.uism.RESPONSIVE_UI_SIZE_INT_300,
        command=lambda value: optionmenu_input_speaker_device_callback(value),
        variable=view_variable.VAR_SPEAKER_DEVICE,
    )
    config_window.sb__speaker_device.grid(row=row)
    row+=1


    config_window.sb__speaker_energy_threshold = createSettingBoxProgressbarXSlider(
        for_var_label_text=view_variable.VAR_LABEL_SPEAKER_ENERGY_THRESHOLD,
        for_var_desc_text=view_variable.VAR_DESC_SPEAKER_ENERGY_THRESHOLD,
        command=slider_input_speaker_energy_threshold_callback,

        entry_variable=view_variable.VAR_SPEAKER_ENERGY_THRESHOLD__ENTRY,
        entry_attr_name="sb__progressbar_x_slider__entry_speaker_energy_threshold",
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_SPEAKER_ENERGY_THRESHOLD,


        slider_attr_name="progressbar_x_slider__slider_speaker_energy_threshold",
        slider_range=view_variable.SLIDER_RANGE_SPEAKER_ENERGY_THRESHOLD,
        slider_variable=view_variable.VAR_SPEAKER_ENERGY_THRESHOLD__SLIDER,

        progressbar_attr_name="sb__progressbar_x_slider__progressbar_speaker_energy_threshold",

        passive_button_attr_name="sb__progressbar_x_slider__passive_button_speaker_energy_threshold",
        passive_button_command=lambda _e: checkbox_input_speaker_threshold_check_callback(True),
        active_button_attr_name="sb__progressbar_x_slider__active_button_speaker_energy_threshold",
        active_button_command=lambda _e: checkbox_input_speaker_threshold_check_callback(False),
        button_image_file=settings.image_file.HEADPHONES_ICON
    )
    config_window.sb__speaker_energy_threshold.grid(row=row)
    row+=1

    # Speaker Dynamic Energy Thresholdも上に引っ付ける予定
    config_window.sb__speaker_dynamic_energy_threshold = createSettingBoxCheckbox(
        for_var_label_text=view_variable.VAR_LABEL_SPEAKER_DYNAMIC_ENERGY_THRESHOLD,
        for_var_desc_text=view_variable.VAR_DESC_SPEAKER_DYNAMIC_ENERGY_THRESHOLD,
        checkbox_attr_name="sb__checkbox_speaker_dynamic_energy_threshold",
        command=lambda: checkbox_input_speaker_dynamic_energy_threshold_callback(config_window.sb__checkbox_speaker_dynamic_energy_threshold),
        variable=view_variable.VAR_MIC_DYNAMIC_ENERGY_THRESHOLD,
    )
    config_window.sb__speaker_dynamic_energy_threshold.grid(row=row)
    row+=1


    # 以下３つも一つの項目にまとめるかもしれない
    config_window.sb__speaker_record_timeout = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_SPEAKER_RECORD_TIMEOUT,
        for_var_desc_text=view_variable.VAR_DESC_SPEAKER_RECORD_TIMEOUT,
        entry_attr_name="sb__entry_speaker_record_timeout",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_speaker_record_timeout_callback(value),
        entry_textvariable=view_variable.VAR_SPEAKER_RECORD_TIMEOUT,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_SPEAKER_RECORD_TIMEOUT,
    )
    config_window.sb__speaker_record_timeout.grid(row=row)
    row+=1

    config_window.sb__speaker_phrase_timeout = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_SPEAKER_PHRASE_TIMEOUT,
        for_var_desc_text=view_variable.VAR_DESC_SPEAKER_PHRASE_TIMEOUT,
        entry_attr_name="sb__entry_speaker_phrase_timeout",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_speaker_phrase_timeout_callback(value),
        entry_textvariable=view_variable.VAR_SPEAKER_PHRASE_TIMEOUT,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_SPEAKER_PHRASE_TIMEOUT,
    )
    config_window.sb__speaker_phrase_timeout.grid(row=row)
    row+=1

    config_window.sb__speaker_max_phrases = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_SPEAKER_MAX_PHRASES,
        for_var_desc_text=view_variable.VAR_DESC_SPEAKER_MAX_PHRASES,
        entry_attr_name="sb__entry_speaker_max_phrases",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_speaker_max_phrases_callback(value),
        entry_textvariable=view_variable.VAR_SPEAKER_MAX_PHRASES,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_SPEAKER_MAX_PHRASES,
    )
    config_window.sb__speaker_max_phrases.grid(row=row, pady=0)
    row+=1
    # ＿＿＿＿＿＿＿＿＿＿