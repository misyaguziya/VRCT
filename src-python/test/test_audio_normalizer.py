"""PCM width/downmix equivalence against audioop and NumPy, including dispatch."""

import audioop
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from models.transcription.audio_vad import Pcm16MonoNormalizer


@pytest.fixture
def native():
    return pytest.importorskip("vrct_audio", reason="Build native/vrct-audio to run native contracts")


def reference(pcm, width, channels):
    pcm16 = audioop.lin2lin(pcm, width, 2) if width != 2 else pcm
    samples = np.frombuffer(pcm16, dtype="<i2")
    samples = samples[:len(samples) // channels * channels]
    if channels > 1 and len(samples):
        samples = np.rint(samples.reshape(-1, channels).astype(np.int32).mean(axis=1)).astype("<i2")
    return samples.tobytes()


@pytest.mark.parametrize("width", [1, 2, 3, 4])
@pytest.mark.parametrize("channels", [1, 2, 6, 256])
def test_integer_width_boundaries_random_and_partial_channels(native, width, channels):
    bits = width * 8
    minimum = -(1 << (bits - 1))
    maximum = (1 << (bits - 1)) - 1
    values = [minimum, minimum + 1, -1, 0, 1, maximum - 1, maximum]
    if width <= 2:
        # Exhaustive signed i8/i16 conversions, including both stereo tie signs.
        values += list(range(minimum, maximum + 1))
    else:
        shift = 1 << (bits - 16)
        values += [-shift - 1, -shift, -shift + 1, shift - 1, shift, shift + 1]
        values += np.random.default_rng(619).integers(minimum, maximum + 1, 8193).tolist()
    pcm = b"".join(value.to_bytes(width, "little", signed=True) for value in values)
    assert native.normalize_pcm16(pcm, width, channels) == reference(pcm, width, channels)
    assert native.normalize_pcm16(b"", width, channels) == b""
    assert native.normalize_pcm16(pcm[:width], width, channels) == reference(pcm[:width], width, channels)


def test_conversion_precedes_ties_even_mean(native):
    # Averaging 24-bit samples before truncation gives a different answer.
    pcm = b"".join(value.to_bytes(3, "little", signed=True) for value in [255, 511, -1, 255])
    assert native.normalize_pcm16(pcm, 3, 2) == b"\0\0\0\0"
    for channels in (2, 6, 256):
        pcm = b"".join(value.to_bytes(2, "little", signed=True) for value in [0, 1] * (channels // 2))
        assert native.normalize_pcm16(pcm, 2, channels) == b"\0\0"


def test_mono16_returns_same_immutable_bytes(native):
    pcm = bytes(range(256)) * 16
    assert native.normalize_pcm16(pcm, 2, 1) is pcm
    for unsupported in (bytearray(pcm), memoryview(pcm), [0, 0]):
        with pytest.raises(TypeError):
            native.normalize_pcm16(unsupported, 2, 1)


def test_conversion_releases_gil_and_returns_owned_bytes(native):
    ready = threading.Event()
    run = threading.Event()
    progressed = threading.Event()

    def observer():
        ready.set()
        run.wait()
        progressed.set()

    thread = threading.Thread(target=observer)
    thread.start()
    assert ready.wait(5)
    pcm = b"\x01\0\x03\0" * (1024 * 1024)
    interval = sys.getswitchinterval()
    try:
        # Prevent the interpreter from scheduling observer between run.set() and
        # entering native code. Its progress then requires allow_threads().
        sys.setswitchinterval(10)
        run.set()
        output = native.normalize_pcm16(pcm, 2, 2)
        released = progressed.is_set()
    finally:
        sys.setswitchinterval(interval)
        thread.join(5)
    assert released
    assert output == b"\x02\0" * (1024 * 1024)
    assert pcm[:4] == b"\x01\0\x03\0"


@pytest.mark.parametrize("width,channels", [(0, 1), (5, 1), (2, 0), (2, 257)])
def test_invalid_native_formats(native, width, channels):
    with pytest.raises(ValueError):
        native.normalize_pcm16(b"", width, channels)


@pytest.mark.parametrize("width", [2, 3, 4])
def test_partial_sample_rejected_but_channel_tail_discarded(native, width):
    with pytest.raises(ValueError):
        native.normalize_pcm16(b"\0" * (width + 1), width, 2)
    assert native.normalize_pcm16(b"\0" * width, width, 2) == b""


def test_native_input_and_expanded_output_size_limits(native):
    with pytest.raises(ValueError, match="input exceeds"):
        native.normalize_pcm16(b"\0" * (64 * 1024 * 1024 + 1), 1, 256)
    with pytest.raises(ValueError, match="output exceeds"):
        native.normalize_pcm16(b"\0" * (32 * 1024 * 1024 + 1), 1, 1)
    pcm = b"\0" * (64 * 1024 * 1024)
    assert native.normalize_pcm16(pcm, 2, 1) is pcm


@pytest.mark.parametrize("rate", [16000, 44100, 48000])
@pytest.mark.parametrize("width", [1, 2, 3, 4])
@pytest.mark.parametrize("channels", [1, 2, 6, 256])
def test_streaming_output_state_and_reset_match_fallback(native, rate, width, channels):
    with patch("models.transcription.audio_vad.get_native_audio", return_value=None):
        old = Pcm16MonoNormalizer(rate, width, channels)
    with patch("models.transcription.audio_vad.get_native_audio", return_value=native):
        new = Pcm16MonoNormalizer(rate, width, channels)
    rng = np.random.default_rng(671)
    for frames in (1, 1024, 17, 512, 3):
        # Complete samples with an incomplete channel tail in every chunk.
        pcm = rng.bytes((frames * channels + channels - 1) * width)
        assert new.process(pcm) == old.process(pcm)
        assert new._rate_state == old._rate_state
    assert new.process(b"") == old.process(b"") == b""
    new.reset()
    old.reset()
    assert new._rate_state is old._rate_state is None
    assert new.process(pcm) == old.process(pcm)
    assert new._rate_state == old._rate_state


@pytest.mark.parametrize("pcm,width,channels", [
    (bytearray(b"\x01\0\x03\0"), 2, 2),
    (memoryview(b"\x01\0\x03\0"), 2, 2),
    (b"\x01\0" * 257, 2, 257),
    (b"\x01\x02", True, 1),
])
def test_nonstandard_inputs_keep_previous_path(native, pcm, width, channels):
    def forbidden(*args):
        pytest.fail("unsupported format must not enter the new native API")
    adapter = SimpleNamespace(normalize_pcm16=forbidden, downmix_pcm16=native.downmix_pcm16)
    with patch("models.transcription.audio_vad.get_native_audio", return_value=adapter):
        normalizer = Pcm16MonoNormalizer(16000, width, channels)
    assert normalizer.process(pcm) == reference(pcm, width, channels)


@pytest.mark.parametrize("pcm,width,error", [(b"\0", 2, ValueError), (b"\0", 3, audioop.error), (b"\0", 5, audioop.error)])
def test_previous_partial_sample_and_width_errors_preserved(native, pcm, width, error):
    with patch("models.transcription.audio_vad.get_native_audio", return_value=native):
        normalizer = Pcm16MonoNormalizer(16000, width, 2)
    with pytest.raises(error):
        normalizer.process(pcm)


def test_legacy_limit_applies_to_expanded_interleaved_not_mono_size(native):
    with patch("models.transcription.audio_vad.get_native_audio", return_value=native):
        normalizer = Pcm16MonoNormalizer(16000, 1, 2)
    pcm = b"\0" * (32 * 1024 * 1024 + 2)
    # New API alone accepts the smaller mono output; the public normalizer must
    # retain the old downmix error for >64 MiB converted interleaved PCM16.
    assert len(native.normalize_pcm16(pcm, 1, 2)) == len(pcm)
    with pytest.raises(ValueError, match="input exceeds"):
        normalizer.process(pcm)


def test_old_wheel_or_native_error_is_not_hidden():
    with patch("models.transcription.audio_vad.get_native_audio", return_value=SimpleNamespace()):
        normalizer = Pcm16MonoNormalizer(16000, 2, 1)
    with pytest.raises(AttributeError, match="normalize_pcm16"):
        normalizer.process(b"\0\0")

    def fail(*args):
        raise ValueError("native failure")
    normalizer._native_audio = SimpleNamespace(normalize_pcm16=fail)
    with pytest.raises(ValueError, match="native failure"):
        normalizer.process(b"\0\0")
