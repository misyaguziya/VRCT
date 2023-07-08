from time import sleep
from os import path as os_path
from threading import Thread
from tkinter import DoubleVar, IntVar 
from tkinter import font as tk_font
import customtkinter
from customtkinter import CTkToplevel, CTkTabview, CTkFont, CTkLabel, CTkSlider, CTkOptionMenu, StringVar, CTkEntry, CTkCheckBox, CTkProgressBar
from flashtext import KeywordProcessor

from utils import save_json, print_textbox
from audio_utils import get_input_device_list, get_output_device_list
from audio_recorder import SelectedMicRecorder, SelectedSpeakerRecorder
from languages import translation_lang, transcription_lang

class ToplevelWindowConfig(CTkToplevel):


    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        # self.geometry(f"{350}x{270}")
        # self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.after(200, lambda: self.iconbitmap(os_path.join(os_path.dirname(__file__), "img", "app.ico")))
        self.title("Config")

        # init parameter
        self.MAX_MIC_ENERGY_THRESHOLD = 2000
        self.MAX_SPEAKER_ENERGY_THRESHOLD = 4000
        self.FLAG_LOOP_MIC = True
        self.FLAG_LOOP_SPEAKER = True

        # tabwiew config
        self.tabview_config = CTkTabview(self)
        self.tabview_config.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.tabview_config.add("UI")
        self.tabview_config.add("Translation")
        self.tabview_config.add("Transcription")
        self.tabview_config.add("Parameter")
        self.tabview_config.tab("UI").grid_columnconfigure(1, weight=1)
        self.tabview_config.tab("Translation").grid_columnconfigure([1,2,3], weight=1)
        self.tabview_config.tab("Transcription").grid_columnconfigure(1, weight=1)
        self.tabview_config.tab("Parameter").grid_columnconfigure(1, weight=1)
        self.tabview_config._segmented_button.configure(font=CTkFont(family=self.parent.FONT_FAMILY))
        self.tabview_config._segmented_button.grid(sticky="W")

        # tab UI
        ## slider transparency
        row = 0
        padx = 5
        pady = 1
        self.label_transparency = CTkLabel(
            self.tabview_config.tab("UI"),
            text="Transparency:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_transparency.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.slider_transparency = CTkSlider(
            self.tabview_config.tab("UI"),
            from_=50,
            to=100,
            command=self.slider_transparency_callback,
            variable=DoubleVar(value=self.parent.TRANSPARENCY),
        )
        self.slider_transparency.grid(row=row, column=1, columnspan=1, padx=padx, pady=10, sticky="nsew")

        ## optionmenu theme
        row += 1
        self.label_appearance_theme = CTkLabel(
            self.tabview_config.tab("UI"),
            text="Appearance Theme:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_appearance_theme.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_appearance_theme = CTkOptionMenu(
            self.tabview_config.tab("UI"),
            values=["Light", "Dark", "System"],
            command=self.optionmenu_theme_callback,
            variable=StringVar(value=self.parent.APPEARANCE_THEME),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_appearance_theme.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_appearance_theme._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu UI scaling
        row += 1
        self.label_ui_scaling = CTkLabel(
            self.tabview_config.tab("UI"),
            text="UI Scaling:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_ui_scaling.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_ui_scaling = CTkOptionMenu(
            self.tabview_config.tab("UI"),
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.optionmenu_ui_scaling_callback,
            variable=StringVar(value=self.parent.UI_SCALING),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_ui_scaling.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_ui_scaling._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu font family
        row += 1
        self.label_font_family = CTkLabel(
            self.tabview_config.tab("UI"),
            text="Font Family:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_font_family.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        font_families = list(tk_font.families())
        self.optionmenu_font_family = CTkOptionMenu(
            self.tabview_config.tab("UI"),
            values=font_families,
            command=self.optionmenu_font_family_callback,
            variable=StringVar(value=self.parent.FONT_FAMILY),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_font_family.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_font_family._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        # tab Translation
        ## optionmenu translation translator
        row = 0
        padx = 5
        pady = 1
        self.label_translation_translator = CTkLabel(
            self.tabview_config.tab("Translation"),
            text="Select Translator:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.label_translation_translator.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_translation_translator = CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            values=list(self.parent.translator.translator_status.keys()),
            command=self.optionmenu_translation_translator_callback,
            variable=StringVar(value=self.parent.CHOICE_TRANSLATOR),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_translator.grid(row=row, column=1, columnspan=3 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_translator._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu translation input language
        row +=1
        self.label_translation_input_language = CTkLabel(
            self.tabview_config.tab("Translation"),
            text="Send Language:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_input_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        ## select translation input source language
        self.optionmenu_translation_input_source_language = CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_input_source_language_callback,
            values=list(translation_lang[self.parent.CHOICE_TRANSLATOR].keys()),
            variable=StringVar(value=self.parent.INPUT_SOURCE_LANG),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_input_source_language.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_input_source_language._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## label translation input arrow
        self.label_translation_input_arrow = CTkLabel(
            self.tabview_config.tab("Translation"),
            text="-->",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_input_arrow.grid(row=row, column=2, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## select translation input target language
        self.optionmenu_translation_input_target_language = CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_input_target_language_callback,
            values=list(translation_lang[self.parent.CHOICE_TRANSLATOR].keys()),
            variable=StringVar(value=self.parent.INPUT_TARGET_LANG),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_input_target_language.grid(row=row, column=3, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_input_target_language._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu translation output language
        row +=1
        self.label_translation_output_language = CTkLabel(
            self.tabview_config.tab("Translation"),
            text="Receive Language:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_output_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        ## select translation output source language
        self.optionmenu_translation_output_source_language = CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_output_source_language_callback,
            values=list(translation_lang[self.parent.CHOICE_TRANSLATOR].keys()),
            variable=StringVar(value=self.parent.OUTPUT_SOURCE_LANG),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_output_source_language.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_output_source_language._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## label translation output arrow
        self.label_translation_output_arrow = CTkLabel(
            self.tabview_config.tab("Translation"),
            text="-->",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_output_arrow.grid(row=row, column=2, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## select translation output target language
        self.optionmenu_translation_output_target_language = CTkOptionMenu(
            self.tabview_config.tab("Translation"),
            command=self.optionmenu_translation_output_target_language_callback,
            values=list(translation_lang[self.parent.CHOICE_TRANSLATOR].keys()),
            variable=StringVar(value=self.parent.OUTPUT_TARGET_LANG),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_output_target_language.grid(row=row, column=3, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_translation_output_target_language._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        # tab Transcription
        ## optionmenu input mic device
        row = 0
        padx = 5
        pady = 1
        self.label_input_mic_device = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Device:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_device.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_mic_device = CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=[device["name"] for device in get_input_device_list()],
            command=self.optionmenu_input_mic_device_callback,
            variable=StringVar(value=self.parent.CHOICE_MIC_DEVICE),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_mic_device.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_input_mic_device._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu input mic voice language
        row +=1
        self.label_input_mic_voice_language = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Voice Language:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_voice_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_mic_voice_language = CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=list(transcription_lang.keys()),
            command=self.optionmenu_input_mic_voice_language_callback,
            variable=StringVar(value=self.parent.INPUT_MIC_VOICE_LANGUAGE),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_mic_voice_language.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_input_mic_voice_language._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## entry input mic energy threshold
        row +=1
        self.label_input_mic_energy_threshold = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Energy Threshold:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_energy_threshold.grid(row=row, column=0, rowspan=2, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.progressBar_input_mic_energy_threshold = CTkProgressBar(
            self.tabview_config.tab("Transcription"),
            corner_radius=0
        )
        self.progressBar_input_mic_energy_threshold.grid(row=row, column=1, columnspan=1, padx=5, pady=(5,0), sticky="nsew")
        self.th_progressBar_input_mic_energy_threshold_recorder = Thread(target=self.progressBar_input_mic_energy_threshold_recorder, daemon=True)
        self.th_progressBar_input_mic_energy_threshold_recorder.start()
        sleep(2)

        row +=1
        self.slider_input_mic_energy_threshold = customtkinter.CTkSlider(
            self.tabview_config.tab("Transcription"),
            from_=0,
            to=self.MAX_MIC_ENERGY_THRESHOLD,
            border_width=5,
            button_length=0,
            button_corner_radius=3,
            number_of_steps=self.MAX_MIC_ENERGY_THRESHOLD,
            command=self.slider_input_mic_energy_threshold_callback,
            variable=IntVar(value=self.parent.INPUT_MIC_ENERGY_THRESHOLD),
        )
        self.slider_input_mic_energy_threshold.grid(row=row, column=1, columnspan=1, padx=0, pady=0, sticky="nsew")

        ## checkbox input mic dynamic energy threshold
        row +=1
        self.label_input_mic_dynamic_energy_threshold = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Dynamic Energy Threshold:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_dynamic_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.checkbox_input_mic_dynamic_energy_threshold = CTkCheckBox(
            self.tabview_config.tab("Transcription"),
            text="",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_input_mic_dynamic_energy_threshold_callback,
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_input_mic_dynamic_energy_threshold.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        if  self.parent.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD is True:
            self.checkbox_input_mic_dynamic_energy_threshold.select()
        else:
            self.checkbox_input_mic_dynamic_energy_threshold.deselect()

        ## entry input mic record timeout
        row +=1
        self.label_input_mic_record_timeout = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Record Timeout:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_record_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_record_timeout = CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=StringVar(value=self.parent.INPUT_MIC_RECORD_TIMEOUT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_record_timeout.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_record_timeout.bind("<Any-KeyRelease>", self.entry_input_mic_record_timeout_callback)

        ## entry input mic phrase timeout
        row +=1
        self.label_input_mic_phrase_timeout = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Phrase Timeout:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_phrase_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_phrase_timeout = CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=StringVar(value=self.parent.INPUT_MIC_PHRASE_TIMEOUT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_phrase_timeout.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_phrase_timeout.bind("<Any-KeyRelease>", self.entry_input_mic_phrase_timeout_callback)

        ## entry input mic max phrases
        row +=1
        self.label_input_mic_max_phrases = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Max Phrases:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_max_phrases.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_max_phrases = CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=StringVar(value=self.parent.INPUT_MIC_MAX_PHRASES),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_max_phrases.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_max_phrases.bind("<Any-KeyRelease>", self.entry_input_mic_max_phrases_callback)

        ## entry input mic word filter
        row +=1
        self.label_input_mic_word_filter = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Mic Word Filter:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_word_filter.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_word_filter = CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=StringVar(value=",".join(self.parent.INPUT_MIC_WORD_FILTER)),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_word_filter.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_word_filter.bind("<Any-KeyRelease>", self.entry_input_mic_word_filters_callback)

        ## optionmenu input speaker device
        row +=1
        self.label_input_speaker_device = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Device:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_device.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_speaker_device = CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=[device["name"] for device in get_output_device_list()],
            command=self.optionmenu_input_speaker_device_callback,
            variable=StringVar(value=self.parent.CHOICE_SPEAKER_DEVICE),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_speaker_device.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_input_speaker_device._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## optionmenu input speaker voice language
        row +=1
        self.label_input_speaker_voice_language = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Voice Language:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_voice_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_speaker_voice_language = CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=list(transcription_lang.keys()),
            command=self.optionmenu_input_speaker_voice_language_callback,
            variable=StringVar(value=self.parent.INPUT_SPEAKER_VOICE_LANGUAGE),
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_speaker_voice_language.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.optionmenu_input_speaker_voice_language._dropdown_menu.configure(font=CTkFont(family=self.parent.FONT_FAMILY))

        ## entry input speaker energy threshold
        row +=1
        self.label_input_speaker_energy_threshold = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Energy Threshold:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_energy_threshold.grid(row=row, column=0, rowspan=2, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        self.progressBar_input_speaker_energy_threshold = CTkProgressBar(
            self.tabview_config.tab("Transcription"),
            corner_radius=0
        )
        self.progressBar_input_speaker_energy_threshold.grid(row=row, column=1, columnspan=1, padx=5, pady=(5,0), sticky="nsew")
        self.th_progressBar_input_speaker_energy_threshold_recorder = Thread(target=self.progressBar_input_speaker_energy_threshold_recorder, daemon=True)
        self.th_progressBar_input_speaker_energy_threshold_recorder.start()

        row +=1
        self.slider_input_speaker_energy_threshold = customtkinter.CTkSlider(
            self.tabview_config.tab("Transcription"),
            from_=0,
            to=self.MAX_SPEAKER_ENERGY_THRESHOLD,
            border_width=5,
            button_length=0,
            button_corner_radius=3,
            number_of_steps=self.MAX_SPEAKER_ENERGY_THRESHOLD,
            command=self.slider_input_speaker_energy_threshold_callback,
            variable=IntVar(value=self.parent.INPUT_SPEAKER_ENERGY_THRESHOLD),
        )
        self.slider_input_speaker_energy_threshold.grid(row=row, column=1, columnspan=1, padx=0, pady=0, sticky="nsew")

        ## checkbox input speaker dynamic energy threshold
        row +=1
        self.label_input_speaker_dynamic_energy_threshold = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Dynamic Energy Threshold:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_dynamic_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.checkbox_input_speaker_dynamic_energy_threshold = CTkCheckBox(
            self.tabview_config.tab("Transcription"),
            text="",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_input_speaker_dynamic_energy_threshold_callback,
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_input_speaker_dynamic_energy_threshold.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        if  self.parent.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD is True:
            self.checkbox_input_speaker_dynamic_energy_threshold.select()
        else:
            self.checkbox_input_speaker_dynamic_energy_threshold.deselect()

        ## entry input speaker record timeout
        row +=1
        self.label_input_speaker_record_timeout = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Record Timeout:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_record_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_record_timeout = CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=StringVar(value=self.parent.INPUT_SPEAKER_RECORD_TIMEOUT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_record_timeout.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_record_timeout.bind("<Any-KeyRelease>", self.entry_input_speaker_record_timeout_callback)

        ## entry input speaker phrase timeout
        row +=1
        self.label_input_speaker_phrase_timeout = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Phrase Timeout:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_phrase_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_phrase_timeout = CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=StringVar(value=self.parent.INPUT_SPEAKER_PHRASE_TIMEOUT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_phrase_timeout.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_phrase_timeout.bind("<Any-KeyRelease>", self.entry_input_speaker_phrase_timeout_callback)

        ## entry input speaker max phrases
        row +=1
        self.label_input_speaker_max_phrases = CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Max Phrases:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_max_phrases.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_max_phrases = CTkEntry(
            self.tabview_config.tab("Transcription"),
            textvariable=StringVar(value=self.parent.INPUT_SPEAKER_MAX_PHRASES),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_max_phrases.grid(row=row, column=1, columnspan=1 ,padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_max_phrases.bind("<Any-KeyRelease>", self.entry_input_speaker_max_phrases_callback)

        # tab Parameter
        ## entry ip address
        row = 0
        padx = 5
        pady = 1
        self.label_ip_address = CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="OSC IP address:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_ip_address.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_ip_address = CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=StringVar(value=self.parent.OSC_IP_ADDRESS),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_ip_address.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_ip_address.bind("<Any-KeyRelease>", self.entry_ip_address_callback)

        ## entry port
        row +=1
        self.label_port = CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="OSC Port:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_port.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_port = CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=StringVar(value=self.parent.OSC_PORT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_port.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_port.bind("<Any-KeyRelease>", self.entry_port_callback)

        ## entry authkey
        row +=1
        self.label_authkey = CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="DeepL Auth Key:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_authkey.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_authkey = CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=StringVar(value=self.parent.AUTH_KEYS["DeepL(auth)"]),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_authkey.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_authkey.bind("<Any-KeyRelease>", self.entry_authkey_callback)

        ## entry message format
        row +=1
        self.label_message_format = CTkLabel(
            self.tabview_config.tab("Parameter"),
            text="Message Format:",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_message_format.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_message_format = CTkEntry(
            self.tabview_config.tab("Parameter"),
            textvariable=StringVar(value=self.parent.MESSAGE_FORMAT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_message_format.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_message_format.bind("<Any-KeyRelease>", self.entry_message_format_callback)

        self.protocol("WM_DELETE_WINDOW", self.delete_window)

    def slider_transparency_callback(self, value):
        self.parent.wm_attributes("-alpha", value/100)
        self.parent.TRANSPARENCY = value
        save_json(self.parent.PATH_CONFIG, "TRANSPARENCY", self.parent.TRANSPARENCY)

    def optionmenu_theme_callback(self, choice):
        customtkinter.set_appearance_mode(choice)
        self.parent.APPEARANCE_THEME = choice
        save_json(self.parent.PATH_CONFIG, "APPEARANCE_THEME", self.parent.APPEARANCE_THEME)

    def optionmenu_ui_scaling_callback(self, choice):
        new_scaling_float = int(choice.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)
        self.parent.UI_SCALING = choice
        save_json(self.parent.PATH_CONFIG, "UI_SCALING", self.parent.UI_SCALING)

    def optionmenu_font_family_callback(self, choice):
        # tab menu
        self.tabview_config._segmented_button.configure(font=CTkFont(family=choice))

        # tab UI
        self.label_transparency.configure(font=CTkFont(family=choice))
        self.label_appearance_theme.configure(font=CTkFont(family=choice))
        self.optionmenu_appearance_theme.configure(font=CTkFont(family=choice))
        self.optionmenu_appearance_theme._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_ui_scaling.configure(font=CTkFont(family=choice))
        self.optionmenu_ui_scaling.configure(font=CTkFont(family=choice))
        self.optionmenu_ui_scaling._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_font_family.configure(font=CTkFont(family=choice))
        self.optionmenu_font_family.configure(font=CTkFont(family=choice))
        self.optionmenu_font_family._dropdown_menu.configure(font=CTkFont(family=choice))

        # tab Translation
        self.label_translation_translator.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_translator.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_translator._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_translation_input_language.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_input_source_language.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_input_source_language._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_translation_input_arrow.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_input_target_language.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_input_target_language._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_translation_output_language.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_output_source_language.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_output_source_language._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_translation_output_arrow.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_output_target_language.configure(font=CTkFont(family=choice))
        self.optionmenu_translation_output_target_language._dropdown_menu.configure(font=CTkFont(family=choice))

        # tab Transcription
        self.label_input_mic_device.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_device.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_device._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_input_mic_voice_language.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_voice_language.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_voice_language._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_input_mic_energy_threshold.configure(font=CTkFont(family=choice))
        self.label_input_mic_dynamic_energy_threshold.configure(font=CTkFont(family=choice))
        self.label_input_mic_record_timeout.configure(font=CTkFont(family=choice))
        self.entry_input_mic_record_timeout.configure(font=CTkFont(family=choice))
        self.label_input_mic_phrase_timeout.configure(font=CTkFont(family=choice))
        self.entry_input_mic_phrase_timeout.configure(font=CTkFont(family=choice))
        self.label_input_mic_max_phrases.configure(font=CTkFont(family=choice))
        self.entry_input_mic_max_phrases.configure(font=CTkFont(family=choice))
        self.label_input_mic_word_filter.configure(font=CTkFont(family=choice))
        self.entry_input_mic_word_filter.configure(font=CTkFont(family=choice))
        self.label_input_speaker_device.configure(font=CTkFont(family=choice))
        self.optionmenu_input_speaker_device.configure(font=CTkFont(family=choice))
        self.optionmenu_input_speaker_device._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_input_speaker_voice_language.configure(font=CTkFont(family=choice))
        self.optionmenu_input_speaker_voice_language.configure(font=CTkFont(family=choice))
        self.optionmenu_input_speaker_voice_language._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_input_speaker_energy_threshold.configure(font=CTkFont(family=choice))
        self.label_input_speaker_dynamic_energy_threshold.configure(font=CTkFont(family=choice))
        self.label_input_speaker_record_timeout.configure(font=CTkFont(family=choice))
        self.entry_input_speaker_record_timeout.configure(font=CTkFont(family=choice))
        self.label_input_speaker_phrase_timeout.configure(font=CTkFont(family=choice))
        self.entry_input_speaker_phrase_timeout.configure(font=CTkFont(family=choice))
        self.label_input_speaker_max_phrases.configure(font=CTkFont(family=choice))
        self.entry_input_speaker_max_phrases.configure(font=CTkFont(family=choice))

        # tab Parameter
        self.label_ip_address.configure(font=CTkFont(family=choice))
        self.entry_ip_address.configure(font=CTkFont(family=choice))
        self.label_port.configure(font=CTkFont(family=choice))
        self.entry_port.configure(font=CTkFont(family=choice))
        self.label_authkey.configure(font=CTkFont(family=choice))
        self.entry_authkey.configure(font=CTkFont(family=choice))
        self.label_message_format.configure(font=CTkFont(family=choice))
        self.entry_message_format.configure(font=CTkFont(family=choice))

        # main window
        self.parent.checkbox_translation.configure(font=CTkFont(family=choice))
        self.parent.checkbox_transcription_send.configure(font=CTkFont(family=choice))
        self.parent.checkbox_transcription_receive.configure(font=CTkFont(family=choice))
        self.parent.checkbox_foreground.configure(font=CTkFont(family=choice))
        self.parent.textbox_message_log.configure(font=CTkFont(family=choice))
        self.parent.textbox_message_send_log.configure(font=CTkFont(family=choice))
        self.parent.textbox_message_receive_log.configure(font=CTkFont(family=choice))
        self.parent.textbox_message_system_log.configure(font=CTkFont(family=choice))
        self.parent.entry_message_box.configure(font=CTkFont(family=choice))
        self.parent.tabview_logs._segmented_button.configure(font=CTkFont(family=choice))

        # window information
        try:
            self.parent.information_window.textbox_information.configure(font=CTkFont(family=choice))
        except:
            pass

        self.parent.FONT_FAMILY = choice
        save_json(self.parent.PATH_CONFIG, "FONT_FAMILY", self.parent.FONT_FAMILY)

    def optionmenu_translation_translator_callback(self, choice):
        if self.parent.translator.authentication(choice, self.parent.AUTH_KEYS[choice]) is False:
            print_textbox(self.parent.textbox_message_log,  "Auth Key or language setting is incorrect", "ERROR")
            print_textbox(self.parent.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
        else:
            self.optionmenu_translation_input_source_language.configure(
                values=list(translation_lang[choice].keys()),
                variable=StringVar(value=list(translation_lang[choice].keys())[0]))
            self.optionmenu_translation_input_target_language.configure(
                values=list(translation_lang[choice].keys()),
                variable=StringVar(value=list(translation_lang[choice].keys())[1]))
            self.optionmenu_translation_output_source_language.configure(
                values=list(translation_lang[choice].keys()),
                variable=StringVar(value=list(translation_lang[choice].keys())[1]))
            self.optionmenu_translation_output_target_language.configure(
                values=list(translation_lang[choice].keys()),
                variable=StringVar(value=list(translation_lang[choice].keys())[0]))

            self.parent.CHOICE_TRANSLATOR = choice
            self.parent.INPUT_SOURCE_LANG = list(translation_lang[choice].keys())[0]
            self.parent.INPUT_TARGET_LANG = list(translation_lang[choice].keys())[1]
            self.parent.OUTPUT_SOURCE_LANG = list(translation_lang[choice].keys())[1]
            self.parent.OUTPUT_TARGET_LANG = list(translation_lang[choice].keys())[0]
            save_json(self.parent.PATH_CONFIG, "CHOICE_TRANSLATOR", self.parent.CHOICE_TRANSLATOR)
            save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)
            save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)
            save_json(self.parent.PATH_CONFIG, "OUTPUT_SOURCE_LANG", self.parent.OUTPUT_SOURCE_LANG)
            save_json(self.parent.PATH_CONFIG, "OUTPUT_TARGET_LANG", self.parent.OUTPUT_TARGET_LANG)

    def optionmenu_translation_input_source_language_callback(self, choice):
        self.parent.INPUT_SOURCE_LANG = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)

    def optionmenu_translation_input_target_language_callback(self, choice):
        self.parent.INPUT_TARGET_LANG = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)

    def optionmenu_translation_output_source_language_callback(self, choice):
        self.parent.OUTPUT_SOURCE_LANG = choice
        save_json(self.parent.PATH_CONFIG, "OUTPUT_SOURCE_LANG", self.parent.OUTPUT_SOURCE_LANG)

    def optionmenu_translation_output_target_language_callback(self, choice):
        self.parent.OUTPUT_TARGET_LANG = choice
        save_json(self.parent.PATH_CONFIG, "OUTPUT_TARGET_LANG", self.parent.OUTPUT_TARGET_LANG)

    def optionmenu_input_mic_device_callback(self, choice):
        self.parent.CHOICE_MIC_DEVICE = choice
        save_json(self.parent.PATH_CONFIG, "CHOICE_MIC_DEVICE", self.parent.CHOICE_MIC_DEVICE)

    def optionmenu_input_mic_voice_language_callback(self, choice):
        self.parent.INPUT_MIC_VOICE_LANGUAGE = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_VOICE_LANGUAGE", self.parent.INPUT_MIC_VOICE_LANGUAGE)

    def progressBar_input_mic_energy_threshold_recorder(self):
        while self.FLAG_LOOP_MIC:
            mic_device_name = self.parent.CHOICE_MIC_DEVICE
            mic_device = [device for device in get_input_device_list() if device["name"] == mic_device_name][0]
            re = SelectedMicRecorder(mic_device, energy_threshold=0, dynamic_energy_threshold=False, record_timeout=0)
            while self.FLAG_LOOP_MIC:
                if mic_device_name != self.parent.CHOICE_MIC_DEVICE:
                    break
                with re.source as source:
                    energy = re.recorder.listen_energy(source)
                    self.progressBar_input_mic_energy_threshold.set(energy/self.MAX_MIC_ENERGY_THRESHOLD)
            sleep(2)

    def slider_input_mic_energy_threshold_callback(self, value):
        self.parent.INPUT_MIC_ENERGY_THRESHOLD = int(value)
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_ENERGY_THRESHOLD", self.parent.INPUT_MIC_ENERGY_THRESHOLD)

    def checkbox_input_mic_dynamic_energy_threshold_callback(self):
        value = self.checkbox_input_mic_dynamic_energy_threshold.get()
        self.parent.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD = value
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD", self.parent.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD)

    def entry_input_mic_record_timeout_callback(self, event):
        self.parent.INPUT_MIC_RECORD_TIMEOUT = int(self.entry_input_mic_record_timeout.get())
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_RECORD_TIMEOUT", self.parent.INPUT_MIC_RECORD_TIMEOUT)

    def entry_input_mic_phrase_timeout_callback(self, event):
        self.parent.INPUT_MIC_PHRASE_TIMEOUT = int(self.entry_input_mic_phrase_timeout.get())
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_PHRASE_TIMEOUT", self.parent.INPUT_MIC_PHRASE_TIMEOUT)

    def entry_input_mic_max_phrases_callback(self, event):
        self.parent.INPUT_MIC_MAX_PHRASES = int(self.entry_input_mic_max_phrases.get())
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_MAX_PHRASES", self.parent.INPUT_MIC_MAX_PHRASES)

    def entry_input_mic_word_filters_callback(self, event):
        self.parent.INPUT_MIC_WORD_FILTER = self.entry_input_mic_word_filter.get().split(",")
        self.parent.keyword_processor = KeywordProcessor()
        for f in self.parent.INPUT_MIC_WORD_FILTER:
            self.parent.keyword_processor.add_keyword(f)
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_WORD_FILTER", self.parent.INPUT_MIC_WORD_FILTER)

    def optionmenu_input_speaker_device_callback(self, choice):
        self.parent.CHOICE_SPEAKER_DEVICE = choice
        save_json(self.parent.PATH_CONFIG, "CHOICE_SPEAKER_DEVICE", self.parent.CHOICE_SPEAKER_DEVICE)

    def optionmenu_input_speaker_voice_language_callback(self, choice):
        self.parent.INPUT_SPEAKER_VOICE_LANGUAGE = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_VOICE_LANGUAGE", self.parent.INPUT_SPEAKER_VOICE_LANGUAGE)

    def progressBar_input_speaker_energy_threshold_recorder(self):
        while self.FLAG_LOOP_SPEAKER:
            speaker_device_name = self.parent.CHOICE_SPEAKER_DEVICE
            speaker_device = [device for device in get_output_device_list() if device["name"] == speaker_device_name][0]
            re = SelectedSpeakerRecorder(speaker_device, energy_threshold=0, dynamic_energy_threshold=False, record_timeout=0)
            while self.FLAG_LOOP_SPEAKER:
                if speaker_device_name != self.parent.CHOICE_SPEAKER_DEVICE:
                    break
                with re.source as source:
                    energy = re.recorder.listen_energy(source)
                    self.progressBar_input_speaker_energy_threshold.set(energy/self.MAX_SPEAKER_ENERGY_THRESHOLD)
            sleep(2)

    def slider_input_speaker_energy_threshold_callback(self, value):
        self.parent.INPUT_SPEAKER_ENERGY_THRESHOLD = int(value)
        save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_ENERGY_THRESHOLD", self.parent.INPUT_SPEAKER_ENERGY_THRESHOLD)

    def checkbox_input_speaker_dynamic_energy_threshold_callback(self):
        value = self.checkbox_input_speaker_dynamic_energy_threshold.get()
        self.parent.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD = value
        save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD", self.parent.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD)

    def entry_input_speaker_record_timeout_callback(self, event):
        self.parent.INPUT_SPEAKER_RECORD_TIMEOUT = int(self.entry_input_speaker_record_timeout.get())
        save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_RECORD_TIMEOUT", self.parent.INPUT_SPEAKER_RECORD_TIMEOUT)

    def entry_input_speaker_phrase_timeout_callback(self, event):
        self.parent.INPUT_SPEAKER_PHRASE_TIMEOUT = int(self.entry_input_speaker_phrase_timeout.get())
        save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_PHRASE_TIMEOUT", self.parent.INPUT_SPEAKER_PHRASE_TIMEOUT)

    def entry_input_speaker_max_phrases_callback(self, event):
        self.parent.INPUT_SPEAKER_MAX_PHRASES = int(self.entry_input_speaker_max_phrases.get())
        save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_MAX_PHRASES", self.parent.INPUT_SPEAKER_MAX_PHRASES)

    def entry_ip_address_callback(self, event):
        self.parent.OSC_IP_ADDRESS = self.entry_ip_address.get()
        save_json(self.parent.PATH_CONFIG, "OSC_IP_ADDRESS", self.parent.OSC_IP_ADDRESS)

    def entry_port_callback(self, event):
        self.parent.OSC_PORT = self.entry_port.get()
        save_json(self.parent.PATH_CONFIG, "OSC_PORT", self.parent.OSC_PORT)

    def entry_authkey_callback(self, event):
        value = self.entry_authkey.get()
        if len(value) > 0:
            if self.parent.translator.authentication("DeepL(auth)", value) is True:
                self.parent.AUTH_KEYS["DeepL(auth)"] = value
                save_json(self.parent.PATH_CONFIG, "AUTH_KEYS", self.parent.AUTH_KEYS)
                print_textbox(self.parent.textbox_message_log, "Auth key update completed", "INFO")
                print_textbox(self.parent.textbox_message_system_log, "Auth key update completed", "INFO")
            else:
                pass

    def delete_window(self):
        self.FLAG_LOOP_MIC = False
        self.FLAG_LOOP_SPEAKER = False
        self.th_progressBar_input_mic_energy_threshold_recorder.join()
        self.th_progressBar_input_speaker_energy_threshold_recorder.join()
        sleep(1)
        self.parent.checkbox_translation.configure(state="normal")
        self.parent.checkbox_transcription_send.configure(state="normal")
        self.parent.checkbox_transcription_receive.configure(state="normal")
        self.parent.config_window.destroy()

    def entry_message_format_callback(self, event):
        value = self.entry_message_format.get()
        if len(value) > 0:
            self.parent.MESSAGE_FORMAT = value
            save_json(self.parent.PATH_CONFIG, "MESSAGE_FORMAT", self.parent.MESSAGE_FORMAT)