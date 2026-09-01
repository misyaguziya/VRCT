"""_AudioDeviceSession._start() の失敗時ロールバックに関するテスト (P0-2 の回帰防止)。

対象の欠陥:
  reconfigure() は self.features = new_features を _start() の前に確定させ、
  _start() は self._recorder = self._create_recorder(device) の成功後に
  self._recorder.recordIntoQueue(...) を呼ぶ。ここでデバイスが処理中に
  消える等で例外が起きると (実機の error.log に
  `OSError: device gone` @ transcription_recorder.py:218 recordIntoQueue
  として記録済み)、self._recorder は非 None のまま、self.features も
  新しい値のまま残っていた。

  結果として:
  - 次の reconfigure(transcript=True) は
    already_running = self._recorder is not None が真になり no-op で
    早期 return する → ユーザーが文字起こしを OFF→ON しても永久に復帰しない。
  - reconfigure(transcript=False) は _stop() の self._recorder.resume() /
    .stop() が (recordIntoQueue が listener を起動する前に失敗したため
    まだ None のままの) None を呼び出そうとして TypeError になる。

  この 2 つのシナリオが実際に修正されていることを、model.py の実クラス
  (MicSession) を使って end-to-end で検証する。
"""

import threading
import unittest
from unittest.mock import patch

import model as model_module
from model import MicSession


class _RealisticAudioRecorder:
    """transcription_recorder.Recorder の失敗/成功セマンティクスを忠実に模す。

    resume/pause/stop は listen_energy_and_audio_in_background() (=
    recordIntoQueue 内部) が成功するまで None のまま
    (transcription_recorder.py:171-173, 261-263 と同じ)。
    test_model_session_reconfigure.py の _FakeAudioRecorder は簡略化のため
    最初から bound method を持たせているため、この P0-2 の再現には使えない。
    """

    instances = []
    should_fail = False

    def __init__(self, *args, **kwargs) -> None:
        self.device_error_event = threading.Event()
        self.device_kwarg = kwargs.get("device")
        self.resume = None
        self.pause = None
        self.stop = None
        _RealisticAudioRecorder.instances.append(self)

    def recordIntoQueue(self, *args, **kwargs) -> None:
        if _RealisticAudioRecorder.should_fail:
            raise OSError("device gone")
        self.resume = lambda: None
        self.pause = lambda: None
        self.stop = lambda *a, **k: None


class _FakeAudioTranscriber:
    last_recognition_error = True

    def __init__(self, *args, **kwargs) -> None:
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


DEVICE = {"name": "MicA", "index": 3}


class StartFailureRollbackTests(unittest.TestCase):
    def setUp(self) -> None:
        _RealisticAudioRecorder.instances.clear()
        _RealisticAudioRecorder.should_fail = False
        _CapturingThreadFnc.instances.clear()

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedMicEnergyAndAudioRecorder", _RealisticAudioRecorder)
    def test_failed_start_rolls_back_recorder_features_and_device(self) -> None:
        session = MicSession()
        session.transcript_fnc = lambda result: None
        _RealisticAudioRecorder.should_fail = True

        with self.assertRaises(OSError):
            session.reconfigure(transcript=True, device=DEVICE)

        self.assertIsNone(session._recorder)
        self.assertEqual(session.features, set())
        self.assertIsNone(session._active_device)
        self.assertIsNone(session._transcriber)
        self.assertIsNone(session._audio_queue)

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedMicEnergyAndAudioRecorder", _RealisticAudioRecorder)
    def test_recovers_on_the_next_reconfigure_after_a_transient_failure(self) -> None:
        # これが本来のバグシナリオそのもの: 1 回目は失敗するが、デバイスが
        # 復帰した後の 2 回目の reconfigure(transcript=True) は
        # (修正前は already_running 誤判定で) no-op にならず、実際に
        # Recorder を起動しなければならない。
        session = MicSession()
        session.transcript_fnc = lambda result: None

        _RealisticAudioRecorder.should_fail = True
        with self.assertRaises(OSError):
            session.reconfigure(transcript=True, device=DEVICE)

        _RealisticAudioRecorder.should_fail = False
        session.reconfigure(transcript=True, device=DEVICE)  # 例外を出さずに成功するはず

        # 「壊れた Recorder がロールバックされず使い回されている」だけでも
        # features/_active_device の値自体は偶然一致してしまう (同じ device・
        # 同じ features を再要求しているため) ので、それだけでは検証にならない。
        # listener が実際に起動できたか (.stop がまだ None のままではないか)
        # を直接確認する。
        self.assertIsNotNone(session._recorder)
        self.assertIsNotNone(
            session._recorder.stop,
            "listener が実際には起動していない (壊れた Recorder が使い回されている疑い)",
        )
        self.assertEqual(session.features, {"transcript"})
        self.assertEqual(session._active_device, DEVICE)

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedMicEnergyAndAudioRecorder", _RealisticAudioRecorder)
    def test_turning_off_after_a_failed_start_does_not_raise(self) -> None:
        # 修正前は _stop() の self._recorder.resume()/.stop() が (listener
        # 起動前に失敗した Recorder の) None を呼び出して TypeError になり、
        # OFF 操作自体が失敗していた。
        session = MicSession()
        session.transcript_fnc = lambda result: None
        _RealisticAudioRecorder.should_fail = True
        with self.assertRaises(OSError):
            session.reconfigure(transcript=True, device=DEVICE)

        try:
            session.reconfigure(transcript=False, device=DEVICE)
        except TypeError:
            self.fail("reconfigure(transcript=False) raised TypeError after a failed start")

        self.assertEqual(session.features, set())


class StopAndPauseResumeGuardTests(unittest.TestCase):
    """_start() のロールバックとは独立に、_stop()/pause()/resume() 自体が
    resume/pause/stop がまだ None の Recorder を渡されても壊れないことを
    確認する (防御的な二重の安全策)。"""

    def setUp(self) -> None:
        _RealisticAudioRecorder.instances.clear()
        _RealisticAudioRecorder.should_fail = False

    def _session_with_uninitialized_recorder(self) -> MicSession:
        session = MicSession()
        # recordIntoQueue を経ていない (listener 未起動の) Recorder を
        # 直接差し込む。実運用では _start() のロールバックにより通常
        # 到達しない状態だが、防御コードそのものを単体で検証する。
        session._recorder = _RealisticAudioRecorder(device=DEVICE)
        return session

    def test_stop_does_not_raise_when_recorder_callables_are_none(self) -> None:
        session = self._session_with_uninitialized_recorder()
        try:
            session._stop()
        except TypeError:
            self.fail("_stop() raised TypeError on an uninitialized Recorder")
        self.assertIsNone(session._recorder)

    def test_pause_does_not_raise_when_recorder_callable_is_none(self) -> None:
        session = self._session_with_uninitialized_recorder()
        try:
            session.pause()
        except TypeError:
            self.fail("pause() raised TypeError on an uninitialized Recorder")

    def test_resume_does_not_raise_when_recorder_callable_is_none(self) -> None:
        session = self._session_with_uninitialized_recorder()
        try:
            session.resume()
        except TypeError:
            self.fail("resume() raised TypeError on an uninitialized Recorder")


if __name__ == "__main__":
    unittest.main()
