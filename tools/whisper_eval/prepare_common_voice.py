"""Prepare a deterministic Common Voice subset for Whisper evaluation.

The Common Voice archive is intentionally downloaded outside this repository.
This script consumes an extracted corpus, selects a stratified subset, converts
audio to the benchmark format, and creates deterministic noise variants.
"""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .audio import (
    TARGET_CHANNELS,
    TARGET_SAMPLE_RATE,
    TARGET_SAMPLE_WIDTH,
    convert_to_standard_wav,
    deterministic_seed,
    make_noise_variant,
    sha256_file,
    write_pcm16_wav,
)
from .metrics import normalize_transcript


DEFAULT_SOURCE_URL = "https://commonvoice.mozilla.org/en/datasets"
NOISE_VARIANTS = (
    ("white", 10, "white_snr10"),
    ("white", 20, "white_snr20"),
    ("environment", 10, "environment_snr10"),
    ("environment", 20, "environment_snr20"),
)

# Common Voice metadata can contain unusually long optional fields.  The
# default csv parser limit (128 KiB) is lower than some released TSV rows.
csv.field_size_limit(10_000_000)


@dataclass(frozen=True)
class CommonVoiceRow:
    audio_path: str
    transcript: str
    speaker_id: str
    row_number: int

    @property
    def length_bucket(self) -> str:
        length = len(normalize_transcript(self.transcript))
        if length <= 12:
            return "short"
        if length >= 40:
            return "long"
        return "medium"


def load_common_voice_rows(tsv_path: Path) -> list[CommonVoiceRow]:
    """Read validated Common Voice metadata without altering transcript text."""

    rows: list[CommonVoiceRow] = []
    seen_paths: set[str] = set()
    with tsv_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        if not reader.fieldnames or "path" not in reader.fieldnames or "sentence" not in reader.fieldnames:
            raise ValueError(f"{tsv_path}: expected Common Voice path and sentence columns")
        for row_number, row in enumerate(reader, start=2):
            audio_path = (row.get("path") or "").strip()
            transcript = (row.get("sentence") or "").strip()
            if not audio_path or not normalize_transcript(transcript):
                continue
            normalized_path = audio_path.replace("\\", "/")
            if normalized_path in seen_paths:
                continue
            seen_paths.add(normalized_path)
            speaker_id = (
                (row.get("client_id") or row.get("speaker_id") or "").strip()
                or "unknown-speaker"
            )
            rows.append(CommonVoiceRow(normalized_path, transcript, speaker_id, row_number))
    if not rows:
        raise ValueError(f"{tsv_path}: no usable Common Voice rows found")
    return rows


def _rank(row: CommonVoiceRow, seed: int) -> int:
    return deterministic_seed(seed, row.audio_path, row.speaker_id, row.transcript)


def _round_robin_by_speaker(rows: Iterable[CommonVoiceRow], count: int, seed: int) -> list[CommonVoiceRow]:
    groups: dict[str, list[CommonVoiceRow]] = {}
    for row in rows:
        groups.setdefault(row.speaker_id, []).append(row)
    speaker_order = sorted(groups, key=lambda speaker: deterministic_seed(seed, speaker))
    for speaker in speaker_order:
        groups[speaker].sort(key=lambda row: _rank(row, seed))

    selected: list[CommonVoiceRow] = []
    while len(selected) < count and speaker_order:
        exhausted: list[str] = []
        for speaker in speaker_order:
            if groups[speaker]:
                selected.append(groups[speaker].pop(0))
                if len(selected) == count:
                    break
            else:
                exhausted.append(speaker)
        speaker_order = [speaker for speaker in speaker_order if speaker not in exhausted]
    return selected


def select_rows(
    rows: Iterable[CommonVoiceRow],
    count: int,
    seed: int,
    *,
    min_speakers: int = 3,
) -> list[CommonVoiceRow]:
    """Select a deterministic subset balanced across transcript lengths/speakers."""

    candidates = list(rows)
    if count <= 0:
        raise ValueError("count must be greater than zero")
    if count > len(candidates):
        raise ValueError(f"requested {count} clips but only {len(candidates)} are available")

    buckets = {bucket: [] for bucket in ("short", "medium", "long")}
    for row in candidates:
        buckets[row.length_bucket].append(row)
    if any(not bucket_rows for bucket_rows in buckets.values()):
        missing = ", ".join(bucket for bucket, bucket_rows in buckets.items() if not bucket_rows)
        raise ValueError(f"Common Voice subset has no usable {missing} utterances")

    bucket_targets = {bucket: count // 3 for bucket in buckets}
    for bucket in ("short", "medium", "long")[: count % 3]:
        bucket_targets[bucket] += 1

    selected: list[CommonVoiceRow] = []
    selected_paths: set[str] = set()
    for bucket, target in bucket_targets.items():
        for row in _round_robin_by_speaker(buckets[bucket], target, seed):
            if row.audio_path not in selected_paths:
                selected.append(row)
                selected_paths.add(row.audio_path)

    if len(selected) < count:
        remaining = sorted(
            (row for row in candidates if row.audio_path not in selected_paths),
            key=lambda row: _rank(row, seed),
        )
        selected.extend(remaining[: count - len(selected)])

    if len({row.speaker_id for row in selected}) < min_speakers:
        raise ValueError(
            f"selected subset contains fewer than {min_speakers} speakers; "
            "use a larger or more diverse Common Voice metadata file"
        )
    return selected[:count]


def _resolve_source(input_dir: Path, relative_path: str) -> Path:
    root = input_dir.resolve()
    for base in (root, root / "clips"):
        candidate = (base / relative_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError(f"Common Voice path escapes input directory: {relative_path}")
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(root / "clips" / relative_path)


def _relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def prepare_dataset(
    *,
    input_dir: Path,
    tsv_path: Path,
    output_dir: Path,
    environment_noise_path: Path,
    count: int,
    seed: int,
    ffmpeg: str,
    source_name: str,
    source_url: str,
    license_name: str,
    dataset_version: str,
) -> dict[str, object]:
    rows = load_common_voice_rows(tsv_path)
    selected = select_rows(rows, count, seed, min_speakers=3)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="vrct-whisper-eval-") as temp_dir:
        environment_wav = Path(temp_dir) / "environment_noise.wav"
        environment_samples = convert_to_standard_wav(
            environment_noise_path,
            environment_wav,
            ffmpeg=ffmpeg,
        )

        metadata_rows: list[dict[str, object]] = []
        manifest_items: list[dict[str, object]] = []
        total_clean_duration_seconds = 0.0
        for index, row in enumerate(selected, start=1):
            item_id = f"cv_{index:04d}"
            source_path = _resolve_source(input_dir, row.audio_path)
            clean_relative_path = f"clean/{item_id}.wav"
            clean_path = output_dir / clean_relative_path
            clean_samples = convert_to_standard_wav(source_path, clean_path, ffmpeg=ffmpeg)
            total_clean_duration_seconds += len(clean_samples) / TARGET_SAMPLE_RATE
            source_digest = sha256_file(source_path)
            variants: list[dict[str, object]] = []

            clean_record = {
                "condition": "clean",
                "snr_db": None,
                "audio_path": clean_relative_path,
            }
            variants.append(clean_record)
            metadata_rows.append(
                _metadata_row(
                    item_id=item_id,
                    row=row,
                    condition="clean",
                    snr_db=None,
                    audio_path=clean_path,
                    output_dir=output_dir,
                    source_digest=source_digest,
                    source_name=source_name,
                    source_url=source_url,
                    license_name=license_name,
                    duration_seconds=len(clean_samples) / TARGET_SAMPLE_RATE,
                )
            )

            for noise_kind, snr_db, condition in NOISE_VARIANTS:
                relative_path = f"{condition}/{item_id}.wav"
                variant_path = output_dir / relative_path
                variant_samples = make_noise_variant(
                    clean_samples,
                    noise_kind=noise_kind,
                    snr_db=snr_db,
                    seed=deterministic_seed(seed, item_id, condition),
                    environment_noise=environment_samples,
                )
                write_pcm16_wav(variant_path, variant_samples, TARGET_SAMPLE_RATE)
                variants.append(
                    {"condition": condition, "snr_db": snr_db, "audio_path": relative_path}
                )
                metadata_rows.append(
                    _metadata_row(
                        item_id=item_id,
                        row=row,
                        condition=condition,
                        snr_db=snr_db,
                        audio_path=variant_path,
                        output_dir=output_dir,
                        source_digest=source_digest,
                        source_name=source_name,
                        source_url=source_url,
                        license_name=license_name,
                        duration_seconds=len(clean_samples) / TARGET_SAMPLE_RATE,
                    )
                )

            manifest_items.append(
                {
                    "id": item_id,
                    "speaker_id": row.speaker_id,
                    "length_bucket": row.length_bucket,
                    "transcript": row.transcript,
                    "source_path": row.audio_path,
                    "source_sha256": source_digest,
                    "variants": variants,
                }
            )

    _write_metadata_csv(output_dir / "metadata.csv", metadata_rows)
    manifest = {
        "schema_version": 1,
        "seed": seed,
        "count": len(selected),
        "total_clean_duration_seconds": round(total_clean_duration_seconds, 6),
        "audio_format": {
            "sample_rate": TARGET_SAMPLE_RATE,
            "channels": TARGET_CHANNELS,
            "sample_width": TARGET_SAMPLE_WIDTH,
            "encoding": "PCM signed 16-bit little-endian",
        },
        "source": {
            "name": source_name,
            "url": source_url,
            "license": license_name,
            "dataset_version": dataset_version,
            "metadata_file": _relative_path(tsv_path, input_dir),
        },
        "environment_noise": {
            "name": environment_noise_path.name,
            "sha256": sha256_file(environment_noise_path),
        },
        "noise_variants": [
            {"condition": condition, "kind": kind, "snr_db": snr_db}
            for kind, snr_db, condition in NOISE_VARIANTS
        ],
        "items": manifest_items,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _metadata_row(
    *,
    item_id: str,
    row: CommonVoiceRow,
    condition: str,
    snr_db: int | None,
    audio_path: Path,
    output_dir: Path,
    source_digest: str,
    source_name: str,
    source_url: str,
    license_name: str,
    duration_seconds: float,
) -> dict[str, object]:
    return {
        "id": item_id,
        "speaker_id": row.speaker_id,
        "length_bucket": row.length_bucket,
        "condition": condition,
        "snr_db": "" if snr_db is None else snr_db,
        "audio_path": _relative_path(audio_path, output_dir),
        "transcript": row.transcript,
        "duration_seconds": f"{duration_seconds:.6f}",
        "sample_rate": TARGET_SAMPLE_RATE,
        "channels": TARGET_CHANNELS,
        "source_path": row.audio_path,
        "source_sha256": source_digest,
        "source_name": source_name,
        "source_url": source_url,
        "license": license_name,
    }


def _write_metadata_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "id",
        "speaker_id",
        "length_bucket",
        "condition",
        "snr_db",
        "audio_path",
        "transcript",
        "duration_seconds",
        "sample_rate",
        "channels",
        "source_path",
        "source_sha256",
        "source_name",
        "source_url",
        "license",
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True, help="extracted Common Voice corpus root")
    parser.add_argument("--tsv", default="validated.tsv", help="metadata TSV relative to --input-dir")
    parser.add_argument("--output-dir", type=Path, required=True, help="generated evaluation dataset directory")
    parser.add_argument("--environment-noise", type=Path, required=True, help="licensed environment-noise WAV/audio file")
    parser.add_argument("--count", type=int, default=150, help="number of clean utterances (100-200 for the planned set)")
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg executable name or path")
    parser.add_argument("--source-name", default="Mozilla Common Voice Japanese")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--license", dest="license_name", default="CC0-1.0")
    parser.add_argument("--dataset-version", default="", help="Common Voice release identifier")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not 100 <= args.count <= 200:
        parser.error("--count must be between 100 and 200 for the planned evaluation set")

    try:
        tsv_path = (args.input_dir / args.tsv).resolve()
        manifest = prepare_dataset(
            input_dir=args.input_dir,
            tsv_path=tsv_path,
            output_dir=args.output_dir,
            environment_noise_path=args.environment_noise,
            count=args.count,
            seed=args.seed,
            ffmpeg=args.ffmpeg,
            source_name=args.source_name,
            source_url=args.source_url,
            license_name=args.license_name,
            dataset_version=args.dataset_version,
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(f"Prepared {manifest['count']} utterances at {args.output_dir}")


if __name__ == "__main__":
    main()
