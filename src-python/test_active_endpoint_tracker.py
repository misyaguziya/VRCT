"""ActiveEndpointTracker のヒステリシス / 選択ロジックの単体テスト。

COM/pycaw を触らず、_update_history と _decide_selected の純粋部分だけを
入力ピークで駆動して検証する。
"""

import unittest

from active_endpoint_tracker import ActiveEndpointTracker


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


if __name__ == "__main__":
    unittest.main()
