"""Legacy Google web recognizer; intentionally distinct from Google Cloud Speech.

Protocol and multi-result behavior derived from custom_speech_recognition
afae7ff78cd5da36e864122f16972d2b0044e03f. See google_speech_LICENSE.txt.
"""

import audioop
from http.client import HTTPException
import json
import math
from io import BytesIO
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .pcm_audio import PcmAudio
from .native_audio import require_native_audio


class GoogleRequestError(Exception):
    """Encoding, transport or malformed-response failure (not a no-match)."""


def encode_flac(pcm16: bytes, sample_rate: int) -> bytes:
    """Encode PCM16 at its actual rate, without a SpeechRecognition subprocess."""
    if (not isinstance(pcm16, bytes) or not pcm16 or len(pcm16) % 2
            or len(pcm16) > 64 * 1024 * 1024):
        raise GoogleRequestError("FLAC requires nonempty complete PCM16 samples up to 64 MiB")
    if type(sample_rate) is not int or sample_rate < 8000:
        raise GoogleRequestError("Invalid FLAC sample rate")
    if sample_rate <= 96000:
        try:
            return require_native_audio().encode_flac(pcm16, sample_rate)
        except (ValueError, OverflowError) as exc:
            raise GoogleRequestError("FLAC encoding failed") from exc
    # Preserve the rates accepted by the previously bundled FLAC executable.
    if sample_rate > 655350 or sample_rate % 10:
        raise GoogleRequestError("Unsupported high FLAC sample rate")
    return _encode_flac_high_rate(pcm16, sample_rate)


def _encode_flac_high_rate(pcm16: bytes, sample_rate: int) -> bytes:
    """High-rate compatibility using the existing PyAV dependency, with no resampling."""
    import av
    import numpy as np

    try:
        output = BytesIO()
        with av.open(output, mode="w", format="flac") as container:
            stream = container.add_stream("flac", rate=sample_rate)
            stream.layout = "mono"
            stream.codec_context.format = "s16"
            for offset in range(0, len(pcm16), 32768):
                samples = np.frombuffer(pcm16, dtype="<i2", count=min(32768, len(pcm16) - offset) // 2,
                                        offset=offset).reshape(1, -1)
                frame = av.AudioFrame.from_ndarray(samples, format="s16", layout="mono")
                frame.sample_rate = sample_rate
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode(None):
                container.mux(packet)
        encoded = output.getvalue()
        if not encoded.startswith(b"fLaC"):
            raise GoogleRequestError("FLAC encoder returned invalid output")
        return encoded
    except (av.FFmpegError, ValueError, OverflowError, OSError) as exc:
        raise GoogleRequestError("FLAC encoding failed") from exc


def parse_google_response(response_text: str) -> tuple[str, float]:
    transcripts, confidences = [], []
    try:
        for line in response_text.splitlines():
            if not line.strip():
                continue
            results = json.loads(line)["result"]
            if not isinstance(results, list):
                raise ValueError("result must be a list")
            if not results:
                continue
            candidate = results[0]
            if not isinstance(candidate, dict):
                raise ValueError("result entry must be an object")
            alternatives = candidate.get("alternative", [])
            if not isinstance(alternatives, list):
                raise ValueError("alternative must be a list")
            if not alternatives:
                continue
            best = alternatives[0]
            if not isinstance(best, dict):
                raise ValueError("alternative entry must be an object")
            if "transcript" not in best:
                continue
            transcript, confidence = best["transcript"], best.get("confidence", 0.5)
            if not isinstance(transcript, str) or type(confidence) not in (int, float):
                raise ValueError("invalid transcript or confidence")
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("invalid confidence")
            transcripts.append(transcript)
            confidences.append(confidence)
    except (ValueError, KeyError, TypeError) as exc:
        raise GoogleRequestError("Malformed Google recognition response") from exc
    if not transcripts:
        return "", 0.0
    return " ".join(transcripts), sum(confidences) / len(confidences)


class GoogleSpeechClient:
    def __init__(self, timeout: float = 10):
        self.timeout = timeout

    def recognize(self, audio: PcmAudio, language: str) -> tuple[str, float]:
        if not audio.frame_data:
            return "", 0.0
        rate = max(8000, audio.sample_rate)
        try:
            flac = encode_flac(audio.get_raw_data(convert_rate=rate, convert_width=2), rate)
            query = urlencode({"client": "chromium", "lang": language,
                               "key": _LEGACY_KEY, "pFilter": 0})
            request = Request(
                "http://www.google.com/speech-api/v2/recognize?" + query,
                data=flac, headers={"Content-Type": f"audio/x-flac; rate={rate}"},
            )
            with urlopen(request, timeout=self.timeout) as response:
                text = response.read().decode("utf-8")
        except (OSError, URLError, HTTPException, ValueError, audioop.error):
            # Do not include the URL (which contains the legacy key) in messages.
            raise GoogleRequestError("Google recognition request failed") from None
        return parse_google_response(text)


# Shared legacy service key inherited from the pinned dependency.
_LEGACY_KEY = 'AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw'
