import os
import tkinter as tk
import customtkinter
import utils
import audio_utils
import languages

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
        row = 0
        padx = 5
        pady = 1
        self.label_transparency = customtkinter.CTkLabel(
            self.tabview_config.tab("UI"),
            text="Transparency:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_transparency.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.slider_transparency = customtkinter.CTkSlider(
            self.tabview_config.tab("UI"),
            from_=50,
            to=100,
            command=self.slider_transparency_callback,
            variable=tk.DoubleVar(value=self.parent.TRANSPARENCY),
        )
        self.slider_transparency.grid(row=row, column=1, columnspan=1, padx=padx, pady=10, sticky="nsew")

        ## optionmenu theme
        row += 1
        self.label_appearance_theme = customtkinter.CTkLabel(
            self.tabview_config.tab("UI"),
            text="Appearance Theme:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_appearance_theme.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_appearance_theme = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("UI"),
            values=["Light", "Dark", "System"],
            command=self.optionmenu_theme_callback,
            variable=customtkinter.StringVar(value=self.parent.APPEARANCE_THEME),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_appearance_theme.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_appearance_theme._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu UI scaling
        row += 1
        self.label_ui_scaling = customtkinter.CTkLabel(
            self.tabview_config.tab("UI"),
            text="UI Scaling:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_ui_scaling.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_ui_scaling = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("UI"),
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.optionmenu_ui_scaling_callback,
            variable=customtkinter.StringVar(value=self.parent.UI_SCALING),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_ui_scaling.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_ui_scaling._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu font family
        row += 1
        self.label_font_family = customtkinter.CTkLabel(
            self.tabview_config.tab("UI"),
            text="Font Family:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_font_family.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        font_families = list(tk.font.families())
        self.optionmenu_font_family = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("UI"),
            values=font_families,
            command=self.optionmenu_font_family_callback,
            variable=customtkinter.StringVar(value=self.parent.FONT_FAMILY),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_font_family.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_font_family._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        # tab Translation
        ## optionmenu translation translator
        row = 0
        padx = 5
        pady = 1
        self.label_translation_translator = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="Select Translator:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.label_translation_translator.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_translation_translator = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            values=list(self.parent.translator.translator_status.keys()),
            command=self.optionmenu_translation_translator_callback,
            variable=customtkinter.StringVar(value=self.parent.CHOICE_TRANSLATOR),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_translator.grid(row=row, column=1, columnspan=3 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_translator._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu translation input language
        row +=1
        self.label_translation_input_language = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="Send Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_input_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        ## select translation input source language
        self.optionmenu_translation_input_source_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_input_source_language_callback,
            values=list(languages.translation_lang[self.parent.CHOICE_TRANSLATOR].keys()),
            variable=customtkinter.StringVar(value=self.parent.INPUT_SOURCE_LANG),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_input_source_language.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_input_source_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## label translation input arrow
        self.label_translation_input_arrow = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="-->",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_input_arrow.grid(row=row, column=2, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## select translation input target language
        self.optionmenu_translation_input_target_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_input_target_language_callback,
            values=list(languages.translation_lang[self.parent.CHOICE_TRANSLATOR].keys()),
            variable=customtkinter.StringVar(value=self.parent.INPUT_TARGET_LANG),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_input_target_language.grid(row=row, column=3, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_input_target_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu translation output language
        row +=1
        self.label_translation_output_language = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="Receive Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_output_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        ## select translation output source language
        self.optionmenu_translation_output_source_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_output_source_language_callback,
            values=list(languages.translation_lang[self.parent.CHOICE_TRANSLATOR].keys()),
            variable=customtkinter.StringVar(value=self.parent.OUTPUT_SOURCE_LANG),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_output_source_language.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_output_source_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## label translation output arrow
        self.label_translation_output_arrow = customtkinter.CTkLabel(
            self.tabview_config.tab("Translation"),
            text="-->",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_output_arrow.grid(row=row, column=2, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## select translation output target language
        self.optionmenu_translation_output_target_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_output_target_language_callback,
            values=list(languages.translation_lang[self.parent.CHOICE_TRANSLATOR].keys()),
            variable=customtkinter.StringVar(value=self.parent.OUTPUT_TARGET_LANG),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_output_target_language.grid(row=row, column=3, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_output_target_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        # tab Transcription
        ## optionmenu input mic device
        row = 0
        padx = 5
        pady = 1
        self.label_input_mic_device = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Device:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_device.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_mic_device = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=[device["name"] for device in audio_utils.get_input_device_list()],
            command=self.optionmenu_input_mic_device_callback,
            variable=customtkinter.StringVar(value=self.parent.CHOICE_MIC_DEVICE),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_mic_device.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_input_mic_device._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu input mic voice language
        row +=1
        self.label_input_mic_voice_language = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Voice Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_voice_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_mic_voice_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=list(languages.transcription_lang.keys()),
            command=self.optionmenu_input_mic_voice_language_callback,
            variable=customtkinter.StringVar(value=self.parent.INPUT_MIC_VOICE_LANGUAGE),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_mic_voice_language.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_input_mic_voice_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## entry input mic energy threshold
        row +=1
        self.label_input_mic_energy_threshold = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Energy Threshold:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_energy_threshold = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_MIC_ENERGY_THRESHOLD),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_energy_threshold.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_energy_threshold.bind("<Any-KeyRelease>", self.entry_input_mic_energy_threshold_callback)

        ## checkbox input mic dynamic energy threshold
        row +=1
        self.label_input_mic_dynamic_energy_threshold = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Dynamic Energy Threshold:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_dynamic_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.checkbox_input_mic_dynamic_energy_threshold = customtkinter.CTkCheckBox(
            self.tabview_config.tab("Transcription"),
            text="",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_input_mic_dynamic_energy_threshold_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_input_mic_dynamic_energy_threshold.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        if  self.parent.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD is True:
            self.checkbox_input_mic_dynamic_energy_threshold.select()
        else:
            self.checkbox_input_mic_dynamic_energy_threshold.deselect()

        ## entry input mic record timeout
        row +=1
        self.label_input_mic_record_timeout = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Record Timeout:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_record_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_record_timeout = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_MIC_RECORD_TIMEOUT),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_record_timeout.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_record_timeout.bind("<Any-KeyRelease>", self.entry_input_mic_record_timeout_callback)

        ## entry input mic phrase timeout
        row +=1
        self.label_input_mic_phrase_timeout = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Phrase Timeout:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_phrase_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_phrase_timeout = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_MIC_PHRASE_TIMEOUT),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_phrase_timeout.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_phrase_timeout.bind("<Any-KeyRelease>", self.entry_input_mic_phrase_timeout_callback)

        ## entry input mic max phrases
        row +=1
        self.label_input_mic_max_phrases = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Max Phrases:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_max_phrases.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_max_phrases = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_MIC_MAX_PHRASES),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_max_phrases.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_max_phrases.bind("<Any-KeyRelease>", self.entry_input_mic_max_phrases_callback)

        ## optionmenu input speaker device
        row +=1
        self.label_input_speaker_device = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Device:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_device.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_speaker_device = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=[device["name"] for device in audio_utils.get_output_device_list()],
            command=self.optionmenu_input_speaker_device_callback,
            variable=customtkinter.StringVar(value=self.parent.CHOICE_SPEAKER_DEVICE),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_speaker_device.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_input_speaker_device._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu input speaker voice language
        row +=1
        self.label_input_speaker_voice_language = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Voice Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_voice_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_speaker_voice_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=list(languages.transcription_lang.keys()),
            command=self.optionmenu_input_speaker_voice_language_callback,
            variable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_VOICE_LANGUAGE),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_speaker_voice_language.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_input_speaker_voice_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY))

        ## entry input speaker energy threshold
        row +=1
        self.label_input_speaker_energy_threshold = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Energy Threshold:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_energy_threshold = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_ENERGY_THRESHOLD),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_energy_threshold.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_energy_threshold.bind("<Any-KeyRelease>", self.entry_input_speaker_energy_threshold_callback)

        ## checkbox input speaker dynamic energy threshold
        row +=1
        self.label_input_speaker_dynamic_energy_threshold = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Dynamic Energy Threshold:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_dynamic_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.checkbox_input_speaker_dynamic_energy_threshold = customtkinter.CTkCheckBox(
            self.tabview_config.tab("Transcription"),
            text="",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_input_speaker_dynamic_energy_threshold_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_input_speaker_dynamic_energy_threshold.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        if  self.parent.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD is True:
            self.checkbox_input_speaker_dynamic_energy_threshold.select()
        else:
            self.checkbox_input_speaker_dynamic_energy_threshold.deselect()

        ## entry input speaker record timeout
        row +=1
        self.label_input_speaker_record_timeout = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Record Timeout:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_record_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_record_timeout = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_RECORD_TIMEOUT),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_record_timeout.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_record_timeout.bind("<Any-KeyRelease>", self.entry_input_speaker_record_timeout_callback)

        ## entry input speaker phrase timeout
        row +=1
        self.label_input_speaker_phrase_timeout = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Phrase Timeout:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_phrase_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_phrase_timeout = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_PHRASE_TIMEOUT),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_phrase_timeout.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_phrase_timeout.bind("<Any-KeyRelease>", self.entry_input_speaker_phrase_timeout_callback)

        ## entry input speaker max phrases
        row +=1
        self.label_input_speaker_max_phrases = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Max Phrases:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_max_phrases.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_max_phrases = customtkinter.CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_MAX_PHRASES),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_max_phrases.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_max_phrases.bind("<Any-KeyRelease>", self.entry_input_speaker_max_phrases_callback)

        # tab Parameter
        ## entry ip address
        row = 0
        padx = 5
        pady = 1
        self.label_ip_address = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="OSC IP address:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_ip_address.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_ip_address = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=customtkinter.StringVar(value=self.parent.OSC_IP_ADDRESS),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_ip_address.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_ip_address.bind("<Any-KeyRelease>", self.entry_ip_address_callback)

        ## entry port
        row +=1
        self.label_port = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="OSC Port:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_port.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_port = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=customtkinter.StringVar(value=self.parent.OSC_PORT),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_port.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_port.bind("<Any-KeyRelease>", self.entry_port_callback)

        ## entry authkey
        row +=1
        self.label_authkey = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="DeepL Auth Key:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_authkey.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_authkey = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=customtkinter.StringVar(value=self.parent.AUTH_KEYS["DeepL(auth)"]),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_authkey.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_authkey.bind("<Any-KeyRelease>", self.entry_authkey_callback)

        ## entry message format
        row +=1
        self.label_message_format = customtkinter.CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="Message Format:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_message_format.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_message_format = customtkinter.CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=customtkinter.StringVar(value=self.parent.MESSAGE_FORMAT),
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_message_format.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_message_format.bind("<Any-KeyRelease>", self.entry_message_format_callback)

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
        self.optionmenu_appearance_theme._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_ui_scaling.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_ui_scaling.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_ui_scaling._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_font_family.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_font_family.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_font_family._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))

        # tab Translation
        self.label_translation_translator.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_translator.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_translator._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_translation_input_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_input_source_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_input_source_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_translation_input_arrow.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_input_target_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_input_target_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_translation_output_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_output_source_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_output_source_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_translation_output_arrow.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_output_target_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_translation_output_target_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))

        # tab Transcription
        self.label_input_mic_device.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_mic_device.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_mic_device._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_mic_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_mic_voice_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_energy_threshold.configure(font=customtkinter.CTkFont(family=choice))
        self.entry_input_mic_energy_threshold.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_dynamic_energy_threshold.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_record_timeout.configure(font=customtkinter.CTkFont(family=choice))
        self.entry_input_mic_record_timeout.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_speaker_device.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_speaker_device.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_speaker_device._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_speaker_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_speaker_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_speaker_voice_language._dropdown_menu.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_speaker_energy_threshold.configure(font=customtkinter.CTkFont(family=choice))
        self.entry_input_speaker_energy_threshold.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_speaker_dynamic_energy_threshold.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_speaker_record_timeout.configure(font=customtkinter.CTkFont(family=choice))
        self.entry_input_speaker_record_timeout.configure(font=customtkinter.CTkFont(family=choice))

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
        self.parent.checkbox_transcription_send.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.checkbox_transcription_receive.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.checkbox_foreground.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.textbox_message_log.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.textbox_message_send_log.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.textbox_message_receive_log.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.textbox_message_system_log.configure(font=customtkinter.CTkFont(family=choice))
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
            utils.print_textbox(self.parent.textbox_message_log,  "Auth Key or language setting is incorrect", "ERROR")
            utils.print_textbox(self.parent.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
        else:
            self.optionmenu_translation_input_source_language.configure(
                values=list(languages.translation_lang[choice].keys()),
                variable=customtkinter.StringVar(value=list(languages.translation_lang[choice].keys())[0]))
            self.optionmenu_translation_input_target_language.configure(
                values=list(languages.translation_lang[choice].keys()),
                variable=customtkinter.StringVar(value=list(languages.translation_lang[choice].keys())[1]))
            self.optionmenu_translation_output_source_language.configure(
                values=list(languages.translation_lang[choice].keys()),
                variable=customtkinter.StringVar(value=list(languages.translation_lang[choice].keys())[1]))
            self.optionmenu_translation_output_target_language.configure(
                values=list(languages.translation_lang[choice].keys()),
                variable=customtkinter.StringVar(value=list(languages.translation_lang[choice].keys())[0]))

            self.parent.CHOICE_TRANSLATOR = choice
            self.parent.INPUT_SOURCE_LANG = list(languages.translation_lang[choice].keys())[0]
            self.parent.INPUT_TARGET_LANG = list(languages.translation_lang[choice].keys())[1]
            self.parent.OUTPUT_SOURCE_LANG = list(languages.translation_lang[choice].keys())[1]
            self.parent.OUTPUT_TARGET_LANG = list(languages.translation_lang[choice].keys())[0]
            utils.save_json(self.parent.PATH_CONFIG, "CHOICE_TRANSLATOR", self.parent.CHOICE_TRANSLATOR)
            utils.save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)
            utils.save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)
            utils.save_json(self.parent.PATH_CONFIG, "OUTPUT_SOURCE_LANG", self.parent.OUTPUT_SOURCE_LANG)
            utils.save_json(self.parent.PATH_CONFIG, "OUTPUT_TARGET_LANG", self.parent.OUTPUT_TARGET_LANG)

    def optionmenu_translation_input_source_language_callback(self, choice):
        self.parent.INPUT_SOURCE_LANG = choice
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)

    def optionmenu_translation_input_target_language_callback(self, choice):
        self.parent.INPUT_TARGET_LANG = choice
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)

    def optionmenu_translation_output_source_language_callback(self, choice):
        self.parent.OUTPUT_SOURCE_LANG = choice
        utils.save_json(self.parent.PATH_CONFIG, "OUTPUT_SOURCE_LANG", self.parent.OUTPUT_SOURCE_LANG)

    def optionmenu_translation_output_target_language_callback(self, choice):
        self.parent.OUTPUT_TARGET_LANG = choice
        utils.save_json(self.parent.PATH_CONFIG, "OUTPUT_TARGET_LANG", self.parent.OUTPUT_TARGET_LANG)

    def optionmenu_input_mic_device_callback(self, choice):
        self.parent.CHOICE_MIC_DEVICE = choice
        utils.save_json(self.parent.PATH_CONFIG, "CHOICE_MIC_DEVICE", self.parent.CHOICE_MIC_DEVICE)

    def optionmenu_input_mic_voice_language_callback(self, choice):
        self.parent.INPUT_MIC_VOICE_LANGUAGE = choice
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_MIC_VOICE_LANGUAGE", self.parent.INPUT_MIC_VOICE_LANGUAGE)

    def entry_input_mic_energy_threshold_callback(self, event):
        self.parent.INPUT_MIC_ENERGY_THRESHOLD = int(self.entry_input_mic_energy_threshold.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_MIC_ENERGY_THRESHOLD", self.parent.INPUT_MIC_ENERGY_THRESHOLD)

    def checkbox_input_mic_dynamic_energy_threshold_callback(self):
        value = self.checkbox_input_mic_dynamic_energy_threshold.get()
        self.parent.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = value
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD", self.parent.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD)

    def entry_input_mic_record_timeout_callback(self, event):
        self.parent.INPUT_MIC_RECORD_TIMEOUT = int(self.entry_input_mic_record_timeout.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_MIC_RECORD_TIMEOUT", self.parent.INPUT_MIC_RECORD_TIMEOUT)

    def entry_input_mic_phrase_timeout_callback(self, event):
        self.parent.INPUT_MIC_PHRASE_TIMEOUT = int(self.entry_input_mic_phrase_timeout.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_MIC_PHRASE_TIMEOUT", self.parent.INPUT_MIC_PHRASE_TIMEOUT)

    def entry_input_mic_max_phrases_callback(self, event):
        self.parent.INPUT_MIC_MAX_PHRASES = int(self.entry_input_mic_max_phrases.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_MIC_MAX_PHRASES", self.parent.INPUT_MIC_MAX_PHRASES)

    def optionmenu_input_speaker_device_callback(self, choice):
        self.parent.CHOICE_SPEAKER_DEVICE = choice
        utils.save_json(self.parent.PATH_CONFIG, "CHOICE_SPEAKER_DEVICE", self.parent.CHOICE_SPEAKER_DEVICE)

    def optionmenu_input_speaker_voice_language_callback(self, choice):
        self.parent.INPUT_SPEAKER_VOICE_LANGUAGE = choice
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_VOICE_LANGUAGE", self.parent.INPUT_SPEAKER_VOICE_LANGUAGE)

    def entry_input_speaker_energy_threshold_callback(self, event):
        self.parent.INPUT_SPEAKER_ENERGY_THRESHOLD = int(self.entry_input_speaker_energy_threshold.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_ENERGY_THRESHOLD", self.parent.INPUT_SPEAKER_ENERGY_THRESHOLD)

    def checkbox_input_speaker_dynamic_energy_threshold_callback(self):
        value = self.checkbox_input_speaker_dynamic_energy_threshold.get()
        self.parent.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = value
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD", self.parent.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD)

    def entry_input_speaker_record_timeout_callback(self, event):
        self.parent.INPUT_SPEAKER_RECORD_TIMEOUT = int(self.entry_input_speaker_record_timeout.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_RECORD_TIMEOUT", self.parent.INPUT_SPEAKER_RECORD_TIMEOUT)

    def entry_input_speaker_phrase_timeout_callback(self, event):
        self.parent.INPUT_SPEAKER_PHRASE_TIMEOUT = int(self.entry_input_speaker_phrase_timeout.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_PHRASE_TIMEOUT", self.parent.INPUT_SPEAKER_PHRASE_TIMEOUT)

    def entry_input_speaker_max_phrases_callback(self, event):
        self.parent.INPUT_SPEAKER_MAX_PHRASES = int(self.entry_input_speaker_max_phrases.get())
        utils.save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_MAX_PHRASES", self.parent.INPUT_SPEAKER_MAX_PHRASES)

    def entry_ip_address_callback(self, event):
        self.parent.OSC_IP_ADDRESS = self.entry_ip_address.get()
        utils.save_json(self.parent.PATH_CONFIG, "OSC_IP_ADDRESS", self.parent.OSC_IP_ADDRESS)

    def entry_port_callback(self, event):
        self.parent.OSC_PORT = self.entry_port.get()
        utils.save_json(self.parent.PATH_CONFIG, "OSC_PORT", self.parent.OSC_PORT)

    def entry_authkey_callback(self, event):
        value = self.entry_authkey.get()
        if len(value) > 0:
            if self.parent.translator.authentication("DeepL(auth)", value) is True:
                self.parent.AUTH_KEYS["DeepL(auth)"] = value
                utils.save_json(self.parent.PATH_CONFIG, "AUTH_KEYS", self.parent.AUTH_KEYS)
                utils.print_textbox(self.parent.textbox_message_log, "Auth key update completed", "INFO")
                utils.print_textbox(self.parent.textbox_message_system_log, "Auth key update completed", "INFO")
            else:
                pass

    def entry_message_format_callback(self, event):
        value = self.entry_message_format.get()
        if len(value) > 0:
            self.parent.MESSAGE_FORMAT = value
            utils.save_json(self.parent.PATH_CONFIG, "MESSAGE_FORMAT", self.parent.MESSAGE_FORMAT)