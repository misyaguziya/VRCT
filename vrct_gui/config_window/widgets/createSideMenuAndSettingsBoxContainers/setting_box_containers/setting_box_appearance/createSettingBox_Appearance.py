from time import sleep

from customtkinter import StringVar, IntVar


from ..SettingBoxGenerator import SettingBoxGenerator

from config import config

def createSettingBox_Appearance(setting_box_wrapper, config_window, settings):


    sbg = SettingBoxGenerator(config_window, settings)

    createSettingBoxDropdownMenu = sbg.createSettingBoxDropdownMenu
    createSettingBoxSwitch = sbg.createSettingBoxSwitch
    createSettingBoxCheckbox = sbg.createSettingBoxCheckbox
    createSettingBoxSlider = sbg.createSettingBoxSlider
    createSettingBoxProgressbarXSlider = sbg.createSettingBoxProgressbarXSlider
    createSettingBoxEntry = sbg.createSettingBoxEntry



    # 関数名は変えるかもしれない。
    # テーマ変更、フォント変更時、 Widget再生成か再起動かは検討中


    def slider_transparency_callback(value):
        # self.parent.wm_attributes("-alpha", int(value/100))
        config.TRANSPARENCY = int(value)

    def optionmenu_appearance_theme_callback(value):
        config.APPEARANCE_THEME = value



    row=0
    config_window.sb__transparency = createSettingBoxSlider(
        parent_widget=setting_box_wrapper,
        label_text="Transparency",
        desc_text="It will change window's transparency. 50% to 100%. (Default: 100%)",
        slider_attr_name="sb__transparency_slider",
        slider_range=(50, 100),
        command=lambda value: slider_transparency_callback(value),
        variable=IntVar(value=config.TRANSPARENCY),
    )
    config_window.sb__transparency.grid(row=row)
    row+=1



    config_window.sb__appearance_theme = createSettingBoxDropdownMenu(
        parent_widget=setting_box_wrapper,
        label_text="Theme",
        desc_text="You can choose the color theme from \"Light\" and \"Dark\". If you select \"System\", It will adjust based on your Windows theme. (Default: System)",
        optionmenu_attr_name="sb__appearance_theme_optionmenu",
        dropdown_menu_attr_name="sb__appearance_theme_optionmenu_dropdown",
        dropdown_menu_values=["Light", "Dark", "System"],
        command=lambda value: optionmenu_appearance_theme_callback(value),
        variable=StringVar(value=config.APPEARANCE_THEME)
    )
    config_window.sb__appearance_theme.grid(row=row)
    row+=1


    # config_window.sb__dropdown_menu_2 = createSettingBoxDropdownMenu(
    #     parent_widget=setting_box_wrapper,
    #     label_text="Option Menu",
    #     desc_text="Select your preferences from the options menu.\nYou can choose your preferred language.",
    #     optionmenu_attr_name="optionmenu_attr_name_2",
    #     dropdown_menu_attr_name="dropdown_menu_attr_name_1",
    #     dropdown_menu_values=["tt", "Japanese", "English"],
    #     command=lambda value: dropdownMenuFun(value, config_window.optionmenu_attr_name_2, config_window.dropdown_menu_attr_name_1),
    #     variable=StringVar(value=config.INPUT_SOURCE_LANG)
    # )
    # config_window.sb__dropdown_menu_2.grid(row=row)
    # row+=1

    # config_window.sb__switch_1 = createSettingBoxSwitch(
    #     parent_widget=setting_box_wrapper,
    #     label_text="Switch",
    #     desc_text="Turning this switch on will bring happiness.\nAs for turning it off... I leave that to your imagination",
    #     switch_attr_name="switch_attr_name_1",
    #     command=lambda: switchFun(config_window.switch_attr_name_1),
    #     is_checked=True,
    # )
    # config_window.sb__switch_1.grid(row=row)
    # row+=1

    # config_window.sb__checkbox_1 = createSettingBoxCheckbox(
    #     parent_widget=setting_box_wrapper,
    #     label_text="Checkbox",
    #     desc_text="Checkbox ticked, a checkmark.",
    #     checkbox_attr_name="checkbox_attr_name_1",
    #     command=lambda: checkboxFun(config_window.checkbox_attr_name_1),
    #     is_checked=False,
    # )
    # config_window.sb__checkbox_1.grid(row=row)
    # row+=1

    # config_window.sb__slider_1 = createSettingBoxSlider(
    #     parent_widget=setting_box_wrapper,
    #     label_text="Slider",
    #     desc_text="Adjust using the slider; the balance is up to you.",
    #     slider_attr_name="slider_attr_name_1",
    #     slider_range=(0, config_window.MAX_SPEAKER_ENERGY_THRESHOLD),
    #     slider_number_of_steps=config_window.MAX_SPEAKER_ENERGY_THRESHOLD,
    #     command=lambda value: sliderFun(value, config_window.slider_attr_name_1),
    #     variable=IntVar(value=config_window.INPUT_SPEAKER_ENERGY_THRESHOLD),
    # )
    # config_window.sb__slider_1.grid(row=row)
    # row+=1


    # config_window.sb__progressbar_x_slider_1 = createSettingBoxProgressbarXSlider(
    #     parent_widget=setting_box_wrapper,
    #     label_text="Progressbar and Slider for check the threshold",
    #     desc_text="just the slider to modify the threshold for activating voice input.\nPress the microphone button to start input, and you can adjust it while monitoring the actual volume.",
    #     command=set_input_threshold, # ?
    #     variable=IntVar(value=config.INPUT_MIC_ENERGY_THRESHOLD),
    #     entry_attr_name="progressbar_x_slider__entry_attr_name_1",


    #     slider_attr_name="progressbar_x_slider__slider_attr_name_1",
    #     slider_range=(0, config_window.MAX_SPEAKER_ENERGY_THRESHOLD),
    #     slider_number_of_steps=config_window.MAX_SPEAKER_ENERGY_THRESHOLD,

    #     progressbar_attr_name="progressbar_x_slider__progressbar_attr_name_1",

    #     passive_button_attr_name="progressbar_x_slider__passive_button_attr_name_1",
    #     passive_button_command=lambda e: checkbox_input_speaker_threshold_check_callback(
    #         e,
    #         config_window.progressbar_x_slider__passive_button_attr_name_1,
    #         config_window.progressbar_x_slider__active_button_attr_name_1,
    #         is_turned_on=True,
    #     ),
    #     active_button_attr_name="progressbar_x_slider__active_button_attr_name_1",
    #     active_button_command=lambda e: checkbox_input_speaker_threshold_check_callback(
    #         e,
    #         config_window.progressbar_x_slider__passive_button_attr_name_1,
    #         config_window.progressbar_x_slider__active_button_attr_name_1,
    #         is_turned_on=False,
    #     ),
    #     button_image_filename="mic_icon_white.png"
    # )
    # config_window.sb__progressbar_x_slider_1.grid(row=row)
    # row+=1

    # config_window.sb__progressbar_x_slider_2 = createSettingBoxProgressbarXSlider(
    #     parent_widget=setting_box_wrapper,
    #     label_text="Progressbar and Slider for check the threshold2",
    #     desc_text="just the slider to modify the threshold for activating voice input.\nPress the microphone button to start input, and you can adjust it while monitoring the actual volume.",
    #     command=set_input_threshold, # ?
    #     variable=IntVar(value=config.INPUT_SPEAKER_ENERGY_THRESHOLD),

    #     entry_attr_name="progressbar_x_slider__entry_attr_name_2",


    #     slider_attr_name="progressbar_x_slider__slider_attr_name_2",
    #     slider_range=(0, config_window.MAX_SPEAKER_ENERGY_THRESHOLD),
    #     slider_number_of_steps=config_window.MAX_SPEAKER_ENERGY_THRESHOLD,
    #     progressbar_attr_name="progressbar_x_slider__progressbar_attr_name_2",

    #     passive_button_attr_name="progressbar_x_slider__passive_button_attr_name_2",
    #     passive_button_command=lambda e: checkbox_input_speaker_threshold_check_callback(
    #         e,
    #         config_window.progressbar_x_slider__passive_button_attr_name_2,
    #         config_window.progressbar_x_slider__active_button_attr_name_2,
    #         is_turned_on=True,
    #     ),
    #     active_button_attr_name="progressbar_x_slider__active_button_attr_name_2",
    #     active_button_command=lambda e: checkbox_input_speaker_threshold_check_callback(
    #         e,
    #         config_window.progressbar_x_slider__passive_button_attr_name_2,
    #         config_window.progressbar_x_slider__active_button_attr_name_2,
    #         is_turned_on=False,
    #     ),
    #     button_image_filename="headphones_icon_white.png"
    # )
    # config_window.sb__progressbar_x_slider_2.grid(row=row)
    # row+=1

    # config_window.sb__entry_1 = createSettingBoxEntry(
    #     parent_widget=setting_box_wrapper,
    #     label_text="Entry",
    #     desc_text="Please input a numerical value.",
    #     entry_attr_name="entry_attr_name_1",
    #     entry_width=settings.uism.SB__ENTRY_WIDTH_100,
    #     entry_bind__Any_KeyRelease=lambda value: entryFun(value, config_window.entry_attr_name_1),
    #     entry_textvariable=IntVar(value=config_window.INPUT_MIC_PHRASE_TIMEOUT),
    # )
    # config_window.sb__entry_1.grid(row=row, pady=0)
    # row+=1