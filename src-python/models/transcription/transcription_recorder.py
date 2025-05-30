"""Provides classes for recording audio from microphones and speakers using SpeechRecognition."""
from datetime import datetime
from queue import Queue
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

from pyaudiowpatch import get_sample_size, paInt16 # type: ignore # pyaudiowpatch might not have stubs
from speech_recognition import (AudioData, AudioSource, Microphone, # type: ignore
                                Recognizer)

# Type alias for the stop function returned by listen_in_background
StopCallable = Optional[Callable[[bool], None]]

class BaseRecorder:
    """
    Base class for audio recorders. Handles common recorder setup and operations.
    """
    recorder: Recognizer
    source: AudioSource
    record_timeout: Optional[float]
    stop: StopCallable
    pause: Optional[Callable[[], None]]
    resume: Optional[Callable[[], None]]

    def __init__(self, source: AudioSource, energy_threshold: float, dynamic_energy_threshold: bool, record_timeout: Optional[float]) -> None:
        """
        Initializes the BaseRecorder.

        Args:
            source: The audio source (e.g., Microphone instance).
            energy_threshold: The energy level threshold for considering audio as speech.
            dynamic_energy_threshold: Whether to dynamically adjust the energy threshold.
            record_timeout: How long to record audio after speech stops before finalizing a phrase.
        """
        self.recorder = Recognizer()
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = dynamic_energy_threshold
        self.record_timeout = record_timeout
        self.stop: StopCallable = None
        self.pause: Optional[Callable[[], None]] = None
        self.resume: Optional[Callable[[], None]] = None


        if source is None:
            raise ValueError("Audio source can't be None")
        self.source = source

    def adjustForNoise(self) -> None:
        """Adjusts the recorder's energy threshold based on ambient noise."""
        if self.source: # Ensure source is not None
            with self.source:
                self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, audio_queue: Queue[Tuple[bytes, datetime]]) -> None:
        """
        Starts listening in the background and puts recorded audio data into a queue.

        Args:
            audio_queue: The queue to put (audio_bytes, timestamp) tuples into.
        """
        def record_callback(_recognizer: Recognizer, audio: AudioData) -> None:
            """Internal callback to put audio data onto the queue."""
            audio_queue.put((audio.get_raw_data(), datetime.now()))

        if self.source: # Ensure source is not None
            stop_tuple = self.recorder.listen_in_background(
                self.source, record_callback, phrase_time_limit=self.record_timeout
            )
            # listen_in_background can return a 3-tuple or just the stop function
            if isinstance(stop_tuple, tuple) and len(stop_tuple) == 3:
                self.stop, self.pause, self.resume = stop_tuple
            else: # Should be just the stop function based on current SR docs for simple callback
                self.stop = stop_tuple # type: ignore

class SelectedMicRecorder(BaseRecorder):
    """Recorder specifically for selected microphone devices."""
    def __init__(self, device: Dict[str, Any], energy_threshold: float, dynamic_energy_threshold: bool, record_timeout: Optional[float]) -> None:
        """
        Initializes the SelectedMicRecorder.

        Args:
            device: A dictionary containing microphone device information (index, defaultSampleRate).
            energy_threshold: Energy threshold for speech detection.
            dynamic_energy_threshold: Whether to dynamically adjust energy threshold.
            record_timeout: Recording timeout after speech stops.
        """
        source=Microphone(
            device_index=device['index'],
            sample_rate=int(device["defaultSampleRate"]),
        )
        super().__init__(source=source, energy_threshold=energy_threshold, dynamic_energy_threshold=dynamic_energy_threshold, record_timeout=record_timeout)
        # self.adjustForNoise()

class SelectedSpeakerRecorder(BaseRecorder):
    def __init__(self, device: Dict[str, Any], energy_threshold: float, dynamic_energy_threshold: bool, record_timeout: Optional[float]) -> None:
        """
        Initializes the SelectedSpeakerRecorder.

        Args:
            device: Dictionary with speaker device info (index, defaultSampleRate, maxInputChannels).
            energy_threshold: Energy threshold for speech detection.
            dynamic_energy_threshold: Whether to dynamically adjust energy threshold.
            record_timeout: Recording timeout after speech stops.
        """
        source = Microphone(speaker=True, # type: ignore # speaker is a valid arg for pyaudiowpatch Microphone
            device_index=device["index"],
            sample_rate=int(device["defaultSampleRate"]),
            chunk_size=get_sample_size(paInt16), # type: ignore # pyaudiowpatch types
            channels=device["maxInputChannels"]
        )
        super().__init__(
            source=source,
            energy_threshold=energy_threshold,
            dynamic_energy_threshold=dynamic_energy_threshold,
            record_timeout=record_timeout
        )
        # self.adjustForNoise()

class BaseEnergyRecorder:
    """Base class for recorders that only capture audio energy levels."""
    recorder: Recognizer
    source: AudioSource
    stop: StopCallable
    pause: Optional[Callable[[], None]]
    resume: Optional[Callable[[], None]]
    # record_timeout is not used by listen_energy_in_background

    def __init__(self, source: AudioSource) -> None:
        """
        Initializes the BaseEnergyRecorder.

        Args:
            source: The audio source (e.g., Microphone instance).
        """
        self.recorder = Recognizer()
        self.recorder.energy_threshold = 0 # Not strictly used by listen_energy_in_background
        self.recorder.dynamic_energy_threshold = False
        self.stop: StopCallable = None
        self.pause: Optional[Callable[[], None]] = None
        self.resume: Optional[Callable[[], None]] = None

        if source is None:
            raise ValueError("Audio source can't be None")
        self.source = source

    def adjustForNoise(self) -> None:
        """Adjusts the recorder's energy threshold based on ambient noise (less relevant for energy-only)."""
        if self.source:
            with self.source:
                self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, energy_queue: Queue[float]) -> None:
        """
        Starts listening for energy levels in the background and puts them into a queue.

        Args:
            energy_queue: The queue to put energy float values into.
        """
        def recordCallback(_recognizer: Recognizer, energy: float) -> None:
            """Internal callback to put energy data onto the queue."""
            energy_queue.put(energy)
        
        if self.source:
            # listen_energy_in_background might also return a 3-tuple or just stop
            stop_tuple = self.recorder.listen_energy_in_background(self.source, recordCallback)
            if isinstance(stop_tuple, tuple) and len(stop_tuple) == 3:
                 self.stop, self.pause, self.resume = stop_tuple # type: ignore
            else:
                 self.stop = stop_tuple # type: ignore


class SelectedMicEnergyRecorder(BaseEnergyRecorder):
    """Energy recorder specifically for selected microphone devices."""
    def __init__(self, device: Dict[str, Any]) -> None:
        """
        Initializes the SelectedMicEnergyRecorder.

        Args:
            device: Dictionary with microphone device info (index, defaultSampleRate).
        """
        source=Microphone(
            device_index=device['index'],
            sample_rate=int(device["defaultSampleRate"]),
        )
        super().__init__(source=source)
        # self.adjustForNoise()

class SelectedSpeakerEnergyRecorder(BaseEnergyRecorder):
    def __init__(self, device: Dict[str, Any]) -> None:
        """
        Initializes the SelectedSpeakerEnergyRecorder.

        Args:
            device: Dictionary with speaker device info (index, defaultSampleRate, maxInputChannels).
        """
        source = Microphone(speaker=True, # type: ignore
            device_index=device["index"],
            sample_rate=int(device["defaultSampleRate"]),
            channels=device["maxInputChannels"]
        )
        super().__init__(source=source)
        # self.adjustForNoise()

class BaseEnergyAndAudioRecorder:
    """Base class for recorders that capture both audio data and energy levels."""
    recorder: Recognizer
    source: AudioSource
    phrase_time_limit: Optional[float] # Max seconds for a phrase before cutting off
    phrase_timeout: float      # Max seconds of silence after speech before considering phrase complete
    record_timeout: Optional[float]  # How long to record audio after speech stops
    stop: StopCallable
    pause: Optional[Callable[[], None]]
    resume: Optional[Callable[[], None]]

    def __init__(self, source: AudioSource, energy_threshold: float, dynamic_energy_threshold: bool, 
                 phrase_time_limit: Optional[float], phrase_timeout: float, record_timeout: Optional[float]) -> None:
        """
        Initializes the BaseEnergyAndAudioRecorder.

        Args:
            source: The audio source.
            energy_threshold: Energy threshold for speech detection.
            dynamic_energy_threshold: Whether to dynamically adjust energy threshold.
            phrase_time_limit: Maximum duration of a phrase.
            phrase_timeout: Silence duration to mark end of phrase.
            record_timeout: Duration to continue recording after speech ends.
        """
        self.recorder = Recognizer()
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = dynamic_energy_threshold
        self.phrase_time_limit = phrase_time_limit
        self.phrase_timeout = phrase_timeout
        self.record_timeout = record_timeout # This is passed to listen_energy_and_audio_in_background
        self.stop: StopCallable = None
        self.pause: Optional[Callable[[], None]] = None
        self.resume: Optional[Callable[[], None]] = None

        if source is None:
            raise ValueError("Audio source can't be None")
        self.source = source

    def adjustForNoise(self) -> None:
        """Adjusts the recorder's energy threshold based on ambient noise."""
        if self.source:
            with self.source:
                self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, audio_queue: Queue[Tuple[bytes, datetime]], energy_queue: Optional[Queue[float]] = None) -> None:
        """
        Starts listening for audio and energy, putting results into respective queues.

        Args:
            audio_queue: Queue for (audio_bytes, timestamp) tuples.
            energy_queue: Optional queue for energy float values.
        """
        def audioRecordCallback(_recognizer: Recognizer, audio: AudioData) -> None:
            """Internal callback for audio data."""
            audio_queue.put((audio.get_raw_data(), datetime.now()))

        energy_callback_for_listen: Optional[Callable[[float], None]] = None
        if energy_queue is not None:
            # Need a properly typed wrapper if energy_queue is provided
            def energyRecordCallbackWrapper(energy_level: float) -> None:
                if energy_queue: # Double check, though type system should ensure if not None
                     energy_queue.put(energy_level)
            energy_callback_for_listen = energyRecordCallbackWrapper
        
        if self.source:
            stop_tuple = self.recorder.listen_energy_and_audio_in_background( # type: ignore
                source=self.source,
                callback=audioRecordCallback,
                phrase_time_limit=self.phrase_time_limit,
                callback_energy=energy_callback_for_listen,
                phrase_timeout=self.phrase_timeout,
                record_timeout=self.record_timeout 
            )
            if isinstance(stop_tuple, tuple) and len(stop_tuple) == 3:
                 self.stop, self.pause, self.resume = stop_tuple # type: ignore
            else: # Should be just the stop function
                 self.stop = stop_tuple # type: ignore


class SelectedMicEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    """Energy and audio recorder for selected microphone devices."""
    def __init__(self, device: Dict[str, Any], energy_threshold: float, dynamic_energy_threshold: bool, 
                 phrase_time_limit: Optional[float], phrase_timeout: float = 1.0, record_timeout: Optional[float] = 5.0) -> None:
        """
        Initializes SelectedMicEnergyAndAudioRecorder.

        Args:
            device: Microphone device information.
            energy_threshold: Energy threshold.
            dynamic_energy_threshold: Dynamic energy adjustment.
            phrase_time_limit: Max phrase duration.
            phrase_timeout: Silence duration for phrase end.
            record_timeout: Post-speech recording duration.
        """
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