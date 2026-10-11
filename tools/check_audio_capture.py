"""Check default Windows mic/loopback locally; no saved audio or network.

benchmark opens/closes both devices. lifecycle briefly captures both, discards
PCM, and checks pause requests, simultaneous stop and restart. Run with the VRCT
venv and its native extension. Each run is isolated with a 90-second watchdog.
These modes do not test physical unplug/replug, recognition, or guaranteed silence.
enumeration profiles device-list updates without opening or recording streams;
it needs PyAudioWPatch but not the Rust extension.

hotplug is interactive: it opens the chosen mic with the production recorder and
asks you (Enter on the console) to switch the Windows default endpoint, unplug
the USB headset, and plug it back in. It records callback counts, device errors,
stop() duration and whether a new recorder opens; every prompt and wait has a
--step-timeout, stop() is bounded like model.py, and the worker is capped at 900 s.
From the repository root in PowerShell:

    $env:PYTHONPATH="$PWD\\tmp\\native-site;$PWD\\src-python"
    .\\.venv\\Scripts\\python.exe tools/check_audio_capture.py hotplug --output tmp/capture-hotplug.json

Add --vad for SelectedMicVadRecorder and --speaker to also watch the default loopback.
With $env:VRCT_RUST_AUDIO="1" the devices are the Rust backend's (vrct_audio / cpal) instead of
PyAudioWPatch / pycaw; the report says which.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import asdict
import hashlib
from importlib import import_module
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
from queue import Queue
import statistics
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import pyaudiowpatch as pa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src-python'))


def devices():
    if os.environ.get('VRCT_RUST_AUDIO') == '1':
        # the Rust backend's devices (vrct_audio / cpal), as device_manager lists them then
        listed = import_module('vrct_audio').list_devices()
        mic = next(d for d in listed['inputs'] if d['name'] == listed['default_input'])
        speaker = next(d for d in listed['loopbacks'] if d['name'] == listed['default_loopback'])
        return mic, speaker
    with pa.PyAudio() as api:
        mic = api.get_default_input_device_info()
        host = api.get_host_api_info_by_type(pa.paWASAPI)
        output = api.get_device_info_by_index(int(host['defaultOutputDevice']))
        speaker = api.get_wasapi_loopback_analogue_by_dict(output)
    return mic, speaker


def benchmark():
    from models.transcription.audio_source import AudioCaptureSource
    mic, speaker = devices()
    report = []
    original = pa.PyAudio
    # App callers hold this lock for constructor/probe too. There are no
    # competing captures in this worker, but retain the production contract.
    from device_manager import pyaudio_op_lock
    for label, device in [('mic', mic), ('loopback', speaker)]:
        kwargs = dict(device_index=int(device['index']), sample_rate=int(device['defaultSampleRate']),
                      speaker=label == 'loopback', channels=int(device['maxInputChannels']) if label == 'loopback' else 1)
        measurements = {'current': []}
        counts = {'current': []}
        for iteration in range(7):
            order = [('current', AudioCaptureSource)]
            for name, factory in order:
                initialized = []
                def counted():
                    initialized.append(1)
                    return original()
                with pyaudio_op_lock, patch.object(pa, 'PyAudio', side_effect=counted):
                    started = time.perf_counter_ns()
                    source = factory(**kwargs)
                    with source:
                        assert source.stream is not None
                    elapsed_ms = (time.perf_counter_ns() - started) / 1e6
                measurements[name].append(elapsed_ms)
                counts[name].append(len(initialized))
                assert len(initialized) == 1
        report.append({'device': label, 'index': kwargs['device_index'], 'rate': kwargs['sample_rate'],
                       'channels': kwargs['channels'], 'milliseconds': measurements,
                       'median_ms': {name: statistics.median(values) for name, values in measurements.items()},
                       'pyaudio_init_counts': counts})
    return {'scope': 'Actual default-device constructor plus probe open/close only; no reads or ASR',
            'comparison': 'Current capture source only; historical comparisons are archived separately',
            'repeats': 7, 'results': report}


def enumeration():
    with patch.object(pa.PyAudio, 'open', side_effect=AssertionError('Enumeration must not open audio streams')) as forbidden_open:
        result = _profile_enumeration()
        if forbidden_open.called:
            raise RuntimeError('Device enumeration failed: attempted to open an audio stream')
        return result


def _profile_enumeration():
    import device_manager as dm

    if dm.PyAudio is not pa.PyAudio:
        raise RuntimeError('DeviceManager has no usable PyAudioWPatch backend')
    methods = ('__init__', 'terminate', 'get_host_api_count', 'get_host_api_info_by_index',
               'get_host_api_info_by_type', 'get_device_info_by_host_api_device_index',
               'get_device_info_by_index', 'get_loopback_device_info_generator')
    originals = {name: getattr(pa.PyAudio, name) for name in methods}
    trials = []
    snapshot_hashes = []
    for _ in range(9):
        counts = Counter()
        elapsed = {'__init__': 0.0, 'terminate': 0.0}
        failures = []

        def wrap(name):
            if name == 'get_loopback_device_info_generator':
                def measured_generator(*args, **kwargs):
                    counts[name] += 1
                    try:
                        yield from originals[name](*args, **kwargs)
                    except Exception as error:
                        failures.append((name, type(error).__name__))
                        raise
                return measured_generator

            def measured(*args, **kwargs):
                counts[name] += 1
                started = time.perf_counter_ns() if name in elapsed else None
                try:
                    return originals[name](*args, **kwargs)
                except Exception as error:
                    failures.append((name, type(error).__name__))
                    raise
                finally:
                    if started is not None:
                        elapsed[name] += (time.perf_counter_ns() - started) / 1e6
            return measured

        with ExitStack() as stack:
            for name in methods:
                stack.enter_context(patch.object(pa.PyAudio, name, wrap(name)))
            stack.enter_context(patch.object(dm, 'errorLogging', side_effect=lambda: failures.append(('update', 'logged_error'))))
            started = time.perf_counter_ns()
            dm.device_manager.update()
            total = (time.perf_counter_ns() - started) / 1e6
        if failures:
            raise RuntimeError(f'Device enumeration failed: {failures}')
        snapshot = asdict(dm.device_manager._device_snapshot)
        snapshot_hashes.append(hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode('utf-8')).hexdigest())
        trials.append({'total_ms': total, 'initialize_ms': elapsed['__init__'],
                       'terminate_ms': elapsed['terminate'],
                       'other_ms': total - elapsed['__init__'] - elapsed['terminate'],
                       'calls': dict(counts)})
    if len(set(snapshot_hashes)) != 1:
        raise RuntimeError('Device snapshot changed during enumeration measurement; repeat when stable')
    return {'scope': 'Isolated DeviceManager.update with no open streams in this worker; no capture or network',
            'timing_note': 'Import-time initialization is excluded. Other time includes Python instrumentation. '
                           'Times are per-trial non-overlapping; only init and terminate calls are timed separately. '
                           'Results do not describe updates while an existing PortAudio stream remains open.',
            'repeats': len(trials), 'trials': trials,
            'median_ms': {key: statistics.median(row[key] for row in trials)
                          for key in ('total_ms', 'initialize_ms', 'terminate_ms', 'other_ms')},
            'snapshot_sha256': snapshot_hashes[0],
            'pyaudiowpatch': {'version': version('PyAudioWPatch'),
                             'extension_sha256': hashlib.sha256(Path(pa.pa.__file__).read_bytes()).hexdigest()},
            'device_manager_sha256': hashlib.sha256((ROOT / 'src-python/device_manager.py').read_bytes()).hexdigest()}


class DiscardQueue:
    def __init__(self):
        self.calls = 0
        self.total_bytes = 0
        self.last_at = None

    def put_nowait(self, value):
        self.calls += 1
        self.last_at = time.monotonic()
        if isinstance(value, tuple):  # phrases; energy values carry no bytes
            self.total_bytes += len(value[0])


def lifecycle():
    from models.transcription.native_audio import get_native_audio
    from models.transcription.transcription_recorder import (
        SelectedMicEnergyAndAudioRecorder, SelectedSpeakerEnergyAndAudioRecorder,
    )
    assert get_native_audio() is not None, 'Install native/vrct-audio first'
    assert 'speech_recognition' not in sys.modules
    mic, speaker = devices()
    reports = []
    for run in range(3):
        def make(cls, device):
            return cls(device, 300, False, 1, record_timeout=3)
        with ThreadPoolExecutor(max_workers=2) as workers:
            mic_future = workers.submit(make, SelectedMicEnergyAndAudioRecorder, mic)
            speaker_future = workers.submit(make, SelectedSpeakerEnergyAndAudioRecorder, speaker)
            recorders = [mic_future.result(), speaker_future.result()]
        actual_sources = []
        for recorder, requested, channels in zip(recorders, (mic, speaker), (1, int(speaker['maxInputChannels']))):
            source = recorder.source
            assert source.device_index == int(requested['index']), 'unexpected default-device fallback'
            assert source.SAMPLE_RATE == int(requested['defaultSampleRate'])
            assert source.channels == channels and source.SAMPLE_WIDTH == 2
            actual_sources.append({'index': source.device_index, 'rate': source.SAMPLE_RATE,
                                   'channels': source.channels})
        queues = [DiscardQueue(), DiscardQueue()]
        meters = [Queue(maxsize=1), Queue(maxsize=1)]
        try:
            for recorder, output, meter in zip(recorders, queues, meters):
                recorder.recordIntoQueue(output, meter)
            deadline = time.monotonic() + 5
            while any(recorder.source.stream is None for recorder in recorders):
                assert time.monotonic() < deadline, 'listener did not open both devices'
                assert not any(recorder.device_error_event.is_set() for recorder in recorders)
                time.sleep(0.01)
            time.sleep(0.8)
            if run == 1:
                for recorder in recorders:
                    recorder.pause()
                time.sleep(0.2)
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=2) as workers:
                list(workers.map(lambda recorder: recorder.stop(), recorders))
            stop_ms = (time.perf_counter() - started) * 1000
            for recorder in recorders:
                recorder.stop()
                assert recorder.source.stream is None
                assert recorder.source.audio is None
                assert not recorder.device_error_event.is_set(), recorder.device_error_info
            reports.append({'run': run, 'pause_requested': run == 1, 'stop_ms': stop_ms,
                            'actual_sources': actual_sources,
                            'meter_received': [not meter.empty() for meter in meters],
                            'discarded_phrases': [output.calls for output in queues],
                            'discarded_bytes': [output.total_bytes for output in queues]})
        finally:
            for recorder in recorders:
                if recorder.stop is not None:
                    recorder.stop()
    return {'scope': 'Actual default mic and WASAPI loopback; raw PCM discarded immediately, no ASR/network',
            'runs': reports, 'not_tested': ['physical unplug/replug', 'endpoint switch', 'recognition accuracy']}


STOP_TIMEOUT_SEC = 15  # Same bound as model.TRANSCRIPT_STOP_JOIN_TIMEOUT for recorder.stop().
OPEN_TIMEOUT_SEC = 30
HOTPLUG_CAP_SEC = 900


def wait_until(predicate, timeout):
    # Short sleeps keep Ctrl+C responsive on Windows, unlike one long Event.wait.
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)
    return True


def bounded(function, timeout):
    """Run a call that may hang inside PyAudio on a daemon thread."""
    outcome = {}

    def run():
        try:
            outcome['value'] = function()
        except Exception as error:
            outcome['error'] = type(error).__name__

    started = time.monotonic()
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    returned = wait_until(lambda: not thread.is_alive(), timeout)
    return returned, elapsed_ms(time.monotonic(), started), outcome


def elapsed_ms(later, earlier):
    return None if later is None or earlier is None else round((later - earlier) * 1000, 1)


def ask(step, message, timeout):
    print(f'\n>>> {message}\n    (Enterで続行 / {timeout:.0f}秒で中止 / Ctrl+Cで中止)', file=sys.stderr, flush=True)
    line = []
    threading.Thread(target=lambda: line.append(sys.stdin.readline()), daemon=True).start()
    if not wait_until(lambda: line, timeout):
        raise TimeoutError(f'{step}: no input within {timeout:.0f}s')
    if not line[0]:
        raise EOFError(f'{step}: stdin closed')
    return line[0].strip()


class Probe:
    """One production recorder; counts callbacks and keeps no PCM or levels."""

    def __init__(self, label, recorder, requested):
        self.label, self.recorder = label, recorder
        self.audio, self.energy = DiscardQueue(), DiscardQueue()
        self.error_seen_at = None
        self.stopped = False
        # Timestamp the error when it is raised, not when a step next polls
        # (the user may unplug while the console is still waiting for Enter).
        threading.Thread(target=self._watch_error, daemon=True).start()
        source = recorder.source
        self.source = {'requested_index': int(requested['index']), 'actual_index': source.device_index,
                       'rate': source.SAMPLE_RATE, 'channels': source.channels}
        recorder.recordIntoQueue(self.audio, self.energy)

    def _watch_error(self):
        self.recorder.device_error_event.wait()
        if self.error_seen_at is None:
            self.error_seen_at = time.monotonic()

    def poll(self):
        if self.error_seen_at is None and self.recorder.device_error_event.is_set():
            self.error_seen_at = time.monotonic()
        return self.error_seen_at is not None

    def snapshot(self):
        self.poll()
        info = self.recorder.device_error_info
        return {'device': self.label, 'energy_callbacks': self.energy.calls, 'queued_phrases': self.audio.calls,
                'stream_open': self.recorder.source.stream is not None,
                'device_error': None if info is None else {'code': info.error_code.value, 'stage': info.stage,
                                                           'exception_type': info.exception_type}}

    def stop(self):
        self.stopped = True
        returned, stop_ms, outcome = bounded(self.recorder.stop, STOP_TIMEOUT_SEC)
        return {'device': self.label, 'returned_within_timeout': returned, 'stop_ms': stop_ms,
                'error': outcome.get('error'), 'stream_closed': self.recorder.source.stream is None}


def hotplug(vad=False, speaker=False, step_timeout=120.0):
    from device_manager import device_manager
    from models.transcription.native_audio import get_native_audio
    from models.transcription.transcription_recorder import (
        SelectedMicEnergyAndAudioRecorder, SelectedMicVadRecorder, SelectedSpeakerEnergyAndAudioRecorder,
    )
    assert get_native_audio() is not None, 'Install native/vrct-audio first'
    # Same constructor arguments MicSession/SpeakerSession pass with record_timeout=3.
    makers = {'mic': (lambda d: SelectedMicVadRecorder(d, record_timeout=3)) if vad else
              (lambda d: SelectedMicEnergyAndAudioRecorder(d, 300, False, 3, record_timeout=3)),
              'speaker': lambda d: SelectedSpeakerEnergyAndAudioRecorder(d, 300, False, 3, record_timeout=3)}

    default = device_manager.getDefaultMicDevice()
    host = default['host']['name']
    mics = [d for d in device_manager.getMicDevices().get(host, []) if d.get('name') != 'NoDevice']
    if not mics:
        raise RuntimeError('No microphone found on the default host')
    print('\nマイク一覧 (この表示は保存されません):', file=sys.stderr)
    for number, device in enumerate(mics):
        mark = ' (既定)' if device['index'] == default['device']['index'] else ''
        print(f'  [{number}] {device["name"]}{mark}', file=sys.stderr)
    choice = ask('select', '抜き差しするマイク(USBヘッドセット)の番号を入力。空欄なら既定', step_timeout)
    if choice and not (choice.isdigit() and int(choice) < len(mics)):
        raise ValueError('Invalid microphone number')
    mic_name = mics[int(choice)]['name'] if choice else default['device']['name']
    speaker_name = device_manager.getDefaultSpeakerDevice()['device']['name'] if speaker else None

    def resolve():
        # Like MicSession/SpeakerSession._resolve_device: look the name up in the current list.
        targets = [('mic', next((d for d in device_manager.getMicDevices().get(host, [])
                                 if d['name'] == mic_name), None))]
        if speaker_name not in (None, 'NoDevice'):
            targets.append(('speaker', next((d for d in device_manager.getSpeakerDevices()
                                             if d['name'] == speaker_name), None)))
        return targets

    opened = []

    def open_probes():
        probes, rows = [], []
        for label, device in resolve():
            if device is None:
                rows.append({'device': label, 'found': False, 'listening': False})
                continue
            # ponytail: a recorder that opens after this timeout is left for os._exit to discard.
            returned, open_ms, outcome = bounded(lambda label=label, device=device: Probe(
                label, makers[label](device), device), OPEN_TIMEOUT_SEC)
            probe = outcome.get('value')
            if probe is not None:
                opened.append(probe)
                probes.append(probe)
                wait_until(lambda: probe.recorder.source.stream is not None or probe.poll(), 5)
            rows.append({'device': label, 'found': True, 'open_ms': open_ms, 'returned_within_timeout': returned,
                         'error': outcome.get('error'), 'source': probe and probe.source,
                         'fell_back_to_other_device': probe and probe.source['actual_index'] != probe.source['requested_index'],
                         'listening': probe is not None and probe.recorder.source.stream is not None})
        return probes, rows

    report = {'scope': 'Guided physical hotplug check of the production recorder classes; '
                       'raw PCM discarded immediately, no ASR/network',
              'settings': {'recorder': 'vad' if vad else 'energy', 'speaker_loopback': speaker_name is not None,
                           'step_timeout_s': step_timeout, 'stop_timeout_s': STOP_TIMEOUT_SEC},
              'limitations': [
                  'Recorder layer only: MicSession/SpeakerSession, controller error notices and restarts are not run.',
                  'With Auto Mic Select on, the app follows the OS default input: DeviceManager monitoring stops the '
                  'mic session, re-resolves the new default by name and restarts it. This tool never re-selects.',
                  'Auto Speaker Select also follows the active render endpoint (ActiveEndpointTracker); not run here.',
                  'error_after_enter_ms includes human delay before unplugging (negative if unplugged before Enter); last_data_to_error_ms does not.',
                  'outcome no_data means no read returned during the window; it says nothing about loudness.',
                  'Device names are printed to the console only and not saved.'],
              'steps': [], 'completed': False}
    started = time.monotonic()

    def record(step, **data):
        report['steps'].append({'step': step, 'at_s': round(time.monotonic() - started, 3), **data})

    def observe(probes, seconds):
        before = [probe.snapshot() for probe in probes]
        wait_until(lambda: all([probe.poll() for probe in probes]), seconds)
        rows = []
        for probe, old in zip(probes, before):
            row = probe.snapshot()
            row['energy_delta'] = row['energy_callbacks'] - old['energy_callbacks']
            row['phrase_delta'] = row['queued_phrases'] - old['queued_phrases']
            row['outcome'] = ('error' if row['device_error'] else
                              'no_data' if row['energy_delta'] == 0 else 'data_continued')
            rows.append(row)
        return rows

    try:
        probes, rows = open_probes()
        record('open', devices=rows)
        if not all(row['listening'] for row in rows):
            report['aborted'] = 'open_failed'
            return report
        record('baseline', probes=observe(probes, 3))
        ask('endpoint_switch', 'Windowsのサウンド設定で既定の入力デバイス(--speaker時は出力も)を'
                               'テスト対象以外へ切り替えてからEnter', step_timeout)
        record('endpoint_switch', probes=observe(probes, 5))
        ask('endpoint_restore', '既定デバイスを元に戻してからEnter', step_timeout)
        record('endpoint_restore', probes=observe(probes, 3))
        ask('unplug', 'Enterを押したら、すぐにUSBヘッドセットを物理的に抜いてください', step_timeout)
        pressed = time.monotonic()
        mic = probes[0]
        detected = wait_until(lambda: all([probe.poll() for probe in probes]) or mic.poll(), step_timeout)
        record('unplug', mic_error_detected=detected,
               probes=[{**probe.snapshot(), 'error_after_enter_ms': elapsed_ms(probe.error_seen_at, pressed),
                        'last_data_to_error_ms': elapsed_ms(probe.error_seen_at, probe.energy.last_at)}
                       for probe in probes])
        record('stop_after_unplug', results=[probe.stop() for probe in probes])
        ask('replug', 'USBヘッドセットを挿し直し、Windowsが認識したらEnter', step_timeout)
        update_returned, update_ms, update = bounded(device_manager.update, OPEN_TIMEOUT_SEC)
        probes, rows = open_probes()
        record('restart_after_replug', device_update={'returned_within_timeout': update_returned,
                                                      'ms': update_ms, 'error': update.get('error')},
               devices=rows, probes=observe(probes, 3))
        record('stop_after_replug', results=[probe.stop() for probe in probes])
        report['completed'] = all(row['listening'] for row in rows)
    except KeyboardInterrupt:
        report['aborted'] = 'KeyboardInterrupt'
    except (TimeoutError, EOFError) as error:
        report['aborted'] = str(error)
    finally:
        cleanup = [probe.stop() for probe in opened if not probe.stopped]
        if cleanup:
            report['cleanup'] = cleanup
    return report


def environment():
    paths = ['src-python/models/transcription/audio_source.py',
             'src-python/models/transcription/audio_listener.py',
             'src-python/models/transcription/transcription_recorder.py',
             'src-python/device_manager.py',
             'tools/check_audio_capture.py']
    result = {'python': platform.python_version(), 'platform': platform.platform(),
              'rust_audio': os.environ.get('VRCT_RUST_AUDIO') == '1',
              'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in paths}}
    if 'vrct_audio' in sys.modules:
        path = Path(import_module('vrct_audio.vrct_audio').__file__)
        result['native_binary_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['benchmark', 'lifecycle', 'enumeration', 'hotplug'])
    parser.add_argument('--output', type=Path, help='Save metrics only (never PCM) as JSON')
    parser.add_argument('--vad', action='store_true', help='hotplug: use SelectedMicVadRecorder')
    parser.add_argument('--speaker', action='store_true', help='hotplug: also capture the default speaker loopback')
    parser.add_argument('--step-timeout', type=float, default=120.0, help='hotplug: seconds per prompt or wait')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.mode == 'hotplug':
            result = hotplug(args.vad, args.speaker, args.step_timeout)
        else:
            result = {'benchmark': benchmark, 'lifecycle': lifecycle, 'enumeration': enumeration}[args.mode]()
        result.update(environment())
        print(json.dumps(result, indent=2), flush=True)
        if args.mode == 'hotplug':
            # Do not wait for a stdin reader or a stop() still stuck in PyAudio.
            os._exit(0 if result['completed'] else 1)
    else:
        command = [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), args.mode, '--worker']
        if args.mode == 'hotplug':
            command += ['--step-timeout', str(args.step_timeout)] + ['--vad'] * args.vad + ['--speaker'] * args.speaker
            # Prompts need the console, so only stdout (the JSON report) is captured.
            process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True, encoding='utf-8')
            try:
                try:
                    stdout, _ = process.communicate(timeout=HOTPLUG_CAP_SEC)
                except KeyboardInterrupt:
                    # The worker got the same Ctrl+C; give it time to stop recorders and report.
                    stdout, _ = process.communicate(timeout=STOP_TIMEOUT_SEC * 3)
            except subprocess.TimeoutExpired:
                process.kill()
                parser.exit(1, 'Hotplug check exceeded its time cap; worker terminated.\n')
            if not stdout.strip():
                parser.exit(1, 'Hotplug worker produced no report.\n')
        else:
            try:
                process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=90,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
            except subprocess.TimeoutExpired:
                parser.exit(1, 'Audio check timed out after 90 seconds; worker terminated.\n')
            if process.returncode:
                parser.exit(1, process.stdout + process.stderr)
            stdout = process.stdout
        # Require a complete report before presenting a successful result.
        data = json.loads(stdout)
        report = json.dumps(data, indent=2) + '\n'
        print(report, end='')
        if args.output:
            args.output.write_text(report, encoding='utf-8')
        if args.mode == 'hotplug' and not data['completed']:
            parser.exit(1, 'Hotplug check did not complete; the partial report is shown above.\n')
