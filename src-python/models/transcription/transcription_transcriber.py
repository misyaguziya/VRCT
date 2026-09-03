"""Runtime transcriber that wraps Google SpeechRecognition and faster-whisper.

This class focuses on converting incoming raw audio buffers into text using
either the Google web recognizer (online) or a local Whisper model (offline).

VAD ストリーミング撤退 (ADR-0004) 以降、キューには
(raw_bytes, recorded_at) タプルだけが積まれる。フレーズ境界は
`speech_recognition.listen_energy_and_audio_in_background` の phrase_time_limit と
AudioTranscriber.updateLastSampleAndPhraseStatus の phrase_timeout で決まる。
partial (発話中の暫定結果) 通知は行わない。
"""

import time
from io import BytesIO
from queue import Empty
from threading import Event
import wave
from typing import Any, Dict, List, Optional
from speech_recognition import Recognizer, AudioData, AudioFile
from speech_recognition.exceptions import UnknownValueError
from datetime import timedelta
from pyaudiowpatch import get_sample_size, paInt16
from .transcription_whisper import getWhisperModel, checkWhisperWeight
from .transcription_providers import (
    GoogleProvider,
    LocalWhisperProvider,
    OpenAICompatibleTranscriptionProvider,
    DeepgramProvider,
    TranscriptionApiError,
)
from .transcription_openai_compatible import TRANSCRIPTION_API_ENGINES as _API_TRANSCRIPTION_ENGINES

# OpenAI互換系 (base_url/model差し替え) に加えて、独自プロトコルの
# Deepgramも「APIキー/モデルを持つクラウドエンジン」として同列に扱う箇所
# (last_recognition_errorのリセット対象等) で使う。
_CLOUD_TRANSCRIPTION_ENGINES = _API_TRANSCRIPTION_ENGINES + ("Deepgram",)

from pydub import AudioSegment
from errors import ErrorCode
from utils import errorLogging

import warnings
warnings.simplefilter('ignore', RuntimeWarning)

PHRASE_TIMEOUT = 3
MAX_PHRASES = 10
GOOGLE_RECOGNIZE_TIMEOUT_SECONDS = 10


class AudioTranscriber:
    """Convert queued audio buffers into transcripts.

    Public attributes set by the constructor:
    - speaker: bool
    - phrase_timeout: int
    - max_phrases: int
    """

    def __init__(
        self,
        speaker: bool,
        source: Any,
        phrase_timeout: int,
        max_phrases: int,
        transcription_engine: str,
        root: Optional[str] = None,
        whisper_weight_type: Optional[str] = None,
        device: str = "cpu",
        device_index: int = 0,
        compute_type: str = "auto",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        api_model: Optional[str] = None,
        api_model_languages: Optional[List[str]] = None,
    ) -> None:
        self.speaker = speaker
        self.phrase_timeout = phrase_timeout
        self.max_phrases = max_phrases
        self.transcript_data: List[Dict[str, Any]] = []
        self.transcript_changed_event = Event()
        self.last_recognition_error = False
        self.last_api_error_code: Optional[ErrorCode] = None
        self.audio_recognizer = Recognizer()
        self.audio_recognizer.operation_timeout = GOOGLE_RECOGNIZE_TIMEOUT_SECONDS
        self.transcription_engine = "Google"
        self.whisper_model = None
        self.whisper_weight_type = whisper_weight_type
        self._api_provider: Optional[OpenAICompatibleTranscriptionProvider] = None
        self.audio_sources: Dict[str, Any] = {
            "sample_rate": source.SAMPLE_RATE,
            "sample_width": source.SAMPLE_WIDTH,
            "channels": source.channels,
            "last_sample": bytes(),
            "last_spoken": None,
            "new_phrase": True,
            "process_data_func": self.processSpeakerData if speaker else self.processMicData,
        }

        if transcription_engine == "Whisper" and checkWhisperWeight(root, whisper_weight_type) is True:
            self.whisper_model = getWhisperModel(
                root, whisper_weight_type, device=device, device_index=device_index, compute_type=compute_type
            )
            self.transcription_engine = "Whisper"
        elif transcription_engine in _API_TRANSCRIPTION_ENGINES:
            self.transcription_engine = transcription_engine
            try:
                self._api_provider = OpenAICompatibleTranscriptionProvider(
                    api_key=api_key or "",
                    base_url=base_url or "",
                    model=api_model or "",
                    engine_name=transcription_engine,
                )
            except Exception:
                errorLogging()
                self._api_provider = None
        elif transcription_engine == "Deepgram":
            self.transcription_engine = transcription_engine
            try:
                self._api_provider = DeepgramProvider(
                    api_key=api_key or "",
                    model=api_model or "",
                    model_languages=api_model_languages,
                )
            except Exception:
                errorLogging()
                self._api_provider = None

    def _resolve_provider(self):
        """`self.transcription_engine`/`self.whisper_model` の"現在の"値を見て
        対応するプロバイダを返す。既存テストが構築後に直接
        `transcriber.transcription_engine`/`transcriber.whisper_model` を
        書き換える運用になっているため、`__init__` 時点で1回だけ決め打つ
        のではなく、呼び出しの都度その場で解決する。
        """
        if self.transcription_engine == "Whisper":
            if self.whisper_model is None:
                return None
            return LocalWhisperProvider(self.whisper_model)
        if self.transcription_engine in _CLOUD_TRANSCRIPTION_ENGINES:
            return self._api_provider
        return GoogleProvider(self.audio_recognizer)

    def transcribeAudioQueue(
        self,
        audio_queue: Any,
        languages: List[str],
        countries: List[str],
        avg_logprob: float = -0.8,
        no_speech_prob: float = 0.6,
        no_repeat_ngram_size: int = 0,
    ) -> bool:
        try:
            audio, time_spoken = audio_queue.get_nowait()
        except Empty:
            time.sleep(0.01)
            return False
        # まとめて drain して最新まで反映する (backlog を残さない)
        self.updateLastSampleAndPhraseStatus(audio, time_spoken)
        while True:
            try:
                audio, time_spoken = audio_queue.get_nowait()
            except Empty:
                break
            self.updateLastSampleAndPhraseStatus(audio, time_spoken)

        # Google/API系はネットワーク経由のためエラーが一時的なことが多く、
        # 呼び出しの都度エラー状態をクリアして UI に古いエラーを残さない。
        # ローカル Whisper は従来からこのリセットを行っておらず、その挙動は
        # 変更しない (エラーが決定的である= リトライしても意味が薄いため)。
        if self.transcription_engine == "Google" or self.transcription_engine in _CLOUD_TRANSCRIPTION_ENGINES:
            self.last_recognition_error = False
            self.last_api_error_code = None

        best: Dict[str, Any] = {"confidence": 0, "text": "", "language": None}
        try:
            audio_data = self.audio_sources["process_data_func"]()
            provider = self._resolve_provider()
            if provider is not None:
                force_language = len(languages) == 1
                for language, country in zip(languages, countries):
                    try:
                        text, confidence, is_definitive = provider.transcribe(
                            audio_data,
                            language,
                            country,
                            avg_logprob=avg_logprob,
                            no_speech_prob=no_speech_prob,
                            no_repeat_ngram_size=no_repeat_ngram_size,
                            force_language=force_language,
                        )
                    except UnknownValueError:
                        continue
                    except TranscriptionApiError as exc:
                        self.last_recognition_error = True
                        self.last_api_error_code = exc.error_code
                        continue
                    except Exception:
                        self.last_recognition_error = True
                        errorLogging()
                        continue

                    if confidence > best["confidence"]:
                        best = {"confidence": confidence, "text": text, "language": language}
                    if is_definitive:
                        break

        except UnknownValueError:
            pass
        except Exception:
            errorLogging()

        if best["text"] != "":
            self.updateTranscript(best)
        return True

    def updateLastSampleAndPhraseStatus(self, data: bytes, time_spoken) -> None:
        source_info = self.audio_sources
        if source_info["last_spoken"] and time_spoken - source_info["last_spoken"] > timedelta(seconds=self.phrase_timeout):
            source_info["last_sample"] = bytes()
            source_info["new_phrase"] = True
        else:
            source_info["new_phrase"] = False

        source_info["last_sample"] += data
        source_info["last_spoken"] = time_spoken

    def processMicData(self) -> AudioData:
        audio_data = AudioData(
            self.audio_sources["last_sample"], self.audio_sources["sample_rate"], self.audio_sources["sample_width"]
        )
        return audio_data

    def processSpeakerData(self) -> AudioData:
        temp_file = BytesIO()
        with wave.open(temp_file, 'wb') as wf:
            wf.setnchannels(self.audio_sources["channels"])
            wf.setsampwidth(get_sample_size(paInt16))
            wf.setframerate(self.audio_sources["sample_rate"])
            wf.writeframes(self.audio_sources["last_sample"])
        temp_file.seek(0)

        if self.audio_sources["channels"] > 2:
            audio = AudioSegment.from_file(temp_file, format="wav")
            mono_audio = audio.set_channels(1)
            temp_file = BytesIO()
            mono_audio.export(temp_file, format="wav")
            temp_file.seek(0)

        with AudioFile(temp_file) as source:
            audio = self.audio_recognizer.record(source)
        return audio

    def updateTranscript(self, result: dict) -> None:
        source_info = self.audio_sources
        transcript = self.transcript_data

        if source_info["new_phrase"] or len(transcript) == 0:
            if len(transcript) > self.max_phrases:
                transcript.pop(-1)
            transcript.insert(0, result)
        else:
            transcript[0] = result

    def getTranscript(self) -> dict:
        if len(self.transcript_data) > 0:
            result = self.transcript_data.pop(-1)
        else:
            result = {"confidence": 0, "text": "", "language": None}
        return result

    def clearTranscriptData(self) -> None:
        self.transcript_data.clear()
        self.audio_sources["last_sample"] = bytes()
        self.audio_sources["new_phrase"] = True
