"""Recorders that wrap speech_recognition microphone interfaces.

These classes provide small adapters that push raw audio bytes into queues.
They intentionally keep a thin API so the rest of the system can mock them
in tests.
"""

from typing import Any
from speech_recognition import Recognizer, Microphone
from pyaudiowpatch import get_sample_size, paInt16
from datetime import datetime


class BaseRecorder:
    def __init__(self, source: Any, energy_threshold: int, dynamic_energy_threshold: bool, record_timeout: int) -> None:
        self.recorder = Recognizer()
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = dynamic_energy_threshold
        self.record_timeout = record_timeout
        self.stop = None

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source

    def adjustForNoise(self) -> None:
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, audio_queue: Any) -> None:
        def record_callback(_, audio):
            audio_queue.put((audio.get_raw_data(), datetime.now()))

        self.stop, self.pause, self.resume = self.recorder.listen_in_background(self.source, record_callback, phrase_time_limit=self.record_timeout)


class SelectedMicRecorder(BaseRecorder):
    def __init__(self, device: dict, energy_threshold: int, dynamic_energy_threshold: bool, record_timeout: int) -> None:
        # Safely construct Microphone source. If device dict is missing expected keys
        # or index is out-of-range for the platform, fallback to default device (None)
        try:
            device_index = int(device.get('index', -1))
            sample_rate = int(device.get("defaultSampleRate", 16000))
            if device_index < 0:
                # invalid index -> fallback
                raise ValueError("invalid device index")
            source = Microphone(
                device_index=device_index,
                sample_rate=sample_rate,
            )
        except Exception:
            # Best-effort fallback: use system default microphone
            try:
                source = Microphone()
            except Exception:
                raise
        super().__init__(source=source, energy_threshold=energy_threshold, dynamic_energy_threshold=dynamic_energy_threshold, record_timeout=record_timeout)
        # self.adjustForNoise()


class SelectedSpeakerRecorder(BaseRecorder):
    def __init__(self, device: dict, energy_threshold: int, dynamic_energy_threshold: bool, record_timeout: int) -> None:
        try:
            device_index = int(device.get('index', -1))
            sample_rate = int(device.get("defaultSampleRate", 16000))
            channels = int(device.get("maxInputChannels", 1))
            if device_index < 0:
                raise ValueError("invalid device index")
            source = Microphone(speaker=True,
                device_index=device_index,
                sample_rate=sample_rate,
                chunk_size=get_sample_size(paInt16),
                channels=channels
            )
        except Exception:
            try:
                source = Microphone(speaker=True)
            except Exception:
                raise
        super().__init__(source=source, energy_threshold=energy_threshold, dynamic_energy_threshold=dynamic_energy_threshold, record_timeout=record_timeout)
        # self.adjustForNoise()

class BaseEnergyRecorder:
    def __init__(self, source: Any) -> None:
        self.recorder = Recognizer()
        self.recorder.energy_threshold = 0
        self.recorder.dynamic_energy_threshold = False
        self.record_timeout = 0
        self.stop = None

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source

    def adjustForNoise(self) -> None:
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, energy_queue: Any) -> None:
        def recordCallback(_, energy):
            energy_queue.put(energy)

        self.stop, self.pause, self.resume = self.recorder.listen_energy_in_background(self.source, recordCallback)


class SelectedMicEnergyRecorder(BaseEnergyRecorder):
    def __init__(self, device: dict) -> None:
        try:
            device_index = int(device.get('index', -1))
            sample_rate = int(device.get("defaultSampleRate", 16000))
            if device_index < 0:
                raise ValueError("invalid device index")
            source = Microphone(
                device_index=device_index,
                sample_rate=sample_rate,
            )
        except Exception:
            try:
                source = Microphone()
            except Exception:
                raise
        super().__init__(source=source)
        # self.adjustForNoise()


class SelectedSpeakerEnergyRecorder(BaseEnergyRecorder):
    def __init__(self, device: dict) -> None:
        try:
            device_index = int(device.get('index', -1))
            sample_rate = int(device.get("defaultSampleRate", 16000))
            channels = int(device.get("maxInputChannels", 1))
            if device_index < 0:
                raise ValueError("invalid device index")
            source = Microphone(speaker=True,
                device_index=device_index,
                sample_rate=sample_rate,
                channels=channels
            )
        except Exception:
            try:
                source = Microphone(speaker=True)
            except Exception:
                raise
        super().__init__(source=source)
        # self.adjustForNoise()

class BaseEnergyAndAudioRecorder:
    def __init__(
        self,
        source: Any,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        phrase_timeout: int,
        record_timeout: int,
    ) -> None:
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

    def adjustForNoise(self) -> None:
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, audio_queue: Any, energy_queue: Any = None) -> None:
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
            record_timeout=self.record_timeout,
        )


class SelectedMicEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(
        self,
        device: dict,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        phrase_timeout: int = 1,
        record_timeout: int = 5,
    ) -> None:
        try:
            device_index = int(device.get('index', -1))
            sample_rate = int(device.get("defaultSampleRate", 16000))
            if device_index < 0:
                raise ValueError("invalid device index")
            source = Microphone(
                device_index=device_index,
                sample_rate=sample_rate,
            )
        except Exception:
            try:
                source = Microphone()
            except Exception:
                raise
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
    def __init__(
        self,
        device: dict,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        phrase_timeout: int = 1,
        record_timeout: int = 5,
    ) -> None:

        try:
            device_index = int(device.get('index', -1))
            sample_rate = int(device.get("defaultSampleRate", 16000))
            channels = int(device.get("maxInputChannels", 1))
            if device_index < 0:
                raise ValueError("invalid device index")
            source = Microphone(speaker=True,
                device_index=device_index,
                sample_rate=sample_rate,
                chunk_size=get_sample_size(paInt16),
                channels=channels,
            )
        except Exception:
            try:
                source = Microphone(speaker=True)
                device_index = -1  # Unknown device index for fallback
            except Exception:
                raise
        super().__init__(
            source=source,
            energy_threshold=energy_threshold,
            dynamic_energy_threshold=dynamic_energy_threshold,
            phrase_time_limit=phrase_time_limit,
            phrase_timeout=phrase_timeout,
            record_timeout=record_timeout,
        )
        # Store device index for availability checking
        self.device_index = device_index
        self.device_name = device.get('name', 'Unknown')
        # self.adjustForNoise()