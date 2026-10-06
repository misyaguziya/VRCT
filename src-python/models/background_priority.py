"""重い計算 (OCR・音声認識など) のスレッドを、VR UI や VRChat より低い優先度にする (Windows のみ)。

onnxruntime などは Python から見えないネイティブのスレッドを作り、通常の優先度のまま CPU を取り合う。
実機で、OCR を動かすと VR UI のオーバーレイの処理が数倍に遅れた。優先度が同じだと、OCR のスレッドが
CPU を使っている間、VR UI のスレッドは待たされる。低い優先度なら、他が空いたときだけ動く。
"""
import ctypes
import os
import threading

try:
    from utils import errorLogging
except Exception:  # pragma: no cover
    def errorLogging():
        import traceback
        print(traceback.format_exc())

THREAD_PRIORITY_BELOW_NORMAL = -1
_THREAD_SET_INFORMATION = 0x0020


def _nativeThreadIds() -> set:
    import psutil

    return {t.id for t in psutil.Process().threads()}


def _setPriority(native_id: int, priority: int) -> bool:
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenThread.restype = ctypes.c_void_p
    kernel32.OpenThread.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel32.OpenThread(_THREAD_SET_INFORMATION, 0, native_id)
    if not handle:
        return False
    try:
        return bool(kernel32.SetThreadPriority(handle, priority))
    finally:
        kernel32.CloseHandle(handle)


def lowerCurrentThread() -> None:
    """今のスレッドを低い優先度にする。"""
    if os.name != "nt":
        return
    try:
        _setPriority(threading.get_native_id(), THREAD_PRIORITY_BELOW_NORMAL)
    except Exception:
        errorLogging()


class BackgroundThreads:
    """作った時点より後に増えたネイティブのスレッドを、lower() で低い優先度にする。

    Python の Thread (オーバーレイ・音声入力など) は対象にしない。作る範囲の間に別の機能が
    ネイティブのスレッドを作ると一緒に下げてしまうので、モデルを読んだ直後など短い間にだけ使う。
    """

    def __init__(self) -> None:
        self._before = self._ids()
        self._done: set = set()

    @staticmethod
    def _ids() -> set:
        if os.name != "nt":
            return set()
        try:
            return _nativeThreadIds()
        except Exception:
            errorLogging()
            return set()

    def lower(self) -> int:
        if os.name != "nt":
            return 0
        python_threads = {t.native_id for t in threading.enumerate() if t.native_id is not None}
        lowered = 0
        for native_id in self._ids() - self._before - self._done - python_threads:
            self._done.add(native_id)
            try:
                lowered += bool(_setPriority(native_id, THREAD_PRIORITY_BELOW_NORMAL))
            except Exception:
                errorLogging()
        return lowered
