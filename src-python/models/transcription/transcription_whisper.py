"""Utility functions for downloading and managing Whisper models via faster_whisper and Hugging Face Hub."""
import logging
from os import makedirs as os_makedirs
from os import path as os_path
from typing import Any, Callable, Dict, List, Optional 

import huggingface_hub 
import requests 
from faster_whisper import WhisperModel 

from utils import getBestComputeType 

logger = logging.getLogger(__name__) 
faster_whisper_logger = logging.getLogger('faster_whisper')
faster_whisper_logger.setLevel(logging.WARNING) 


_MODELS: Dict[str, str] = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large-v3-turbo-int8": "Zoont/faster-whisper-large-v3-turbo-int8-ct2",
    "large-v3-turbo": "deepdml/faster-whisper-large-v3-turbo-ct2",
}

_FILENAMES: List[str] = [
    "config.json",
    "preprocessor_config.json", 
    "model.bin",
    "tokenizer.json",
    "vocabulary.txt", 
    "vocabulary.json", 
]

def downloadFile(url: str, file_path: str, progress_callback: Optional[Callable[[float], None]] = None) -> None:
    """
    Downloads a file from a URL to a local path, with an optional progress callback.

    Args:
        url: URL to download from.
        file_path: Local path to save the downloaded file.
        progress_callback: Optional function to call with download progress (0.0 to 1.0).
    """
    try:
        response = requests.get(url, stream=True, timeout=10) 
        response.raise_for_status() 
        
        file_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        os_makedirs(os_path.dirname(file_path), exist_ok=True)

        with open(file_path, 'wb') as file_handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024): 
                if chunk: 
                    file_handle.write(chunk)
                    if progress_callback and file_size > 0:
                        downloaded_size += len(chunk)
                        progress_callback(min(1.0, downloaded_size / file_size)) 
        if progress_callback and file_size > 0 and downloaded_size == file_size : 
             progress_callback(1.0)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download {url}: {e}")
    except IOError as e:
        logger.error(f"Failed to write to {file_path}: {e}")
    except Exception as e: 
        logger.error(f"An unexpected error occurred during download of {url}: {e}")


def checkWhisperWeight(root: str, weight_type: str) -> bool:
    """
    Checks if a specified Whisper model weight type seems to be correctly downloaded
    by attempting to load it with local_files_only=True.

    Args:
        root: The root directory where weights are stored.
        weight_type: The user-friendly name of the weight type (e.g., "tiny", "base").

    Returns:
        True if the model loads successfully from local files, False otherwise.
    """
    model_path = os_path.join(root, "weights", "whisper", weight_type)
    if not os_path.isdir(model_path): 
        return False
        
    if not os_path.exists(os_path.join(model_path, "model.bin")):
        return False

    try:
        WhisperModel(
            model_path,
            device="cpu",      
            device_index=0,
            compute_type="int8", 
            cpu_threads=1,     
            num_workers=1,
            local_files_only=True, 
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to load local Whisper model {weight_type} for check: {e}")
        return False

def downloadWhisperWeight(root: str, weight_type: str, 
                          progress_callback: Optional[Callable[[float], None]] = None, 
                          end_callback: Optional[Callable[[], None]] = None) -> None:
    """
    Downloads a specified Whisper model weight type from Hugging Face Hub if not already present.

    Args:
        root: The root directory to store weights.
        weight_type: The name of the weight type to download.
        progress_callback: Optional callback for download progress of the main model file.
        end_callback: Optional callback executed after all download attempts.
    """
    if weight_type not in _MODELS:
        logger.error(f"Unknown Whisper weight type: {weight_type}")
        if callable(end_callback):
            end_callback()
        return

    model_storage_path = os_path.join(root, "weights", "whisper", weight_type)
    os_makedirs(model_storage_path, exist_ok=True)

    if not checkWhisperWeight(root, weight_type): 
        logger.info(f"Downloading Whisper model: {weight_type}...")
        model_id = _MODELS[weight_type]
        for filename in _FILENAMES:
            file_destination_path = os_path.join(model_storage_path, filename)
            if not os_path.exists(file_destination_path) or os_path.getsize(file_destination_path) == 0:
                try:
                    url = huggingface_hub.hf_hub_url(model_id, filename)
                    logger.debug(f"Downloading {filename} from {url} to {file_destination_path}")
                    current_file_progress_callback = progress_callback if filename == "model.bin" else None
                    downloadFile(url, file_destination_path, current_file_progress_callback)
                except Exception as e: 
                    logger.error(f"Failed to download {filename} for {weight_type}: {e}")
    else:
        logger.info(f"Whisper model {weight_type} already exists locally.")

    if callable(end_callback):
        end_callback()


def getWhisperModel(root: str, weight_type: str, device: str = "cpu", device_index: int = 0) -> WhisperModel:
    """
    Loads and returns a faster_whisper WhisperModel.

    Args:
        root: Root directory where weights are stored.
        weight_type: Name of the weight type.
        device: "cpu" or "cuda".
        device_index: Index of the GPU if using CUDA.

    Returns:
        A faster_whisper.WhisperModel instance.
    """
    model_path = os_path.join(root, "weights", "whisper", weight_type)
    compute_type = getBestComputeType(device, device_index) 
    
    if not checkWhisperWeight(root, weight_type):
        logger.warning(f"Whisper model {weight_type} not found locally at {model_path}. Attempting download...")
        downloadWhisperWeight(root, weight_type) 
        if not checkWhisperWeight(root, weight_type): 
            raise RuntimeError(f"Failed to download or verify Whisper model {weight_type} after download attempt.")

    logger.info(f"Loading Whisper model: {weight_type} with compute_type: {compute_type} on {device}:{device_index}")
    return WhisperModel(
        model_path,
        device=device,
        device_index=device_index,
        compute_type=compute_type,
        cpu_threads=4, 
        num_workers=1, 
        local_files_only=True, 
    )

if __name__ == "__main__":
    test_root_dir: str = "./test_whisper_weights" 

    def progress_cb(value: float) -> None:
        """Sample progress callback."""
        print(f"Download progress: {value*100:.2f}%")

    def end_cb() -> None:
        """Sample end callback."""
        print("Download process finished.")

    test_weight_type: str = "tiny" 
    print(f"\nTesting with Whisper model: {test_weight_type}")
    downloadWhisperWeight(test_root_dir, test_weight_type, progress_cb, end_cb)
    
    print(f"\nChecking weight for {test_weight_type}: {checkWhisperWeight(test_root_dir, test_weight_type)}")
    
    if checkWhisperWeight(test_root_dir, test_weight_type):
        print(f"\nLoading model: {test_weight_type}")
        try:
            model_instance: WhisperModel = getWhisperModel(test_root_dir, test_weight_type)
            print(f"Successfully loaded model: {model_instance}")
        except Exception as e:
            print(f"Error loading model {test_weight_type}: {e}")
    
    print("\nWhisper module test finished.")