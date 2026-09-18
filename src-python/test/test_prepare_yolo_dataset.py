"""ディスク上の一時データセットだけを扱う。学習も画像デコードも行わない。"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools import prepare_yolo_dataset as prep  # noqa: E402

LITERAL_NEWLINE = chr(92) + "n"


def make_session(root: Path, name: str, frames: int, negatives: tuple[int, ...] = ()) -> Path:
    """連番フレームのセッションを作る。negatives に指定したフレーム番号は空ラベル。"""
    session = root / name
    (session / "images").mkdir(parents=True)
    (session / "annotations").mkdir(parents=True)
    for i in range(frames):
        stem = f"{name}_run_{i:06d}"
        (session / "images" / f"{stem}.png").write_bytes(b"fake")
        # アノテーションツールが改行をバックスラッシュとnの2文字で書くことがあるので両方混ぜる。
        terminator = "\n" if i % 2 else LITERAL_NEWLINE
        body = "" if i in negatives else "0 0.5 0.5 0.1 0.1" + terminator
        (session / "annotations" / f"{stem}.txt").write_text(body, encoding="utf-8")
    return session


def read_split(root: Path, name: str) -> list[str]:
    return root.joinpath(f"{name}.txt").read_text(encoding="utf-8").split()


def frame_index(entry: str) -> int:
    return int(entry.rsplit("_", 1)[1].split(".")[0])


def test_split_is_scene_based_so_neighbouring_frames_do_not_leak(tmp_path):
    make_session(tmp_path, "sessionA", frames=100)

    assert prep.prepare(tmp_path, val_ratio=0.2, seed=0, scene_size=10) == (80, 20)

    train, val = read_split(tmp_path, "train"), read_split(tmp_path, "val")
    assert set(train).isdisjoint(val)
    assert len(set(train + val)) == 100
    # 同じ10フレームのまとまりがtrainとvalに割れていないこと。
    train_scenes = {frame_index(e) // 10 for e in train}
    val_scenes = {frame_index(e) // 10 for e in val}
    assert train_scenes.isdisjoint(val_scenes)
    assert "train: train.txt" in tmp_path.joinpath("data.yaml").read_text(encoding="utf-8")


def test_negatives_are_kept_as_empty_labels(tmp_path):
    session = make_session(tmp_path, "sessionA", frames=100, negatives=(3, 47, 88))

    prep.prepare(tmp_path, val_ratio=0.2, seed=0, scene_size=10)

    for i in (3, 47, 88):
        label = session / "labels" / f"sessionA_run_{i:06d}.txt"
        assert label.is_file() and label.read_text(encoding="utf-8") == ""
    entries = read_split(tmp_path, "train") + read_split(tmp_path, "val")
    assert {3, 47, 88} <= {frame_index(e) for e in entries}


def test_too_few_scenes_stops_instead_of_making_an_empty_split(tmp_path):
    make_session(tmp_path, "sessionA", frames=8)

    with pytest.raises(SystemExit, match="cannot split"):
        prep.prepare(tmp_path, val_ratio=0.2, seed=0, scene_size=10)


def test_literal_backslash_n_becomes_a_real_newline(tmp_path):
    """これを取りこぼすとultralyticsがラベルをcorrupt扱いで黙って捨てる。"""
    session = make_session(tmp_path, "sessionA", frames=20)

    prep.prepare(tmp_path, val_ratio=0.2, seed=0, scene_size=5)

    for label in sorted((session / "labels").iterdir()):
        assert label.read_text(encoding="utf-8") == "0 0.500000 0.500000 0.100000 0.100000\n"


@pytest.mark.parametrize("broken", ["0 0.5 0.5 0.1\n", "0 x 0.5 0.1 0.1\n", "0 1.5 0.5 0.1 0.1\n"])
def test_broken_label_stops_instead_of_being_silently_dropped(tmp_path, broken):
    session = make_session(tmp_path, "sessionA", frames=20)
    (session / "annotations" / "sessionA_run_000000.txt").write_text(broken, encoding="utf-8")

    with pytest.raises(SystemExit, match="broken label"):
        prep.prepare(tmp_path, val_ratio=0.2, seed=0, scene_size=5)


def test_rerun_is_stable_and_refreshes_changed_labels(tmp_path):
    session = make_session(tmp_path, "sessionA", frames=20)
    prep.prepare(tmp_path, val_ratio=0.2, seed=0, scene_size=5)
    first = read_split(tmp_path, "val")

    (session / "annotations" / "sessionA_run_000000.txt").write_text("0 0.25 0.25 0.2 0.2\n", encoding="utf-8")
    prep.prepare(tmp_path, val_ratio=0.2, seed=0, scene_size=5)

    assert read_split(tmp_path, "val") == first
    label = (session / "labels" / "sessionA_run_000000.txt").read_text(encoding="utf-8")
    assert label == "0 0.250000 0.250000 0.200000 0.200000\n"


def test_image_without_label_is_skipped(tmp_path):
    session = make_session(tmp_path, "sessionA", frames=20)
    (session / "images" / "orphan.png").write_bytes(b"fake")

    assert prep.prepare(tmp_path, val_ratio=0.2, seed=0, scene_size=5) == (15, 5)
    assert not (session / "labels" / "orphan.txt").exists()
