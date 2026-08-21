"""_AudioDeviceSession.reconfigure(device=...) の差分検知テスト。

Phase 2 で追加した挙動:
- 同一デバイスかつ features 変化なしなら no-op (Recorder を再作成しない)
- device 変化ありなら stop→start 1 回のみ (旧: feature 単位で 2 回)
- device=NoDevice 相当が渡されると None 扱いで停止する
"""
import threading
import unittest
from unittest.mock import patch

import model as model_module
from model import MicSession, SpeakerSession


class _FakeAudioTranscriber:
    last_recognition_error = True

    def __init__(self, *args, **kwargs) -> None:
        pass


class _FakeAudioRecorder:
    """model.py の isinstance() チェックを通しつつ recordIntoQueue 等を no-op 化。"""

    instances = []

    def __init__(self, *args, **kwargs) -> None:
        self.device_error_event = threading.Event()
        self.device_kwarg = kwargs.get("device")
        _FakeAudioRecorder.instances.append(self)

    def recordIntoQueue(self, *args, **kwargs) -> None:
        pass

    def resume(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def stop(self, *args, **kwargs) -> None:
        pass


class _CapturingThreadFnc:
    instances = []

    def __init__(self, fnc, end_fnc=None, daemon=True, *args, **kwargs):
        self.fnc = fnc
        self.end_fnc = end_fnc
        self.daemon = daemon
        _CapturingThreadFnc.instances.append(self)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def join(self, timeout=None) -> None:
        pass

    def is_alive(self) -> bool:
        return False


class TestMicSessionDeviceDiff(unittest.TestCase):
    def setUp(self) -> None:
        _FakeAudioRecorder.instances.clear()
        _CapturingThreadFnc.instances.clear()

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedMicEnergyAndAudioRecorder", _FakeAudioRecorder)
    def test_reconfigure_with_same_device_is_noop(self) -> None:
        session = MicSession()
        session.transcript_fnc = lambda result: None
        device = {"name": "MicA", "index": 3}

        session.reconfigure(transcript=True, device=device)
        self.assertEqual(len(_FakeAudioRecorder.instances), 1)
        self.assertEqual(session._active_device, device)

        # 2 回目は同一 device + 同一 features → no-op (Recorder を作り直さない)
        session.reconfigure(transcript=True, device=device)
        self.assertEqual(len(_FakeAudioRecorder.instances), 1, "同一デバイスなら Recorder は使い回されるべき")

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedMicEnergyAndAudioRecorder", _FakeAudioRecorder)
    def test_reconfigure_with_new_device_swaps_recorder_once(self) -> None:
        session = MicSession()
        session.transcript_fnc = lambda result: None
        device_a = {"name": "MicA", "index": 3}
        device_b = {"name": "MicB", "index": 5}

        session.reconfigure(transcript=True, device=device_a)
        session.reconfigure(transcript=True, device=device_b)

        # 旧実装 (_reopen* が feature 単位で stop→start) では
        # transcript + energy 両方 ON のとき 2 回 open/close が走っていた。
        # 新実装は 1 呼び出しで 1 回のみの想定。
        self.assertEqual(len(_FakeAudioRecorder.instances), 2)
        self.assertEqual(_FakeAudioRecorder.instances[-1].device_kwarg, device_b)
        self.assertEqual(session._active_device, device_b)

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedMicEnergyAndAudioRecorder", _FakeAudioRecorder)
    def test_reconfigure_no_device_stops_session(self) -> None:
        session = MicSession()
        session.transcript_fnc = lambda result: None
        session.reconfigure(transcript=True, device={"name": "MicA", "index": 3})
        self.assertIsNotNone(session._active_device)

        # NoDevice が明示的に渡された場合はセッション停止
        session.reconfigure(transcript=True, device={"name": "NoDevice", "index": -1})
        self.assertIsNone(session._active_device)
        self.assertEqual(session.features, set())


class TestSpeakerSessionDeviceDiff(unittest.TestCase):
    def setUp(self) -> None:
        _FakeAudioRecorder.instances.clear()
        _CapturingThreadFnc.instances.clear()

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedSpeakerEnergyAndAudioRecorder", _FakeAudioRecorder)
    def test_reconfigure_with_same_device_is_noop(self) -> None:
        session = SpeakerSession()
        session.transcript_fnc = lambda result: None
        device = {"name": "SpeakerA", "index": 8}

        session.reconfigure(transcript=True, device=device)
        session.reconfigure(transcript=True, device=device)
        self.assertEqual(len(_FakeAudioRecorder.instances), 1)


if __name__ == "__main__":
    unittest.main()
