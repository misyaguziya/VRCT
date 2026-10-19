"""Helpers for downloading and loading Whisper (faster-whisper) models.

This module exposes small utilities used by the transcription subsystem:
- downloadFile: stream-download a file with optional progress callback
- checkWhisperWeight: quick local availability check
- downloadWhisperWeight: download model artifacts from HF hub
- getWhisperModel: construct and return a WhisperModel instance

The functions are defensive: failures are caught and reported by the caller.
"""

from os import path as os_path, makedirs as os_makedirs, remove as os_remove
from time import sleep
from requests import get as requests_get
from requests.exceptions import HTTPError
from typing import Callable, Optional
import logging
from utils import getBestComputeType, isWeightVerifiedCache, writeWeightVerifiedCache, errorLogging, printLog

# 起動時の初回ダウンロードで一時的なネットワーク断 (接続リセット・HF Hub の
# 429/503 等) が起きても、1 回の取りこぼしで「AIモデル未検出。VRCTを再起動して
# ください」通知に落ちないよう、タイムアウトと指数バックオフ付きの再試行を行う。
_DOWNLOAD_TIMEOUT = (10, 60)  # (connect, read) 秒
_DOWNLOAD_MAX_ATTEMPTS = 3
_DOWNLOAD_RETRY_BACKOFF = 2  # 秒。attempt 番号を掛けて待機 (2s, 4s, ...)

# Optional deps; None fallback lets checkWhisperWeight etc. return False
# gracefully when the package is missing.
try:
    from faster_whisper import WhisperModel  # noqa: F401
except Exception:
    WhisperModel = None  # type: ignore

try:
    import huggingface_hub  # noqa: F401
except Exception:
    huggingface_hub = None  # type: ignore

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

def downloadFile(url: str, path: str, func: Optional[Callable[[float], None]] = None) -> bool:
    """Download a file from `url` to `path`.

    Args:
        url: remote URL to download from
        path: local filepath to write
        func: optional callback(progress: float) called with a 0.0-1.0 progress

    Returns:
        True on success, False if every attempt failed. Transient network
        errors are retried with a short backoff before giving up so a single
        connection reset during the first-run model download doesn't leave the
        app permanently reporting "AI models have not been detected".
    """
    for attempt in range(1, _DOWNLOAD_MAX_ATTEMPTS + 1):
        try:
            res = requests_get(url, stream=True, timeout=_DOWNLOAD_TIMEOUT)
            res.raise_for_status()
            file_size = int(res.headers.get('content-length', 0))
            total_chunk = 0
            with open(os_path.join(path), 'wb') as file:
                for chunk in res.iter_content(chunk_size=1024 * 2000):
                    file.write(chunk)
                    if callable(func) and file_size:
                        total_chunk += len(chunk)
                        func(total_chunk / file_size)
            return True
        except Exception as e:
            errorLogging()
            # Remove any partial/corrupt file so the retry below, or the
            # post-download WhisperModel verification in checkWhisperWeight,
            # doesn't see stale truncated bytes from the failed attempt.
            try:
                if os_path.exists(path):
                    os_remove(path)
            except Exception:
                pass
            # 404 等の恒久エラー (そのリポジトリに存在しないファイル) は
            # 再試行しても無駄なので即座に打ち切る。429/5xx や接続エラーのみ再試行。
            status = getattr(getattr(e, "response", None), "status_code", None)
            if isinstance(e, HTTPError) and status is not None and 400 <= status < 500 and status != 429:
                return False
            if attempt < _DOWNLOAD_MAX_ATTEMPTS:
                printLog(f"Whisper file download failed, retrying ({attempt}/{_DOWNLOAD_MAX_ATTEMPTS - 1})", url)
                sleep(_DOWNLOAD_RETRY_BACKOFF * attempt)
    return False

def checkWhisperWeight(root: str, weight_type: str) -> bool:
    """Return True if a Whisper model for `weight_type` is loadable from disk.

    This attempts to construct a local `WhisperModel` with local_files_only=True
    to verify required files exist and are compatible.
    """
    path = os_path.join(root, "weights", "whisper", weight_type)

    if isWeightVerifiedCache(path):
        return True

    if WhisperModel is None:
        return False
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
        writeWeightVerifiedCache(path)
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
        repo_id = _MODELS[weight_type]
        # _FILENAMES は複数の変換元リポジトリ (Systran, Zoont, deepdml 等)
        # に共通する候補の和集合。実際のファイル構成はリポジトリごとに
        # 異なる (例: Systran 系は vocabulary.txt のみ、Zoont/deepdml 系は
        # preprocessor_config.json/vocabulary.json を含み vocabulary.txt が
        # 無い) ため、存在しないファイルを固定リストのままダウンロードしよ
        # うとすると 404 になる。実在するファイルのみに絞り込む。
        try:
            available_files = set(huggingface_hub.list_repo_files(repo_id))
        except Exception:
            errorLogging()
            # 一覧取得に失敗した場合は従来通り全候補で試す (完全に
            # ダウンロードできなくても checkWhisperWeight 側の
            # WhisperModel ロード検証で最終的に弾かれる)。
            available_files = set(_FILENAMES)

        for filename in _FILENAMES:
            if filename not in available_files:
                continue
            file_path = os_path.join(path, filename)
            url = huggingface_hub.hf_hub_url(repo_id, filename)
            downloadFile(url, file_path, func=callback if filename == "model.bin" else None)
    if callable(end_callback):
        end_callback()

def getWhisperModel(
    root: str,
    weight_type: str,
    device: str = "cpu",
    device_index: int = 0,
    compute_type: str = "auto",
):
    """Return a `WhisperModel` instance loaded from local weights.

    Raises:
        ValueError: when VRAM shortage is detected (wrapped from RuntimeError)
        Exception: other loading errors are propagated.
    """
    if WhisperModel is None:
        raise RuntimeError("faster_whisper is not installed")
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