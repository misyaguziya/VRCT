"""PCM16 capture source; PyAudio lifecycle is serialized by the caller's lock.

Stream behavior follows SpeechRecognition's Microphone adapter. See the BSD
notice in google_speech_LICENSE.txt. No recognition or device selection lives here.
"""

import math

import pyaudiowpatch as pyaudio

from .native_audio import get_rust_devices


class _CaptureStream:
    def __init__(self, stream):
        self.pyaudio_stream = stream

    def read(self, size):
        return self.pyaudio_stream.read(size, exception_on_overflow=False)

    def close(self):
        try:
            if not self.pyaudio_stream.is_stopped():
                self.pyaudio_stream.stop_stream()
        except OSError:
            pass
        finally:
            try:
                self.pyaudio_stream.close()
            except OSError:
                pass


class AudioCaptureSource:
    SAMPLE_WIDTH = 2

    def __init__(self, device_index=None, sample_rate=None, chunk_size=1024,
                 speaker=False, channels=1, device_name=None):
        if device_index is not None and (type(device_index) is not int or device_index < 0):
            raise ValueError("device_index must be a nonnegative integer or None")
        if sample_rate is not None and (type(sample_rate) is not int or sample_rate <= 0):
            raise ValueError("sample_rate must be a positive integer or None")
        if type(chunk_size) is not int or chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        if type(channels) is not int or channels <= 0:
            raise ValueError("channels must be a positive integer")
        self._rust = get_rust_devices()
        self.device_name = device_name if device_index is not None else None
        if self._rust is not None and sample_rate is None:
            listed = self._rust.list_devices()
            default = next((d for d in listed["inputs"] if d["name"] == listed["default_input"]), None)
            if default is None:
                raise OSError("no default input device")
            sample_rate = int(default["defaultSampleRate"])
        if sample_rate is None:
            audio = pyaudio.PyAudio()
            try:
                self._validate_index(audio, device_index)
                info = (audio.get_default_input_device_info() if device_index is None
                        else audio.get_device_info_by_index(device_index))
                rate = info.get("defaultSampleRate")
                if type(rate) not in (int, float) or not math.isfinite(rate) or rate < 1:
                    raise ValueError("invalid device sample rate")
                sample_rate = int(rate)
            except BaseException:
                try:
                    audio.terminate()
                except BaseException:
                    pass
                raise
            else:
                audio.terminate()
        self.device_index = device_index
        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.channels = channels if speaker else 1
        self.audio = None
        self.stream = None

    @staticmethod
    def _validate_index(audio, index):
        count = audio.get_device_count()
        if index is not None and index >= count:
            raise ValueError("device_index is outside the available device range")

    def __enter__(self):
        if self.audio is not None or self.stream is not None:
            raise RuntimeError("capture source is already open")
        if self._rust is not None:
            stream = self._rust.Capture(self.device_name)
            if stream.sample_rate != self.SAMPLE_RATE or stream.channels != self.channels:
                # the device's format changed since it was listed
                stream.close()
                raise OSError("the audio device's format changed")
            self.stream = _CaptureStream(stream)
            return self
        audio = pyaudio.PyAudio()
        try:
            self._validate_index(audio, self.device_index)
            stream = audio.open(input_device_index=self.device_index, channels=self.channels,
                                format=pyaudio.paInt16, rate=self.SAMPLE_RATE,
                                frames_per_buffer=self.CHUNK, input=True)
        except BaseException:
            # Preserve the open/metadata exception even when cleanup also fails.
            try:
                audio.terminate()
            except Exception:
                pass
            raise
        self.audio = audio
        self.stream = _CaptureStream(stream)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        stream, audio = self.stream, self.audio
        self.stream = None
        self.audio = None
        cleanup_error = None
        try:
            if stream is not None:
                stream.close()
        except BaseException as error:
            cleanup_error = error
        try:
            if audio is not None:
                audio.terminate()
        except BaseException as error:
            if cleanup_error is None:
                cleanup_error = error
        # Preserve body > stream close > PyAudio terminate, but never skip cleanup.
        if exc_value is None and cleanup_error is not None:
            raise cleanup_error
