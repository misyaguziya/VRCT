from time import sleep

from customtkinter import StringVar, IntVar


from ..SettingBoxGenerator import SettingBoxGenerator

from config import config

def createSettingBox_Mic(setting_box_wrapper, config_window, settings):


    sbg = SettingBoxGenerator(config_window, settings)

    createSettingBoxDropdownMenu = sbg.createSettingBoxDropdownMenu
    createSettingBoxSwitch = sbg.createSettingBoxSwitch
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox
    createSettingBoxSlider = sbg.createSettingBoxSlider
    createSettingBoxProgressbarXSlider = sbg.createSettingBoxProgressbarXSlider
    createSettingBoxEntry = sbg.createSettingBoxEntry


    def checkbox_input_speaker_threshold_check_callback(e, passive_button_wrapper_widget, active_button_wrapper_widget, is_turned_on):
        print("is_turned_on", is_turned_on)

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
        config.CHOICE_MIC_HOST = value

    def optionmenu_input_mic_device_callback(value):
        config.CHOICE_MIC_DEVICE = value

    def slider_input_mic_energy_threshold_callback(value):
        config.INPUT_MIC_ENERGY_THRESHOLD = int(value)

    def checkbox_input_mic_dynamic_energy_threshold_callback(checkbox_box_widget):
        print(checkbox_box_widget.get())
        config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = checkbox_box_widget.get()


    def entry_input_mic_record_timeout_callback(value):
        print(int(value))
        config.INPUT_MIC_RECORD_TIMEOUT = int(value)

    def entry_input_mic_phrase_timeout_callback(value):
        print(int(value))
        config.INPUT_MIC_PHRASE_TIMEOUT = int(value)

    def entry_input_mic_max_phrases_callback(value):
        print(int(value))
        config.INPUT_MIC_MAX_PHRASES = int(value)

    def entry_input_mic_word_filters_callback(value):
        word_filter = str(value)
        word_filter = [w.strip() for w in word_filter.split(",") if len(w.strip()) > 0]
        word_filter = ",".join(word_filter)
        print(word_filter)
        if len(word_filter) > 0:
            config.INPUT_MIC_WORD_FILTER = word_filter.split(",")
        else:
            config.INPUT_MIC_WORD_FILTER = []
        # model.resetKeywordProcessor()
        # model.addKeywords()


    row=0
    # Mic Host と Mic Device は一つの項目として引っ付ける予定
    config_window.sb__mic_host = createSettingBoxDropdownMenu(
        parent_widget=setting_box_wrapper,
        label_text="Mic Host",
        desc_text="Select the mic host. (Default: ?)",
        optionmenu_attr_name="sb__optionmenu_mic_host",
        dropdown_menu_attr_name="sb__dropdown_mic_host",
        # dropdown_menu_values=model.getListInputHost(),
        dropdown_menu_values=["host1", "host2", "host3"],
        command=lambda value: optionmenu_mic_host_callback(value),
        variable=StringVar(value=config.CHOICE_MIC_HOST)
    )
    config_window.sb__mic_host.grid(row=row)
    row+=1

    config_window.sb__mic_device = createSettingBoxDropdownMenu(
        parent_widget=setting_box_wrapper,
        label_text="Mic Device",
        desc_text="Select the mic devise. (Default: ?)",
        optionmenu_attr_name="sb__optionmenu_mic_device",
        dropdown_menu_attr_name="sb__dropdown_mic_device",
        # dropdown_menu_values=model.getListInputDevice(),
        dropdown_menu_values=["device1", "device2", "device3"],
        command=lambda value: optionmenu_input_mic_device_callback(value),
        variable=StringVar(value=config.CHOICE_MIC_DEVICE)
    )
    config_window.sb__mic_device.grid(row=row)
    row+=1


    config_window.sb__mic_energy_threshold = createSettingBoxProgressbarXSlider(
        parent_widget=setting_box_wrapper,
        label_text="Mic Energy Threshold",
        desc_text="Slider to modify the threshold for activating voice input.\nPress the microphone button to start input and speak something, so you can adjust it while monitoring the actual volume. 0 to 2000 (Default: 300)",
        command=slider_input_mic_energy_threshold_callback,
        variable=IntVar(value=config.INPUT_MIC_ENERGY_THRESHOLD),
        entry_attr_name="sb__progressbar_x_slider__entry_mic_energy_threshold",


        slider_attr_name="progressbar_x_slider__slider_mic_energy_threshold",
        slider_range=(0, config.MAX_MIC_ENERGY_THRESHOLD),
        slider_number_of_steps=config.MAX_MIC_ENERGY_THRESHOLD,

        progressbar_attr_name="sb__progressbar_x_slider__progressbar_mic_energy_threshold",

        passive_button_attr_name="sb__progressbar_x_slider__passive_button_mic_energy_threshold",
        passive_button_command=lambda e: checkbox_input_speaker_threshold_check_callback(
            e,
            config_window.sb__progressbar_x_slider__passive_button_mic_energy_threshold,
            config_window.sb__progressbar_x_slider__active_button_mic_energy_threshold,
            is_turned_on=True,
        ),
        active_button_attr_name="sb__progressbar_x_slider__active_button_mic_energy_threshold",
        active_button_command=lambda e: checkbox_input_speaker_threshold_check_callback(
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
        label_text="Mic Dynamic Energy Threshold",
        desc_text="When this feature is selected, it will automatically adjust in a way that works well, based on the set Mic Energy Threshold.",
        checkbox_attr_name="sb__checkbox_mic_dynamic_energy_threshold",
        command=lambda: checkbox_input_mic_dynamic_energy_threshold_callback(config_window.sb__checkbox_mic_dynamic_energy_threshold),
        is_checked=False
    )
    config_window.sb__mic_dynamic_energy_threshold.grid(row=row)
    row+=1


    # 以下３つも一つの項目にまとめるかもしれない
    config_window.sb__mic_record_timeout = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        label_text="Mic Record Timeout",
        desc_text="(Default: 3)",
        entry_attr_name="sb__entry_mic_record_timeout",
        entry_width=settings.uism.SB__ENTRY_WIDTH_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_mic_record_timeout_callback(value),
        entry_textvariable=IntVar(value=config.INPUT_MIC_RECORD_TIMEOUT),
    )
    config_window.sb__mic_record_timeout.grid(row=row)
    row+=1

    config_window.sb__mic_phrase_timeout = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        label_text="Mic Phrase Timeout",
        desc_text="It will stop recording and send the recordings when the set second(s) is reached. (Default: 3)",
        entry_attr_name="sb__entry_mic_phrase_timeout",
        entry_width=settings.uism.SB__ENTRY_WIDTH_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_mic_phrase_timeout_callback(value),
        entry_textvariable=IntVar(value=config.INPUT_MIC_PHRASE_TIMEOUT),
    )
    config_window.sb__mic_phrase_timeout.grid(row=row)
    row+=1

    config_window.sb__mic_max_phrases = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        label_text="Mic Max Phrases",
        desc_text="It will stop recording and send the recordings when the set count of phrase(s) is reached. (Default: 10)",
        entry_attr_name="sb__entry_mic_max_phrases",
        entry_width=settings.uism.SB__ENTRY_WIDTH_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_mic_max_phrases_callback(value),
        entry_textvariable=IntVar(value=config.INPUT_MIC_MAX_PHRASES),
    )
    config_window.sb__mic_max_phrases.grid(row=row)
    row+=1
    # ＿＿＿＿＿＿＿＿＿＿



    if len(config.INPUT_MIC_WORD_FILTER) > 0:
        entry_textvariable=StringVar(value=",".join(config.INPUT_MIC_WORD_FILTER))
    else:
        entry_textvariable=None
    config_window.sb__mic_word_filter = createSettingBoxEntry(
        parent_widget=setting_box_wrapper,
        label_text="Mic Word Filter",
        desc_text="It will not send the sentence if the word(s) included in the set list of words.\nHow to set: e.g. AAA,BBB,CCC",
        entry_attr_name="sb__entry_mic_word_filter",
        entry_width=settings.uism.SB__ENTRY_WIDTH_100,
        entry_bind__Any_KeyRelease=lambda value: entry_input_mic_word_filters_callback(value),
        entry_textvariable=entry_textvariable,
    )
    config_window.sb__mic_word_filter.grid(row=row)
    row+=1