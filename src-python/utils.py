import base64
from typing import Any
import json
import traceback
import logging
from logging.handlers import RotatingFileHandler

from ctranslate2 import get_supported_compute_types
import requests
import ipaddress

def isConnectedNetwork(url="http://www.google.com", timeout=3) -> bool:
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False

def isValidIpAddress(ip_address: str) -> bool:
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

def getBestComputeType(device, device_index) -> str:
    compute_types = get_supported_compute_types(device, device_index)
    compute_types = set(compute_types)
    preferred_types = ["int8_bfloat16", "int8_float16", "int8", "bfloat16", "float16", "int8_float32", "float32"]

    for preferred_type in preferred_types:
        if preferred_type in compute_types:
            return preferred_type

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

    # filled with 10MB logs
    max_log_size = 10 * 1024 * 1024  # 10MB

    # ハンドラーを作成
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_log_size,
        backupCount=1,
        encoding="utf-8",
        delay=True
        )
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