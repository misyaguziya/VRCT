import tempfile
from zipfile import ZipFile
from os import path as os_path
from os import makedirs as os_makedirs
from requests import get as requests_get
from typing import Callable, Optional
import hashlib
import transformers
from utils import errorLogging


"""Utilities for downloading and verifying CTranslate2 weights and tokenizers.

This module provides a small, dependency-light set of helpers used by the
translation layer. It purposely keeps behavior resilient: network errors are
logged (via utils.errorLogging) and the functions return/complete without
raising, which matches the repository's defensive style.
"""

ctranslate2_weights = {
    "small": {
        "url": "https://github.com/misyaguziya/VRCT-weights/releases/download/v1.0/m2m100_418m.zip",
        "directory_name": "m2m100_418m",
        "tokenizer": "facebook/m2m100_418M",
        "hash": {
            "model.bin": "e7c26a9abb5260abd0268fbe3040714070dec254a990b4d7fd3f74c5230e3acb",
            "sentencepiece.model": "d8f7c76ed2a5e0822be39f0a4f95a55eb19c78f4593ce609e2edbc2aea4d380a",
            "shared_vocabulary.txt": "bd440aa21b8ca3453fc792a0018a1f3fe68b3464aadddd4d16a4b72f73c86d8c",
        },
    },
    "large": {
        "url": "https://github.com/misyaguziya/VRCT-weights/releases/download/v1.0/m2m100_12b.zip",
        "directory_name": "m2m100_12b",
        "tokenizer": "facebook/m2m100_1.2b",
        "hash": {
            "model.bin": "abb7bf4ba7e5e016b6e3ed480c752459b2f783ac8fca372e7587675e5bf3a919",
            "sentencepiece.model": "d8f7c76ed2a5e0822be39f0a4f95a55eb19c78f4593ce609e2edbc2aea4d380a",
            "shared_vocabulary.txt": "bd440aa21b8ca3453fc792a0018a1f3fe68b3464aadddd4d16a4b72f73c86d8c",
        },
    },
}


def calculate_file_hash(file_path: str, block_size: int = 65536) -> str:
    hash_object = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            hash_object.update(block)
    return hash_object.hexdigest()


def checkCTranslate2Weight(root: str, weight_type: str = "small") -> bool:
    """Return True if the requested weight files exist and match their hashes.

    This function intentionally avoids raising: callers use the boolean to
    decide whether to (re)download weights.
    """
    weight_info = ctranslate2_weights.get(weight_type)
    if weight_info is None:
        return False
    weight_directory_name = weight_info["directory_name"]
    hash_data = weight_info["hash"]
    files = ["model.bin", "sentencepiece.model", "shared_vocabulary.txt"]
    base_path = os_path.join(root, "weights", "ctranslate2")
    # quick existence check
    for f in files:
        p = os_path.join(base_path, weight_directory_name, f)
        if not os_path.exists(p):
            return False
    # verify hashes
    for f in files:
        p = os_path.join(base_path, weight_directory_name, f)
        try:
            if calculate_file_hash(p) != hash_data[f]:
                return False
        except Exception:
            errorLogging()
            return False
    return True


def downloadCTranslate2Weight(root: str, weight_type: str = "small", callback: Optional[Callable[[float], None]] = None, end_callback: Optional[Callable[[], None]] = None) -> None:
    """Download and extract ctranslate2 weights for the given type.

    callback receives a float between 0 and 1 for progress when available.
    end_callback is invoked after success or failure to allow caller cleanup.
    """
    weight_info = ctranslate2_weights.get(weight_type)
    if weight_info is None:
        return
    url = weight_info["url"]
    filename = "weight.zip"
    dst_path = os_path.join(root, "weights", "ctranslate2")
    os_makedirs(dst_path, exist_ok=True)
    if checkCTranslate2Weight(root, weight_type):
        if callable(end_callback):
            end_callback()
        return
    try:
        with tempfile.TemporaryDirectory() as tmp_path:
            res = requests_get(url, stream=True, timeout=30)
            total = int(res.headers.get("content-length", 0) or 0)
            written = 0
            out_path = os_path.join(tmp_path, filename)
            with open(out_path, "wb") as out:
                for chunk in res.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    out.write(chunk)
                    written += len(chunk)
                    if callable(callback) and total:
                        try:
                            callback(written / total)
                        except Exception:
                            errorLogging()
            with ZipFile(out_path) as zf:
                zf.extractall(dst_path)
    except Exception:
        errorLogging()
    finally:
        if callable(end_callback):
            end_callback()


def downloadCTranslate2Tokenizer(root: str, weight_type: str = "small") -> None:
    """Ensure a tokenizer for the requested weight is available (cached).

    This will attempt to download the tokenizer via Hugging Face's transformers
    and cache it under the weights directory. It logs failures instead of
    raising to keep runtime resilient during startup.
    """
    weight_info = ctranslate2_weights.get(weight_type)
    if weight_info is None:
        return
    directory_name = weight_info["directory_name"]
    tokenizer_name = weight_info["tokenizer"]
    tokenizer_cache = os_path.join(root, "weights", "ctranslate2", directory_name, "tokenizer")
    try:
        os_makedirs(tokenizer_cache, exist_ok=True)
        transformers.AutoTokenizer.from_pretrained(tokenizer_name, cache_dir=tokenizer_cache)
    except Exception:
        errorLogging()