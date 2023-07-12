from json import load, dump
from os import path as os_path
import yaml
from datetime import datetime
from threading import Thread, Event

def save_json(path, key, value):
    with open(path, "r") as fp:
        json_data = load(fp)
    json_data[key] = value
    with open(path, "w") as fp:
        dump(json_data, fp, indent=4)

def print_textbox(textbox, message, tags=None):
    now = datetime.now()
    now = now.strftime('%H:%M:%S')

    textbox.tag_config("ERROR", foreground="#FF0000")
    textbox.tag_config("INFO", foreground="#1BFF00")
    textbox.tag_config("SEND", foreground="#0378e2")
    textbox.tag_config("RECEIVE", foreground="#ffa500")

    textbox.configure(state='normal')
    textbox.insert("end", f"[{now}][")
    textbox.insert("end", f"{tags}", tags)
    textbox.insert("end", f"]{message}\n")
    textbox.configure(state='disabled')
    textbox.see("end")

class thread_fnc(Thread):
    def __init__(self, fnc, daemon=True, *args, **kwargs):
        super(thread_fnc, self).__init__(daemon=daemon, *args, **kwargs)
        self.fnc = fnc
        self._stop = Event()
    def stop(self):
        self._stop.set()
    def stopped(self):
        return self._stop.isSet()
    def run(self):
        while True:
            if self.stopped():
                return
            self.fnc(*self._args, **self._kwargs)

def get_localized_text(language):
    file_path = os_path.join(os_path.dirname(__file__), "locales.yml")

    with open(file_path, encoding="utf-8") as file:
        languages_yaml_data = yaml.safe_load(file)
    default_language = "en"
    if language in languages_yaml_data:
        localized_text = languages_yaml_data[language]
        if default_language in languages_yaml_data:
            default_text = languages_yaml_data[default_language]
            merged_text = {**default_text, **localized_text}
            return merged_text
        else:
            return localized_text
    else:
        return None
    
def get_key_by_value(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None

def widget_config_window_label_setter(self, language_yaml_data):
    widget_names = [
        # tab UI
        "label_transparency",
        "label_appearance_theme",
        "label_ui_scaling",
        "label_font_family",
        "label_ui_language",

        # tab Translation
        "label_translation_translator",
        "label_translation_input_language",
        "label_translation_output_language",

        # tab Transcription
        "label_input_mic_host",
        "label_input_mic_device",
        "label_input_mic_voice_language",
        "label_input_mic_energy_threshold",
        "checkbox_input_mic_threshold_check",
        "label_input_mic_dynamic_energy_threshold",
        "label_input_mic_record_timeout",
        "label_input_mic_phrase_timeout",
        "label_input_mic_max_phrases",
        "label_input_mic_word_filter",

        "label_input_speaker_device",
        "label_input_speaker_voice_language",
        "label_input_speaker_energy_threshold",
        "checkbox_input_speaker_threshold_check",
        "label_input_speaker_dynamic_energy_threshold",
        "label_input_speaker_record_timeout",
        "label_input_speaker_phrase_timeout",
        "label_input_speaker_max_phrases",

        
        # tab Parameter
        "label_ip_address",
        "label_port",
        "label_authkey",
        "label_message_format",
    
        # tab Others
        "label_checkbox_auto_clear_chatbox"
    ]
    for name in widget_names:
        widget = getattr(self, name)
        text_value = language_yaml_data.get(name)
        if widget is not None and text_value is not None:
            widget.configure(text=text_value + ":")

def widget_main_window_label_setter(self, language_yaml_data):
    widget_names = [
        "checkbox_translation",
        "checkbox_transcription_send",
        "checkbox_transcription_receive",
        "checkbox_foreground",
    ]
    for name in widget_names:
        widget = getattr(self, name)
        text_value = language_yaml_data.get(name)
        if widget is not None and text_value is not None:
            widget.configure(text=text_value)