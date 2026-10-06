import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from tools.whisper_eval.audio import (
    TARGET_SAMPLE_RATE,
    deterministic_seed,
    make_noise_variant,
    read_pcm16_wav,
    write_pcm16_wav,
)
from tools.whisper_eval.metrics import character_error_rate, normalize_transcript
from tools.whisper_eval.prepare_common_voice import _resolve_source, prepare_dataset


class TestEvaluationHelpers(unittest.TestCase):
    def test_normalize_transcript_and_cer_are_character_based(self) -> None:
        self.assertEqual(normalize_transcript(" ＡＢＣ\n"), "ABC")
        self.assertEqual(character_error_rate("こんにちは", "こんにちは"), 0.0)
        self.assertAlmostEqual(character_error_rate("あいうえお", "あいうお"), 0.2)

    def test_noise_variant_is_reproducible(self) -> None:
        clean = np.full(16_000, 0.1, dtype=np.float32)
        first = make_noise_variant(
            clean,
            noise_kind="white",
            snr_db=20,
            seed=deterministic_seed("clip", "white_snr20"),
        )
        second = make_noise_variant(
            clean,
            noise_kind="white",
            snr_db=20,
            seed=deterministic_seed("clip", "white_snr20"),
        )
        np.testing.assert_array_equal(first, second)
        self.assertFalse(np.array_equal(first, clean))

    def test_prepare_dataset_writes_manifest_and_all_noise_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "commonvoice"
            clips_dir = input_dir / "clips"
            clips_dir.mkdir(parents=True)
            output_dir = root / "dataset"
            noise_path = root / "environment.wav"

            write_pcm16_wav(
                noise_path,
                np.sin(np.arange(TARGET_SAMPLE_RATE) * 0.1).astype(np.float32) * 0.1,
                TARGET_SAMPLE_RATE,
            )
            rows = [
                ("short one", "話します", "speaker-a"),
                ("short two", "聞きます", "speaker-b"),
                ("medium one", "これは中程度の長さの日本語テキストです", "speaker-c"),
                ("medium two", "こちらも中程度の長さを持つ発話サンプルです", "speaker-a"),
                (
                    "long one",
                    "これは評価用の十分に長い日本語発話サンプルとして使用します。複数の語を含む文章です",
                    "speaker-b",
                ),
                (
                    "long two",
                    "複数話者と異なる発話長を確認するための長いテスト音声です。日本語認識評価の例です",
                    "speaker-c",
                ),
            ]
            for index, (_label, sentence, _speaker) in enumerate(rows):
                write_pcm16_wav(
                    clips_dir / f"clip-{index}.wav",
                    np.zeros(TARGET_SAMPLE_RATE // 10, dtype=np.float32),
                    TARGET_SAMPLE_RATE,
                )

            tsv_path = input_dir / "validated.tsv"
            with tsv_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(
                    output,
                    fieldnames=["path", "sentence", "client_id"],
                    delimiter="\t",
                )
                writer.writeheader()
                for index, (_label, sentence, speaker) in enumerate(rows):
                    writer.writerow(
                        {
                            "path": f"clips/clip-{index}.wav",
                            "sentence": sentence,
                            "client_id": speaker,
                        }
                    )

            manifest = prepare_dataset(
                input_dir=input_dir,
                tsv_path=tsv_path,
                output_dir=output_dir,
                environment_noise_path=noise_path,
                count=6,
                seed=20260911,
                ffmpeg="ffmpeg",
                source_name="test dataset",
                source_url="https://example.invalid/dataset",
                license_name="CC0-1.0",
                dataset_version="test-version",
            )

            self.assertEqual(manifest["count"], 6)
            self.assertEqual(len(manifest["items"]), 6)
            self.assertTrue((output_dir / "manifest.json").is_file())
            with (output_dir / "metadata.csv").open(encoding="utf-8", newline="") as source:
                metadata = list(csv.DictReader(source))
            self.assertEqual(len(metadata), 30)
            self.assertEqual(
                {row["condition"] for row in metadata},
                {
                    "clean",
                    "white_snr10",
                    "white_snr20",
                    "environment_snr10",
                    "environment_snr20",
                },
            )
            prepared_audio, sample_rate = read_pcm16_wav(output_dir / metadata[0]["audio_path"])
            self.assertEqual(sample_rate, TARGET_SAMPLE_RATE)
            self.assertEqual(prepared_audio.ndim, 1)

            saved_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_manifest["source"]["license"], "CC0-1.0")

    def test_prepare_dataset_rejects_metadata_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "commonvoice"
            input_dir.mkdir()
            with self.assertRaises(ValueError):
                _resolve_source(input_dir, "../outside.wav")

    def test_resolve_source_supports_common_voice_clip_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir) / "commonvoice"
            clips_dir = input_dir / "clips"
            clips_dir.mkdir(parents=True)
            clip_path = clips_dir / "clip.wav"
            clip_path.write_bytes(b"test")

            self.assertEqual(_resolve_source(input_dir, "clip.wav"), clip_path.resolve())

if __name__ == "__main__":
    unittest.main()
