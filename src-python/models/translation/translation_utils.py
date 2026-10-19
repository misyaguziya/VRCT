from os import path as os_path
from os import makedirs as os_makedirs
from os import rename as os_rename
from os import remove as os_remove
from shutil import rmtree as shutil_rmtree
from time import sleep
from requests import get as requests_get
from requests.exceptions import HTTPError
from typing import Callable
import yaml

try:
    from utils import errorLogging, getBestComputeType, isWeightVerifiedCache, writeWeightVerifiedCache, printLog
except Exception:
    import sys
    print(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from utils import errorLogging, getBestComputeType, isWeightVerifiedCache, writeWeightVerifiedCache, printLog

# 起動時の初回ダウンロードで一時的なネットワーク断が起きても 1 回の取りこぼしで
# 「AIモデル未検出。VRCTを再起動してください」通知に落ちないよう、タイムアウトと
# 指数バックオフ付きの再試行を行う。
_DOWNLOAD_TIMEOUT = (10, 60)  # (connect, read) 秒
_DOWNLOAD_MAX_ATTEMPTS = 3
_DOWNLOAD_RETRY_BACKOFF = 2  # 秒。attempt 番号を掛けて待機 (2s, 4s, ...)

# Optional runtime deps; None fallback disables the corresponding features
# (check/download/tokenizer) when the package is unavailable.
try:
    import ctranslate2  # noqa: F401
except Exception:
    ctranslate2 = None  # type: ignore

try:
    from huggingface_hub import hf_hub_url, list_repo_files  # noqa: F401
except Exception:
    hf_hub_url = None  # type: ignore
    list_repo_files = None  # type: ignore

try:
    import transformers  # noqa: F401
except Exception:
    transformers = None  # type: ignore


"""Utilities for downloading and verifying CTranslate2 weights and tokenizers.

This module provides a small, dependency-light set of helpers used by the
translation layer. It purposely keeps behavior resilient: network errors are
logged (via utils.errorLogging) and the functions return/complete without
raising, which matches the repository's defensive style.
"""

ctranslate2_weights = {
    "m2m100_418M-ct2-int8": {
        "hf_repo": "jncraton/m2m100_418M-ct2-int8",
        "directory_name": "m2m100_418M-ct2-int8",
        "tokenizer": "facebook/m2m100_418M",
    },
    "m2m100_1.2B-ct2-int8": {
        "hf_repo": "jncraton/m2m100_1.2B-ct2-int8",
        "directory_name": "m2m100_1.2B-ct2-int8",
        "tokenizer": "facebook/m2m100_1.2B",
    },
    "nllb-200-distilled-600M-ct2-int8": {
        "hf_repo": "JustFrederik/nllb-200-distilled-600M-ct2-int8",
        "directory_name": "nllb-200-distilled-600M-ct2-int8",
        "tokenizer": "facebook/nllb-200-distilled-600M",
    },
    "nllb-200-distilled-1.3B-ct2-int8": {
        "hf_repo": "OpenNMT/nllb-200-distilled-1.3B-ct2-int8",
        "directory_name": "nllb-200-distilled-1.3B-ct2-int8",
        "tokenizer": "facebook/nllb-200-distilled-1.3B",
    },
    "nllb-200-3.3B-ct2-int8": {
        "hf_repo": "OpenNMT/nllb-200-3.3B-ct2-int8",
        "directory_name": "nllb-200-3.3B-ct2-int8",
        "tokenizer": "facebook/nllb-200-3.3B",
    },
}

def backwardCompatibleRenameWeightsDir(root: str):
    # 後方互換のためファイル名を変更する
    legacy_dirs = {
        "m2m100_418M": "m2m100_418M-ct2-int8",
        "m2m100_12b": "m2m100_1.2B-ct2-int8",
    }

    for weight_type_old, weight_type_new in legacy_dirs.items():
        path = os_path.join(root, "weights", "ctranslate2", weight_type_new)
        old_path = os_path.join(root, "weights", "ctranslate2", weight_type_old)
        if not os_path.isdir(old_path):
            continue
        if os_path.isdir(path):
            # 新形式のディレクトリが既に存在する場合、旧形式は不要になったディスク領域なので削除する
            shutil_rmtree(old_path)
        else:
            os_rename(old_path, path)

def checkCTranslate2Weight(root: str, weight_type: str = "m2m100_418M-ct2-int8"):
    weight_directory_name = ctranslate2_weights[weight_type]["directory_name"]
    path = os_path.join(root, "weights", "ctranslate2", weight_directory_name)

    if isWeightVerifiedCache(path):
        return True

    try:
        if ctranslate2 is None:
            return False
        # モデルロード可能かどうかで判定
        compute_type = getBestComputeType("cpu", 0)
        ctranslate2.Translator(path, compute_type=compute_type)
        writeWeightVerifiedCache(path)
        return True
    except Exception:
        return False

def downloadCTranslate2Weight(root: str, weight_type: str = "m2m100_418M-ct2-int8", callback: Callable = None, end_callback: Callable = None) -> bool:
    if hf_hub_url is None or list_repo_files is None:
        return False
    hf_repo = ctranslate2_weights[weight_type]["hf_repo"]
    path = os_path.join(root, "weights", "ctranslate2", ctranslate2_weights[weight_type]["directory_name"])
    # 既にロード検証済みなら以降のネットワークアクセス (list_repo_files) を一切行わない。
    # list_repo_files は従来 try/except の外にあり、一時的な HF Hub 障害でここから
    # 例外が伝播してダウンロードスレッドごと死ぬ原因になっていた。
    if checkCTranslate2Weight(root, weight_type):
        return True

    files = None
    for attempt in range(1, _DOWNLOAD_MAX_ATTEMPTS + 1):
        try:
            files = list_repo_files(repo_id=hf_repo)
            break
        except Exception:
            errorLogging()
            if attempt < _DOWNLOAD_MAX_ATTEMPTS:
                printLog(f"CTranslate2 repo listing failed, retrying ({attempt}/{_DOWNLOAD_MAX_ATTEMPTS - 1})", hf_repo)
                sleep(_DOWNLOAD_RETRY_BACKOFF * attempt)
    if files is None:
        return False

    os_makedirs(path, exist_ok=True)
    base_dir = os_path.abspath(path)

    def downloadFile(url: str, file_path: str, func: Callable = None) -> bool:
        for attempt in range(1, _DOWNLOAD_MAX_ATTEMPTS + 1):
            try:
                res = requests_get(url, stream=True, timeout=_DOWNLOAD_TIMEOUT)
                res.raise_for_status()
                file_size = int(res.headers.get('content-length', 0))
                total_chunk = 0
                os_makedirs(os_path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb') as file:
                    for chunk in res.iter_content(chunk_size=1024*2000):
                        file.write(chunk)
                        if func is not None:
                            total_chunk += len(chunk)
                            if file_size > 0:
                                func(total_chunk/file_size)
                return True
            except Exception as e:
                errorLogging()
                try:
                    if os_path.exists(file_path):
                        os_remove(file_path)
                except Exception:
                    pass
                status = getattr(getattr(e, "response", None), "status_code", None)
                if isinstance(e, HTTPError) and status is not None and 400 <= status < 500 and status != 429:
                    return False
                if attempt < _DOWNLOAD_MAX_ATTEMPTS:
                    printLog(f"CTranslate2 file download failed, retrying ({attempt}/{_DOWNLOAD_MAX_ATTEMPTS - 1})", url)
                    sleep(_DOWNLOAD_RETRY_BACKOFF * attempt)
        return False

    all_succeeded = True
    for filename in files:
        # HFのfilenameはリモート由来。".."を含む場合はパストラバーサルの可能性があるため
        # 正規化して展開先ディレクトリ配下であることを確認してから書き込む
        normalized = os_path.normpath(filename)
        file_path = os_path.abspath(os_path.join(path, normalized))
        if not (file_path == base_dir or file_path.startswith(base_dir + os_path.sep)):
            errorLogging()
            all_succeeded = False
            continue
        url = hf_hub_url(hf_repo, filename)
        if not downloadFile(url, file_path, func=callback if filename == "model.bin" else None):
            all_succeeded = False

    if end_callback is not None:
        end_callback()
    return all_succeeded

def downloadCTranslate2Tokenizer(path: str, weight_type: str = "m2m100_418M-ct2-int8"):
    if transformers is None:
        return
    directory_name = ctranslate2_weights[weight_type]["directory_name"]
    tokenizer = ctranslate2_weights[weight_type]["tokenizer"]
    tokenizer_path = os_path.join(path, "weights", "ctranslate2", directory_name, "tokenizer")
    try:
        os_makedirs(tokenizer_path, exist_ok=True)
        transformers.AutoTokenizer.from_pretrained(tokenizer, cache_dir=tokenizer_path)
    except Exception:
        errorLogging()
        tokenizer_path = os_path.join("./weights", "ctranslate2", directory_name, "tokenizer")
        transformers.AutoTokenizer.from_pretrained(tokenizer, cache_dir=tokenizer_path)

def loadTranslatePromptConfig(root_path: str | None = None, prompt_filename: str | None = None) -> dict:
    # PyInstaller 展開後
    if root_path and prompt_filename and os_path.exists(os_path.join(root_path, "_internal", "translation_settings", "prompt", prompt_filename)):
        prompt_path = os_path.join(root_path, "_internal", "translation_settings", "prompt", prompt_filename)
    # src-python 直下実行
    elif prompt_filename and os_path.exists(os_path.join(os_path.dirname(__file__), "models", "translation", "translation_settings", "prompt", prompt_filename)):
        prompt_path = os_path.join(os_path.dirname(__file__), "models", "translation", "translation_settings", "prompt", prompt_filename)
    # translation フォルダ直下実行
    elif prompt_filename and os_path.exists(os_path.join(os_path.dirname(__file__), "translation_settings", "prompt", prompt_filename)):
        prompt_path = os_path.join(os_path.dirname(__file__), "translation_settings", "prompt", prompt_filename)
    else:
        raise FileNotFoundError(f"Prompt file not found: {prompt_filename}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# テスト用コード（直接実行時のみ）
if __name__ == "__main__":
    def progress_callback(percent):
        print(f"Download progress: {percent*100:.2f}%")

    def end_callback():
        print("Download finished.")

    root = "./"  # 必要に応じてパスを変更
    # for weight_type in ctranslate2_weights.keys():
    #     print(f"Testing download for: {weight_type}")
    #     downloadCTranslate2Weight(root, weight_type, callback=progress_callback, end_callback=end_callback)
    #     result = checkCTranslate2Weight(root, weight_type)
    #     print(f"Model loadable: {result}")
    #     break
    # downloadCTranslate2Tokenizer(root, "m2m100_418M-ct2-int8")

    # model download test
    downloadCTranslate2Weight(root, "nllb-200-distilled-1.3B", callback=progress_callback, end_callback=end_callback)
    result = checkCTranslate2Weight(root, "nllb-200-distilled-1.3B")
    print(f"Model loadable: {result}")