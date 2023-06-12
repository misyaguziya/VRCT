import sounddevice as sd
import speech_recognition as sr

# VoiceRecognizer
class VoiceRecognizer():
    def __init__(self):
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
        device_list = sd.query_devices()
        input_device_list = []

        for device in device_list:
            if device["max_input_channels"] > 0:
                input_device_list.append({"name": device["name"],  "index": device["index"]})

        return input_device_list

    def search_output_device(self):
        device_list = sd.query_devices()
        output_device_list = []

        for device in device_list:
            if device["max_output_channels"] > 0:
                output_device_list.append({"name": device["name"],  "index": device["index"]})

        return output_device_list

    def search_default_device_index(self):
        device_list = sd.query_devices()
        default_device_list = []
        for i in sd.default.device:
            default_device_list.append({"name": device_list[i]["name"],  "index": device_list[i]["index"]})
        return default_device_list

    def set_mic(self, device_name, threshold=50, is_dynamic=False):
        input_device_list = self.search_input_device()
        if device_name in [input_device["name"] for input_device in input_device_list]:
            index = [device["index"] for device in input_device_list if device["name"] == device_name][0]

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