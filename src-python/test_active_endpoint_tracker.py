"""ActiveEndpointTracker のヒステリシス / 選択ロジックおよび
meter cache 管理の単体テスト。

COM/pycaw を触らず、_decide_selected の純粋部分と、_enum_active_devices を
モックで差し替えた _collect_peaks_locked の cache 管理部分を検証する。
"""

import unittest
from unittest.mock import MagicMock, patch

from active_endpoint_tracker import ActiveEndpointTracker, _MeterEntry


def _feed(tracker: ActiveEndpointTracker, peaks: dict, now: float) -> str:
    """1 poll 相当の副作用を _update_history + _decide_selected で再現し、
    決定された endpoint 名を返す (テストヘルパ)。"""
    tracker._update_history(peaks, now)
    selected = tracker._decide_selected(now)
    tracker._current_endpoint_name = selected
    return selected


class TestActiveEndpointTrackerDecision(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = ActiveEndpointTracker("render")

    def test_all_silent_returns_none_initially(self) -> None:
        selected = _feed(self.tracker, {"A": 0.0, "B": 0.0}, now=1.0)
        self.assertIsNone(selected)

    def test_first_active_endpoint_is_picked_immediately(self) -> None:
        selected = _feed(self.tracker, {"A": 0.5, "B": 0.0}, now=1.0)
        self.assertEqual(selected, "A")

    def test_silence_preserves_previous_selection(self) -> None:
        _feed(self.tracker, {"A": 0.5, "B": 0.0}, now=1.0)
        # 3 秒経過して A も B も無音になったが、選択は維持されるはず
        selected = _feed(self.tracker, {"A": 0.0, "B": 0.0}, now=5.0)
        self.assertEqual(selected, "A")

    def test_new_candidate_requires_ratio_and_hold_to_switch(self) -> None:
        # A を選択中 (rolling max=0.2)
        _feed(self.tracker, {"A": 0.2, "B": 0.0}, now=1.0)
        # B が rolling A の 2 倍以上のピークで登場 (SWITCH_RATIO=2.0)
        # 候補にはなるが SWITCH_HOLD_SEC (1.0s) 待たないと切替わらない
        selected = _feed(self.tracker, {"A": 0.1, "B": 0.5}, now=1.1)
        self.assertEqual(selected, "A", "候補観測後すぐは切替わらない")
        # 0.5s 経過、まだ足りない
        selected = _feed(self.tracker, {"A": 0.1, "B": 0.5}, now=1.6)
        self.assertEqual(selected, "A")
        # 1.1s 経過、SWITCH_HOLD_SEC を超えたので切替
        selected = _feed(self.tracker, {"A": 0.1, "B": 0.5}, now=2.2)
        self.assertEqual(selected, "B")

    def test_no_switch_when_ratio_never_met(self) -> None:
        _feed(self.tracker, {"A": 0.5, "B": 0.0}, now=1.0)
        # B は常に A の 2 倍未満 → HOLD 時間を大きく超えても切替らない
        selected = _feed(self.tracker, {"A": 0.5, "B": 0.7}, now=1.1)
        self.assertEqual(selected, "A")
        selected = _feed(self.tracker, {"A": 0.5, "B": 0.8}, now=3.0)
        self.assertEqual(selected, "A")
        selected = _feed(self.tracker, {"A": 0.5, "B": 0.9}, now=5.0)
        self.assertEqual(selected, "A")

    def test_selected_disappears_from_list_falls_to_best(self) -> None:
        _feed(self.tracker, {"A": 0.5, "B": 0.0}, now=1.0)
        # A が消えて B だけになった → ウィンドウ内なら A の履歴が残るので次の poll では A が rolling max 0.5
        # 4 秒後 (WINDOW_SEC=3s 超え) には A の履歴も失効
        selected = _feed(self.tracker, {"B": 0.3}, now=5.0)
        self.assertEqual(selected, "B")


class TestMeterCacheManagement(unittest.TestCase):
    """`_collect_peaks_locked` のキャッシュ管理を検証する。

    以前の実装には「`set(current_ids)` を `(id_str, IMMDevice)` タプルの
    集合として作り、endpoint_id 文字列集合と差集合を取る」型ミスマッチ
    バグがあり、キャッシュが毎 poll 全消しになっていた (=Activate が
    毎回走り、hotfix が実質 no-op になっていた)。このテストは
    「同一 endpoint への 2 回目の poll では新しい Activate が発生しない」
    ことを保証する。
    """

    def _make_device(self, endpoint_id: str, name: str, peak: float) -> MagicMock:
        """IMMDevice ダミー。dev.GetId() / dev.Activate() / meter.GetPeakValue() を
        必要最低限だけ模す。"""
        dev = MagicMock(name=f"IMMDevice[{endpoint_id}]")
        dev.GetId.return_value = endpoint_id
        meter = MagicMock(name=f"meter[{endpoint_id}]")
        meter.GetPeakValue.return_value = peak
        dev._meter_for_test = meter
        dev._friendly_name = name
        return dev

    def _install_stubs(self, tracker: ActiveEndpointTracker, devices: list) -> None:
        """`_enum_active_devices` を devices に、`_MeterEntry` 生成に必要な
        Activate / CreateDevice.FriendlyName / cast をパッチする。"""
        tracker._enum_active_devices = lambda: [(d.GetId(), d) for d in devices]

        def fake_activate(iid, ctx, params):
            # 呼び出された dev は closure で追跡できないので、Activate 引数と
            # dev._meter_for_test の橋渡しは per-device の side_effect で行う。
            raise AssertionError("shouldn't reach top-level fake_activate")

        for d in devices:
            d.Activate.side_effect = lambda iid, ctx, params, meter=d._meter_for_test: meter

    def test_second_poll_reuses_cached_meter(self) -> None:
        """同一 endpoint への 2 回目 poll では Activate 再発行されない。
        これが Phase 4 hotfix の中心的な保証。以前の実装ではキャッシュが
        全消しされ、毎回 Activate が走っていた。"""
        tracker = ActiveEndpointTracker("render")
        dev_a = self._make_device("id_A", "Speaker A", peak=0.5)
        self._install_stubs(tracker, [dev_a])

        with patch(
            "active_endpoint_tracker.AudioUtilities.CreateDevice",
            return_value=MagicMock(FriendlyName="Speaker A"),
        ), patch("active_endpoint_tracker.cast", side_effect=lambda x, _t: x):
            tracker._collect_peaks_locked()
            self.assertEqual(dev_a.Activate.call_count, 1)
            self.assertIn("id_A", tracker._meter_cache)

            tracker._collect_peaks_locked()
            # 2 回目は cache hit — Activate は呼ばれないはず
            self.assertEqual(dev_a.Activate.call_count, 1)

    def test_disappeared_endpoint_dropped_from_cache(self) -> None:
        tracker = ActiveEndpointTracker("render")
        dev_a = self._make_device("id_A", "Speaker A", peak=0.5)
        dev_b = self._make_device("id_B", "Speaker B", peak=0.3)

        with patch(
            "active_endpoint_tracker.AudioUtilities.CreateDevice",
            side_effect=lambda d: MagicMock(FriendlyName=d._friendly_name),
        ), patch("active_endpoint_tracker.cast", side_effect=lambda x, _t: x):
            self._install_stubs(tracker, [dev_a, dev_b])
            tracker._collect_peaks_locked()
            self.assertEqual(set(tracker._meter_cache.keys()), {"id_A", "id_B"})

            # B が消えて A だけになる
            self._install_stubs(tracker, [dev_a])
            tracker._collect_peaks_locked()
            self.assertEqual(set(tracker._meter_cache.keys()), {"id_A"})

    def test_still_present_endpoint_kept_across_polls(self) -> None:
        """id 集合の差集合ロジックが型ミスマッチで壊れると、生存中の
        endpoint まで消える。回帰防止として明示的にチェック。"""
        tracker = ActiveEndpointTracker("render")
        dev_a = self._make_device("id_A", "Speaker A", peak=0.5)

        with patch(
            "active_endpoint_tracker.AudioUtilities.CreateDevice",
            return_value=MagicMock(FriendlyName="Speaker A"),
        ), patch("active_endpoint_tracker.cast", side_effect=lambda x, _t: x):
            self._install_stubs(tracker, [dev_a])
            tracker._collect_peaks_locked()
            entry_first = tracker._meter_cache["id_A"]
            self.assertIsInstance(entry_first, _MeterEntry)

            tracker._collect_peaks_locked()
            entry_second = tracker._meter_cache["id_A"]
            # 全消しバグがあるとキャッシュエントリの identity が変わる
            self.assertIs(entry_first, entry_second)

    def test_getpeakvalue_failure_invalidates_cache_entry(self) -> None:
        tracker = ActiveEndpointTracker("render")
        dev_a = self._make_device("id_A", "Speaker A", peak=0.5)

        with patch(
            "active_endpoint_tracker.AudioUtilities.CreateDevice",
            return_value=MagicMock(FriendlyName="Speaker A"),
        ), patch("active_endpoint_tracker.cast", side_effect=lambda x, _t: x):
            self._install_stubs(tracker, [dev_a])
            tracker._collect_peaks_locked()
            # 次の GetPeakValue で失敗するように差し替え
            dev_a._meter_for_test.GetPeakValue.side_effect = Exception("com fail")
            tracker._collect_peaks_locked()
            # 失敗したエントリは cache から消えている (次回 Activate 再挑戦のため)
            self.assertNotIn("id_A", tracker._meter_cache)


class TestStopTimeout(unittest.TestCase):
    """stop() が時間内にスレッドを止められなかった場合の可視化を検証する。

    tracker が COM 呼び出しで滞留したまま join がタイムアウトすると、
    CoUninitialize されずに COM ポインタだけが GC で破棄され得る
    (access violation につながる経路、実機で確認済み)。完全な防止は
    「スレッドが終わるまで待つ」以外に無いため、せめて診断できるよう
    printLog で警告することを保証する。
    """

    def test_logs_warning_when_thread_does_not_stop_in_time(self) -> None:
        tracker = ActiveEndpointTracker("capture")
        stuck_thread = MagicMock()
        stuck_thread.is_alive.return_value = True
        tracker._thread = stuck_thread

        with patch.object(ActiveEndpointTracker, "STOP_JOIN_TIMEOUT_SEC", 0.01):
            with patch("active_endpoint_tracker.printLog") as mock_print_log:
                tracker.stop()

        stuck_thread.join.assert_called_once_with(timeout=0.01)
        mock_print_log.assert_called_once()
        self.assertIn("timed out", mock_print_log.call_args.args[0])

    def test_no_warning_when_thread_stops_in_time(self) -> None:
        tracker = ActiveEndpointTracker("capture")
        finished_thread = MagicMock()
        finished_thread.is_alive.return_value = False
        tracker._thread = finished_thread

        with patch("active_endpoint_tracker.printLog") as mock_print_log:
            tracker.stop()

        mock_print_log.assert_not_called()


if __name__ == "__main__":
    unittest.main()
