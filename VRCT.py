import os
import json
import threading
import deepl
import deepl_translate
import translators as ts
from pythonosc import osc_message_builder
from pythonosc import udp_client
import tkinter as tk
import customtkinter
from PIL import Image
import pyaudio
import speech_recognition as sr

def save_json(path, key, value):
    with open(path, "r") as fp:
        json_data = json.load(fp)
    json_data[key] = value
    with open(path, "w") as fp:
        json.dump(json_data, fp, indent=4)

# Translator
class Translator():
    def __init__(self):
        self.translator_status = {
            "DeepL(web)": False,
            "DeepL(auth)": False,
            "Google(web)": False,
            "Bing(web)": False,
        }
        self.languages = {}
        self.languages["DeepL(web)"] = [
            "JA","EN","BG","ZH","CS","DA","NL","ET","FI","FR","DE","EL","HU","IT",
            "LV","LT","PL","PT","RO","RU","SK","SL","ES","SV",
        ]
        self.languages["DeepL(auth)"] = [
            "JA","EN-US","EN-GB","BG","CS","DA","DE","EL","ES","ET","FI","FR","HU",
            "ID","IT","KO","LT","LV","NB","NL","PL","PT","PT-BR","PT-PT","RO","RU",
            "SK","SL","SV","TR","UK","ZH",
        ]
        self.languages["Google(web)"] = [
            "ja","en","zh","ar","ru","fr","de","es","pt","it","ko","el","nl","hi",
            "tr","ms","th","vi","id","he","pl","mn","cs","hu","et","bg","da","fi",
            "ro","sv","sl","fa","bs","sr","tl","ht","ca","hr","lv","lt","ur","uk",
            "cy","sw","sm","sk","af","no","bn","mg","mt","gu","ta","te","pa","am",
            "az","be","ceb","eo","eu","ga"
        ]
        self.languages["Bing(web)"] = [
            "ja","en","zh","ar","ru","fr","de","es","pt","it","ko","el","nl","hi",
            "tr","ms","th","vi","id","he","pl","cs","hu","et","bg","da","fi","ro",
            "sv","sl","fa","bs","sr","fj","tl","ht","ca","hr","lv","lt","ur","uk",
            "cy","ty","to","sw","sm","sk","af","no","bn","mg","mt","otq","tlh","gu",
            "ta","te","pa","ga"
        ]
        self.deepl_client = None

    def authentication(self, translator_name, authkey=None):
        result = False
        try:
            if translator_name == "DeepL(web)":
                self.translator_status["DeepL(web)"] = True
                result = True
            elif translator_name == "DeepL(auth)":
                self.deepl_client = deepl.Translator(authkey)
                self.deepl_client.translate_text(" ", target_lang="EN-US")
                self.translator_status["DeepL(auth)"] = True
                result = True
            elif translator_name == "Google(web)":
                self.translator_status["Google(web)"] = True
                result = True
            elif translator_name == "Bing(web)":
                self.translator_status["Bing(web)"] = True
                result = True
        except:
            pass
        return result

    def translate(self, translator_name, source_language, target_language, message):
        result = False
        try:
            if translator_name == "DeepL(web)":
                result = deepl_translate.translate(source_language=source_language, target_language=target_language, text=message)
            elif translator_name == "DeepL(auth)":
                result = self.deepl_client.translate_text(message, source_lang=source_language, target_lang=target_language).text
            elif translator_name == "Google(web)":
                result = ts.translate_text(query_text=message, translator="google", from_language=source_language, to_language=target_language)
            elif translator_name == "Bing(web)":
                result = ts.translate_text(query_text=message, translator="bing", from_language=source_language, to_language=target_language)
        except:
            pass
        return result

# VoiceRecognizer
class VoiceRecognizer():
    def __init__(self):
        self.input_device_dict = self.search_input_device()
        self.r = sr.Recognizer()
        self.mic = None
        self.languages = [
            "ja-JP","en-US","en-GB","af-ZA","ar-DZ","ar-BH","ar-EG","ar-IL","ar-IQ","ar-JO","ar-KW","ar-LB","ar-MA",
            "ar-OM","ar-PS","ar-QA","ar-SA","ar-TN","ar-AE","eu-ES","bg-BG","ca-ES","cmn-Hans-CN","cmn-Hans-HK",
            "cmn-Hant-TW","yue-Hant-HK","hr_HR","cs-CZ","da-DK","en-AU","en-CA","en-IN","en-IE","en-NZ","en-PH",
            "en-ZA","fa-IR","fr-FR","fil-PH","gl-ES","de-DE","el-GR","fi-FI","he-IL","hi-IN","hu-HU","id-ID","is-IS",
            "it-IT","it-CH","ko-KR","lt-LT","ms-MY","nl-NL","nb-NO","pl-PL","pt-BR","pt-PT","ro-RO","ru-RU","sr-RS",
            "sk-SK","sl-SI","es-AR","es-BO","es-CL","es-CO","es-CR","es-DO","es-EC","es-SV","es-GT","es-HN","es-MX",
            "es-NI","es-PA","es-PY","es-PE","es-PR","es-ES","es-UY","es-US","es-VE","sv-SE","th-TH","tr-TR","uk-UA",
            "vi-VN","zu-ZA"
        ]

    def search_input_device(self):
        pa = pyaudio.PyAudio()
        input_device_dict = {}

        mic_cnt = 1
        for i in range(pa.get_device_count()):
            device = pa.get_device_info_by_index(i)
            try:
                device["name"] = device["name"].encode('shift_jis').decode('utf-8')
            except:
                device["name"] = device["name"].encode('utf-8').decode('utf-8')
            if device["maxInputChannels"] > 0:
                input_device_dict[f'No.{mic_cnt}:{device["name"]}'] = device["index"]
                mic_cnt += 1
        pa.terminate()
        return input_device_dict

    def set_mic(self, device_name, threshold=50, is_dynamic=False):
        if device_name in [v for v in self.input_device_dict.keys()]:
            index = self.input_device_dict[device_name]
            self.mic = sr.Microphone(device_index=index)
            self.r.energy_threshold = threshold
            if is_dynamic:
                with self.mic as source:
                    self.r.adjust_for_ambient_noise(source, 3.0)
            return True
        else:
            return False

    def init_mic(self, threshold=50, is_dynamic=False):
        if isinstance(self.mic, sr.Microphone):
            self.r.energy_threshold = threshold
            if is_dynamic:
                with self.mic as source:
                    self.r.adjust_for_ambient_noise(source, 3.0)
            return True
        else:
            return False

    def listen_voice(self, language):
        if self.mic != None:
            with self.mic as source:
                audio = self.r.listen(source)
            try:
                text = self.r.recognize_google(audio, language=language)
                return text
            except:
                return ""
        else:
            return False

class ToplevelWindowInformation(customtkinter.CTkToplevel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        # self.geometry(f"{500}x{300}")
        self.minsize(500, 300)

        self.after(200, lambda: self.iconbitmap(os.path.join(os.path.dirname(__file__), "img", "app.ico")))
        self.title("Information")
        # create textbox information
        self.textbox_information = customtkinter.CTkTextbox(
            self,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY)
        )
        self.textbox_information.grid(row=0, column=0, padx=(10, 10), pady=(10, 10), sticky="nsew")
        textbox_information_message = """VRCT(v0.4b)

# 概要
VRChatで使用されるChatBoxをOSC経由でメッセージを送信するツールになります。
翻訳エンジンを使用してメッセージとその翻訳部分を同時に送信することができます。
(翻訳エンジンはDeepL,Google,Bingに対応)

# 使用方法
    初期設定時
        0. VRChatのOSCを有効にする（重要）

        (任意)
        1. DeepLのAPIを使用するためにアカウント登録し、認証キーを取得する
        2. ギアアイコンのボタンでconfigウィンドウを開く
        3. ParameterタブのDeepL Auth Keyに認証キーを記載し、フロッピーアイコンのボタンを押す
        4. configウィンドウを閉じる

    通常使用時
        1. メッセージボックスにメッセージを記入
        2. Enterキーを押し、メッセージを送信する

# その他の設定
    translation チェックボックス: 翻訳の有効無効
    foreground チェックボックス: 最前面表示の有効無効

    configウィンドウ
        UIタブ
            Select translator: 翻訳エンジンの変更
            Select Language: 翻訳する言語[source, target]を選択
            Transparency: ウィンドウの透過度の調整
            Appearance Theme: ウィンドウテーマを選択
            UI Scaling: UIサイズを調整
            Font Family: 表示フォントを選択
        Parameterタブ
            OSC IP address: 変更不要
            OSC port: 変更不要
            DeepL Auth key: DeepLの認証キーの設定
            Message Format: 送信するメッセージのデコレーションの設定
                [message]がメッセージボックスに記入したメッセージに置換される
                [translation]が翻訳されたメッセージに置換される
                初期フォーマット:"[message]([translation])"

    設定の初期化
        config.jsonを削除

# お問い合わせ
要望などはTwitterまで
https://twitter.com/misya_ai

# アップデート履歴
[2023-05-29: v0.1b] v0.1b リリース
[2023-05-30: v0.2b]
- configボタンをギアアイコンに変更
- 詳細情報のボタンを追加
- 翻訳機能有効無効のチェックボックスを追加
- 最前面表示の有効無効のチェックボックスを追加
- いくつかのバグを修正
[2023-06-03: v0.3b]
- 全体的にUIを刷新
- 透過機能を追加
- テーマのLight/Dark/Systemのモードの変更機能を追加
- UIのスケール変更機能を追加
- フォントの変更機能を追加
[2023-06-06: v0.4b]
- 翻訳エンジンを追加
- 入力と出力の翻訳言語を選択できるように変更

# 注意事項
再配布とかはやめてね
"""

        self.textbox_information.insert("end", textbox_information_message)
        self.textbox_information.configure(state='disabled')

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
            values=list(self.parent.vr.input_device_dict.keys()),
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
        if  self.parent.ENABLE_MIC_IS_DYNAMIC is True:
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
            variable=tk.DoubleVar(value=self.parent.MIC_THRESHOLD),
        )
        self.slider_input_mic_threshold.grid(row=3, column=1, columnspan=3 ,padx=5, pady=10, sticky="nsew")

        ## optionmenu input speaker device
        self.label_input_speaker_device = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Device:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY, overstrike=True)
        )
        self.label_input_speaker_device.grid(row=4, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.optionmenu_input_speaker_device = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=list(self.parent.vr.input_device_dict.keys()),
            # command=self.optionmenu_input_speaker_device_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            variable=customtkinter.StringVar(value=self.parent.CHOICE_SPEAKER_DEVICE),
            state="disabled"
        )
        self.optionmenu_input_speaker_device.grid(row=4, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")

        ## optionmenu input speaker voice language
        self.label_input_speaker_voice_language = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Voice Language:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY, overstrike=True)
        )
        self.label_input_speaker_voice_language.grid(row=5, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.optionmenu_input_speaker_voice_language = customtkinter.CTkOptionMenu(
            self.tabview_config.tab("Transcription"),
            values=list(self.parent.vr.languages),
            # command=self.optionmenu_input_speaker_voice_language_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            variable=customtkinter.StringVar(value=self.parent.INPUT_SPEAKER_VOICE_LANGUAGE),
            state="disabled"
        )
        self.optionmenu_input_speaker_voice_language.grid(row=5, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")

        ## checkbox input speaker in dynamic
        self.label_input_speaker_is_dynamic = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker IsDynamic:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY, overstrike=True)
        )
        self.label_input_speaker_is_dynamic.grid(row=6, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.checkbox_input_speaker_is_dynamic = customtkinter.CTkCheckBox(
            self.tabview_config.tab("Transcription"),
            text="",
            onvalue=True,
            offvalue=False,
            # command=self.checkbox_input_speaker_is_dynamic_callback,
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY),
            state="disabled"
        )
        self.checkbox_input_speaker_is_dynamic.grid(row=6, column=1, columnspan=3 ,padx=5, pady=5, sticky="nsew")
        if  self.parent.ENABLE_SPEAKER_IS_DYNAMIC is True:
            self.checkbox_input_speaker_is_dynamic.select()
        else:
            self.checkbox_input_speaker_is_dynamic.deselect()

        ## slider input speaker threshold
        self.label_input_speaker_threshold = customtkinter.CTkLabel(
            self.tabview_config.tab("Transcription"),
            text="Input Speaker Threshold:",
            fg_color="transparent",
            font=customtkinter.CTkFont(family=self.parent.FONT_FAMILY, overstrike=True)
        )
        self.label_input_speaker_threshold.grid(row=7, column=0, columnspan=1, padx=5, pady=5, sticky="nsw")
        self.slider_input_speaker_threshold = customtkinter.CTkSlider(
            self.tabview_config.tab("Transcription"),
            from_=0,
            to=300,
            # command=self.slider_input_speaker_threshold_callback,
            variable=tk.DoubleVar(value=self.parent.SPEAKER_THRESHOLD),
            state="disabled"
        )
        self.slider_input_speaker_threshold.grid(row=7, column=1, columnspan=3 ,padx=5, pady=10, sticky="nsew")

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
        # self.label_translation_output_language.configure(font=customtkinter.CTkFont(family=choice))
        # self.optionmenu_translation_output_source_language.configure(font=customtkinter.CTkFont(family=choice))
        # self.label_translation_output_arrow.configure(font=customtkinter.CTkFont(family=choice))
        # self.optionmenu_translation_output_target_language.configure(font=customtkinter.CTkFont(family=choice))

        # tab Transcription
        self.label_input_mic_device.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_mic_device.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.optionmenu_input_mic_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_is_dynamic.configure(font=customtkinter.CTkFont(family=choice))
        self.label_input_mic_threshold.configure(font=customtkinter.CTkFont(family=choice))
        # self.label_input_speaker_device.configure(font=customtkinter.CTkFont(family=choice))
        # self.optionmenu_input_speaker_device.configure(font=customtkinter.CTkFont(family=choice))
        # self.label_input_speaker_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        # self.optionmenu_input_speaker_voice_language.configure(font=customtkinter.CTkFont(family=choice))
        # self.label_input_speaker_is_dynamic.configure(font=customtkinter.CTkFont(family=choice))
        # self.label_input_speaker_threshold.configure(font=customtkinter.CTkFont(family=choice))

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
        self.parent.checkbox_foreground.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.textbox_message_log.configure(font=customtkinter.CTkFont(family=choice))
        self.parent.entry_message_box.configure(font=customtkinter.CTkFont(family=choice))

        # window information
        try:
            self.parent.information_window.textbox_information.configure(font=customtkinter.CTkFont(family=choice))
        except:
            pass

        self.parent.FONT_FAMILY = choice
        save_json(self.parent.PATH_CONFIG, "FONT_FAMILY", self.parent.FONT_FAMILY)

    def optionmenu_translation_translator_callback(self, choice):
        if self.parent.translator.authentication(choice, self.parent.AUTH_KEYS[choice]) is False:
            self.parent.textbox_message_log.configure(state='normal')
            self.parent.textbox_message_log.insert("end", f"[ERROR]Auth Keyを設定してないか間違っています\n")
            self.parent.textbox_message_log.configure(state='disabled')
            self.parent.textbox_message_log.see("end")
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
            save_json(self.parent.PATH_CONFIG, "CHOICE_TRANSLATOR", self.parent.CHOICE_TRANSLATOR)
            save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)
            save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)

    def optionmenu_translation_input_source_language_callback(self, choice):
        self.parent.INPUT_SOURCE_LANG = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_SOURCE_LANG", self.parent.INPUT_SOURCE_LANG)

    def optionmenu_translation_input_target_language_callback(self, choice):
        self.parent.INPUT_TARGET_LANG = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_TARGET_LANG", self.parent.INPUT_TARGET_LANG)

    def optionmenu_input_mic_device_callback(self, choice):
        self.parent.CHOICE_MIC_DEVICE = choice
        save_json(self.parent.PATH_CONFIG, "CHOICE_MIC_DEVICE", self.parent.CHOICE_MIC_DEVICE)

    def optionmenu_input_mic_voice_language_callback(self, choice):
        self.parent.INPUT_MIC_VOICE_LANGUAGE = choice
        save_json(self.parent.PATH_CONFIG, "INPUT_MIC_VOICE_LANGUAGE", self.parent.INPUT_MIC_VOICE_LANGUAGE)

    def checkbox_input_mic_is_dynamic_callback(self):
        value = self.checkbox_input_mic_is_dynamic.get()
        self.parent.ENABLE_MIC_IS_DYNAMIC = value
        save_json(self.parent.PATH_CONFIG, "ENABLE_MIC_IS_DYNAMIC", self.parent.ENABLE_MIC_IS_DYNAMIC)
        self.parent.vr.init_mic(threshold=self.parent.MIC_THRESHOLD, is_dynamic=self.parent.ENABLE_MIC_IS_DYNAMIC)

    def slider_input_mic_threshold_callback(self, value):
        self.parent.MIC_THRESHOLD = value
        save_json(self.parent.PATH_CONFIG, "MIC_THRESHOLD", self.parent.MIC_THRESHOLD)
        self.parent.vr.init_mic(threshold=self.parent.MIC_THRESHOLD, is_dynamic=self.parent.ENABLE_MIC_IS_DYNAMIC)

    def update_ip_address(self):
        value = self.entry_ip_address.get()
        if len(value) > 0:
            self.parent.OSC_IP_ADDRESS = value
            save_json(self.parent.PATH_CONFIG, "OSC_IP_ADDRESS", self.parent.OSC_IP_ADDRESS)

    def update_port(self):
        value = self.entry_port.get()
        if len(value) > 0:
            self.parent.OSC_PORT = value
            save_json(self.parent.PATH_CONFIG, "OSC_PORT", self.parent.OSC_PORT)

    def update_authkey(self):
        value = self.entry_authkey.get()
        if len(value) > 0:
            self.parent.textbox_message_log.configure(state='normal')
            self.parent.textbox_message_log.delete("0.0", "end")
            self.parent.textbox_message_log.configure(state='disabled')
            self.parent.textbox_message_log.see("end")

            if self.parent.translator.authentication(self.parent.CHOICE_TRANSLATOR, self.parent.AUTH_KEYS[self.parent.CHOICE_TRANSLATOR]) is True:
                self.parent.AUTH_KEYS["DeepL(auth)"] = value
                save_json(self.parent.PATH_CONFIG, "AUTH_KEYS", self.parent.AUTH_KEYS)
            else:
                self.parent.textbox_message_log.configure(state='normal')
                self.parent.textbox_message_log.insert("end", f"[ERROR]Auth Keyを設定してないか間違っています\n")
                self.parent.textbox_message_log.configure(state='disabled')
                self.parent.textbox_message_log.see("end")

    def update_message_format(self):
        value = self.entry_message_format.get()
        if len(value) > 0:
            self.parent.MESSAGE_FORMAT = value
            save_json(self.parent.PATH_CONFIG, "MESSAGE_FORMAT", self.parent.MESSAGE_FORMAT)

class App(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # init config
        self.PATH_CONFIG = "./config.json"
        ## main window
        self.ENABLE_TRANSLATION = False
        self.ENABLE_TRANSCRIPTION = False
        self.ENABLE_FOREGROUND = False
        ## UI
        self.TRANSPARENCY = 100
        self.APPEARANCE_THEME = "System"
        self.UI_SCALING = "100%"
        self.FONT_FAMILY = "Yu Gothic UI"
        ## Translation
        self.CHOICE_TRANSLATOR = "DeepL(web)"
        self.INPUT_SOURCE_LANG = "JA"
        self.INPUT_TARGET_LANG = "EN"
        self.OUTPUT_SOURCE_LANG = "JA"
        self.OUTPUT_TARGET_LANG = "EN"
        ## Transcription
        self.CHOICE_MIC_DEVICE = None
        self.INPUT_MIC_VOICE_LANGUAGE = "ja-JP"
        self.ENABLE_MIC_IS_DYNAMIC = False
        self.MIC_THRESHOLD = 300
        self.CHOICE_SPEAKER_DEVICE = None
        self.INPUT_SPEAKER_VOICE_LANGUAGE = "ja-JP"
        self.ENABLE_SPEAKER_IS_DYNAMIC = False
        self.SPEAKER_THRESHOLD = 300
        ## Parameter
        self.OSC_IP_ADDRESS = "127.0.0.1"
        self.OSC_PORT = 9000
        self.AUTH_KEYS = {
            "DeepL(web)": None,
            "DeepL(auth)": None,
            "Bing(web)": None,
            "Google(web)": None,
        }
        self.MESSAGE_FORMAT = "[message]([translation])"

        # load config
        if os.path.isfile(self.PATH_CONFIG) is not False:
            with open(self.PATH_CONFIG, 'r') as fp:
                config = json.load(fp)
            # main window
            if "ENABLE_TRANSLATION" in config.keys():
                self.ENABLE_TRANSLATION = config["ENABLE_TRANSLATION"]
            if "ENABLE_TRANSCRIPTION" in config.keys():
                self.ENABLE_TRANSCRIPTION = config["ENABLE_TRANSCRIPTION"]
            if "ENABLE_FOREGROUND" in config.keys():
                self.ENABLE_FOREGROUND = config["ENABLE_FOREGROUND"]

            # tab ui
            if "TRANSPARENCY" in config.keys():
                self.TRANSPARENCY = config["TRANSPARENCY"]
            if "APPEARANCE_THEME" in config.keys():
                self.APPEARANCE_THEME = config["APPEARANCE_THEME"]
            if "UI_SCALING" in config.keys():
                self.UI_SCALING = config["UI_SCALING"]
            if "FONT_FAMILY" in config.keys():
                self.FONT_FAMILY = config["FONT_FAMILY"]

            # translation
            if "CHOICE_TRANSLATOR" in config.keys():
                self.CHOICE_TRANSLATOR = config["CHOICE_TRANSLATOR"]
            if "INPUT_SOURCE_LANG" in config.keys():
                self.INPUT_SOURCE_LANG = config["INPUT_SOURCE_LANG"]
            if "INPUT_TARGET_LANG" in config.keys():
                self.INPUT_TARGET_LANG = config["INPUT_TARGET_LANG"]
            if "OUTPUT_SOURCE_LANG" in config.keys():
                self.OUTPUT_SOURCE_LANG = config["OUTPUT_SOURCE_LANG"]
            if "OUTPUT_TARGET_LANG" in config.keys():
                self.OUTPUT_TARGET_LANG = config["OUTPUT_TARGET_LANG"]

            # Transcription
            if "CHOICE_MIC_DEVICE" in config.keys():
                self.CHOICE_MIC_DEVICE = config["CHOICE_MIC_DEVICE"]
            if "INPUT_MIC_VOICE_LANGUAGE" in config.keys():
                self.INPUT_MIC_VOICE_LANGUAGE = config["INPUT_MIC_VOICE_LANGUAGE"]
            if "ENABLE_MIC_IS_DYNAMIC" in config.keys():
                self.ENABLE_MIC_IS_DYNAMIC = config["ENABLE_MIC_IS_DYNAMIC"]
            if "MIC_THRESHOLD" in config.keys():
                self.MIC_THRESHOLD = config["MIC_THRESHOLD"]
            if "CHOICE_SPEAKER_DEVICE" in config.keys():
                self.CHOICE_SPEAKER_DEVICE = config["CHOICE_SPEAKER_DEVICE"]
            if "INPUT_SPEAKER_VOICE_LANGUAGE" in config.keys():
                self.INPUT_SPEAKER_VOICE_LANGUAGE = config["INPUT_SPEAKER_VOICE_LANGUAGE"]
            if "ENABLE_SPEAKER_IS_DYNAMIC" in config.keys():
                self.ENABLE_SPEAKER_IS_DYNAMIC = config["ENABLE_SPEAKER_IS_DYNAMIC"]
            if "SPEAKER_THRESHOLD" in config.keys():
                self.SPEAKER_THRESHOLD = config["SPEAKER_THRESHOLD"]

            # Parameter
            if "OSC_IP_ADDRESS" in config.keys():
                self.OSC_IP_ADDRESS = config["OSC_IP_ADDRESS"]
            if "OSC_PORT" in config.keys():
                self.OSC_PORT = config["OSC_PORT"]
            if "AUTH_KEYS" in config.keys():
                self.AUTH_KEYS = config["AUTH_KEYS"]
            if "MESSAGE_FORMAT" in config.keys():
                self.MESSAGE_FORMAT = config["MESSAGE_FORMAT"]

        with open(self.PATH_CONFIG, 'w') as fp:
            config = {
                "ENABLE_TRANSLATION": self.ENABLE_TRANSLATION,
                "ENABLE_TRANSCRIPTION": self.ENABLE_TRANSCRIPTION,
                "ENABLE_FOREGROUND": self.ENABLE_FOREGROUND,
                "TRANSPARENCY": self.TRANSPARENCY,
                "APPEARANCE_THEME": self.APPEARANCE_THEME,
                "UI_SCALING": self.UI_SCALING,
                "FONT_FAMILY": self.FONT_FAMILY,
                "CHOICE_TRANSLATOR": self.CHOICE_TRANSLATOR,
                "INPUT_SOURCE_LANG": self.INPUT_SOURCE_LANG,
                "INPUT_TARGET_LANG": self.INPUT_TARGET_LANG,
                "OUTPUT_SOURCE_LANG": self.OUTPUT_SOURCE_LANG,
                "OUTPUT_TARGET_LANG": self.OUTPUT_TARGET_LANG,
                "CHOICE_MIC_DEVICE": self.CHOICE_MIC_DEVICE,
                "INPUT_MIC_VOICE_LANGUAGE": self.INPUT_MIC_VOICE_LANGUAGE,
                "ENABLE_MIC_IS_DYNAMIC": self.ENABLE_MIC_IS_DYNAMIC,
                "MIC_THRESHOLD": self.MIC_THRESHOLD,
                "CHOICE_SPEAKER_DEVICE": self.CHOICE_SPEAKER_DEVICE,
                "INPUT_SPEAKER_VOICE_LANGUAGE": self.INPUT_SPEAKER_VOICE_LANGUAGE,
                "ENABLE_SPEAKER_IS_DYNAMIC": self.ENABLE_SPEAKER_IS_DYNAMIC,
                "SPEAKER_THRESHOLD": self.SPEAKER_THRESHOLD,
                "OSC_IP_ADDRESS": self.OSC_IP_ADDRESS,
                "OSC_PORT": self.OSC_PORT,
                "AUTH_KEYS": self.AUTH_KEYS,
                "MESSAGE_FORMAT": self.MESSAGE_FORMAT,
            }
            json.dump(config, fp, indent=4)

        # init main window
        self.iconbitmap(os.path.join(os.path.dirname(__file__), "img", "app.ico"))
        self.title("VRCT")
        self.geometry(f"{400}x{140}")
        self.minsize(400, 140)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # add sidebar left
        self.sidebar_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # add checkbox translation
        self.checkbox_translation = customtkinter.CTkCheckBox(
            self.sidebar_frame,
            text="Translation",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_translation_callback,
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_translation.grid(row=0, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # add checkbox transcription
        self.checkbox_transcription = customtkinter.CTkCheckBox(
            self.sidebar_frame,
            text="Transcription",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_transcription_callback,
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_transcription.grid(row=1, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # add checkbox foreground
        self.checkbox_foreground = customtkinter.CTkCheckBox(
            self.sidebar_frame,
            text="Foreground",
            onvalue=True,
            offvalue=False,
            command=self.checkbox_foreground_callback,
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.checkbox_foreground.grid(row=2, column=0, columnspan=2 ,padx=10, pady=(5, 5), sticky="we")

        # add button information
        self.button_information = customtkinter.CTkButton(
            self.sidebar_frame,
            text="",
            width=25,
            command=self.button_information_callback,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "info-icon-white.png")))
        )
        self.button_information.grid(row=5, column=0, padx=(10, 5), pady=(5, 5), sticky="wse")
        self.information_window = None

        # add button config
        self.button_config = customtkinter.CTkButton(
            self.sidebar_frame,
            text="",
            width=25,
            command=self.button_config_callback,
            image=customtkinter.CTkImage(Image.open(os.path.join(os.path.dirname(__file__), "img", "config-icon-white.png")))
        )
        self.button_config.grid(row=5, column=1, padx=(5, 10), pady=(5, 5), sticky="wse")
        self.config_window = None

        # add tabview textbox
        self.tabview_logs = customtkinter.CTkTabview(master=self)
        self.tabview_logs.add("send")
        self.tabview_logs.add("receive")
        self.tabview_logs.grid(row=0, column=1, padx=5, pady=0, sticky="nsew")
        self.tabview_logs._segmented_button.grid(sticky="W")
        self.tabview_logs.tab("send").grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab("send").grid_columnconfigure(0, weight=1)
        self.tabview_logs.tab("receive").grid_rowconfigure(0, weight=1)
        self.tabview_logs.tab("receive").grid_columnconfigure(0, weight=1)
        self.tabview_logs.configure(state='disabled')

        # add textbox message log
        self.textbox_message_log = customtkinter.CTkTextbox(
            self.tabview_logs.tab("send"),
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_log.configure(state='disabled')

        # add textbox message log
        self.textbox_message_receive_log = customtkinter.CTkTextbox(
            self.tabview_logs.tab("receive"),
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.textbox_message_receive_log.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.textbox_message_receive_log.configure(state='disabled')

        # add entry message box
        self.entry_message_box = customtkinter.CTkEntry(
            self,
            placeholder_text="message",
            font=customtkinter.CTkFont(family=self.FONT_FAMILY)
        )
        self.entry_message_box.grid(row=1, column=1, columnspan=2, padx=(10, 10), pady=(5, 10), sticky="nsew")

        # set default values
        ## set translator instance
        self.translator = Translator()
        if self.translator.authentication(self.CHOICE_TRANSLATOR, self.AUTH_KEYS[self.CHOICE_TRANSLATOR]) is False:
            # error update Auth key
            self.textbox_message_log.configure(state='normal')
            self.textbox_message_log.insert("end", f"[ERROR] Auth Keyを設定してないか間違っています\n")
            self.textbox_message_log.configure(state='disabled')
            self.textbox_message_log.see("end")

        ## set transcription instance
        self.vr = VoiceRecognizer()
        self.CHOICE_MIC_DEVICE = self.CHOICE_MIC_DEVICE if self.CHOICE_MIC_DEVICE is not None else list(self.vr.input_device_dict.keys())[0]

        ## set checkbox enable translation
        if self.ENABLE_TRANSLATION:
            self.checkbox_translation.select()
            self.checkbox_translation_callback()
        else:
            self.checkbox_translation.deselect()

        ## set checkbox enable transcription
        if self.ENABLE_TRANSCRIPTION:
            self.checkbox_transcription.select()
        else:
            self.checkbox_transcription.deselect()
        self.checkbox_transcription_callback()

        ## set set checkbox enable foreground
        if self.ENABLE_FOREGROUND:
            self.checkbox_foreground.select()
        else:
            self.checkbox_foreground.deselect()
        self.checkbox_foreground_callback()

        ## set bind entry message box
        self.entry_message_box.bind("<Return>", self.entry_message_box_press_key_enter)
        self.entry_message_box.bind("<Any-KeyPress>", self.entry_message_box_press_key_any)
        self.entry_message_box.bind("<Leave>", self.entry_message_box_leave)

        ## set transparency for main window
        self.wm_attributes("-alpha", self.TRANSPARENCY/100)

        ## set UI scale
        new_scaling_float = int(self.UI_SCALING.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

        ## set UI theme
        customtkinter.set_appearance_mode(self.APPEARANCE_THEME)
        customtkinter.set_default_color_theme("blue")

    def button_config_callback(self):
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = ToplevelWindowConfig(self)
        self.config_window.focus()

    def button_information_callback(self):
        if self.information_window is None or not self.information_window.winfo_exists():
            self.information_window = ToplevelWindowInformation(self)
        self.information_window.focus()

    def checkbox_translation_callback(self):
        self.ENABLE_TRANSLATION = self.checkbox_translation.get()
        self.textbox_message_log.configure(state='normal')
        if self.ENABLE_TRANSLATION:
            self.textbox_message_log.insert("end", f"[INFO] start translation\n")
        else:
            self.textbox_message_log.insert("end", f"[INFO] stop translation\n")
        self.textbox_message_log.configure(state='disabled')
        self.textbox_message_log.see("end")
        save_json(self.PATH_CONFIG, "ENABLE_TRANSLATION", self.ENABLE_TRANSLATION)

    def checkbox_transcription_callback(self):
        self.ENABLE_TRANSCRIPTION = self.checkbox_transcription.get()
        if self.ENABLE_TRANSCRIPTION is True:
            # start threading
            th = threading.Thread(target = self.voice_input)
            th.start()
        save_json(self.PATH_CONFIG, "ENABLE_TRANSCRIPTION", self.ENABLE_TRANSCRIPTION)

    def voice_input(self):
        self.vr.set_mic(self.CHOICE_MIC_DEVICE)
        self.vr.init_mic(threshold=self.MIC_THRESHOLD, is_dynamic=self.ENABLE_MIC_IS_DYNAMIC)

        # start voice_input
        if self.checkbox_transcription.get() is True:
            self.textbox_message_log.configure(state='normal')
            self.textbox_message_log.insert("end", f"[INFO] start transcription\n")
            self.textbox_message_log.configure(state='disabled')
            self.textbox_message_log.see("end")

        while self.checkbox_transcription.get() is True:
            message = self.vr.listen_voice(language=self.INPUT_MIC_VOICE_LANGUAGE)
            if len(message) > 0:
                # translate
                if self.checkbox_translation.get() is False:
                    chat_message = f"{message}"
                elif (self.translator.translator_status[self.CHOICE_TRANSLATOR] is False) or (self.INPUT_SOURCE_LANG == "None") or (self.INPUT_TARGET_LANG == "None"):
                    self.textbox_message_log.configure(state='normal')
                    self.textbox_message_log.insert("end", f"[ERROR] Auth Keyもしくは言語の設定が間違っています\n")
                    self.textbox_message_log.configure(state='disabled')
                    self.textbox_message_log.see("end")
                    chat_message = f"{message}"
                else:
                    result = self.translator.translate(
                        translator_name=self.CHOICE_TRANSLATOR,
                        source_language=self.INPUT_SOURCE_LANG,
                        target_language=self.INPUT_TARGET_LANG,
                        message=message
                    )
                    chat_message = self.MESSAGE_FORMAT.replace("[message]", message).replace("[translation]", result)

                # send OSC message
                message = osc_message_builder.OscMessageBuilder(address="/chatbox/input")
                message.add_arg(f"{chat_message}")
                message.add_arg(True)
                message.add_arg(True)
                message = message.build()
                client = udp_client.SimpleUDPClient(self.OSC_IP_ADDRESS, self.OSC_PORT)
                client.send(message)

                # update textbox message log
                self.textbox_message_log.configure(state='normal')
                self.textbox_message_log.insert("end", f"[VOICE] {chat_message}\n")
                self.textbox_message_log.configure(state='disabled')
                self.textbox_message_log.see("end")
        self.textbox_message_log.configure(state='normal')
        self.textbox_message_log.insert("end", f"[INFO] stop transcription\n")
        self.textbox_message_log.configure(state='disabled')
        self.textbox_message_log.see("end")

    def checkbox_foreground_callback(self):
        self.ENABLE_FOREGROUND = self.checkbox_foreground.get()
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)
        else:
            self.attributes("-topmost", False)
        save_json(self.PATH_CONFIG, "ENABLE_FOREGROUND", self.ENABLE_FOREGROUND)

    def entry_message_box_press_key_enter(self, event):
        # send OSC typing
        typing = osc_message_builder.OscMessageBuilder(address="/chatbox/typing")
        typing.add_arg(False)
        typing = typing.build()
        client = udp_client.SimpleUDPClient(self.OSC_IP_ADDRESS, self.OSC_PORT)
        client.send(typing)

        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)

        message = self.entry_message_box.get()
        if len(message) > 0:
            # translate
            if self.checkbox_translation.get() is False:
                chat_message = f"{message}"
            elif (self.translator.translator_status[self.CHOICE_TRANSLATOR] is False) or (self.INPUT_SOURCE_LANG == "None") or (self.INPUT_TARGET_LANG == "None"):
                self.textbox_message_log.configure(state='normal')
                self.textbox_message_log.insert("end", f"[ERROR] Auth Keyもしくは言語の設定が間違っています\n")
                self.textbox_message_log.configure(state='disabled')
                self.textbox_message_log.see("end")
                chat_message = f"{message}"
            else:
                result = self.translator.translate(
                    translator_name=self.CHOICE_TRANSLATOR,
                    source_language=self.INPUT_SOURCE_LANG,
                    target_language=self.INPUT_TARGET_LANG,
                    message=message
                )
                chat_message = self.MESSAGE_FORMAT.replace("[message]", message).replace("[translation]", result)

            # send OSC message
            message = osc_message_builder.OscMessageBuilder(address="/chatbox/input")
            message.add_arg(f"{chat_message}")
            message.add_arg(True)
            message.add_arg(True)
            message = message.build()
            client = udp_client.SimpleUDPClient(self.OSC_IP_ADDRESS, self.OSC_PORT)
            client.send(message)

            # update textbox message log
            self.textbox_message_log.configure(state='normal')
            self.textbox_message_log.insert("end", f"[CHAT] {chat_message}\n")
            self.textbox_message_log.configure(state='disabled')
            self.textbox_message_log.see("end")

            # delete message in entry message box
            # self.entry_message_box.delete(0, customtkinter.END)

    def entry_message_box_press_key_any(self, event):
        # send OSC typing
        typing = osc_message_builder.OscMessageBuilder(address="/chatbox/typing")
        typing.add_arg(True)
        typing = typing.build()
        client = udp_client.SimpleUDPClient(self.OSC_IP_ADDRESS, self.OSC_PORT)
        client.send(typing)
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", False)

    def entry_message_box_leave(self, event):
        # send OSC typing
        typing = osc_message_builder.OscMessageBuilder(address="/chatbox/typing")
        typing.add_arg(False)
        typing = typing.build()
        client = udp_client.SimpleUDPClient(self.OSC_IP_ADDRESS, self.OSC_PORT)
        client.send(typing)
        if self.ENABLE_FOREGROUND:
            self.attributes("-topmost", True)

if __name__ == "__main__":
    app = App()
    app.mainloop()