import base64
from typing import Any
import json
import random
from typing import Union
from os import path as os_path, rename as os_rename
import traceback
import logging
from PIL.Image import open as Image_open

def getImageFile(file_name):
    img = Image_open(os_path.join(os_path.dirname(__file__), "img", file_name))
    return img

def callFunctionIfCallable(function, *args):
    if callable(function) is True:
        function(*args)

def isEven(number):
    return number % 2 == 0

def makeEven(number, minus:bool=False):
    if minus is True:
        return number if isEven(number) else number - 1
    return number if isEven(number) else number + 1

def intToPctStr(value:int):
    return f"{value}%"

def floatToPctStr(value:float):
    return f"{int(value*100)}%"

def strPctToInt(value:str):
    return int(value.replace("%", ""))

def isUniqueStrings(unique_strings:Union[str, list], input_string:str, require=False):
    import re
    if isinstance(unique_strings, str):
        unique_strings = [unique_strings]
    patterns = [re.escape(s) for s in unique_strings]

    counts = [len(re.findall(pattern, input_string)) for pattern in patterns]

    if require is True:
        # If require is True, unique_strings must appear once
        return all(count == 1 for count in counts) and counts.count(1) == 2
    else:
        # If require is False, check if unique strings are used exactly once
        return all(count == 1 for count in counts)

# path先のweightフォルダがある場合にはそのフォルダ名をweightsに変更する
def renameWeightFolder(path):
    weight_path = os_path.join(path, "weight")
    if os_path.exists(weight_path):
        os_rename(weight_path, os_path.join(path, "weights"))

def splitList(lst:list, split_count:int, to_shuffle:bool=False):
    if to_shuffle is True:
        random.shuffle(lst)

    split_lists = []
    for i in range(0, len(lst), split_count):
        sub_list = lst[i:i+split_count]
        split_lists.append(sub_list)
    return split_lists

def encodeBase64(data:str) -> dict:
    return json.loads(base64.b64decode(data).decode('utf-8'))

def removeLog():
    with open('process.log', 'w', encoding="utf-8") as f:
        f.write("")

def setupLogger(name, log_file, level=logging.INFO):
    """
    特定の名前とログファイルを持つロガーを設定します。
    """
    # ロガーを作成
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # 親ロガーへの伝播を防ぐ

    # ハンドラーを作成
    file_handler = logging.FileHandler(log_file, encoding="utf-8", delay=True)
    file_handler.setLevel(level)

    # フォーマッターを設定
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # ロガーにハンドラーを追加
    logger.addHandler(file_handler)

    return logger

process_logger = None
def printLog(log:str, data:Any=None) -> None:
    global process_logger
    if process_logger is None:
        process_logger = setupLogger("process", "process.log", logging.INFO)

    response = {
        "status": 348,
        "log": log,
        "data": str(data),
    }
    process_logger.info(response)
    response = json.dumps(response)
    print(response, flush=True)

def printResponse(status:int, endpoint:str, result:Any=None) -> None:
    global process_logger
    if process_logger is None:
        process_logger = setupLogger("process", "process.log", logging.INFO)

    response = {
        "status": status,
        "endpoint": endpoint,
        "result": result,
    }
    process_logger.info(response)
    response = json.dumps(response)
    print(response, flush=True)

error_logger = None
def errorLogging() -> None:
    global error_logger
    if error_logger is None:
        error_logger = setupLogger("error", "error.log", logging.ERROR)

    error_logger.error(traceback.format_exc())