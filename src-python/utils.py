import base64
from typing import Any
import json
import traceback
import logging
from logging.handlers import RotatingFileHandler

from ctranslate2 import get_supported_compute_types
import requests
import ipaddress
import socket

def validateDictStructure(data: dict, structure: dict) -> bool:
    """
    辞書とその期待される構造（型）が完全に一致するかを判別する関数
    Args:
        data (dict): 検証対象の辞書
        structure (dict): 期待される構造を定義した辞書値には型（str, int, bool等）や入れ子の辞書を指定

    Returns:
        bool: 構造が完全に一致する場合True、そうでなければFalse
    """

    if not isinstance(data, dict) or not isinstance(structure, dict):
        return False

    # キーの数と名前が完全に一致するかチェック
    if set(data.keys()) != set(structure.keys()):
        return False

    # 各キーの値の型または構造をチェック
    for key, expected_type_or_structure in structure.items():
        if key not in data:
            return False

        value = data[key]
        # 期待される型が辞書の場合（入れ子構造）
        if isinstance(expected_type_or_structure, dict):
            # 再帰的に検証（多重入れ子に対応）
            if not validateDictStructure(value, expected_type_or_structure):
                return False
        # 期待される型が型オブジェクトの場合
        else:
            if not isinstance(value, expected_type_or_structure):
                return False
    return True

def isConnectedNetwork(url="http://www.google.com", timeout=3) -> bool:
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False

def isAvailableWebSocketServer(host:str, port:int) -> bool:
    """WebSocketサーバーのポートが使用中かどうかを確認する"""
    response = True
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as chk:
            try:
                # SO_REUSEADDRを設定してソケットの再利用を許可
                chk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                chk.bind((host, port))
                # シャットダウン前にリッスン状態にする必要はない
                chk.close()
            except Exception:
                response = False
    except Exception:
        errorLogging()
        response = False

    return response

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
    process_logger.info(response)  # Log the unserialized response

    try:
        serialized_response = json.dumps(response)
    except OSError as e:
        errorLogging()  # Log the full traceback of the OSError
        process_logger.error(f"Problematic response object before json.dumps: {response}")
        process_logger.error(f"OSError during json.dumps: {e}")
        # Optionally, print a generic error JSON to stdout if needed, or re-raise
        # For now, we'll print a simple error message to stdout as a fallback
        error_json = json.dumps({
            "status": 500,
            "endpoint": endpoint,
            "result": {"error": "Failed to serialize response due to OSError", "details": str(e)}
        })
        print(error_json, flush=True)
    else:
        print(serialized_response, flush=True)

error_logger = None
def errorLogging() -> None:
    global error_logger
    if error_logger is None:
        error_logger = setupLogger("error", "error.log", logging.ERROR)

    error_logger.error(traceback.format_exc())