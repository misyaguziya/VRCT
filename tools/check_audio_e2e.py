"""End-to-end audio pipeline check without a physical device.

Plays synthetic speech (Windows SAPI) in real time through the production
chain MicSession/SpeakerSession -> recorder -> native listener/VAD -> queue ->
AudioTranscriber -> provider, replacing only the PyAudio capture source.
Whisper runs for real; Google and the OpenAI-compatible API run against a
local fake transport. No audio is saved except the cached SAPI clips, and
nothing is sent off the machine (an HTTP(S)_PROXY would still apply to the
local API client, so unset it).

Side effects: importing `model` constructs the real `config`, which creates or
rewrites `src-python/config.json` of the checkout being run and appends to its
process/error logs (the same as the unit tests). PyAudio enumerates devices
read-only at import; no device is opened.

    python tools/check_audio_e2e.py --output tmp/e2e.json [--compute cpu|cuda]
    python tools/check_audio_e2e.py --listener fork ...   # develop's fork listener (A/B)

Per utterance it records text, CER and end-of-speech -> text latency plus the
provider time; per case it records where audio was lost (record_timeout drop
vs short-phrase rejection). Not covered: physical hot-unplug, endpoint
switching, loopback devices that deliver no frames during silence, and buffer
overflow when the reader falls behind (the fake catches up instead).
"""

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import wave
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from unittest.mock import patch

import audioop

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src-python"), str(ROOT)]

TEXTS = [
    "今日はいい天気ですね。散歩に行きましょう。",
    "この音声認識のテストは正常に動作していますか。",
    "ブイアールチャットで友達と一緒に遊びたいです。",
]
# LEAD_S leaves room for the transcriber (Whisper load) that model.py creates
# after the listener has already started.
LEAD_S, GAP_S, CHUNK, RECORD_TIMEOUT = 4.0, 8.0, 1024, 3


def synthesize(text, cache_dir):
    """SAPI -> 16 kHz mono PCM16 bytes (cached)."""
    wav = Path(cache_dir) / f"sapi_{hashlib.sha1(text.encode()).hexdigest()[:12]}.wav"
    if not wav.exists():
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.SelectVoice('Microsoft Haruka Desktop');"
            "$f=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,'Sixteen','Mono');"
            f"$s.SetOutputToWaveFile('{wav}',$f);$s.Speak($env:E2E_TEXT);$s.Dispose()"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True,
                       env={**os.environ, "E2E_TEXT": text}, timeout=60)
    with wave.open(str(wav)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
        return w.readframes(w.getnframes())


def to_device(pcm16k, rate, channels):
    mono = audioop.ratecv(pcm16k, 2, 1, 16000, rate, None)[0] if rate != 16000 else pcm16k
    return audioop.tostereo(mono, 2, 1, 1) if channels == 2 else mono


def build_timeline(clips, rate, channels):
    """Returns (pcm, speech_ends, speech_starts) with low-level seeded noise as silence."""
    import numpy as np

    rng = np.random.default_rng(20261008)

    def noise(seconds):
        mono = rng.normal(0, 12, int(seconds * rate)).astype("<i2").tobytes()
        return audioop.tostereo(mono, 2, 1, 1) if channels == 2 else mono

    out, ends, starts, t = [noise(LEAD_S)], [], [], LEAD_S
    for clip in clips:
        data = to_device(clip, rate, channels)
        out.append(data)
        starts.append(t)
        t += len(data) / (2 * channels * rate)
        ends.append(t)
        out.append(noise(GAP_S))
        t += GAP_S
    return b"".join(out), ends, starts


class PacedSource:
    """Clock-driven fake of AudioCaptureSource and its PyAudio stream.

    Frames become available as the wall clock advances (so get_read_available
    is 0 right after a read, like a real device); read blocks until a chunk is
    available, and stop_stream unblocks it with OSError like PyAudio does.
    """

    SAMPLE_WIDTH = 2

    def __init__(self, timeline, rate, channels, **_):
        self.timeline, self.SAMPLE_RATE, self.channels, self.CHUNK = timeline, rate, channels, CHUNK
        self.stream = self.pyaudio_stream = None
        self.t0 = None
        self._consumed = 0
        self._stopped = threading.Event()
        self.stop_stream_calls = 0

    def __enter__(self):
        if self.stream is not None:
            raise RuntimeError("capture source is already open")
        self._stopped.clear()
        self.stream = self.pyaudio_stream = self
        self.t0, self._consumed = time.monotonic(), 0  # probe open and real open both restart
        return self

    def __exit__(self, *exc):
        self._stopped.set()
        self.stream = self.pyaudio_stream = None

    def is_stopped(self):
        return self._stopped.is_set()

    def stop_stream(self):
        self.stop_stream_calls += 1
        self._stopped.set()

    def close(self):
        self._stopped.set()

    def get_read_available(self):
        return max(0, int((time.monotonic() - self.t0) * self.SAMPLE_RATE) - self._consumed)

    def read(self, count, exception_on_overflow=False):
        assert count == CHUNK
        due = self.t0 + (self._consumed + CHUNK) / self.SAMPLE_RATE
        if self._stopped.wait(max(0.0, due - time.monotonic())):
            raise OSError("Stream is stopped")
        frame = 2 * self.channels
        start = self._consumed * frame
        data = self.timeline[start:start + CHUNK * frame]
        self._consumed += CHUNK
        return data + bytes(CHUNK * frame - len(data))


class CountingDetector:
    """Records where the native energy detector discards audio."""

    def __init__(self, detector, losses):
        self._detector, self._losses = detector, losses
        self.events = []  # (monotonic, action, bytes, seconds since phrase start)
        self._recording_since = None

    def before_read(self, now):
        was_recording = not self._detector.waiting
        action, audio = self._detector.before_read(now)
        since = None if self._recording_since is None else now - self._recording_since
        if action != "READ":
            self.events.append((now, action, len(audio) if audio else 0, since))
        if action == "RETRY" and was_recording:
            # A wall-clock record_timeout fires ~RECORD_TIMEOUT after the phrase
            # start; an earlier RETRY follows a rejected (too short) phrase.
            long_enough = since is not None and since >= RECORD_TIMEOUT - 2 * CHUNK / 16000
            self._losses.append((now, "record_timeout" if long_enough else "rejected_short"))
        if self._detector.waiting:
            self._recording_since = None
        return action, audio

    def push(self, pcm, now):
        energy = self._detector.push(pcm, now)
        if self._recording_since is None and not self._detector.waiting:
            self._recording_since = now
            self.events.append((now, "START", 0, None))
        return energy

    def __getattr__(self, name):
        return getattr(self._detector, name)


class TimedQueue(Queue):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.items = []

    def put(self, item, *a, **k):
        audio = item[0] if isinstance(item, tuple) else item
        self.items.append((time.monotonic(), len(audio) if isinstance(audio, (bytes, bytearray)) else None,
                           item[2] if isinstance(item, tuple) and len(item) > 2 else None))
        return super().put(item, *a, **k)


class FakeApiServer(ThreadingHTTPServer):
    """Local OpenAI-compatible /audio/transcriptions that validates the WAV upload."""

    def __init__(self):
        outer = self
        self.uploads = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                boundary = self.headers.get_content_type() == "multipart/form-data" and \
                    self.headers.get_param("boundary")
                try:
                    part = next(p for p in body.split(b"--" + boundary.encode()) if b"RIFF" in p)
                    data = part[part.index(b"\r\n\r\n") + 4:].removesuffix(b"\r\n")
                    with wave.open(io.BytesIO(data)) as w:
                        frames = w.getnframes()
                        valid = len(w.readframes(frames)) == frames * w.getnchannels() * w.getsampwidth()
                        outer.uploads.append([w.getframerate(), w.getnchannels(), frames, valid])
                except Exception as error:  # recorded as an invalid upload
                    outer.uploads.append(repr(error))
                payload = json.dumps({"text": "api ok", "language": "ja"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *a):
                pass

        super().__init__(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.serve_forever, daemon=True).start()

    def close(self):
        self.shutdown()
        self.server_close()


def fork_patches(transcription_recorder, losses):
    """Swap in the pinned SpeechRecognition fork listener (develop's behaviour)."""
    import inspect

    import speech_recognition as sr

    lines, first = inspect.getsourcelines(sr.Recognizer.listen_energy_and_audio)
    guard = next(i for i, line in enumerate(lines) if "time.time() - record_start_time > record_timeout" in line)
    record_timeout_line = first + guard + 1  # the raise inside the recording loop
    original_listen = sr.Recognizer.listen_energy_and_audio

    def counting_listen(self, *a, **k):
        try:
            return original_listen(self, *a, **k)
        except sr.WaitTimeoutError as error:
            if traceback.extract_tb(error.__traceback__)[-1].lineno == record_timeout_line:
                losses.append((time.monotonic(), "record_timeout"))
            raise

    source_cls = type("ForkPacedSource", (PacedSource, sr.AudioSource), {})
    locked = type("ForkLockedSource", (transcription_recorder._LockedAudioSource, sr.AudioSource), {})
    return source_cls, [
        patch.object(transcription_recorder, "create_listener", lambda on_error: sr.Recognizer()),
        patch.object(transcription_recorder, "_LockedAudioSource", locked),
        patch.object(sr.Recognizer, "listen_energy_and_audio", counting_listen),
    ]


def run_case(args, clips, kind, vad, engine):
    import model
    from models.transcription import audio_listener, google_speech, transcription_recorder
    from models.transcription import transcription_providers as providers
    from tools.whisper_eval.metrics import character_error_rate

    rate, channels = (48000, 2) if kind == "speaker" else (44100, 1)
    timeline, ends, starts = build_timeline(clips, rate, channels)
    lang = {"1": {"1": {"language": "Japanese", "country": "Japan", "enable": True}}}
    cfg = SimpleNamespace(
        SELECTED_TAB_NO="1", SELECTED_YOUR_LANGUAGES=lang, SELECTED_TARGET_LANGUAGES=lang,
        PATH_LOCAL=args.root, WHISPER_WEIGHT_TYPE=args.weight,
        SELECTED_TRANSCRIPTION_COMPUTE_DEVICE={"device": args.compute, "device_index": 0},
        SELECTED_TRANSCRIPTION_COMPUTE_TYPE="int8_float16" if args.compute == "cuda" else "int8",
        SELECTED_TRANSCRIPTION_ENGINE={"whisper": "Whisper", "google": "Google",
                                       "api": "Custom_Whisper"}[engine],
        TRANSCRIPTION_AUTH_KEYS={"Custom_Whisper": "x"}, TRANSCRIPTION_CUSTOM_URL="",
        SELECTED_CUSTOM_WHISPER_MODEL="m",
    )
    for prefix in ("MIC", "SPEAKER"):  # config.py defaults
        for key, value in dict(THRESHOLD=300, AUTOMATIC_THRESHOLD=False, RECORD_TIMEOUT=RECORD_TIMEOUT,
                               PHRASE_TIMEOUT=3, MAX_PHRASES=10, AVG_LOGPROB=-0.8,
                               NO_SPEECH_PROB=0.6, NO_REPEAT_NGRAM_SIZE=0,
                               ENABLE_VAD=vad).items():
            setattr(cfg, f"{prefix}_{key}", value)

    inference, results, sources, losses, detectors, queues, google_requests = [], [], [], [], [], [], []

    def timed(cls):
        original = cls.transcribe

        def wrapper(self, *a, **k):
            begin = time.monotonic()
            try:
                return original(self, *a, **k)
            finally:
                inference.append((begin, time.monotonic()))
        return wrapper

    class FakeGoogleResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(request, timeout=None):
        google_requests.append((request.data, request.headers.get("Content-type")))
        return FakeGoogleResponse(json.dumps(
            {"result": [{"alternative": [{"transcript": "google ok", "confidence": 0.9}]}]}
        ).encode())

    class RecordingQueue(TimedQueue):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            queues.append(self)

    original_detector = audio_listener.NativeAudioListener._detector

    def counting_detector(self, *a, **k):
        detectors.append(CountingDetector(original_detector(self, *a, **k), losses))
        return detectors[-1]

    source_cls, extra = PacedSource, []
    if args.listener == "fork":
        source_cls, extra = fork_patches(transcription_recorder, losses)

    def make_source(**kw):
        sources.append(source_cls(timeline, kw.get("sample_rate", rate), kw.get("channels", channels)))
        return sources[-1]

    seconds = len(timeline) / (2 * channels * rate)
    with ExitStack() as stack:
        server = FakeApiServer() if engine == "api" else None
        if server:
            stack.callback(server.close)
            cfg.TRANSCRIPTION_CUSTOM_URL = f"http://127.0.0.1:{server.server_address[1]}/v1"
        for p in [
            patch.object(audio_listener.NativeAudioListener, "_detector", counting_detector),
            patch.object(model, "config", cfg), patch.object(model, "Queue", RecordingQueue),
            patch.object(transcription_recorder, "AudioCaptureSource", make_source),
            patch.object(providers.LocalWhisperProvider, "transcribe", timed(providers.LocalWhisperProvider)),
            patch.object(providers.GoogleProvider, "transcribe", timed(providers.GoogleProvider)),
            patch.object(providers.OpenAICompatibleTranscriptionProvider, "transcribe",
                         timed(providers.OpenAICompatibleTranscriptionProvider)),
            patch.object(google_speech, "urlopen", fake_urlopen), *extra,
        ]:
            stack.enter_context(p)
        session = (model.SpeakerSession if kind == "speaker" else model.MicSession)()
        session.transcript_fnc = lambda result: results.append((time.monotonic(), result))
        device = {"name": "fake", "index": 0, "defaultSampleRate": rate, "maxInputChannels": channels}
        began = time.monotonic()
        try:
            session.reconfigure(transcript=True, device=device)
            ready = time.monotonic()
            while time.monotonic() - began < seconds + 8:
                time.sleep(0.2)
        finally:
            stop_began = time.monotonic()
            timed_out = session._stop()
            stop_seconds = time.monotonic() - stop_began

    t0 = sources[-1].t0 if sources else began
    texts = [(t - t0, r) for t, r in results if r.get("text")]
    # A result belongs to the last utterance that had started when it arrived; a
    # sentence split by VAD at a pause therefore still scores as one utterance.
    groups = [[] for _ in clips]
    for t, r in texts:
        groups[max([i for i, start in enumerate(starts) if start <= t] or [0])].append((t, r))
    utterances = []
    for reference, end, group in zip(TEXTS, ends, groups):
        entry = {"reference": reference, "speech_end_s": round(end, 3), "results": len(group)}
        if group:
            hypothesis = "".join(r["text"] for _, r in group)
            entry.update(text=hypothesis, language=group[-1][1].get("language"),
                         latency_s=round(group[-1][0] - end, 3))
            if engine == "whisper":
                entry["cer"] = round(character_error_rate(reference, hypothesis), 4)
            last = [e - b for b, e in inference if e - t0 <= group[-1][0] + 1e-3]
            if last:
                entry["last_inference_s"] = round(last[-1], 3)
        utterances.append(entry)
    case = {
        "listener": args.listener, "kind": kind, "detector": "vad" if vad else "energy", "engine": engine,
        "device_rate": rate, "device_channels": channels, "utterances": utterances,
        "transcriber_ready_s": round(ready - t0, 3),
        "losses": [(round(t - t0, 3), kind_) for t, kind_ in losses],
        "record_timeout_drops": sum(1 for _, k in losses if k == "record_timeout"),
        "rejected_short": sum(1 for _, k in losses if k == "rejected_short"),
        "detector_events": [(round(t - t0, 3), action, size, None if since is None else round(since, 3))
                            for d in detectors for t, action, size, since in d.events],
        "results": sum(1 for g in groups if g), "expected": len(clips),
        "attribution_ambiguous": any(u.get("latency_s", 0) > GAP_S - 1 for u in utterances),
        "result_log": [(round(t - t0, 3), r.get("text"), r.get("recognition_error")) for t, r in results],
        "queued": [(round(t - t0, 3), n, reason) for q in queues for t, n, reason in q.items],
        "stop_seconds": round(stop_seconds, 3), "stop_timed_out": bool(timed_out),
        "stop_stream_calls": sum(s.stop_stream_calls for s in sources),
        "recognition_error_seen": any(r.get("recognition_error") for _, r in results),
    }
    if engine == "google":
        import av
        decoded = []
        for data, header in google_requests:
            with av.open(io.BytesIO(data)) as c:
                frames = sum(f.samples for f in c.decode(audio=0))
                decoded.append({"content_type": header, "rate": c.streams.audio[0].rate,
                                "seconds": round(frames / c.streams.audio[0].rate, 2)})
        case["google_requests"] = decoded
    if server:
        case["api_uploads"] = server.uploads
    return case


def passed(case, fail_on_loss):
    ok = (case["results"] == case["expected"] and not case["stop_timed_out"]
          and not case["recognition_error_seen"] and not case["attribution_ambiguous"]
          and case["transcriber_ready_s"] < LEAD_S)
    if fail_on_loss:
        ok = ok and not case["losses"]
    if case["engine"] == "whisper":
        ok = ok and all(u.get("cer", 1) <= 0.5 for u in case["utterances"])
    if case["engine"] == "google":
        ok = ok and len(case.get("google_requests", [])) >= case["expected"]
    if case["engine"] == "api":
        uploads = case.get("api_uploads", [])
        ok = ok and len(uploads) >= case["expected"] and all(isinstance(u, list) and u[3] for u in uploads)
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--compute", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--weight", default="base")
    parser.add_argument("--root", default=str(ROOT), help="folder containing weights/whisper/<weight>")
    parser.add_argument("--kinds", default="mic,speaker")
    parser.add_argument("--detectors", default="energy,vad")
    parser.add_argument("--engines", default="whisper,google,api")
    parser.add_argument("--listener", choices=("native", "fork"), default="native",
                        help="fork = develop's SpeechRecognition listener (energy and VAD listen loops)")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--fail-on-loss", action="store_true",
                        help="FAIL a case when any phrase is dropped or rejected")
    parser.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "vrct-e2e"))
    args = parser.parse_args()
    if "whisper" in args.engines.split(","):
        from models.transcription.transcription_whisper import checkWhisperWeight
        if not checkWhisperWeight(args.root, args.weight):  # else the app silently falls back to Google
            parser.error(f"no loadable Whisper weight {args.weight!r} under {args.root}")
    Path(args.cache_dir).mkdir(parents=True, exist_ok=True)
    clips = [synthesize(text, args.cache_dir) for text in TEXTS]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"listener": args.listener, "compute": args.compute, "weight": args.weight,
              "python": sys.version.split()[0], "status": "PASS", "cases": []}
    for _ in range(args.repeat):
        for engine in args.engines.split(","):
            for kind in args.kinds.split(","):
                for detector in args.detectors.split(","):
                    label = f"{args.listener}/{engine}/{kind}/{detector}"
                    try:
                        case = run_case(args, clips, kind, detector == "vad", engine)
                        case["status"] = "PASS" if passed(case, args.fail_on_loss) else "FAIL"
                    except Exception:
                        case = {"listener": args.listener, "kind": kind, "detector": detector,
                                "engine": engine, "status": "ERROR", "error": traceback.format_exc()}
                    report["cases"].append(case)
                    if case["status"] != "PASS":
                        report["status"] = "FAIL"
                    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"{label}: {case['status']} {case.get('results')}/{case.get('expected')} "
                          f"losses={case.get('losses')} "
                          f"latency={[u.get('latency_s') for u in case.get('utterances', [])]}", flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
