"""VAD-driven speech boundary detection.

このモジュールは「VAD の発話確率計算」(`SileroFrameProbability`) と
「発話区間 (speech boundary) の状態機械」(`VadSegmenter`) を分離する。
設計は主に2つの実績ある参照実装に忠実に倣っている:

- `docs/ref/PuriPuly-heart/src/puripuly_heart/core/vad/gating.py` の
  `VadGating` — 状態機械の構造 (pre-roll、start commit、hangover、
  max_segment による強制分割とその際に VAD state をリセットしない設計)。
- `docs/ref/silero-vad/src/silero_vad/utils_vad.py` の `VADIterator` —
  ヒステリシス (`negative_threshold = threshold - 0.15`) を
  「フレーム毎のカウンタで一段一段減衰させる」のではなく「無音に転じた
  フレーム番号を記録し、しきい値以上に復帰したときだけキャンセルする」
  という anchor 方式で実装している点。

VRCT が以前 (`a01ffc7f`) 自作した `StreamingVadSegmenter` は、中間確率帯
(`negative_threshold <= prob < positive_threshold`) のフレームで
`_negative_frames` カウンタが「増えも減りもしない」という未定義動作を
持っており、これが誤った早期終端や復帰遅延の温床になった
(ADR-0003 参照、ADR-0004 でパイプライン自体を一度撤退)。
今回は上記 anchor 方式を採用することで、この種の未定義動作をそもそも
発生させない設計にしている。

max_speech_frames による強制分割は PuriPuly の `max_segment_ms` と同じ
安全装置で、ADR-0003 で「無音が来ない限りセグメントが無限に伸びる」
退行の再発を防ぐために必須とする。

デフォルトパラメータ (threshold=0.25, negative=0.10, hangover=24frames
≒768ms, pre_speech_pad=5frames≒160ms, min_speech=2frames) は、
`docs/ref/kikitan-translator/src/recognizers/VAD.ts` で実運用され、
ユーザー評価上 VRCT より認識精度が高いとされる値をそのまま採用する。
silero-vad 公式ライブラリのデフォルト (threshold=0.5, min_silence=100ms)
は汎用チューニングであり、VRChat の音声環境 (BGM混入、複数人の会話) を
想定した実績値を優先する。

`diagnostic_callback` は PuriPuly-heart の `diagnostic_event_callback` に
倣った任意のフック。フレーム単位ではなく speech_start/speech_end の
状態遷移時のみ呼ばれる (VRCT の用途ではフレーム毎に呼ぶ必要がある
ほどホットパスではないため、PuriPuly側にある `diagnostics_enabled` の
遅延ゲートは持たない)。呼び出し元が壊れていても VAD 自体は止めない。
"""

import audioop
import itertools
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Literal, Optional, Protocol

import numpy as np

TARGET_SAMPLE_RATE = 16000
FRAME_SAMPLES = 512
FRAME_DURATION_MS = FRAME_SAMPLES / TARGET_SAMPLE_RATE * 1000  # 32.0 ms

# mic/speaker セッションを再起動しても UI 上で表示済みの segment_id と
# 衝突しないよう、プロセス全体で共有するカウンタ。
_segment_id_counter = itertools.count()

SegmentEndReason = Literal["silence", "max_duration", "flush"]


class Pcm16MonoNormalizer:
    """任意のサンプルレート/チャンネル数の PCM を 16kHz mono int16 に正規化する。"""

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


class VadEngine(Protocol):
    def __call__(self, frame: np.ndarray) -> float: ...
    def reset(self) -> None: ...


class SileroFrameProbability:
    """faster-whisper に同梱される Silero VAD ONNX モデルで1フレームの発話確率を計算する。

    faster-whisper は既存依存であり、追加のモデルバンドルやネットワーク
    アクセスなしにオフラインで動作する (PyInstaller 配布物にも同梱済み)。
    """

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


@dataclass(frozen=True)
class SpeechSegment:
    audio: bytes
    segment_id: int
    reason: SegmentEndReason

    @property
    def duration_ms(self) -> float:
        return len(self.audio) / 2 / TARGET_SAMPLE_RATE * 1000


class VadSegmenter:
    """発話区間を検出し、確定済み (silence/max_duration/flush で終端した)
    セグメントのみを返す状態機械。

    partial (発話中の暫定結果) は一切扱わない — `SpeechEnd` 相当の
    確定セグメントのみを外部に公開する。理由は ADR-0005 参照
    (partial 関連のバグ再発を避けるため、今回のスコープから明示的に除外)。
    """

    def __init__(
        self,
        probability: Optional[VadEngine] = None,
        *,
        speech_threshold: float = 0.25,
        negative_threshold: Optional[float] = None,
        hangover_frames: int = 24,
        max_speech_frames: Optional[int] = 250,
        min_speech_frames: int = 2,
        pre_speech_pad_frames: int = 5,
        diagnostic_callback: Optional[Callable[[str], None]] = None,
        diagnostic_label: str = "vad",
    ) -> None:
        self.probability = probability or SileroFrameProbability()
        self.speech_threshold = speech_threshold
        # silero-vad 公式 VADIterator は negative_threshold を
        # `threshold - 0.15` の固定オフセットとして扱う
        # (docs/ref/silero-vad/src/silero_vad/utils_vad.py:538)。
        # 明示指定が無ければこの式に従う。
        self.negative_threshold = (
            negative_threshold if negative_threshold is not None else max(0.0, speech_threshold - 0.15)
        )
        self.hangover_frames = hangover_frames
        self.max_speech_frames = max_speech_frames
        self.min_speech_frames = min_speech_frames
        self.pre_speech_frames: Deque[bytes] = deque(maxlen=pre_speech_pad_frames)
        self.diagnostic_callback = diagnostic_callback
        self.diagnostic_label = diagnostic_label
        self._remainder = b""
        self._speech_frames: list[bytes] = []
        self._positive_frames = 0
        self._speech_frame_count = 0
        # 無音に転じたフレーム番号 (speech_frame_count 基準) を記録する
        # anchor。しきい値以上に復帰したときだけ None に戻す。中間確率帯
        # のフレームでは何もしない (anchor をリセットも延長もしない) —
        # これが公式 VADIterator の temp_end と同じ設計で、ADR-0003 の
        # 「中間帯フレームで負カウンタが停滞する」バグをそもそも起こさない。
        self._silence_start_frame: Optional[int] = None
        self._speaking = False
        self._segment_id = next(_segment_id_counter)

    @property
    def speaking(self) -> bool:
        return self._speaking

    def process(self, pcm: bytes) -> list[SpeechSegment]:
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

        return segments

    def flush(self) -> Optional[SpeechSegment]:
        """pause/stop 等でストリームを止める際、未確定の発話区間があれば
        強制的にセグメントとして確定する (`reason="flush"`)。
        """
        if self._remainder:
            padded = self._remainder.ljust(FRAME_SAMPLES * 2, b"\0")
            self._remainder = b""
            samples = np.frombuffer(padded, dtype="<i2").astype(np.float32) / 32768.0
            result = self._process_frame(padded, self.probability(samples))
            if result is not None:
                return result
        if not self._speaking:
            return None
        return self._finish_segment(reason="flush")

    def reset(self) -> None:
        """外部から完全な初期状態に戻す (mute/デバイス切替等)。"""
        self._remainder = b""
        self._speech_frames = []
        self._positive_frames = 0
        self._speech_frame_count = 0
        self._silence_start_frame = None
        self._speaking = False
        self.pre_speech_frames.clear()
        reset = getattr(self.probability, "reset", None)
        if callable(reset):
            reset()

    def _process_frame(self, frame: bytes, prob: float) -> Optional[SpeechSegment]:
        if not self._speaking:
            self.pre_speech_frames.append(frame)
            if prob >= self.speech_threshold:
                self._positive_frames += 1
            else:
                self._positive_frames = 0
            if self._positive_frames >= self.min_speech_frames:
                self._speaking = True
                self._speech_frames = list(self.pre_speech_frames)
                self._speech_frame_count = self._positive_frames
                self._silence_start_frame = None
                self.pre_speech_frames.clear()
                self._log(
                    f"speech_start segment_id={self._segment_id} prob={prob:.3f} "
                    f"threshold={self.speech_threshold} pre_roll_frames={len(self._speech_frames)}"
                )
                if self._max_speech_reached():
                    return self._finish_segment(reason="max_duration")
            return None

        self._speech_frames.append(frame)
        self._speech_frame_count += 1

        if prob >= self.speech_threshold:
            self._silence_start_frame = None
        elif prob < self.negative_threshold:
            if self._silence_start_frame is None:
                self._silence_start_frame = self._speech_frame_count
            if self._speech_frame_count - self._silence_start_frame >= self.hangover_frames:
                return self._finish_segment(reason="silence")
        # else: 中間確率帯。anchor には触れない (公式実装と同じ)。

        if self._max_speech_reached():
            return self._finish_segment(reason="max_duration")
        return None

    def _max_speech_reached(self) -> bool:
        if self.max_speech_frames is None:
            return False
        return self._speech_frame_count >= self.max_speech_frames

    def _finish_segment(self, reason: SegmentEndReason) -> Optional[SpeechSegment]:
        frame_count = self._speech_frame_count
        result = None
        if self._speaking and frame_count >= self.min_speech_frames:
            result = SpeechSegment(b"".join(self._speech_frames), self._segment_id, reason=reason)
        if self._speaking or self._positive_frames:
            self._segment_id = next(_segment_id_counter)

        self._speech_frames = []
        self._positive_frames = 0
        self._speech_frame_count = 0
        self._silence_start_frame = None
        self._speaking = False
        self.pre_speech_frames.clear()

        if result is not None:
            self._log(
                f"speech_end segment_id={result.segment_id} reason={reason} "
                f"duration_ms={result.duration_ms:.1f} frames={frame_count}"
            )

        if reason != "max_duration":
            # PuriPuly-heart の VadGating に倣い、強制分割 (max_duration) では
            # Silero ONNX の内部 state をリセットしない。発話者はまだ話し
            # 続けているため、モデルの文脈を維持したまま次のセグメントの
            # 認識に引き継ぐ (state をリセットすると、話者が実際には
            # 話し続けているのに再度「発話開始」から検出し直すことになり、
            # min_speech_frames 分の遅延と精度低下を招く)。
            reset = getattr(self.probability, "reset", None)
            if callable(reset):
                reset()
        return result

    def _log(self, message: str) -> None:
        if self.diagnostic_callback is None:
            return
        try:
            self.diagnostic_callback(f"[VAD][{self.diagnostic_label}] {message}")
        except Exception:
            # 診断ログの失敗で VAD 自体を止めない。
            pass


class VadRecognizerAdapter:
    """custom_speech_recognition の `Recognizer.listen_with_segmenter_in_background`
    が要求するプロトコル (`sample_rate`/`sample_width`/`process`/`flush`) に
    `VadSegmenter` を適合させる薄いアダプタ。

    `custom_speech_recognition` 自体は VAD/Silero を一切知らない (汎用の
    差し込み点のみを提供する設計、詳細は fork 側コミット参照)。`VadSegmenter`
    もマイク/スピーカーのネイティブなサンプルレート/チャンネル数を知らない
    (常に 16kHz mono int16 前提) ため、両者を繋ぐ変換をここで行う。
    """

    sample_rate = TARGET_SAMPLE_RATE
    sample_width = 2  # 16-bit PCM

    def __init__(
        self,
        native_sample_rate: int,
        native_sample_width: int,
        native_channels: int,
        segmenter: Optional[VadSegmenter] = None,
    ) -> None:
        self._normalizer = Pcm16MonoNormalizer(native_sample_rate, native_sample_width, native_channels)
        self.segmenter = segmenter or VadSegmenter()

    def process(self, pcm_bytes: bytes) -> list[SpeechSegment]:
        normalized = self._normalizer.process(pcm_bytes)
        if not normalized:
            return []
        return self.segmenter.process(normalized)

    def flush(self) -> Optional[SpeechSegment]:
        result = self.segmenter.flush()
        self._normalizer.reset()
        return result

    def reset(self) -> None:
        """外部から完全な初期状態に戻す (mute/デバイス切替等)。"""
        self._normalizer.reset()
        self.segmenter.reset()
