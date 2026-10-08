"""Native audio contracts; decode FLAC with PyAV, independently of flacenc."""

import audioop
from io import BytesIO
from unittest.mock import MagicMock, patch

import av
import numpy as np
import pytest
from pydub import AudioSegment

from models.transcription import native_audio
from models.transcription.audio_vad import Pcm16MonoNormalizer
from models.transcription.google_speech import GoogleRequestError, GoogleSpeechClient, encode_flac
from models.transcription.pcm_audio import PcmAudio


@pytest.fixture
def native():
    return pytest.importorskip("vrct_audio", reason="Build native/vrct-audio to run native contracts")


@pytest.mark.parametrize("channels", [3, 6, 8, 31, 127, 254, 256])
@pytest.mark.parametrize("kind", ["random", "zero", "negative", "minimum", "maximum"])
def test_speaker_downmix_matches_pydub_including_overflow(native, channels, kind):
    frames = np.random.default_rng(841).integers(-32768, 32768, (97, channels), dtype=np.int16)
    if kind != "random":
        frames.fill({"zero": 0, "negative": -1, "minimum": -32768, "maximum": 32767}[kind])
    pcm = frames.astype("<i2").tobytes()
    try:
        expected = AudioSegment(data=pcm, sample_width=2, frame_rate=48000, channels=channels).set_channels(1).raw_data
    except OverflowError:
        with pytest.raises(OverflowError):
            native.speaker_downmix_pcm16(pcm, channels)
    else:
        assert native.speaker_downmix_pcm16(pcm, channels) == expected


def test_speaker_intermediate_overflow_even_when_final_sum_fits(native):
    frames = np.array([-32768] * 253 + [32767], dtype="<i2")
    assert (frames.astype(np.int32) // 254).sum() == -32761
    pcm = frames.tobytes()
    with pytest.raises(OverflowError):
        AudioSegment(data=pcm, sample_width=2, frame_rate=48000, channels=254).set_channels(1)
    with pytest.raises(OverflowError):
        native.speaker_downmix_pcm16(pcm, 254)


@pytest.mark.parametrize("channels", [0, 1, 2, 257])
def test_speaker_invalid_channels(native, channels):
    with pytest.raises(ValueError):
        native.speaker_downmix_pcm16(b"", channels)


def test_speaker_empty_partial_and_oversize(native):
    assert native.speaker_downmix_pcm16(b"", 3) == b""
    for pcm in [b"\0", b"\0\0", b"\0" * (64 * 1024 * 1024 + 2)]:
        with pytest.raises(ValueError):
            native.speaker_downmix_pcm16(pcm, 3)


@pytest.mark.parametrize("rate", [8000, 16000, 44100, 48000, 96000])
@pytest.mark.parametrize("count", [1, 4095, 4096, 4097, 16000])
def test_flac_decodes_to_identical_pcm(native, rate, count):
    samples = np.random.default_rng(731).integers(-32768, 32768, count, dtype=np.int16)
    pcm = samples.astype("<i2").tobytes()
    flac = native.encode_flac(pcm, rate)
    with av.open(BytesIO(flac)) as container:
        assert container.streams.audio[0].sample_rate == rate
        decoded = []
        for frame in container.decode(audio=0):
            assert frame.format.name == "s16"
            assert len(frame.layout.channels) == 1
            decoded.append(frame.to_ndarray().astype("<i2").tobytes())
    assert b"".join(decoded) == pcm


@pytest.mark.parametrize("sample", [0, -32768, 32767])
def test_flac_silence_and_extremes(native, sample):
    pcm = np.full(8193, sample, dtype="<i2").tobytes()
    with av.open(BytesIO(native.encode_flac(pcm, 16000))) as container:
        assert b"".join(f.to_ndarray().astype("<i2").tobytes() for f in container.decode(audio=0)) == pcm


@pytest.mark.parametrize("rate", [0, 7999, 96001, 192000])
def test_flac_rejects_unsupported_rate(native, rate):
    with pytest.raises(ValueError):
        native.encode_flac(b"\0\0", rate)


@pytest.mark.parametrize("pcm", [b"", b"\0", b"\0\0\0"])
def test_flac_rejects_empty_and_partial_samples(native, pcm):
    with pytest.raises(ValueError):
        native.encode_flac(pcm, 16000)


def test_downmix_ties_and_extremes(native):
    frames = np.array([[0, 1], [1, 2], [0, -1], [-1, -2], [32767, -32768], [-32768, -32768]], dtype="<i2")
    expected = np.array([0, 2, 0, -2, 0, -32768], dtype="<i2").tobytes()
    assert native.downmix_pcm16(frames.tobytes(), 2) == expected
    assert native.downmix_pcm16(b"", 2) == b""


@pytest.mark.parametrize("pcm,channels", [(b"\0", 1), (b"\0\0", 2), (b"", 0), (b"", 257)])
def test_downmix_rejects_invalid_frames(native, pcm, channels):
    with pytest.raises(ValueError):
        native.downmix_pcm16(pcm, channels)


@pytest.mark.parametrize("rate", [8000, 16000, 44100, 48000, 96000])
@pytest.mark.parametrize("channels", [1, 2, 6])
@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_streaming_normalizer_matches_python_across_chunks(native, rate, channels, width):
    with patch("models.transcription.audio_vad.get_native_audio", return_value=None):
        old = Pcm16MonoNormalizer(rate, width, channels)
    with patch("models.transcription.audio_vad.get_native_audio", return_value=native):
        new = Pcm16MonoNormalizer(rate, width, channels)
    assert new._native_audio is native
    rng = np.random.default_rng(237)
    for frames in [1024, 1536, 512, 17, 2048]:
        pcm16 = rng.integers(-32768, 32768, frames * channels, dtype=np.int16).astype("<i2").tobytes()
        pcm = audioop.lin2lin(pcm16, 2, width)
        assert new.process(pcm) == old.process(pcm)
    old.reset()
    new.reset()
    assert new.process(pcm) == old.process(pcm)


def test_incomplete_multichannel_tail_keeps_existing_behavior(native):
    with patch("models.transcription.audio_vad.get_native_audio", return_value=native):
        normalizer = Pcm16MonoNormalizer(16000, 2, 3)
    assert normalizer.process(b"\0\0") == b""
    assert normalizer.process(b"\0\0" * 4) == b"\0\0"


def test_loader_only_falls_back_for_missing_extension():
    native_audio.get_native_audio.cache_clear()
    try:
        with patch.object(native_audio, "import_module", side_effect=ModuleNotFoundError(name="vrct_audio")) as load:
            assert native_audio.get_native_audio() is None
            assert native_audio.get_native_audio() is None
            assert load.call_count == 1
        for error in [ImportError("DLL load failed"), ModuleNotFoundError(name="dependency")]:
            native_audio.get_native_audio.cache_clear()
            with patch.object(native_audio, "import_module", side_effect=error), pytest.raises(ImportError):
                native_audio.get_native_audio()
    finally:
        native_audio.get_native_audio.cache_clear()


def test_encoder_selects_native_and_does_not_hide_failure():
    native = MagicMock()
    native.encode_flac.return_value = b"fLaCnative"
    with patch("models.transcription.google_speech.require_native_audio", return_value=native), \
         patch("models.transcription.google_speech._encode_flac_high_rate") as legacy:
        assert encode_flac(b"\0\0", 48000) == b"fLaCnative"
        native.encode_flac.assert_called_once_with(b"\0\0", 48000)
        native.encode_flac.side_effect = ValueError("invalid")
        with pytest.raises(GoogleRequestError):
            encode_flac(b"\0\0", 48000)
        legacy.assert_not_called()


def test_high_rate_uses_pyav_without_resampling():
    native = MagicMock()
    with patch("models.transcription.google_speech.require_native_audio", return_value=native), \
         patch("models.transcription.google_speech._encode_flac_high_rate", return_value=b"fLaClegacy") as legacy:
        assert encode_flac(b"\0\0", 192000) == b"fLaClegacy"
        legacy.assert_called_once_with(b"\0\0", 192000)
        native.encode_flac.assert_not_called()


def test_empty_audio_is_not_encoded_or_sent():
    with patch("models.transcription.google_speech.encode_flac") as encode, \
         patch("models.transcription.google_speech.urlopen") as send:
        assert GoogleSpeechClient().recognize(PcmAudio(b"", 16000, 2), "ja-JP") == ("", 0.0)
        encode.assert_not_called()
        send.assert_not_called()


@pytest.mark.parametrize("rate", [96010, 100000, 176400, 192000, 384000, 655350])
@pytest.mark.parametrize("count", [1, 16383, 16384, 16385, 33001])
def test_high_rate_flac_decodes_exact_pcm_and_rate(rate, count):
    pcm = np.random.default_rng(618).integers(-32768, 32768, count, dtype=np.int16).astype("<i2").tobytes()
    with av.open(BytesIO(encode_flac(pcm, rate))) as container:
        assert container.streams.audio[0].sample_rate == rate
        frames = list(container.decode(audio=0))
        assert all(len(frame.layout.channels) == 1 and frame.format.name == "s16" for frame in frames)
        assert b"".join(frame.to_ndarray().astype("<i2").tobytes() for frame in frames) == pcm
