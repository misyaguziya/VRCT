"""Validation-only PyInstaller runtime hook for tools/check_frozen_e2e.py.

Inert unless VRCT_FROZEN_E2E_DIR is set. Replaces only the capture source with
a WAV played in real time, forbids real recording and network access, and
records which ASR providers ran. Builds containing it are not release builds.
"""
import os

if os.environ.get("VRCT_FROZEN_E2E_DIR"):
    import atexit
    import collections
    import ipaddress
    import json
    import sys
    import threading
    import time
    import wave
    from pathlib import Path

    run_dir = Path(os.environ["VRCT_FROZEN_E2E_DIR"])
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      DO_NOT_TRACK="1")
    counts = collections.Counter()
    state = {"frozen": bool(getattr(sys, "frozen", False)), "opens": []}

    def audit(event, args):
        if event in ("socket.connect", "socket.sendto", "socket.bind"):
            counts["blocked_" + event] += 1
            raise OSError("Network disabled by frozen E2E validation")
        if event == "socket.getaddrinfo":
            try:
                ipaddress.ip_address(args[0])
            except ValueError:
                counts["blocked_dns"] += 1
                raise OSError("DNS disabled by frozen E2E validation") from None

    sys.addaudithook(audit)
    import requests

    def no_http(*args, **kwargs):
        counts["blocked_requests"] += 1
        raise requests.ConnectionError("HTTP disabled by frozen E2E validation")

    requests.sessions.Session.request = no_http
    import pyaudiowpatch

    def no_recording(*args, **kwargs):
        counts["real_recording_opens"] += 1
        raise OSError("Real recording disabled by frozen E2E validation")

    pyaudiowpatch.PyAudio.open = no_recording
    from models.clipboard import clipboard
    clipboard.checkSteamvrRunning = lambda: False

    with wave.open(os.environ["VRCT_FROZEN_E2E_WAV"]) as w:
        wav_rate, wav_channels, timeline = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    chunk = 1024

    class PacedWavSource:
        """Clock-driven stand-in for AudioCaptureSource (see tools/check_audio_e2e.py)."""

        SAMPLE_WIDTH = 2

        def __init__(self, device_index=None, sample_rate=None, chunk_size=chunk, speaker=False, channels=1):
            self.device_index, self.SAMPLE_RATE, self.CHUNK = device_index, wav_rate, chunk
            self.channels = wav_channels
            self.stream = self.pyaudio_stream = None
            self.t0, self._consumed, self._stopped = None, 0, threading.Event()

        def __enter__(self):
            self._stopped.clear()
            self.stream = self.pyaudio_stream = self
            self.t0, self._consumed = time.monotonic(), 0
            state["opens"].append(self.t0)
            return self

        def __exit__(self, *exc):
            self._stopped.set()
            self.stream = self.pyaudio_stream = None

        def is_stopped(self):
            return self._stopped.is_set()

        def stop_stream(self):
            self._stopped.set()

        def close(self):
            self._stopped.set()

        def get_read_available(self):
            return max(0, int((time.monotonic() - self.t0) * self.SAMPLE_RATE) - self._consumed)

        def read(self, count, exception_on_overflow=False):
            due = self.t0 + (self._consumed + count) / self.SAMPLE_RATE
            if self._stopped.wait(max(0.0, due - time.monotonic())):
                raise OSError("Stream is stopped")
            frame = 2 * self.channels
            data = timeline[self._consumed * frame:(self._consumed + count) * frame]
            self._consumed += count
            return data + bytes(count * frame - len(data))

    from models.transcription import transcription_providers, transcription_recorder
    transcription_recorder.AudioCaptureSource = PacedWavSource

    def counted(cls, name):
        original = cls.transcribe

        def wrapper(self, *args, **kwargs):
            counts[name] += 1
            return original(self, *args, **kwargs)
        cls.transcribe = wrapper

    counted(transcription_providers.LocalWhisperProvider, "whisper_calls")
    counted(transcription_providers.GoogleProvider, "google_calls")
    counted(transcription_providers.OpenAICompatibleTranscriptionProvider, "api_calls")

    def save():
        config = getattr(sys.modules.get("config"), "config", None)  # None while still importing
        if config is not None:
            state["config"] = {"engine": config.SELECTED_TRANSCRIPTION_ENGINE,
                               "weight": config.WHISPER_WEIGHT_TYPE,
                               "compute_device": config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE.get("device"),
                               "compute_type": config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE}
        try:
            import vrct_audio
            import hashlib
            state["native_sha256"] = hashlib.sha256(Path(vrct_audio.vrct_audio.__file__).read_bytes()).hexdigest()
        except Exception as error:  # recorded, not raised, at exit
            state["native_sha256"] = repr(error)
        state["counts"] = dict(counts)
        (run_dir / "worker-result.json").write_text(json.dumps(state, indent=2), encoding="utf-8")

    def save_periodically():
        # The UI never waits for the sidecar to exit: it sends /run/shutdown and
        # Tauri terminates the process ~2 s later, so atexit alone is not enough.
        while True:
            time.sleep(1)
            try:
                save()
            except Exception as error:  # keep the last good result; retry next tick
                state["save_error"] = repr(error)

    atexit.register(save)
    threading.Thread(target=save_periodically, name="FrozenE2EResult", daemon=True).start()
