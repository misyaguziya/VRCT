import unittest
from datetime import datetime, timedelta
from queue import Queue
from unittest.mock import MagicMock, patch

import numpy as np

from speech_recognition.exceptions import RequestError, UnknownValueError

from errors import ErrorCode
from models.transcription.transcription_providers import TranscriptionApiError
from models.transcription.transcription_transcriber import (
    AudioTranscriber,
    GOOGLE_RECOGNIZE_TIMEOUT_SECONDS,
    MAX_PHRASE_DURATION_SECONDS,
)


class FakeAudioSource:
    SAMPLE_RATE = 16000
    SAMPLE_WIDTH = 2
    channels = 1


def _already_old_timestamp() -> datetime:
    """実時間で既に phrase_timeout (テストでは常に3秒以下) を超えている
    過去の時刻を返す。「確定してから送る」設計 (フェーズ3項目20の代替、
    2026-09-06のコードレビュー議論) では、キューに1件しか無い単発の
    チャンクは無音ギャップ・最大長のどちらの確定条件にも触れないため、
    末尾タイムアウト (キューが空のまま実時間で phrase_timeout 秒経過) を
    使って確定を即座に発生させる。"""
    return datetime.now() - timedelta(seconds=10)


class TestAudioProcessingSelection(unittest.TestCase):
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_selects_mic_processing_for_microphone(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")

        self.assertEqual(transcriber.audio_sources["process_data_func"], transcriber.processMicData)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_selects_speaker_processing_for_speaker(self, _) -> None:
        transcriber = AudioTranscriber(True, FakeAudioSource(), 3, 10, "Google")

        self.assertEqual(transcriber.audio_sources["process_data_func"], transcriber.processSpeakerData)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_reads_normalized_speaker_pcm_as_mono(self, _) -> None:
        transcriber = AudioTranscriber(True, FakeAudioSource(), 3, 10, "Google")
        pcm = np.array([1000, -1000], dtype="<i2").tobytes()
        transcriber.audio_sources["last_sample"] = pcm

        result = transcriber.processSpeakerData()

        self.assertEqual(result.get_raw_data(), pcm)


class TestGoogleRecognizerTimeout(unittest.TestCase):
    """Issue #63: Google recognition must not block indefinitely on a bad network."""

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_recognizer_has_finite_operation_timeout(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")

        self.assertEqual(transcriber.audio_recognizer.operation_timeout, GOOGLE_RECOGNIZE_TIMEOUT_SECONDS)

    @patch("models.transcription.transcription_transcriber.errorLogging")
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_request_error_is_logged_instead_of_swallowed(self, _, mock_error_logging) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.audio_recognizer.recognize_google = MagicMock(
            side_effect=RequestError("recognition connection failed: timed out")
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        mock_error_logging.assert_called_once()

    @patch("models.transcription.transcription_transcriber.errorLogging")
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_flags_recognition_error_for_ui_visibility(self, _, __) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.audio_recognizer.recognize_google = MagicMock(
            side_effect=RequestError("recognition connection failed: timed out")
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(transcriber.last_recognition_error)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_clears_recognition_error_flag_after_a_successful_call(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.last_recognition_error = True
        transcriber.audio_recognizer.recognize_google = MagicMock(return_value=("hello", 0.9))
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertFalse(transcriber.last_recognition_error)


class TestQueueProcessing(unittest.TestCase):
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_drains_queued_audio_before_transcribing(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now))
        audio_queue.put((b"\x02\x00", now + timedelta(milliseconds=100)))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        # Queue が空になっていて、まだ確定条件に触れていないので蓄積される
        # だけ (無音ギャップも最大長も超えていない)。
        self.assertTrue(audio_queue.empty())
        self.assertEqual(transcriber.audio_sources["last_sample"], b"\x01\x00\x02\x00")
        transcriber.whisper_model.transcribe.assert_not_called()

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_phrase_timeout_finalizes_the_previous_phrase_before_reset(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now))
        # phrase_timeout=3s より大きなギャップ。直前のフレーズ (chunk1) は
        # リセットで消える前に確定・送信され、chunk2 から新フレーズとして
        # 蓄積が始まる。
        audio_queue.put((b"\x02\x00", now + timedelta(seconds=5)))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        transcriber.whisper_model.transcribe.assert_called_once()
        self.assertEqual(transcriber.audio_sources["last_sample"], b"\x02\x00")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_passes_configured_thresholds_to_whisper(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(
            audio_queue,
            ["Japanese"],
            ["Japan"],
            avg_logprob=-0.55,
            no_speech_prob=0.42,
        )

        kwargs = transcriber.whisper_model.transcribe.call_args.kwargs
        self.assertEqual(kwargs["log_prob_threshold"], -0.55)
        self.assertEqual(kwargs["no_speech_threshold"], 0.42)


class TestConfirmedCompleteTranscription(unittest.TestCase):
    """フェーズ3項目20の代替 (2026-09-06のコードレビュー議論): 無音ギャップ
    が来ない継続発話でも、毎回その時点の last_sample 全体を再送信すると、
    送るたびに音声が長くなり推論がさらに遅くなる雪だるま式の遅延になる。
    フレーズが「完成した」と判断できるまで文字起こしを実行しないことで
    これを防ぐ。完成の判定は3種類 (無音ギャップ/最大長/末尾タイムアウト)。
    """

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_still_accumulating_does_not_transcribe_and_returns_false(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertFalse(result)
        transcriber.whisper_model.transcribe.assert_not_called()
        self.assertEqual(transcriber.audio_sources["last_sample"], b"\x01\x00")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_max_duration_forces_finalization_without_a_silence_gap(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 30, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now))
        # 無音ギャップ (phrase_timeout=30s) は超えていないが、
        # MAX_PHRASE_DURATION_SECONDS (15秒) を超えて継続しているので
        # 強制的に確定されるはず。
        self.assertLess(MAX_PHRASE_DURATION_SECONDS, 30)
        audio_queue.put((b"\x02\x00", now + timedelta(seconds=MAX_PHRASE_DURATION_SECONDS + 1)))

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(result)
        # 最大長チェックはチャンクを追記した後に行う (PuriPuly-heart 等の
        # 参考実装と同じ方式) ため、閾値を超えさせた chunk2 自身も
        # まとめて確定・送信される (chunk2 用に新フレーズを開始する
        # わけではない)。
        transcriber.whisper_model.transcribe.assert_called_once()
        self.assertEqual(transcriber.audio_sources["last_sample"], b"")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_trailing_timeout_finalizes_when_no_further_chunk_ever_arrives(self, _) -> None:
        """発話がそこで終わった場合、次のチャンクは永久に来ない。次の
        チャンク到達を待つだけでは検知できないため、キューが空のまま
        実時間で phrase_timeout 秒経過したことを検知して確定させる。"""
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(result)
        transcriber.whisper_model.transcribe.assert_called_once()
        self.assertEqual(transcriber.audio_sources["last_sample"], b"")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_empty_queue_with_no_pending_audio_does_not_transcribe(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        audio_queue = Queue()

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertFalse(result)
        transcriber.whisper_model.transcribe.assert_not_called()

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_multiple_completed_phrases_in_one_backlog_catch_up_each_transcribe_once(self, _) -> None:
        """バックログ catch-up で1回の呼び出し中に複数の無音ギャップを
        跨ぐ場合、それぞれ個別に確定・送信されるはず (取りこぼさない)。"""
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now))
        audio_queue.put((b"\x02\x00", now + timedelta(seconds=5)))  # 1つ目のギャップ
        audio_queue.put((b"\x03\x00", now + timedelta(seconds=10)))  # 2つ目のギャップ

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(result)
        self.assertEqual(transcriber.whisper_model.transcribe.call_count, 2)
        self.assertEqual(transcriber.audio_sources["last_sample"], b"\x03\x00")


class TestVadSegmentedTranscription(unittest.TestCase):
    """config.ENABLE_VAD 経由 (vad_segmented=True) の場合、audio_queue の
    各アイテムは (raw_bytes, recorded_at, reason) の3要素タプル。

    当初は reason を区別せず毎回単独で確定・送信していたが、実機検証で
    「無音を挟まない継続発話が VadSegmenter.max_speech_frames の安全弁
    (reason="max_duration") で強制打ち切りされるたびに、単語の途中で
    始まり/終わる不自然な断片が単独でエンジンに送られ、境界の不自然さで
    信頼度フィルタに丸ごと棄却される」regressionが判明した (2026-09-06)。
    PuriPuly-heart を参考に、reason=="max_duration" の断片は単独送信せず
    蓄積し、次の自然な区切り (silence/flush) が来た時点でまとめて確定・
    送信するよう変更した。
    """

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_natural_reason_transcribes_immediately(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 999, 10, "Whisper", vad_segmented=True)
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now(), "silence"))

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(result)
        transcriber.whisper_model.transcribe.assert_called_once()
        self.assertEqual(transcriber.audio_sources["last_sample"], b"")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_flush_reason_also_transcribes_immediately(self, _) -> None:
        """flush (stop/pause 時の強制確定) も silence と同様に自然な区切り
        として即座に確定・送信すること (max_duration だけを特別扱いする)。"""
        transcriber = AudioTranscriber(False, FakeAudioSource(), 999, 10, "Whisper", vad_segmented=True)
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now(), "flush"))

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(result)
        transcriber.whisper_model.transcribe.assert_called_once()

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_max_duration_reason_accumulates_without_transcribing(self, _) -> None:
        """強制打ち切り (max_duration) された断片は単独で送信せず蓄積する
        だけ。まだ話者は話し続けている可能性が高く、単独送信すると単語の
        途中で始まり/終わる不自然な音声になり、エンジン側の信頼度フィルタ
        に丸ごと棄却されるリスクがあるため (2026-09-06、実機で確認)。"""
        transcriber = AudioTranscriber(False, FakeAudioSource(), 999, 10, "Whisper", vad_segmented=True)
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now(), "max_duration"))

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertFalse(result)
        transcriber.whisper_model.transcribe.assert_not_called()
        self.assertEqual(transcriber.audio_sources["last_sample"], b"\x01\x00")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_max_duration_fragments_are_concatenated_then_sent_together_on_natural_reason(
        self, _
    ) -> None:
        """複数回の強制打ち切り (max_duration) を挟んでも音声は蓄積され、
        最終的に自然な区切り (silence) が来た時点でまとめて1回だけ
        エンジンに送信されること (分断された断片をそれぞれ単独送信して
        内容を欠落させない)。"""
        transcriber = AudioTranscriber(False, FakeAudioSource(), 999, 10, "Whisper", vad_segmented=True)
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        seen_last_samples = []

        def _record_and_transcribe(*_args, **_kwargs):
            seen_last_samples.append(transcriber.audio_sources["last_sample"])
            return ([], MagicMock(language_probability=1.0))

        transcriber.whisper_model.transcribe.side_effect = _record_and_transcribe
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now, "max_duration"))
        audio_queue.put((b"\x02\x00", now + timedelta(seconds=7), "max_duration"))
        audio_queue.put((b"\x03\x00", now + timedelta(seconds=14), "silence"))

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(result)
        transcriber.whisper_model.transcribe.assert_called_once()
        self.assertEqual(seen_last_samples, [b"\x01\x00\x02\x00\x03\x00"])
        self.assertEqual(transcriber.audio_sources["last_sample"], b"")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_max_duration_safety_net_forces_send_if_no_natural_reason_ever_arrives(
        self, _
    ) -> None:
        """話者が本当にノンストップで話し続け、VAD が silence/flush を
        一切返さず max_duration だけを繰り返す病的なケースの保険。
        MAX_PHRASE_DURATION_SECONDS を超えたら max_duration のままでも
        強制的に確定・送信する (エネルギー閾値方式と同じ安全弁)。"""
        transcriber = AudioTranscriber(False, FakeAudioSource(), 999, 10, "Whisper", vad_segmented=True)
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now, "max_duration"))
        self.assertLess(MAX_PHRASE_DURATION_SECONDS, 20)
        audio_queue.put(
            (b"\x02\x00", now + timedelta(seconds=MAX_PHRASE_DURATION_SECONDS + 1), "max_duration")
        )

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(result)
        transcriber.whisper_model.transcribe.assert_called_once()
        self.assertEqual(transcriber.audio_sources["last_sample"], b"")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_empty_queue_does_not_transcribe(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper", vad_segmented=True)
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        audio_queue = Queue()

        result = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertFalse(result)
        transcriber.whisper_model.transcribe.assert_not_called()


class TestApiTranscriptionEngines(unittest.TestCase):
    """Groq/OpenAI/カスタムサーバー (OpenAICompatibleTranscriptionProvider) 経由の
    ディスパッチ。プロバイダ自体の挙動 (SDK呼び出し詳細) は
    test_transcription_providers.py で検証済みのため、ここでは
    AudioTranscriber 側の配線・エラー伝播・複数言語候補ループのみを見る。
    """

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_constructs_provider_with_engine_specific_credentials(self, provider_cls, _) -> None:
        AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Groq_Whisper",
            api_key="sk-groq", base_url="https://api.groq.com/openai/v1", api_model="whisper-large-v3",
        )

        provider_cls.assert_called_once_with(
            api_key="sk-groq",
            base_url="https://api.groq.com/openai/v1",
            model="whisper-large-v3",
            engine_name="Groq_Whisper",
        )

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_transcribes_via_api_provider_and_updates_transcript(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "OpenAI_Whisper",
            api_key="sk-openai", base_url="https://api.openai.com/v1", api_model="whisper-1",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertEqual(transcriber.getTranscript()["text"], "hello")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_api_error_sets_recognition_error_and_error_code(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.side_effect = TranscriptionApiError(
            ErrorCode.TRANSCRIPTION_API_AUTH_FAILED
        )
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Custom_Whisper",
            api_key="", base_url="http://localhost:8000/v1", api_model="whisper",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(transcriber.last_recognition_error)
        self.assertEqual(transcriber.last_api_error_code, ErrorCode.TRANSCRIPTION_API_AUTH_FAILED)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_clears_previous_error_state_before_a_successful_call(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Groq_Whisper",
            api_key="sk-groq", base_url="https://api.groq.com/openai/v1", api_model="whisper-large-v3",
        )
        transcriber.last_recognition_error = True
        transcriber.last_api_error_code = ErrorCode.TRANSCRIPTION_API_TIMEOUT
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertFalse(transcriber.last_recognition_error)
        self.assertIsNone(transcriber.last_api_error_code)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_definitive_result_stops_trying_further_language_candidates(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Groq_Whisper",
            api_key="sk-groq", base_url="https://api.groq.com/openai/v1", api_model="whisper-large-v3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese", "English"], ["Japan", "United States"])

        self.assertEqual(provider_cls.return_value.transcribe.call_count, 1)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_keeps_trying_remaining_candidates_when_not_definitive(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.side_effect = [
            ("low", 0.2, False),
            ("high", 0.8, False),
        ]
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Groq_Whisper",
            api_key="sk-groq", base_url="https://api.groq.com/openai/v1", api_model="whisper-large-v3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese", "English"], ["Japan", "United States"])

        self.assertEqual(provider_cls.return_value.transcribe.call_count, 2)
        self.assertEqual(transcriber.getTranscript()["text"], "high")


class TestDeepgramTranscriptionEngine(unittest.TestCase):
    """Deepgram (DeepgramProvider) 経由のディスパッチ。base_url を持たない
    点が Groq/OpenAI/カスタムサーバーと異なる。"""

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.DeepgramProvider")
    def test_constructs_provider_with_api_key_and_model_only(self, provider_cls, _) -> None:
        AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Deepgram",
            api_key="dg-test", api_model="nova-3",
        )

        provider_cls.assert_called_once_with(api_key="dg-test", model="nova-3", model_languages=None)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.DeepgramProvider")
    def test_passes_model_languages_through_to_provider(self, provider_cls, _) -> None:
        AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Deepgram",
            api_key="dg-test", api_model="nova-3", api_model_languages=["en", "ja"],
        )

        provider_cls.assert_called_once_with(api_key="dg-test", model="nova-3", model_languages=["en", "ja"])

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.DeepgramProvider")
    def test_transcribes_via_provider_and_updates_transcript(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Deepgram",
            api_key="dg-test", api_model="nova-3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertEqual(transcriber.getTranscript()["text"], "hello")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.DeepgramProvider")
    def test_api_error_sets_recognition_error_and_error_code(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.side_effect = TranscriptionApiError(
            ErrorCode.TRANSCRIPTION_API_AUTH_FAILED
        )
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Deepgram",
            api_key="dg-bad", api_model="nova-3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(transcriber.last_recognition_error)
        self.assertEqual(transcriber.last_api_error_code, ErrorCode.TRANSCRIPTION_API_AUTH_FAILED)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.DeepgramProvider")
    def test_single_call_regardless_of_candidate_language_count(self, provider_cls, _) -> None:
        # DeepgramProvider は常に is_definitive=True を返す (1回の呼び出しで
        # 自動言語検出が完結するため)。複数候補言語を渡しても1回しか
        # 呼ばれないことを確認する。
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Deepgram",
            api_key="dg-test", api_model="nova-3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese", "English"], ["Japan", "United States"])

        self.assertEqual(provider_cls.return_value.transcribe.call_count, 1)


class TestWhisperResilienceAcrossCandidates(unittest.TestCase):
    """ローカル Whisper は1候補目で例外が出ても2候補目を試す
    (エラーハンドリングを Google/API系と共通化した副次効果)。
    """

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_continues_to_next_language_after_an_error(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.side_effect = [
            RuntimeError("boom"),
            ([], MagicMock(text="ok", language_probability=0.7, language="ja")),
        ]
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        with patch("models.transcription.transcription_transcriber.errorLogging"):
            transcriber.transcribeAudioQueue(audio_queue, ["Japanese", "English"], ["Japan", "United States"])

        self.assertTrue(transcriber.last_recognition_error)
        self.assertEqual(transcriber.whisper_model.transcribe.call_count, 2)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_does_not_reset_error_flag_at_start_of_call(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0, language="ja"))
        transcriber.last_recognition_error = True
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", _already_old_timestamp()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(transcriber.last_recognition_error)


class TestMutedMicMessage(unittest.TestCase):
    @patch("controller.model")
    @patch("controller.config")
    def test_discards_queued_result_while_vrc_mic_is_muted(self, config, model) -> None:
        from controller import Controller

        config.VRC_MIC_MUTE_SYNC = True
        model.mic_mute_status = True

        controller = Controller.__new__(Controller)
        controller.micMessage({"text": "anything", "language": "Japanese"})

        self.assertEqual(model.method_calls, [])


class TestRepeatDetection(unittest.TestCase):
    """VAD ストリーミング撤退 (ADR-0004) で segment_id が消えたため、
    連続同一メッセージは純粋にテキスト比較で抑制する。"""

    def test_receive_repeat_blocks_second_identical_text(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_receive_message = ""

        self.assertFalse(model.detectRepeatReceiveMessage("same text"))
        self.assertTrue(model.detectRepeatReceiveMessage("same text"))

    def test_receive_repeat_allows_different_text(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_receive_message = ""

        self.assertFalse(model.detectRepeatReceiveMessage("first"))
        self.assertFalse(model.detectRepeatReceiveMessage("second"))

    def test_send_repeat_blocks_second_identical_text(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_send_message = ""

        self.assertFalse(model.detectRepeatSendMessage("same text"))
        self.assertTrue(model.detectRepeatSendMessage("same text"))

    def test_send_repeat_allows_different_text(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_send_message = ""

        self.assertFalse(model.detectRepeatSendMessage("first"))
        self.assertFalse(model.detectRepeatSendMessage("second"))


if __name__ == "__main__":
    unittest.main()
