"""オーバーレイの位置の行列 (overlay.getBaseMatrix / 追従先ごとの基準 / overlay_utils.transform_matrix) を、
今の Python 版で記録する。

    python native/reference/export_overlay_math.py   ->  native/testdata/overlay/math.json

Overlay.updatePosition が SteamVR に渡す 3x4 と同じ計算 (追従先の基準に、設定の移動 (x, y, -z) と回転)。
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src-python"))
sys.path.insert(0, str(ROOT / "src-python" / "models" / "overlay"))


def main():
    import overlay_utils as utils
    import overlay
    rng = random.Random(20261012)
    bases = {"HMD": overlay.getHMDBaseMatrix(), "LeftHand": overlay.getLeftHandBaseMatrix(),
             "RightHand": overlay.getRightHandBaseMatrix()}
    cases = []
    for i in range(300):
        tracker = rng.choice(["HMD", "LeftHand", "RightHand", "Playspace"])
        x, y, z = (rng.choice([0.0, rng.uniform(-1, 1)]) for _ in range(3))
        rx, ry, rz = (rng.choice([0.0, 90.0, -45.0, rng.uniform(-180, 180)]) for _ in range(3))
        if tracker == "Playspace":
            import numpy as np
            base = np.hstack([np.eye(3), np.zeros((3, 1))])
        else:
            base = bases[tracker]
        m = utils.transform_matrix(base, (x, y, -z), (rx, ry, rz))
        cases.append({"tracker": tracker, "position": [x, y, z, rx, ry, rz], "matrix": m.tolist()})
    out = ROOT / "native" / "testdata" / "overlay" / "math.json"
    out.write_text(json.dumps({"bases": {k: v.tolist() for k, v in bases.items()}, "cases": cases}), encoding="utf-8")
    print(out, len(cases))


if __name__ == "__main__":
    main()
