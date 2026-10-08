"""Capture lifecycle tests use fake PyAudio only; never open a real device."""

from collections import deque
import os
from queue import Queue
import subprocess
import sys
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from models.transcription.audio_listener import create_listener
from models.transcription.audio_source import AudioCaptureSource
from models.transcription.transcription_recorder import (
    BaseEnergyAndAudioRecorder, BaseVadAndAudioRecorder, _LockedAudioSource,
    _create_microphone,
)
from device_manager import pyaudio_op_lock


@pytest.fixture
def audio_factory():
    with patch("models.transcription.audio_source.pyaudio.PyAudio") as factory:
        factory.return_value.get_device_count.return_value = 5
        factory.return_value.get_default_input_device_info.return_value = {"defaultSampleRate": 44100.0}
        factory.return_value.get_device_info_by_index.return_value = {"defaultSampleRate": 48000.0}
        yield factory


def test_explicit_rate_does_not_initialize_pyaudio(audio_factory):
    source = AudioCaptureSource(device_index=2, sample_rate=48000, channels=8)
    audio_factory.assert_not_called()
    assert (source.SAMPLE_WIDTH, source.SAMPLE_RATE, source.CHUNK, source.channels) == (2, 48000, 1024, 1)
    with source:
        audio_factory.return_value.open.assert_called_once_with(
            input_device_index=2, channels=1, format=8, rate=48000,
            frames_per_buffer=1024, input=True,
        )
    assert source.audio is source.stream is None


@pytest.mark.parametrize("index,rate", [(None, 44100), (2, 48000)])
def test_default_rate_resolution_terminates_temporary_instance(audio_factory, index, rate):
    source = AudioCaptureSource(device_index=index, speaker=True)
    assert source.SAMPLE_RATE == rate
    assert source.channels == 1
    audio_factory.assert_called_once()
    audio_factory.return_value.terminate.assert_called_once()


@pytest.mark.parametrize("kwargs", [dict(device_index=-1), dict(device_index=True), dict(sample_rate=0),
    dict(sample_rate=1.5), dict(channels=0), dict(channels=True), dict(chunk_size=0)])
def test_invalid_parameters_never_touch_pyaudio(audio_factory, kwargs):
    with pytest.raises(ValueError):
        AudioCaptureSource(**kwargs)
    audio_factory.assert_not_called()


@pytest.mark.parametrize("rate", [None, 0, -1, float("nan"), float("inf"), True])
def test_invalid_metadata_is_cleaned_up(audio_factory, rate):
    audio_factory.return_value.get_default_input_device_info.return_value = {"defaultSampleRate": rate}
    with pytest.raises(ValueError):
        AudioCaptureSource()
    audio_factory.return_value.terminate.assert_called_once()


def test_metadata_failure_takes_precedence_over_terminate_failure(audio_factory):
    original = OSError("metadata")
    audio_factory.return_value.get_default_input_device_info.side_effect = original
    audio_factory.return_value.terminate.side_effect = RuntimeError("terminate")
    with pytest.raises(OSError) as caught:
        AudioCaptureSource()
    assert caught.value is original
    audio_factory.return_value.terminate.assert_called_once()


def test_metadata_success_does_not_hide_terminate_failure(audio_factory):
    original = RuntimeError("terminate")
    audio_factory.return_value.terminate.side_effect = original
    with pytest.raises(RuntimeError) as caught:
        AudioCaptureSource()
    assert caught.value is original


def test_out_of_range_is_rejected_before_open_and_falls_back(audio_factory):
    source = _create_microphone({}, device_index=9, sample_rate=48000)
    assert source.device_index is None
    assert source.SAMPLE_RATE == 44100
    assert audio_factory.call_count == 3  # rejected enter, default-rate resolve, probe
    audio_factory.return_value.open.assert_called_once()
    assert audio_factory.return_value.terminate.call_count == 3
    assert source.audio is source.stream is None


@pytest.mark.parametrize("failure", ["metadata", "open"])
def test_enter_failure_preserves_original_exception_and_clears_state(audio_factory, failure):
    source = AudioCaptureSource(sample_rate=16000)
    original = OSError(failure)
    method = "get_device_count" if failure == "metadata" else "open"
    getattr(audio_factory.return_value, method).side_effect = original
    audio_factory.return_value.terminate.side_effect = RuntimeError("cleanup")
    with pytest.raises(OSError) as caught:
        source.__enter__()
    assert caught.value is original
    assert source.audio is source.stream is None
    audio_factory.return_value.terminate.assert_called_once()


@pytest.mark.parametrize("failure", ["is_stopped", "stop_stream", "close"])
def test_stream_close_tolerates_oserrors(audio_factory, failure):
    stream = audio_factory.return_value.open.return_value
    stream.is_stopped.return_value = False
    getattr(stream, failure).side_effect = OSError("unplugged")
    source = AudioCaptureSource(sample_rate=48000, speaker=True, channels=2)
    with source:
        assert source.channels == 2
    stream.close.assert_called_once()
    audio_factory.return_value.terminate.assert_called_once()
    assert source.audio is source.stream is None


def test_close_failure_still_terminates_and_reopen_is_supported(audio_factory):
    source = AudioCaptureSource(sample_rate=16000)
    stream = audio_factory.return_value.open.return_value
    stream.close.side_effect = RuntimeError("close")
    with pytest.raises(RuntimeError, match="close"):
        with source:
            pass
    assert source.audio is source.stream is None
    source.__exit__(None, None, None)
    audio_factory.return_value.terminate.assert_called_once()
    stream.close.side_effect = None
    with source:
        with pytest.raises(RuntimeError, match="already open"):
            source.__enter__()
    assert audio_factory.return_value.terminate.call_count == 2


@pytest.mark.parametrize("body_fails,close_fails", [(True, True), (True, False), (False, True), (False, False)])
def test_exit_failure_priority_and_cleanup(audio_factory, body_fails, close_fails):
    body_error = ValueError("body")
    close_error = RuntimeError("close")
    terminate_error = OSError("terminate")
    stream = audio_factory.return_value.open.return_value
    if close_fails:
        stream.close.side_effect = close_error
    audio_factory.return_value.terminate.side_effect = terminate_error
    source = AudioCaptureSource(sample_rate=16000)
    expected = body_error if body_fails else close_error if close_fails else terminate_error
    with pytest.raises(type(expected)) as caught:
        with source:
            if body_fails:
                raise body_error
    assert caught.value is expected
    stream.close.assert_called_once()
    audio_factory.return_value.terminate.assert_called_once()
    assert source.audio is source.stream is None
    source.__exit__(None, None, None)
    audio_factory.return_value.terminate.assert_called_once()


def test_read_overflow_and_read_error_reporting(audio_factory):
    source = _LockedAudioSource(AudioCaptureSource(sample_rate=16000))
    errors = []
    source.set_read_error_handler(errors.append)
    stream = audio_factory.return_value.open.return_value
    stream.read.side_effect = OSError("read")
    with source as opened:
        assert opened.stream.pyaudio_stream is stream
        with pytest.raises(OSError, match="read"):
            opened.stream.read(1024)
    stream.read.assert_called_once_with(1024, exception_on_overflow=False)
    assert len(errors) == 1


def test_open_error_reports_through_locked_source(audio_factory):
    source = _LockedAudioSource(AudioCaptureSource(sample_rate=16000))
    errors = []
    source.set_read_error_handler(errors.append)
    audio_factory.return_value.open.side_effect = OSError("open")
    with pytest.raises(OSError, match="open"):
        source.__enter__()
    assert len(errors) == 1


class ControlledStream:
    def __init__(self, chunks=()):
        self.chunks = deque(chunks)
        self.blocked = threading.Event()
        self.stopped = threading.Event()
        self.closed = threading.Event()

    def get_read_available(self):
        return 1024

    def read(self, count, exception_on_overflow=False):
        assert count == 1024 and exception_on_overflow is False
        if self.chunks:
            return self.chunks.popleft()
        self.blocked.set()
        assert self.stopped.wait(3), "test must stop capture"
        raise OSError("stopped")

    def is_stopped(self):
        return self.stopped.is_set()

    def stop_stream(self):
        self.stopped.set()

    def close(self):
        self.closed.set()


@pytest.mark.parametrize("mode", ["energy", "vad"])
def test_native_accepts_plain_capture_and_stops(audio_factory, mode):
    stream = ControlledStream([b"\xd0\x07" * 1024] * 10 + [b"\0\0" * 1024] * 15)
    audio_factory.return_value.open.return_value = stream
    source = _LockedAudioSource(AudioCaptureSource(sample_rate=16000))
    with patch("models.transcription.audio_listener.require_native_audio", return_value=pytest.importorskip("vrct_audio")):
        recorder = (BaseEnergyAndAudioRecorder(source, 300, False, 3, 3) if mode == "energy"
                    else BaseVadAndAudioRecorder(source, 3))
    if mode == "vad":
        segmenter = SimpleNamespace(sample_rate=16000, sample_width=2,
            process=MagicMock(return_value=[SimpleNamespace(audio=b"\1\0", reason="silence")]),
            flush=MagicMock(return_value=None))
        recorder._error_reporting_segmenter = segmenter
    output = Queue()
    recorder.recordIntoQueue(output)
    assert output.get(timeout=2)[0]
    assert stream.blocked.wait(2)
    recorder.stop()
    recorder.stop()
    assert stream.closed.is_set()
    assert not recorder.device_error_event.is_set()
    audio_factory.return_value.terminate.assert_called_once()


def test_native_calibration_does_not_reenter_source(audio_factory):
    stream = ControlledStream([b"\x64\0" * 1024] * 16)
    audio_factory.return_value.open.return_value = stream
    source = _LockedAudioSource(AudioCaptureSource(sample_rate=16000))
    with patch("models.transcription.audio_listener.require_native_audio", return_value=pytest.importorskip("vrct_audio")):
        recorder = BaseEnergyAndAudioRecorder(source, 300, True, 3, 3)
    recorder.adjustForNoise()
    assert 150 < recorder.recorder.energy_threshold < 300
    audio_factory.return_value.open.assert_called_once()
    audio_factory.return_value.terminate.assert_called_once()


def test_native_stop_wakes_pause_loop(audio_factory):
    stream = ControlledStream([b"\xd0\x07" * 1024] * 10 + [b"\0\0" * 1024] * 15)
    audio_factory.return_value.open.return_value = stream
    source = _LockedAudioSource(AudioCaptureSource(sample_rate=16000))
    entered, release = threading.Event(), threading.Event()
    with patch("models.transcription.audio_listener.require_native_audio", return_value=pytest.importorskip("vrct_audio")):
        listener = create_listener(MagicMock())
    listener.dynamic_energy_threshold = False

    def callback(*_):
        entered.set()
        assert release.wait(2)

    stop, pause, _ = listener.listen_energy_and_audio_in_background(source, callback)
    assert entered.wait(2)
    pause()
    release.set()
    # A bounded joining thread makes a regression fail instead of hanging pytest.
    joining = threading.Thread(target=stop, daemon=True)
    joining.start()
    joining.join(2)
    assert not joining.is_alive()
    assert stream.closed.is_set()


@pytest.mark.parametrize("phase", ["before_open", "during_open", "during_close"])
def test_stop_races_are_serialized_and_cleanup_once(audio_factory, phase):
    native = pytest.importorskip("vrct_audio")
    entered, release = threading.Event(), threading.Event()
    stream = ControlledStream()
    if phase == "during_close":
        stream.chunks.append(b"")

        def close():
            entered.set()
            assert release.wait(2)
            stream.closed.set()

        stream.close = close
    elif phase == "during_open":
        def open_stream(**kwargs):
            entered.set()
            assert release.wait(2)
            return stream

        audio_factory.return_value.open.side_effect = open_stream
    audio_factory.return_value.open.return_value = stream
    source = _LockedAudioSource(AudioCaptureSource(sample_rate=16000))
    with patch("models.transcription.audio_listener.require_native_audio", return_value=native):
        recorder = BaseEnergyAndAudioRecorder(source, 300, False, 3, 3)
    if phase == "before_open":
        pyaudio_op_lock.acquire()
    try:
        recorder.recordIntoQueue(Queue())
        if phase != "before_open":
            assert entered.wait(2)
        joining = threading.Thread(target=recorder.stop, daemon=True)
        joining.start()
    finally:
        if phase == "before_open":
            pyaudio_op_lock.release()
        release.set()
    joining.join(2)
    assert not joining.is_alive()
    assert stream.closed.is_set()
    assert source.stream is source.audio is None
    audio_factory.return_value.terminate.assert_called_once()


def test_probe_timeout_late_success_does_not_double_terminate(audio_factory):
    entered, release, closed = threading.Event(), threading.Event(), threading.Event()
    stream = MagicMock()
    stream.close.side_effect = closed.set

    def open_stream(**kwargs):
        entered.set()
        assert release.wait(2)
        return stream

    audio_factory.return_value.open.side_effect = open_stream
    with patch("models.transcription.transcription_recorder._MIC_OPEN_TIMEOUT_SEC", 0.02):
        with pytest.raises(OSError, match="Timed out"):
            _create_microphone({}, sample_rate=16000)
    assert entered.is_set()
    release.set()
    assert closed.wait(2)
    # Wait for the probe's lock to be released after terminate and state clearing.
    with pyaudio_op_lock:
        audio_factory.return_value.terminate.assert_called_once()


def test_native_recorder_runs_with_speech_recognition_import_forbidden():
    pytest.importorskip("vrct_audio")
    script = '''
import importlib.abc, sys, threading
class Deny(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, *args):
  if fullname == "speech_recognition" or fullname.startswith("speech_recognition."):
   raise AssertionError("SpeechRecognition import forbidden")
sys.meta_path.insert(0, Deny())
from unittest.mock import MagicMock, patch
from models.transcription.audio_source import AudioCaptureSource
from models.transcription.transcription_recorder import BaseEnergyAndAudioRecorder, _LockedAudioSource
from queue import Queue
stream = MagicMock()
closed = threading.Event()
stream.close.side_effect = closed.set
stream.get_read_available.return_value = 1024
stream.read.side_effect = [b"\\xd0\\x07" * 1024] * 10 + [b"\\0\\0" * 1024] * 15 + [b""]
with patch("models.transcription.audio_source.pyaudio.PyAudio") as factory:
 factory.return_value.get_device_count.return_value = 1
 factory.return_value.open.return_value = stream
 recorder = BaseEnergyAndAudioRecorder(_LockedAudioSource(AudioCaptureSource(sample_rate=16000)),300,False,3,3)
 output = Queue()
 recorder.recordIntoQueue(output)
 assert output.get(timeout=2)[0]
 assert closed.wait(2)
 recorder.stop()
 assert not recorder.device_error_event.is_set()
 assert "speech_recognition" not in sys.modules
'''
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                            timeout=15, env=os.environ.copy())
    assert result.returncode == 0, result.stdout + result.stderr
