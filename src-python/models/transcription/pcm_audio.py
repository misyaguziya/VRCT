"""Provider-neutral immutable mono PCM (8-bit unsigned, otherwise signed LE).

Conversion ordering follows SpeechRecognition; see google_speech_LICENSE.txt.
"""

import audioop
from dataclasses import dataclass, field
from io import BytesIO
import wave


@dataclass(frozen=True)
class PcmAudio:
    frame_data: bytes
    sample_rate: int
    sample_width: int
    channels: int = 1
    # Language candidates share one immutable clip. Retain only the common
    # provider format, never an unbounded mapping of requested rates/widths.
    _raw_16k16: bytes | None = field(default=None, init=False, repr=False, compare=False)
    _wav_16k16: bytes | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.frame_data, bytes):
            raise TypeError("PCM data must be immutable bytes")
        if type(self.sample_rate) is not int or self.sample_rate <= 0:
            raise ValueError("sample_rate must be a positive integer")
        if type(self.sample_width) is not int or not 1 <= self.sample_width <= 4:
            raise ValueError("sample_width must be between 1 and 4")
        if type(self.channels) is not int or self.channels != 1:
            raise ValueError("provider PCM must be mono")
        if len(self.frame_data) % self.sample_width:
            raise ValueError("incomplete PCM sample")

    def _conversion_format(self, convert_rate, convert_width):
        rate = self.sample_rate if convert_rate is None else convert_rate
        width = self.sample_width if convert_width is None else convert_width
        if type(rate) is not int or rate <= 0:
            raise ValueError("conversion rate must be a positive integer")
        if type(width) is not int or not 1 <= width <= 4:
            raise ValueError("conversion width must be between 1 and 4")
        return rate, width

    def get_raw_data(self, convert_rate=None, convert_width=None):
        rate, width = self._conversion_format(convert_rate, convert_width)
        canonical = rate == 16000 and width == 2
        if canonical and self._raw_16k16 is not None:
            return self._raw_16k16
        raw = self.frame_data
        if self.sample_width == 1:
            raw = audioop.bias(raw, 1, -128)
        if rate != self.sample_rate:
            raw, _ = audioop.ratecv(raw, self.sample_width, 1, self.sample_rate, rate, None)
        if width != self.sample_width:
            raw = audioop.lin2lin(raw, self.sample_width, width)
        if width == 1:
            raw = audioop.bias(raw, 1, 128)
        if canonical:
            object.__setattr__(self, "_raw_16k16", raw)
        return raw

    def get_wav_data(self, convert_rate=None, convert_width=None):
        rate, width = self._conversion_format(convert_rate, convert_width)
        canonical = rate == 16000 and width == 2
        if canonical and self._wav_16k16 is not None:
            return self._wav_16k16
        raw = self.get_raw_data(rate, width)
        with BytesIO() as output:
            with wave.open(output, "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(width)
                writer.setframerate(rate)
                writer.writeframes(raw)
            wav = output.getvalue()
        if canonical:
            object.__setattr__(self, "_wav_16k16", wav)
        return wav
