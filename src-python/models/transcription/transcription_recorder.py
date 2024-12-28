from speech_recognition import Recognizer, Microphone
from pyaudiowpatch import get_sample_size, paInt16
from datetime import datetime
from queue import Queue

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

    def adjustForNoise(self):
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, audio_queue):
        def record_callback(_, audio):
            audio_queue.put((audio.get_raw_data(), datetime.now()))

        self.stop, self.pause, self.resume = self.recorder.listen_in_background(self.source, record_callback, phrase_time_limit=self.record_timeout)

class SelectedMicRecorder(BaseRecorder):
    def __init__(self, device, energy_threshold, dynamic_energy_threshold, record_timeout):
        source=Microphone(
            device_index=device['index'],
            sample_rate=int(device["defaultSampleRate"]),
        )
        super().__init__(source=source, energy_threshold=energy_threshold, dynamic_energy_threshold=dynamic_energy_threshold, record_timeout=record_timeout)
        # self.adjustForNoise()

class SelectedSpeakerRecorder(BaseRecorder):
    def __init__(self, device, energy_threshold, dynamic_energy_threshold, record_timeout):

        source = Microphone(speaker=True,
            device_index= device["index"],
            sample_rate=int(device["defaultSampleRate"]),
            chunk_size=get_sample_size(paInt16),
            channels=device["maxInputChannels"]
        )
        super().__init__(source=source, energy_threshold=energy_threshold, dynamic_energy_threshold=dynamic_energy_threshold, record_timeout=record_timeout)
        # self.adjustForNoise()

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

    def adjustForNoise(self):
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, energy_queue):
        def recordCallback(_, energy):
            energy_queue.put(energy)

        self.stop, self.pause, self.resume = self.recorder.listen_energy_in_background(self.source, recordCallback)

class SelectedMicEnergyRecorder(BaseEnergyRecorder):
    def __init__(self, device):
        source=Microphone(
            device_index=device['index'],
            sample_rate=int(device["defaultSampleRate"]),
        )
        super().__init__(source=source)
        # self.adjustForNoise()

class SelectedSpeakerEnergyRecorder(BaseEnergyRecorder):
    def __init__(self, device):

        source = Microphone(speaker=True,
            device_index= device["index"],
            sample_rate=int(device["defaultSampleRate"]),
            channels=device["maxInputChannels"]
        )
        super().__init__(source=source)
        # self.adjustForNoise()

class BaseEnergyAndAudioRecorder:
    def __init__(self, source, energy_threshold, dynamic_energy_threshold, phrase_time_limit, phrase_timeout, record_timeout):
        self.recorder = Recognizer()
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = dynamic_energy_threshold
        self.phrase_time_limit = phrase_time_limit
        self.phrase_timeout = phrase_timeout
        self.record_timeout = record_timeout
        self.stop = None

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source

    def adjustForNoise(self):
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, audio_queue, energy_queue=None):
        def audioRecordCallback(_, audio):
            audio_queue.put((audio.get_raw_data(), datetime.now()))

        def energyRecordCallback(energy):
            energy_queue.put(energy)

        self.stop, self.pause, self.resume = self.recorder.listen_energy_and_audio_in_background(
            source=self.source,
            callback=audioRecordCallback,
            phrase_time_limit=self.phrase_time_limit,
            callback_energy=energyRecordCallback if energy_queue is not None else None,
            phrase_timeout=self.phrase_timeout,
            record_timeout=self.record_timeout)

class SelectedMicEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(self, device, energy_threshold, dynamic_energy_threshold, phrase_time_limit, phrase_timeout:int=1, record_timeout:int=5):
        source=Microphone(
            device_index=device['index'],
            sample_rate=int(device["defaultSampleRate"]),
        )
        super().__init__(
            source=source,
            energy_threshold=energy_threshold,
            dynamic_energy_threshold=dynamic_energy_threshold,
            phrase_time_limit=phrase_time_limit,
            phrase_timeout=phrase_timeout,
            record_timeout=record_timeout,
        )
        # self.adjustForNoise()

class SelectedSpeakerEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(self, device, energy_threshold, dynamic_energy_threshold, phrase_time_limit, phrase_timeout:int=1, record_timeout:int=5):

        source = Microphone(speaker=True,
            device_index= device["index"],
            sample_rate=int(device["defaultSampleRate"]),
            chunk_size=get_sample_size(paInt16),
            channels=device["maxInputChannels"]
        )
        super().__init__(
            source=source,
            energy_threshold=energy_threshold,
            dynamic_energy_threshold=dynamic_energy_threshold,
            phrase_time_limit=phrase_time_limit,
            phrase_timeout=phrase_timeout,
            record_timeout=record_timeout,
        )
        # self.adjustForNoise()