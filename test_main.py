import time
import threading
import queue
import AudioTranscriber
import AudioRecorder
import audio_utils

mic_audio_queue = queue.Queue()

mic_device = audio_utils.get_default_input_device()
mic_audio_recorder = AudioRecorder.SelectedMicRecorder(mic_device)
mic_audio_recorder.record_into_queue(mic_audio_queue)

mic_transcriber = AudioTranscriber.AudioTranscriber(source=mic_audio_recorder.source, language="ja-JP")
mic_transcribe = threading.Thread(target=mic_transcriber.transcribe_audio_queue, args=(mic_audio_queue,))
mic_transcribe.daemon = True
mic_transcribe.start()

time.sleep(2)

spk_audio_queue = queue.Queue()
spk_device = audio_utils.get_default_output_device()
spk_audio_recorder = AudioRecorder.SelectedSpeakerRecorder(spk_device)
spk_audio_recorder.record_into_queue(spk_audio_queue)

spk_transcriber = AudioTranscriber.AudioTranscriber(source=mic_audio_recorder.source, language="ja-JP")
spk_transcribe = threading.Thread(target=spk_transcriber.transcribe_audio_queue, args=(spk_audio_queue,))
spk_transcribe.daemon = True
spk_transcribe.start()

while True:
    text = mic_transcriber.get_transcript()
    if len(text) > 0:
        print("mic:", text)
    # text = spk_transcriber.get_transcript()
    # if len(text) > 0:
    #     print("spk:", text)
    time.sleep(0.1)