"""Check default Windows mic/loopback locally; no saved audio or network.

benchmark opens/closes both devices. lifecycle briefly captures both, discards
PCM, and checks pause requests, simultaneous stop and restart. Run with the VRCT
venv and its native extension. Each run is isolated with a 90-second watchdog.
This does not test physical unplug/replug, recognition, or guaranteed silence.
enumeration profiles device-list updates without opening or recording streams;
it needs PyAudioWPatch but not the Rust extension.
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
from pathlib import Path
import platform
from queue import Queue
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

import pyaudiowpatch as pa

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src-python'))


def devices():
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

    def put_nowait(self, value):
        self.calls += 1
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


def environment():
    paths = ['src-python/models/transcription/audio_source.py',
             'src-python/models/transcription/audio_listener.py',
             'src-python/models/transcription/transcription_recorder.py',
             'tools/check_audio_capture.py']
    result = {'python': platform.python_version(), 'platform': platform.platform(),
              'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in paths}}
    if 'vrct_audio' in sys.modules:
        path = Path(import_module('vrct_audio.vrct_audio').__file__)
        result['native_binary_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['benchmark', 'lifecycle', 'enumeration'])
    parser.add_argument('--output', type=Path, help='Save metrics only (never PCM) as JSON')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        result = {'benchmark': benchmark, 'lifecycle': lifecycle, 'enumeration': enumeration}[args.mode]()
        result.update(environment())
        print(json.dumps(result, indent=2), flush=True)
    else:
        try:
            process = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), args.mode, '--worker'],
                                     capture_output=True, text=True, encoding='utf-8', timeout=90,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired:
            parser.exit(1, 'Audio check timed out after 90 seconds; worker terminated.\n')
        if process.returncode:
            parser.exit(1, process.stdout + process.stderr)
        # Require a complete report before presenting a successful result.
        report = json.dumps(json.loads(process.stdout), indent=2) + '\n'
        print(report, end='')
        if args.output:
            args.output.write_text(report, encoding='utf-8')
