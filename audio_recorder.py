import custom_speech_recognition as sr
import pyaudiowpatch as pyaudio
from datetime import datetime

RECORD_TIMEOUT = 3
ENERGY_THRESHOLD = 1000
DYNAMIC_ENERGY_THRESHOLD = False

class BaseRecorder:
    def __init__(self, source):
        self.recorder = sr.Recognizer()
        self.recorder.energy_threshold = ENERGY_THRESHOLD
        self.recorder.dynamic_energy_threshold = DYNAMIC_ENERGY_THRESHOLD
        self.stop = None

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source

    def adjust_for_noise(self):
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def record_into_queue(self, audio_queue):
        def record_callback(_, audio:sr.AudioData) -> None:
            audio_queue.put((audio.get_raw_data(), datetime.now()))

        self.stop = self.recorder.listen_in_background(self.source, record_callback, phrase_time_limit=RECORD_TIMEOUT)

class SelectedMicRecorder(BaseRecorder):
    def __init__(self, device):
        source=sr.Microphone(
            device_index=device['index'],
            sample_rate=int(device["defaultSampleRate"]),
        )
        super().__init__(source=source)
        self.adjust_for_noise()

class SelectedSpeakerRecorder(BaseRecorder):
    def __init__(self, device):

        source = sr.Microphone(speaker=True,
            device_index= device["index"],
            sample_rate=int(device["defaultSampleRate"]),
            chunk_size=pyaudio.get_sample_size(pyaudio.paInt16),
            channels=device["maxInputChannels"]
        )
        super().__init__(source=source)
        self.adjust_for_noise()