import time
from io import BytesIO
from threading import Event
import wave
from speech_recognition import Recognizer, AudioData, AudioFile
from speech_recognition.exceptions import UnknownValueError
from datetime import timedelta
from pyaudiowpatch import get_sample_size, paInt16
from .transcription_languages import transcription_lang
from .transcription_whisper import getWhisperModel, checkWhisperWeight

import torch
import numpy as np
from pydub import AudioSegment
from utils import errorLogging

import warnings
warnings.simplefilter('ignore', RuntimeWarning)

PHRASE_TIMEOUT = 3
MAX_PHRASES = 10

class AudioTranscriber:
    def __init__(self, speaker, source, phrase_timeout, max_phrases, transcription_engine, root=None, whisper_weight_type=None, device="cpu", device_index=0):
        self.speaker = speaker
        self.phrase_timeout = phrase_timeout
        self.max_phrases = max_phrases
        self.transcript_data = []
        self.transcript_changed_event = Event()
        self.audio_recognizer = Recognizer()
        self.transcription_engine = "Google"
        self.whisper_model = None
        self.audio_sources = {
                "sample_rate": source.SAMPLE_RATE,
                "sample_width": source.SAMPLE_WIDTH,
                "channels": source.channels,
                "last_sample": bytes(),
                "last_spoken": None,
                "new_phrase": True,
                "process_data_func": self.processSpeakerData if speaker else self.processSpeakerData
        }

        if transcription_engine == "Whisper" and checkWhisperWeight(root, whisper_weight_type) is True:
            self.whisper_model = getWhisperModel(root, whisper_weight_type, device=device, device_index=device_index)
            self.transcription_engine = "Whisper"

    def transcribeAudioQueue(self, audio_queue, languages, countries, avg_logprob=-0.8, no_speech_prob=0.6):
        if audio_queue.empty():
            time.sleep(0.01)
            return False
        audio, time_spoken = audio_queue.get()
        self.updateLastSampleAndPhraseStatus(audio, time_spoken)

        confidences = [{"confidence": 0, "text": "", "language": None}]
        try:
            audio_data = self.audio_sources["process_data_func"]()
            match self.transcription_engine:
                case "Google":
                    for language, country in zip(languages, countries):
                        try:
                            text, confidence = self.audio_recognizer.recognize_google(
                                audio_data,
                                language=transcription_lang[language][country][self.transcription_engine],
                                with_confidence=True
                                )
                            confidences.append({"confidence": confidence, "text": text, "language": language})
                        except Exception:
                            pass
                case "Whisper":
                    audio_data = np.frombuffer(audio_data.get_raw_data(convert_rate=16000, convert_width=2), np.int16).flatten().astype(np.float32) / 32768.0
                    if isinstance(audio_data, torch.Tensor):
                        audio_data = audio_data.detach().numpy()

                    for language, country in zip(languages, countries):
                        text = ""
                        source_language = transcription_lang[language][country][self.transcription_engine] if len(languages) == 1 else None
                        segments, info = self.whisper_model.transcribe(
                            audio_data,
                            beam_size=5,
                            temperature=0.0,
                            log_prob_threshold=-0.8,
                            no_speech_threshold=0.6,
                            language=source_language,
                            word_timestamps=False,
                            without_timestamps=True,
                            task="transcribe",
                            vad_filter=False,
                            )
                        for s in segments:
                            if s.avg_logprob < avg_logprob or s.no_speech_prob > no_speech_prob:
                                continue
                            text += s.text
                        confidences.append({"confidence": info.language_probability, "text": text, "language": language})
                        if (len(languages) == 1) or (transcription_lang[language][country][self.transcription_engine] == info.language):
                            break

        except UnknownValueError:
            pass
        except Exception:
            errorLogging()
        finally:
            pass

        result = max(confidences, key=lambda x: x["confidence"])
        if result["text"] != "":
            self.updateTranscript(result)
        return True

    def updateLastSampleAndPhraseStatus(self, data, time_spoken):
        source_info = self.audio_sources
        if source_info["last_spoken"] and time_spoken - source_info["last_spoken"] > timedelta(seconds=self.phrase_timeout):
            source_info["last_sample"] = bytes()
            source_info["new_phrase"] = True
        else:
            source_info["new_phrase"] = False

        source_info["last_sample"] += data
        source_info["last_spoken"] = time_spoken

    def processMicData(self):
        audio_data = AudioData(self.audio_sources["last_sample"], self.audio_sources["sample_rate"], self.audio_sources["sample_width"])
        return audio_data

    def processSpeakerData(self):
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

    def updateTranscript(self, result):
        source_info = self.audio_sources
        transcript = self.transcript_data

        if source_info["new_phrase"] or len(transcript) == 0:
            if len(transcript) > self.max_phrases:
                transcript.pop(-1)
            transcript.insert(0, result)
        else:
            transcript[0] = result

    def getTranscript(self):
        if len(self.transcript_data) > 0:
            result = self.transcript_data.pop(-1)
        else:
            result = {"confidence": 0, "text": "", "language": None}
        return result

    def clearTranscriptData(self):
        self.transcript_data.clear()
        self.audio_sources["last_sample"] = bytes()
        self.audio_sources["new_phrase"] = True