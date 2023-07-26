from time import sleep
from queue import Queue
from os import path as os_path
from tkinter import DoubleVar, IntVar
from tkinter import font as tk_font
import customtkinter
from customtkinter import CTkToplevel, CTkTabview, CTkFont, CTkLabel, CTkSlider, CTkOptionMenu, StringVar, CTkEntry, CTkCheckBox, CTkProgressBar
from flashtext import KeywordProcessor

from threading import Thread
from utils import save_json, print_textbox, thread_fnc, get_localized_text, get_key_by_value, widget_config_window_label_setter
from audio_utils import get_input_device_list, get_output_device_list, get_default_output_device
from audio_recorder import SelectedMicEnergyRecorder, SelectedSpeakeEnergyRecorder
from languages import translation_lang, transcription_lang, selectable_languages

from ctk_scrollable_dropdown import CTkScrollableDropdown

SCROLLABLE_DROPDOWN = False

class ToplevelWindowConfig(CTkToplevel):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.withdraw()
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
        self.mic_energy_recorder = None
        self.mic_energy_plot_progressbar = None
        self.speaker_energy_recorder = None
        self.speaker_energy_get_progressbar = None
        self.speaker_energy_plot_progressbar = None

        # load ui language data
        language_yaml_data = get_localized_text(f"{self.parent.UI_LANGUAGE}")
        # add tabview config
        self.add_tabview_config(language_yaml_data, selectable_languages)
        # set all config window labels
        widget_config_window_label_setter(self, language_yaml_data)

        self.protocol("WM_DELETE_WINDOW", self.delete_window)

    def slider_transparency_callback(self, value):
        self.parent.wm_attributes("-alpha", value/100)
        self.parent.TRANSPARENCY = value
        save_json(self.parent.PATH_CONFIG, "TRANSPARENCY", self.parent.TRANSPARENCY)

    def optionmenu_appearance_theme_callback(self, choice):
        self.optionmenu_appearance_theme.set(choice)

        customtkinter.set_appearance_mode(choice)
        self.parent.APPEARANCE_THEME = choice
        save_json(self.parent.PATH_CONFIG, "APPEARANCE_THEME", self.parent.APPEARANCE_THEME)

    def optionmenu_ui_scaling_callback(self, choice):
        self.optionmenu_ui_scaling.set(choice)

        new_scaling_float = int(choice.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)
        self.parent.UI_SCALING = choice
        save_json(self.parent.PATH_CONFIG, "UI_SCALING", self.parent.UI_SCALING)

    def optionmenu_font_family_callback(self, choice):
        self.optionmenu_font_family.set(choice)

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
        self.label_ui_language.configure(font=CTkFont(family=choice))
        self.optionmenu_ui_language.configure(font=CTkFont(family=choice))
        self.optionmenu_ui_language._dropdown_menu.configure(font=CTkFont(family=choice))

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
        self.label_input_mic_host.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_host.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_host._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_input_mic_device.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_device.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_device._dropdown_menu.configure(font=CTkFont(family=choice))
        self.label_input_mic_voice_language.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_voice_language.configure(font=CTkFont(family=choice))
        self.optionmenu_input_mic_voice_language._dropdown_menu.configure(font=CTkFont(family=choice))
        self.checkbox_input_mic_threshold_check.configure(font=CTkFont(family=choice))
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
        self.checkbox_input_speaker_threshold_check.configure(font=CTkFont(family=choice))
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

        # tab Others
        self.label_checkbox_auto_clear_chatbox.configure(font=CTkFont(family=choice))

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

    def optionmenu_ui_language_callback(self, choice):
        self.optionmenu_ui_language.set(choice)

        self.withdraw()
        pre_language_yaml_data = get_localized_text(f"{self.parent.UI_LANGUAGE}")
        self.parent.UI_LANGUAGE = get_key_by_value(selectable_languages, choice)
        language_yaml_data = get_localized_text(f"{self.parent.UI_LANGUAGE}")
        save_json(self.parent.PATH_CONFIG, "UI_LANGUAGE", self.parent.UI_LANGUAGE)


        # delete
        self.parent.delete_tabview_logs(pre_language_yaml_data)
        self.delete_tabview_config(pre_language_yaml_data)
        # add tabview textbox
        self.parent.add_tabview_logs(language_yaml_data)
        self.add_tabview_config(language_yaml_data, selectable_languages)

        # 翻訳予定
        # window information
        # try:
        #     self.parent.information_window.textbox_information.configure(font=customtkinter.CTkFont(family=choice))
        # except:
        #     pass
        self.deiconify()

    def optionmenu_translation_translator_callback(self, choice):
        self.optionmenu_translation_translator.set(choice)

        if self.parent.translator.authentication(choice, self.parent.AUTH_KEYS[choice]) is False:
            print_textbox(self.parent.textbox_message_log,  "Auth Key or language setting is incorrect", "ERROR")
            print_textbox(self.parent.textbox_message_system_log, "Auth Key or language setting is incorrect", "ERROR")
        else:
            self.optionmenu_translation_input_source_language.configure(
                values=list(translation_lang[choice]["source"].keys()),
                variable=StringVar(value=list(translation_lang[choice]["source"].keys())[0]))
            self.optionmenu_translation_input_target_language.configure(
                values=list(translation_lang[choice]["target"].keys()),
                variable=StringVar(value=list(translation_lang[choice]["target"].keys())[1]))
            self.optionmenu_translation_output_source_language.configure(
                values=list(translation_lang[choice]["source"].keys()),
                variable=StringVar(value=list(translation_lang[choice]["source"].keys())[1]))
            self.optionmenu_translation_output_target_language.configure(
                values=list(translation_lang[choice]["target"].keys()),
                variable=StringVar(value=list(translation_lang[choice]["target"].keys())[0]))

            if SCROLLABLE_DROPDOWN:
                self.scrollableDropdown_translation_input_source_language.configure(
                values=list(translation_lang[choice]["source"].keys()))
                self.scrollableDropdown_translation_input_target_language.configure(
                values=list(translation_lang[choice]["target"].keys()))
                self.scrollableDropdown_translation_output_source_language.configure(
                values=list(translation_lang[choice]["source"].keys()))
                self.scrollableDropdown_translation_output_target_language.configure(
                values=list(translation_lang[choice]["target"].keys()))

            self.parent.CHOICE_TRANSLATOR = choice
            self.parent.INPUT_SOURCE_LANG = list(translation_lang[choice]["source"].keys())[0]
            self.parent.INPUT_TARGET_LANG = list(translation_lang[choice]["target"].keys())[1]
            self.parent.OUTPUT_SOURCE_LANG = list(translation_lang[choice]["source"].keys())[1]
            self.parent.OUTPUT_TARGET_LANG = list(translation_lang[choice]["target"].keys())[0]
            save_json(self.parent.PATH_CONFIG, "CHOICE_TRANSLATOR", self.parent.CHOICE_TRANSLATOR)
            save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)
            save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)
            save_json(self.parent.PATH_CONFIG, "OUTPUT_SOURCE_LANG", self.parent.OUTPUT_SOURCE_LANG)
            save_json(self.parent.PATH_CONFIG, "OUTPUT_TARGET_LANG", self.parent.OUTPUT_TARGET_LANG)

    def optionmenu_translation_input_source_language_callback(self, choice):
        self.optionmenu_translation_input_source_language.set(choice)

        self.parent.INPUT_SOURCE_LANG = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)

    def optionmenu_translation_input_target_language_callback(self, choice):
        self.optionmenu_translation_input_target_language.set(choice)

        self.parent.INPUT_TARGET_LANG = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)

    def optionmenu_translation_output_source_language_callback(self, choice):
        self.optionmenu_translation_output_source_language.set(choice)

        self.parent.OUTPUT_SOURCE_LANG = choice
        save_json(self.parent.PATH_CONFIG, "OUTPUT_SOURCE_LANG", self.parent.OUTPUT_SOURCE_LANG)

    def optionmenu_translation_output_target_language_callback(self, choice):
        self.optionmenu_translation_output_target_language.set(choice)

        self.parent.OUTPUT_TARGET_LANG = choice
        save_json(self.parent.PATH_CONFIG, "OUTPUT_TARGET_LANG", self.parent.OUTPUT_TARGET_LANG)

    def optionmenu_input_mic_host_callback(self, choice):
        self.optionmenu_input_mic_host.set(choice)

        self.optionmenu_input_mic_device.configure(
            values=[device["name"] for device in get_input_device_list()[choice]],
            variable=StringVar(value=[device["name"] for device in get_input_device_list()[choice]][0]))

        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_input_mic_device.configure(values=[device["name"] for device in get_input_device_list()[choice]])

        self.parent.CHOICE_MIC_HOST = choice
        self.parent.CHOICE_MIC_DEVICE = [device["name"] for device in get_input_device_list()[choice]][0]
        save_json(self.parent.PATH_CONFIG, "CHOICE_MIC_HOST", self.parent.CHOICE_MIC_HOST)
        save_json(self.parent.PATH_CONFIG, "CHOICE_MIC_DEVICE", self.parent.CHOICE_MIC_DEVICE)

    def optionmenu_input_mic_device_callback(self, choice):
        self.optionmenu_input_mic_device.set(choice)

        self.parent.CHOICE_MIC_DEVICE = choice
        save_json(self.parent.PATH_CONFIG, "CHOICE_MIC_DEVICE", self.parent.CHOICE_MIC_DEVICE)
        self.checkbox_input_mic_threshold_check.deselect()
        self.checkbox_input_mic_threshold_check_callback()

    def optionmenu_input_mic_voice_language_callback(self, choice):
        self.optionmenu_input_mic_voice_language.set(choice)

        self.parent.INPUT_MIC_VOICE_LANGUAGE = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_VOICE_LANGUAGE", self.parent.INPUT_MIC_VOICE_LANGUAGE)

    def progressBar_input_mic_energy_plot(self):
        if self.mic_energy_queue.empty() is False:
            energy = self.mic_energy_queue.get()
            try:
                self.progressBar_input_mic_energy_threshold.set(energy/self.MAX_MIC_ENERGY_THRESHOLD)
            except:
                pass
        sleep(0.01)

    def mic_threshold_check_start(self):
        self.mic_energy_queue = Queue()
        mic_device = [device for device in get_input_device_list()[self.parent.CHOICE_MIC_HOST] if device["name"] == self.parent.CHOICE_MIC_DEVICE][0]
        self.mic_energy_recorder = SelectedMicEnergyRecorder(mic_device)
        self.mic_energy_recorder.record_into_queue(self.mic_energy_queue)
        self.mic_energy_plot_progressbar = thread_fnc(self.progressBar_input_mic_energy_plot)
        self.mic_energy_plot_progressbar.daemon = True
        self.mic_energy_plot_progressbar.start()
        self.checkbox_input_mic_threshold_check.configure(state="normal")
        self.checkbox_input_speaker_threshold_check.configure(state="normal")

    def mic_threshold_check_stop(self):
        if self.mic_energy_recorder != None:
            self.mic_energy_recorder.stop()
        if self.mic_energy_plot_progressbar != None:
            self.mic_energy_plot_progressbar.stop()
        self.progressBar_input_mic_energy_threshold.set(0)
        self.checkbox_input_mic_threshold_check.configure(state="normal")
        self.checkbox_input_speaker_threshold_check.configure(state="normal")

    def checkbox_input_mic_threshold_check_callback(self):
        self.checkbox_input_mic_threshold_check.configure(state="disabled")
        self.checkbox_input_speaker_threshold_check.configure(state="disabled")
        self.update()
        if self.checkbox_input_mic_threshold_check.get():
            th_mic_threshold_check_start = Thread(target=self.mic_threshold_check_start)
            th_mic_threshold_check_start.daemon = True
            th_mic_threshold_check_start.start()
        else:
            th_mic_threshold_check_stop = Thread(target=self.mic_threshold_check_stop)
            th_mic_threshold_check_stop.daemon = True
            th_mic_threshold_check_stop.start()

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
        word_filter = self.entry_input_mic_word_filter.get()
        word_filter = [w.strip() for w in word_filter.split(",") if len(w.strip()) > 0]
        word_filter = ",".join(word_filter)
        if len(word_filter) > 0:
            self.parent.INPUT_MIC_WORD_FILTER = word_filter.split(",")
        else:
            self.parent.INPUT_MIC_WORD_FILTER = []
        self.parent.keyword_processor = KeywordProcessor()
        for f in self.parent.INPUT_MIC_WORD_FILTER:
            self.parent.keyword_processor.add_keyword(f)
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_WORD_FILTER", self.parent.INPUT_MIC_WORD_FILTER)

    def optionmenu_input_speaker_device_callback(self, choice):
        speaker_device = [device for device in get_output_device_list() if device["name"] == choice][0]
        if get_default_output_device()["index"] == speaker_device["index"]:
            self.optionmenu_input_speaker_device.set(choice)
            self.parent.CHOICE_SPEAKER_DEVICE = choice
            save_json(self.parent.PATH_CONFIG, "CHOICE_SPEAKER_DEVICE", self.parent.CHOICE_SPEAKER_DEVICE)
        else:
            print_textbox(self.parent.textbox_message_log,  "Windows playback device and selected device do not match. Change the Windows playback device.", "ERROR")
            print_textbox(self.parent.textbox_message_system_log,  "Windows playback device and selected device do not match. Change the Windows playback device.", "ERROR")
            self.optionmenu_input_speaker_device.configure(variable=StringVar(value=self.parent.CHOICE_SPEAKER_DEVICE))

    def optionmenu_input_speaker_voice_language_callback(self, choice):
        self.optionmenu_input_speaker_voice_language.set(choice)

        self.parent.INPUT_SPEAKER_VOICE_LANGUAGE = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_SPEAKER_VOICE_LANGUAGE", self.parent.INPUT_SPEAKER_VOICE_LANGUAGE)

    def progressBar_input_speaker_energy_plot(self):
        if self.speaker_energy_queue.empty() is False:
            energy = self.speaker_energy_queue.get()
            try:
                self.progressBar_input_speaker_energy_threshold.set(energy/self.MAX_SPEAKER_ENERGY_THRESHOLD)
            except:
                pass
        sleep(0.01)

    def progressBar_input_speaker_energy_get(self):
        with self.speaker_energy_recorder.source as source:
            energy = self.speaker_energy_recorder.recorder.listen_energy(source)
            self.speaker_energy_queue.put(energy)

    def speaker_threshold_check_start(self):
        speaker_device = [device for device in get_output_device_list() if device["name"] == self.parent.CHOICE_SPEAKER_DEVICE][0]

        if get_default_output_device()["index"] == speaker_device["index"]:
            self.speaker_energy_queue = Queue()
            self.speaker_energy_recorder = SelectedSpeakeEnergyRecorder(speaker_device)
            self.speaker_energy_get_progressbar = thread_fnc(self.progressBar_input_speaker_energy_get)
            self.speaker_energy_get_progressbar.daemon = True
            self.speaker_energy_get_progressbar.start()
            self.speaker_energy_plot_progressbar = thread_fnc(self.progressBar_input_speaker_energy_plot)
            self.speaker_energy_plot_progressbar.daemon = True
            self.speaker_energy_plot_progressbar.start()
        else:
            print_textbox(self.parent.textbox_message_log,  "Windows playback device and selected device do not match. Change the Windows playback device.", "ERROR")
            print_textbox(self.parent.textbox_message_system_log,  "Windows playback device and selected device do not match. Change the Windows playback device.", "ERROR")
            self.checkbox_input_speaker_threshold_check.deselect()
        self.checkbox_input_mic_threshold_check.configure(state="normal")
        self.checkbox_input_speaker_threshold_check.configure(state="normal")

    def speaker_threshold_check_stop(self):
        if self.speaker_energy_get_progressbar != None:
            self.speaker_energy_get_progressbar.stop()
        if self.speaker_energy_plot_progressbar != None:
            self.speaker_energy_plot_progressbar.stop()

        self.progressBar_input_speaker_energy_threshold.set(0)
        self.checkbox_input_mic_threshold_check.configure(state="normal")
        self.checkbox_input_speaker_threshold_check.configure(state="normal")

    def checkbox_input_speaker_threshold_check_callback(self):
        self.checkbox_input_mic_threshold_check.configure(state="disabled")
        self.checkbox_input_speaker_threshold_check.configure(state="disabled")
        self.update()
        if self.checkbox_input_speaker_threshold_check.get():
            th_speaker_threshold_check_start = Thread(target=self.speaker_threshold_check_start)
            th_speaker_threshold_check_start.daemon = True
            th_speaker_threshold_check_start.start()
        else:
            th_speaker_threshold_check_stop = Thread(target=self.speaker_threshold_check_stop)
            th_speaker_threshold_check_stop.daemon = True
            th_speaker_threshold_check_stop.start()

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

    def checkbox_auto_clear_chatbox_callback(self):
        value = self.checkbox_auto_clear_chatbox.get()
        self.parent.ENABLE_AUTO_CLEAR_CHATBOX = value
        save_json(self.parent.PATH_CONFIG, "ENABLE_AUTO_CLEAR_CHATBOX", self.parent.ENABLE_AUTO_CLEAR_CHATBOX)

    def checkbox_notice_xsoverlay_callback(self):
        value = self.checkbox_notice_xsoverlay.get()
        self.parent.ENABLE_NOTICE_XSOVERLAY = value
        save_json(self.parent.PATH_CONFIG, "ENABLE_NOTICE_XSOVERLAY", self.parent.ENABLE_NOTICE_XSOVERLAY)

    def delete_window(self):
        self.checkbox_input_mic_threshold_check.deselect()
        self.checkbox_input_speaker_threshold_check.deselect()
        self.checkbox_input_mic_threshold_check_callback()
        self.checkbox_input_speaker_threshold_check_callback()

        self.parent.checkbox_translation.configure(state="normal")
        self.parent.checkbox_transcription_send.configure(state="normal")
        self.parent.checkbox_transcription_receive.configure(state="normal")
        self.parent.button_config.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])
        self.parent.config_window.withdraw()

    def entry_message_format_callback(self, event):
        value = self.entry_message_format.get()
        if len(value) > 0:
            self.parent.MESSAGE_FORMAT = value
            save_json(self.parent.PATH_CONFIG, "MESSAGE_FORMAT", self.parent.MESSAGE_FORMAT)

    def delete_tabview_config(self, pre_language_yaml_data):
        self.tabview_config.delete(pre_language_yaml_data["config_tab_title_ui"])
        self.tabview_config.delete(pre_language_yaml_data["config_tab_title_translation"])
        self.tabview_config.delete(pre_language_yaml_data["config_tab_title_transcription"])
        self.tabview_config.delete(pre_language_yaml_data["config_tab_title_parameter"])
        self.tabview_config.delete(pre_language_yaml_data["config_tab_title_others"])

    def add_tabview_config(self, language_yaml_data, selectable_languages):
        config_tab_title_ui = language_yaml_data["config_tab_title_ui"]
        config_tab_title_translation = language_yaml_data["config_tab_title_translation"]
        config_tab_title_transcription = language_yaml_data["config_tab_title_transcription"]
        config_tab_title_parameter = language_yaml_data["config_tab_title_parameter"]
        config_tab_title_others = language_yaml_data["config_tab_title_others"]

        init_lang_text = "Loading..."

        # tabwiew config
        self.tabview_config = CTkTabview(self)
        self.tabview_config.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.tabview_config.add(config_tab_title_ui)
        self.tabview_config.add(config_tab_title_translation)
        self.tabview_config.add(config_tab_title_transcription)
        self.tabview_config.add(config_tab_title_parameter)
        self.tabview_config.add(config_tab_title_others)
        self.tabview_config.tab(config_tab_title_ui).grid_columnconfigure(1, weight=1)
        self.tabview_config.tab(config_tab_title_translation).grid_columnconfigure([1,2,3], weight=1)
        self.tabview_config.tab(config_tab_title_transcription).grid_columnconfigure(1, weight=1)
        self.tabview_config.tab(config_tab_title_parameter).grid_columnconfigure(1, weight=1)
        self.tabview_config.tab(config_tab_title_others).grid_columnconfigure(1, weight=1)
        self.tabview_config._segmented_button.configure(font=CTkFont(family=self.parent.FONT_FAMILY))
        self.tabview_config._segmented_button.grid(sticky="W")

        # tab UI
        ## slider transparency
        row = 0
        padx = 5
        pady = 1
        self.label_transparency = CTkLabel(
            self.tabview_config.tab(config_tab_title_ui),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_transparency.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.slider_transparency = CTkSlider(
            self.tabview_config.tab(config_tab_title_ui),
            from_=50,
            to=100,
            command=self.slider_transparency_callback,
            variable=DoubleVar(value=self.parent.TRANSPARENCY),
        )
        self.slider_transparency.grid(row=row, column=1, columnspan=1, padx=padx, pady=10, sticky="nsew")

        ## optionmenu theme
        row += 1
        self.label_appearance_theme = CTkLabel(
            self.tabview_config.tab(config_tab_title_ui),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_appearance_theme.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_appearance_theme = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_ui),
            values=["Light", "Dark", "System"],
            command=self.optionmenu_appearance_theme_callback,
            variable=StringVar(value=self.parent.APPEARANCE_THEME),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_appearance_theme.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown appearance theme
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_appearance_theme = CTkScrollableDropdown(
                self.optionmenu_appearance_theme,
                values=["Light", "Dark", "System"],
                justify="left",
                button_color="transparent",
                command=self.optionmenu_appearance_theme_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_appearance_theme.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_appearance_theme._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_appearance_theme.frame._parent_frame)) else None,
            )

        ## optionmenu UI scaling
        row += 1
        self.label_ui_scaling = CTkLabel(
            self.tabview_config.tab(config_tab_title_ui),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_ui_scaling.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_ui_scaling = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_ui),
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.optionmenu_ui_scaling_callback,
            variable=StringVar(value=self.parent.UI_SCALING),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_ui_scaling.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown ui scaling
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_ui_scaling = CTkScrollableDropdown(
                self.optionmenu_ui_scaling,
                values=["80%", "90%", "100%", "110%", "120%"],
                justify="left",
                button_color="transparent",
                command=self.optionmenu_ui_scaling_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_ui_scaling.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_ui_scaling._iconify() if not str(e.widget).startswith(str(self.scrollableDropdown_ui_scaling.frame._parent_frame)) else None,
            )

        ## optionmenu font family
        row += 1
        self.label_font_family = CTkLabel(
            self.tabview_config.tab(config_tab_title_ui),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_font_family.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        font_families = list(tk_font.families())
        self.optionmenu_font_family = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_ui),
            values=font_families,
            command=self.optionmenu_font_family_callback,
            variable=StringVar(value=self.parent.FONT_FAMILY),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_font_family.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown font family
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_font_family = CTkScrollableDropdown(
                self.optionmenu_font_family,
                values=font_families,
                justify="left",
                button_color="transparent",
                command=self.optionmenu_font_family_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_font_family.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_font_family._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_font_family.frame._parent_frame)) else None,
            )

        ## optionmenu ui language
        row += 1
        self.label_ui_language = CTkLabel(
            self.tabview_config.tab(config_tab_title_ui),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_ui_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        selectable_languages_values = list(selectable_languages.values())
        self.optionmenu_ui_language = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_ui),
            values=selectable_languages_values,
            command=self.optionmenu_ui_language_callback,
            variable=StringVar(value=selectable_languages[self.parent.UI_LANGUAGE]),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_ui_language.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown ui language
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_ui_language = CTkScrollableDropdown(
                self.optionmenu_ui_language,
                values=selectable_languages_values,
                justify="left",
                button_color="transparent",
                command=self.optionmenu_ui_language_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_ui_language.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_ui_language._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_ui_language.frame._parent_frame)) else None,
            )

        # tab Translation
        ## optionmenu translation translator
        row = 0
        padx = 5
        pady = 1
        self.label_translation_translator = CTkLabel(
            self.tabview_config.tab(config_tab_title_translation),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.label_translation_translator.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_translation_translator = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_translation),
            values=list(self.parent.translator.translator_status.keys()),
            command=self.optionmenu_translation_translator_callback,
            variable=StringVar(value=self.parent.CHOICE_TRANSLATOR),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_translator.grid(row=row, column=1, columnspan=3, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown translation translator
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_translation_translator = CTkScrollableDropdown(
                self.optionmenu_translation_translator,
                values=list(self.parent.translator.translator_status.keys()),
                justify="left",
                button_color="transparent",
                command=self.optionmenu_translation_translator_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_translation_translator.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_translation_translator._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_translation_translator.frame._parent_frame)) else None,
            )

        ## optionmenu translation input language
        row +=1
        self.label_translation_input_language = CTkLabel(
            self.tabview_config.tab(config_tab_title_translation),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_input_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        ## select translation input source language
        self.optionmenu_translation_input_source_language = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_translation),
            command=self.optionmenu_translation_input_source_language_callback,
            values=list(translation_lang[self.parent.CHOICE_TRANSLATOR]["source"].keys()),
            variable=StringVar(value=self.parent.INPUT_SOURCE_LANG),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_input_source_language.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown translation input source language
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_translation_input_source_language = CTkScrollableDropdown(
                self.optionmenu_translation_input_source_language,
                values=list(translation_lang[self.parent.CHOICE_TRANSLATOR]["source"].keys()),
                justify="left",
                button_color="transparent",
                command=self.optionmenu_translation_input_source_language_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_translation_input_source_language.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_translation_input_source_language._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_translation_input_source_language.frame._parent_frame)) else None,
            )

        ## label translation input arrow
        self.label_translation_input_arrow = CTkLabel(
            self.tabview_config.tab(config_tab_title_translation),
            text="-->",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_input_arrow.grid(row=row, column=2, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## select translation input target language
        self.optionmenu_translation_input_target_language = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_translation),
            command=self.optionmenu_translation_input_target_language_callback,
            values=list(translation_lang[self.parent.CHOICE_TRANSLATOR]["target"].keys()),
            variable=StringVar(value=self.parent.INPUT_TARGET_LANG),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_input_target_language.grid(row=row, column=3, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown translation input target language
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_translation_input_target_language = CTkScrollableDropdown(
                self.optionmenu_translation_input_target_language,
                values=list(translation_lang[self.parent.CHOICE_TRANSLATOR]["target"].keys()),
                justify="left",
                button_color="transparent",
                command=self.optionmenu_translation_input_target_language_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_translation_input_target_language.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_translation_input_target_language._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_translation_input_target_language.frame._parent_frame)) else None,
            )

        ## optionmenu translation output language
        row +=1
        self.label_translation_output_language = CTkLabel(
            self.tabview_config.tab(config_tab_title_translation),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_output_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        ## select translation output source language
        self.optionmenu_translation_output_source_language = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_translation),
            command=self.optionmenu_translation_output_source_language_callback,
            values=list(translation_lang[self.parent.CHOICE_TRANSLATOR]["source"].keys()),
            variable=StringVar(value=self.parent.OUTPUT_SOURCE_LANG),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_output_source_language.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown translation output source language
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_translation_output_source_language = CTkScrollableDropdown(
                self.optionmenu_translation_output_source_language,
                values=list(translation_lang[self.parent.CHOICE_TRANSLATOR]["source"].keys()),
                justify="left",
                button_color="transparent",
                command=self.optionmenu_translation_output_source_language_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_translation_output_source_language.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_translation_output_source_language._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_translation_output_source_language.frame._parent_frame)) else None,
            )

        ## label translation output arrow
        self.label_translation_output_arrow = CTkLabel(
            self.tabview_config.tab(config_tab_title_translation),
            text="-->",
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_translation_output_arrow.grid(row=row, column=2, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## select translation output target language
        self.optionmenu_translation_output_target_language = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_translation),
            command=self.optionmenu_translation_output_target_language_callback,
            values=list(translation_lang[self.parent.CHOICE_TRANSLATOR]["target"].keys()),
            variable=StringVar(value=self.parent.OUTPUT_TARGET_LANG),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_translation_output_target_language.grid(row=row, column=3, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown translation output target language
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_translation_output_target_language = CTkScrollableDropdown(
                self.optionmenu_translation_output_target_language,
                values=list(translation_lang[self.parent.CHOICE_TRANSLATOR]["target"].keys()),
                justify="left",
                button_color="transparent",
                command=self.optionmenu_translation_output_target_language_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_translation_output_target_language.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_translation_output_target_language._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_translation_output_target_language.frame._parent_frame)) else None,
            )

        # tab Transcription
        ## optionmenu input mic device's host
        row = 0
        padx = 5
        pady = 1
        self.label_input_mic_host = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_host.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_mic_host = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_transcription),
            values=[host for host in get_input_device_list().keys()],
            command=self.optionmenu_input_mic_host_callback,
            variable=StringVar(value=self.parent.CHOICE_MIC_HOST),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_mic_host.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown input mic device's host
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_input_mic_host = CTkScrollableDropdown(
                self.optionmenu_input_mic_host,
                values=[host for host in get_input_device_list().keys()],
                justify="left",
                button_color="transparent",
                command=self.optionmenu_input_mic_host_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_input_mic_host.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_input_mic_host._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_input_mic_host.frame._parent_frame)) else None,
            )

        ## optionmenu input mic device
        row += 1
        self.label_input_mic_device = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_device.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_mic_device = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_transcription),
            values=[device["name"] for device in get_input_device_list()[self.parent.CHOICE_MIC_HOST]],
            command=self.optionmenu_input_mic_device_callback,
            variable=StringVar(value=self.parent.CHOICE_MIC_DEVICE),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_mic_device.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown input mic device
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_input_mic_device = CTkScrollableDropdown(
                self.optionmenu_input_mic_device,
                values=[device["name"] for device in get_input_device_list()[self.parent.CHOICE_MIC_HOST]],
                justify="left",
                button_color="transparent",
                command=self.optionmenu_input_mic_device_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_input_mic_device.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_input_mic_device._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_input_mic_device.frame._parent_frame)) else None,
            )

        ## optionmenu input mic voice language
        row +=1
        self.label_input_mic_voice_language = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_voice_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_mic_voice_language = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_transcription),
            values=list(transcription_lang.keys()),
            command=self.optionmenu_input_mic_voice_language_callback,
            variable=StringVar(value=self.parent.INPUT_MIC_VOICE_LANGUAGE),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_mic_voice_language.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown input mic voice language
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_input_voice_language = CTkScrollableDropdown(
                self.optionmenu_input_mic_voice_language,
                values=list(transcription_lang.keys()),
                justify="left",
                button_color="transparent",
                command=self.optionmenu_input_mic_voice_language_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_input_voice_language.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_input_voice_language._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_input_voice_language.frame._parent_frame)) else None,
            )

        ## slider input mic energy threshold
        row +=1
        self.label_input_mic_energy_threshold = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        self.slider_input_mic_energy_threshold = CTkSlider(
            self.tabview_config.tab(config_tab_title_transcription),
            from_=0,
            to=self.MAX_MIC_ENERGY_THRESHOLD,
            border_width=7,
            button_length=0,
            button_corner_radius=3,
            number_of_steps=self.MAX_MIC_ENERGY_THRESHOLD,
            command=self.slider_input_mic_energy_threshold_callback,
            variable=IntVar(value=self.parent.INPUT_MIC_ENERGY_THRESHOLD),
        )
        self.slider_input_mic_energy_threshold.grid(row=row, column=1, columnspan=1, padx=0, pady=5, sticky="nsew")

        ## progressBar input mic energy threshold
        row +=1
        self.checkbox_input_mic_threshold_check = CTkCheckBox(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_input_mic_threshold_check_callback,
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_input_mic_threshold_check.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        self.progressBar_input_mic_energy_threshold = CTkProgressBar(
            self.tabview_config.tab(config_tab_title_transcription),
            corner_radius=0
        )
        self.progressBar_input_mic_energy_threshold.grid(row=row, column=1, columnspan=1, padx=padx, pady=5, sticky="nsew")
        self.progressBar_input_mic_energy_threshold.set(0)

        ## checkbox input mic dynamic energy threshold
        row +=1
        self.label_input_mic_dynamic_energy_threshold = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_dynamic_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.checkbox_input_mic_dynamic_energy_threshold = CTkCheckBox(
            self.tabview_config.tab(config_tab_title_transcription),
            text="",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_input_mic_dynamic_energy_threshold_callback,
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_input_mic_dynamic_energy_threshold.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        if  self.parent.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD is True:
            self.checkbox_input_mic_dynamic_energy_threshold.select()
        else:
            self.checkbox_input_mic_dynamic_energy_threshold.deselect()

        ## entry input mic record timeout
        row +=1
        self.label_input_mic_record_timeout = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_record_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_record_timeout = CTkEntry(
            self.tabview_config.tab(config_tab_title_transcription),
            textvariable=StringVar(value=self.parent.INPUT_MIC_RECORD_TIMEOUT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_record_timeout.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_record_timeout.bind("<Any-KeyRelease>", self.entry_input_mic_record_timeout_callback)

        ## entry input mic phrase timeout
        row +=1
        self.label_input_mic_phrase_timeout = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_phrase_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_phrase_timeout = CTkEntry(
            self.tabview_config.tab(config_tab_title_transcription),
            textvariable=StringVar(value=self.parent.INPUT_MIC_PHRASE_TIMEOUT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_phrase_timeout.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_phrase_timeout.bind("<Any-KeyRelease>", self.entry_input_mic_phrase_timeout_callback)

        ## entry input mic max phrases
        row +=1
        self.label_input_mic_max_phrases = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_max_phrases.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_mic_max_phrases = CTkEntry(
            self.tabview_config.tab(config_tab_title_transcription),
            textvariable=StringVar(value=self.parent.INPUT_MIC_MAX_PHRASES),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_max_phrases.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_max_phrases.bind("<Any-KeyRelease>", self.entry_input_mic_max_phrases_callback)

        ## entry input mic word filter
        row +=1
        self.label_input_mic_word_filter = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_mic_word_filter.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        if len(self.parent.INPUT_MIC_WORD_FILTER) > 0:
            textvariable=StringVar(value=",".join(self.parent.INPUT_MIC_WORD_FILTER))
        else:
            textvariable=None
        self.entry_input_mic_word_filter = CTkEntry(
            self.tabview_config.tab(config_tab_title_transcription),
            textvariable=textvariable,
            placeholder_text="AAA,BBB,CCC",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_mic_word_filter.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_input_mic_word_filter.bind("<Any-KeyRelease>", self.entry_input_mic_word_filters_callback)

        ## optionmenu input speaker device
        row +=1
        self.label_input_speaker_device = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_device.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_speaker_device = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_transcription),
            values=[device["name"] for device in get_output_device_list()],
            command=self.optionmenu_input_speaker_device_callback,
            variable=StringVar(value=self.parent.CHOICE_SPEAKER_DEVICE),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_speaker_device.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown input speaker device
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_input_speaker_device = CTkScrollableDropdown(
                self.optionmenu_input_speaker_device,
                values=[device["name"] for device in get_output_device_list()],
                justify="left",
                button_color="transparent",
                command=self.optionmenu_input_speaker_device_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_input_speaker_device.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_input_speaker_device._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_input_speaker_device.frame._parent_frame)) else None,
            )

        ## optionmenu input speaker voice language
        row +=1
        self.label_input_speaker_voice_language = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_voice_language.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.optionmenu_input_speaker_voice_language = CTkOptionMenu(
            self.tabview_config.tab(config_tab_title_transcription),
            values=list(transcription_lang.keys()),
            command=self.optionmenu_input_speaker_voice_language_callback,
            variable=StringVar(value=self.parent.INPUT_SPEAKER_VOICE_LANGUAGE),
            font=CTkFont(family=self.parent.FONT_FAMILY),
            dropdown_font=CTkFont(family=self.parent.FONT_FAMILY),
        )
        self.optionmenu_input_speaker_voice_language.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")

        ## scrollableDropdown input speaker voice language
        if SCROLLABLE_DROPDOWN:
            self.scrollableDropdown_input_speaker_voice_language = CTkScrollableDropdown(
                self.optionmenu_input_speaker_voice_language,
                values=list(transcription_lang.keys()),
                justify="left",
                button_color="transparent",
                command=self.optionmenu_input_speaker_voice_language_callback,
                font=CTkFont(family=self.parent.FONT_FAMILY),
            )
            self.scrollableDropdown_input_speaker_voice_language.bind(
                "<Leave>",
                lambda e: self.scrollableDropdown_input_speaker_voice_language._withdraw() if not str(e.widget).startswith(str(self.scrollableDropdown_input_speaker_voice_language.frame._parent_frame)) else None,
            )

        ## entry input speaker energy threshold
        row +=1
        self.label_input_speaker_energy_threshold = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        ## progressBar input speaker energy threshold
        self.slider_input_speaker_energy_threshold = CTkSlider(
            self.tabview_config.tab(config_tab_title_transcription),
            from_=0,
            to=self.MAX_SPEAKER_ENERGY_THRESHOLD,
            border_width=7,
            button_length=0,
            button_corner_radius=3,
            number_of_steps=self.MAX_SPEAKER_ENERGY_THRESHOLD,
            command=self.slider_input_speaker_energy_threshold_callback,
            variable=IntVar(value=self.parent.INPUT_SPEAKER_ENERGY_THRESHOLD),
        )
        self.slider_input_speaker_energy_threshold.grid(row=row, column=1, columnspan=1, padx=0, pady=5, sticky="nsew")

        ## progressBar input speaker energy threshold
        row +=1
        self.checkbox_input_speaker_threshold_check = CTkCheckBox(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            onvalue=True,
            offvalue=False,
            command=self.checkbox_input_speaker_threshold_check_callback,
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_input_speaker_threshold_check.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")

        self.progressBar_input_speaker_energy_threshold = CTkProgressBar(
            self.tabview_config.tab(config_tab_title_transcription),
            corner_radius=0
        )
        self.progressBar_input_speaker_energy_threshold.grid(row=row, column=1, columnspan=1, padx=padx, pady=5, sticky="nsew")
        self.progressBar_input_speaker_energy_threshold.set(0)

        ## checkbox input speaker dynamic energy threshold
        row +=1
        self.label_input_speaker_dynamic_energy_threshold = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_dynamic_energy_threshold.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.checkbox_input_speaker_dynamic_energy_threshold = CTkCheckBox(
            self.tabview_config.tab(config_tab_title_transcription),
            text="",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_input_speaker_dynamic_energy_threshold_callback,
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_input_speaker_dynamic_energy_threshold.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        if  self.parent.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD is True:
            self.checkbox_input_speaker_dynamic_energy_threshold.select()
        else:
            self.checkbox_input_speaker_dynamic_energy_threshold.deselect()

        ## entry input speaker record timeout
        row +=1
        self.label_input_speaker_record_timeout = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_record_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_record_timeout = CTkEntry(
            self.tabview_config.tab(config_tab_title_transcription),
            textvariable=StringVar(value=self.parent.INPUT_SPEAKER_RECORD_TIMEOUT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_record_timeout.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_record_timeout.bind("<Any-KeyRelease>", self.entry_input_speaker_record_timeout_callback)

        ## entry input speaker phrase timeout
        row +=1
        self.label_input_speaker_phrase_timeout = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_phrase_timeout.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_phrase_timeout = CTkEntry(
            self.tabview_config.tab(config_tab_title_transcription),
            textvariable=StringVar(value=self.parent.INPUT_SPEAKER_PHRASE_TIMEOUT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_phrase_timeout.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_phrase_timeout.bind("<Any-KeyRelease>", self.entry_input_speaker_phrase_timeout_callback)

        ## entry input speaker max phrases
        row +=1
        self.label_input_speaker_max_phrases = CTkLabel(
            self.tabview_config.tab(config_tab_title_transcription),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_input_speaker_max_phrases.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_input_speaker_max_phrases = CTkEntry(
            self.tabview_config.tab(config_tab_title_transcription),
            textvariable=StringVar(value=self.parent.INPUT_SPEAKER_MAX_PHRASES),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_input_speaker_max_phrases.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_input_speaker_max_phrases.bind("<Any-KeyRelease>", self.entry_input_speaker_max_phrases_callback)

        # tab Parameter
        ## entry ip address
        row = 0
        padx = 5
        pady = 1
        self.label_ip_address = CTkLabel(
            self.tabview_config.tab(config_tab_title_parameter),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_ip_address.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_ip_address = CTkEntry(
            self.tabview_config.tab(config_tab_title_parameter),
            textvariable=StringVar(value=self.parent.OSC_IP_ADDRESS),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_ip_address.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_ip_address.bind("<Any-KeyRelease>", self.entry_ip_address_callback)

        ## entry port
        row +=1
        self.label_port = CTkLabel(
            self.tabview_config.tab(config_tab_title_parameter),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_port.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_port = CTkEntry(
            self.tabview_config.tab(config_tab_title_parameter),
            textvariable=StringVar(value=self.parent.OSC_PORT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_port.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_port.bind("<Any-KeyRelease>", self.entry_port_callback)

        ## entry authkey
        row +=1
        self.label_authkey = CTkLabel(
            self.tabview_config.tab(config_tab_title_parameter),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_authkey.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_authkey = CTkEntry(
            self.tabview_config.tab(config_tab_title_parameter),
            textvariable=StringVar(value=self.parent.AUTH_KEYS["DeepL(auth)"]),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_authkey.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_authkey.bind("<Any-KeyRelease>", self.entry_authkey_callback)

        ## entry message format
        row +=1
        self.label_message_format = CTkLabel(
            self.tabview_config.tab(config_tab_title_parameter),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_message_format.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.entry_message_format = CTkEntry(
            self.tabview_config.tab(config_tab_title_parameter),
            textvariable=StringVar(value=self.parent.MESSAGE_FORMAT),
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.entry_message_format.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        self.entry_message_format.bind("<Any-KeyRelease>", self.entry_message_format_callback)

        # tab Others
        ## checkbox auto clear chat box
        row = 0
        self.label_checkbox_auto_clear_chatbox = CTkLabel(
            self.tabview_config.tab(config_tab_title_others),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_checkbox_auto_clear_chatbox.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.checkbox_auto_clear_chatbox = CTkCheckBox(
            self.tabview_config.tab(config_tab_title_others),
            text="",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_auto_clear_chatbox_callback,
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_auto_clear_chatbox.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        if  self.parent.ENABLE_AUTO_CLEAR_CHATBOX is True:
            self.checkbox_auto_clear_chatbox.select()
        else:
            self.checkbox_auto_clear_chatbox.deselect()

        # checkbox notice xsoverlay
        row += 1
        self.label_checkbox_notice_xsoverlay = CTkLabel(
            self.tabview_config.tab(config_tab_title_others),
            text=init_lang_text,
            fg_color="transparent",
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.label_checkbox_notice_xsoverlay.grid(row=row, column=0, columnspan=1, padx=padx, pady=pady, sticky="nsw")
        self.checkbox_notice_xsoverlay = CTkCheckBox(
            self.tabview_config.tab(config_tab_title_others),
            text="",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_notice_xsoverlay_callback,
            font=CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.checkbox_notice_xsoverlay.grid(row=row, column=1, columnspan=1, padx=padx, pady=pady, sticky="nsew")
        if  self.parent.ENABLE_NOTICE_XSOVERLAY is True:
            self.checkbox_notice_xsoverlay.select()
        else:
            self.checkbox_notice_xsoverlay.deselect()
        widget_config_window_label_setter(self, language_yaml_data)