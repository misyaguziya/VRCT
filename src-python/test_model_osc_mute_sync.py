"""OSC ミュート同期 (changeHandlerMute) の直列化に関するテスト
(ロードマップ項目 6)。

対象の欠陥:
  ThreadingOSCUDPServer は受信メッセージごとに新しいスレッドを起こすため、
  changeHandlerMute (model.py: startReceiveOSC 内) は
  mic_lifecycle_lock を一切持たない任意のスレッドで走っていた。
  Auto Mic Select のデバイス切替や mainloop ワーカーが直接呼ぶ start/stop 系
  (audio_lifecycle_worker 経由/直接ロック経由いずれも _stop()/_start() を
  実行しうる) とミュート連打による pause()/resume() が無ロックで交錯すると、
  壊れた Recorder に触れて例外になったり、resume() が新しい _audio_queue を
  drain して録音済み音声を取りこぼす。

  修正 (2 段階):
  1. changeHandlerMute は self.changeMicTranscriptStatus() をインラインで
     呼ぶのではなく、Auto Select の他のデバイス操作と同じ
     audio_lifecycle_worker の FIFO キューに投げて直列実行させる。
  2. 実行される関数自体を mic_mute_status_change_callback
     (= Controller.__init__ が登録する mic_lifecycle_lock 付きラッパー
     _changeMicTranscriptStatusLocked) にすることで、ロックを直接
     取得する経路 (mainloop ワーカーが直接呼ぶ startTranscriptionSendMessage
     等) とも完全に排他制御する。未登録時は changeMicTranscriptStatus() に
     フォールバックする (Model が Controller を知らないままでも壊れない)。
"""

import threading
import unittest
from unittest.mock import MagicMock, patch

import config as config_module
from controller import Controller
from model import Model


class OscMuteHandlerRoutesThroughWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        # Model はプロセス全体で共有されるシングルトン。他のテストが既に
        # init() 済みかもしれないので、実属性を保存してから上書きし、
        # tearDown で必ず元に戻す。
        self.model = Model.__new__(Model)
        self._had_inited = hasattr(self.model, "_inited")
        self._original_inited = getattr(self.model, "_inited", None)
        self._had_mute_status = hasattr(self.model, "mic_mute_status")
        self._original_mute_status = getattr(self.model, "mic_mute_status", None)
        self._had_mic_session = hasattr(self.model, "_mic_session")
        self._original_mic_session = getattr(self.model, "_mic_session", None)
        self._had_worker = hasattr(self.model, "audio_lifecycle_worker")
        self._original_worker = getattr(self.model, "audio_lifecycle_worker", None)
        self._had_osc_handler = hasattr(self.model, "osc_handler")
        self._original_osc_handler = getattr(self.model, "osc_handler", None)
        self._had_mute_callback = hasattr(self.model, "mic_mute_status_change_callback")
        self._original_mute_callback = getattr(self.model, "mic_mute_status_change_callback", None)

        self.model._inited = True  # ensure_initialized() の実init発火を防ぐ
        self.model.mic_mute_status = False
        self.model._mic_session = MagicMock()
        self.enqueued = []
        self.model.audio_lifecycle_worker = MagicMock()
        self.model.audio_lifecycle_worker.enqueue.side_effect = lambda fn: self.enqueued.append(fn)
        self.model.osc_handler = MagicMock()
        self.model.osc_handler.osc_parameter_muteself = "/avatar/parameters/MuteSelf"
        # デフォルトは未登録 (フォールバック経路) を検証する。登録済みの
        # 場合の挙動は別のテストクラスで検証する。
        self.model.mic_mute_status_change_callback = None

        self._original_mute_sync = config_module.config.VRC_MIC_MUTE_SYNC
        config_module.config.VRC_MIC_MUTE_SYNC = True

    def tearDown(self) -> None:
        config_module.config.VRC_MIC_MUTE_SYNC = self._original_mute_sync
        for attr, had, original in (
            ("_inited", self._had_inited, self._original_inited),
            ("mic_mute_status", self._had_mute_status, self._original_mute_status),
            ("_mic_session", self._had_mic_session, self._original_mic_session),
            ("audio_lifecycle_worker", self._had_worker, self._original_worker),
            ("osc_handler", self._had_osc_handler, self._original_osc_handler),
            ("mic_mute_status_change_callback", self._had_mute_callback, self._original_mute_callback),
        ):
            if had:
                setattr(self.model, attr, original)
            else:
                try:
                    delattr(self.model, attr)
                except AttributeError:
                    pass

    def _get_registered_mute_callback(self):
        self.model.startReceiveOSC()
        (dict_filter_and_target,), _ = self.model.osc_handler.setDictFilterAndTarget.call_args
        return dict_filter_and_target[self.model.osc_handler.osc_parameter_muteself]

    def test_mute_true_enqueues_instead_of_calling_pause_inline(self) -> None:
        callback = self._get_registered_mute_callback()
        callback(address="/x", osc_arguments=True)

        self.assertEqual(len(self.enqueued), 1)
        self.assertEqual(self.enqueued[0], self.model.changeMicTranscriptStatus)
        # OSC スレッド上でインラインには呼ばれていないこと。
        self.model._mic_session.pause.assert_not_called()

    def test_mute_false_enqueues_instead_of_calling_resume_inline(self) -> None:
        self.model.mic_mute_status = True
        callback = self._get_registered_mute_callback()
        callback(address="/x", osc_arguments=False)

        self.assertEqual(len(self.enqueued), 1)
        self.model._mic_session.resume.assert_not_called()

    def test_enqueued_function_performs_pause_when_actually_run(self) -> None:
        callback = self._get_registered_mute_callback()
        callback(address="/x", osc_arguments=True)

        # ワーカースレッドがキューから取り出して実行した場合の効果を検証する。
        self.enqueued[0]()
        self.model._mic_session.pause.assert_called_once()

    def test_enqueued_function_performs_resume_when_actually_run(self) -> None:
        self.model.mic_mute_status = True
        callback = self._get_registered_mute_callback()
        callback(address="/x", osc_arguments=False)

        self.enqueued[0]()
        self.model._mic_session.resume.assert_called_once()

    def test_duplicate_mute_state_does_not_enqueue(self) -> None:
        self.model.mic_mute_status = True
        callback = self._get_registered_mute_callback()
        callback(address="/x", osc_arguments=True)  # 既に True なので変化なし
        self.assertEqual(self.enqueued, [])

    def test_sync_disabled_does_not_enqueue(self) -> None:
        config_module.config.VRC_MIC_MUTE_SYNC = False
        callback = self._get_registered_mute_callback()
        callback(address="/x", osc_arguments=True)
        self.assertEqual(self.enqueued, [])

    def test_registered_callback_is_enqueued_instead_of_the_unlocked_fallback(self) -> None:
        # Controller.__init__ が setMicMuteStatusChangeCallback() で
        # 自身の mic_lifecycle_lock 付きラッパーを登録した状態を模す。
        locked_wrapper = MagicMock(name="_changeMicTranscriptStatusLocked")
        self.model.mic_mute_status_change_callback = locked_wrapper

        callback = self._get_registered_mute_callback()
        callback(address="/x", osc_arguments=True)

        self.assertEqual(self.enqueued, [locked_wrapper])
        # フォールバックの changeMicTranscriptStatus ではなく、登録された
        # ロック付きラッパーが使われていること。
        self.assertNotIn(self.model.changeMicTranscriptStatus, self.enqueued)


class ControllerRegistersLockedMuteCallbackTests(unittest.TestCase):
    """Controller が起動時に mic_lifecycle_lock 付きラッパーを Model へ
    登録し、そのラッパー自体が実際にロックを取得することを確認する。"""

    @patch("controller.model")
    def test_init_registers_the_locked_wrapper_with_model(self, mock_model) -> None:
        # controller.model をまるごとモックしているため、model.init() を
        # 含む __init__ 全体を実行しても実デバイス/実ネットワークには
        # 一切触れない。
        controller = Controller()
        mock_model.setMicMuteStatusChangeCallback.assert_called_once_with(
            controller._changeMicTranscriptStatusLocked
        )

    def test_locked_wrapper_acquires_the_lock_around_change_mic_transcript_status(self) -> None:
        controller = Controller.__new__(Controller)
        controller.mic_lifecycle_lock = threading.Lock()
        lock = controller.mic_lifecycle_lock
        observed_locked = []

        with patch("controller.model") as mock_model:
            mock_model.changeMicTranscriptStatus.side_effect = lambda: observed_locked.append(lock.locked())
            controller._changeMicTranscriptStatusLocked()

        self.assertEqual(observed_locked, [True])
        self.assertFalse(lock.locked())


if __name__ == "__main__":
    unittest.main()
