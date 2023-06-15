import io
import queue
import numpy as np
import soundcard as sc
import soundfile as sf
import sounddevice as sd
import speech_recognition as sr

# VoiceRecognizer
class VoiceRecognizer():
    def __init__(self):
        self.r = sr.Recognizer()
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
        self.mic_device_name = None
        self.mic_threshold = 50
        self.mic_is_dynamic = False
        self.mic_queue = queue.Queue()

        self.spk_device_name = None
        self.spk_sample_rate = 16000
        self.spk_interval = 3
        self.spk_buffer_size = 4096
        self.spk_audio = np.empty(self.spk_sample_rate * self.spk_interval + self.spk_buffer_size, dtype=np.float32)
        self.n = 0
        self.spk_queue = queue.Queue()

    def search_input_device(self):
        device_list = sd.query_devices()
        input_device_list = []

        for device in device_list:
            if device["max_input_channels"] > 0:
                input_device_list.append({"name": device["name"],  "index": device["index"]})

        return input_device_list

    def search_output_device(self):
        device_list = sc.all_speakers()
        output_device_list = []

        for device in device_list:
            output_device_list.append(str(device.name))

        return output_device_list

    def search_default_device(self):
        device_list = sd.query_devices()
        mic_index = sd.default.device[0]
        name_mic = device_list[mic_index]["name"]
        name_spk = str(sc.default_speaker().name)
        return name_mic, name_spk

    def set_mic(self, device_name, threshold=50, is_dynamic=False):
        input_device_list = self.search_input_device()
        self.mic_device_name = [device["index"] for device in input_device_list if device["name"] == device_name][0]
        self.mic_threshold = threshold
        self.mic_is_dynamic = is_dynamic

    def init_mic(self):
        self.r.energy_threshold = self.mic_threshold
        if self.mic_is_dynamic:
            with self.mic as source:
                self.r.adjust_for_ambient_noise(source, 3.0)

    def listen_mic(self):
        with sr.Microphone(device_index=self.mic_device_name) as source:
            audio = self.r.listen(source)
            self.mic_queue.put(audio)

    def recognize_mic(self, language):
        try:
            audio = self.mic_queue.get()
            text = self.r.recognize_google(audio, language=language)
        except:
            text = ""
        return text

    def set_spk(self, device_name=str(sc.default_speaker().name), sample_rate=16000, interval=3, buffer_size=4096):
        self.spk_device_name = device_name
        self.spk_sample_rate = sample_rate
        self.spk_interval = interval
        self.spk_buffer_size = buffer_size

    def init_spk(self):
        self.spk_audio = np.empty(self.spk_sample_rate * self.spk_interval + self.spk_buffer_size, dtype=np.float32)
        self.n = 0

    def listen_spk(self):
        audio = self.spk_audio
        n = self.n
        with sc.get_microphone(id=self.spk_device_name, include_loopback=True).recorder(samplerate=self.spk_sample_rate, channels=1) as source:
            while n < self.spk_sample_rate * self.spk_interval:
                data = source.record(self.spk_buffer_size)
                audio[n:n+len(data)] = data.reshape(-1)
                n += len(data)
            m = n * 4 // 5
            vol = np.convolve(audio[m:n] ** 2, np.ones(100) / 100, 'same')
            m += vol.argmin()
            audio_prev = audio.copy()
            self.spk_queue.put(audio[:m])
            audio = np.empty(self.spk_sample_rate * self.spk_interval + self.spk_buffer_size, dtype=np.float32)
            audio[:n-m] = audio_prev[m:n]
            n = n-m
        self.spk_audio = audio
        self.n = n

    def recognize_spk(self, language):
        try:
            audio = self.spk_queue.get()
            with io.BytesIO() as memory_file:
                sf.write(file=memory_file, data=audio, format="WAV", samplerate=self.spk_sample_rate)
                memory_file.seek(0)
                with sr.AudioFile(memory_file) as source:
                    audio = self.r.record(source)
                text = self.r.recognize_google(audio, language=language)
        except:
            text = ""
        return text

if __name__ == "__main__":
    import time
    import threading

    vr = VoiceRecognizer()
    mic_name, spk_name = vr.search_default_device()
    vr.spk_enable_recognize = True
    vr.set_spk(language="ja-JP")
    vr.init_spk()

    def vr_listen_spk():
        while True:
            vr.listen_spk()

    def vr_recognize_spk():
        while True:
            text = vr.recognize_spk()
            print(text)

    th_vr_listen_spk = threading.Thread(target=vr_listen_spk)
    th_vr_recognize_spk = threading.Thread(target=vr_recognize_spk)
    th_vr_listen_spk.start()
    th_vr_recognize_spk.start()

    while True:
        time.sleep(60)