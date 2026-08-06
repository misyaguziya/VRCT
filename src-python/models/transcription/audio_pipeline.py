import audioop
import itertools
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Deque, Optional

import numpy as np


TARGET_SAMPLE_RATE = 16000
FRAME_SAMPLES = 512

# Shared across StreamingVadSegmenter instances so segment ids stay unique even
# after a mic/speaker session is stopped and a new segmenter instance is created
# on restart (a fresh instance-local counter would collide with ids already
# shown in the UI and get treated as an update to the old row instead of a new one).
_segment_id_counter = itertools.count()


@dataclass(frozen=True)
class AudioQueueItem:
    audio: bytes
    recorded_at: datetime
    is_final: bool = True
    segment_id: int = 0
    speech_ended_at: Optional[datetime] = None


@dataclass(frozen=True)
class SpeechSegment:
    audio: bytes
    segment_id: int
    is_final: bool

    @property
    def duration_ms(self) -> float:
        return len(self.audio) / 2 / TARGET_SAMPLE_RATE * 1000


class Pcm16MonoNormalizer:
    def __init__(self, sample_rate: int, sample_width: int, channels: int) -> None:
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = max(1, channels)
        self._rate_state = None

    def reset(self) -> None:
        self._rate_state = None

    def process(self, data: bytes) -> bytes:
        if not data:
            return b""

        if self.sample_width != 2:
            data = audioop.lin2lin(data, self.sample_width, 2)

        samples = np.frombuffer(data, dtype=np.int16)
        complete_samples = samples.size - samples.size % self.channels
        samples = samples[:complete_samples]
        if self.channels > 1 and samples.size:
            frames = samples.reshape(-1, self.channels).astype(np.int32)
            samples = np.rint(frames.mean(axis=1)).clip(-32768, 32767).astype(np.int16)
        data = samples.astype("<i2", copy=False).tobytes()

        if self.sample_rate != TARGET_SAMPLE_RATE:
            data, self._rate_state = audioop.ratecv(
                data,
                2,
                1,
                self.sample_rate,
                TARGET_SAMPLE_RATE,
                self._rate_state,
            )
        return data


class SileroFrameProbability:
    def __init__(self) -> None:
        self._model = None
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, 64), dtype=np.float32)

    def reset(self) -> None:
        self._state.fill(0)
        self._context.fill(0)

    def __call__(self, frame: np.ndarray) -> float:
        if frame.shape != (FRAME_SAMPLES,):
            raise ValueError(f"Expected {(FRAME_SAMPLES,)} audio frame, got {frame.shape}")
        if self._model is None:
            from faster_whisper.vad import get_vad_model

            self._model = get_vad_model()

        model_input = np.concatenate((self._context, frame.reshape(1, -1)), axis=1)
        encoder_output = self._model.encoder_session.run(None, {"input": model_input})[0]
        decoder_input = encoder_output.reshape(1, 128)
        output, self._state = self._model.decoder_session.run(
            None,
            {"input": decoder_input, "state": self._state},
        )
        self._context = frame[-64:].reshape(1, -1)
        return float(np.asarray(output).reshape(-1)[0])


class StreamingVadSegmenter:
    def __init__(
        self,
        probability: Optional[Callable[[np.ndarray], float]] = None,
        positive_threshold: float = 0.25,
        negative_threshold: float = 0.10,
        redemption_frames: int = 24,
        min_speech_frames: int = 2,
        pre_speech_pad_frames: int = 5,
    ) -> None:
        self.probability = probability or SileroFrameProbability()
        self.positive_threshold = positive_threshold
        self.negative_threshold = negative_threshold
        self.redemption_frames = redemption_frames
        self.min_speech_frames = min_speech_frames
        self.pre_speech_frames: Deque[bytes] = deque(maxlen=pre_speech_pad_frames)
        self._remainder = b""
        self._speech_frames: list[bytes] = []
        self._positive_frames = 0
        self._negative_frames = 0
        self._speech_frame_count = 0
        self._speaking = False
        self._segment_id = next(_segment_id_counter)

    @property
    def speaking(self) -> bool:
        return self._speaking

    def process(self, pcm: bytes, final_input: bool = False) -> list[SpeechSegment]:
        self._remainder += pcm
        frame_bytes = FRAME_SAMPLES * 2
        segments: list[SpeechSegment] = []

        while len(self._remainder) >= frame_bytes:
            frame = self._remainder[:frame_bytes]
            self._remainder = self._remainder[frame_bytes:]
            samples = np.frombuffer(frame, dtype="<i2").astype(np.float32) / 32768.0
            segment = self._process_frame(frame, self.probability(samples))
            if segment is not None:
                segments.append(segment)

        if final_input:
            segment = self.flush()
            if segment is not None:
                segments.append(segment)
        return segments

    def snapshot(self) -> Optional[SpeechSegment]:
        if not self._speaking or self._speech_frame_count < self.min_speech_frames:
            return None
        return SpeechSegment(b"".join(self._speech_frames), self._segment_id, False)

    def flush(self) -> Optional[SpeechSegment]:
        if self._remainder:
            padded = self._remainder.ljust(FRAME_SAMPLES * 2, b"\0")
            self._remainder = b""
            samples = np.frombuffer(padded, dtype="<i2").astype(np.float32) / 32768.0
            result = self._process_frame(padded, self.probability(samples))
            if result is not None:
                return result
        return self._finish_segment()

    def reset(self, advance_segment: bool = False) -> None:
        if advance_segment and (self._speaking or self._positive_frames):
            self._segment_id = next(_segment_id_counter)
        self._remainder = b""
        self._speech_frames = []
        self._positive_frames = 0
        self._negative_frames = 0
        self._speech_frame_count = 0
        self._speaking = False
        self.pre_speech_frames.clear()
        reset = getattr(self.probability, "reset", None)
        if callable(reset):
            reset()

    def _process_frame(self, frame: bytes, speech_probability: float) -> Optional[SpeechSegment]:
        if not self._speaking:
            self.pre_speech_frames.append(frame)
            if speech_probability >= self.positive_threshold:
                self._positive_frames += 1
            else:
                self._positive_frames = 0
            if self._positive_frames >= self.min_speech_frames:
                self._speaking = True
                self._speech_frames = list(self.pre_speech_frames)
                self._speech_frame_count = self._positive_frames
                self.pre_speech_frames.clear()
            return None

        self._speech_frames.append(frame)
        if speech_probability >= self.positive_threshold:
            self._negative_frames = 0
            self._speech_frame_count += 1
        elif speech_probability < self.negative_threshold:
            self._negative_frames += 1
            if self._negative_frames >= self.redemption_frames:
                return self._finish_segment()
        return None

    def _finish_segment(self) -> Optional[SpeechSegment]:
        result = None
        if self._speaking and self._speech_frame_count >= self.min_speech_frames:
            result = SpeechSegment(b"".join(self._speech_frames), self._segment_id, True)
        if self._speaking or self._positive_frames:
            self._segment_id = next(_segment_id_counter)
        self.reset()
        return result