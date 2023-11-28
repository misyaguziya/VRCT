import tempfile
from zipfile import ZipFile
from os import path as os_path
from os import makedirs as os_makedirs
from requests import get as requests_get, head as requests_head
from tqdm import tqdm
from typing import Callable

ctranslate2_weights = {
    "small": { # M2M-100 418M-parameter model
        "url": "https://bit.ly/33fM1AO",
        "directory_name": "m2m100_418m",
        "tokenizer": "facebook/m2m100_418M"
    },
    "large": { # M2M-100 1.2B-parameter model
        "url": "https://bit.ly/3GYiaed",
        "directory_name": "m2m100_12b",
        "tokenizer": "facebook/m2m100_12b"
    },
}

def downloadCTranslate2Weight(path, weight_type="small", ctranslate2_weights=ctranslate2_weights, func=None):
    url = ctranslate2_weights[weight_type]["url"]
    filename = 'weight.zip'
    directory_name = 'weight'
    current_directory = path
    weight_directory_name = ctranslate2_weights[weight_type]["directory_name"]
    files = ["model.bin", "sentencepiece.model", "shared_vocabulary.txt"]

    # check already downloaded
    if all(os_path.exists(os_path.join(current_directory, directory_name, weight_directory_name, file)) for file in files):
        return

    try:
        os_makedirs(os_path.join(current_directory, directory_name), exist_ok=True)
        print(os_path.join(current_directory, directory_name))
        with tempfile.TemporaryDirectory() as tmp_path:
            res = requests_get(url, stream=True)
            file_size = int(res.headers.get('content-length', 0))
            pbar = tqdm(total=file_size, unit="B", unit_scale=True)
            total_chunk = 0
            with open(os_path.join(tmp_path, filename), 'wb') as file:
                for chunk in res.iter_content(chunk_size=1024):
                    file.write(chunk)
                    pbar.update(len(chunk))
                    if isinstance(func, Callable):
                        total_chunk += len(chunk)
                        func(total_chunk/file_size)
                pbar.close()

            with ZipFile(os_path.join(tmp_path, filename)) as zf:
                zf.extractall(os_path.join(current_directory, directory_name))
    except Exception as e:
            print("error:downloadCTranslate2Weight()", e)