import os
import tkinter as tk
import customtkinter
from PIL import Image
import utils

class ToplevelWindowConfig(customtkinter.CTkToplevel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        # self.geometry(f"{350}x{270}")
        # self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.after(200, lambda: self.iconbitmap(os.path.join(os.path.dirname(__file__), "img", "app.ico")))
        self.title("Config")

        # tabwiew config
        self.tabview_config = customtkinter.CTkTabview(self)
        self.tabview_config.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.tabview_config.add("UI")
        self.tabview_config.add("Translation")
        self.tabview_config.add("Transcription")
        self.tabview_config.add("Parameter")
        self.tabview_config.tab("UI").grid_columnconfigure(1, weight=1)
        self.tabview_config.tab("Translation").grid_columnconfigure([1,2,3], weight=1)
        self.tabview_config.tab("Transcription").grid_columnconfigure(1, weight=1)
        self.tabview_config.tab("Parameter").grid_columnconfigure(1, weight=1)
        self.tabview_config._segmented_button.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))
        self.tabview_config._segmented_button.grid(sticky="W")

        # tab UI
        ## slider transparency
        self.label_transparency = customtkinter.CTkLabel(
            self.tabview_config.tab("UI"),
            text="Transparency:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_transparency.grid(row=0, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.slider_transparency = customtkinter.CTkSlider(
            self.tabview_config.tab("UI"),
            from_=50,
            to=100,
            command=self.slider_transparency_callback,
            variable=tk.DoubleVar(value=self.parent.TRANSPARENCY),
        )
        self.slider_transparency.grid(row=0, column=1, columnspan=3, padx=5, pady=10, sticky="nsew")

        ## optionmenu theme
        self.label_appearance_theme = customtkinter.CTkLabel(
            self.tabview_config.tab("UI"),
            text="Appearance Theme:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_appearance_theme.grid(row=1, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.optionmenu_appearance_theme = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("UI"),
            values=["Light", "Dark", "System"],
            command=self.optionmenu_theme_callback,
            variable=customtkinter.StringVar(value=self.parent.APPEARANCE_THEME)
        )
        self.optionmenu_appearance_theme.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="nsew")

        ## optionmenu UI scaling
        self.label_ui_scaling = customtkinter.CTkLabel(
            self.tabview_config.tab("UI"),
            text="UI Scaling:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_ui_scaling.grid(row=2, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.optionmenu_ui_scaling = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("UI"),
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.optionmenu_ui_scaling_callback,
            variable=customtkinter.StringVar(value=self.parent.UI_SCALING)
        )
        self.optionmenu_ui_scaling.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="nsew")

        ## optionmenu font family
        self.label_font_family = customtkinter.CTkLabel(
            self.tabview_config.tab("UI"),
            text="Font Family:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_font_family.grid(row=3, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        font_families = list(tk.font.families())
        self.optionmenu_font_family = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("UI"),
            values=font_families,
            command=self.optionmenu_font_family_callback,
            variable=customtkinter.StringVar(value=self.parent.FONT_FAMILY)
        )
        self.optionmenu_font_family.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky="nsew")

        # tab Translation
        ## optionmenu translation translator
        self.label_translation_translator = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="Select Translator:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_translator.grid(row=0, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.optionmenu_translation_translator = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            values=list(self.parent.translator.translator_status.keys()),
            command=self.optionmenu_translation_translator_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            variable=customtkinter.StringVar(value=self.parent.CHOICE_TRANSLATOR)
        )
        self.optionmenu_translation_translator.grid(row=0, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")

        ## optionmenu translation input language
        self.label_translation_input_language = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="Input Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_input_language.grid(row=1, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")

        ## select translation input source language
        self.optionmenu_translation_input_source_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_input_source_language_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            values=self.parent.translator.languages[self.parent.CHOICE_TRANSLATOR],
            variable=customtkinter.StringVar(value=self.parent.INPUT_SOURCE_LANG),
        )
        self.optionmenu_translation_input_source_language.grid(row=1, column=1, columnspan=1, padx=5, pady=5, sticky="nsew")

        ## label translation input arrow
        self.label_translation_input_arrow = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="-->",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_input_arrow.grid(row=1, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

        ## select translation input target language
        self.optionmenu_translation_input_target_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_input_target_language_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            values=self.parent.translator.languages[self.parent.CHOICE_TRANSLATOR],
            variable=customtkinter.StringVar(value=self.parent.INPUT_TARGET_LANG),
        )
        self.optionmenu_translation_input_target_language.grid(row=1, column=3, columnspan=1, padx=5, pady=5, sticky="nsew")

        ## optionmenu translation output language
        self.label_translation_output_language = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="Output Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY, overstrike=True)
        )
        self.label_translation_output_language.grid(row=2, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")

        ## select translation output source language
        self.optionmenu_translation_output_source_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            # command=self.optionmenu_translation_output_source_language_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            values=self.parent.translator.languages[self.parent.CHOICE_TRANSLATOR],
            variable=customtkinter.StringVar(value=self.parent.OUTPUT_SOURCE_LANG),
            state="disabled",
        )
        self.optionmenu_translation_output_source_language.grid(row=2, column=1, columnspan=1, padx=5, pady=5, sticky="nsew")

        ## label translation output arrow
        self.label_translation_output_arrow = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="-->",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_output_arrow.grid(row=2, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

        ## select translation output target language
        self.optionmenu_translation_output_target_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            # command=self.optionmenu_translation_output_target_language_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            values=self.parent.translator.languages[self.parent.CHOICE_TRANSLATOR],
            variable=customtkinter.StringVar(value=self.parent.OUTPUT_TARGET_LANG),
            state="disabled",
        )
        self.optionmenu_translation_output_target_language.grid(row=2, column=3, columnspan=1, padx=5, pady=5, sticky="nsew")

        # tab Transcription
        ## optionmenu input mic device
        self.label_input_mic_device = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Device:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_device.grid(row=0, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.optionmenu_input_mic_device = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=[device["name"] for device in self.parent.vr.search_input_device()],
            command=self.optionmenu_input_mic_device_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            variable=customtkinter.StringVar(value=self.parent.CHOICE_MIC_DEVICE)
        )
        self.optionmenu_input_mic_device.grid(row=0, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")

        ## optionmenu input mic voice language
        self.label_input_mic_voice_language = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Voice Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_voice_language.grid(row=1, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.optionmenu_input_mic_voice_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=list(self.parent.vr.languages),
            command=self.optionmenu_input_mic_voice_language_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            variable=customtkinter.StringVar(value=self.parent.INPUT_MIC_VOICE_LANGUAGE)
        )
        self.optionmenu_input_mic_voice_language.grid(row=1, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")

        ## checkbox input mic in dynamic
        self.label_input_mic_is_dynamic = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic IsDynamic:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_is_dynamic.grid(row=2, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.checkbox_input_mic_is_dynamic = customtkinter.CTkCheckBox(
            self.tabview_config.tab("Transcription"),
            text="",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_input_mic_is_dynamic_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_input_mic_is_dynamic.grid(row=2, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")
        if  self.parent.INPUT_MIC_IS_DYNAMIC is True:
            self.checkbox_input_mic_is_dynamic.select()
        else:
            self.checkbox_input_mic_is_dynamic.deselect()

        ## slider input mic threshold
        self.label_input_mic_threshold = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Threshold:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_threshold.grid(row=3, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.slider_input_mic_threshold = customtkinter.CTkSlider(
            self.tabview_config.tab("Transcription"),
            from_=0,
            to=300,
            command=self.slider_input_mic_threshold_callback,
            variable=tk.DoubleVar(value=self.parent.INPUT_MIC_THRESHOLD),
        )
        self.slider_input_mic_threshold.grid(row=3, column=1, columnspan=3 ,padx=5, pady=10, sticky="nsew")

        ## optionmenu input speaker device
        self.label_input_speaker_device = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Device:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_device.grid(row=4, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.optionmenu_input_speaker_device = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=self.parent.vr.search_output_device(),
            command=self.optionmenu_input_speaker_device_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            variable=customtkinter.StringVar(value=self.parent.CHOICE_SPEAKER_DEVICE),
        )
        self.optionmenu_input_speaker_device.grid(row=4, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")

        ## optionmenu input speaker voice language
        self.label_input_speaker_voice_language = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Voice Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_voice_language.grid(row=5, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.optionmenu_input_speaker_voice_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=list(self.parent.vr.languages),
            command=self.optionmenu_input_speaker_voice_language_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            variable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_VOICE_LANGUAGE),
        )
        self.optionmenu_input_speaker_voice_language.grid(row=5, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")

        ## entry input speaker sampling rate
        self.label_input_speaker_sampling_rate = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker SamplingRate:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_sampling_rate.grid(row=6, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.entry_input_speaker_sampling_rate = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_SAMPLING_RATE),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_sampling_rate.grid(row=6, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")
        self.entry_input_speaker_sampling_rate.bind("<Any-KeyRelease>", self.entry_input_speaker_sampling_rate_callback)

        ## entry input speaker interval
        self.label_input_speaker_interval = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Interval:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_interval.grid(row=7, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.entry_input_speaker_interval = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_INTERVAL),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_interval.grid(row=7, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")
        self.entry_input_speaker_interval.bind("<Any-KeyRelease>", self.entry_input_speaker_interval_callback)

        ## entry input speaker buffer size
        self.label_input_speaker_buffer_size = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker BufferSize:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_buffer_size.grid(row=8, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.entry_input_speaker_buffer_size = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_BUFFER_SIZE),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_buffer_size.grid(row=8, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")
        self.entry_input_speaker_buffer_size.bind("<Any-KeyRelease>", self.entry_input_speaker_buffer_size_callback)

        # tab Parameter
        ## entry ip address
        self.label_ip_address = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="OSC IP address:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_ip_address.grid(row=0, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.entry_ip_address = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=customtkinter.StringVar(value=self.parent.OSC_IP_ADDRESS),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_ip_address.grid(row=0, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_ip_address = customtkinter.CTkButton(
            self.tabview_config.tab("Parameter"),
            text="",
            width=1,
            command=self.update_ip_address,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "save-icon.png")))
        )
        self.button_ip_address.grid(row=0, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

        ## entry port
        self.label_port = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="OSC Port:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_port.grid(row=1, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.entry_port = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=customtkinter.StringVar(value=self.parent.OSC_PORT),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_port.grid(row=1, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_port = customtkinter.CTkButton(
            self.tabview_config.tab("Parameter"),
            text="",
            width=1,
            command=self.update_port,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "save-icon.png")))
        )
        self.button_port.grid(row=1, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

        ## entry authkey
        self.label_authkey = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="DeepL Auth Key:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_authkey.grid(row=2, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.entry_authkey = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=customtkinter.StringVar(value=self.parent.AUTH_KEYS["DeepL(auth)"]),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_authkey.grid(row=2, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_authkey = customtkinter.CTkButton(
            self.tabview_config.tab("Parameter"),
            text="",
            width=1,
            command=self.update_authkey,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "save-icon.png")))
        )
        self.button_authkey.grid(row=2, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

        ## entry message format
        self.label_message_format = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="Message Format:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_message_format.grid(row=3, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.entry_message_format = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=customtkinter.StringVar(value=self.parent.MESSAGE_FORMAT),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_message_format.grid(row=3, column=1, columnspan=1, padx=1, pady=5, sticky="nsew")
        self.button_message_format = customtkinter.CTkButton(
            self.tabview_config.tab("Parameter"),
            text="",
            width=1,
            command=self.update_message_format,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "save-icon.png")))
        )
        self.button_message_format.grid(row=3, column=2, columnspan=1, padx=5, pady=5, sticky="nsew")

    def slider_transparency_callback(self, value):
        self.parent.wm_attributes("-alpha", value/100)
        self.parent.TRANSPARENCY = value
        utils.save_json(self.parent.PATH_CONFIG, "TRANSPARENCY", self.parent.TRANSPARENCY)

    def optionmenu_theme_callback(self, choice):
        customtkinter.set_appearance_mode(choice)
        self.parent.APPEARANCE_THEME = choice
        utils.save_json(self.parent.PATH_CONFIG, "APPEARANCE_THEME", self.parent.APPEARANCE_THEME)

    def optionmenu_ui_scaling_callback(self, choice):
        new_scaling_float = int(choice.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)
        self.parent.UI_SCALING = choice
        utils.save_json(self.parent.PATH_CONFIG, "UI_SCALING", self.parent.UI_SCALING)

    def optionmenu_font_family_callback(self, choice):
        # tab menu
        self.tabview_config._segmented_button.configure(font=customtkinter.CTkFont(family=choice))

        # tab UI
        self.label_transparency.configure(font=customtkinter.CTkFont(family=choice))
        self.label_appearance_theme.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_appearance_theme.configure(font=customtkinter.CTkFont(family=choice))
        self.label_ui_scaling.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_ui_scaling.configure(font=customtkinter.CTkFont(family=choice))
        self.label_font_family.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_font_family.configure(font=customtkinter.CTkFont(family=choice))

        # tab Translation
        self.label_translation_translator.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_translator.configure(font=customtkinter.CTkFont(family=choice))
        self.label_translation_input_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_input_source_language.configure(font=customtkinter.CTkFont(family=choice))
        self.label_translation_input_arrow.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_input_target_language.configure(font=customtkinter.CTkFont(family=choice))
        self.label_translation_output_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_output_source_language.configure(font=customtkinter.CTkFont(family=choice))
        self.label_translation_output_arrow.configure(font=customtkinter.CTkFont(family=choice))
        self.label_translation_output_arrow.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_output_target_language.configure(font=customtkinter.CTkFont(family=choice))

        # tab Transcription
        self.label_input_mic_device.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_mic_device.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_mic_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_is_dynamic.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_threshold.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_speaker_device.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_speaker_device.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_speaker_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_speaker_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_speaker_is_dynamic.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_speaker_threshold.configure(font=customtkinter.CTkFont(family=choice))

        # tab Parameter
        self.label_ip_address.configure(font=customtkinter.CTkFont(family=choice))
        self.entry_ip_address.configure(font=customtkinter.CTkFont(family=choice))
        self.label_port.configure(font=customtkinter.CTkFont(family=choice))
        self.entry_port.configure(font=customtkinter.CTkFont(family=choice))
        self.label_authkey.configure(font=customtkinter.CTkFont(family=choice))
        self.entry_authkey.configure(font=customtkinter.CTkFont(family=choice))
        self.label_message_format.configure(font=customtkinter.CTkFont(family=choice))
        self.entry_message_format.configure(font=customtkinter.CTkFont(family=choice))

        # main window
        self.parent.checkbox_translation.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.checkbox_transcription.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.checkbox_foreground.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.textbox_message_log.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.entry_message_box.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.tabview_logs._segmented_button.configure(font=customtkinter.CTkFont(family=choice))

        # window information
        try:
            self.parent.information_window.textbox_information.configure(font=customtkinter.CTkFont(family=choice))
        except:
            pass

        self.parent.FONT_FAMILY = choice
        utils.save_json(self.parent.PATH_CONFIG, "FONT_FAMILY", self.parent.FONT_FAMILY)

    def optionmenu_translation_translator_callback(self, choice):
        if self.parent.translator.authentication(choice, self.parent.AUTH_KEYS[choice]) is False:
            self.parent.textbox_message_system_log.configure(state='normal')
            self.parent.textbox_message_system_log.insert("end", f"[ERROR]Auth Keyを設定してないか間違っています\n")
            self.parent.textbox_message_system_log.configure(state='disabled')
            self.parent.textbox_message_system_log.see("end")
        else:
            self.optionmenu_translation_input_source_language.configure(
                values=self.parent.translator.languages[choice],
                variable=customtkinter.StringVar(value=self.parent.translator.languages[choice][0]))
            self.optionmenu_translation_input_target_language.configure(
                values=self.parent.translator.languages[choice],
                variable=customtkinter.StringVar(value=self.parent.translator.languages[choice][1]))

            self.parent.CHOICE_TRANSLATOR = choice
            self.parent.INPUT_SOURCE_LANG = self.parent.translator.languages[choice][0]
            self.parent.INPUT_TARGET_LANG = self.parent.translator.languages[choice][1]
            utils.save_json(self.parent.PATH_CONFIG, "CHOICE_TRANSLATOR", self.parent.CHOICE_TRANSLATOR)
            utils.save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)
            utils.save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)

    def optionmenu_translation_input_source_language_callback(self, choice):
        self.parent.INPUT_SOURCE_LANG = choice
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)

    def optionmenu_translation_input_target_language_callback(self, choice):
        self.parent.INPUT_TARGET_LANG = choice
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)

    def optionmenu_input_mic_device_callback(self, choice):
        self.parent.CHOICE_MIC_DEVICE = choice
        utils.save_json(self.parent.PATH_CONFIG, "CHOICE_MIC_DEVICE", self.parent.CHOICE_MIC_DEVICE)

    def optionmenu_input_mic_voice_language_callback(self, choice):
        self.parent.INPUT_MIC_VOICE_LANGUAGE = choice
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_MIC_VOICE_LANGUAGE", self.parent.INPUT_MIC_VOICE_LANGUAGE)

    def checkbox_input_mic_is_dynamic_callback(self):
        value = self.checkbox_input_mic_is_dynamic.get()
        self.parent.INPUT_MIC_IS_DYNAMIC = value
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_MIC_IS_DYNAMIC", self.parent.INPUT_MIC_IS_DYNAMIC)
        self.parent.vr.set_mic(self.parent.CHOICE_MIC_DEVICE, threshold=self.parent.INPUT_MIC_THRESHOLD, is_dynamic=self.parent.INPUT_MIC_IS_DYNAMIC)

    def slider_input_mic_threshold_callback(self, value):
        self.parent.INPUT_MIC_THRESHOLD = value
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_MIC_THRESHOLD", self.parent.INPUT_MIC_THRESHOLD)
        self.parent.vr.set_mic(self.parent.CHOICE_MIC_DEVICE, threshold=self.parent.INPUT_MIC_THRESHOLD, is_dynamic=self.parent.INPUT_MIC_IS_DYNAMIC)

    def optionmenu_input_speaker_device_callback(self, choice):
        self.parent.CHOICE_SPEAKER_DEVICE = choice
        utils.save_json(self.parent.PATH_CONFIG, "CHOICE_SPEAKER_DEVICE", self.parent.CHOICE_SPEAKER_DEVICE)

    def optionmenu_input_speaker_voice_language_callback(self, choice):
        self.parent.INPUT_SPEAKER_VOICE_LANGUAGE = choice
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_VOICE_LANGUAGE", self.parent.INPUT_SPEAKER_VOICE_LANGUAGE)

    def entry_input_speaker_sampling_rate_callback(self, event):
        self.parent.INPUT_SPEAKER_SAMPLING_RATE = int(self.entry_input_speaker_sampling_rate.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_SAMPLING_RATE", self.parent.INPUT_SPEAKER_SAMPLING_RATE)

    def entry_input_speaker_interval_callback(self, event):
        self.parent.INPUT_SPEAKER_INTERVAL = int(self.entry_input_speaker_interval.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_INTERVAL", self.parent.INPUT_SPEAKER_INTERVAL)

    def entry_input_speaker_buffer_size_callback(self, event):
        self.parent.INPUT_SPEAKER_BUFFER_SIZE = int(self.entry_input_speaker_buffer_size.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_BUFFER_SIZE", self.parent.INPUT_SPEAKER_BUFFER_SIZE)

    def update_ip_address(self):
        value = self.entry_ip_address.get()
        if len(value) > 0:
            self.parent.OSC_IP_ADDRESS = value
            utils.save_json(self.parent.PATH_CONFIG, "OSC_IP_ADDRESS", self.parent.OSC_IP_ADDRESS)

    def update_port(self):
        value = self.entry_port.get()
        if len(value) > 0:
            self.parent.OSC_PORT = value
            utils.save_json(self.parent.PATH_CONFIG, "OSC_PORT", self.parent.OSC_PORT)

    def update_authkey(self):
        value = self.entry_authkey.get()
        if len(value) > 0:
            if self.parent.translator.authentication(self.parent.CHOICE_TRANSLATOR, self.parent.AUTH_KEYS[self.parent.CHOICE_TRANSLATOR]) is True:
                self.parent.AUTH_KEYS["DeepL(auth)"] = value
                utils.save_json(self.parent.PATH_CONFIG, "AUTH_KEYS", self.parent.AUTH_KEYS)
            else:
                self.parent.textbox_message_system_log.configure(state='normal')
                self.parent.textbox_message_system_log.insert("end", f"[ERROR]Auth Keyを設定してないか間違っています\n")
                self.parent.textbox_message_system_log.configure(state='disabled')
                self.parent.textbox_message_system_log.see("end")

    def update_message_format(self):
        value = self.entry_message_format.get()
        if len(value) > 0:
            self.parent.MESSAGE_FORMAT = value
            utils.save_json(self.parent.PATH_CONFIG, "MESSAGE_FORMAT", self.parent.MESSAGE_FORMAT)