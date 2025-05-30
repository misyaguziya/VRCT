"""Collection of utility functions for network operations, compute type determination, data decoding, and application logging."""
import base64
import ipaddress
import json
import logging
from logging.handlers import RotatingFileHandler
import socket
import traceback
from typing import Any, Optional, Set # Added Set, Optional

import ctranslate2 # type: ignore # Assuming stubs might not be available
import requests

def isConnectedNetwork(url: str = "http://www.google.com", timeout: int = 3) -> bool:
    """
    Checks for an active internet connection by trying to connect to a specified URL.

    Args:
        url: The URL to attempt to connect to. Defaults to Google.
        timeout: Connection timeout in seconds.

    Returns:
        True if the connection is successful (HTTP 200), False otherwise.
    """
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False

def isAvailableWebSocketServer(host: str, port: int) -> bool:
    """
    Checks if a WebSocket server port is available (not in use) on the given host.

    Args:
        host: The hostname or IP address.
        port: The port number.

    Returns:
        True if the port is available, False if it's in use or an error occurs.
    """
    is_available = True
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as chk:
            # SO_REUSEADDR allows faster restart of the server if it was recently closed
            chk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Try to bind to the port. If it succeeds, the port is available.
            chk.bind((host, port))
            # No need to listen, just close immediately after successful bind.
            chk.close()
    except socket.error: # Specifically catch socket errors for "port in use"
        is_available = False
    except Exception: # Catch any other unexpected errors
        errorLogging() # Log the full traceback for unexpected issues
        is_available = False
    return is_available

def isValidIpAddress(ip_address: str) -> bool:
    """
    Validates if the given string is a correct IPv4 or IPv6 address.

    Args:
        ip_address: The IP address string to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

def getBestComputeType(device: str, device_index: int = 0) -> str: # Added device_index default
    """
    Determines the best available CTranslate2 compute type for a given device.
    Prioritizes types for performance and precision.

    Args:
        device: "cpu" or "cuda".
        device_index: The index of the CUDA device if applicable.

    Returns:
        The preferred compute type string (e.g., "int8_float16", "float32").
    """
    supported_types: Set[str] = ctranslate2.get_supported_compute_types(device, device_index=device_index) # type: ignore
    
    # Preferred types, from most performant/quantized to most precise/fallback
    preferred_types_order: list[str] = [
        "int8_bfloat16", "int8_float16", "int8", 
        "bfloat16", "float16", 
        "int8_float32", "float32" 
    ]

    for preferred_type in preferred_types_order:
        if preferred_type in supported_types:
            return preferred_type
    return "default" # Fallback if no preferred types are found (should not happen with CTranslate2)


def decodeBase64Json(data: str) -> Any:
    """
    Decodes a base64 encoded string, then parses it as JSON.

    Args:
        data: The base64 encoded string.

    Returns:
        The parsed JSON data (can be dict, list, str, int, etc.), or None if decoding/parsing fails.
    """
    try:
        decoded_bytes = base64.b64decode(data)
        decoded_string = decoded_bytes.decode('utf-8')
        return json.loads(decoded_string)
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        errorLogging() # Log the error
        return None # Return None or raise a custom exception

def removeLog() -> None:
    """Clears the content of the 'process.log' file by overwriting it as empty."""
    try:
        with open('process.log', 'w', encoding="utf-8") as f:
            f.write("")
    except IOError:
        errorLogging() # Log if there's an issue clearing the log

def setupLogger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger instance with a rotating file handler.

    Args:
        name: The name of the logger.
        log_file: The path to the log file.
        level: The logging level (e.g., logging.INFO, logging.ERROR).

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False # Prevent messages from being passed to the root logger

    # Max log size: 10MB, keep 1 backup file.
    max_log_size_bytes = 10 * 1024 * 1024 

    # Create a rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_log_size_bytes,
        backupCount=1,
        encoding="utf-8",
        delay=True # Defer file opening until the first log message is emitted
    )
    file_handler.setLevel(level)

    # Create a formatter and set it for the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the handler to the logger (only if no handlers of this type exist)
    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == file_handler.baseFilename for h in logger.handlers):
        logger.addHandler(file_handler)

    return logger

# Global logger instances, initialized to None
process_logger: Optional[logging.Logger] = None
error_logger: Optional[logging.Logger] = None

def printLog(log_message: str, data: Any = None) -> None:
    """
    Logs a message and optional data to 'process.log' and prints a JSON
    representation of the log entry to stdout.
    """
    global process_logger
    if process_logger is None:
        process_logger = setupLogger("process", "process.log", logging.INFO)

    log_entry = {
        "status": 348, # Custom status code for log entries via printLog
        "log": log_message,
        "data": str(data), # Ensure data is stringified for logging & JSON
    }
    if process_logger: # Check if logger was successfully initialized
        process_logger.info(json.dumps(log_entry)) # Log the JSON string directly
    
    try:
        json_output = json.dumps(log_entry)
        print(json_output, flush=True)
    except TypeError as e:
        # Fallback if data cannot be JSON serialized after str()
        fallback_log_entry = {
             "status": 348, "log": log_message, "data": "Error serializing data for printLog."
        }
        print(json.dumps(fallback_log_entry), flush=True)
        if process_logger:
            process_logger.error(f"Serialization error in printLog for data '{str(data)}': {e}")


def printResponse(status: int, endpoint: str, result: Any = None) -> None:
    """
    Logs a structured response to 'process.log' and prints a JSON
    representation of the response to stdout.
    """
    global process_logger
    if process_logger is None:
        process_logger = setupLogger("process", "process.log", logging.INFO)

    response = {
        "status": status,
        "endpoint": endpoint,
        "result": result, # Result can be Any type that is JSON serializable
    }
    if process_logger:
        process_logger.info(json.dumps(response)) # Log the JSON string

    try:
        json_output = json.dumps(response)
        print(json_output, flush=True)
    except TypeError as e:
        # Fallback for non-serializable results
        fallback_response = {
            "status": status, "endpoint": endpoint, "result": f"Error serializing result: {str(e)}"
        }
        print(json.dumps(fallback_response), flush=True)
        if process_logger:
            process_logger.error(f"Serialization error in printResponse for result '{str(result)}': {e}")


def errorLogging() -> None:
    """Logs the current exception traceback to 'error.log'."""
    global error_logger
    if error_logger is None:
        error_logger = setupLogger("error", "error.log", logging.ERROR)
    
    if error_logger: # Check if logger was successfully initialized
        # Get traceback string and log it
        tb_str = traceback.format_exc()
        error_logger.error(tb_str)
    else: # Fallback if logger setup failed
        print("ERROR LOGGER NOT INITIALIZED. Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)