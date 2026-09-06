"""audio_queue の有界化に関するテスト (フェーズ3項目20)。

対象の欠陥: `_AudioDeviceSession._start()` が作る audio_queue に maxsize が
無く、文字起こしが実時間に追いつけない (例: CPUでWhisper large-v3) 状況で
無制限に溜まり続けていた。drain 時に last_sample がまとめて連結されて
音声が長くなり、推論がさらに遅くなってもっと溜まる、という正の
フィードバックループになりうる (last_sample 側の上限は
test_transcription_transcriber.py で別途検証)。
"""

import threading
import unittest
from queue import Queue
from unittest.mock import patch

import model as model_module
from model import MicSession
from config import config


class _FakeAudioTranscriber:
    last_recognition_error = True

    def __init__(self, *args, **kwargs) -> None:
        pass


class _FakeAudioRecorder:
    """model.py の isinstance() チェックを通しつつ、recordIntoQueue に
    渡された audio_queue を検査できるように捕捉する。"""

    instances = []

    def __init__(self, *args, **kwargs) -> None:
        self.device_error_event = threading.Event()
        self.captured_audio_queue = None
        self.captured_energy_queue = None
        _FakeAudioRecorder.instances.append(self)

    def recordIntoQueue(self, audio_queue, energy_queue=None) -> None:
        self.captured_audio_queue = audio_queue
        self.captured_energy_queue = energy_queue

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


class TestAudioQueueIsBounded(unittest.TestCase):
    def setUp(self) -> None:
        _FakeAudioRecorder.instances.clear()
        _CapturingThreadFnc.instances.clear()
        # このテストは _create_recorder() がエネルギー閾値方式の
        # Recorder を作ることを前提に @patch("model.SelectedMic...") して
        # いる。config.json 側で ENABLE_VAD=true になっていると
        # SelectedMicVadRecorder (未パッチの実クラス) が代わりに作られて
        # しまい、フェイクが一切呼ばれなくなる。ここでは常に False に
        # 固定してこのテストの前提を守る。
        self._original_enable_vad = config.ENABLE_VAD
        config.ENABLE_VAD = False

    def tearDown(self) -> None:
        config.ENABLE_VAD = self._original_enable_vad

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedMicEnergyAndAudioRecorder", _FakeAudioRecorder)
    def test_transcript_session_uses_a_bounded_queue(self) -> None:
        session = MicSession()
        session.transcript_fnc = lambda result: None

        session.reconfigure(transcript=True, device={"name": "MicA", "index": 3})

        audio_queue = _FakeAudioRecorder.instances[-1].captured_audio_queue
        self.assertIsInstance(audio_queue, Queue)
        self.assertEqual(audio_queue.maxsize, model_module._AUDIO_QUEUE_MAXSIZE)
        self.assertGreater(model_module._AUDIO_QUEUE_MAXSIZE, 0, "0 は無制限 (Queue()) と同義になってしまう")

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedMicEnergyAndAudioRecorder", _FakeAudioRecorder)
    def test_energy_session_uses_a_bounded_queue(self) -> None:
        """energy_queue はメーター表示用で直近の値のみ意味を持つため、
        audio_queue と同じ理由 (レビュー指摘) で有界化されているはず。"""
        session = MicSession()
        session.transcript_fnc = lambda result: None

        session.reconfigure(transcript=True, energy=True, device={"name": "MicA", "index": 3})

        energy_queue = _FakeAudioRecorder.instances[-1].captured_energy_queue
        self.assertIsInstance(energy_queue, Queue)
        self.assertEqual(energy_queue.maxsize, 1)


if __name__ == "__main__":
    unittest.main()
