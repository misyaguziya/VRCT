from io import BytesIO
from threading import Event
import wave
from speech_recognition import Recognizer, AudioData, AudioFile
from datetime import timedelta
from pyaudiowpatch import get_sample_size, paInt16
from .transcription_languages import transcription_lang

PHRASE_TIMEOUT = 3
MAX_PHRASES = 10

class AudioTranscriber:
    def __init__(self, speaker, source, phrase_timeout, max_phrases):
        self.speaker = speaker
        self.phrase_timeout = phrase_timeout
        self.max_phrases = max_phrases
        self.transcript_data = []
        self.transcript_changed_event = Event()
        self.audio_recognizer = Recognizer()
        self.audio_sources = {
                "sample_rate": source.SAMPLE_RATE,
                "sample_width": source.SAMPLE_WIDTH,
                "channels": source.channels,
                "last_sample": bytes(),
                "last_spoken": None,
                "new_phrase": True,
                "process_data_func": self.process_speaker_data if speaker else self.process_speaker_data
        }

    def transcribe_audio_queue(self, audio_queue, language):
        # while True:
        audio, time_spoken = audio_queue.get()
        self.update_last_sample_and_phrase_status(audio, time_spoken)

        text = ''
        try:
            # fd, path = tempfile.mkstemp(suffix=".wav")
            # os.close(fd)
            audio_data = self.audio_sources["process_data_func"]()
            text = self.audio_recognizer.recognize_google(audio_data, language=transcription_lang[language])
        except Exception as e:
            pass
        finally:
            pass
            # os.unlink(path)

        if text != '':
            self.update_transcript(text)

    def update_last_sample_and_phrase_status(self, data, time_spoken):
        source_info = self.audio_sources
        if source_info["last_spoken"] and time_spoken - source_info["last_spoken"] > timedelta(seconds=self.phrase_timeout):
            source_info["last_sample"] = bytes()
            source_info["new_phrase"] = True
        else:
            source_info["new_phrase"] = False

        source_info["last_sample"] += data
        source_info["last_spoken"] = time_spoken

    def process_mic_data(self):
        audio_data = AudioData(self.audio_sources["last_sample"], self.audio_sources["sample_rate"], self.audio_sources["sample_width"])
        return audio_data

    def process_speaker_data(self):
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

    def update_transcript(self, text):
        source_info = self.audio_sources
        transcript = self.transcript_data

        if source_info["new_phrase"] or len(transcript) == 0:
            if len(transcript) > self.max_phrases:
                transcript.pop(-1)
            transcript.insert(0, text)
        else:
            transcript[0] = text

    def get_transcript(self):
        if len(self.transcript_data) > 0:
            text = self.transcript_data.pop(-1)
        else:
            text = ""
        return text

    def clear_transcript_data(self):
        self.transcript_data.clear()
        self.audio_sources["last_sample"] = bytes()
        self.audio_sources["new_phrase"] = True