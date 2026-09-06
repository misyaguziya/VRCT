import base64
from typing import Any, Callable, List, Dict, Optional
import json
import os
import queue
import sys
import traceback
import logging
import threading
from logging.handlers import RotatingFileHandler

import requests
import ipaddress
import socket

# Optional runtime dependencies. `None` fallback lets non-GPU / no-ctranslate2
# environments keep the app running with reduced feature set.
try:
    from ctranslate2 import get_supported_compute_types as _ct2_get_supported_compute_types  # noqa: F401
except Exception:
    def _ct2_get_supported_compute_types(device: str, device_index: int) -> List[str]:  # type: ignore
        return []

try:
    import torch  # noqa: F401
except Exception:
    torch = None  # type: ignore

_WEIGHT_VERIFIED_MARKER_NAME = ".weight_verified.json"

# stdout は Tauri 側が読み取る IPC チャンネルとして使われており、
# printLog/printResponse は複数スレッド (mainloop の worker 群、
# MicSession/SpeakerSession の transcript スレッド、
# AudioLifecycleWorker 等) から高頻度・並行に呼ばれ得る。
# print(..., flush=True) は内部で複数の write システムコールに
# 分解され得るため、ロック無しで並行に呼ぶと (特に Windows の名前付き
# パイプ相手に) 出力が混ざったり、OSError (Errno 22, Invalid argument)
# を招くことがある。1 プロセス内で書き込みを直列化する。
_stdout_write_lock = threading.Lock()


def _writeStdoutLine(line: str) -> bool:
    """flush 付きで 1 行 stdout に書き込む。呼び出し元 (専用の書き込み
    スレッド、下記参照) には例外を伝播させず、ログにだけ記録する。

    戻り値は成功したかどうか (フェーズ3項目18: 呼び出し元が連続失敗を
    数えてフロントエンド消失を検知するために使う)。
    """
    try:
        with _stdout_write_lock:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
        return True
    except Exception:
        errorLogging()
        return False


# --- stdout 専用書き込みスレッド (フェーズ3項目18) ---
#
# 以前は printLog/printResponse を呼んだスレッドが直接 _writeStdoutLine()
# を (ロック付きで) 実行していた。Tauri 側のパイプが壊れると
# sys.stdout.write() が OSError (Errno 22) を送出し (error.log に実例あり、
# 2026-08-27)、パイプが「読まれずに埋まる」場合はブロックする。
# いずれの場合も _stdout_write_lock を握ったまま止まるため、
# printLog/printResponse/run() を呼ぶ全スレッド (energy メーターは
# 毎秒15回程度 run() を叩く) が芋づる式に停止していた
# (freeze_trace.log 2026-08-27、35秒フリーズで実際に確認済み)。
#
# 書き込み自体を専用スレッド1本に閉じ込め、呼び出し元は「キューに積む」
# だけにすることでこの連鎖を断つ。printResponse (実際のエンドポイント
# 応答) は無制限キューに積み絶対に取りこぼさない。printLog (診断ログ)
# は有界キューにし、あふれたら古いものから捨てる (診断用途なので
# 欠落しても機能に影響しない)。
#
# NOTE: 「例外を出さずに書き込みが永久にブロックし続ける」ケース
# (パイプが読まれずに埋まる場合) はこの実装では検知できない
# (連続失敗カウンタは書き込みが実際に失敗して初めて進む)。実際に
# freeze_trace.log で観測された障害は全スレッドのロック待ち連鎖であり、
# それはこの分離だけで解消する。無応答のままブロックし続けるケースへの
# 対応は、書き込みスレッドの進捗を外部から監視する別の仕組みが必要な
# ため、別項目として切り出す方針とした。
_STDOUT_LOG_QUEUE_MAXSIZE = 200
_MAX_CONSECUTIVE_STDOUT_FAILURES = 50
# ログが無い間、応答キューと停止フラグを再確認する間隔。
# queue.Queue.get(timeout=...) は条件変数によるブロッキング待ちであり
# ビジーループではないため、短くしてもCPU負荷はほぼ増えない。短いほど
# 「ログだけが流れていて応答が来ていない」状況での応答の検知遅延と、
# stopStdoutWriter() の反映遅延の両方が縮む。
_LOG_QUEUE_POLL_TIMEOUT_SECONDS = 0.02

_stdout_response_queue: "queue.Queue" = queue.Queue()
_stdout_log_queue: "queue.Queue" = queue.Queue(maxsize=_STDOUT_LOG_QUEUE_MAXSIZE)
_stdout_writer_thread: Optional[threading.Thread] = None
_stdout_writer_start_lock = threading.Lock()
_stdout_writer_stop_event = threading.Event()
_on_frontend_lost: Optional[Callable[[], None]] = None


def setFrontendLostCallback(callback: Optional[Callable[[], None]]) -> None:
    """stdoutへの書き込みが連続して失敗した際に呼ぶコールバックを登録する。

    未登録 (None、既定) の場合は os._exit(1) で自己終了する。テストが
    実プロセスを終了させずに検知だけを確認できるようにするための差し替え口。
    """
    global _on_frontend_lost
    _on_frontend_lost = callback


def _stdoutWriterLoop() -> None:
    consecutive_failures = 0
    while not _stdout_writer_stop_event.is_set():
        # 応答キューを先に (ブロックせず) 確認し、優先して処理する。
        # 無ければログキューを短いタイムアウト付きで待つ。もし逆に
        # 応答キューを毎回 get(timeout=...) で待ってしまうと、ログだけが
        # 溜まっている状況でも1件処理するごとにこのタイムアウト分の
        # 遅延が入り、ログのスループットが不必要に制限されてしまう
        # (energy メーターだけで秒15回程度 printLog が呼ばれるため、
        # 実際にテストでタイムアウトとして検出された)。
        try:
            line = _stdout_response_queue.get_nowait()
        except queue.Empty:
            try:
                line = _stdout_log_queue.get(timeout=_LOG_QUEUE_POLL_TIMEOUT_SECONDS)
            except queue.Empty:
                continue

        if _writeStdoutLine(line):
            consecutive_failures = 0
            continue

        consecutive_failures += 1
        if consecutive_failures >= _MAX_CONSECUTIVE_STDOUT_FAILURES:
            callback = _on_frontend_lost
            if callback is not None:
                try:
                    callback()
                except Exception:
                    errorLogging()
            else:
                os._exit(1)
            return  # コールバック指定時は書き込みスレッドを終了する


def _ensureStdoutWriterStarted() -> None:
    # 2つのスレッドがほぼ同時に初回の printLog/printResponse を呼ぶと、
    # 素朴な "None なら作る" チェックだけでは両方が「まだ無い」と判定し
    # 書き込みスレッドが2本立ち上がりうる (直そうとしている「複数スレッドが
    # 同時に stdout へ書き込む」問題の再発になる)。起動処理自体をロックで
    # 直列化する。
    global _stdout_writer_thread
    with _stdout_writer_start_lock:
        if _stdout_writer_thread is not None and _stdout_writer_thread.is_alive():
            return
        _stdout_writer_stop_event.clear()
        _stdout_writer_thread = threading.Thread(
            target=_stdoutWriterLoop, name="StdoutWriter", daemon=True
        )
        _stdout_writer_thread.start()


def stopStdoutWriter() -> None:
    """通常のシャットダウン時に書き込みスレッドを止める。デーモンスレッド
    なのでプロセス終了自体はこれを呼ばなくてもブロックしないが、
    行儀よく止めておく。"""
    _stdout_writer_stop_event.set()


def _enqueueResponseLine(line: str) -> None:
    _ensureStdoutWriterStarted()
    _stdout_response_queue.put(line)


def putDroppingOldestOnFull(q: "queue.Queue", item: Any) -> bool:
    """非ブロッキングでqに積む。満杯なら最も古い項目を1つ捨てて積み直す。

    ブロッキングpush (put()) は呼び出し元スレッド (録音コールバックや
    ログ出力元などリアルタイム処理を行うプロデューサ) を止めてしまう
    ため、常にput_nowaitのみを使う。あふれた場合は直近の状態の方が
    有用という前提で、古いものから捨てる (フェーズ3項目18で導入、
    項目20でaudio_queueにも展開する際に共通ヘルパーへ切り出した)。

    Returns:
        満杯で古い項目を1つ捨てた場合はTrue。呼び出し元が「捨てが
        発生したこと」をログに残したい場合に使う。
    """
    try:
        q.put_nowait(item)
        return False
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(item)
        except queue.Full:
            pass
        return True


def _enqueueLogLine(line: str) -> None:
    _ensureStdoutWriterStarted()
    putDroppingOldestOnFull(_stdout_log_queue, line)


def _collectWeightFileStats(root: str) -> Dict[str, Dict[str, float]]:
    """Recursively collect {relative_path: {size, mtime}} for files under root.

    mtime is rounded to avoid float round-trip mismatches after JSON (de)serialization.
    """
    stats: Dict[str, Dict[str, float]] = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name == _WEIGHT_VERIFIED_MARKER_NAME:
                continue
            full_path = os.path.join(dirpath, name)
            rel_path = os.path.relpath(full_path, root).replace("\\", "/")
            try:
                st = os.stat(full_path)
                stats[rel_path] = {"size": st.st_size, "mtime": round(st.st_mtime, 3)}
            except OSError:
                continue
    return stats


def isWeightVerifiedCache(root: str) -> bool:
    """Return True if a weight directory's files exactly match a previously
    recorded "verified" snapshot (same file set, sizes, and mtimes).

    This lets callers skip an expensive full model load to re-verify weights
    that haven't changed since the last successful load-based verification.
    Any change (missing marker, added/removed/modified file) invalidates the
    cache and forces a real verification.
    """
    marker_path = os.path.join(root, _WEIGHT_VERIFIED_MARKER_NAME)
    if not os.path.isfile(marker_path):
        return False
    try:
        with open(marker_path, "r", encoding="utf-8") as f:
            recorded = json.load(f).get("verified_files", {})
    except Exception:
        return False
    if not recorded:
        return False
    return _collectWeightFileStats(root) == recorded


def writeWeightVerifiedCache(root: str) -> None:
    """Record the current file stats under root as a verified snapshot."""
    try:
        stats = _collectWeightFileStats(root)
        if not stats:
            return
        marker_path = os.path.join(root, _WEIGHT_VERIFIED_MARKER_NAME)
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump({"verified_files": stats}, f)
    except Exception:
        pass

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

def isWildcardBindAddress(ip_address: str) -> bool:
    """Return True if `ip_address` is the IPv4/IPv6 "unspecified" address
    (0.0.0.0 / ::), which means "listen on every interface".

    Used to reject binding the local WebSocket server to a wildcard
    address: unlike a specific LAN IP (which at least requires the same
    network segment), 0.0.0.0/:: exposes the unauthenticated-by-default
    transcript stream to literally any interface the machine has,
    including ones the user may not realize are reachable (VPN, hotspot,
    etc.).
    """
    try:
        return ipaddress.ip_address(ip_address).is_unspecified
    except ValueError:
        return False

def getComputeDeviceList() -> List[Dict[str, Any]]:
    """Return a list of available compute devices and supported compute types.

    The returned list contains dicts describing CPU and (if available)
    CUDA devices. This function is defensive to missing optional packages.
    """
    get_supported_compute_types = _ct2_get_supported_compute_types

    compute_types: List[Dict[str, Any]] = [
        {
            "device": "cpu",
            "device_index": 0,
            "device_name": "cpu",
            "compute_types": ["auto"] + sorted(list(get_supported_compute_types("cpu", 0))),
        }
    ]

    try:
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
        compute_types = set(_ct2_get_supported_compute_types(device, device_index))
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

class TruncatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that truncates the log file in place instead of
    rotating it to a numbered backup (e.g. process.log.1). Creating that
    backup file was being picked up by Tauri's dev file watcher (src-tauri
    is inside the watched tree) and triggering a rebuild loop.
    """
    def doRollover(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None
        with open(self.baseFilename, "w", encoding=self.encoding):
            pass
        if not self.delay:
            self.stream = self._open()

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
    file_handler = TruncatingFileHandler(
        log_file,
        maxBytes=max_log_size,
        backupCount=0,
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

# エンドポイント名にこれらのいずれかが含まれる場合、ログに書き出す値をマスクする
SENSITIVE_ENDPOINT_MARKERS = ("auth_key", "api_key", "password", "token", "secret")


def _isSensitiveEndpoint(endpoint: Any) -> bool:
    if not isinstance(endpoint, str):
        return False
    # ラベル文字列 ("Set OpenRouter Auth Key") とエンドポイント文字列
    # ("/set/data/openrouter_auth_key") の両方で "auth_key" 等のマーカーに
    # ヒットするよう、空白をアンダースコアに正規化してから判定する。
    lowered = endpoint.lower().replace(" ", "_")
    return any(marker in lowered for marker in SENSITIVE_ENDPOINT_MARKERS)


def _maskSensitiveValue(value: Any) -> Any:
    return "***MASKED***" if value not in (None, "") else value


def _maskSensitiveData(data: Any) -> Any:
    """Recursively mask values under dict keys that look like secrets.

    Used for aggregate payloads (e.g. the /run/initialization_complete
    response, which bundles every /get/data/* result including the
    *_auth_key entries into a single dict) where the top-level endpoint
    name itself isn't "sensitive" but individual keys inside the payload
    are. Each dict key is checked with the same normalization as
    _isSensitiveEndpoint, so both endpoint-style keys
    ("/get/data/openrouter_auth_key") and log-label keys are caught.
    """
    if isinstance(data, dict):
        return {
            key: (_maskSensitiveValue(value) if _isSensitiveEndpoint(str(key)) else _maskSensitiveData(value))
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [_maskSensitiveData(item) for item in data]
    return data


def printLog(log: str, data: Any = None) -> None:
    """Log and print a structured process log message."""
    global process_logger
    if process_logger is None:
        process_logger = setupLogger("process", "process.log", logging.INFO)

    logged_data = _maskSensitiveValue(data) if _isSensitiveEndpoint(log) else data
    response = {
        "status": 348,
        "log": log,
        "data": str(logged_data),
    }
    process_logger.info(response)
    serialized = json.dumps(response)
    _enqueueLogLine(serialized)

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

    # エンドポイント自体が機微な場合 (/get/data/openrouter_auth_key 等) は
    # result 全体を、そうでない場合 (/run/initialization_complete のような
    # 集約レスポンス) は result 内部を再帰的に走査してマスクする。
    # エンドポイント名だけを見る判定は集約レスポンスに対して機能しないため。
    if _isSensitiveEndpoint(endpoint):
        logged_result = _maskSensitiveValue(result)
    else:
        logged_result = _maskSensitiveData(result)
    logged_response = {**response, "result": logged_result}
    process_logger.info(logged_response)  # Log the (possibly masked) response, never the raw secret

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
        _enqueueResponseLine(error_json)
    else:
        _enqueueResponseLine(serialized_response)

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