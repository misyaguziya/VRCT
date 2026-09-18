"""Run one prepared utterance through VRCT's VAD-to-Whisper path.

This is an integration smoke test for the VRCT transcription feature. It does
not call ``WhisperModel.transcribe`` directly; audio is segmented by the VRCT
VAD adapter, placed on the same queue shape used by the recorder, and then
processed by ``AudioTranscriber``.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
from typing import Any

import numpy as np

from models.transcription.audio_vad import FRAME_SAMPLES, VadRecognizerAdapter
from models.transcription.transcription_transcriber import AudioTranscriber
from errors import AudioPipelineError

from .audio import TARGET_SAMPLE_RATE, TARGET_SAMPLE_WIDTH, read_pcm16_wav, sha256_file
from .metrics import character_error_rate


class EvaluationAudioSource:
    """Minimal recorder shape consumed by ``AudioTranscriber``."""

    SAMPLE_RATE = TARGET_SAMPLE_RATE
    SAMPLE_WIDTH = TARGET_SAMPLE_WIDTH
    channels = 1


def _load_row(dataset_dir: Path, condition: str, item_id: str | None) -> dict[str, str]:
    metadata_path = dataset_dir / "metadata.csv"
    with metadata_path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    required = {"id", "condition", "audio_path", "transcript", "duration_seconds"}
    missing = required.difference(rows[0].keys() if rows else set())
    if missing:
        raise ValueError(f"{metadata_path}: missing columns: {', '.join(sorted(missing))}")
    candidates = [
        row for row in rows
        if row["condition"] == condition and (item_id is None or row["id"] == item_id)
    ]
    if not candidates:
        selector = f"id={item_id!r}" if item_id else "the first matching id"
        raise ValueError(f"{metadata_path}: no {condition!r} row found for {selector}")
    return candidates[0]


def _resolve_dataset_path(dataset_dir: Path, relative_path: str) -> Path:
    root = dataset_dir.resolve()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"metadata path escapes dataset directory: {relative_path}")
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def _read_pcm16(path: Path) -> bytes:
    samples, sample_rate = read_pcm16_wav(path)
    if sample_rate != TARGET_SAMPLE_RATE or samples.ndim != 1:
        raise ValueError(f"{path}: integration input is not 16 kHz mono WAV")
    return np.clip(np.rint(samples * 32768.0), -32768, 32767).astype("<i2").tobytes()


def _segment_audio(raw_audio: bytes) -> list[Any]:
    """Run the same VAD adapter used by the recorder on one audio clip."""

    adapter = VadRecognizerAdapter(
        native_sample_rate=TARGET_SAMPLE_RATE,
        native_sample_width=TARGET_SAMPLE_WIDTH,
        native_channels=1,
    )
    frame_bytes = FRAME_SAMPLES * TARGET_SAMPLE_WIDTH
    segments: list[Any] = []
    for offset in range(0, len(raw_audio), frame_bytes * 4):
        segments.extend(adapter.process(raw_audio[offset : offset + frame_bytes * 4]))
    final_segment = adapter.flush()
    if final_segment is not None:
        segments.append(final_segment)
    return segments


def run_vrct_transcription_test(
    *,
    repo_root: Path,
    dataset_dir: Path,
    output_path: Path,
    condition: str = "clean",
    item_id: str | None = None,
    engine: str = "Whisper",
    model: str = "base",
    compute_type: str = "int8",
) -> dict[str, object]:
    """Run one clip through VRCT VAD, transcription, and transcript storage."""

    dataset_dir = dataset_dir.resolve()
    if engine not in {"Whisper", "Google"}:
        raise ValueError(f"unsupported integration test engine: {engine}")
    row = _load_row(dataset_dir, condition, item_id)
    source_path = _resolve_dataset_path(dataset_dir, row["audio_path"])
    raw_audio = _read_pcm16(source_path)

    vad_started = time.perf_counter()
    segments = _segment_audio(raw_audio)
    vad_seconds = time.perf_counter() - vad_started
    if not segments:
        raise RuntimeError(f"VAD emitted no speech segment for {source_path}")

    load_started = time.perf_counter()
    transcriber = AudioTranscriber(
        speaker=False,
        source=EvaluationAudioSource(),
        phrase_timeout=3,
        max_phrases=10,
        transcription_engine=engine,
        root=str(repo_root.resolve()),
        whisper_weight_type=model if engine == "Whisper" else None,
        compute_type=compute_type,
        vad_segmented=True,
        source_label="mic",
    )
    model_load_seconds = time.perf_counter() - load_started

    audio_queue: Queue = Queue()
    timestamp = datetime.now()
    for segment in segments:
        audio_queue.put((segment.audio, timestamp, segment.reason))
        timestamp += timedelta(milliseconds=segment.duration_ms)

    asr_started = time.perf_counter()
    pipeline_error = ""
    try:
        transcribed = transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])
    except AudioPipelineError as error:
        transcribed = False
        pipeline_error = type(error).__name__
    asr_seconds = time.perf_counter() - asr_started
    transcript = transcriber.getTranscript()
    hypothesis = str(transcript.get("text", "") or "")
    result = {
        "test": "vrct_vad_to_transcription",
        "engine": engine,
        "model": model if engine == "Whisper" else None,
        "compute_type": compute_type if engine == "Whisper" else None,
        "condition": condition,
        "id": row["id"],
        "audio_path": row["audio_path"],
        "reference": row["transcript"],
        "hypothesis": hypothesis,
        "cer": character_error_rate(row["transcript"], hypothesis),
        "vad_segment_count": len(segments),
        "vad_reasons": [segment.reason for segment in segments],
        "queue_drained": audio_queue.empty(),
        "transcribed": transcribed,
        "asr_attempts": transcriber.asr_attempts,
        "asr_successes": transcriber.asr_successes,
        "pipeline_error": pipeline_error,
        "last_recognition_error": transcriber.last_recognition_error,
        "confidence": transcript.get("confidence", 0.0),
        "vad_seconds": vad_seconds,
        "model_load_seconds": model_load_seconds,
        "asr_seconds": asr_seconds,
        "passed": bool(
            hypothesis
            and audio_queue.empty()
            and transcriber.asr_successes > 0
            and not pipeline_error
        ),
        "dataset_manifest_sha256": sha256_file(dataset_dir / "manifest.json")
        if (dataset_dir / "manifest.json").is_file()
        else None,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--condition", default="clean")
    parser.add_argument("--id", dest="item_id")
    parser.add_argument("--engine", choices=("Whisper", "Google"), default="Whisper")
    parser.add_argument("--model", default="base")
    parser.add_argument("--compute-type", default="int8")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = run_vrct_transcription_test(
            repo_root=args.repo_root,
            dataset_dir=args.dataset_dir,
            output_path=args.output,
            condition=args.condition,
            item_id=args.item_id,
            engine=args.engine,
            model=args.model,
            compute_type=args.compute_type,
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
    print(
        f"VRCT transcription test passed={result['passed']} "
        f"segments={result['vad_segment_count']} "
        f"asr_successes={result['asr_successes']} "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
