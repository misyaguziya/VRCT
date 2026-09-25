"""アノテーション結果をYOLO学習用のデータセットに整える。

python tools/prepare_yolo_dataset.py [--val-ratio 0.2] [--scene-size 10] [--seed 0]
                                     [--stratify-label-ratio]

dataset_annotated/<session>/ にある images/ と annotations/ を読み、
labels/ を作って train.txt / val.txt / data.yaml を書き出す。画像は複製しない。
2秒周期の連番撮影なので、隣接フレームが train と val に割れないようシーン単位で分割する。
分割はセッション単位で層化するので、セッションを足しても既存セッションの val は変わらない。
Chat表示なしの画像(空の.txt)はネガティブサンプルとしてそのまま残す。
--stratify-label-ratio は全画像を使い、positive / negative の比率が train と val で
ほぼ同じになるようにシーンを割り当てる。
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


def pick_val_scenes(keys: list[str], scenes: dict[str, list[tuple[str, bool]]],
                    val_ratio: float, seed: int, label: str) -> set[str]:
    """シーンを shuffle して、目標枚数に届くまで val に取る。"""
    keys = sorted(keys)
    random.Random(seed).shuffle(keys)
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
            f"cannot split {label} ({len(keys)} scene(s)) with --val-ratio {val_ratio}: "
            "シーン数が足りない。--scene-size を小さくするか撮影シーンを増やす。")
    return val_keys


def split_scenes(scenes: dict[str, list[tuple[str, bool]]], val_ratio: float,
                 seed: int) -> tuple[list[str], list[str]]:
    """シーンごと train / val に振り分ける。同じシーンの画像が両方に入ることはない。

    **セッション単位で層化する**。全シーンをまとめて shuffle すると、セッションを
    足したときに val が特定のセッションへ偏りうる(実際に2セッション目を足した直後、
    val 40枚が全部2セッション目になり、1セッション目の旧 val が全部 train へ移った)。
    val はワールドと窓サイズの違いを見るためのものなので、どのセッションからも
    同じ比率で取る。seed はセッションごとに独立なので、既存セッションの val は
    セッションを足しても変わらない。
    """
    by_session: dict[str, list[str]] = defaultdict(list)
    for key in scenes:
        by_session[key.split("/", 1)[0]].append(key)
    val_keys: set[str] = set()
    for session, keys in sorted(by_session.items()):
        val_keys |= pick_val_scenes(keys, scenes, val_ratio, seed, session)
    train = [e for k in scenes if k not in val_keys for e, _ in scenes[k]]
    val = [e for k in val_keys for e, _ in scenes[k]]
    return sorted(train), sorted(val)


def split_stratified_scenes(scenes: dict[str, list[tuple[str, bool]]], val_ratio: float,
                            seed: int) -> tuple[list[str], list[str]]:
    """全画像を使い、positive / negative比率を揃えてシーン単位で分割する。"""
    session_names = sorted({key.split("/", 1)[0] for key in scenes})
    session_bits = {name: 1 << index for index, name in enumerate(session_names)}
    full_mask = (1 << len(session_names)) - 1
    total_images = sum(len(entries) for entries in scenes.values())
    total_positive = sum(1 for entries in scenes.values() for _, positive in entries if positive)
    val_image_target = round(total_images * val_ratio)
    val_positive_target = round(total_positive * val_ratio)

    # (画像数, positive数, session mask)ごとに選択シーンを1組保持する。
    states: dict[tuple[int, int, int], tuple[str, ...]] = {(0, 0, 0): ()}
    for key in sorted(scenes):
        entries = scenes[key]
        images = len(entries)
        positive = sum(1 for _, is_positive in entries if is_positive)
        bit = session_bits[key.split("/", 1)[0]]
        additions = {}
        for (image_count, positive_count, mask), selected in states.items():
            next_images = image_count + images
            if next_images > val_image_target + max(len(v) for v in scenes.values()):
                continue
            state = (next_images, positive_count + positive, mask | bit)
            additions.setdefault(state, selected + (key,))
        states.update(additions)

    candidates = []
    for (images, positive, mask), selected in states.items():
        if mask != full_mask:
            continue
        candidates.append((
            abs(images - val_image_target) + abs(positive - val_positive_target),
            abs(images - val_image_target),
            abs(positive - val_positive_target),
            tuple(random.Random(seed).sample(list(selected), len(selected))),
        ))
    if not candidates:
        raise SystemExit(
            "cannot make a scene-separated stratified split across every session")

    val_keys = set(min(candidates)[3])
    train = [entry for key, entries in scenes.items() if key not in val_keys
             for entry, _ in entries]
    val = [entry for key, entries in scenes.items() if key in val_keys
           for entry, _ in entries]
    return sorted(train), sorted(val)


def prepare(root: Path, val_ratio: float, seed: int, scene_size: int = 10,
            stratify_label_ratio: bool = False) -> tuple[int, int]:
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
    if stratify_label_ratio:
        train, val = split_stratified_scenes(scenes, val_ratio, seed)
    else:
        train, val = split_scenes(scenes, val_ratio, seed)
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
    parser.add_argument("--stratify-label-ratio", action="store_true",
                        help="全画像を使いpositive/negative比率をtrainとvalで揃える")
    args = parser.parse_args()
    if not 0.0 < args.val_ratio < 1.0:
        raise SystemExit("--val-ratio must be between 0 and 1")
    if args.scene_size < 1:
        raise SystemExit("--scene-size must be 1 or more")
    n_train, n_val = prepare(
        args.root, args.val_ratio, args.seed, args.scene_size, args.stratify_label_ratio)
    print(f"train {n_train} / val {n_val} -> {args.root / 'data.yaml'}")


if __name__ == "__main__":
    main()
