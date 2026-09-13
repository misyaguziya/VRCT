"""Audio preparation helpers for the VRCT transcription evaluation.

The benchmark uses a deliberately small audio contract: 16 kHz, mono, signed
16-bit PCM WAV.  MP3 and other input formats are converted through the
user-provided ffmpeg executable; no audio decoder is downloaded implicitly.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import wave
from pathlib import Path
import numpy as np


TARGET_SAMPLE_RATE = 16_000
TARGET_CHANNELS = 1
TARGET_SAMPLE_WIDTH = 2


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_path(path: Path | str) -> Path:
    return Path(path).expanduser()


def read_pcm16_wav(path: Path | str) -> tuple[np.ndarray, int]:
    """Read a PCM16 WAV and return mono-capable samples as float32.

    The returned array is shaped ``(frames, channels)`` for multi-channel
    files and ``(frames,)`` for mono files. Values are in approximately
    ``[-1.0, 1.0]``.
    """

    path = _as_path(path)
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        if sample_width != TARGET_SAMPLE_WIDTH:
            raise ValueError(f"{path}: expected 16-bit PCM WAV, got {sample_width * 8}-bit")
        raw = source.readframes(source.getnframes())

    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        if samples.size % channels:
            raise ValueError(f"{path}: WAV frame data is truncated")
        samples = samples.reshape(-1, channels)
    return samples, sample_rate


def to_mono(samples: np.ndarray) -> np.ndarray:
    """Downmix a sample array without clipping."""

    if samples.ndim == 1:
        return samples.astype(np.float32, copy=False)
    if samples.ndim != 2:
        raise ValueError(f"expected a 1D or 2D sample array, got {samples.ndim}D")
    return np.mean(samples, axis=1, dtype=np.float32)


def write_pcm16_wav(path: Path | str, samples: np.ndarray, sample_rate: int) -> None:
    """Write mono float samples as signed 16-bit PCM WAV."""

    path = _as_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mono = to_mono(np.asarray(samples, dtype=np.float32))
    pcm = np.clip(np.rint(mono * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(TARGET_CHANNELS)
        output.setsampwidth(TARGET_SAMPLE_WIDTH)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


def is_standard_wav(path: Path | str) -> bool:
    """Return whether a WAV already satisfies the benchmark audio contract."""

    try:
        with wave.open(str(_as_path(path)), "rb") as source:
            return (
                source.getnchannels() == TARGET_CHANNELS
                and source.getsampwidth() == TARGET_SAMPLE_WIDTH
                and source.getframerate() == TARGET_SAMPLE_RATE
            )
    except (OSError, wave.Error):
        return False


def _ffmpeg_path(ffmpeg: str) -> str:
    resolved = shutil.which(ffmpeg)
    if resolved is None:
        raise RuntimeError(
            "ffmpeg is required to convert non-WAV/Common Voice audio. "
            "Install ffmpeg and ensure it is on PATH, or pass --ffmpeg."
        )
    return resolved


def convert_to_standard_wav(
    source: Path | str,
    destination: Path | str,
    *,
    ffmpeg: str = "ffmpeg",
) -> np.ndarray:
    """Convert an audio file to the benchmark format and return its samples.

    Existing standard WAV files are decoded with the Python standard library.
    Other formats are converted with ffmpeg using explicit mono, sample-rate,
    and sample-format options. The resulting samples receive light RMS/peak
    normalization before being written.
    """

    source = _as_path(source)
    destination = _as_path(destination)
    if not source.is_file():
        raise FileNotFoundError(source)

    if is_standard_wav(source):
        samples, sample_rate = read_pcm16_wav(source)
        normalized = normalize_light(to_mono(samples))
        write_pcm16_wav(destination, normalized, sample_rate)
        return normalized

    resolved_ffmpeg = _ffmpeg_path(ffmpeg)
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        resolved_ffmpeg,
        "-v",
        "error",
        "-y",
        "-i",
        str(source),
        "-ac",
        str(TARGET_CHANNELS),
        "-ar",
        str(TARGET_SAMPLE_RATE),
        "-sample_fmt",
        "s16",
        str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        destination.unlink(missing_ok=True)
        detail = completed.stderr.strip() or "unknown ffmpeg error"
        raise RuntimeError(f"ffmpeg failed for {source}: {detail}")

    samples, sample_rate = read_pcm16_wav(destination)
    normalized = normalize_light(to_mono(samples))
    write_pcm16_wav(destination, normalized, sample_rate)
    return normalized


def normalize_light(
    samples: np.ndarray,
    *,
    target_rms_dbfs: float = -24.0,
    max_gain_db: float = 6.0,
    peak_dbfs: float = -1.0,
) -> np.ndarray:
    """Apply conservative RMS and peak normalization.

    Quiet recordings are amplified by at most ``max_gain_db``. Loud recordings
    are only attenuated when they exceed the peak ceiling. This avoids the
    aggressive noise suppression that can remove consonants and hurt recall.
    """

    result = np.asarray(samples, dtype=np.float32).copy()
    if result.size == 0:
        return result

    rms = float(np.sqrt(np.mean(np.square(result), dtype=np.float64)))
    if rms > 0.0:
        target_rms = 10.0 ** (target_rms_dbfs / 20.0)
        max_gain = 10.0 ** (max_gain_db / 20.0)
        result *= min(target_rms / rms, max_gain)

    peak = float(np.max(np.abs(result), initial=0.0))
    peak_limit = 10.0 ** (peak_dbfs / 20.0)
    if peak > peak_limit:
        result *= peak_limit / peak
    return np.clip(result, -1.0, 1.0)


def deterministic_seed(*parts: object) -> int:
    """Create a stable uint64 seed from arbitrary identifiers."""

    joined = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(joined).digest()[:8], "little")


def _noise_window(noise: np.ndarray, length: int, rng: np.random.Generator) -> np.ndarray:
    if noise.size == 0:
        raise ValueError("noise input is empty")
    noise = np.asarray(noise, dtype=np.float32).reshape(-1)
    start = int(rng.integers(0, noise.size)) if noise.size > 1 else 0
    indices = (np.arange(length, dtype=np.int64) + start) % noise.size
    return noise[indices]


def create_white_noise(length: int, rng: np.random.Generator) -> np.ndarray:
    """Create deterministic zero-mean white noise."""

    return rng.standard_normal(length).astype(np.float32)


def mix_at_snr(
    clean: np.ndarray,
    noise: np.ndarray,
    snr_db: float,
) -> np.ndarray:
    """Mix noise into clean audio at the requested RMS SNR."""

    clean = np.asarray(clean, dtype=np.float32).reshape(-1)
    noise = np.asarray(noise, dtype=np.float32).reshape(-1)
    if clean.size == 0 or noise.size == 0:
        return clean.copy()

    clean_rms = float(np.sqrt(np.mean(np.square(clean), dtype=np.float64)))
    noise_rms = float(np.sqrt(np.mean(np.square(noise), dtype=np.float64)))
    if clean_rms == 0.0 or noise_rms == 0.0:
        return clean.copy()

    desired_noise_rms = clean_rms / (10.0 ** (snr_db / 20.0))
    mixed = clean + noise * (desired_noise_rms / noise_rms)
    peak = float(np.max(np.abs(mixed), initial=0.0))
    if peak > 0.98:
        mixed *= 0.98 / peak
    return np.clip(mixed, -1.0, 1.0).astype(np.float32)


def make_noise_variant(
    clean: np.ndarray,
    *,
    noise_kind: str,
    snr_db: float,
    seed: int,
    environment_noise: np.ndarray | None = None,
) -> np.ndarray:
    """Create one deterministic white/environment noise variant."""

    rng = np.random.default_rng(seed)
    if noise_kind == "white":
        noise = create_white_noise(len(clean), rng)
    elif noise_kind == "environment":
        if environment_noise is None:
            raise ValueError("environment noise is required for environment variants")
        noise = _noise_window(environment_noise, len(clean), rng)
        noise = noise - float(np.mean(noise, dtype=np.float64))
    else:
        raise ValueError(f"unsupported noise kind: {noise_kind}")
    return mix_at_snr(clean, noise, snr_db)
