"""Offline checks for the manual enumeration profiler, using no audio devices."""

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
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
