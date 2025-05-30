"""Utility functions for managing CTranslate2 model weights and tokenizers."""
import hashlib
from os import makedirs as os_makedirs
from os import path as os_path
import tempfile
from typing import Any, Callable, Dict, Optional, Union # Added Union for Dict value
from zipfile import ZipFile

import requests # Changed from 'get as requests_get' for clarity
import transformers # For AutoTokenizer

from utils import errorLogging

# Defines information about available CTranslate2 model weights, their download URLs,
# directory names, corresponding Hugging Face tokenizer identifiers, and file hashes for verification.
ctranslate2_weights: Dict[str, Dict[str, Union[str, Dict[str, str]]]] = {
    "small": {  # M2M-100 418M-parameter model
        "url": "https://github.com/misyaguziya/VRCT-weights/releases/download/v1.0/m2m100_418m.zip",
        "directory_name": "m2m100_418m",
        "tokenizer": "facebook/m2m100_418M",
        "hash": {
            "model.bin": "e7c26a9abb5260abd0268fbe3040714070dec254a990b4d7fd3f74c5230e3acb",
            "sentencepiece.model": "d8f7c76ed2a5e0822be39f0a4f95a55eb19c78f4593ce609e2edbc2aea4d380a",
            "shared_vocabulary.txt": "bd440aa21b8ca3453fc792a0018a1f3fe68b3464aadddd4d16a4b72f73c86d8c",
        },
    },
    "large": {  # M2M-100 1.2B-parameter model
        "url": "https://github.com/misyaguziya/VRCT-weights/releases/download/v1.0/m2m100_12b.zip",
        "directory_name": "m2m100_12b",
        "tokenizer": "facebook/m2m100_1.2B",
        "hash": {
            "model.bin": "abb7bf4ba7e5e016b6e3ed480c752459b2f783ac8fca372e7587675e5bf3a919",
            "sentencepiece.model": "d8f7c76ed2a5e0822be39f0a4f95a55eb19c78f4593ce609e2edbc2aea4d380a",
            "shared_vocabulary.txt": "bd440aa21b8ca3453fc792a0018a1f3fe68b3464aadddd4d16a4b72f73c86d8c",
        },
    },
}

def calculate_file_hash(file_path: str, block_size: int = 65536) -> str:
    """
    Calculates the SHA256 hash of a file.

    Args:
        file_path: Path to the file.
        block_size: Size of blocks to read for hashing.

    Returns:
        The hexadecimal SHA256 hash string of the file.
    """
    hash_object = hashlib.sha256()
    try:
        with open(file_path, 'rb') as file_handle:
            for block in iter(lambda: file_handle.read(block_size), b''):
                hash_object.update(block)
        return hash_object.hexdigest()
    except IOError:
        errorLogging(f"Error reading file for hashing: {file_path}")
        return "" # Return empty string or raise error

def checkCTranslate2Weight(root: str, weight_type: str = "small") -> bool:
    """
    Checks if CTranslate2 model weights are already downloaded and valid by comparing file hashes.

    Args:
        root: The root directory where weights are stored (e.g., "./weights").
        weight_type: The type of weight to check ("small" or "large").

    Returns:
        True if weights are present and valid, False otherwise.
    """
    weight_info = ctranslate2_weights.get(weight_type)
    if not weight_info:
        errorLogging(f"Unknown weight type for CTranslate2: {weight_type}")
        return False

    weight_directory_name = str(weight_info["directory_name"]) # Ensure str
    hash_data: Dict[str, str] = weight_info["hash"] # type: ignore # hash is Dict[str, str]
    
    # Files expected to be present for a complete model weight set
    expected_files = list(hash_data.keys()) 
    
    base_path = os_path.join(root, "weights", "ctranslate2", weight_directory_name)

    if not all(os_path.exists(os_path.join(base_path, file)) for file in expected_files):
        return False # Not all files are present

    # Check hashes if all files exist
    for file_name, expected_hash in hash_data.items():
        current_file_path = os_path.join(base_path, file_name)
        current_hash = calculate_file_hash(current_file_path)
        if original_hash := hash_data.get(file_name): # Use assignment expression
             if original_hash != current_hash:
                logger.warning(f"Hash mismatch for {file_name}: expected {original_hash}, got {current_hash}")
                return False # Hash mismatch
        else: # Should not happen if hash_data is well-formed
            logger.warning(f"Missing hash for {file_name} in ctranslate2_weights definition.")
            return False
            
    return True # All files exist and hashes match

def downloadCTranslate2Weight(root: str, weight_type: str = "small", 
                              progress_callback: Optional[Callable[[float], None]] = None, 
                              end_callback: Optional[Callable[[], None]] = None) -> None:
    """
    Downloads and extracts CTranslate2 model weights if they are not present or invalid.

    Args:
        root: Root directory for storing weights.
        weight_type: Type of weight to download ("small" or "large").
        progress_callback: Optional callback for download progress (0.0 to 1.0).
        end_callback: Optional callback executed after download attempt.
    """
    weight_info = ctranslate2_weights.get(weight_type)
    if not weight_info:
        errorLogging(f"Unknown weight type for CTranslate2 download: {weight_type}")
        if callable(end_callback): end_callback()
        return

    url = str(weight_info["url"]) # Ensure str
    download_destination_path = os_path.join(root, "weights", "ctranslate2")
    os_makedirs(download_destination_path, exist_ok=True)
    
    zip_filename = "weight.zip" # Temporary name for the downloaded zip

    if not checkCTranslate2Weight(root, weight_type):
        logger.info(f"Downloading CTranslate2 model weights: {weight_type} from {url}")
        try:
            with tempfile.TemporaryDirectory() as tmp_download_dir:
                zip_file_path = os_path.join(tmp_download_dir, zip_filename)
                
                response = requests.get(url, stream=True, timeout=10)
                response.raise_for_status()
                file_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(zip_file_path, 'wb') as file_handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024): # 1MB chunks
                        if chunk:
                            file_handle.write(chunk)
                            if callable(progress_callback) and file_size > 0:
                                downloaded_size += len(chunk)
                                progress_callback(min(1.0, downloaded_size / file_size))
                
                if callable(progress_callback) and file_size > 0 and downloaded_size == file_size:
                    progress_callback(1.0) # Ensure 100% is called

                logger.info(f"Extracting {zip_filename} to {download_destination_path}")
                with ZipFile(zip_file_path, 'r') as zf:
                    zf.extractall(download_destination_path)
                logger.info(f"Extraction complete for {weight_type}.")

        except requests.exceptions.RequestException as e:
            errorLogging(f"Failed to download CTranslate2 weights for {weight_type}: {e}")
        except IOError as e:
            errorLogging(f"File error during CTranslate2 weight download/extraction for {weight_type}: {e}")
        except Exception as e:
            errorLogging(f"Unexpected error downloading CTranslate2 weights for {weight_type}: {e}")
    else:
        logger.info(f"CTranslate2 model {weight_type} already exists and is valid.")

    if callable(end_callback):
        end_callback()

def downloadCTranslate2Tokenizer(root_path: str, weight_type: str = "small") -> None:
    """
    Downloads the Hugging Face AutoTokenizer for the specified CTranslate2 model weight type.

    Args:
        root_path: The root directory where the 'weights' folder is located.
        weight_type: The type of weight ("small" or "large"), used to find the tokenizer name.
    """
    weight_info = ctranslate2_weights.get(weight_type)
    if not weight_info:
        errorLogging(f"Unknown weight type for CTranslate2 tokenizer: {weight_type}")
        return

    directory_name = str(weight_info["directory_name"])
    tokenizer_name = str(weight_info["tokenizer"]) # Hugging Face tokenizer identifier
    
    # Define path for storing the tokenizer, typically alongside the model weights
    tokenizer_storage_path = os_path.join(root_path, "weights", "ctranslate2", directory_name, "tokenizer")
    os_makedirs(tokenizer_storage_path, exist_ok=True)

    try:
        logger.info(f"Downloading tokenizer '{tokenizer_name}' for CTranslate2 model '{weight_type}' to {tokenizer_storage_path}")
        # from_pretrained will download if not found in cache_dir, then load from cache_dir.
        # If it's already in cache_dir, it will load from there.
        transformers.AutoTokenizer.from_pretrained(tokenizer_name, cache_dir=tokenizer_storage_path)
        logger.info(f"Tokenizer for {weight_type} successfully downloaded/loaded.")
    except Exception as e:
        errorLogging(f"Failed to download/load CTranslate2 tokenizer '{tokenizer_name}' for {weight_type}: {e}")
        # Fallback path was removed as cache_dir should handle this. If specific local paths are needed,
        # the logic would need to be more complex, involving checking local paths first.