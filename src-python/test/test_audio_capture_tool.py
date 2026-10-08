"""Offline checks for the manual audio capture tool, using no audio devices."""

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import pytest


@pytest.fixture
def profiler(monkeypatch):
    state = SimpleNamespace(failure=None, changes=False, updates=0)

    class FakeAudio:
        def __init__(self):
            pass

        def terminate(self):
            pass

        def open(self):
            raise AssertionError('The profiler guard must replace open')

        def get_host_api_count(self):
            if state.failure == 'method':
                raise OSError('synthetic failure')
            return 1

        def get_host_api_info_by_index(self):
            return {}

        get_host_api_info_by_type = get_host_api_info_by_index
        get_device_info_by_host_api_device_index = get_host_api_info_by_index
        get_device_info_by_index = get_host_api_info_by_index

        def get_loopback_device_info_generator(self):
            yield {'index': 0}
            if state.failure == 'generator':
                raise OSError('synthetic error after yielding')

    @dataclass
    class Snapshot:
        generation: int = 0

    manager = SimpleNamespace(_device_snapshot=Snapshot())
    dm = SimpleNamespace(PyAudio=FakeAudio, device_manager=manager, errorLogging=lambda: None)

    def update():
        state.updates += 1
        audio = FakeAudio()
        try:
            audio.get_host_api_count()
            list(audio.get_loopback_device_info_generator())
            if state.failure == 'open':
                audio.open()
            if state.failure == 'logged':
                dm.errorLogging()
        except Exception:
            # Like the production speaker path, swallow failures silently.
            pass
        finally:
            audio.terminate()
        if state.changes:
            manager._device_snapshot = Snapshot(state.updates)

    manager.update = update
    pa = SimpleNamespace(PyAudio=FakeAudio, pa=SimpleNamespace(__file__=__file__))
    monkeypatch.setitem(sys.modules, 'pyaudiowpatch', pa)
    monkeypatch.setitem(sys.modules, 'device_manager', dm)
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('audio_capture_tool_test', root / 'tools/check_audio_capture.py')
    module = importlib.util.module_from_spec(spec)
    # Loading the CLI normally prepends src-python. Restore it after this fixture.
    monkeypatch.setattr(sys, 'path', list(sys.path))
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'version', lambda name: 'test')
    originals = {name: getattr(FakeAudio, name) for name in ('open', '__init__', 'terminate',
                                                         'get_host_api_count', 'get_loopback_device_info_generator')}
    yield module, state
    for name, original in originals.items():
        assert getattr(FakeAudio, name) is original


def test_enumeration_measures_without_streams_and_restores_patches(profiler):
    module, state = profiler
    result = module.enumeration()
    assert state.updates == result['repeats'] == 9
    assert len(result['snapshot_sha256']) == 64
    for row in result['trials']:
        assert row['calls']['__init__'] == row['calls']['terminate'] == 1
        assert row['calls']['get_loopback_device_info_generator'] == 1
        assert row['total_ms'] == pytest.approx(row['initialize_ms'] + row['terminate_ms'] + row['other_ms'])
    assert 'native_binary_sha256' not in result


@pytest.mark.parametrize('failure', ['method', 'generator', 'logged', 'open'])
def test_enumeration_rejects_failures_hidden_by_update(profiler, failure):
    module, state = profiler
    state.failure = failure
    with pytest.raises(RuntimeError, match='Device enumeration failed'):
        module.enumeration()


def test_enumeration_rejects_changed_device_snapshot(profiler):
    module, state = profiler
    state.changes = True
    with pytest.raises(RuntimeError, match='snapshot changed'):
        module.enumeration()


@pytest.fixture
def hotplug_tool(monkeypatch):
    """Drive the hotplug steps with fake recorders and scripted Enter presses."""
    state = SimpleNamespace(index=1, unplugged=threading.Event(), hang_stop=False, release=threading.Event(),
                            asked=[])

    class FakeRecorder:
        def __init__(self, device, *args, **kwargs):
            self.source = SimpleNamespace(device_index=device['index'], SAMPLE_RATE=48000, channels=1,
                                          stream=object())
            self.device_error_event = threading.Event()
            self.device_error_info = None
            self.stop = None

        def recordIntoQueue(self, audio, energy):
            stopped = threading.Event()

            def run():
                while not stopped.is_set() and not state.unplugged.is_set():
                    energy.put_nowait(1.0)
                    time.sleep(0.01)
                if state.unplugged.is_set() and not stopped.is_set():
                    self.device_error_info = SimpleNamespace(error_code=SimpleNamespace(value='AUDIO_READ_ERROR'),
                                                             stage='recording', exception_type='OSError')
                    self.device_error_event.set()

            def stop(wait_for_stop=True):
                stopped.set()
                if state.hang_stop:
                    state.release.wait()
                self.source.stream = None

            threading.Thread(target=run, daemon=True).start()
            self.stop = stop

    def devices():
        return {'Host': [{'index': state.index, 'name': 'Headset'}]}

    def update():
        state.index = 3
        state.unplugged.clear()

    manager = SimpleNamespace(getDefaultMicDevice=lambda: {'host': {'name': 'Host'}, 'device': devices()['Host'][0]},
                              getMicDevices=devices, getSpeakerDevices=lambda: [],
                              getDefaultSpeakerDevice=lambda: {'device': {'name': 'NoDevice'}}, update=update)
    recorders = SimpleNamespace(SelectedMicEnergyAndAudioRecorder=FakeRecorder, SelectedMicVadRecorder=FakeRecorder,
                                SelectedSpeakerEnergyAndAudioRecorder=FakeRecorder)
    monkeypatch.setitem(sys.modules, 'pyaudiowpatch', SimpleNamespace())
    monkeypatch.setitem(sys.modules, 'device_manager', SimpleNamespace(device_manager=manager))
    monkeypatch.setitem(sys.modules, 'models.transcription.native_audio',
                        SimpleNamespace(get_native_audio=lambda: object()))
    monkeypatch.setitem(sys.modules, 'models.transcription.transcription_recorder', recorders)
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('audio_capture_hotplug_test', root / 'tools/check_audio_capture.py')
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setattr(sys, 'path', list(sys.path))
    spec.loader.exec_module(module)
    wait_until = module.wait_until
    monkeypatch.setattr(module, 'wait_until', lambda predicate, timeout: wait_until(predicate, min(timeout, 0.3)))

    def ask(step, message, timeout):
        state.asked.append(step)
        if step == 'unplug':
            state.unplugged.set()
        return ''

    monkeypatch.setattr(module, 'ask', ask)
    yield module, state
    state.release.set()


def test_hotplug_records_unplug_stop_and_replug(hotplug_tool):
    module, state = hotplug_tool
    report = module.hotplug()
    assert report['completed'], report
    steps = {row['step']: row for row in report['steps']}
    assert state.asked == ['select', 'endpoint_switch', 'endpoint_restore', 'unplug', 'replug']
    assert steps['endpoint_switch']['probes'][0]['outcome'] == 'data_continued'
    unplug = steps['unplug']
    assert unplug['mic_error_detected']
    assert unplug['probes'][0]['device_error'] == {'code': 'AUDIO_READ_ERROR', 'stage': 'recording',
                                                   'exception_type': 'OSError'}
    assert unplug['probes'][0]['last_data_to_error_ms'] is not None
    assert steps['stop_after_unplug']['results'][0]['returned_within_timeout']
    restart = steps['restart_after_replug']
    assert restart['devices'][0]['source']['requested_index'] == 3
    assert not restart['devices'][0]['fell_back_to_other_device']
    assert restart['probes'][0]['outcome'] == 'data_continued'
    assert 'cleanup' not in report


def test_hotplug_bounds_a_hung_stop(hotplug_tool):
    module, state = hotplug_tool
    state.hang_stop = True
    report = module.hotplug()
    steps = {row['step']: row for row in report['steps']}
    assert steps['stop_after_unplug']['results'][0]['returned_within_timeout'] is False
    assert steps['stop_after_unplug']['results'][0]['stream_closed'] is False
