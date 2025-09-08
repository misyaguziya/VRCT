from os import path as os_path
from os import makedirs as os_makedirs
from typing import Callable
import transformers
import ctranslate2
from huggingface_hub import hf_hub_url, list_repo_files
from requests import get as requests_get

try:
    from utils import errorLogging, getBestComputeType
except Exception:
    import sys
    print(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from utils import errorLogging, getBestComputeType

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

def checkCTranslate2Weight(root: str, weight_type: str = "m2m100_418M-ct2-int8"):
    weight_directory_name = ctranslate2_weights[weight_type]["directory_name"]
    path = os_path.join(root, "weights", "ctranslate2", weight_directory_name)
    try:
        # モデルロード可能かどうかで判定
        compute_type = getBestComputeType("cpu", 0)
        ctranslate2.Translator(path, compute_type=compute_type)
        return True
    except Exception:
        return False

def downloadCTranslate2Weight(root: str, weight_type: str = "m2m100_418M-ct2-int8", callback: Callable = None, end_callback: Callable = None):
    hf_repo = ctranslate2_weights[weight_type]["hf_repo"]
    files = list_repo_files(repo_id=hf_repo)
    path = os_path.join(root, "weights", "ctranslate2", ctranslate2_weights[weight_type]["directory_name"])
    if checkCTranslate2Weight(root, weight_type):
        return True
    os_makedirs(path, exist_ok=True)

    def downloadFile(url: str, file_path: str, func: Callable = None):
        try:
            res = requests_get(url, stream=True)
            res.raise_for_status()
            file_size = int(res.headers.get('content-length', 0))
            total_chunk = 0
            with open(file_path, 'wb') as file:
                for chunk in res.iter_content(chunk_size=1024*2000):
                    file.write(chunk)
                    if func is not None:
                        total_chunk += len(chunk)
                        func(total_chunk/file_size)
        except Exception:
            errorLogging()

    for filename in files:
        file_path = os_path.join(path, filename)
        url = hf_hub_url(hf_repo, filename)
        downloadFile(url, file_path, func=callback if filename == "model.bin" else None)

    if end_callback is not None:
        end_callback()

def downloadCTranslate2Tokenizer(path: str, weight_type: str = "m2m100_418M-ct2-int8"):
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