"""Silero VAD と発話区間の区切り (audio_vad.VadRecognizerAdapter) を、今の Python 版で記録する。

    python native/reference/export_vad.py   ->  native/testdata/audio/vad.json

照合用の音声 (testdata/whisper/audio の 16 kHz mono) をつなげ、録音デバイスの形 (48 kHz ステレオ) に
audioop で直して 1024 フレームずつ流す。Rust 側も同じ手順で入力を作る。
"""

import audioop
import hashlib
import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))
AUDIO = ROOT / "native" / "testdata" / "whisper" / "audio"

STREAMS = {
    # pauses between clips, noise, a tone, and speech without pauses (to reach max_duration)
    "mixed": ["silence", "ja00", "silence", "en00", "noise", "ja05", "tone", "short", "silence", "en03"],
    "continuous": ["ja01", "ja02", "ja03", "ja04", "en01", "en02", "silence"],
}
CHUNK_FRAMES = 1024


def build(names):
    """16 kHz mono clips -> one 48 kHz stereo PCM16 stream"""
    mono = b""
    for name in names:
        with wave.open(str(AUDIO / f"{name}.wav"), "rb") as w:
            assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2
            mono += w.readframes(w.getnframes())
    up, _ = audioop.ratecv(mono, 2, 1, 16000, 48000, None)
    return audioop.tostereo(up, 2, 1, 1)


def main():
    from models.transcription import audio_vad
    runs = []
    for stream, names in STREAMS.items():
        data = build(names)
        for max_frames in (250, 219, 40, 8):
            probs = []
            silero = audio_vad.SileroFrameProbability()
            original = silero.__call__

            class Recording:
                def __call__(self, frame):
                    p = original(frame)
                    probs.append(p)
                    return p

                def reset(self):
                    silero.reset()

            segmenter = audio_vad.VadSegmenter(Recording(), max_speech_frames=max_frames)
            adapter = audio_vad.VadRecognizerAdapter(48000, 2, 2, segmenter)
            first_id = segmenter._segment_id
            segments = []

            def record(segment, chunk):
                segments.append({"chunk": chunk, "bytes": len(segment.audio), "reason": segment.reason,
                                 "id": segment.segment_id - first_id,
                                 "sha256": hashlib.sha256(segment.audio).hexdigest()})

            step = CHUNK_FRAMES * 4
            for i in range(0, len(data), step):
                for segment in adapter.process(data[i:i + step]):
                    record(segment, i // step)
            flushed = adapter.flush()
            if flushed is not None:
                record(flushed, -1)
            runs.append({"stream": stream, "clips": names, "max_speech_frames": max_frames, "probs": probs,
                         "segments": segments})
            print(stream, max_frames, len(probs), [(s["reason"], s["bytes"]) for s in segments])
    out = ROOT / "native" / "testdata" / "audio" / "vad.json"
    out.write_text(json.dumps({"chunk_frames": CHUNK_FRAMES, "runs": runs}), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
