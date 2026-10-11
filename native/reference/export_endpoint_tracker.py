"""音が出ている出力デバイスの判定 (active_endpoint_tracker.ActiveEndpointTracker の _update_history /
_decide_selected) を、今の Python 版で記録する。

    python native/reference/export_endpoint_tracker.py   ->  native/testdata/audio/endpoint_tracker.json

COM には触らない。決まった乱数でピークの列 (0.25 秒ごと) を作って流し、各回の選択を書く。
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src-python"))

NAMES = ["Speakers (A)", "Headset (B)", "Monitor (C)"]


def peak(rng, level):
    return 0.0 if level == 0 else max(0.0, min(1.0, rng.gauss(level, level / 4)))


def main():
    from active_endpoint_tracker import ActiveEndpointTracker
    rng = random.Random(20261012)
    scenarios = []
    for n in range(60):
        tracker = ActiveEndpointTracker("render", com_lock=None)
        now = 1000.0 + rng.random()
        polls = []
        levels = {name: rng.choice([0, 0, 0.0005, 0.01, 0.2, 0.6]) for name in NAMES}
        for i in range(rng.randint(10, 120)):
            if rng.random() < 0.08:  # a device starts / stops playing, or goes away
                name = rng.choice(NAMES)
                levels[name] = rng.choice([0, 0.0005, 0.002, 0.05, 0.3, 0.9, None])
            peaks = {name: peak(rng, level) for name, level in levels.items() if level is not None}
            now += 0.25 + rng.choice([0, 0, 0.01, 0.3, 1.2])
            tracker._update_history(peaks, now)
            selected = tracker._decide_selected(now)
            tracker._current_endpoint_name = selected
            polls.append({"now": now, "peaks": peaks, "selected": selected})
        scenarios.append(polls)
    out = ROOT / "native" / "testdata" / "audio" / "endpoint_tracker.json"
    out.write_text(json.dumps({"scenarios": scenarios}), encoding="utf-8")
    print(out, sum(len(s) for s in scenarios), "polls")


if __name__ == "__main__":
    main()
