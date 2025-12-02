import base64
from typing import Any, List, Dict, Optional
import json
import traceback
import logging
from logging.handlers import RotatingFileHandler

try:
    import torch
except Exception:
    torch = None  # type: ignore

try:
    from ctranslate2 import get_supported_compute_types
except Exception:
    # Fallback: if ctranslate2 is not installed, provide a safe stub.
    def get_supported_compute_types(device: str, device_index: int) -> List[str]:
        return []

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
    """Quick network connectivity check by requesting `url`.

    Returns True when a 200 response is returned within `timeout` seconds.
    """
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False

def isAvailableWebSocketServer(host: str, port: int) -> bool:
    """Return True if the given host/port appear available for binding.

    Note: This attempts to bind a TCP socket to the address. If bind
    succeeds the function returns True (meaning the address was available).
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as chk:
            chk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            chk.bind((host, port))
        return True
    except Exception:
        return False

def isValidIpAddress(ip_address: str) -> bool:
    """Return True if `ip_address` is a valid IPv4/IPv6 address."""
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

def isZLUDADevice(device_dict: Dict[str, Any]) -> bool:
    """Check if a device dictionary represents a ZLUDA device.
    
    Args:
        device_dict: Device dictionary with device info
        
    Returns:
        True if the device is a ZLUDA device, False otherwise
    """
    return isinstance(device_dict, dict) and device_dict.get("zluda", False) is True


def detectZLUDARuntimeError(exception: Exception) -> bool:
    """Detect if an exception is a ZLUDA runtime error.
    
    ZLUDA runtime errors can occur when:
    - AMD GPU drivers are incompatible
    - ZLUDA libraries are corrupted or missing
    - CUDA operations fail on AMD GPU
    - Memory allocation fails on AMD GPU
    
    Args:
        exception: The exception to check
        
    Returns:
        True if the exception appears to be a ZLUDA runtime error
    """
    error_str = str(exception).lower()
    error_type = type(exception).__name__.lower()
    
    # Common ZLUDA/CUDA error patterns
    zluda_error_patterns = [
        "cuda",
        "zluda",
        "amd",
        "hip",  # AMD's HIP runtime
        "rocm",  # AMD's ROCm platform
        "device",
        "gpu",
        "out of memory",
        "cudnn",
        "cublas",
        "driver",
        "runtime error",
    ]
    
    # Check if error message contains ZLUDA-related keywords
    for pattern in zluda_error_patterns:
        if pattern in error_str or pattern in error_type:
            return True
    
    return False


def getZLUDADeviceList() -> List[Dict[str, Any]]:
    """Return list of AMD GPUs available through ZLUDA.
    
    Uses torch.cuda API (which ZLUDA intercepts) to enumerate AMD GPU devices.
    ZLUDA must be initialized before calling this function.
    
    Returns:
        List of device dictionaries, each containing:
        - device: "cuda" (ZLUDA intercepts CUDA calls)
        - device_index: GPU index
        - device_name: AMD GPU model name with "(ZLUDA)" suffix
        - compute_types: Supported compute types for AMD GPU
        - zluda: True (flag to indicate ZLUDA device)
        
    Examples:
        >>> from zluda_installer import detectZLUDA, initializeZLUDA
        >>> zluda_path = detectZLUDA()
        >>> if zluda_path:
        ...     initializeZLUDA(zluda_path)
        ...     devices = getZLUDADeviceList()
        ...     for device in devices:
        ...         print(f"{device['device_name']} - {device['compute_types']}")
    """
    zluda_devices: List[Dict[str, Any]] = []
    
    try:
        # Check if torch and CUDA API are available
        if torch is None or not hasattr(torch, "cuda"):
            return zluda_devices
        
        # Check if CUDA (via ZLUDA) is available
        if not torch.cuda.is_available():
            return zluda_devices
        
        # Enumerate devices through torch.cuda API (intercepted by ZLUDA)
        for device_index in range(torch.cuda.device_count()):
            try:
                # Get device name from torch.cuda
                gpu_device_name = torch.cuda.get_device_name(device_index)
                
                # Add "(ZLUDA)" suffix to indicate ZLUDA device
                zluda_device_name = f"{gpu_device_name} (ZLUDA)"
                
                # Get supported compute types for this device
                gpu_compute_types = ["auto"] + sorted(list(get_supported_compute_types("cuda", device_index)))
                
                # AMD GPUs through ZLUDA typically support float32 and int8
                # More conservative compute type selection for AMD GPUs
                # Filter out types that may not be well-supported on AMD
                if gpu_compute_types and len(gpu_compute_types) > 1:
                    # Keep auto, float32, and int8-related types
                    safe_types = {"auto", "float32", "int8", "int8_float32"}
                    gpu_compute_types = [t for t in gpu_compute_types if t in safe_types or t == "auto"]
                
                # If filtering removed everything except auto, add float32 as fallback
                if gpu_compute_types == ["auto"]:
                    gpu_compute_types = ["auto", "float32"]
                
                zluda_devices.append({
                    "device": "cuda",  # ZLUDA intercepts CUDA calls
                    "device_index": device_index,
                    "device_name": zluda_device_name,
                    "compute_types": gpu_compute_types,
                    "zluda": True,  # Flag to indicate this is a ZLUDA device
                })
                
            except Exception:
                # If we fail to get info for a specific device, log and continue
                errorLogging()
                continue
                
    except Exception:
        # If enumeration fails entirely, log and return empty list
        errorLogging()
    
    return zluda_devices


def getZLUDAInstallationInfo() -> Dict[str, Any]:
    """Get ZLUDA installation information for UI display.
    
    Returns:
        Dictionary containing:
        - installed: bool - Whether ZLUDA is installed
        - path: str - Installation path if installed, empty string otherwise
        - version: str - ZLUDA version if detectable, "unknown" otherwise
        - help_url: str - URL to ZLUDA GitHub releases page
        - devices_available: int - Number of AMD GPUs detected
    """
    from pathlib import Path
    import os
    
    info = {
        "installed": False,
        "path": "",
        "version": "unknown",
        "help_url": "https://github.com/vosen/ZLUDA/releases/tag/v5",
        "devices_available": 0
    }
    
    try:
        # Try to detect ZLUDA installation
        from zluda_installer import detectZLUDA, ZLUDAInstaller
        
        zluda_path = detectZLUDA()
        if zluda_path:
            info["installed"] = True
            info["path"] = zluda_path
            
            # Try to detect version from path or files
            path_obj = Path(zluda_path)
            if "v5" in str(path_obj) or (path_obj.parent.name == "zluda" and path_obj.exists()):
                info["version"] = "v5"
            
            # Check for AMD GPU
            installer = ZLUDAInstaller(zluda_path)
            if installer.detectAMDGPU():
                # Try to count devices if ZLUDA is initialized
                try:
                    from zluda_installer import initializeZLUDA
                    initializeZLUDA(zluda_path)
                    devices = getZLUDADeviceList()
                    info["devices_available"] = len(devices)
                except Exception:
                    # If we can't enumerate, just mark as available
                    info["devices_available"] = 1
        else:
            # Check if zluda_path.txt exists (created by installer)
            try:
                app_root = Path(__file__).parent.parent
                zluda_path_file = app_root / "zluda_path.txt"
                if zluda_path_file.exists():
                    with open(zluda_path_file, 'r') as f:
                        zluda_path = f.read().strip()
                        if zluda_path and Path(zluda_path).exists():
                            info["installed"] = True
                            info["path"] = zluda_path
                            info["version"] = "v5"
            except Exception:
                pass
                
    except Exception:
        errorLogging()
    
    return info


def getComputeDeviceList() -> List[Dict[str, Any]]:
    """Return a list of available compute devices and supported compute types.

    The returned list contains dicts describing CPU and (if available)
    CUDA and ZLUDA devices. This function is defensive to missing optional packages.
    
    Device order:
    1. CPU
    2. NVIDIA CUDA GPUs (if available and ZLUDA not initialized)
    3. AMD ZLUDA GPUs (if ZLUDA installed and initialized)
    
    Returns:
        List of device dictionaries, each containing:
        - device: Device type ("cpu" or "cuda")
        - device_index: Device index
        - device_name: Human-readable device name
        - compute_types: List of supported compute types
        - zluda: True for ZLUDA devices (optional field)
    """
    compute_types: List[Dict[str, Any]] = [
        {
            "device": "cpu",
            "device_index": 0,
            "device_name": "cpu",
            "compute_types": ["auto"] + sorted(list(get_supported_compute_types("cpu", 0))),
        }
    ]

    try:
        # Import ZLUDA detection functions
        try:
            from zluda_installer import detectZLUDA, initializeZLUDA
        except ImportError:
            detectZLUDA = None
            initializeZLUDA = None
        
        # Check for ZLUDA first
        zluda_detected = False
        if detectZLUDA is not None and initializeZLUDA is not None:
            zluda_path = detectZLUDA()
            if zluda_path:
                # Initialize ZLUDA environment
                if initializeZLUDA(zluda_path):
                    zluda_detected = True
                    # Get ZLUDA devices
                    zluda_devices = getZLUDADeviceList()
                    compute_types.extend(zluda_devices)
        
        # If ZLUDA not detected, check for native CUDA
        if not zluda_detected:
            if torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available():
                for device_index in range(torch.cuda.device_count()):
                    gpu_device_name = torch.cuda.get_device_name(device_index)
                    gpu_compute_types = ["auto"] + sorted(list(get_supported_compute_types("cuda", device_index)))

                    # デバイスごとの計算タイプの制限
                    if "GTX" in gpu_device_name:
                        unsupported_types = {"int8_bfloat16", "bfloat16", "float16", "int8"}
                        gpu_compute_types = [t for t in gpu_compute_types if t not in unsupported_types]
                    elif not any(keyword in gpu_device_name for keyword in ["RTX", "Tesla", "A100", "Quadro"]):
                        gpu_compute_types = ["float32"]

                    compute_types.append(
                        {
                            "device": "cuda",
                            "device_index": device_index,
                            "device_name": gpu_device_name,
                            "compute_types": gpu_compute_types,
                        }
                    )
    except Exception:
        # If querying GPU devices fails, return at least the CPU entry
        errorLogging()

    return compute_types

def getBestComputeType(device: str, device_index: int) -> str:
    """Pick the best available compute type for a device.

    Falls back to "float32" when no preferred type is available.
    """
    try:
        compute_types = set(get_supported_compute_types(device, device_index))
    except Exception:
        compute_types = set()

    try:
        device_name = "cpu" if device == "cpu" else (torch.cuda.get_device_name(device_index) if torch is not None else "")
    except Exception:
        device_name = ""

    # デバイスごとの優先計算タイプ
    preferred_types = {
        "default": ["int8_bfloat16", "int8_float16", "int8", "bfloat16", "float16", "int8_float32", "float32"],
        "GTX": ["float32"],
        "RTX": ["int8_bfloat16", "int8_float16", "int8", "bfloat16", "float16", "int8_float32", "float32"],
        "Tesla": ["int8_bfloat16", "int8_float16", "int8", "bfloat16", "float16", "int8_float32", "float32"],
        "A100": ["int8_bfloat16", "int8_float16", "int8", "bfloat16", "float16", "int8_float32", "float32"],
        "Quadro": ["int8_bfloat16", "int8_float16", "int8", "bfloat16", "float16", "int8_float32", "float32"],
    }

    # デバイス名に基づいて優先タイプを選択
    selected_types = preferred_types["default"]
    for key in preferred_types:
        if key in device_name:
            selected_types = preferred_types[key]
            break

    # 利用可能な計算タイプを返す
    for compute_type in selected_types:
        if compute_type in compute_types:
            return compute_type

    return "float32"

def encodeBase64(data: str) -> Dict[str, Any]:
    """Decode a base64-encoded JSON string and return the parsed object.

    Returns an empty dict on failure.
    """
    try:
        return json.loads(base64.b64decode(data).decode('utf-8'))
    except Exception:
        errorLogging()
        return {}

def removeLog() -> None:
    """Truncate the process log file (process.log) if present."""
    try:
        with open('process.log', 'w', encoding="utf-8") as f:
            f.write("")
    except Exception:
        errorLogging()

def setupLogger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
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

    # ロガーにハンドラーを追加（重複追加を避ける）
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == getattr(file_handler, 'baseFilename', None) for h in logger.handlers):
        logger.addHandler(file_handler)

    return logger

process_logger: Optional[logging.Logger] = None


def printLog(log: str, data: Any = None) -> None:
    """Log and print a structured process log message."""
    global process_logger
    if process_logger is None:
        process_logger = setupLogger("process", "process.log", logging.INFO)

    response = {
        "status": 348,
        "log": log,
        "data": str(data),
    }
    process_logger.info(response)
    serialized = json.dumps(response)
    print(serialized, flush=True)

def printResponse(status: int, endpoint: str, result: Any = None) -> None:
    """Log and print a structured response object.

    If JSON serialization fails, record the error and emit a generic error payload.
    """
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
    except Exception as e:
        errorLogging()  # Log the full traceback of the exception
        try:
            process_logger.error(f"Problematic response object before json.dumps: {response}")
            process_logger.error(f"Exception during json.dumps: {e}")
        except Exception:
            pass
        # Fallback generic error payload
        error_json = json.dumps({
            "status": 500,
            "endpoint": endpoint,
            "result": {"error": "Failed to serialize response", "details": str(e)},
        })
        print(error_json, flush=True)
    else:
        print(serialized_response, flush=True)

error_logger: Optional[logging.Logger] = None


def errorLogging() -> None:
    """Log the current exception traceback to the error logger."""
    global error_logger
    if error_logger is None:
        error_logger = setupLogger("error", "error.log", logging.ERROR)

    try:
        error_logger.error(traceback.format_exc())
    except Exception:
        # As a last resort, print the traceback to stdout
        print(traceback.format_exc(), flush=True)

if __name__ == "__main__":
    print(getComputeDeviceList())