"""Frozen-sidecar end-to-end check: real Whisper inside the PyInstaller exe.

    python tools/check_frozen_e2e.py build cpu|cuda   # validation build under tmp/frozen-e2e
    python tools/check_frozen_e2e.py run cpu|cuda --weights <dir containing weights/whisper/base>

`build` copies spec/backend*.spec with absolute paths and tools/frozen_e2e_hook.py
as a runtime hook, then runs PyInstaller from the shared venv without modifying
it (PYTHONPATH supplies the built vrct_audio and the pinned headless cv2).
`run` copies the dist to a fresh folder with an isolated config.json and the
Whisper weights, starts the exe, enables mic transcription over the real stdin
IPC, plays SAPI speech through the hook's capture source and checks the
/run/transcription_send_mic_message events, then sends /run/shutdown and ends the
process 2 s later as the Tauri UI does (the sidecar never exits on its own). Network,
real recording and translation are off. The build is NOT a release build.
"""

import argparse
import base64
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src-python"), str(ROOT)]
VENVS = {"cpu": Path(r"D:\WORKSPACE\WORK\VRChatProject\VRCT\.venv"),
         "cuda": Path(r"D:\WORKSPACE\WORK\VRChatProject\VRCT\.venv_cuda")}
SPECS = {"cpu": "backend.spec", "cuda": "backend_cuda.spec"}
WORK = ROOT / "tmp" / "frozen-e2e"
EXE = "VRCT-sidecar-x86_64-pc-windows-msvc.exe"
RATE = 48000


def build(mode, args):
    venv = Path(args.venv or VENVS[mode])
    text = (ROOT / "spec" / SPECS[mode]).read_text(encoding="utf-8")
    # backend_cuda.spec also reads hf_xet from the CPU .venv; map each name to its real venv.
    text = text.replace("./../.venv_cuda/", Path(args.venv or VENVS["cuda"]).as_posix() + "/")
    text = text.replace("./../.venv/", (venv if mode == "cpu" else VENVS["cpu"]).as_posix() + "/")
    text = text.replace("./../", ROOT.as_posix() + "/")
    text = text.replace("'..\\\\src-python\\\\mainloop.py'", repr(str(ROOT / "src-python" / "mainloop.py")))
    assert "./../" not in text and "..\\\\src-python" not in text, "unhandled relative path in spec"
    assert text.count("runtime_hooks=[]") == 1
    text = text.replace("runtime_hooks=[]", f"runtime_hooks=[{str(ROOT / 'tools' / 'frozen_e2e_hook.py')!r}]")
    WORK.mkdir(parents=True, exist_ok=True)
    spec = WORK / f"{mode}.spec"
    spec.write_text(text, encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [str(ROOT / "tmp" / "native-site"), args.cv2_site, str(ROOT / "src-python")])}
    command = [str(venv / "Scripts" / "python.exe"), "-m", "PyInstaller", str(spec), "--noconfirm",
               "--distpath", str(WORK / f"dist-{mode}"), "--workpath", str(WORK / f"work-{mode}"),
               "--log-level", "WARN"]
    started = time.monotonic()
    with (WORK / f"build-{mode}.log").open("w", encoding="utf-8") as log:
        code = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, cwd=WORK).returncode
    print(f"build {mode}: exit {code} in {time.monotonic() - started:.0f}s; log {WORK / f'build-{mode}.log'}")
    return code


def make_timeline(path):
    from tools.check_audio_e2e import TEXTS, build_timeline, synthesize

    cache = Path(os.environ.get("TEMP", "/tmp")) / "vrct-e2e"
    cache.mkdir(parents=True, exist_ok=True)
    pcm, ends, starts = build_timeline([synthesize(t, cache) for t in TEXTS], RATE, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return len(pcm) / (2 * RATE), ends, starts


def run(mode, args):
    from tools.whisper_eval.metrics import character_error_rate
    from tools.check_audio_e2e import TEXTS

    dist = WORK / f"dist-{mode}"
    run_dir = WORK / f"run-{mode}-{args.suffix}"
    if run_dir.exists():
        raise SystemExit(f"{run_dir} exists; use a new --suffix to keep earlier evidence")
    app = run_dir / "app"
    shutil.copytree(dist, app)
    shutil.copytree(Path(args.weights) / "weights" / "whisper" / args.weight,
                    app / "weights" / "whisper" / args.weight)
    seconds, ends, starts = make_timeline(run_dir / "timeline.wav")
    settings = {key: False for key in (
        "ENABLE_TELEMETRY", "AUTO_MIC_SELECT", "AUTO_SPEAKER_SELECT", "VRC_MIC_MUTE_SYNC", "WEBSOCKET_SERVER",
        "OBS_BROWSER_SOURCE", "OVERLAY_SMALL_LOG", "OVERLAY_LARGE_LOG", "OVERLAY_VR_PANEL", "LOGGER_FEATURE",
        "ENABLE_CLIPBOARD", "CONVERT_MESSAGE_TO_ROMAJI", "CONVERT_MESSAGE_TO_HIRAGANA", "ENABLE_TRANSLATION",
        "SEND_MESSAGE_TO_VRC", "MIC_ENABLE_VAD")}
    settings.update(OSC_IP_ADDRESS="127.0.0.2", SELECTED_TRANSCRIPTION_ENGINE="Whisper",
                    WHISPER_WEIGHT_TYPE=args.weight)
    if args.vad:
        settings["MIC_ENABLE_VAD"] = True
    (app / "config.json").write_text(json.dumps(settings), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "HTTP_PROXY", "HTTPS_PROXY")}
    env.update(PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", VRCT_FROZEN_E2E_DIR=str(run_dir),
               VRCT_FROZEN_E2E_WAV=str(run_dir / "timeline.wav"))
    events = queue.Queue()
    stderr = (run_dir / "stderr.log").open("w", encoding="utf-8")
    child = subprocess.Popen([str(app / EXE)], cwd=run_dir, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=stderr, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)

    def reader():
        with (run_dir / "stdout.log").open("w", encoding="utf-8") as out:
            for line in child.stdout:
                out.write(line)
                out.flush()
                try:
                    events.put((time.monotonic(), json.loads(line)))
                except json.JSONDecodeError:
                    pass

    threading.Thread(target=reader, daemon=True).start()

    def send(endpoint, data=None):
        # Like the UI, data travels as base64-encoded JSON (mainloop.receiver -> utils.encodeBase64).
        if data is not None:
            data = base64.b64encode(json.dumps(data).encode("utf-8")).decode("ascii")
        child.stdin.write(json.dumps({"endpoint": endpoint, "data": data}) + "\n")
        child.stdin.flush()

    report = {"mode": mode, "weight": args.weight, "detector": "vad" if args.vad else "energy",
              "scope": "frozen sidecar, real IPC, real Whisper, paced WAV capture; network/recording/translation off",
              "status": "FAIL"}
    messages, responses, last_feed = [], {}, 0.0
    began = time.monotonic()
    phase, enabled_at = "init", None
    try:
        while True:
            now = time.monotonic()
            assert child.poll() is None, f"sidecar exited early with {child.returncode}"
            assert now - began < 180 + seconds, f"timeout in phase {phase}"
            if now - last_feed > 10:
                send("/run/feed_watchdog")
                last_feed = now
            if phase == "listening" and now - enabled_at > seconds + 10:
                send("/set/disable/transcription_send")
                phase = "disabling"
            try:
                at, event = events.get(timeout=0.2)
            except queue.Empty:
                continue
            endpoint = event.get("endpoint")
            if endpoint == "/run/initialization_complete" and phase == "init":
                assert event["status"] == 200, event
                report["init_seconds"] = round(at - began, 2)
                send("/get/data/compute_mode")
                send("/get/data/selectable_transcription_compute_device_list")
                phase = "selecting"
            elif endpoint == "/get/data/compute_mode":
                responses[endpoint] = event.get("result")
            elif endpoint == "/get/data/selectable_transcription_compute_device_list" and phase == "selecting":
                # Select the device like the UI does; the config default is always the CPU entry.
                device = next(d for d in event["result"] if d["device"] == mode)
                send("/set/data/selected_transcription_compute_device", device)
            elif endpoint == "/set/data/selected_transcription_compute_device" and phase == "selecting":
                assert event["status"] == 200 and event["result"]["device"] == mode, event
                send("/set/enable/transcription_send")
                phase = "enabling"
            elif endpoint == "/set/enable/transcription_send" and phase == "enabling":
                assert event["status"] == 200 and event["result"] is True, event
                enabled_at, phase = at, "listening"
            elif endpoint == "/run/transcription_send_mic_message":
                messages.append((at, event))
            elif endpoint == "/set/disable/transcription_send" and phase == "disabling":
                assert event["status"] == 200, event
                send("/run/shutdown")
                phase = "shutdown"
            elif endpoint == "/run/shutdown" and phase == "shutdown":
                assert event["status"] == 200, event
                break
        # Like src-ui useWindow.asyncCloseApp: wait 2 s, then Tauri ends the sidecar.
        time.sleep(2)
        report["alive_after_shutdown_grace"] = child.poll() is None
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        stderr.close()
    worker = json.loads((run_dir / "worker-result.json").read_text(encoding="utf-8"))
    t0 = worker["opens"][-1] if worker["opens"] else None
    texts = []
    for at, event in messages:
        result = event.get("result") or {}
        text = result.get("original", {}).get("message") if isinstance(result.get("original"), dict) else None
        texts.append({"at_s": None if t0 is None else round(at - t0, 3),
                      "text": text if text is not None else result})
    utterances = []
    # Same attribution as check_audio_e2e: a message belongs to the last utterance started.
    bounds = starts[1:] + [float("inf")]
    for reference, start, end, until in zip(TEXTS, starts, ends, bounds):
        window = [m for m in texts if isinstance(m["text"], str) and m["at_s"] is not None
                  and start <= m["at_s"] < until]
        hypothesis = "".join(m["text"] for m in window)
        utterances.append({"reference": reference, "text": hypothesis,
                           "cer": round(character_error_rate(reference, hypothesis), 4),
                           "latency_s": round(window[-1]["at_s"] - end, 3) if window else None})
    stderr_text = (run_dir / "stderr.log").read_text(encoding="utf-8")
    error_log = (run_dir / "error.log").read_text(encoding="utf-8") if (run_dir / "error.log").exists() else ""
    expected = "requests.exceptions.ConnectionError: HTTP disabled by frozen E2E validation"
    report["error_log_only_expected_http"] = (error_log.count("Traceback (most recent call last):")
                                              == error_log.count(expected))
    report.update(compute_mode=responses.get("/get/data/compute_mode"), worker=worker, messages=texts,
                  utterances=utterances, stderr_bytes=len(stderr_text.encode()))
    ok = (not report["stderr_bytes"] and report["error_log_only_expected_http"]
          and worker["counts"].get("whisper_calls", 0) > 0
          and not worker["counts"].get("google_calls") and not worker["counts"].get("real_recording_opens")
          and worker["config"]["engine"] == "Whisper" and all(u["cer"] <= 0.5 for u in utterances)
          and report["compute_mode"] == mode and worker["config"]["compute_device"] == mode)
    report["status"] = "PASS" if ok else "FAIL"
    (run_dir / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"run {mode}: {report['status']} cer={[u['cer'] for u in utterances]} "
          f"latency={[u['latency_s'] for u in utterances]} -> {run_dir / 'result.json'}")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("build", "run"))
    parser.add_argument("mode", choices=("cpu", "cuda"))
    parser.add_argument("--venv", help="override the shared venv used for PyInstaller")
    parser.add_argument("--cv2-site", default=r"D:\codex\home\worktrees\4508\VRCT\tmp\cv2-pinned",
                        help="site dir with the pinned opencv-python-headless 4.10 (see progress.md cycle 11)")
    parser.add_argument("--weights", default=r"D:\WORKSPACE\WORK\VRChatProject\VRCT")
    parser.add_argument("--weight", default="base")
    parser.add_argument("--vad", action="store_true")
    parser.add_argument("--suffix", default="1")
    args = parser.parse_args()
    return (build if args.action == "build" else run)(args.mode, args)


if __name__ == "__main__":
    sys.exit(main())
