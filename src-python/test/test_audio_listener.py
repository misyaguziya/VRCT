"""No devices: fixed-fork differential tests and controlled thread/stream tests."""

import audioop
import hashlib
import json
from pathlib import Path
from collections import deque
from queue import Queue
import struct
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from models.transcription.audio_listener import NativeAudioListener, create_listener
from models.transcription.transcription_recorder import BaseEnergyAndAudioRecorder

GOLDEN = json.loads((Path(__file__).parent / "fixtures/legacy_audio_contracts.json").read_text(encoding="utf-8"))


@pytest.fixture
def native():
    return pytest.importorskip("vrct_audio")


def chunk(value, channels=1):
    return struct.pack("<h", value) * (1024 * channels)


class FakeSource:
    SAMPLE_WIDTH = 2
    CHUNK = 1024

    def __init__(self, chunks=(), rate=16000, channels=1, clock=None):
        self.SAMPLE_RATE = rate
        self.channels = channels
        self.chunks = deque(chunks)
        self.stream = self
        self.pyaudio_stream = self
        self.clock = clock
        self.closed = threading.Event()
        self.read_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed.set()

    def get_read_available(self):
        return 1024

    def read(self, count):
        assert count == self.CHUNK
        self.read_count += 1
        if self.clock is not None:
            self.clock[0] += self.CHUNK / self.SAMPLE_RATE
        return self.chunks.popleft() if self.chunks else b""


@pytest.mark.parametrize("rate,channels", [(16000, 1), (48000, 1), (48000, 2)])
@pytest.mark.parametrize("case", ["phrase", "equal", "short", "preroll", "dynamic", "phrase_limit", "wall_limit", "wait_limit", "eof"])
def test_energy_matches_pinned_fork(native, rate, channels, case):
    values = [0] * 4 + [2000] * 30 + [0] * 50
    settings = dict(phrase_time_limit=None, record_timeout=5, timeout=1)
    if case == "equal":
        values = [300] * 100
    elif case == "short":
        values = [2000] + [0] * 50 + [2000] * 30 + [0] * 50
        settings["timeout"] = 10
    elif case == "preroll":
        values = [100] * 20 + [2000] * 30 + [0] * 50
        settings["timeout"] = 10
    elif case == "dynamic":
        values = [100] * 8 + [2000] * 30 + [0] * 50
    elif case == "phrase_limit":
        values = [2000] * 200
        settings["phrase_time_limit"] = 0.7
    elif case == "wall_limit":
        values = [2000] * 200
        settings["record_timeout"] = 0.1
    elif case == "wait_limit":
        values = [0] * 200
    elif case == "eof":
        values = [0, 2000, 2000]
    chunks = [chunk(v, channels) for v in values]
    expected = GOLDEN["energy"][f"{rate}/{channels}/{case}"]

    detector = native.EnergyDetector(rate, 1024, 300, case == "dynamic",
        settings["phrase_time_limit"] or 0, settings["record_timeout"], settings["timeout"])
    new_energy = []
    clock = [0.0]
    new_source = FakeSource(chunks, rate, channels, clock)
    for _ in range(1000):
        action, actual = detector.before_read(clock[0])
        if action != "READ":
            break
        pcm = new_source.read(1024)
        new_energy.append(detector.push(pcm, clock[0]))
    else:
        pytest.fail("detector did not terminate")
    assert ("PHRASE" if action == "EOF" else action) == expected["action"]
    assert (hashlib.sha256(actual).hexdigest() if actual is not None else None) == expected["pcm_sha256"]
    assert (len(actual) if actual is not None else None) == expected["pcm_bytes"]
    assert new_energy == expected["energy"]
    assert new_source.read_count == expected["reads"]
    assert detector.energy_threshold == pytest.approx(expected["threshold"], abs=1e-9)


@pytest.mark.parametrize("case,expected", [
    # The fork dropped this phrase (RETRY): the wall clock beat the equal phrase limit.
    ("wall_limit_long", [("PHRASE", 9), ("PHRASE", 10), ("RETRY", 0)]),
    # The fork rejected the 3-buffer tail of a phrase-limit split as too short.
    ("split_tail", [("PHRASE", 11), ("PHRASE", 11), ("RETRY", 0)]),
    # After a real pause (> pause_threshold) a short blip is rejected as in the fork.
    ("split_pause_blip", [("PHRASE", 11), ("RETRY", 0)]),
])
def test_energy_time_limit_splits_keep_speech(native, case, expected):
    limit, wall, values = 0.7, 5, [2000] * 11
    if case == "wall_limit_long":
        limit, wall, values = 0, 0.5, [2000] * 9 + [0, 2000]
    elif case == "split_pause_blip":
        values += [0] * 14
    values += [2000] * (0 if case == "wall_limit_long" else 3) + [0] * 40
    detector = native.EnergyDetector(16000, 1024, 300, False, limit, wall, 1)
    source, clock, actions = FakeSource([chunk(v) for v in values]), [0.0], []
    source.clock = clock
    while not actions or actions[-1][0] != "RETRY":
        action, audio = detector.before_read(clock[0])
        if action == "READ":
            detector.push(source.read(1024), clock[0])
        else:
            actions.append((action, len(audio or b"") // 2048))
    assert actions == expected


def test_rms_extremes_and_interleaved_samples(native):
    for values in ([0], [-32768], [32767], [-32768, 32767, 1, -1], range(-32768, 32768, 17)):
        pcm = b"".join(struct.pack("<h", v) for v in values)
        assert native.rms_pcm16(pcm) == audioop.rms(pcm, 2)
    with pytest.raises(ValueError):
        native.rms_pcm16(b"x")


@pytest.mark.parametrize("byte_count", [16 * 1024 * 1024 - 2, 16 * 1024 * 1024, 16 * 1024 * 1024 + 2])
@pytest.mark.parametrize("pattern", [b"\x00\x80", struct.pack("<4h", -32768, 32767, 0, 1)])
def test_rms_integer_reduction_boundary_matches_audioop(native, byte_count, pattern):
    pcm = (pattern * (byte_count // len(pattern) + 1))[:byte_count]
    assert native.rms_pcm16(pcm) == audioop.rms(pcm, 2)


def test_selection_requires_native(native):
    with patch("models.transcription.audio_listener.require_native_audio", return_value=native):
        assert isinstance(create_listener(MagicMock()), NativeAudioListener)
    with patch("models.transcription.native_audio.get_native_audio", return_value=None):
        with pytest.raises(ImportError, match="Build/install"):
            create_listener(MagicMock())
    with patch("models.transcription.audio_listener.require_native_audio", side_effect=ImportError("broken")):
        with pytest.raises(ImportError):
            create_listener(MagicMock())


def test_energy_thread_delivers_and_closes_without_legacy_calls(native):
    errors, phrases, energies = [], [], []
    source = FakeSource([chunk(2000)] * 10 + [chunk(0)] * 15)
    listener = NativeAudioListener(native, errors.append)
    listener.dynamic_energy_threshold = False
    stop, _, _ = listener.listen_energy_and_audio_in_background(source, lambda _, audio: phrases.append(audio.raw), callback_energy=energies.append)
    assert source.closed.wait(2)
    stop()
    stop()
    assert not errors
    assert phrases[0].startswith(chunk(2000))
    assert len(energies) == source.read_count


class BlockingSource(FakeSource):
    def __init__(self):
        super().__init__()
        self.reading = threading.Event()
        self.unblock = threading.Event()
        self.stopped = False

    def read(self, count):
        self.reading.set()
        assert self.unblock.wait(2), "test must unblock stream"
        raise OSError("stream stopped")

    def is_stopped(self):
        return self.stopped

    def stop_stream(self):
        self.stopped = True
        self.unblock.set()


def test_existing_stopper_unblocks_native_read_and_discards_phrase(native):
    source = BlockingSource()
    with patch("models.transcription.audio_listener.require_native_audio", return_value=native):
        recorder = BaseEnergyAndAudioRecorder(source, 300, False, 3, 3)
    output = Queue()
    recorder.recordIntoQueue(output)
    assert source.reading.wait(2)
    recorder.stop()
    recorder.stop()
    assert source.closed.is_set()
    assert output.empty()
    assert not recorder.device_error_event.is_set()


def test_pause_applies_at_boundary_and_stop_wakes_it(native):
    source = FakeSource([chunk(2000)] * 10 + [chunk(0)] * 40)
    at_callback, release = threading.Event(), threading.Event()
    errors = []
    listener = NativeAudioListener(native, errors.append)
    listener.dynamic_energy_threshold = False

    def callback(*_):
        at_callback.set()
        assert release.wait(2)

    stop, pause, _ = listener.listen_energy_and_audio_in_background(source, callback)
    assert at_callback.wait(2)
    pause()
    count = source.read_count
    release.set()
    stop()
    assert source.closed.is_set()
    assert source.read_count == count
    assert not errors


@pytest.mark.parametrize("failure", ["open", "read", "callback"])
def test_thread_failures_report_and_close(native, failure):
    errors = []
    source = FakeSource([chunk(2000)] * 10 + [chunk(0)] * 30)
    if failure == "open":
        class BadSource(FakeSource):
            def __enter__(self):
                raise RuntimeError("open failed")
        source = BadSource()
    elif failure == "read":
        source.read = MagicMock(side_effect=RuntimeError("read failed"))
    callback = MagicMock(side_effect=RuntimeError("callback failed")) if failure == "callback" else MagicMock()
    listener = NativeAudioListener(native, errors.append)
    stop, _, _ = listener.listen_energy_and_audio_in_background(source, callback)
    stop_event = threading.Event()
    # Join only after failure: stopping first would intentionally suppress the report.
    for _ in range(200):
        if errors:
            break
        stop_event.wait(0.005)
    stop()
    assert len(errors) == 1
    assert str(errors[0]) == f"{failure} failed"
    assert failure == "open" or source.closed.is_set()


def test_vad_delivers_all_segments_and_flushes_once(native):
    source = FakeSource([chunk(123)])
    segments = [SimpleNamespace(audio=b"one", reason="max_duration"), SimpleNamespace(audio=b"two", reason="silence")]
    segmenter = SimpleNamespace(process=MagicMock(return_value=segments), flush=MagicMock(return_value=SimpleNamespace(audio=b"tail", reason="flush")))
    errors, output = [], []
    listener = NativeAudioListener(native, errors.append)
    stop, _, _ = listener.listen_with_segmenter_in_background(source, lambda _, audio: output.append((audio.raw, audio.segment_reason)), segmenter)
    assert source.closed.wait(2)
    stop()
    stop()
    assert output == [(b"one", "max_duration"), (b"two", "silence"), (b"tail", "flush")]
    segmenter.flush.assert_called_once()
    assert not errors


def test_vad_stop_flushes_once_after_read_unblock(native):
    source = BlockingSource()
    segmenter = SimpleNamespace(process=MagicMock(return_value=[]), flush=MagicMock(return_value=SimpleNamespace(audio=b"tail", reason="flush")))
    output, errors = [], []
    listener = NativeAudioListener(native, errors.append)
    stop, pause, _ = listener.listen_with_segmenter_in_background(source, lambda _, audio: output.append(audio.raw), segmenter, record_timeout=0.01)
    assert source.reading.wait(2)
    pause()
    stop(wait_for_stop=False)
    source.stop_stream()
    stop()
    assert output == [b"tail"]
    segmenter.flush.assert_called_once()
    assert not errors


def test_vad_timeout_does_not_reset_incomplete_segment(native):
    clock = [0.0]
    source = FakeSource([chunk(100)] * 3, clock=clock)
    segmenter = SimpleNamespace(
        process=MagicMock(side_effect=[[], [], [SimpleNamespace(audio=b"whole", reason="silence")]]),
        flush=MagicMock(return_value=None),
    )
    errors, output = [], []
    listener = NativeAudioListener(native, errors.append)
    with patch("models.transcription.audio_listener.time.monotonic", side_effect=lambda: clock[0]):
        stop, _, _ = listener.listen_with_segmenter_in_background(
            source, lambda _, audio: output.append(audio.raw), segmenter, record_timeout=0.01,
        )
        assert source.closed.wait(2)
        stop()
    assert output == [b"whole"]
    assert segmenter.process.call_count == 3
    segmenter.flush.assert_called_once()
    assert not errors


def test_stop_during_vad_callback_keeps_completed_batch(native):
    entered, release = threading.Event(), threading.Event()
    source = FakeSource([chunk(100)])
    segments = [SimpleNamespace(audio=b"one"), SimpleNamespace(audio=b"two")]
    segmenter = SimpleNamespace(process=MagicMock(return_value=segments), flush=MagicMock(return_value=None))
    output, errors = [], []

    def callback(_, audio):
        output.append(audio.raw)
        if audio.raw == b"one":
            entered.set()
            assert release.wait(2)

    listener = NativeAudioListener(native, errors.append)
    stop, _, _ = listener.listen_with_segmenter_in_background(source, callback, segmenter)
    assert entered.wait(2)
    stop(wait_for_stop=False)
    release.set()
    stop()
    assert output == [b"one", b"two"]
    segmenter.flush.assert_called_once()
    assert not errors


def test_energy_buffer_is_bounded_even_without_time_limits(native):
    detector = native.EnergyDetector(16000, 1024, 300, record_timeout=0, wait_timeout=0)
    pcm = chunk(2000) * 512  # 1 MiB per read; no device involved.
    for _ in range(64):
        assert detector.before_read(0.0)[0] == "READ"
        detector.push(pcm, 0.0)
    assert detector.before_read(0.0)[0] == "READ"
    with pytest.raises(ValueError, match="64 MiB"):
        detector.push(pcm, 0.0)
    detector.cancel()
    assert detector.waiting


@pytest.mark.parametrize("settings", [dict(sample_rate=0), dict(chunk=0), dict(energy_threshold=float("nan")),
    dict(pause_threshold=0.1), dict(record_timeout=float("nan")), dict(damping=-1)])
def test_rejects_invalid_detector_configuration(native, settings):
    kwargs = dict(sample_rate=16000, chunk=1024, energy_threshold=300)
    kwargs.update(settings)
    with pytest.raises(ValueError):
        native.EnergyDetector(**kwargs)


def test_calibration_matches_legacy(native):
    listener = NativeAudioListener(native, MagicMock())
    listener.adjust_for_ambient_noise(FakeSource([chunk(100)] * 20))
    assert listener.energy_threshold == pytest.approx(GOLDEN["calibration_threshold"])
