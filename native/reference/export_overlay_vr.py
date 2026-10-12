"""VR UI の計算 (overlay.py のモジュール関数: 姿勢・並び・マスク、overlay_tooltip.py) を、今の Python 版で記録する。

    python native/reference/export_overlay_vr.py   ->  native/testdata/overlay/vr.json

姿勢は乱数の回転と位置。マスクと画像は行ごとの連長 ([値, 長さ], ...) で残す (Pillow の描画と比べる)。
"""

import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src-python"))
sys.path.insert(0, str(ROOT / "src-python" / "models" / "overlay"))


def runs(array):
    """2 次元 (高さ, 幅[, 色]) を、行ごとの [値, 長さ] の並びに。"""
    out = []
    for row in array:
        keys = [tuple(int(v) for v in np.atleast_1d(px)) for px in row]
        line = []
        for key in keys:
            if line and line[-1][0] == list(key):
                line[-1][1] += 1
            else:
                line.append([list(key), 1])
        out.append(line)
    return out


def main():
    import overlay as o
    import overlay_utils as utils
    import overlay_tooltip as t
    from types import SimpleNamespace

    rng = random.Random(20261012)

    def pose():
        rot = utils.euler_to_rotation_matrix([rng.uniform(-180, 180) for _ in range(3)])
        m = np.eye(4)
        m[:3, :3] = rot
        m[:3, 3] = [rng.uniform(-2, 2), rng.uniform(0, 2), rng.uniform(-2, 2)]
        return m

    def vec():
        return np.array([rng.uniform(-2, 2), rng.uniform(0, 2), rng.uniform(-2, 2)])

    L = lambda m: np.asarray(m).tolist()
    cases = {k: [] for k in ("ray_plane_hit", "pose_facing", "face_head", "pose_on_sphere", "sphere_radius", "is_out_of_view",
                             "recall_pose", "intro_front_pose", "intro_flight_pose", "push_pull_distance", "push_pull",
                             "launcher_looks_visible", "launcher_reach", "matrix_to_position", "laser_tilt", "uv_to_pixel")}
    for _ in range(200):
        ray, plane = pose(), pose()
        if rng.random() < 0.5:  # 面の正面から指す
            plane[:3, 3] = ray[:3, 3] - ray[:3, 2] * rng.uniform(0.2, 2) + vec() * 0.1
        hit = o.rayPlaneHit(ray, plane)
        cases["ray_plane_hit"].append({"ray": L(ray), "plane": L(plane),
                                       "hit": None if hit is None else [hit[0], hit[1], L(hit[2]), hit[3]]})
        p, target = vec(), vec()
        up = None if rng.random() < 0.3 else (np.array([0.0, 1.0, 0.0]) if rng.random() < 0.1 else vec())
        cases["pose_facing"].append({"position": L(p), "target": L(target), "up": None if up is None else L(up),
                                     "pose": L(o.popupPoseFacing(p, target, up))})
        head = pose()
        cases["face_head"].append({"position": L(p), "head": L(head), "pose": L(o.faceHead(p, head))})
        radius = rng.uniform(0.2, 3)
        point = head[:3, 3] if rng.random() < 0.05 else vec()
        cases["pose_on_sphere"].append({"point": L(point), "head": L(head), "radius": radius, "pose": L(o.poseOnSphere(point, head, radius))})
        base, start, now = rng.uniform(0.1, 3), rng.uniform(0.0, 1), rng.uniform(0.0, 1)
        cases["sphere_radius"].append([base, start, now, o.sphereRadius(base, start, now)])
        near = head[:3, 3] - head[:3, 2] * rng.uniform(0.1, 3.5) + vec() * rng.choice([0, 0.3, 1])
        for was_out in (False, True):
            cases["is_out_of_view"].append({"head": L(head), "position": L(near), "was_out": was_out,
                                            "out": o.isOutOfView(head, near, was_out)})
        cases["recall_pose"].append({"head": L(head), "pose": L(o.recallPose(head))})
        cases["intro_front_pose"].append({"head": L(head), "pose": L(o.introFrontPose(head))})
        a, b = pose(), pose()
        if rng.random() < 0.2:
            b[:3, :3] = a[:3, :3]
        progress = rng.choice([0.0, 1.0, rng.random()])
        cases["intro_flight_pose"].append({"front": L(a), "target": L(b), "progress": progress, "pose": L(o.introFlightPose(a, b, progress))})
        x, y = rng.choice([0.0, rng.uniform(-1, 1)]), rng.uniform(-1, 1)
        state = SimpleNamespace(rAxis=[SimpleNamespace(x=x, y=y)])
        distance, dt = rng.uniform(0.1, 3), rng.uniform(0, 0.1)
        cases["push_pull_distance"].append([distance, x, y, dt, o.pushPullDistance(distance, state, dt)])
        cases["push_pull"].append({"pose": L(a), "stick": [x, y], "dt": dt, "result": L(o.pushPull(a, state, dt))})
        face, gaze = rng.choice([45.0, 55.0]), rng.choice([40.0, 45.0])
        launcher = o.faceHead(head[:3, 3] - head[:3, 2] * 0.4 + vec() * 0.2, head) if rng.random() < 0.5 else pose()
        cases["launcher_looks_visible"].append({"launcher": L(launcher), "head": L(head), "face": face, "gaze": gaze,
                                                "visible": bool(o.launcherLooksVisible(launcher, head, face, gaze))})
        s = {"x_pos": rng.uniform(-0.2, 0.2), "y_pos": rng.uniform(-0.2, 0.2), "z_pos": rng.uniform(-0.2, 0.2),
             "ui_scaling": rng.uniform(0.05, 1.2)}
        near_s = o.launcherNearestInReach(s)
        cases["launcher_reach"].append({"settings": s, "out": o.launcherOutOfReach(s), "nearest": near_s})
        tracker = rng.choice(["HMD", "LeftHand", "RightHand", "Playspace"])
        base3 = {"HMD": o.getHMDBaseMatrix(), "LeftHand": o.getLeftHandBaseMatrix(), "RightHand": o.getRightHandBaseMatrix(),
                 "Playspace": np.hstack([np.eye(3), np.zeros((3, 1))])}[tracker]
        relative = pose()
        if rng.random() < 0.1:  # ジンバルロック
            relative[:3, :3] = utils.euler_to_rotation_matrix((rng.uniform(-90, 90), rng.choice([90.0, -90.0]), rng.uniform(-90, 90)))
            relative = utils.toHomogeneous(base3) @ relative
        cases["matrix_to_position"].append({"base": L(base3), "relative": L(relative[:3, :]),
                                            "position": list(utils.matrix_to_position(base3, relative[:3, :]))})
        deg = rng.uniform(-40, 40)
        cases["laser_tilt"].append({"degrees": deg, "pose": L(o.laserTilt(deg))})
        u, v, w, h = rng.uniform(-0.1, 1.1), rng.uniform(-0.5, 1.5), rng.randint(1, 800), rng.randint(1, 800)
        cases["uv_to_pixel"].append([u, v, w, h, list(o.uvToPixel(u, v, w, h))])

    layouts = []
    for size in [(900, 700), (600, 400), (1400, 1000), (955, 401), (1000, 900)]:
        layout = o.computeVrLayout(*size)
        for width_scale in (1.0, 1.25, 1.5):
            image = (round(layout["atlas"][0] * width_scale), round(layout["atlas"][1] * width_scale))
            entry = {"panel": list(size), "atlas": list(layout["atlas"]),
                     "regions": {k: list(v) for k, v in layout["regions"].items()}, "image": list(image),
                     "rects": {k: list(o.regionRect(k, image, layout)) for k in layout["regions"]},
                     "bounds": {k: list(o.regionBounds(k, layout)) for k in layout["regions"]},
                     "marker": list(t.marker_points(image[0], layout))}
            if width_scale != 1.25:
                mask = o.atlasMaskArray(image, layout)
                entry["mask"] = runs(mask)
                state = {"size": [360, rng.randint(1, 104)], "arrow_x": rng.uniform(12, 348)}
                entry["tooltip"] = {"state": state, "mask": runs(t.tooltip_mask(image, layout, state, mask))}
            layouts.append(entry)
    clamps = [[w, h, list(o.clampPanelSize(w, h))] for w, h in
              [(500, 300), (2000, 2000), (900.5, 700.5), (901.5, 699.5), (750.4, 610.6), (600, 1000)]]

    tooltips = []
    good = {"epoch": 5, "revision": 2, "visible": True, "region": "launcher", "button": [10, 20, 60, 40], "size": [360, 50], "arrow_x": 40}
    variants = [good, {**good, "mode": "focus"}, {**good, "region": "toolbar", "button": [0, 0, 720, 96]},
                {"epoch": 5, "revision": 2, "visible": False}, {"epoch": 5, "revision": 2, "visible": False, "region": "launcher"},
                {**good, "epoch": 0}, {**good, "epoch": 1 << 48}, {**good, "epoch": 5.0}, {**good, "epoch": True},
                {**good, "revision": 1 << 32}, {**good, "visible": 1}, {**good, "extra": 1}, {**good, "region": "panel"},
                {**good, "mode": "click"}, {**good, "button": [10, 20, 60]}, {**good, "button": [10, 20, 60, "4"]},
                {**good, "button": [10, 20, 60, True]}, {**good, "button": [-1, 20, 60, 40]}, {**good, "button": [900, 20, 60, 40]},
                {**good, "button": [10, 20, 0, 40]}, {**good, "region": "toolbar", "button": [0, 0, 720, 97]},
                {**good, "size": [361, 50]}, {**good, "size": [360, 0]}, {**good, "size": [360, 104.0]}, {**good, "size": [360, 105]},
                {**good, "arrow_x": 11}, {**good, "arrow_x": 348.0}, {**good, "arrow_x": 2e6},
                {**good, "button": [10, 20, 60, 1e7]}, {**good, "mode": None}, [1, 2], {**good, "epoch": (1 << 48) - 1}]
    for data in variants:
        try:
            result = t.validate_tooltip(data)
            tooltips.append({"data": data, "ok": result})
        except ValueError as e:
            tooltips.append({"data": data, "error": str(e)})
    rows = []
    layout = o.computeVrLayout(900, 700)
    for epoch, revision in [(1, 1), ((1 << 48) - 1, (1 << 32) - 1), (123456789, 42)]:
        py, columns = t.marker_points(layout["atlas"][0], layout)
        bits = (epoch << 32) | revision
        row = np.zeros((layout["atlas"][0], 4), np.uint8)
        for i, px in enumerate(columns):
            row[px, :3] = 240 if (bits >> (79 - i)) & 1 else 10
        bad = row.copy()
        bad[columns[7], 0] = 100
        rows.append({"epoch": epoch, "revision": revision, "row": row.flatten().tolist(),
                     "matches": t.marker_row_matches(row, columns, {"epoch": epoch, "revision": revision}),
                     "bad": bad.flatten().tolist(), "bad_matches": t.marker_row_matches(bad, columns, {"epoch": epoch, "revision": revision})})

    images = {"pointer": {k: runs(np.asarray(v)) for k, v in o.createPointerImages().items()},
              "ghost": [{"size": [w, h], "at_limit": lim, "image": runs(np.asarray(o.createGhostImage(w, h, lim)))}
                        for w, h, lim in [(900, 700, False), (600, 400, True), (1400, 1000, False), (20, 20, False)]]}

    out = ROOT / "native" / "testdata" / "overlay" / "vr.json"
    out.write_text(json.dumps({"cases": cases, "layouts": layouts, "clamps": clamps, "tooltips": tooltips,
                               "marker_rows": rows, "images": images}), encoding="utf-8")
    print(out, out.stat().st_size)


if __name__ == "__main__":
    main()
