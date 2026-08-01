import argparse
import json
import wave
from pathlib import Path
from typing import Any

import numpy as np
from faster_whisper import WhisperModel

from models.transcription.audio_pipeline import Pcm16MonoNormalizer
from models.transcription.transcription_evaluation import evaluate_case, summarize


def load_wav(path: Path) -> tuple[np.ndarray, float]:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        raw_audio = wav_file.readframes(wav_file.getnframes())
    normalized = Pcm16MonoNormalizer(sample_rate, sample_width, channels).process(raw_audio)
    audio = np.frombuffer(normalized, dtype="<i2").astype(np.float32) / 32768.0
    return audio, len(audio) / 16000 * 1000


def run_evaluation(
    manifest_path: Path,
    model_path: Path,
    device: str,
    compute_type: str,
) -> dict[str, Any]:
    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)
    model = WhisperModel(str(model_path), device=device, compute_type=compute_type, local_files_only=True)
    results = []

    for case in manifest.get("cases", []):
        audio_path = (manifest_path.parent / case["audio"]).resolve()
        audio, duration_ms = load_wav(audio_path)

        def recognize() -> str:
            segments, _ = model.transcribe(
                audio,
                language=case.get("language"),
                beam_size=int(case.get("beam_size", 5)),
                temperature=0.0,
                without_timestamps=True,
                vad_filter=True,
            )
            return "".join(segment.text for segment in segments).strip()

        results.append(evaluate_case(case["id"], case["reference"], duration_ms, recognize))

    return {
        "model": str(model_path),
        "summary": summarize(results),
        "results": [result.to_dict() for result in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate VRCT transcription with a shared WAV manifest")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--model", type=Path, default=Path("weights/whisper/base"))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_evaluation(args.manifest, args.model, args.device, args.compute_type)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output is None:
        print(output)
    else:
        args.output.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()