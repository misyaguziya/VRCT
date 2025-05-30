"""Handles audio transcription using Google Speech Recognition or local Whisper models."""
import time
from datetime import datetime, timedelta
from io import BytesIO
from queue import Queue
from threading import Event
from typing import Any, Callable, Dict, List, Optional, Tuple # Added necessary types
import wave

import numpy as np
import torch # Assuming torch is used if whisper is used with GPU
from pydub import AudioSegment # type: ignore # No stubs for pydub by default
from speech_recognition import (AudioData, AudioFile, AudioSource, # type: ignore
                                Recognizer, UnknownValueError) # type: ignore

from faster_whisper import WhisperModel, TranscriptionInfo # type: ignore # If stubs are not available

from utils import errorLogging # Assuming this is from the parent directory
from .transcription_languages import \
    transcription_lang as transcription_lang_data # Alias to avoid conflict
from .transcription_whisper import checkWhisperWeight, getWhisperModel

# Suppress RuntimeWarning if it's common and understood, e.g., from underlying libraries
import warnings
warnings.simplefilter('ignore', RuntimeWarning) # Consider if this is still needed or if issues can be fixed

# Constants (consider moving to a config or making them class attributes if they vary per instance)
PHRASE_TIMEOUT: float = 3.0 # Default phrase timeout in seconds
MAX_PHRASES: int = 10     # Default max phrases to keep in transcript

class AudioTranscriber:
    """
    Manages audio transcription by processing audio data from a queue,
    using either Google Speech Recognition API or a local Whisper model.
    """
    speaker: bool  # True if transcribing speaker audio, False for microphone
    phrase_timeout: float
    max_phrases: int
    transcript_data: List[Dict[str, Any]] # Stores {"confidence": float, "text": str, "language": Optional[str]}
    transcript_changed_event: Event # Event to signal changes in transcript_data
    audio_recognizer: Recognizer # SpeechRecognition Recognizer instance
    transcription_engine: str    # "Google" or "Whisper"
    whisper_model: Optional[WhisperModel] # Loaded Whisper model if used
    
    # Stores audio source information and intermediate data for processing
    audio_sources: Dict[str, Any] 
    # Expected keys: "sample_rate", "sample_width", "channels", 
    # "last_sample" (bytes), "last_spoken" (Optional[datetime]), 
    # "new_phrase" (bool), "process_data_func" (Callable)

    def __init__(self, 
                 speaker: bool, 
                 source: AudioSource, 
                 phrase_timeout: float, 
                 max_phrases: int, 
                 transcription_engine: str, 
                 root: Optional[str] = None, 
                 whisper_weight_type: Optional[str] = None, 
                 device: str = "cpu", 
                 device_index: int = 0) -> None:
        """
        Initializes the AudioTranscriber.

        Args:
            speaker: True if this instance transcribes speaker audio, False for microphone.
            source: The AudioSource from speech_recognition (e.g., Microphone).
            phrase_timeout: Seconds of silence after which a phrase is considered complete.
            max_phrases: Maximum number of phrases to store in the transcript history.
            transcription_engine: The engine to use ("Google" or "Whisper").
            root: Root path for Whisper model weights (if using Whisper).
            whisper_weight_type: Specific Whisper model size/type (e.g., "base", "small").
            device: Compute device for Whisper ("cpu", "cuda").
            device_index: Index of the compute device for Whisper.
        """
        self.speaker = speaker
        self.phrase_timeout = phrase_timeout
        self.max_phrases = max_phrases
        self.transcript_data = []
        self.transcript_changed_event = Event()
        self.audio_recognizer = Recognizer()
        self.transcription_engine = "Google" # Default to Google
        self.whisper_model = None
        
        self.audio_sources = {
            "sample_rate": source.SAMPLE_RATE,
            "sample_width": source.SAMPLE_WIDTH,
            "channels": source.channels,
            "last_sample": bytes(),
            "last_spoken": None, # Optional[datetime]
            "new_phrase": True,
            # Corrected process_data_func assignment
            "process_data_func": self.processSpeakerData if speaker else self.processMicData
        }

        if transcription_engine == "Whisper":
            if root is None or whisper_weight_type is None:
                errorLogging("Whisper engine selected but root path or weight type not provided.")
            elif checkWhisperWeight(root, whisper_weight_type):
                try:
                    self.whisper_model = getWhisperModel(root, whisper_weight_type, device=device, device_index=device_index)
                    self.transcription_engine = "Whisper"
                    print(f"Whisper model {whisper_weight_type} loaded on {device}:{device_index}.")
                except Exception as e:
                    errorLogging(f"Failed to load Whisper model {whisper_weight_type}: {e}")
                    # Fallback to Google if Whisper fails to load? Or raise error?
                    # Current behavior: stays Google if Whisper fails.
            else:
                errorLogging(f"Whisper weight {whisper_weight_type} not found at {root}. Falling back to Google.")
        
        if self.transcription_engine == "Google":
            print("Using Google Speech Recognition.")
        
    def transcribeAudioQueue(self, 
                             audio_queue: Queue[Tuple[bytes, datetime]], 
                             languages: List[str], 
                             countries: List[str], 
                             avg_logprob: float = -0.8, 
                             no_speech_prob: float = 0.6) -> bool:
        """
        Processes audio from the queue, transcribes it, and updates the transcript.

        Args:
            audio_queue: Queue containing (audio_bytes, timestamp) tuples.
            languages: List of languages to attempt transcription in.
            countries: List of corresponding country codes for Google API.
            avg_logprob: For Whisper, minimum average log probability for a segment.
            no_speech_prob: For Whisper, maximum no-speech probability for a segment.

        Returns:
            True if audio was processed, False if the queue was empty.
        """
        if audio_queue.empty():
            time.sleep(0.01) # Avoid busy waiting if queue is empty
            return False
        
        audio_chunk, time_spoken = audio_queue.get()
        self.updateLastSampleAndPhraseStatus(audio_chunk, time_spoken)

        # Initialize with a low-confidence default to ensure `max` works even if all transcriptions fail
        confidences: List[Dict[str, Any]] = [{"confidence": -1.0, "text": "", "language": None}]
        
        try:
            # process_data_func returns AudioData
            processed_audio_data: Optional[AudioData] = self.audio_sources["process_data_func"]()
            if not processed_audio_data:
                return True # No data to process after combining samples

            if self.transcription_engine == "Google":
                for lang_name, country_name in zip(languages, countries):
                    try:
                        # Ensure transcription_lang_data is accessed safely
                        google_lang_code = transcription_lang_data.get(lang_name, {}).get(country_name, {}).get("Google")
                        if google_lang_code:
                            text, confidence = self.audio_recognizer.recognize_google( # type: ignore
                                processed_audio_data,
                                language=google_lang_code,
                                with_confidence=True
                            )
                            confidences.append({"confidence": float(confidence), "text": str(text), "language": lang_name})
                    except UnknownValueError:
                        # This is expected if Google couldn't understand, try next language
                        pass 
                    except Exception as e_google:
                        errorLogging(f"Google API error for {lang_name}-{country_name}: {e_google}")
            
            elif self.transcription_engine == "Whisper" and self.whisper_model:
                audio_bytes = processed_audio_data.get_raw_data(convert_rate=16000, convert_width=2)
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                for lang_name, country_name in zip(languages, countries): 
                    whisper_lang_code = transcription_lang_data.get(lang_name, {}).get(country_name, {}).get("Whisper")
                    effective_whisper_lang_for_transcribe = whisper_lang_code if len(languages) == 1 and whisper_lang_code else None
                    
                    try:
                        segments, info = self.whisper_model.transcribe(
                            audio_np,
                            beam_size=5,
                            temperature=0.0,
                            log_prob_threshold=avg_logprob, # Use provided arg
                            no_speech_threshold=no_speech_prob, # Use provided arg
                            language=effective_whisper_lang_for_transcribe,
                            word_timestamps=False,
                            without_timestamps=True,
                            task="transcribe",
                            vad_filter=False, 
                        )
                        
                        full_text = "".join(s.text for s in segments if s.avg_logprob >= avg_logprob and s.no_speech_prob <= no_speech_prob).strip()
                        
                        detected_language_whisper = info.language 
                        
                        confidences.append({
                            "confidence": float(info.language_probability), 
                            "text": full_text, 
                            "language": lang_name 
                        })
                        
                        if info and (effective_whisper_lang_for_transcribe and detected_language_whisper == effective_whisper_lang_for_transcribe or \
                           (not effective_whisper_lang_for_transcribe and whisper_lang_code == detected_language_whisper)):
                             break 
                    except Exception as e_whisper:
                        errorLogging(f"Whisper transcription error for {lang_name}: {e_whisper}")
            else:
                errorLogging(f"Unknown or uninitialized transcription engine: {self.transcription_engine}")

        except UnknownValueError:
            pass 
        except Exception as e:
            errorLogging(f"Error during transcription processing: {e}")
        
        best_result = max(confidences, key=lambda x: x.get("confidence", -1.0))
        
        if best_result.get("text"): 
            self.updateTranscript(best_result)
        return True

    def updateLastSampleAndPhraseStatus(self, data: bytes, time_spoken: datetime) -> None:
        """Updates the last audio sample and determines if it's a new phrase."""
        source_info = self.audio_sources
        # Ensure "last_spoken" is a datetime object before comparison
        last_spoken_time: Optional[datetime] = source_info.get("last_spoken")
        if last_spoken_time and (time_spoken - last_spoken_time) > timedelta(seconds=self.phrase_timeout):
            source_info["last_sample"] = bytes() # Start new sample
            source_info["new_phrase"] = True
        else:
            source_info["new_phrase"] = False

        current_sample: bytes = source_info.get("last_sample", bytes())
        source_info["last_sample"] = current_sample + data
        source_info["last_spoken"] = time_spoken

    def processMicData(self) -> AudioData:
        """Processes microphone audio data directly into an AudioData object."""
        # Ensure keys exist and have correct types from self.audio_sources
        last_sample: bytes = self.audio_sources.get("last_sample", bytes())
        sample_rate: int = self.audio_sources.get("sample_rate", 16000) # Default if not found
        sample_width: int = self.audio_sources.get("sample_width", 2)   # Default if not found
        return AudioData(last_sample, sample_rate, sample_width)

    def processSpeakerData(self) -> AudioData:
        """
        Processes speaker audio data. This may involve converting multi-channel audio
        to mono and saving to a temporary WAV file for compatibility with AudioFile.
        """
        last_sample: bytes = self.audio_sources.get("last_sample", bytes())
        channels: int = self.audio_sources.get("channels", 1)
        sample_rate: int = self.audio_sources.get("sample_rate", 16000)
        # sample_width from pyaudiowpatch.paInt16 is 2 bytes
        sample_width: int = get_sample_size(paInt16) # type: ignore 

        temp_file = BytesIO()
        try:
            with wave.open(temp_file, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sample_width)
                wf.setframerate(sample_rate)
                wf.writeframes(last_sample)
            temp_file.seek(0)

            # Convert to mono if more than 2 channels (standard is 1 or 2 for AudioFile)
            # pydub might be more robust for various channel configurations if needed.
            if channels > 2: # Typically stereo (2) is fine, but >2 might need downmixing.
                audio_segment = AudioSegment.from_file(temp_file, format="wav")
                mono_audio_segment = audio_segment.set_channels(1)
                
                # Overwrite temp_file with mono audio
                temp_file.seek(0)
                temp_file.truncate(0) # Clear the stream before exporting new data
                mono_audio_segment.export(temp_file, format="wav")
                temp_file.seek(0)

            with AudioFile(temp_file) as source_file: # speech_recognition.AudioFile
                # record() reads the entire file content into an AudioData object
                audio_data_obj: AudioData = self.audio_recognizer.record(source_file) # type: ignore
            return audio_data_obj
        finally:
            temp_file.close() # Ensure BytesIO buffer is closed

    def updateTranscript(self, result: Dict[str, Any]) -> None:
        """
        Updates the transcript data with a new result.
        If it's a new phrase or the transcript is empty, appends to the start.
        Otherwise, updates the most recent (first) entry.
        Manages max_phrases limit.
        """
        source_info = self.audio_sources
        transcript_list = self.transcript_data # Works on the instance's list

        is_new_phrase: bool = source_info.get("new_phrase", True)

        if is_new_phrase or not transcript_list:
            if len(transcript_list) >= self.max_phrases:
                transcript_list.pop() # Remove the oldest item (from the end)
            transcript_list.insert(0, result) # Add new item at the beginning
        else:
            if transcript_list: # Should not be empty if new_phrase is False, but check for safety
                transcript_list[0] = result # Update the current phrase (first item)
        
        self.transcript_changed_event.set() # Signal that transcript has changed

    def getTranscript(self) -> Dict[str, Any]:
        """
        Retrieves and removes the oldest complete phrase from the transcript data.
        Returns a default empty result if no data is available.
        """
        if self.transcript_data: # Check if list is not empty
            # .pop() without an index removes and returns the last item (oldest phrase)
            result = self.transcript_data.pop() 
        else:
            result = {"confidence": 0.0, "text": "", "language": None} # Default structure
        return result

    def clearTranscriptData(self) -> None:
        """Clears all stored transcript data and resets audio source state."""
        self.transcript_data.clear()
        if self.audio_sources: # Check if audio_sources has been initialized
            self.audio_sources["last_sample"] = bytes()
            self.audio_sources["new_phrase"] = True
        self.transcript_changed_event.set() # Signal change (clearing)