import pyaudio
import speech_recognition as sr

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