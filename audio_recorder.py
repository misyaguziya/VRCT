from speech_recognition import Recognizer, Microphone
from pyaudiowpatch import get_sample_size, paInt16
from datetime import datetime

class BaseRecorder:
    def __init__(self, source, energy_threshold, dynamic_energy_threshold, record_timeout):
        self.recorder = Recognizer()
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = dynamic_energy_threshold
        self.record_timeout = record_timeout
        self.stop = None

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source

    def adjust_for_noise(self):
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def record_into_queue(self, audio_queue):
        def record_callback(_, audio):
            audio_queue.put((audio.get_raw_data(), datetime.now()))

        self.stop = self.recorder.listen_in_background(self.source, record_callback, phrase_time_limit=self.record_timeout)

class SelectedMicRecorder(BaseRecorder):
    def __init__(self, device, energy_threshold, dynamic_energy_threshold, record_timeout):
        source=Microphone(
            device_index=device['index'],
            sample_rate=int(device["defaultSampleRate"]),
        )
        super().__init__(source=source, energy_threshold=energy_threshold, dynamic_energy_threshold=dynamic_energy_threshold, record_timeout=record_timeout)
        self.adjust_for_noise()

class SelectedSpeakerRecorder(BaseRecorder):
    def __init__(self, device, energy_threshold, dynamic_energy_threshold, record_timeout):

        source = Microphone(speaker=True,
            device_index= device["index"],
            sample_rate=int(device["defaultSampleRate"]),
            chunk_size=get_sample_size(paInt16),
            channels=device["maxInputChannels"]
        )
        super().__init__(source=source, energy_threshold=energy_threshold, dynamic_energy_threshold=dynamic_energy_threshold, record_timeout=record_timeout)
        self.adjust_for_noise()

class BaseEnergyRecorder:
    def __init__(self, source):
        self.recorder = Recognizer()
        self.recorder.energy_threshold = 0
        self.recorder.dynamic_energy_threshold = False
        self.record_timeout = 0
        self.stop = None

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source

    def adjust_for_noise(self):
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def record_into_queue(self, energy_queue):
        def record_callback(_, energy):
            energy_queue.put(energy)

        self.stop = self.recorder.listen_energy_in_background(self.source, record_callback)

class SelectedMicEnergyRecorder(BaseEnergyRecorder):
    def __init__(self, device):
        source=Microphone(
            device_index=device['index'],
            sample_rate=int(device["defaultSampleRate"]),
        )
        super().__init__(source=source)
        self.adjust_for_noise()

class SelectedSpeakeEnergyRecorder(BaseEnergyRecorder):
    def __init__(self, device):

        source = Microphone(speaker=True,
            device_index= device["index"],
            sample_rate=int(device["defaultSampleRate"]),
            chunk_size=get_sample_size(paInt16),
            channels=device["maxInputChannels"]
        )
        super().__init__(source=source)
        self.adjust_for_noise()