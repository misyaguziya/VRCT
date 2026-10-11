"""ローカル Whisper (faster-whisper) の基準データを、今の Python 版のコードで書き出す。

    python native/reference/export_whisper.py <weights の親> <weight_type> [cpu|cuda] [compute_type]
      -> native/testdata/whisper/<weight_type>-<device>.json

getWhisperModel で読み込み、LocalWhisperProvider.transcribe をそのまま呼ぶ (音声は 16 kHz / 16 bit
で渡す)。各ケースの音声は testdata/whisper/audio/ の wav を files の順につないだもの。無音・雑音・
純音・極端に短い音声もここで作って wav に書く。メル特徴量は 80 / 128 メルの SHA-256 も記録する。
"""

import hashlib
import json
import os
import sys
import wave
from pathlib import Path

import numpy as np

os.environ.setdefault("HF_HUB_OFFLINE", "1")
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))

from faster_whisper.feature_extractor import FeatureExtractor  # noqa: E402
from models.transcription.transcription_providers import LocalWhisperProvider  # noqa: E402
from models.transcription.transcription_whisper import getWhisperModel  # noqa: E402
from utils import getBestComputeType  # noqa: E402

AUDIO = ROOT / "native" / "testdata" / "whisper" / "audio"
LANGUAGES = {"ja": ("Japanese", "Japan"), "en": ("English", "United States")}


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2), path
        return np.frombuffer(w.readframes(w.getnframes()), np.int16)


def write_wav(path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(samples.astype("<i2").tobytes())


def make_synthetic():
    rng = np.random.RandomState(20261011)
    t = np.arange(32000) / 16000
    synthetic = {
        "silence": np.zeros(32000, np.int16),
        "noise": np.clip(rng.normal(0, 1500, 32000), -32768, 32767).astype(np.int16),
        "tone": (np.sin(2 * np.pi * 440 * t) * 8000).astype(np.int16),
        "short": read_wav(AUDIO / "ja00.wav")[4000:4800],
    }
    for name, samples in synthetic.items():
        write_wav(AUDIO / f"{name}.wav", samples)


class Pcm:
    """PcmAudio の代わり: get_raw_data(convert_rate=16000, convert_width=2) だけ使われる。"""

    def __init__(self, samples):
        self.samples = samples

    def get_raw_data(self, convert_rate=None, convert_width=None):
        assert (convert_rate, convert_width) == (16000, 2)
        return self.samples.astype("<i2").tobytes()


def sha256_f32(a):
    return hashlib.sha256(np.ascontiguousarray(a, dtype="<f4").tobytes()).hexdigest()


def main():
    weights_root, weight_type = sys.argv[1], sys.argv[2]
    device = sys.argv[3] if len(sys.argv) > 3 else "cpu"
    compute_type = sys.argv[4] if len(sys.argv) > 4 else getBestComputeType(device, 0)
    make_synthetic()
    model = getWhisperModel(weights_root, weight_type, device=device, compute_type=compute_type)
    provider = LocalWhisperProvider(model)

    clips = sorted(p.stem for p in AUDIO.glob("*.wav") if p.stem[:2] in LANGUAGES)
    cases = []
    for clip in clips:
        for force in (False, True):
            cases.append({"files": [clip], "language": clip[:2], "force_language": force})
    for lang in LANGUAGES:
        long = [c for c in clips if c.startswith(lang)]
        for force in (False, True):
            cases.append({"files": long, "language": lang, "force_language": force})
        cases.append({"files": long, "language": lang, "force_language": False, "no_repeat_ngram_size": 2})
    for name in ("silence", "noise", "tone", "short"):
        cases.append({"files": [name], "language": "ja", "force_language": False})

    for case in cases:
        samples = np.concatenate([read_wav(AUDIO / f"{f}.wav") for f in case["files"]])
        language, country = LANGUAGES[case["language"]]
        avg_logprob, no_speech_prob = -0.8, 0.6  # config.py の既定値
        case.update(avg_logprob=avg_logprob, no_speech_prob=no_speech_prob)
        case.setdefault("no_repeat_ngram_size", 0)
        # LocalWhisperProvider.transcribe の中身を分けて記録 (照合の段階を分けるため)
        raw = samples.astype(np.float32)
        raw /= 32768.0
        segments, info = model.transcribe(
            raw, beam_size=5, temperature=0.0, log_prob_threshold=avg_logprob, no_speech_threshold=no_speech_prob,
            language=case["language"] if case["force_language"] else None, word_timestamps=False,
            without_timestamps=True, task="transcribe", no_repeat_ngram_size=case["no_repeat_ngram_size"])
        case["segments"] = [{"id": s.id, "seek": s.seek, "start": s.start, "end": s.end, "text": s.text,
                             "tokens": list(s.tokens), "avg_logprob": s.avg_logprob,
                             "no_speech_prob": s.no_speech_prob} for s in segments]
        case["info"] = {"language": info.language, "language_probability": info.language_probability,
                        "duration": info.duration}
        text, probability, definitive = provider.transcribe(
            Pcm(samples), language, country, avg_logprob=avg_logprob, no_speech_prob=no_speech_prob,
            no_repeat_ngram_size=case["no_repeat_ngram_size"], force_language=case["force_language"])
        case["provider"] = {"text": text, "language_probability": probability, "is_definitive": definitive}
        print(case["files"][0], len(case["files"]), case["force_language"], repr(text)[:60])

    features = {}
    for clip in sorted(p.stem for p in AUDIO.glob("*.wav")):
        raw = read_wav(AUDIO / f"{clip}.wav").astype(np.float32)
        raw /= 32768.0
        features[clip] = {str(n): sha256_f32(FeatureExtractor(feature_size=n)(raw)) for n in (80, 128)}

    from faster_whisper.transcribe import get_suppressed_tokens
    from faster_whisper.tokenizer import Tokenizer
    suppress = get_suppressed_tokens(Tokenizer(model.hf_tokenizer, model.model.is_multilingual, task="transcribe",
                                               language="ja"), [-1])

    out = ROOT / "native" / "testdata" / "whisper" / f"{weight_type}-{device}.json"
    report = {"weight_type": weight_type, "device": device, "compute_type": compute_type,
              "suppress_tokens": list(suppress), "features_sha256": features, "cases": cases}
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}: {len(cases)} cases")


if __name__ == "__main__":
    main()
