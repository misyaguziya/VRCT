import time
from io import BytesIO
from threading import Event
import wave
from speech_recognition import Recognizer, AudioData, AudioFile
from datetime import timedelta
from pyaudiowpatch import get_sample_size, paInt16
from .transcription_languages import transcription_lang
from .transcription_whisper import getWhisperModel, checkWhisperWeight

import torch
import numpy as np

PHRASE_TIMEOUT = 3
MAX_PHRASES = 10

class AudioTranscriber:
    def __init__(self, speaker, source, phrase_timeout, max_phrases, transcription_engine, root=None, whisper_weight_type=None):
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
            self.whisper_model = getWhisperModel(root, whisper_weight_type)
            self.transcription_engine = "Whisper"

    def transcribeAudioQueue(self, audio_queue, language, country):
        if audio_queue.empty():
            time.sleep(0.1)
            return False
        audio, time_spoken = audio_queue.get()
        self.updateLastSampleAndPhraseStatus(audio, time_spoken)

        text = ''
        try:
            audio_data = self.audio_sources["process_data_func"]()
            match self.transcription_engine:
                case "Google":
                    text = self.audio_recognizer.recognize_google(audio_data, language=transcription_lang[language][country][self.transcription_engine])
                case "Whisper":
                    audio_data = np.frombuffer(audio_data.get_raw_data(convert_rate=16000, convert_width=2), np.int16).flatten().astype(np.float32) / 32768.0
                    if isinstance(audio_data, torch.Tensor):
                        audio_data = audio_data.detach().numpy()
                    segments, _ = self.whisper_model.transcribe(
                        audio_data,
                        beam_size=5,
                        temperature=0.0,
                        log_prob_threshold=-0.8,
                        no_speech_threshold=0.6,
                        language=transcription_lang[language][country][self.transcription_engine],
                        word_timestamps=False,
                        without_timestamps=True,
                        task="transcribe",
                        vad_filter=False,
                        )
                    for s in segments:
                        if s.avg_logprob < -0.8 or s.no_speech_prob > 0.6:
                            continue
                        text += s.text

        except Exception:
            pass
        finally:
            pass

        if text != '':
            self.updateTranscript(text)
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
        with AudioFile(temp_file) as source:
            audio = self.audio_recognizer.record(source)
        return audio

    def updateTranscript(self, text):
        source_info = self.audio_sources
        transcript = self.transcript_data

        if source_info["new_phrase"] or len(transcript) == 0:
            if len(transcript) > self.max_phrases:
                transcript.pop(-1)
            transcript.insert(0, text)
        else:
            transcript[0] = text

    def getTranscript(self):
        if len(self.transcript_data) > 0:
            text = self.transcript_data.pop(-1)
        else:
            text = ""
        return text

    def clearTranscriptData(self):
        self.transcript_data.clear()
        self.audio_sources["last_sample"] = bytes()
        self.audio_sources["new_phrase"] = True