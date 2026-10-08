import audioop
import json
from pathlib import Path
from dataclasses import FrozenInstanceError, replace
from io import BytesIO
import struct
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import wave

import pytest

from models.transcription.pcm_audio import PcmAudio
from models.transcription.transcription_transcriber import AudioTranscriber

GOLDEN = json.loads((Path(__file__).parent / "fixtures/legacy_audio_contracts.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("rate", [8000, 16000, 44100, 48000])
@pytest.mark.parametrize("width", [1, 2, 4])
def test_conversion_matches_legacy_and_wav_decodes(rate, width):
    raw = struct.pack("<8h", -32768, -12000, -1, 0, 1, 12000, 30000, 32767)
    pcm = PcmAudio(raw, rate, 2)
    converted = pcm.get_raw_data(16000, width)
    assert converted == bytes.fromhex(GOLDEN["pcm"][f"{rate}/{width}"])
    with wave.open(BytesIO(pcm.get_wav_data(16000, width))) as wav:
        assert (wav.getframerate(), wav.getsampwidth(), wav.getnchannels()) == (16000, width, 1)
        assert wav.readframes(wav.getnframes()) == converted


def test_unsigned_8bit_roundtrip_and_24bit_conversion():
    pcm = PcmAudio(bytes([0, 128, 255]), 16000, 1)
    assert pcm.get_raw_data() == bytes([0, 128, 255])
    assert pcm.get_raw_data(convert_width=2) == struct.pack("<3h", -32768, 0, 32512)
    raw = struct.pack("<3h", -32768, 0, 32767)
    assert PcmAudio(raw, 16000, 2).get_raw_data(convert_width=3) == audioop.lin2lin(raw, 2, 3)


@pytest.mark.parametrize("args", [(b"a", 16000, 2), (b"", 0, 2), (b"", 16000, 5), (b"", 16000, 2, 2)])
def test_rejects_invalid_pcm(args):
    with pytest.raises(ValueError):
        PcmAudio(*args)


def test_immutable_and_conversion_validation():
    pcm = PcmAudio(b"\0\0", 16000, 2)
    with pytest.raises(FrozenInstanceError):
        pcm.sample_rate = 8000
    with pytest.raises(TypeError):
        PcmAudio(bytearray(2), 16000, 2)
    with pytest.raises(ValueError):
        pcm.get_raw_data(convert_rate=0)
    with pytest.raises(ValueError):
        pcm.get_raw_data(convert_width=0)


@pytest.mark.parametrize("first", ["raw", "wav"])
@pytest.mark.parametrize("empty", [False, True])
def test_canonical_conversion_and_wav_reused_per_clip(first, empty):
    pcm = PcmAudio(b"" if empty else struct.pack("<4h", -32768, -1, 0, 32767), 48000, 2)
    original_repr, original_hash = repr(pcm), hash(pcm)
    equal_clip = PcmAudio(pcm.frame_data, pcm.sample_rate, pcm.sample_width)
    with patch("models.transcription.pcm_audio.audioop.ratecv", wraps=audioop.ratecv) as resample, \
         patch("models.transcription.pcm_audio.wave.open", wraps=wave.open) as open_wav:
        if first == "raw":
            raw = pcm.get_raw_data(16000, 2)
            wav = pcm.get_wav_data(16000, 2)
        else:
            wav = pcm.get_wav_data(16000, 2)
            raw = pcm.get_raw_data(16000, 2)
        for _ in range(3):
            assert pcm.get_raw_data(16000, 2) is raw
            assert pcm.get_wav_data(16000, 2) is wav
        assert resample.call_count == open_wav.call_count == 1
    assert pcm.frame_data == equal_clip.frame_data
    assert pcm == equal_clip
    assert hash(pcm) == original_hash == hash(equal_clip)
    assert repr(pcm) == original_repr
    assert equal_clip._raw_16k16 is equal_clip._wav_16k16 is None
    assert replace(pcm)._raw_16k16 is replace(pcm)._wav_16k16 is None
    with wave.open(BytesIO(wav)) as reader:
        assert reader.readframes(reader.getnframes()) == raw


def test_default_conversion_arguments_resolve_to_canonical_format():
    pcm = PcmAudio(b"\0\0\1\0", 16000, 2)
    raw = pcm.get_raw_data()
    assert raw is pcm.frame_data
    assert pcm.get_raw_data(16000, None) is pcm.get_raw_data(None, 2) is raw
    wav = pcm.get_wav_data()
    assert pcm.get_wav_data(16000, None) is pcm.get_wav_data(None, 2) is wav
    with pytest.raises(TypeError):
        PcmAudio(b"", 16000, 2, _raw_16k16=b"stale")
    with pytest.raises(FrozenInstanceError):
        pcm._raw_16k16 = b"changed"


@pytest.mark.parametrize("width", [1, 2, 3, 4])
@pytest.mark.parametrize("rate", [16000, 44100, 48000])
def test_cached_canonical_bytes_match_conversion_order_for_all_source_widths(width, rate):
    pcm16 = struct.pack("<8h", -32768, -12000, -1, 0, 1, 12000, 30000, 32767)
    original = audioop.lin2lin(pcm16, 2, width)
    if width == 1:
        original = audioop.bias(original, 1, 128)
    expected = audioop.bias(original, 1, -128) if width == 1 else original
    if rate != 16000:
        expected, _ = audioop.ratecv(expected, width, 1, rate, 16000, None)
    expected = audioop.lin2lin(expected, width, 2)
    pcm = PcmAudio(original, rate, width)
    assert pcm.get_raw_data(16000, 2) == pcm.get_raw_data(16000, 2) == expected
    for _ in range(2):
        with wave.open(BytesIO(pcm.get_wav_data(16000, 2))) as reader:
            assert (reader.getframerate(), reader.getsampwidth(), reader.getnchannels()) == (16000, 2, 1)
            assert reader.readframes(reader.getnframes()) == expected


@pytest.mark.parametrize("rate,width", [(16000.0, 2), (16000, 2.0), (True, 2), (16000, True), (0, 2), (16000, 5)])
@pytest.mark.parametrize("method", ["get_raw_data", "get_wav_data"])
def test_argument_validation_still_runs_after_cache_hit(rate, width, method):
    pcm = PcmAudio(b"\0\0", 16000, 2)
    pcm.get_raw_data()
    pcm.get_wav_data()
    with pytest.raises(ValueError):
        getattr(pcm, method)(rate, width)


def test_noncanonical_requests_do_not_populate_or_evict_canonical_cache():
    pcm = PcmAudio(struct.pack("<4h", -32768, -1, 0, 32767), 48000, 2)
    with patch("models.transcription.pcm_audio.audioop.ratecv", wraps=audioop.ratecv) as resample:
        expected = pcm.get_raw_data(8000, 1)
        assert pcm.get_raw_data(8000, 1) == expected
        assert pcm._raw_16k16 is pcm._wav_16k16 is None
        assert resample.call_count == 2
        cached = pcm.get_wav_data(16000, 2)
        pcm.get_wav_data(22050, 4)
        pcm.get_wav_data(22050, 4)
        assert resample.call_count == 5
        assert pcm.get_wav_data(16000, 2) is cached
        assert resample.call_count == 5


def test_failed_raw_conversion_is_retried():
    pcm = PcmAudio(b"\0\0" * 8, 48000, 2)
    with patch("models.transcription.pcm_audio.audioop.ratecv", side_effect=ValueError("conversion failure")):
        with pytest.raises(ValueError, match="conversion failure"):
            pcm.get_raw_data(16000, 2)
    assert pcm._raw_16k16 is None
    assert pcm.get_raw_data(16000, 2) == b"\0\0" * 3


def test_failed_wav_write_reuses_successful_raw_but_retries_wav():
    pcm = PcmAudio(b"\0\0" * 8, 48000, 2)
    with patch("models.transcription.pcm_audio.wave.open", side_effect=OSError("writer failure")):
        with pytest.raises(OSError, match="writer failure"):
            pcm.get_wav_data(16000, 2)
    assert pcm._raw_16k16 == b"\0\0" * 3
    assert pcm._wav_16k16 is None
    with patch("models.transcription.pcm_audio.audioop.ratecv", side_effect=AssertionError("must reuse PCM")):
        wav = pcm.get_wav_data(16000, 2)
    with wave.open(BytesIO(wav)) as reader:
        assert reader.readframes(reader.getnframes()) == pcm._raw_16k16


@pytest.mark.parametrize("channels", [1, 2, 3, 6, 8])
def test_speaker_matches_legacy_wave_roundtrip(channels):
    values = [-32768, 32000, 15000, -1000, 0, 32767, -25000, 42]
    raw = b"".join(struct.pack("<h", values[i % len(values)]) for i in range(channels * 32))
    source = SimpleNamespace(SAMPLE_RATE=48000, SAMPLE_WIDTH=2, channels=channels)
    transcriber = AudioTranscriber(True, source, 3, 10, "Google")
    transcriber.audio_sources["last_sample"] = raw
    expected = GOLDEN["speaker"][str(channels)]
    actual = transcriber.processSpeakerData()
    assert actual.frame_data == bytes.fromhex(expected["pcm_hex"])
    assert actual.sample_rate == expected["rate"]
    assert actual.sample_width == expected["width"]


def test_mic_ignores_device_channel_metadata():
    source = SimpleNamespace(SAMPLE_RATE=16000, SAMPLE_WIDTH=2, channels=2)
    transcriber = AudioTranscriber(False, source, 3, 10, "Google")
    transcriber.audio_sources["last_sample"] = b"\x01\0"
    assert transcriber.processMicData() == PcmAudio(b"\x01\0", 16000, 2)


def speaker_transcriber(raw, width=2, channels=3):
    source = SimpleNamespace(SAMPLE_RATE=48000, SAMPLE_WIDTH=width, channels=channels)
    transcriber = AudioTranscriber(True, source, 3, 10, "Google")
    transcriber.audio_sources["last_sample"] = raw
    return transcriber


def test_speaker_dispatches_supported_pcm_to_native():
    raw = b"\1\0" * 3
    native = SimpleNamespace(speaker_downmix_pcm16=MagicMock(return_value=b"\0\0"))
    with patch("models.transcription.transcription_transcriber.get_native_audio", return_value=native), \
         patch("models.transcription.transcription_transcriber.AudioSegment") as legacy:
        assert speaker_transcriber(raw).processSpeakerData().frame_data == b"\0\0"
    native.speaker_downmix_pcm16.assert_called_once_with(raw, 3)
    legacy.assert_not_called()


@pytest.mark.parametrize("width,channels", [(1, 3), (4, 3), (2, 257)])
def test_speaker_unsupported_format_keeps_legacy_without_loading_native(width, channels):
    raw = b"\0" * (width * channels)
    with patch("models.transcription.transcription_transcriber.get_native_audio") as load:
        assert speaker_transcriber(raw, width, channels).processSpeakerData().frame_data == b"\0" * width
    load.assert_not_called()


def test_speaker_oversized_dispatch_keeps_legacy_without_allocating_large_fixture():
    class SizedBytes(bytes):
        def __len__(self):
            return (64 * 1024 * 1024 // 6 + 1) * 6

    with patch("models.transcription.transcription_transcriber.get_native_audio") as load, \
         patch("models.transcription.transcription_transcriber.AudioSegment") as legacy:
        legacy.return_value.set_channels.return_value.raw_data = b"\0\0"
        assert speaker_transcriber(SizedBytes(b"\0" * 6)).processSpeakerData().frame_data == b"\0\0"
    load.assert_not_called()
    legacy.assert_called_once()


def test_speaker_missing_native_uses_pydub():
    with patch("models.transcription.transcription_transcriber.get_native_audio", return_value=None):
        assert speaker_transcriber(struct.pack("<3h", -1, -1, 2)).processSpeakerData().frame_data == struct.pack("<h", -2)


@pytest.mark.parametrize("error", [OverflowError("overflow"), RuntimeError("broken")])
def test_speaker_native_failure_does_not_fallback(error):
    native = SimpleNamespace(speaker_downmix_pcm16=MagicMock(side_effect=error))
    with patch("models.transcription.transcription_transcriber.get_native_audio", return_value=native), \
         patch("models.transcription.transcription_transcriber.AudioSegment") as legacy:
        with pytest.raises(type(error)):
            speaker_transcriber(b"\0" * 6).processSpeakerData()
    legacy.assert_not_called()


def test_speaker_old_native_wheel_reports_missing_symbol():
    with patch("models.transcription.transcription_transcriber.get_native_audio", return_value=SimpleNamespace()):
        with pytest.raises(AttributeError):
            speaker_transcriber(b"\0" * 6).processSpeakerData()


def test_stereo_sum_saturates_without_loading_native():
    with patch("models.transcription.transcription_transcriber.get_native_audio") as load:
        assert speaker_transcriber(struct.pack("<2h", 30000, 30000), channels=2).processSpeakerData().frame_data == struct.pack("<h", 32767)
    load.assert_not_called()
