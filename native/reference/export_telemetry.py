"""テレメトリ (Aptabase への送信と日次の重複除去の状態ファイル) を、今の Python 版のコードで記録する。

    python native/reference/export_telemetry.py   ->  native/testdata/telemetry/telemetry.json

鍵は配布ビルドにしか無いので、偽の鍵 (A-EU-...) を差し込む。日付は "<today>" / "<yesterday>" に置き換え、
送信の timestamp と sessionId は値が毎回変わるので形だけ確かめて "<timestamp>" / "<session>" にする。
"""

import json
import re
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).parent))

from http_capture import capture  # noqa: E402

APP_KEY = "A-EU-0000000000"
state = {"status": 200}


def responder(entry):
    return state["status"], {}, {} if state["status"] == 200 else {"error": "server"}


def normalize(text):
    today, yesterday = date.today().isoformat(), (date.today() - timedelta(days=1)).isoformat()
    return text.replace(today, "<today>").replace(yesterday, "<yesterday>")


def normalize_request(record):
    for event in (record.get("body") or {}).get("json") or []:
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{6})?Z", event["timestamp"]), event["timestamp"]
        assert re.fullmatch(r"\d+", event["sessionId"]), event["sessionId"]
        event["timestamp"], event["sessionId"] = "<timestamp>", "<session>"
    return record


def main():
    import models.telemetry as telemetry_module
    from models.telemetry.client import AptabaseWrapper
    AptabaseWrapper.APP_KEY = APP_KEY
    temp = Path(tempfile.mkdtemp())
    storage = temp / "sub" / "telemetry_state.json"
    steps = []

    def step(label, calls, status=200, before=None):
        """calls: [(method, args...)] on a new Telemetry (one app run)"""
        state["status"] = status
        if before is not None:
            storage.parent.mkdir(parents=True, exist_ok=True)
            storage.write_text(before.replace("<today>", date.today().isoformat()).replace(
                "<yesterday>", (date.today() - timedelta(days=1)).isoformat()), encoding="utf-8")
        telemetry_module.Telemetry._instance = None
        t = telemetry_module.Telemetry()
        with capture(responder) as records:
            for name, *args in calls:
                if name == "init":
                    t.init(enabled=args[0], app_version="3.6.0", storage_path=str(storage))
                elif name == "track_error":
                    t.track_error(args[0])
                elif name == "shutdown":
                    t.shutdown()
        file = normalize(storage.read_text(encoding="utf-8")) if storage.exists() else None
        steps.append({"step": label, "status": status, "before": before, "calls": calls, "state_file": file,
                      "requests": [normalize_request(r) for r in records]})
        print(label, len(records), repr(file)[:120])

    run = [("init", True), ("track_error", "E1"), ("track_error", "E1"), ("track_error", "E2"), ("shutdown",)]
    step("first run", run)
    step("second run same day", [("init", True), ("track_error", "E1"), ("track_error", "E3"), ("shutdown",)])
    step("disabled", [("init", False), ("track_error", "E4"), ("shutdown",)])
    step("enabled later", [("init", False), ("init", True), ("track_error", "E5"), ("shutdown",)])
    step("disabled later", [("init", True), ("init", False), ("track_error", "E6"), ("shutdown",)])
    step("restart in run", [("init", True), ("shutdown",), ("init", True), ("track_error", "E7"), ("shutdown",)])
    step("server error", [("init", True), ("track_error", "E8"), ("shutdown",)], status=500,
         before='{"last_app_started_date": "<yesterday>", "errors_sent": {"<yesterday>": ["E1"]}}')
    step("yesterday", run, before='{"last_app_started_date": "<yesterday>", "errors_sent": {"<yesterday>": ["E1"], "<today>": ["E2"]}}')
    step("corrupt", run, before="{not json")
    step("root not dict", run, before="[1, 2]")
    step("odd values", run, before='{"last_app_started_date": 5, "errors_sent": null, "extra": 1}')
    out = ROOT / "native" / "testdata" / "telemetry" / "telemetry.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"app_key": APP_KEY, "steps": steps}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
