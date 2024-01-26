from utils import callFunctionIfCallable

from .._SettingBoxGenerator import _SettingBoxGenerator

def createSettingBox_Mic(setting_box_wrapper, config_window, settings, view_variable):
    sbg = _SettingBoxGenerator(setting_box_wrapper, config_window, settings, view_variable)
    createSettingBoxDropdownMenu = sbg.createSettingBoxDropdownMenu
    createSettingBoxSwitch = sbg.createSettingBoxSwitch
    createSettingBoxProgressbarXSlider = sbg.createSettingBoxProgressbarXSlider
    createSettingBoxEntry = sbg.createSettingBoxEntry
    createSettingBoxArrowSwitch = sbg.createSettingBoxArrowSwitch
    createSettingBoxAddAndDeleteAbleList = sbg.createSettingBoxAddAndDeleteAbleList


    def checkboxInputMicThresholdCheckCallback(is_turned_on):
        callFunctionIfCallable(view_variable.CALLBACK_CHECK_MIC_THRESHOLD, is_turned_on)


    def optionmenuMicHostCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_HOST, value)

    def optionmenuInputMicDeviceCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_DEVICE, value)

    def sliderInputMicEnergyThresholdCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_ENERGY_THRESHOLD, value)

    def checkboxInputMicDynamicEnergyThresholdCallback(checkbox_box_widget):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_DYNAMIC_ENERGY_THRESHOLD, checkbox_box_widget.get())


    def entryInputMicRecordTimeoutCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_RECORD_TIMEOUT, value)

    def entryInputMicPhraseTimeoutCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_PHRASE_TIMEOUT, value)

    def entryInputMicMaxPhrasesCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_MAX_PHRASES, value)

    def arrowSwitchMicWordFilterListOpenCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_ARROW_SWITCH_MIC_WORD_FILTER_LIST_OPEN)
    def arrowSwitchMicWordFilterListCloseCallback(value):
        callFunctionIfCallable(view_variable.CALLBACK_ARROW_SWITCH_MIC_WORD_FILTER_LIST_CLOSE)

# 直接 SettingBoxGenerator.pyでcallFunctionIfCallableから呼んでいます。（word filter 専用関数になっているのでそのままですが、良くはない）
    # def entry_input_mic_word_filters_callback(value):
    #     callFunctionIfCallable(view_variable.CALLBACK_SET_MIC_WORD_FILTER, value)


    row=0
    # Mic Host と Mic Device は一つの項目として引っ付ける予定
    config_window.sb__mic_host = createSettingBoxDropdownMenu(
        for_var_label_text=view_variable.VAR_LABEL_MIC_HOST,
        for_var_desc_text=view_variable.VAR_DESC_MIC_HOST,
        optionmenu_attr_name="sb__optionmenu_mic_host",
        dropdown_menu_values=view_variable.LIST_MIC_HOST,
        command=lambda value: optionmenuMicHostCallback(value),
        variable=view_variable.VAR_MIC_HOST,
    )
    config_window.sb__mic_host.grid(row=row)
    row+=1

    config_window.sb__mic_device = createSettingBoxDropdownMenu(
        for_var_label_text=view_variable.VAR_LABEL_MIC_DEVICE,
        for_var_desc_text=view_variable.VAR_DESC_MIC_DEVICE,
        optionmenu_attr_name="sb__optionmenu_mic_device",
        dropdown_menu_values=view_variable.LIST_MIC_DEVICE,
        command=lambda value: optionmenuInputMicDeviceCallback(value),
        variable=view_variable.VAR_MIC_DEVICE,
    )
    config_window.sb__mic_device.grid(row=row)
    row+=1

    config_window.sb__mic_dynamic_energy_threshold = createSettingBoxSwitch(
        for_var_label_text=view_variable.VAR_LABEL_MIC_DYNAMIC_ENERGY_THRESHOLD,
        for_var_desc_text=view_variable.VAR_DESC_MIC_DYNAMIC_ENERGY_THRESHOLD,
        switch_attr_name="sb__checkbox_mic_dynamic_energy_threshold",
        command=lambda: checkboxInputMicDynamicEnergyThresholdCallback(config_window.sb__checkbox_mic_dynamic_energy_threshold),
        variable=view_variable.VAR_MIC_DYNAMIC_ENERGY_THRESHOLD
    )
    config_window.sb__mic_dynamic_energy_threshold.grid(row=row, pady=0)
    row+=1

    config_window.sb__mic_energy_threshold = createSettingBoxProgressbarXSlider(
        command=sliderInputMicEnergyThresholdCallback,
        progressbar_x_slider_attr_name="sb__mic_energy_threshold",

        entry_attr_name="sb__progressbar_x_slider__entry_mic_energy_threshold",
        entry_variable=view_variable.VAR_MIC_ENERGY_THRESHOLD__ENTRY,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_MIC_ENERGY_THRESHOLD,


        slider_attr_name="progressbar_x_slider__slider_mic_energy_threshold",
        slider_range=view_variable.SLIDER_RANGE_MIC_ENERGY_THRESHOLD,
        slider_variable=view_variable.VAR_MIC_ENERGY_THRESHOLD__SLIDER,

        progressbar_attr_name="sb__progressbar_x_slider__progressbar_mic_energy_threshold",

        passive_button_attr_name="sb__progressbar_x_slider__passive_button_mic_energy_threshold",
        passive_button_command=lambda _e: checkboxInputMicThresholdCheckCallback(True),
        active_button_attr_name="sb__progressbar_x_slider__active_button_mic_energy_threshold",
        active_button_command=lambda _e: checkboxInputMicThresholdCheckCallback(False),
        button_image_file=settings.image_file.MIC_ICON,
        disabled_button_attr_name="sb__progressbar_x_slider__disabled_button_mic_energy_threshold",
        disabled_button_image_file=settings.image_file.MIC_ICON_DISABLED,
    )
    config_window.sb__mic_energy_threshold.grid(row=row)
    row+=1


    # 以下３つも一つの項目にまとめるかもしれない
    config_window.sb__mic_record_timeout = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_MIC_RECORD_TIMEOUT,
        for_var_desc_text=view_variable.VAR_DESC_MIC_RECORD_TIMEOUT,
        entry_attr_name="sb__entry_mic_record_timeout",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_100,
        entry_bind__Any_KeyRelease=lambda value: entryInputMicRecordTimeoutCallback(value),
        entry_textvariable=view_variable.VAR_MIC_RECORD_TIMEOUT,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_MIC_RECORD_TIMEOUT,
    )
    config_window.sb__mic_record_timeout.grid(row=row)
    row+=1

    config_window.sb__mic_phrase_timeout = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_MIC_PHRASE_TIMEOUT,
        for_var_desc_text=view_variable.VAR_DESC_MIC_PHRASE_TIMEOUT,
        entry_attr_name="sb__entry_mic_phrase_timeout",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_100,
        entry_bind__Any_KeyRelease=lambda value: entryInputMicPhraseTimeoutCallback(value),
        entry_textvariable=view_variable.VAR_MIC_PHRASE_TIMEOUT,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_MIC_PHRASE_TIMEOUT,
    )
    config_window.sb__mic_phrase_timeout.grid(row=row)
    row+=1

    config_window.sb__mic_max_phrases = createSettingBoxEntry(
        for_var_label_text=view_variable.VAR_LABEL_MIC_MAX_PHRASES,
        for_var_desc_text=view_variable.VAR_DESC_MIC_MAX_PHRASES,
        entry_attr_name="sb__entry_mic_max_phrases",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_100,
        entry_bind__Any_KeyRelease=lambda value: entryInputMicMaxPhrasesCallback(value),
        entry_textvariable=view_variable.VAR_MIC_MAX_PHRASES,
        entry_bind__FocusOut=view_variable.CALLBACK_FOCUS_OUT_MIC_MAX_PHRASES,
    )
    config_window.sb__mic_max_phrases.grid(row=row)
    row+=1
    # # ＿＿＿＿＿＿＿＿＿＿


    config_window.sb__mic_word_filter = createSettingBoxArrowSwitch(
        for_var_label_text=view_variable.VAR_LABEL_MIC_WORD_FILTER,
        for_var_desc_text=view_variable.VAR_DESC_MIC_WORD_FILTER,
        arrow_switch_attr_name="sb__arrow_switch_mic_word_filter",
        open_command=lambda value: arrowSwitchMicWordFilterListOpenCallback(value),
        close_command=lambda value: arrowSwitchMicWordFilterListCloseCallback(value),
        var_switch_desc=view_variable.VAR_SWITCH_DESC_MIC_WORD_FILTER,
    )
    config_window.sb__mic_word_filter.grid(row=row, pady=0)
    row+=1

    config_window.sb__mic_word_filter_list = createSettingBoxAddAndDeleteAbleList(
        add_and_delete_able_list_attr_name="sb__add_and_delete_able_list_mic_word_filter_list",
        entry_attr_name="sb__entry_mic_word_filter_list",
        entry_width=settings.uism.RESPONSIVE_UI_SIZE_INT_300,
        mic_word_filter_list=view_variable.MIC_WORD_FILTER_LIST,
    )
    config_window.sb__mic_word_filter_list.grid(row=row, pady=0)
    # Default, close the list.
    config_window.sb__mic_word_filter_list.grid_remove()
    row+=1