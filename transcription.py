import queue
import speech_recognition as sr
import pyaudiowpatch as pyaudio
import languages

# VoiceRecognizer
class VoiceRecognizer():
    def __init__(self):
        self.r = sr.Recognizer()
        self.p = pyaudio.PyAudio()

        self.dict_languages = languages.recognize_lang
        self.languages = list(self.dict_languages.keys())
        self.mic_device_name = None
        self.mic_threshold = 50
        self.mic_is_dynamic = False
        self.mic_language = "Japan"
        self.mic_queue = queue.Queue(10)

        self.spk_device = None
        self.spk_interval = 3
        self.spk_language = "Japan"
        self.spk_stream = None
        self.spk_queue = queue.Queue(10)

    def search_input_device(self):
        devices = []
        with pyaudio.PyAudio() as p:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            for host_index in range(0, p.get_host_api_count()):
                for device_index in range(0, p. get_host_api_info_by_index(host_index)['deviceCount']):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device["hostApi"] == wasapi_info["index"] and device["maxInputChannels"] > 0 and device["isLoopbackDevice"] is False:
                        devices.append(device)
        return devices

    def search_output_device(self):
        devices =[]
        with pyaudio.PyAudio() as p:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            for host_index in range(0, p.get_host_api_count()):
                for device_index in range(0, p. get_host_api_info_by_index(host_index)['deviceCount']):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device["hostApi"] == wasapi_info["index"] and device["isLoopbackDevice"] is True:
                        devices.append(device)
        return devices

    def search_default_device(self):
        with pyaudio.PyAudio() as p:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            defaultInputDevice, defaultOutputDevice = wasapi_info["defaultInputDevice"], wasapi_info["defaultOutputDevice"]

            for host_index in range(0, p.get_host_api_count()):
                for device_index in range(0, p. get_host_api_info_by_index(host_index)['deviceCount']):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device["index"] == defaultInputDevice:
                        default_mics = device
                        name_mic = default_mics["name"]
                        break

            for host_index in range(0, p.get_host_api_count()):
                for device_index in range(0, p. get_host_api_info_by_index(host_index)['deviceCount']):
                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                    if device["index"] == defaultOutputDevice:
                        default_speakers = device
                        if not default_speakers["isLoopbackDevice"]:
                            for loopback in p.get_loopback_device_info_generator():
                                if default_speakers["name"] in loopback["name"]:
                                    name_spk = loopback["name"]
                                    break
        return name_mic, name_spk

    def set_mic(self, device_name, threshold=50, is_dynamic=False, language="Japan"):
        input_device_list = self.search_input_device()
        self.mic_device_name = [device["index"] for device in input_device_list if device["name"] == device_name][0]
        self.mic_threshold = threshold
        self.mic_is_dynamic = is_dynamic
        self.mic_language = language

    def init_mic(self):
        while self.mic_queue.empty() is False:
            self.mic_queue.get()

        self.r.energy_threshold = self.mic_threshold
        if self.mic_is_dynamic:
            with self.mic as source:
                self.r.adjust_for_ambient_noise(source, 3.0)

    def listen_mic(self):
        with sr.Microphone(device_index=self.mic_device_name) as source:
            audio = self.r.listen(source)
            self.mic_queue.put(audio)

    def recognize_mic(self):
        try:
            audio = self.mic_queue.get()
            text = self.r.recognize_google(audio, language=self.dict_languages[self.mic_language])
        except:
            text = ""
        return text

    def set_spk(self, device_name, interval=4, language="Japan"):
        output_device_list = self.search_output_device()
        self.spk_device = [device for device in output_device_list if device["name"] == device_name][0]
        self.spk_interval = interval
        self.spk_language = language

    def init_spk(self):
        while self.spk_queue.empty() is False:
            self.spk_queue.get()

    def spk_record_callback(self, in_data, frame_count, time_info, status):
        self.spk_queue.put(in_data)
        return (in_data, pyaudio.paContinue)

    def start_spk_recording(self):
        self.close_spk_stream()
        self.spk_stream = self.p.open(format=pyaudio.paInt16,
                channels=self.spk_device["maxInputChannels"],
                rate=int(self.spk_device["defaultSampleRate"]),
                frames_per_buffer=int(self.spk_device["defaultSampleRate"])*self.spk_interval,
                input=True,
                input_device_index=self.spk_device["index"],
                stream_callback=self.spk_record_callback
        )

    def stop_spk_stream(self):
        self.spk_stream.stop_stream()

    def start_spk_stream(self):
        self.spk_stream.start_stream()

    def close_spk_stream(self):
        if self.spk_stream is not None:
            self.spk_stream.stop_stream()
            self.spk_stream.close()
            self.spk_stream = None

    def recognize_spk(self):
        try:
            in_data = self.spk_queue.get()
            audio_data = sr.AudioData(in_data, int(self.spk_device["defaultSampleRate"]), self.spk_interval)
            text = self.r.recognize_google(audio_data, language=self.dict_languages[self.spk_language])
        except:
            text = ""
        return text

if __name__ == "__main__":
    # import queue
    # import threading

    # mic_queue = queue.Queue()
    # spk_queue = queue.Queue()
    # vr = VoiceRecognizer(mic_queue, spk_queue)

    # mic_name, spk_name = vr.search_default_device()
    # print("mic_name", mic_name)
    # print("spk_name", spk_name)

    # ###############################################################
    # vr.set_mic(device_name=mic_name, threshold=300, is_dynamic=False, language="ja-JP")
    # vr.init_mic()

    # def vr_listen_mic():
    #     while True:
    #         vr.listen_mic()

    # def vr_recognize_mic():
    #     while True:
    #         text = vr.recognize_mic()
    #         if len(text) > 0:
    #             print(text)
    # th_vr_listen_mic = threading.Thread(target=vr_listen_mic)
    # th_vr_listen_mic.start()
    # th_vr_recognize_mic = threading.Thread(target=vr_recognize_mic)
    # th_vr_recognize_mic.start()
    # ###############################################################

    # ###############################################################
    # vr.set_spk(device_name=spk_name, interval=4, language="ja-JP")
    # vr.start_spk_recording()

    # def vr_recognize_spk():
    #     while True:
    #         text = vr.recognize_spk()
    #         if len(text) > 0:
    #             print(text)
    # th_vr_recognize_spk = threading.Thread(target=vr_recognize_spk)
    # th_vr_recognize_spk.start()
    # ###############################################################

    vr = VoiceRecognizer()
    print(vr.search_input_device())
    print(vr.search_default_device())