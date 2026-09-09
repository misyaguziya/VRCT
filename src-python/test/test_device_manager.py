"""DeviceManager のライフサイクル競合と monitoring() の COM 登録方式に
関するテスト (ロードマップ項目 7)。

対象の欠陥 1 (ライフサイクル競合):
  setMicAutoActive/setSpeakerAutoActive は別々のエンドポイント (mainloop の
  ロック) から並行に呼ばれ得るが、DeviceManager 側にはそれを直列化する
  ロックが無かった。結果として:
  - 二重起動: 両方が同時に startMonitoring() に入り、is_alive() が両方
    False のまま monitoring スレッドが 2 本立ち上がりうる。
  - 誤停止: mic 側が _mic_auto_active = True を書く前に speaker 側が
    「両方 inactive」と誤判定して stopMonitoring() してしまいうる。
  - tracker (_startSpeakerEndpointTracker 等) も同じ check-then-act で
    二重起動しうる (マイク側は peak 追従 tracker を起動しないため対象外)。

  修正: _lifecycle_lock を導入し、フラグ更新〜tracker 起動/停止〜
  monitoring 起動/停止判断までを 1 つの原子操作にした。

  テストの注記: 素朴に 2 スレッドを同時に呼ぶだけでは、check-then-act の
  window が狭すぎて (対象の処理が一瞬で終わるため) 偶然パスしてしまう
  ことがある。そのため、レース対象の処理 (monitoring()/tracker の
  start()) を意図的に短時間ブロックさせ、window を確実に広げた状態で
  検証する。

対象の欠陥 2 (monitoring() の COM 登録パターン):
  以前は通知を受けるたびに CoInitialize → RegisterEndpointNotificationCallback
  → UnregisterEndpointNotificationCallback → CoUninitialize を繰り返して
  いた。IMMNotificationClient の標準的な使い方 (スレッド生存中は登録し
  っぱなしにする fire-and-forget) に反しており、同じファイル内の
  ActiveEndpointTracker._run() とも作法が矛盾していた。
  修正: COM 登録はスレッド開始時に 1 回だけ行い、スレッド終了時に 1 回だけ
  後始末するよう変更した。
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import device_manager as device_manager_module
from device_manager import device_manager


class _BlockingTracker:
    """ActiveEndpointTracker の代わりに使うスタブ。

    start() が意図的に少しブロックすることで、
    「_mic_endpoint_tracker is None かどうかの check」と
    「self._mic_endpoint_tracker = tracker の act」の間の競合窓を
    テストで確実に観測できるだけの長さに広げる。
    """

    instances = []
    start_delay_sec = 0.1

    def __init__(self, flow, com_lock=None):
        self.flow = flow
        self.started = False
        self.stopped = False
        _BlockingTracker.instances.append(self)

    def set_on_change_callback(self, cb):
        pass

    def start(self):
        time.sleep(self.start_delay_sec)
        self.started = True

    def stop(self):
        self.stopped = True

    def pause(self):
        pass

    def resume(self):
        pass


class LifecycleLockAutoSelectRaceTests(unittest.TestCase):
    """setMicAutoActive/setSpeakerAutoActive を並行に呼んでも、monitoring
    スレッドと tracker がそれぞれ 1 本ずつしか立たないことを確認する。"""

    def setUp(self) -> None:
        self.dm = device_manager
        # 他のテスト/実行中の状態から独立させるため、確実に停止させておく。
        self.dm._stop_event.set()
        if self.dm.th_monitoring is not None:
            self.dm.th_monitoring.join(timeout=1)
        self.dm._mic_auto_active = False
        self.dm._speaker_auto_active = False
        self.dm._mic_endpoint_tracker = None
        self.dm._speaker_endpoint_tracker = None
        _BlockingTracker.instances.clear()
        _BlockingTracker.start_delay_sec = 0.1

        self._tracker_patch = patch.object(device_manager_module, "ActiveEndpointTracker", _BlockingTracker)
        self._tracker_patch.start()

    def tearDown(self) -> None:
        self._tracker_patch.stop()
        self.dm._stop_event.set()
        self.dm._notify_event.set()
        if self.dm.th_monitoring is not None:
            self.dm.th_monitoring.join(timeout=2)
        self.dm._mic_auto_active = False
        self.dm._speaker_auto_active = False
        self.dm._mic_endpoint_tracker = None
        self.dm._speaker_endpoint_tracker = None

    def test_concurrent_enable_does_not_start_two_monitoring_threads(self) -> None:
        # monitoring() 自体を、is_alive() が競合窓の間ずっと True であり
        # 続けるよう意図的にブロックする実装に差し替える。これにより
        # check-then-act の競合が「2 本のスレッドが同時に存在する」形で
        # 確実に表面化する (ブロックしない実装だと、1 本目がすぐ終わって
        # しまい 2 本目のチェック時には is_alive()==False に見えてしまい、
        # 偶然テストが通ってしまう)。
        block_event = threading.Event()
        created_threads = []
        original_thread_cls = device_manager_module.Thread

        def counting_thread(*args, **kwargs):
            th = original_thread_cls(*args, **kwargs)
            created_threads.append(th)
            return th

        def fake_monitoring(_self):
            block_event.wait(timeout=2)

        with patch.object(device_manager_module.DeviceManager, "monitoring", fake_monitoring), \
             patch.object(device_manager_module, "Thread", counting_thread):

            barrier = threading.Barrier(2, timeout=5)

            def enable_mic():
                barrier.wait()
                self.dm.setMicAutoActive(True)

            def enable_speaker():
                barrier.wait()
                self.dm.setSpeakerAutoActive(True)

            threads = [threading.Thread(target=enable_mic), threading.Thread(target=enable_speaker)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)

            block_event.set()
            for th in created_threads:
                th.join(timeout=2)

        self.assertEqual(
            len(created_threads), 1,
            f"monitoring スレッドが {len(created_threads)} 本作られた (二重起動)",
        )

    def test_enabling_mic_auto_starts_no_endpoint_tracker(self) -> None:
        # マイクの Auto Select は OS 既定デバイス追従のみ。speaker と違い
        # ActiveEndpointTracker (peak 追従) は起動しない
        # (device_manager.setMicAutoActive の docstring 参照)。
        with patch.object(device_manager_module.DeviceManager, "monitoring", lambda self: None):
            self.dm.setMicAutoActive(True)

        self.assertEqual(
            [t for t in _BlockingTracker.instances if t.flow == "capture"],
            [],
            "マイク Auto Select で capture 側 ActiveEndpointTracker が起動した",
        )
        self.assertIsNone(self.dm._mic_endpoint_tracker)
        self.assertTrue(self.dm._mic_auto_active)

    def test_concurrent_enable_starts_speaker_tracker_exactly_once(self) -> None:
        with patch.object(device_manager_module.DeviceManager, "monitoring", lambda self: None):
            barrier = threading.Barrier(2, timeout=5)

            def enable_speaker_a():
                barrier.wait()
                self.dm.setSpeakerAutoActive(True)

            def enable_speaker_b():
                barrier.wait()
                self.dm.setSpeakerAutoActive(True)

            threads = [threading.Thread(target=enable_speaker_a), threading.Thread(target=enable_speaker_b)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)

        started = [t for t in _BlockingTracker.instances if t.started]
        self.assertEqual(len(started), 1, f"speaker tracker が {len(started)} 個起動している (二重起動)")

    def test_disable_one_side_while_other_stays_active_does_not_stop_monitoring(self) -> None:
        with patch.object(device_manager_module.DeviceManager, "monitoring", lambda self: None):
            # 両方 active にしてから、片方だけを無効化する。もう片方が
            # まだ active なので monitoring は止まってはいけない。
            self.dm.setMicAutoActive(True)
            self.dm.setSpeakerAutoActive(True)
            self.assertFalse(self.dm._stop_event.is_set())

            self.dm.setMicAutoActive(False)

            self.assertFalse(
                self.dm._stop_event.is_set(),
                "speaker がまだ active なのに monitoring が止まってしまった",
            )
            self.assertTrue(self.dm._speaker_auto_active)


class MonitoringComRegistrationTests(unittest.TestCase):
    """monitoring() が COM 登録をスレッド開始時に 1 回だけ行い、複数回の
    通知サイクルにわたって使い回すことを確認する。"""

    def setUp(self) -> None:
        self.dm = device_manager
        self.dm._stop_event.set()
        if self.dm.th_monitoring is not None:
            self.dm.th_monitoring.join(timeout=1)
        self._original_timeout = self.dm._MONITOR_WAIT_TIMEOUT_SEC

    def tearDown(self) -> None:
        self.dm._MONITOR_WAIT_TIMEOUT_SEC = self._original_timeout
        self.dm._stop_event.set()
        self.dm._notify_event.set()
        if self.dm.th_monitoring is not None:
            self.dm.th_monitoring.join(timeout=1)

    def test_registers_once_and_survives_multiple_notification_cycles(self) -> None:
        mock_comtypes = MagicMock()
        mock_enumerator = MagicMock()
        mock_audio_utilities = MagicMock()
        mock_audio_utilities.GetDeviceEnumerator.return_value = mock_enumerator

        update_calls = []
        update_called = threading.Event()

        def fake_update():
            update_calls.append(1)
            update_called.set()

        with patch.object(device_manager_module, "comtypes", mock_comtypes), \
             patch.object(device_manager_module, "AudioUtilities", mock_audio_utilities), \
             patch.object(device_manager_module, "Client", MagicMock()), \
             patch.object(self.dm, "update", side_effect=fake_update), \
             patch.object(self.dm, "_applyDeviceDiffs"), \
             patch.object(self.dm, "noticeUpdateDevices"), \
             patch.object(self.dm, "_mic_auto_active", False), \
             patch.object(self.dm, "_speaker_auto_active", False):

            self.dm._stop_event.clear()
            self.dm._notify_event.clear()
            t = threading.Thread(target=self.dm.monitoring, daemon=True)
            t.start()

            for _ in range(3):
                update_called.clear()
                self.dm._notify_event.set()
                self.assertTrue(update_called.wait(timeout=2), "update() が呼ばれなかった")
                self.dm._notify_event.clear()

            self.dm._stop_event.set()
            self.dm._notify_event.set()
            t.join(timeout=2)

        self.assertEqual(len(update_calls), 3)
        # 3 回の通知サイクルを跨いでも、登録関連の呼び出しは 1 回ずつのみ
        # (以前は通知のたびに CoInitialize/Register/Unregister/CoUninitialize
        # を繰り返していた)。
        mock_comtypes.CoInitialize.assert_called_once()
        mock_audio_utilities.GetDeviceEnumerator.assert_called_once()
        mock_enumerator.RegisterEndpointNotificationCallback.assert_called_once()
        mock_enumerator.UnregisterEndpointNotificationCallback.assert_called_once()
        mock_comtypes.CoUninitialize.assert_called_once()

    def test_bare_timeout_does_not_trigger_update_when_com_is_registered(self) -> None:
        # com_registered=True の状態でタイムアウトしても (=通知が来て
        # いない)、update() は呼ばれてはいけない。テストを高速化するため
        # ポーリング間隔を短縮する。
        self.dm._MONITOR_WAIT_TIMEOUT_SEC = 0.05

        mock_comtypes = MagicMock()
        mock_enumerator = MagicMock()
        mock_audio_utilities = MagicMock()
        mock_audio_utilities.GetDeviceEnumerator.return_value = mock_enumerator

        update_calls = []

        with patch.object(device_manager_module, "comtypes", mock_comtypes), \
             patch.object(device_manager_module, "AudioUtilities", mock_audio_utilities), \
             patch.object(device_manager_module, "Client", MagicMock()), \
             patch.object(self.dm, "update", side_effect=lambda: update_calls.append(1)), \
             patch.object(self.dm, "_applyDeviceDiffs"), \
             patch.object(self.dm, "noticeUpdateDevices"):

            self.dm._stop_event.clear()
            self.dm._notify_event.clear()
            t = threading.Thread(target=self.dm.monitoring, daemon=True)
            t.start()

            # ポーリング間隔の 4 倍待っても、一度も通知していないので
            # update() は呼ばれないはず。
            time.sleep(self.dm._MONITOR_WAIT_TIMEOUT_SEC * 4)

            self.dm._stop_event.set()
            self.dm._notify_event.set()
            t.join(timeout=2)

        self.assertEqual(update_calls, [])

    def test_com_unavailable_falls_back_to_polling_every_timeout(self) -> None:
        # comtypes/AudioUtilities が None (非 Windows 等) のときは、
        # 従来どおりタイムアウトのたびに update() が呼ばれる (ポーリング)。
        self.dm._MONITOR_WAIT_TIMEOUT_SEC = 0.05
        update_called = threading.Event()

        with patch.object(device_manager_module, "comtypes", None), \
             patch.object(device_manager_module, "AudioUtilities", None), \
             patch.object(self.dm, "update", side_effect=lambda: update_called.set()), \
             patch.object(self.dm, "_applyDeviceDiffs"), \
             patch.object(self.dm, "noticeUpdateDevices"):

            self.dm._stop_event.clear()
            self.dm._notify_event.clear()
            t = threading.Thread(target=self.dm.monitoring, daemon=True)
            t.start()

            self.assertTrue(update_called.wait(timeout=2), "COM 未登録時にポーリングで update() が呼ばれなかった")

            self.dm._stop_event.set()
            self.dm._notify_event.set()
            t.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
