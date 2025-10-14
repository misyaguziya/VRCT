"""Helpers for downloading and loading Whisper (faster-whisper) models.

This module exposes small utilities used by the transcription subsystem:
- downloadFile: stream-download a file with optional progress callback
- checkWhisperWeight: quick local availability check
- downloadWhisperWeight: download model artifacts from HF hub
- getWhisperModel: construct and return a WhisperModel instance

The functions are defensive: failures are caught and reported by the caller.
"""

from os import path as os_path, makedirs as os_makedirs
from requests import get as requests_get
from typing import Callable, Optional
import huggingface_hub
from faster_whisper import WhisperModel
import logging
from utils import getBestComputeType

logger = logging.getLogger('faster_whisper')
logger.setLevel(logging.CRITICAL)

_MODELS = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large-v3-turbo-int8": "Zoont/faster-whisper-large-v3-turbo-int8-ct2", #794MB
    "large-v3-turbo": "deepdml/faster-whisper-large-v3-turbo-ct2", #1.58GB
}

_FILENAMES = [
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.txt",
    "vocabulary.json",
]

def downloadFile(url: str, path: str, func: Optional[Callable[[float], None]] = None) -> None:
    """Download a file from `url` to `path`.

    Args:
        url: remote URL to download from
        path: local filepath to write
        func: optional callback(progress: float) called with a 0.0-1.0 progress
    """
    try:
        res = requests_get(url, stream=True)
        res.raise_for_status()
        file_size = int(res.headers.get('content-length', 0))
        total_chunk = 0
        with open(os_path.join(path), 'wb') as file:
            for chunk in res.iter_content(chunk_size=1024 * 2000):
                file.write(chunk)
                if callable(func) and file_size:
                    total_chunk += len(chunk)
                    func(total_chunk / file_size)
    except Exception:
        # Silent failure here; caller may re-check or log
        pass

def checkWhisperWeight(root: str, weight_type: str) -> bool:
    """Return True if a Whisper model for `weight_type` is loadable from disk.

    This attempts to construct a local `WhisperModel` with local_files_only=True
    to verify required files exist and are compatible.
    """
    path = os_path.join(root, "weights", "whisper", weight_type)
    try:
        WhisperModel(
            path,
            device="cpu",
            device_index=0,
            compute_type="int8",
            cpu_threads=4,
            num_workers=1,
            local_files_only=True,
        )
        return True
    except Exception:
        return False

def downloadWhisperWeight(
    root: str,
    weight_type: str,
    callback: Optional[Callable[[float], None]] = None,
    end_callback: Optional[Callable[[], None]] = None,
) -> None:
    """Ensure Whisper weight files are present locally; download them if missing.

    Args:
        root: project root where `weights/whisper` lives
        weight_type: key from `_MODELS` (eg. "tiny", "base")
        callback: progress callback for the main model file
        end_callback: called when download completes
    """
    path = os_path.join(root, "weights", "whisper", weight_type)
    os_makedirs(path, exist_ok=True)
    if not checkWhisperWeight(root, weight_type):
        for filename in _FILENAMES:
            file_path = os_path.join(path, filename)
            url = huggingface_hub.hf_hub_url(_MODELS[weight_type], filename)
            downloadFile(url, file_path, func=callback if filename == "model.bin" else None)
    if callable(end_callback):
        end_callback()

def getWhisperModel(
    root: str,
    weight_type: str,
    device: str = "cpu",
    device_index: int = 0,
    compute_type: str = "auto",
) -> WhisperModel:
    """Return a `WhisperModel` instance loaded from local weights.

    Raises:
        ValueError: when VRAM shortage is detected (wrapped from RuntimeError)
        Exception: other loading errors are propagated.
    """
    path = os_path.join(root, "weights", "whisper", weight_type)
    if compute_type == "auto":
        compute_type = getBestComputeType(device, device_index)
    try:
        model = WhisperModel(
            path,
            device=device,
            device_index=device_index,
            compute_type=compute_type,
            cpu_threads=4,
            num_workers=1,
            local_files_only=True,
        )
        return model
    except RuntimeError as e:
        # Detect VRAM out-of-memory-like errors and raise a clear ValueError
        error_message = str(e)
        if "CUDA out of memory" in error_message or "CUBLAS_STATUS_ALLOC_FAILED" in error_message:
            raise ValueError("VRAM_OUT_OF_MEMORY", error_message)
        raise

if __name__ == "__main__":
    def callback(value):
        print(value)
        pass

    def end_callback():
        print("end")
        pass

    downloadWhisperWeight("./", "tiny", callback, end_callback)
    downloadWhisperWeight("./", "base", callback, end_callback)
    downloadWhisperWeight("./", "small", callback, end_callback)
    downloadWhisperWeight("./", "medium", callback, end_callback)
    downloadWhisperWeight("./", "large-v1", callback, end_callback)
    downloadWhisperWeight("./", "large-v2", callback, end_callback)
    downloadWhisperWeight("./", "large-v3", callback, end_callback)