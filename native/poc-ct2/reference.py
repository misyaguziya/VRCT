"""PoC reference: the current Python backend's Whisper and NLLB results, with VRCT's settings.

    python native/poc-ct2/reference.py <repo>/tmp/poc-ct2   ->  <dir>/python.json

Whisper: faster-whisper, base, cpu int8, cpu_threads=4, beam 5, temperature 0, without timestamps,
language detection (force_language off). Segments keep avg_logprob / no_speech_prob so the Rust
side can be compared before VRCT's filter (avg_logprob < -0.8 or no_speech_prob > 0.6 are dropped).
Translation: ctranslate2.Translator + transformers.AutoTokenizer, as translation_translator.py does.
"""

import json
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = ROOT / "src-python" / "weights"
SENTENCES = [
    ("jpn_Jpan", "eng_Latn", "こんにちは。今日はとてもいい天気ですね。"),
    ("jpn_Jpan", "eng_Latn", "明日の会議は午後三時から始まります。資料を準備しておいてください。"),
    ("eng_Latn", "jpn_Jpan", "Hello, how are you doing today? I am testing the speech recognition."),
    ("eng_Latn", "kor_Hang", "Thank you for the translation."),
]


def read_wav(path):
    with wave.open(str(path)) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0


def whisper(out_dir):
    from faster_whisper import WhisperModel

    model = WhisperModel(str(WEIGHTS / "whisper" / "base"), device="cpu", compute_type="int8", cpu_threads=4,
                         num_workers=1, local_files_only=True)
    from faster_whisper.tokenizer import Tokenizer
    from faster_whisper.transcribe import get_suppressed_tokens

    tokenizer = Tokenizer(model.hf_tokenizer, True, task="transcribe", language="en")
    (out_dir / "suppress_tokens.json").write_text(json.dumps(list(get_suppressed_tokens(tokenizer, [-1]))))
    results = {}
    for wav in sorted(out_dir.glob("*.wav")):
        # the log-mel features faster-whisper feeds the encoder (first 30 s window), for a numeric check
        features = model.feature_extractor(read_wav(wav), chunk_length=30)
        content = features.shape[-1] - 1
        window = np.zeros((features.shape[0], 3000), np.float32)
        window[:, :min(content, 3000)] = features[:, :min(content, 3000)]
        window.astype("<f4").tofile(out_dir / f"{wav.stem}.mel.f32")
        segments, info = model.transcribe(read_wav(wav), beam_size=5, temperature=0.0, log_prob_threshold=-0.8,
                                          no_speech_threshold=0.6, language=None, word_timestamps=False,
                                          without_timestamps=True, task="transcribe", no_repeat_ngram_size=0)
        segments = list(segments)
        results[wav.stem] = {
            "language": info.language, "language_probability": round(info.language_probability, 6),
            "segments": [{"text": s.text, "tokens": s.tokens, "avg_logprob": round(s.avg_logprob, 6),
                          "no_speech_prob": round(s.no_speech_prob, 6)} for s in segments],
            "text": "".join(s.text for s in segments if not (s.avg_logprob < -0.8 or s.no_speech_prob > 0.6)),
        }
    return results


def translation():
    import ctranslate2
    import transformers

    directory = WEIGHTS / "ctranslate2" / "nllb-200-distilled-600M-ct2-int8"
    translator = ctranslate2.Translator(str(directory), device="cpu", compute_type="int8", inter_threads=1,
                                        intra_threads=4)
    tokenizer = transformers.AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M",
                                                           cache_dir=str(directory / "tokenizer"))
    results = []
    for source_language, target_language, text in SENTENCES:
        tokenizer.src_lang = source_language
        source = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))
        hypothesis = translator.translate_batch([source], target_prefix=[[target_language]])[0].hypotheses[0]
        results.append({"source_language": source_language, "target_language": target_language, "text": text,
                        "source_tokens": source, "target_tokens": hypothesis,
                        "translation": tokenizer.decode(tokenizer.convert_tokens_to_ids(hypothesis[1:]))})
    return results


if __name__ == "__main__":
    out_dir = Path(sys.argv[1])
    report = {"whisper": whisper(out_dir), "nllb": translation()}
    (out_dir / "python.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, r in report["whisper"].items():
        print(name, r["language"], round(r["language_probability"], 3), repr(r["text"]))
    for r in report["nllb"]:
        print(r["source_language"], "->", r["target_language"], repr(r["translation"]))
