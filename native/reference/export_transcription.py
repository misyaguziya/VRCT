"""音声認識の API (Google / OpenAI 互換 / Deepgram) が送る HTTP 要求を、今の Python 版のコードで記録する。

    PYTHONPATH=tmp/native-site python native/reference/export_transcription.py
      -> native/testdata/transcription/transcription.json
      -> native/data/transcription_languages.json (transcription_lang をそのまま。Rust 版が読む)

GoogleSpeechClient.recognize / OpenAICompatibleTranscriptionProvider.transcribe / DeepgramProvider.transcribe、
モデル一覧と認証の確認、resolveDeepgramLanguageCode を呼ぶ。音声は testdata/whisper/audio の wav。FLAC の
作り方 (vrct_audio) と 16 kHz への変換は P3 で照合するので、Rust 側は記録された本文 (FLAC / WAV) をそのまま使う。
"""

import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).parent))

from http_capture import capture  # noqa: E402
from models.transcription import google_speech  # noqa: E402
from models.transcription.pcm_audio import PcmAudio  # noqa: E402
from models.transcription.transcription_deepgram import (  # noqa: E402
    checkDeepgramApiKey, getAvailableDeepgramModelsDetailed, resolveDeepgramLanguageCode)
from models.transcription.transcription_languages import transcription_lang  # noqa: E402
from models.transcription.transcription_openai_compatible import (  # noqa: E402
    TRANSCRIPTION_MODEL_KEYWORDS, checkTranscriptionApiKey, getAvailableTranscriptionModels)
from models.transcription.transcription_providers import (  # noqa: E402
    DeepgramProvider, OpenAICompatibleTranscriptionProvider, TranscriptionApiError)

AUDIO = ROOT / "native" / "testdata" / "whisper" / "audio"
GOOGLE_REPLY = ('{"result":[]}\n'
                '{"result":[{"alternative":[{"transcript":"こんにちは","confidence":0.75},{"transcript":"今日は"}],'
                '"final":true}],"result_index":0}\n'
                '{"result":[{"alternative":[{"transcript":"いい天気"}],"final":true}]}\n')
WHISPER_REPLY = {"task": "transcribe", "language": "ja", "duration": 2.5, "text": " こんにちは。いい天気",
                 "segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": " こんにちは。", "avg_logprob": -0.25,
                               "no_speech_prob": 0.01, "temperature": 0.0, "compression_ratio": 1.0, "tokens": [1],
                               "seek": 0},
                              {"id": 1, "start": 1.0, "end": 2.0, "text": " ノイズ", "avg_logprob": -1.5,
                               "no_speech_prob": 0.1, "temperature": 0.0, "compression_ratio": 1.0, "tokens": [2],
                               "seek": 0},
                              {"id": 2, "start": 2.0, "end": 2.5, "text": "いい天気", "avg_logprob": -0.5,
                               "no_speech_prob": 0.2, "temperature": 0.0, "compression_ratio": 1.0, "tokens": [3],
                               "seek": 0}]}
MODELS = [{"id": "whisper-large-v3"}, {"id": "Whisper-Large-V3-Turbo"}, {"id": "gpt-4o-transcribe"},
          {"id": "gpt-4o"}, {"id": "distil-whisper-large-v3-en"}, {"id": "llama-3.3-70b"}]
DEEPGRAM_MODELS = {"stt": [
    {"name": "nova-3", "batch": True, "streaming": True, "languages": ["en", "en-US", "ja", "multi"]},
    {"name": "nova-2", "batch": True, "languages": ["en", "en-AU", "en-GB", "ja", "zh-CN"]},
    {"name": "nova-3", "batch": True, "languages": ["dup"]},
    {"name": "live-only", "batch": False, "languages": ["en"]},
    {"name": "", "batch": True}, {"batch": True},
    {"name": "base", "batch": True},
], "tts": [{"name": "aura"}]}
DEEPGRAM_REPLY = {"metadata": {}, "results": {"channels": [{"alternatives": [
    {"transcript": "こんにちは", "confidence": 0.91, "words": []}]}]}}


def responder(entry):
    url, headers = entry["url"], entry["headers"]
    auth = headers.get("authorization", "")
    if "invalid" in auth:
        return 401, {}, {"error": {"message": "invalid key"}}
    if "limited" in auth:
        return 429, {"retry-after": "0.01"}, {"error": {"message": "rate limited"}}
    if "broken" in auth:
        return 500, {}, {"error": "server"}
    if "speech-api/v2/recognize" in url:
        if "lang=xx-XX" in url:
            return 500, {}, "error"
        if "lang=zz-ZZ" in url:
            return 200, {"content-type": "text/plain"}, '{"result":[{"alternative":[{"transcript":1}]}]}'
        return 200, {"content-type": "text/plain"}, GOOGLE_REPLY
    if url.endswith("/audio/transcriptions"):
        if "no-segments" in auth:
            return 200, {}, {"text": " セグメントなし", "language": "japanese"}
        return 200, {}, WHISPER_REPLY
    if url.endswith("/models") and "deepgram" in url:
        return 200, {}, DEEPGRAM_MODELS
    if url.endswith("/models"):
        return 200, {}, {"object": "list", "data": [{"object": "model", "created": 0, "owned_by": "x", **m}
                                                     for m in MODELS]}
    if "api.deepgram.com/v1/listen" in url:
        if "empty" in auth:
            return 200, {}, {"results": {"channels": [{"alternatives": [{"transcript": ""}]}]}}
        return 200, {}, DEEPGRAM_REPLY
    return 404, {}, {"error": "not found"}


def pcm(name, rate=16000):
    with wave.open(str(AUDIO / f"{name}.wav"), "rb") as w:
        return PcmAudio(frame_data=w.readframes(w.getnframes()), sample_rate=rate, sample_width=2)


def main():
    steps = []

    def step(kind, label, call, **args):
        with capture(responder) as records:
            try:
                result = call()
            except TranscriptionApiError as e:
                result = {"error": e.error_code.value}
            except Exception as e:
                result = {"error": type(e).__name__}
        steps.append({"kind": kind, "label": label, "args": args, "result": result, "requests": records})
        print(kind, label, repr(result)[:70], len(records))

    google = google_speech.GoogleSpeechClient()
    audio = pcm("ja00")
    for lang in ("ja-JP", "en-US", "xx-XX", "zz-ZZ"):
        step("google", lang, lambda: list(google.recognize(audio, lang)), language=lang)
    step("google", "22050 Hz", lambda: list(google.recognize(pcm("en00", 22050), "en-US")), language="en-US")

    engines = [("Groq_Whisper", "https://api.groq.com/openai/v1", "whisper-large-v3"),
               ("OpenAI_Whisper", "https://api.openai.com/v1", "gpt-4o-transcribe"),
               ("Custom_Whisper", "http://192.168.0.10:8000/v1/", "my-model")]
    for engine, base, model in engines:
        for key, force in (("key", True), ("key", False), ("no-segments", False), ("invalid", False),
                           ("limited", False)):
            provider = OpenAICompatibleTranscriptionProvider(api_key=key, base_url=base, model=model, engine_name=engine)
            step("whisper_api", f"{engine} {key} force={force}",
                 lambda: list(provider.transcribe(audio, "Japanese", "Japan", avg_logprob=-0.8, no_speech_prob=0.6,
                                                  no_repeat_ngram_size=0, force_language=force)),
                 engine=engine, base_url=base, model=model, key=key, force_language=force)
        step("whisper_api_check", engine, lambda: checkTranscriptionApiKey("key", base), base_url=base, key="key")
        step("whisper_api_check", f"{engine} invalid", lambda: checkTranscriptionApiKey("invalid", base),
             base_url=base, key="invalid")
        keywords = None if engine == "Custom_Whisper" else TRANSCRIPTION_MODEL_KEYWORDS
        step("whisper_api_models", engine, lambda: getAvailableTranscriptionModels("key", base, keywords),
             base_url=base, key="key", keywords=keywords)

    for key, model, langs, force, language, country in [
            ("key", "nova-2", ["en", "en-AU", "ja"], True, "Japanese", "Japan"),
            ("key", "nova-2", ["en", "en-AU", "ja"], True, "English", "Australia"),
            ("key", "nova-3", ["en", "multi"], True, "English", "United States"),
            ("key", "nova-2", ["en"], False, "Japanese", "Japan"),
            ("empty", "nova-2", [], False, "Japanese", "Japan"),
            ("invalid", "nova-2", [], False, "Japanese", "Japan"),
            ("broken", "nova-2", [], False, "Japanese", "Japan")]:
        provider = DeepgramProvider(api_key=key, model=model, model_languages=langs)
        step("deepgram", f"{key} {model} {language}/{country} force={force}",
             lambda: list(provider.transcribe(audio, language, country, avg_logprob=-0.8, no_speech_prob=0.6,
                                              no_repeat_ngram_size=0, force_language=force)),
             key=key, model=model, languages=langs, force_language=force, language=language, country=country)
    step("deepgram_check", "key", lambda: checkDeepgramApiKey("key"), key="key")
    step("deepgram_check", "invalid", lambda: checkDeepgramApiKey("invalid"), key="invalid")
    step("deepgram_models", "key", lambda: getAvailableDeepgramModelsDetailed("key"), key="key")
    step("deepgram_models", "invalid", lambda: getAvailableDeepgramModelsDetailed("invalid"), key="invalid")

    resolve = []
    model_language_sets = [["en", "en-AU", "en-GB", "en-US", "ja", "zh-CN", "zh", "ko", "de", "pt-BR"],
                           ["EN", "Ja"], ["multi", "en"], [], ["", "fr"], ["cmn-Hans-CN", "iw"]]
    for language, countries in transcription_lang.items():
        for country in countries:
            for languages in model_language_sets:
                resolve.append({"language": language, "country": country, "model_languages": languages,
                                "result": resolveDeepgramLanguageCode(language, country, languages)})
    resolve.append({"language": "Klingon", "country": "Qo'noS", "model_languages": ["en"],
                    "result": resolveDeepgramLanguageCode("Klingon", "Qo'noS", ["en"])})

    out = ROOT / "native" / "testdata" / "transcription" / "transcription.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"steps": steps, "resolve_deepgram": resolve}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    table = ROOT / "native" / "data" / "transcription_languages.json"
    table.write_text(json.dumps(transcription_lang, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out, len(steps), "steps,", len(resolve), "resolve cases;", table)


if __name__ == "__main__":
    main()
