"""テレメトリの日次デデュープと送信ロジックのテスト。

Aptabase への実通信は core.send_event をモックして抑止する。
`.venv` に pytest が入っていなくても `python -m unittest test_telemetry` で動くよう unittest で書いている。
"""

import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from models.telemetry.state import TelemetryState
from models.telemetry import Telemetry


class TelemetryStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "telemetry_state.json")

    def test_initializes_from_missing_file(self):
        state = TelemetryState(storage_path=self.path)
        self.assertTrue(state.should_send_app_started_today())
        self.assertTrue(state.should_send_error_today("X"))

    def test_initializes_from_corrupt_file(self):
        with open(self.path, "w", encoding="utf-8") as fp:
            fp.write("not json {{{")
        state = TelemetryState(storage_path=self.path)
        self.assertTrue(state.should_send_app_started_today())

    def test_app_started_dedupe_same_day(self):
        state = TelemetryState(storage_path=self.path)
        self.assertTrue(state.should_send_app_started_today())
        state.mark_app_started_sent_today()
        self.assertFalse(state.should_send_app_started_today())

        # 新しい state インスタンスからロードしても永続されている
        state2 = TelemetryState(storage_path=self.path)
        self.assertFalse(state2.should_send_app_started_today())

    def test_app_started_resends_next_day(self):
        state = TelemetryState(storage_path=self.path)
        state.mark_app_started_sent_today()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        # ファイルを直接書き換えて前日にする
        with open(self.path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        data["last_app_started_date"] = yesterday
        with open(self.path, "w", encoding="utf-8") as fp:
            json.dump(data, fp)

        state2 = TelemetryState(storage_path=self.path)
        self.assertTrue(state2.should_send_app_started_today())

    def test_error_dedupe_per_code_per_day(self):
        state = TelemetryState(storage_path=self.path)
        self.assertTrue(state.should_send_error_today("AUTH_DEEPL_FAILED"))
        state.mark_error_sent_today("AUTH_DEEPL_FAILED")
        self.assertFalse(state.should_send_error_today("AUTH_DEEPL_FAILED"))
        # 別コードは影響を受けない
        self.assertTrue(state.should_send_error_today("DEVICE_NO_MIC"))

    def test_error_dedupe_persists(self):
        state = TelemetryState(storage_path=self.path)
        state.mark_error_sent_today("DEVICE_NO_MIC")

        state2 = TelemetryState(storage_path=self.path)
        self.assertFalse(state2.should_send_error_today("DEVICE_NO_MIC"))

    def test_prunes_old_error_entries_on_write(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        seed = {
            "last_app_started_date": None,
            "errors_sent": {yesterday: ["OLD_CODE"]},
        }
        with open(self.path, "w", encoding="utf-8") as fp:
            json.dump(seed, fp)

        state = TelemetryState(storage_path=self.path)
        state.mark_error_sent_today("NEW_CODE")

        with open(self.path, "r", encoding="utf-8") as fp:
            saved = json.load(fp)
        self.assertNotIn(yesterday, saved["errors_sent"])
        self.assertIn(date.today().isoformat(), saved["errors_sent"])

    def test_empty_error_code_is_noop(self):
        state = TelemetryState(storage_path=self.path)
        self.assertFalse(state.should_send_error_today(""))
        state.mark_error_sent_today("")  # 例外なく無視


class TelemetryFacadeTests(unittest.TestCase):
    """Telemetry シングルトンの挙動。Aptabase 送信部分は完全にモックする。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "telemetry_state.json")

        # シングルトンをリセット（テスト間の隔離）
        Telemetry._instance = None

        # Aptabase 通信は完全に無効化
        self._patchers = [
            patch("models.telemetry.core.TelemetryCore.start", side_effect=self._async_noop),
            patch("models.telemetry.core.TelemetryCore.stop", side_effect=self._async_noop),
        ]
        for p in self._patchers:
            p.start()
            self.addCleanup(p.stop)

    @staticmethod
    async def _async_noop(*args, **kwargs):
        return None

    def _new_telemetry_with_captured_events(self):
        telemetry = Telemetry()
        events = []

        async def capture(event_name, payload=None):
            events.append((event_name, payload or {}))

        # send_event を差し替え
        patcher = patch.object(telemetry.core, "send_event", side_effect=capture)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(telemetry.shutdown)
        return telemetry, events

    def test_app_started_sent_once_across_double_init(self):
        telemetry, events = self._new_telemetry_with_captured_events()
        telemetry.init(enabled=True, storage_path=self.path)
        telemetry.init(enabled=True, storage_path=self.path)  # 冪等

        # イベントループに送信タスクが載っているので同期的に完了するまで待つ
        import time
        for _ in range(20):
            if any(e[0] == "app_started" for e in events):
                break
            time.sleep(0.05)

        app_started_events = [e for e in events if e[0] == "app_started"]
        self.assertEqual(len(app_started_events), 1)

    def test_second_process_same_day_does_not_resend_app_started(self):
        telemetry, events = self._new_telemetry_with_captured_events()
        telemetry.init(enabled=True, storage_path=self.path)
        import time
        time.sleep(0.2)
        telemetry.shutdown()

        # 新しいプロセスを模して singleton を作り直す
        Telemetry._instance = None
        telemetry2, events2 = self._new_telemetry_with_captured_events()
        telemetry2.init(enabled=True, storage_path=self.path)
        time.sleep(0.2)

        self.assertFalse(any(e[0] == "app_started" for e in events2))

    def test_track_error_dedupes_same_code_same_day(self):
        telemetry, events = self._new_telemetry_with_captured_events()
        telemetry.init(enabled=True, storage_path=self.path)
        telemetry.track_error("AUTH_DEEPL_FAILED")
        telemetry.track_error("AUTH_DEEPL_FAILED")
        telemetry.track_error("DEVICE_NO_MIC")

        import time
        time.sleep(0.3)

        error_events = [e for e in events if e[0] == "error"]
        codes = [e[1]["error_code"] for e in error_events]
        self.assertEqual(sorted(codes), ["AUTH_DEEPL_FAILED", "DEVICE_NO_MIC"])

    def test_disabled_sends_nothing(self):
        telemetry, events = self._new_telemetry_with_captured_events()
        telemetry.init(enabled=False, storage_path=self.path)
        telemetry.track_error("DEVICE_NO_MIC")

        import time
        time.sleep(0.1)
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
