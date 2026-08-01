import unittest
from threading import Event
from queue import Queue
from unittest.mock import patch

from models.transcription.audio_pipeline import AudioQueueItem, StreamingVadSegmenter
from models.transcription.transcription_recorder import BaseEnergyAndAudioRecorder, _create_microphone


class FakeAudioSource:
    def __init__(self, opens: bool) -> None:
        self.opens = opens
        self.stream = None
        self.exit_called = False

    def __enter__(self):
        if self.opens:
            self.stream = object()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.exit_called = True
        if self.stream is None:
            raise AttributeError("'NoneType' object has no attribute 'close'")
        self.stream = None


class TestCreateMicrophone(unittest.TestCase):
    def test_falls_back_without_closing_unopened_stream(self) -> None:
        selected_source = FakeAudioSource(opens=False)
        default_source = FakeAudioSource(opens=True)

        with patch(
            "models.transcription.transcription_recorder.Microphone",
            side_effect=[selected_source, default_source],
        ):
            source = _create_microphone({}, device_index=10)

        self.assertIs(source, default_source)
        self.assertFalse(selected_source.exit_called)
        self.assertTrue(default_source.exit_called)

    def test_raises_clear_error_when_no_device_opens(self) -> None:
        selected_source = FakeAudioSource(opens=False)
        default_source = FakeAudioSource(opens=False)

        with patch(
            "models.transcription.transcription_recorder.Microphone",
            side_effect=[selected_source, default_source],
        ):
            with self.assertRaisesRegex(OSError, "audio devices could not be opened"):
                _create_microphone({}, device_index=10)

        self.assertFalse(selected_source.exit_called)
        self.assertFalse(default_source.exit_called)


class RecorderAudioSource:
    SAMPLE_RATE = 48000
    SAMPLE_WIDTH = 2
    channels = 2


class FakeStreamAudioSource:
    SAMPLE_RATE = 16000
    SAMPLE_WIDTH = 2
    channels = 1
    CHUNK = 512

    def __init__(self, frames: int) -> None:
        self.frames = frames
        self.stream = self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self, _) -> bytes:
        if self.frames == 0:
            raise EOFError
        self.frames -= 1
        return b"\xe8\x03" * 512


class BlockingStreamAudioSource(FakeStreamAudioSource):
    def __init__(self, frames: int, block_after_reads: int) -> None:
        super().__init__(frames)
        self.block_after_reads = block_after_reads
        self.read_count = 0
        self.release_event = Event()

    def read(self, chunk_size) -> bytes:
        if self.read_count >= self.block_after_reads:
            self.release_event.wait(timeout=1)
        self.read_count += 1
        return super().read(chunk_size)

    def release(self) -> None:
        self.release_event.set()


class ProbabilitySequence:
    def __init__(self, values: list[float]) -> None:
        self.values = iter(values)

    def __call__(self, _) -> float:
        return next(self.values)


class TestRecorderAudioPipeline(unittest.TestCase):
    def test_exposes_normalized_output_format(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(), 300, False, 3, 3, 5, vad_filter=True
        )

        self.assertEqual(recorder.SAMPLE_RATE, 16000)
        self.assertEqual(recorder.SAMPLE_WIDTH, 2)
        self.assertEqual(recorder.channels, 1)
        self.assertIsInstance(recorder.vad_segmenter, StreamingVadSegmenter)

    def test_streams_final_vad_segment_from_device_frames(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            FakeStreamAudioSource(6), 300, False, 3, 3, 5, vad_filter=True
        )
        recorder.vad_segmenter = StreamingVadSegmenter(
            ProbabilitySequence([0.0, 0.3, 0.4, 0.5, 0.05, 0.05]),
            redemption_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=1,
        )
        queue = Queue()

        recorder.recordIntoQueue(queue)
        item = queue.get(timeout=1)
        recorder.stop()

        self.assertIsInstance(item, AudioQueueItem)
        self.assertTrue(item.is_final)
        self.assertGreater(len(item.audio), 0)

    def test_streams_partial_snapshot_during_long_speech(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            FakeStreamAudioSource(10), 300, False, 0.25, 3, 5, vad_filter=True
        )
        recorder.vad_segmenter = StreamingVadSegmenter(
            ProbabilitySequence([0.0] + [0.5] * 9),
            redemption_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=1,
        )
        queue = Queue()

        recorder.recordIntoQueue(queue)
        item = queue.get(timeout=1)
        recorder.stop()

        self.assertIsInstance(item, AudioQueueItem)
        self.assertFalse(item.is_final)
        self.assertGreaterEqual(len(item.audio) / 2 / 16000, 0.25)

    def test_flushes_final_segment_when_stream_stops_without_trailing_silence(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            FakeStreamAudioSource(3), 300, False, 3, 3, 5, vad_filter=True
        )
        recorder.vad_segmenter = StreamingVadSegmenter(
            ProbabilitySequence([0.0, 0.3, 0.4]),
            redemption_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=1,
        )
        queue = Queue()

        recorder.recordIntoQueue(queue)
        item = queue.get(timeout=1)
        recorder.stop()

        self.assertIsInstance(item, AudioQueueItem)
        self.assertTrue(item.is_final)
        self.assertGreater(len(item.audio), 0)

    def test_flushes_current_segment_when_paused(self) -> None:
        source = BlockingStreamAudioSource(20, block_after_reads=10)
        recorder = BaseEnergyAndAudioRecorder(
            source, 300, False, 0.25, 3, 5, vad_filter=True
        )
        recorder.vad_segmenter = StreamingVadSegmenter(
            ProbabilitySequence([0.0] + [0.5] * 19),
            redemption_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=1,
        )
        queue = Queue()

        recorder.recordIntoQueue(queue)
        partial = queue.get(timeout=1)
        recorder.pause()
        source.release()
        final = queue.get(timeout=1)
        recorder.stop()

        self.assertFalse(partial.is_final)
        self.assertTrue(final.is_final)
        self.assertEqual(partial.segment_id, final.segment_id)


if __name__ == "__main__":
    unittest.main()