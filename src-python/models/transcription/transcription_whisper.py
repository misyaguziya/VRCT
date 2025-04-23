from os import path as os_path, makedirs as os_makedirs
from requests import get as requests_get
from typing import Callable
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

def downloadFile(url, path, func=None):
    try:
        res = requests_get(url, stream=True)
        res.raise_for_status()
        file_size = int(res.headers.get('content-length', 0))
        total_chunk = 0
        with open(os_path.join(path), 'wb') as file:
            for chunk in res.iter_content(chunk_size=1024*2000):
                file.write(chunk)
                if isinstance(func, Callable):
                    total_chunk += len(chunk)
                    func(total_chunk/file_size)
    except Exception:
        pass

def checkWhisperWeight(root, weight_type):
    path = os_path.join(root, "weights", "whisper", weight_type)
    result = False
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
        result = True
    except Exception:
        pass
    return result

def downloadWhisperWeight(root, weight_type, callback=None, end_callback=None):
    path = os_path.join(root, "weights", "whisper", weight_type)
    os_makedirs(path, exist_ok=True)
    if checkWhisperWeight(root, weight_type) is False:
        for filename in _FILENAMES:
            file_path = os_path.join(path, filename)
            url = huggingface_hub.hf_hub_url(_MODELS[weight_type], filename)
            downloadFile(url, file_path, func=callback if filename == "model.bin" else None)
    if isinstance(end_callback, Callable):
        end_callback()

def getWhisperModel(root, weight_type, device="cpu", device_index=0):
    path = os_path.join(root, "weights", "whisper", weight_type)
    compute_type = getBestComputeType(device, device_index)
    return WhisperModel(
        path,
        device=device,
        device_index=device_index,
        compute_type=compute_type,
        cpu_threads=4,
        num_workers=1,
        local_files_only=True,
    )

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