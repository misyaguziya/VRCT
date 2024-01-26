import tempfile
from zipfile import ZipFile
from os import path as os_path
from os import makedirs as os_makedirs
from requests import get as requests_get
from typing import Callable
import hashlib

ctranslate2_weights = {
    "Small": { # M2M-100 418M-parameter model
        "url": "https://bit.ly/33fM1AO",
        "directory_name": "m2m100_418m",
        "tokenizer": "facebook/m2m100_418M",
        "hash": {
            "model.bin": "e7c26a9abb5260abd0268fbe3040714070dec254a990b4d7fd3f74c5230e3acb",
            "sentencepiece.model": "d8f7c76ed2a5e0822be39f0a4f95a55eb19c78f4593ce609e2edbc2aea4d380a",
            "shared_vocabulary.txt": "bd440aa21b8ca3453fc792a0018a1f3fe68b3464aadddd4d16a4b72f73c86d8c",
        }
    },
    "Large": { # M2M-100 1.2B-parameter model
        "url": "https://bit.ly/3GYiaed",
        "directory_name": "m2m100_12b",
        "tokenizer": "facebook/m2m100_1.2b",
        "hash": {
            "model.bin": "abb7bf4ba7e5e016b6e3ed480c752459b2f783ac8fca372e7587675e5bf3a919",
            "sentencepiece.model": "d8f7c76ed2a5e0822be39f0a4f95a55eb19c78f4593ce609e2edbc2aea4d380a",
            "shared_vocabulary.txt": "bd440aa21b8ca3453fc792a0018a1f3fe68b3464aadddd4d16a4b72f73c86d8c",
        }
    },
}

def calculate_file_hash(file_path, block_size=65536):
    hash_object = hashlib.sha256()

    with open(file_path, 'rb') as file:
        for block in iter(lambda: file.read(block_size), b''):
            hash_object.update(block)

    return hash_object.hexdigest()

def checkCTranslate2Weight(path, weight_type="Small"):
    directory_name = 'weight'
    current_directory = path
    weight_directory_name = ctranslate2_weights[weight_type]["directory_name"]
    hash_data = ctranslate2_weights[weight_type]["hash"]
    files = ["model.bin", "sentencepiece.model", "shared_vocabulary.txt"]

    # check already downloaded
    already_downloaded = False
    if all(os_path.exists(os_path.join(current_directory, directory_name, weight_directory_name, file)) for file in files):
        # check hash
        for file in files:
            original_hash = hash_data[file]
            current_hash = calculate_file_hash(os_path.join(current_directory, directory_name, weight_directory_name, file))
            if original_hash != current_hash:
                break
        already_downloaded = True
    return already_downloaded

def downloadCTranslate2Weight(path, weight_type="Small", func=None):
    url = ctranslate2_weights[weight_type]["url"]
    filename = 'weight.zip'
    directory_name = 'weight'
    current_directory = path

    if checkCTranslate2Weight(path, weight_type):
        return

    try:
        os_makedirs(os_path.join(current_directory, directory_name), exist_ok=True)
        print(os_path.join(current_directory, directory_name))
        with tempfile.TemporaryDirectory() as tmp_path:
            res = requests_get(url, stream=True)
            file_size = int(res.headers.get('content-length', 0))
            total_chunk = 0
            with open(os_path.join(tmp_path, filename), 'wb') as file:
                for chunk in res.iter_content(chunk_size=1024*5):
                    file.write(chunk)
                    if isinstance(func, Callable):
                        total_chunk += len(chunk)
                        func(total_chunk/file_size)

            with ZipFile(os_path.join(tmp_path, filename)) as zf:
                zf.extractall(os_path.join(current_directory, directory_name))
    except Exception as e:
            print("error:downloadCTranslate2Weight()", e)