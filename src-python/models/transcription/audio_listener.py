"""Python device/thread ownership with native energy phrase detection.

Microphone and its lock/unblock wrappers remain owned by transcription_recorder.
Listener timing follows the pinned SpeechRecognition fork (BSD notice alongside
google_speech.py). Native code never calls Python or owns a device.
"""

from dataclasses import dataclass
import threading
import time

from .native_audio import require_native_audio


@dataclass(frozen=True)
class _AudioPacket:
    raw: bytes
    segment_reason: str | None = None

    def get_raw_data(self):
        return self.raw


def create_listener(on_error):
    return NativeAudioListener(require_native_audio(), on_error)


class NativeAudioListener:
    """Existing recorder-facing API, without SpeechRecognition listener calls."""

    def __init__(self, native, on_error):
        self._native = native
        self._on_error = on_error
        self.energy_threshold = 300
        self.dynamic_energy_threshold = True
        self.dynamic_energy_adjustment_damping = 0.15
        self.dynamic_energy_ratio = 1.5
        self.pause_threshold = 0.8
        self.phrase_threshold = 0.3
        self.non_speaking_duration = 0.5

    def _detector(self, source, phrase_time_limit=0, record_timeout=float("inf"), phrase_timeout=1):
        if source.SAMPLE_WIDTH != 2:
            raise ValueError("native listener requires PCM16LE capture")
        return self._native.EnergyDetector(
            source.SAMPLE_RATE, source.CHUNK, self.energy_threshold,
            self.dynamic_energy_threshold, phrase_time_limit or 0,
            record_timeout, phrase_timeout or 0, self.pause_threshold,
            self.phrase_threshold, self.non_speaking_duration,
            self.dynamic_energy_adjustment_damping, self.dynamic_energy_ratio,
        )

    def adjust_for_ambient_noise(self, source, duration=1):
        detector = self._detector(source)
        elapsed = 0.0
        while True:
            elapsed += source.CHUNK / source.SAMPLE_RATE
            if elapsed > duration:
                break
            detector.calibrate(self._native.rms_pcm16(source.stream.read(source.CHUNK)))
        self.energy_threshold = detector.energy_threshold

    def _start(self, source, run, flush=None):
        stopped = threading.Event()
        resumed = threading.Event()
        resumed.set()

        def boundary():
            resumed.wait()
            return not stopped.is_set()

        def worker():
            try:
                with source as opened:
                    try:
                        run(opened, stopped, boundary)
                    finally:
                        if flush is not None:
                            flush()
            except Exception as error:
                if not stopped.is_set():
                    self._on_error(error)

        thread = threading.Thread(target=worker, daemon=True)

        def stop(wait_for_stop=True):
            stopped.set()
            resumed.set()
            if wait_for_stop and threading.current_thread() is not thread:
                thread.join()

        thread.start()
        return stop, resumed.clear, resumed.set

    def listen_energy_and_audio_in_background(
        self, source, callback, phrase_time_limit=None, callback_energy=None,
        phrase_timeout=1, record_timeout=5,
    ):
        detector = self._detector(source, phrase_time_limit, record_timeout, phrase_timeout)

        def run(opened, stopped, boundary):
            try:
                while not stopped.is_set():
                    action, audio = detector.before_read(time.monotonic())
                    if action != "READ":
                        if audio is not None and not stopped.is_set():
                            callback(self, _AudioPacket(audio))
                        if action == "EOF" or not boundary():
                            break
                        continue
                    if detector.waiting and opened.stream.pyaudio_stream.get_read_available() == 0:
                        detector.cancel()
                        if stopped.wait(0.01) or not boundary():
                            break
                        continue
                    raw = opened.stream.read(opened.CHUNK)
                    if stopped.is_set():
                        break
                    energy = detector.push(raw, time.monotonic())
                    self.energy_threshold = detector.energy_threshold
                    if callback_energy is not None:
                        callback_energy(energy)
            finally:
                detector.cancel()  # Energy stop never emits an unfinished phrase.

        return self._start(source, run)

    def listen_with_segmenter_in_background(
        self, source, callback, segmenter, callback_energy=None, record_timeout=5,
    ):
        if source.SAMPLE_WIDTH != 2:
            raise ValueError("native listener requires PCM16LE capture")

        def deliver(segment):
            callback(self, _AudioPacket(segment.audio, getattr(segment, "reason", None)))

        def run(opened, stopped, boundary):
            started = time.monotonic()
            while not stopped.is_set():
                if record_timeout > 0 and time.monotonic() - started > record_timeout:
                    if not boundary():
                        break
                    started = time.monotonic()
                    # The model/segmenter state survives a listener timeout.
                raw = opened.stream.read(opened.CHUNK)
                if stopped.is_set():
                    break
                if callback_energy is not None:
                    callback_energy(self._native.rms_pcm16(raw))
                if not raw:
                    break
                segments = segmenter.process(raw)
                for segment in segments:
                    # A completed batch is delivered in full even if stop is
                    # requested by the first callback; flush cannot recover it.
                    deliver(segment)
                if segments:
                    if not boundary():
                        break
                    started = time.monotonic()

        def flush():
            flush_segmenter = getattr(segmenter, "flush", None)
            if callable(flush_segmenter):
                segment = flush_segmenter()
                if segment is not None:
                    deliver(segment)

        return self._start(source, run, flush)
