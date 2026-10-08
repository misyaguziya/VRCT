import json

import av
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from models.transcription.google_speech import (
    GoogleRequestError, GoogleSpeechClient, encode_flac, parse_google_response,
)
from models.transcription.pcm_audio import PcmAudio


def test_joins_first_alternative_of_first_result_per_line():
    lines = ["", '{"result":[]}', json.dumps({"result": [
        {"alternative": [{"transcript": "one", "confidence": 0.8},
                         {"transcript": "wrong", "confidence": 1.0}]},
        {"alternative": [{"transcript": "ignored"}]}]}),
        json.dumps({"result": [{"alternative": [{"transcript": "two"}]}]})]
    text, confidence = parse_google_response("\n".join(lines))
    assert text == "one two"
    assert confidence == pytest.approx(0.65)


@pytest.mark.parametrize("response", ["", '{"result":[]}', '{"result":[{"alternative":[]}]}',
                                      '{"result":[{"alternative":[{}]}]}'])
def test_empty_is_no_match(response):
    assert parse_google_response(response) == ("", 0.0)


@pytest.mark.parametrize("response", ["broken", "null", "[]", "{}", '{"result":{}}',
    '{"result":[null]}', '{"result":[{"alternative":{}}]}',
    '{"result":[{"alternative":[{"transcript":2}]}]}',
    '{"result":[{"alternative":[{"transcript":"a","confidence":NaN}]}]}'])
def test_invalid_response_is_error(response):
    with pytest.raises(GoogleRequestError):
        parse_google_response(response)


@pytest.mark.parametrize("rate", [4000, 44100])
def test_request_encodes_actual_rate_and_language(rate):
    pcm = PcmAudio(b"\x01\0" * 10, rate, 2)
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"result":[]}'
    with patch("models.transcription.google_speech.encode_flac", return_value=b"fLaCtest") as encode, \
         patch("models.transcription.google_speech.urlopen", return_value=response) as send:
        assert GoogleSpeechClient(7).recognize(pcm, "ja-JP") == ("", 0.0)
    request = send.call_args.args[0]
    assert send.call_args.kwargs == {"timeout": 7}
    assert request.data == b"fLaCtest"
    assert request.get_header("Content-type") == f"audio/x-flac; rate={max(rate, 8000)}"
    assert parse_qs(urlsplit(request.full_url).query)["lang"] == ["ja-JP"]
    encode.assert_called_once_with(pcm.get_raw_data(max(rate, 8000), 2), max(rate, 8000))


@pytest.mark.parametrize("error", [TimeoutError(), URLError("offline"), HTTPError("redacted", 500, "failed", {}, None)])
def test_transport_errors_are_not_no_match(error):
    with patch("models.transcription.google_speech.encode_flac", return_value=b"fLaC"), \
         patch("models.transcription.google_speech.urlopen", side_effect=error), \
         pytest.raises(GoogleRequestError):
        GoogleSpeechClient().recognize(PcmAudio(b"\0\0", 16000, 2), "ja-JP")


@pytest.mark.parametrize("error", [ValueError("invalid"), OverflowError("large")])
def test_native_encoder_failure(error):
    native = MagicMock()
    native.encode_flac.side_effect = error
    with patch("models.transcription.google_speech.require_native_audio", return_value=native), pytest.raises(GoogleRequestError):
        encode_flac(b"\0\0", 16000)


@pytest.mark.parametrize("rate", [96001, 96009, 96011, 100001, 192001, 655349, 655351, 655360, 0, True])
def test_rejects_unsupported_rate_before_encoding(rate):
    with patch("models.transcription.google_speech.require_native_audio") as native, pytest.raises(GoogleRequestError):
        encode_flac(b"\0\0", rate)
    native.assert_not_called()


@pytest.mark.parametrize("pcm", [b"", b"x", bytearray(b"xx"), b"x" * (64 * 1024 * 1024 + 2)], ids=["empty", "partial", "mutable", "oversize"])
def test_rejects_invalid_pcm_before_encoding(pcm):
    with patch("models.transcription.google_speech.require_native_audio") as native, pytest.raises(GoogleRequestError):
        encode_flac(pcm, 16000)
    native.assert_not_called()


def test_missing_native_has_install_guidance():
    with patch("models.transcription.native_audio.get_native_audio", return_value=None), pytest.raises(ImportError, match="Build/install"):
        encode_flac(b"\0\0", 16000)


@pytest.mark.parametrize("phase", ["frame", "flush", "close"])
@pytest.mark.parametrize("error", [ValueError("encode"), av.error.InvalidDataError(1, "synthetic")])
def test_pyav_failure_closes_container(phase, error):
    container = MagicMock()
    container.__enter__.return_value = container
    stream = container.add_stream.return_value
    if phase == "close":
        container.__exit__.side_effect = error
    else:
        stream.encode.side_effect = lambda frame: (_ for _ in ()).throw(error) if (frame is None) == (phase == "flush") else []
    with patch("av.open", return_value=container), pytest.raises(GoogleRequestError):
        encode_flac(b"\0\0", 192000)
    container.__exit__.assert_called_once()
