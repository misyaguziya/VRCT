"""Runtime transcriber that wraps Google SpeechRecognition and faster-whisper.

This class focuses on converting incoming raw audio buffers into text using
either the Google web recognizer (online) or a local Whisper model (offline).
"""

import time
from collections import deque
from io import BytesIO
from queue import Empty
from threading import Event
import wave
from typing import Any, Dict, List, Optional, Union
from speech_recognition import Recognizer, AudioData, AudioFile
from speech_recognition.exceptions import UnknownValueError
from datetime import datetime, timedelta
from pyaudiowpatch import get_sample_size, paInt16
from .transcription_languages import transcription_lang
from .transcription_whisper import getWhisperModel, checkWhisperWeight

import numpy as np
from pydub import AudioSegment
from utils import errorLogging
from .audio_pipeline import AudioQueueItem

import warnings
warnings.simplefilter('ignore', RuntimeWarning)

PHRASE_TIMEOUT = 3
MAX_PHRASES = 10
GOOGLE_RECOGNIZE_TIMEOUT_SECONDS = 10


def _should_use_vad_filter(vad_filter: bool, whisper_weight_type: Optional[str]) -> bool:
    return vad_filter or (
        isinstance(whisper_weight_type, str) and "turbo" in whisper_weight_type.lower()
    )


class AudioTranscriber:
    """Convert queued audio buffers into transcripts.

    Public attributes set by the constructor:
    - speaker: bool
    - phrase_timeout: int
    - max_phrases: int

    Methods are intentionally permissive about input types to match the
    existing codebase; this wrapper adds typing for clarity.
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
    ) -> None:
        self.speaker = speaker
        self.phrase_timeout = phrase_timeout
        self.max_phrases = max_phrases
        self.transcript_data: List[Dict[str, Any]] = []
        self.transcript_changed_event = Event()
        self.last_recognition_error = False
        self.audio_recognizer = Recognizer()
        self.audio_recognizer.operation_timeout = GOOGLE_RECOGNIZE_TIMEOUT_SECONDS
        self.transcription_engine = "Google"
        self.whisper_model = None
        self.whisper_weight_type = whisper_weight_type
        self.pending_audio_queue_items = deque()
        self.audio_sources: Dict[str, Any] = {
            "sample_rate": source.SAMPLE_RATE,
            "sample_width": source.SAMPLE_WIDTH,
            "channels": source.channels,
            "last_sample": bytes(),
            "last_spoken": None,
            "new_phrase": True,
            "segment_id": None,
            "is_final": True,
            "speech_ended_at": None,
            "process_data_func": self.processSpeakerData if speaker else self.processMicData,
        }

        if transcription_engine == "Whisper" and checkWhisperWeight(root, whisper_weight_type) is True:
            self.whisper_model = getWhisperModel(
                root, whisper_weight_type, device=device, device_index=device_index, compute_type=compute_type
            )
            self.transcription_engine = "Whisper"

    def transcribeAudioQueue(
        self,
        audio_queue: Any,
        languages: List[str],
        countries: List[str],
        avg_logprob: float = -0.8,
        no_speech_prob: float = 0.6,
        no_repeat_ngram_size: int = 0,
        vad_filter: bool = False,
        vad_parameters: Optional[Union[dict, Any]] = None,
    ) -> bool:
        if audio_queue.empty() and not self.pending_audio_queue_items:
            time.sleep(0.01)
            return False

        if self.pending_audio_queue_items:
            while True:
                try:
                    self._enqueue_audio_queue_item(audio_queue.get_nowait())
                except Empty:
                    break
            self._update_from_queue_item(self.pending_audio_queue_items.popleft())
        else:
            try:
                first_item = audio_queue.get_nowait()
            except Empty:
                time.sleep(0.01)
                return False

            if isinstance(first_item, AudioQueueItem):
                self._enqueue_audio_queue_item(first_item)
                while True:
                    try:
                        self._enqueue_audio_queue_item(audio_queue.get_nowait())
                    except Empty:
                        break
                self._update_from_queue_item(self.pending_audio_queue_items.popleft())
            else:
                self._update_from_queue_item(first_item)
                while True:
                    try:
                        self._update_from_queue_item(audio_queue.get_nowait())
                    except Empty:
                        break

        confidences: List[Dict[str, Any]] = [{"confidence": 0, "text": "", "language": None}]
        inference_started_at = time.perf_counter()
        try:
            audio_data = self.audio_sources["process_data_func"]()
            match self.transcription_engine:
                case "Google":
                    self.last_recognition_error = False
                    for language, country in zip(languages, countries):
                        try:
                            text, confidence = self.audio_recognizer.recognize_google(
                                audio_data,
                                language=transcription_lang[language][country][self.transcription_engine],
                                with_confidence=True
                                )
                            confidences.append({"confidence": confidence, "text": text, "language": language})
                        except UnknownValueError:
                            pass
                        except Exception:
                            self.last_recognition_error = True
                            errorLogging()
                case "Whisper":
                    audio_data = np.frombuffer(
                        audio_data.get_raw_data(convert_rate=16000, convert_width=2), np.int16
                    ).flatten().astype(np.float32) / 32768.0
                    import torch
                    if isinstance(audio_data, torch.Tensor):
                        audio_data = audio_data.detach().numpy()

                    for language, country in zip(languages, countries):
                        text = ""
                        source_language = (
                            transcription_lang[language][country][self.transcription_engine]
                            if len(languages) == 1
                            else None
                        )
                        segments, info = self.whisper_model.transcribe(
                            audio_data,
                            beam_size=5,
                            temperature=0.0,
                            log_prob_threshold=avg_logprob,
                            no_speech_threshold=no_speech_prob,
                            language=source_language,
                            word_timestamps=False,
                            without_timestamps=True,
                            task="transcribe",
                            no_repeat_ngram_size=no_repeat_ngram_size,
                            vad_filter=_should_use_vad_filter(vad_filter, self.whisper_weight_type),
                            vad_parameters=vad_parameters,
                        )
                        for s in segments:
                            if s.avg_logprob < avg_logprob or s.no_speech_prob > no_speech_prob:
                                continue
                            text += s.text
                        confidences.append({"confidence": info.language_probability, "text": text, "language": language})
                        if (len(languages) == 1) or (
                            transcription_lang[language][country][self.transcription_engine] == info.language
                        ):
                            break

        except UnknownValueError:
            pass
        except Exception:
            errorLogging()
        finally:
            pass

        result = max(confidences, key=lambda x: x["confidence"])
        result.update(self._result_metadata(inference_started_at))
        # 空文字の確定結果もsegment_id等のメタデータ付きで積む。
        # ここで捨てると呼び出し側がsegment_idを取得できず、対応するpartial表示のdismissが送れなくなる。
        self.updateTranscript(result)
        return True

    def _enqueue_audio_queue_item(self, item: Any) -> None:
        if not isinstance(item, AudioQueueItem):
            self.pending_audio_queue_items.append(item)
            return

        if item.is_final:
            self.pending_audio_queue_items = deque(
                queued
                for queued in self.pending_audio_queue_items
                if not isinstance(queued, AudioQueueItem)
                or queued.segment_id != item.segment_id
                or queued.is_final
            )
            self.pending_audio_queue_items.append(item)
            return

        if any(
            isinstance(queued, AudioQueueItem)
            and queued.segment_id == item.segment_id
            and queued.is_final
            for queued in self.pending_audio_queue_items
        ):
            return

        self.pending_audio_queue_items = deque(
            queued
            for queued in self.pending_audio_queue_items
            if not (
                isinstance(queued, AudioQueueItem)
                and queued.segment_id == item.segment_id
                and not queued.is_final
            )
        )
        self.pending_audio_queue_items.append(item)

    def _update_from_queue_item(self, item: Any) -> None:
        if isinstance(item, AudioQueueItem):
            source_info = self.audio_sources
            source_info["new_phrase"] = source_info["segment_id"] != item.segment_id
            source_info["segment_id"] = item.segment_id
            source_info["last_sample"] = item.audio
            source_info["last_spoken"] = item.recorded_at
            source_info["is_final"] = item.is_final
            source_info["speech_ended_at"] = item.speech_ended_at
            return

        audio, time_spoken = item
        self.updateLastSampleAndPhraseStatus(audio, time_spoken)
        self.audio_sources["is_final"] = True
        self.audio_sources["speech_ended_at"] = time_spoken

    def _result_metadata(self, inference_started_at: float) -> Dict[str, Any]:
        source_info = self.audio_sources
        inference_ms = (time.perf_counter() - inference_started_at) * 1000
        speech_ended_at = source_info["speech_ended_at"]
        end_to_result_ms = None
        if speech_ended_at is not None:
            end_to_result_ms = max(0.0, (datetime.now() - speech_ended_at).total_seconds() * 1000)
        return {
            "is_final": source_info["is_final"],
            "segment_id": source_info["segment_id"],
            "inference_ms": inference_ms,
            "end_to_result_ms": end_to_result_ms,
            "audio_duration_ms": len(source_info["last_sample"]) / 2 / 16000 * 1000,
        }

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
        self.pending_audio_queue_items.clear()
        self.audio_sources["last_sample"] = bytes()
        self.audio_sources["new_phrase"] = True