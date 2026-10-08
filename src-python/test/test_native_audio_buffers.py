"""Immutable Python input lifetimes across the native GIL-release boundary."""

from concurrent.futures import ThreadPoolExecutor
import gc
import sys
import threading

import pytest


@pytest.fixture
def native():
    return pytest.importorskip("vrct_audio", reason="Build native/vrct-audio to run native contracts")


CASES = [
    ("encode_flac", (16000,), b"\x01\0"),
    ("downmix_pcm16", (2,), b"\x01\0\x03\0"),
    ("speaker_downmix_pcm16", (3,), b"\x03\0\x06\0\x09\0"),
    ("normalize_pcm16", (3, 2), b"\0\x01\0\0\x03\0"),
]


@pytest.mark.parametrize("name,args,frame", CASES)
@pytest.mark.parametrize("kind", [bytearray, memoryview])
def test_mutable_or_buffer_inputs_still_rejected(native, name, args, frame, kind):
    with pytest.raises(TypeError):
        getattr(native, name)(kind(frame), *args)


@pytest.mark.parametrize("name,args,frame", CASES)
def test_temporary_bytes_subclass_preserves_value_and_exact_output_type(native, name, args, frame):
    class Input(bytes):
        pass

    function = getattr(native, name)
    expected = function(frame * 4096, *args)
    result = function(Input(frame * 4096), *args)
    assert type(result) is bytes
    assert result == expected


@pytest.mark.parametrize("name,args,frame", CASES)
def test_shared_immutable_input_can_be_processed_concurrently(native, name, args, frame):
    pcm = frame * 16384
    original = bytes(bytearray(pcm))
    function = getattr(native, name)
    expected = function(pcm, *args)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: function(pcm, *args), range(12)))
    assert all(result == expected for result in results)
    assert pcm == original


@pytest.mark.parametrize("name,args,frame", CASES)
def test_call_retains_input_when_other_thread_drops_last_external_reference(native, name, args, frame):
    # The OS may not schedule the observer within the few-ms GIL release; such a
    # run proves nothing either way, so retry instead of failing on scheduling luck.
    for _ in range(5):
        if _drop_reference_during_call(native, name, args, frame):
            return
    pytest.fail("observer never ran while the native call released the GIL")


def _drop_reference_during_call(native, name, args, frame):
    ready = threading.Event()
    run = threading.Event()
    destroyed = threading.Event()
    observed = []

    class Input(bytes):
        def __del__(self):
            destroyed.set()

    # No local variable owns this object except the holder. The native call's
    # argument must retain it after the observer clears that external reference.
    holder = [Input(frame * (1024 * 1024))]
    function = getattr(native, name)
    expected = function(bytes(holder[0]), *args)

    def observer():
        ready.set()
        run.wait()
        holder.clear()
        gc.collect()
        observed.append(not destroyed.is_set())

    thread = threading.Thread(target=observer)
    thread.start()
    interval = sys.getswitchinterval()
    try:
        assert ready.wait(5)
        # Prevent a Python scheduler switch between run.set() and the native
        # call. Observer progress inside the call requires its GIL release.
        sys.setswitchinterval(10)
        run.set()
        result = function(holder[0], *args)
        progressed_during_call = bool(observed)
    finally:
        sys.setswitchinterval(interval)
        run.set()
        thread.join(5)
    assert not thread.is_alive()
    assert result == expected
    if not progressed_during_call:
        return False  # The observer only ran after the call: inconclusive.
    assert observed == [True]
    assert destroyed.is_set()
    return True
