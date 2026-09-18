"""アノテーション結果をYOLO学習用のデータセットに整える。

python tools/prepare_yolo_dataset.py [--val-ratio 0.2] [--scene-size 10] [--seed 0]

dataset_annotated/<session>/ にある images/ と annotations/ を読み、
labels/ を作って train.txt / val.txt / data.yaml を書き出す。画像は複製しない。
2秒周期の連番撮影なので、隣接フレームが train と val に割れないようシーン単位で分割する。
Chat表示なしの画像(空の.txt)はネガティブサンプルとしてそのまま残す。
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import random
import sys

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
ROOT = Path(__file__).resolve().parents[1] / "dataset_annotated"
LITERAL_NEWLINE = "\\" + "n"


def find_sessions(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir()
                  if p.is_dir() and (p / "images").is_dir() and (p / "annotations").is_dir())


def normalize_label(text: str, source: Path) -> str:
    """YOLOラベルを検証して正規化する。壊れた行があれば止める。

    アノテーションツールが改行をバックスラッシュとnの2文字で書き出すことがあり、
    そのままだとultralyticsがファイルごとcorrupt扱いで黙って捨てる(80枚中57枚が落ちた)。
    """
    normalized: list[str] = []
    for line in text.replace(LITERAL_NEWLINE, "\n").splitlines():
        line = line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 5:
            raise SystemExit(f"broken label (expected 5 fields): {source}: {line!r}")
        try:
            class_id = int(fields[0])
            coords = [float(v) for v in fields[1:]]
        except ValueError:
            raise SystemExit(f"broken label (not a number): {source}: {line!r}") from None
        if class_id < 0 or not all(0.0 <= v <= 1.0 for v in coords):
            raise SystemExit(f"broken label (out of range): {source}: {line!r}")
        normalized.append(" ".join([str(class_id)] + [f"{v:.6f}" for v in coords]))
    return "".join(f"{line}\n" for line in normalized)


def scene_of(session: Path, stem: str, scene_size: int) -> str:
    """連番の近いフレームを1シーンにまとめる。似た画像がtrainとvalに割れるのを防ぐ。"""
    run_id, _, index = stem.rpartition("_")
    if run_id and index.isdigit():
        return f"{session.name}/{run_id}#{int(index) // scene_size:04d}"
    return f"{session.name}/{stem}"  # 連番でない名前は1枚1シーン扱い


def write_labels(session: Path, scene_size: int) -> dict[str, list[tuple[str, bool]]]:
    """annotations/*.txt を検証して labels/ へ書き、シーン -> [(画像の相対パス, positive)] を返す。"""
    labels = session / "labels"
    labels.mkdir(exist_ok=True)
    scenes: dict[str, list[tuple[str, bool]]] = defaultdict(list)
    for image in sorted(p for p in (session / "images").iterdir() if p.suffix.lower() in IMAGE_SUFFIXES):
        source = session / "annotations" / f"{image.stem}.txt"
        if not source.is_file():
            print(f"skip (no label): {image.name}", file=sys.stderr)
            continue
        body = normalize_label(source.read_text(encoding="utf-8"), source)
        target = labels / source.name
        if not target.is_file() or target.read_text(encoding="utf-8") != body:
            target.write_text(body, encoding="utf-8")
        entry = f"./{session.name}/images/{image.name}"
        scenes[scene_of(session, image.stem, scene_size)].append((entry, bool(body)))
    return scenes


def split_scenes(scenes: dict[str, list[tuple[str, bool]]], val_ratio: float,
                 rng: random.Random) -> tuple[list[str], list[str]]:
    """シーンごと train / val に振り分ける。同じシーンの画像が両方に入ることはない。"""
    keys = sorted(scenes)
    rng.shuffle(keys)
    target = round(sum(len(scenes[k]) for k in keys) * val_ratio)
    val_keys: set[str] = set()
    taken = 0
    for key in keys:
        if taken >= target:
            break
        val_keys.add(key)
        taken += len(scenes[key])
    if not val_keys or len(val_keys) == len(keys):
        raise SystemExit(
            f"cannot split {len(keys)} scene(s) with --val-ratio {val_ratio}: "
            "シーン数が足りない。--scene-size を小さくするか撮影シーンを増やす。")
    train = [e for k in keys if k not in val_keys for e, _ in scenes[k]]
    val = [e for k in val_keys for e, _ in scenes[k]]
    return sorted(train), sorted(val)


def prepare(root: Path, val_ratio: float, seed: int, scene_size: int = 10) -> tuple[int, int]:
    sessions = find_sessions(root)
    if not sessions:
        raise SystemExit(f"no annotated session under {root}")
    scenes: dict[str, list[tuple[str, bool]]] = {}
    for session in sessions:
        found = write_labels(session, scene_size)
        images = sum(len(v) for v in found.values())
        positives = sum(1 for v in found.values() for _, pos in v if pos)
        print(f"{session.name}: {images} images / {positives} positive / "
              f"{images - positives} negative / {len(found)} scenes")
        scenes.update(found)

    positive = {entry for v in scenes.values() for entry, pos in v if pos}
    train, val = split_scenes(scenes, val_ratio, random.Random(seed))
    (root / "train.txt").write_text("\n".join(train) + "\n", encoding="utf-8")
    (root / "val.txt").write_text("\n".join(val) + "\n", encoding="utf-8")
    (root / "data.yaml").write_text(
        f"path: {root.as_posix()}\ntrain: train.txt\nval: val.txt\nnames:\n  0: chat\n",
        encoding="utf-8")
    for name, entries in (("train", train), ("val", val)):
        pos = sum(1 for e in entries if e in positive)
        print(f"{name}: {len(entries)} images / {pos} positive / {len(entries) - pos} negative")
    return len(train), len(val)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--scene-size", type=int, default=10,
                        help="連続する何フレームを1シーンとみなすか (既定: 10 = 2秒周期で約20秒)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if not 0.0 < args.val_ratio < 1.0:
        raise SystemExit("--val-ratio must be between 0 and 1")
    if args.scene_size < 1:
        raise SystemExit("--scene-size must be 1 or more")
    n_train, n_val = prepare(args.root, args.val_ratio, args.seed, args.scene_size)
    print(f"train {n_train} / val {n_val} -> {args.root / 'data.yaml'}")


if __name__ == "__main__":
    main()
