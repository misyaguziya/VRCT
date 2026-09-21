"""AMD GPU (ROCm) で VRCT の推論が動くかを実機で確かめる。

    python tools/amd_spike/check_amd.py

issue #88 の設計調査 (docs/amd-gpu-support-design-2026-09-19.md §9 Phase 2) で
洗い出した未確認事項を、Radeon を持っている人に確かめてもらうためのスクリプト。
開発側には検証できる実機が無いので、ここが唯一の確認手段になる。

段階 A → B → C の順に進み、前の段階が駄目なら後ろは意味がないので止まる。
A は数秒で終わり何もダウンロードしない。C だけモデルのダウンロードが要る。

**実行時の出力は英語**。依頼する相手 (issue #88 の要望者) が英語話者のため。
コード中のコメントは日本語のまま (読むのはメンテナ側なので)。

結果は amd_spike_report.txt に書き出す。何も送信しない。
"""

from __future__ import annotations

import argparse
import ctypes
import gc
import glob
import json
import os
import platform
import struct
import sys
import threading
import time
import traceback
import wave
from pathlib import Path

REPORT_PATH = Path("amd_spike_report.txt")

_report = None  # 逐次書き出し用のハンドル。_openReport() 参照
_stage_failed = False
# 解放するとハングしうるモデルの置き場。理由は Stage D を参照。
_keep_alive: list = []


def _setup_frozen_rocm_paths() -> None:
    """凍結 exe のとき、同梱した ROCm ランタイムを見つけられるようにする。

    ROCm 版 ctranslate2.dll は hipblas.dll / amdhip64_7.dll を**静的に**
    インポートするので、`import ctranslate2` の瞬間にはもう検索パスに載って
    いる必要がある (2026-09-20 実測。CPU/CUDA 版が cuBLAS を遅延ロードする
    のとは事情が違う)。このスクリプトは ctranslate2 を stage_b の中でしか
    import しないので、ここで先に仕込める。

    rocblas.dll は Tensile カーネルを自分の隣の rocblas/library から探す。
    凍結レイアウトでは相対位置が変わりうるので、環境変数で明示しておく。

    非凍結 (開発中に python で直接叩く場合) は何もしない。その場合は
    HIP SDK が PATH に入っている前提。
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass or os.name != "nt":
        return
    try:
        os.add_dll_directory(meipass)
    except OSError:
        pass
    os.environ["PATH"] = meipass + os.pathsep + os.environ.get("PATH", "")
    tensile = os.path.join(meipass, "rocblas", "library")
    if os.path.isdir(tensile):
        os.environ.setdefault("ROCBLAS_TENSILE_LIBPATH", tensile)


def _setup_console() -> None:
    """日本語混じりでなくても、パスに非ASCIIが入ると cp932 で落ちうるので UTF-8 に寄せる。

    install.bat が `python -X utf8` を付けている前提には乗らない
    (このスクリプトは手で叩かれるので)。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _openReport() -> None:
    """レポートを1行ずつ書き出す。

    以前は最後にまとめて書いていたが、ROCm はモデルの解放から帰ってこない
    ことがあり (Stage D)、書き出しに到達できずに計測結果を丸ごと失った。
    1行ずつ flush しておけば、どこでハングしてもそこまでは残る。
    """
    global _report
    try:
        _report = open(REPORT_PATH, "w", encoding="utf-8")
    except Exception:
        _report = None


def log(text: str = "") -> None:
    print(text, flush=True)
    if _report is not None:
        try:
            # 1行ずつ伏せ字にする。redact は単純な文字列置換なので、
            # 全体に掛けたときと結果は変わらない。
            _report.write(redact(text) + "\n")
            _report.flush()
        except Exception:
            pass


def redact(text: str) -> str:
    """ユーザー名とホームディレクトリを伏せる。共有される前提の出力なので。"""
    home = str(Path.home())
    out = text.replace(home, "<HOME>").replace(home.replace("\\", "/"), "<HOME>")
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if user and len(user) > 2:
        out = out.replace(user, "<USER>")
    return out


def section(title: str) -> None:
    log()
    log("=" * 70)
    log(title)
    log("=" * 70)


def result(tag: str, name: str, detail: str = "") -> None:
    log(f"[{tag:4}] {name}" + (f"  -- {detail}" if detail else ""))


def fail_stage(reason: str) -> None:
    global _stage_failed
    _stage_failed = True
    log()
    log(f"!! STOPPING HERE: {reason}")


# ----------------------------------------------------------------------------
# Stage A -- HIP ランタイムと DLL の状況 (ダウンロード不要、数秒)
# ----------------------------------------------------------------------------

# amdhip64 はバージョンごとに名前が変わる。7 系 / 6 系 / 無印の順に試す。
_HIP_RUNTIME_NAMES = ("amdhip64_7.dll", "amdhip64_6.dll", "amdhip64.dll")
# #2016: wheel が ROCm 7.2 ビルドだと hipblas.dll を、7.1.1 以前だと
# libhipblas.dll を探す。どちらがあるかで回避策の要否が決まる。
_HIPBLAS_NAMES = ("hipblas.dll", "libhipblas.dll")


def _loaded_module_path(handle: ctypes.CDLL) -> str:
    """ロード済み DLL の実体パスを取る。ドライバ由来か SDK 由来かの判別用。"""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetModuleFileNameW(
            ctypes.c_void_p(handle._handle), buf, len(buf))
        return buf.value or "(unknown)"
    except Exception:
        return "(unknown)"


def stage_a() -> dict:
    section("Stage A: environment and HIP runtime (no downloads)")
    info: dict = {}

    log(f"OS            : {platform.platform()}")
    log(f"Python        : {sys.version.split()[0]} ({struct.calcsize('P') * 8}-bit)")
    log(f"Machine       : {platform.machine()}")
    log()

    if os.name != "nt":
        result("FAIL", "not running on Windows", os.name)
        fail_stage("VRCT targets Windows only.")
        return info

    # --- GPU の名前 (WMI 経由。取れなくても致命的ではない) ---
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             ("Get-CimInstance Win32_VideoController | "
              "Select-Object -ExpandProperty Name")],
            capture_output=True, text=True, timeout=30, check=False)
        gpus = [g.strip() for g in out.stdout.splitlines() if g.strip()]
        info["gpus"] = gpus
        for gpu in gpus:
            result("INFO", "GPU", gpu)
        if not gpus:
            result("WARN", "could not read GPU names", "continuing anyway")
    except Exception as exc:
        result("WARN", "could not read GPU names", repr(exc))

    # --- HIP SDK が入っているか ---
    hip_path = os.environ.get("HIP_PATH", "")
    rocm_dirs = sorted(glob.glob(r"C:\Program Files\AMD\ROCm\*"))
    info["hip_sdk_installed"] = bool(hip_path or rocm_dirs)
    if hip_path:
        result("INFO", "HIP_PATH", redact(hip_path))
    if rocm_dirs:
        result("INFO", "ROCm install", ", ".join(Path(d).name for d in rocm_dirs))
    if not info["hip_sdk_installed"]:
        result("INFO", "HIP SDK", "not found -- that is fine, and is useful to know")

    # --- A4: HIP ランタイムを SDK なしで引けるか (同梱サイズに直結) ---
    log()
    log("-- HIP runtime --")
    hip = None
    for name in _HIP_RUNTIME_NAMES:
        try:
            hip = ctypes.CDLL(name)
        except OSError:
            continue
        path = _loaded_module_path(hip)
        info["hip_runtime"] = name
        info["hip_runtime_path"] = redact(path)
        # 「同梱物から来たのか」を区別する。この exe は ROCm ランタイムを
        # 同梱して「SDK を入れずに済む」ことを確かめるためのものなので、
        # どこから来たかが我々の知りたい答えそのものになる。
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and os.path.normcase(meipass) in os.path.normcase(path):
            origin = "bundled with this tool (no HIP SDK needed -- this is what we hoped for)"
        elif "AMD\\ROCm" in path:
            origin = "the HIP SDK installed on this machine"
        else:
            origin = "the driver or somewhere else on PATH"
        result("OK", f"loaded {name}", redact(path))
        result("INFO", "came from", origin)
        info["hip_origin"] = origin
        break
    if hip is None:
        for name in _HIP_RUNTIME_NAMES:
            result("FAIL", f"cannot load {name}")
        fail_stage("No HIP runtime found. Please make sure your AMD driver "
                   "(Adrenalin) is up to date, then run this again.")
        return info

    # --- A5: #2016 の DLL 名問題 ---
    log()
    log("-- hipBLAS (checking CTranslate2 issue #2016) --")
    found_blas = []
    for name in _HIPBLAS_NAMES:
        try:
            handle = ctypes.CDLL(name)
        except OSError:
            result("--", f"{name} not present")
            continue
        found_blas.append(name)
        result("OK", f"loaded {name}", redact(_loaded_module_path(handle)))
    info["hipblas_names"] = found_blas
    if not found_blas:
        result("WARN", "hipblas not found under either name",
               "the CTranslate2 ROCm wheel may ship its own -- Stage B will tell")

    # --- A6 / R3: HIP のシンボルと、アーキ世代の取得 ---
    log()
    log("-- HIP API symbols the design relies on --")
    symbols = ("hipInit", "hipGetDeviceCount", "hipDeviceGet",
               "hipDeviceGetName", "hipDeviceComputeCapability")
    missing = []
    for sym in symbols:
        if hasattr(hip, sym):
            result("OK", sym)
        else:
            result("FAIL", sym, "not exported")
            missing.append(sym)
    info["missing_symbols"] = missing

    if missing:
        fail_stage("A HIP API the design assumes is missing. We will need to "
                   "use hipGetDeviceProperties instead. This is useful to know.")
        return info

    # 実際に叩いてデバイス名と gfx 世代を取る。
    # 設計の「major 11/12 だけ一覧に出す」という判断がこの値に依存している。
    try:
        if hip.hipInit(0) != 0:
            result("FAIL", "hipInit(0)", "returned non-zero")
            fail_stage("HIP could not be initialised.")
            return info
        result("OK", "hipInit(0)")

        count = ctypes.c_int()
        hip.hipGetDeviceCount(ctypes.byref(count))
        result("INFO", "hipGetDeviceCount", str(count.value))
        info["hip_device_count"] = count.value

        devices = []
        name_buf = ctypes.create_string_buffer(256)
        for i in range(count.value):
            dev = ctypes.c_int()
            if hip.hipDeviceGet(ctypes.byref(dev), i) != 0:
                continue
            name = ""
            if hip.hipDeviceGetName(name_buf, len(name_buf), dev) == 0:
                name = name_buf.value.decode("utf-8", "replace")
            major, minor = ctypes.c_int(), ctypes.c_int()
            cap = hip.hipDeviceComputeCapability(
                ctypes.byref(major), ctypes.byref(minor), dev)
            cap_text = f"{major.value}.{minor.value}" if cap == 0 else "(failed)"
            gated = major.value in (11, 12)
            # VRAM 容量。モデル同時ロードの上限を見積もるのに要る
            # (VRCT は STT と翻訳のモデルを同時に載せる)。
            vram = ""
            if hasattr(hip, "hipSetDevice") and hasattr(hip, "hipMemGetInfo"):
                free_b, total_b = ctypes.c_size_t(), ctypes.c_size_t()
                if (hip.hipSetDevice(i) == 0 and hip.hipMemGetInfo(
                        ctypes.byref(free_b), ctypes.byref(total_b)) == 0):
                    vram = (f" / VRAM {total_b.value / 2 ** 30:.1f} GiB"
                            f" ({free_b.value / 2 ** 30:.1f} GiB free)")
            result("INFO", f"device {i}", f"{name} / compute capability {cap_text}{vram}")
            result("INFO", f"device {i} passes the planned architecture gate",
                   "yes" if gated else f"no (major={major.value})")
            devices.append({"index": i, "name": name,
                            "major": major.value, "minor": minor.value})
        info["hip_devices"] = devices
    except Exception:
        result("FAIL", "calling the HIP API raised", "")
        log(redact(traceback.format_exc()))
        fail_stage("Could not call into the HIP API.")
    return info


# ----------------------------------------------------------------------------
# Stage B -- ROCm 版 CTranslate2 (ROCm wheel を入れた venv が要る)
# ----------------------------------------------------------------------------

def _dll_imports(path: Path) -> list[str]:
    """PE のインポートテーブルから、この DLL が必要とする DLL 名を読む。

    ビルド種別の判定に使う。`get_cuda_device_count() > 0` では判定できない:
    ctranslate2 は CPU 版ビルドでも GPU の存在自体は見えてしまうため
    (src-python/test/test_utils_compute_device.py に実測が残っている)。
    実際に amdhip64 にリンクしているかを見るのが確実。

    ついでに「ROCm 版 CT2 がどの DLL を要求するか」(設計の R4) の答えにもなる。
    読めなければ空リストを返す。判定できないだけで致命的ではない。
    """
    try:
        data = path.read_bytes()
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe:pe + 4] != b"PE\0\0":
            return []
        n_sections = struct.unpack_from("<H", data, pe + 6)[0]
        opt_size = struct.unpack_from("<H", data, pe + 20)[0]
        opt = pe + 24
        magic = struct.unpack_from("<H", data, opt)[0]
        # データディレクトリの位置は PE32 と PE32+ で違う。import は index 1。
        dd = opt + (96 if magic == 0x10B else 112)
        import_rva = struct.unpack_from("<I", data, dd + 8)[0]
        if not import_rva:
            return []

        sections = []
        sec = opt + opt_size
        for i in range(n_sections):
            off = sec + i * 40
            virt_size, virt_addr, raw_size, raw_ptr = struct.unpack_from(
                "<IIII", data, off + 8)
            sections.append((virt_addr, max(virt_size, raw_size), raw_ptr))

        def to_offset(rva: int) -> int | None:
            for virt_addr, size, raw_ptr in sections:
                if virt_addr <= rva < virt_addr + size:
                    return raw_ptr + (rva - virt_addr)
            return None

        names: list[str] = []
        table = to_offset(import_rva)
        if table is None:
            return []
        while True:
            # IMAGE_IMPORT_DESCRIPTOR は 20 バイト。Name は +12。
            name_rva = struct.unpack_from("<I", data, table + 12)[0]
            if name_rva == 0:
                break
            name_off = to_offset(name_rva)
            if name_off is None:
                break
            end = data.index(b"\0", name_off)
            names.append(data[name_off:end].decode("ascii", "replace"))
            table += 20
            if len(names) > 200:
                break
        return names
    except Exception:
        return []


def stage_b(stage_a_info: dict | None = None) -> dict:
    section("Stage B: CTranslate2 (is it really the ROCm build?)")
    info: dict = {}
    stage_a_info = stage_a_info or {}
    try:
        import ctranslate2
    except Exception:
        result("FAIL", "import ctranslate2", "not installed")
        log(redact(traceback.format_exc()))
        fail_stage("Install the ROCm CTranslate2 wheel first -- see the README.")
        return info

    version = getattr(ctranslate2, "__version__", "(unknown)")
    result("OK", "import ctranslate2", version)
    info["ct2_version"] = version

    # --- どのビルドか。ここを省くと偽の PASS になる ---
    log()
    log("-- which build is installed --")
    pkg_dir = Path(ctranslate2.__file__).parent
    dll = pkg_dir / "ctranslate2.dll"
    imports = _dll_imports(dll) if dll.exists() else []
    info["ct2_imports"] = imports
    if imports:
        hip_linked = [n for n in imports
                      if any(k in n.lower() for k in ("amdhip", "hipblas", "rocblas", "hiprt"))]
        cuda_linked = [n for n in imports
                       if any(k in n.lower() for k in ("cudart", "cublas", "nvcuda", "cudnn"))]
        log(f"       ctranslate2.dll imports: {', '.join(imports)}")
        info["ct2_hip_linked"] = hip_linked
        info["ct2_cuda_linked"] = cuda_linked
        if hip_linked:
            result("OK", "this looks like the ROCm/HIP build", ", ".join(hip_linked))
        elif cuda_linked:
            result("FAIL", "this looks like the NVIDIA/CUDA build", ", ".join(cuda_linked))
            fail_stage("The installed ctranslate2 links against CUDA, not HIP. "
                       "Please install the ROCm wheel (see the README) into a "
                       "clean venv and run this again.")
            return info
        else:
            result("WARN", "could not tell which build from the import table",
                   "GPU libraries are probably loaded lazily -- Stage C is the real test")
    else:
        result("WARN", "could not read ctranslate2.dll imports",
               "skipping the build check -- Stage C is the real test")

    # --- デバイスが見えるか ---
    log()
    log("-- device enumeration --")
    try:
        count = ctranslate2.get_cuda_device_count()
    except Exception:
        result("FAIL", "get_cuda_device_count()", "raised")
        log(redact(traceback.format_exc()))
        fail_stage("CTranslate2 cannot enumerate GPUs.")
        return info

    info["ct2_device_count"] = count
    if count <= 0:
        result("FAIL", "get_cuda_device_count()", "0")
        fail_stage("CTranslate2 does not see any GPU.")
        return info

    result("OK", "get_cuda_device_count()", str(count))
    log("       NOTE: a non-zero count on its own does NOT prove the ROCm build")
    log("       works -- CTranslate2 reports a count even on CPU-only builds.")
    log("       The build check above and Stage C are what actually decide.")

    # Stage A が見た HIP デバイス数と突き合わせる。食い違っていたら
    # 別ベンダーの GPU を数えている可能性がある (NVIDIA と AMD の同居構成)。
    hip_count = stage_a_info.get("hip_device_count")
    if isinstance(hip_count, int):
        if hip_count == count:
            result("OK", "count matches what HIP reported in Stage A", str(hip_count))
        else:
            result("WARN", "count does NOT match HIP's device count",
                   f"HIP said {hip_count}, CTranslate2 says {count}")
            log("       If this machine also has an NVIDIA GPU, CTranslate2 may be")
            log("       counting that one instead. Please mention your GPU setup.")

    types = {}
    for i in range(count):
        try:
            supported = sorted(ctranslate2.get_supported_compute_types("cuda", i))
            types[i] = supported
            result("OK", f"get_supported_compute_types('cuda', {i})", ", ".join(supported))
        except Exception:
            result("FAIL", f"get_supported_compute_types('cuda', {i})", "raised")
            log(redact(traceback.format_exc()))
    info["ct2_compute_types"] = types
    return info


# ----------------------------------------------------------------------------
# Stage C -- 実際に動かす (モデルのダウンロードが要る)
# ----------------------------------------------------------------------------

def _make_test_wav(path: Path, seconds: float = 5.0, rate: int = 16000) -> None:
    """発話1回ぶんの長さのテスト音声を作る。

    合成音なので認識結果は意味を成さない。ここで測りたいのは認識精度ではなく
    「同じ入力に対する GPU と CPU の所要時間の比」なので、それで足りる。
    実際の音声で測りたい場合は --audio で wav を渡せる。
    """
    import math
    frames = bytearray()
    total = int(rate * seconds)
    for n in range(total):
        t = n / rate
        # 適当に変調をかけた音。完全な無音だと早期に打ち切る実装があるため。
        value = 0.3 * math.sin(2 * math.pi * 220 * t) * (1 + 0.5 * math.sin(2 * math.pi * 3 * t))
        frames += struct.pack("<h", int(value * 32767))
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(bytes(frames))


def _transcribe_once(model, audio_path: Path) -> float:
    start = time.perf_counter()
    segments, _ = model.transcribe(str(audio_path), beam_size=1)
    list(segments)  # generator なので消費するまで実行されない
    return time.perf_counter() - start


def stage_c(model_id: str, audio: Path | None, runs: int) -> dict:
    section("Stage C: actually run faster-whisper")
    info: dict = {}
    try:
        from faster_whisper import WhisperModel
    except Exception:
        result("FAIL", "import faster_whisper", "not installed")
        fail_stage("Install faster-whisper first -- see the README.")
        return info
    result("OK", "import faster_whisper")

    if audio is None:
        audio = Path("amd_spike_test_audio.wav")
        if not audio.exists():
            _make_test_wav(audio)
        result("INFO", "test audio", f"{audio} (synthetic tone, 5s)")
        log("       This measures compute time, not accuracy. The transcript will")
        log("       be nonsense -- that is expected and fine.")
    else:
        result("INFO", "test audio", redact(str(audio)))

    log(f"       model: {model_id}")
    log("       The first run downloads the model, so it will take a while.")

    # --- C1: GPU でロード。#2021 のクラッシュが出るならここ ---
    log()
    log("-- loading on GPU (device='cuda', compute_type='float16') --")
    gpu_model = None
    try:
        gpu_model = WhisperModel(model_id, device="cuda", device_index=0,
                                 compute_type="float16")
        result("OK", "model loaded on GPU")
    except Exception as exc:
        result("FAIL", "loading the model on GPU", type(exc).__name__)
        log()
        log("       vvv PLEASE INCLUDE THIS TEXT IN YOUR REPORT vvv")
        log("       (we need the exact wording to detect out-of-memory errors)")
        log(redact(traceback.format_exc()))
        log("       ^^^ end ^^^")
        info["gpu_load_error"] = redact(f"{type(exc).__name__}: {exc}")
        fail_stage("The model could not be loaded on the GPU. The exception text "
                   "above is exactly what we need -- please report it verbatim.")
        return info

    # --- C2: GPU のレイテンシ ---
    log()
    log("-- time per utterance --")
    try:
        _transcribe_once(gpu_model, audio)  # ウォームアップ (初回は初期化を含む)
        gpu_times = [_transcribe_once(gpu_model, audio) for _ in range(runs)]
        gpu_best = min(gpu_times)
        info["gpu_times"] = gpu_times
        result("OK", "GPU", "  ".join(f"{t:.3f}s" for t in gpu_times)
               + f"  (best {gpu_best:.3f}s)")
    except Exception as exc:
        result("FAIL", "running inference on GPU", type(exc).__name__)
        log(redact(traceback.format_exc()))
        info["gpu_infer_error"] = redact(f"{type(exc).__name__}: {exc}")
        fail_stage("Inference failed on the GPU -- please report the text above.")
        return info

    # --- C3 / R9: スレッド安全性。過去に別ライブラリで実機フリーズを起こしている ---
    log()
    log("-- concurrent use (VRCT drives one model from both mic and speaker) --")
    errors: list[str] = []

    # model を引数で渡す。クロージャで掴むと、ハングしてスレッドが生き残った
    # ままこの関数を抜けるときに名前が消えて NameError になり、
    # 肝心のハングの実態が別のエラーに化ける。
    def worker(model) -> None:
        try:
            for _ in range(2):
                _transcribe_once(model, audio)
        except Exception as exc:
            errors.append(redact(f"{type(exc).__name__}: {exc}"))

    threads = [threading.Thread(target=worker, args=(gpu_model,), daemon=True)
               for _ in range(2)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    # ハングしても救えるよう必ずタイムアウトを付ける (daemon なので抜けられる)
    budget = max(60.0, gpu_best * 20)
    for t in threads:
        t.join(timeout=budget)
    hung = any(t.is_alive() for t in threads)
    if hung:
        result("FAIL", "concurrent use", f"did not finish within {budget:.0f}s -- looks like a hang")
        log("       This is an important result, please report it. It means VRCT")
        log("       would need to serialise GPU access on AMD.")
        info["thread_safety"] = "hang"
    elif errors:
        result("FAIL", "concurrent use", "; ".join(errors))
        info["thread_safety"] = errors
    else:
        result("OK", "concurrent use",
               f"2 threads x 2 runs finished in {time.perf_counter() - t0:.1f}s")
        info["thread_safety"] = "ok"

    # gpu_model はここで del しない。ハングしたスレッドが生き残っている場合に
    # そのスレッドが掴んでいる参照を壊してしまう。CPU モデルはシステム RAM を
    # 使うので、GPU 側を抱えたままでも競合しない。

    # --- C4: CPU と比べる。ここが本題 ---
    log()
    log("-- for comparison: CPU (the path VRCT already has today) --")
    cpu_model = None
    try:
        cpu_model = WhisperModel(model_id, device="cpu", compute_type="int8")
        _transcribe_once(cpu_model, audio)
        cpu_times = [_transcribe_once(cpu_model, audio) for _ in range(runs)]
        cpu_best = min(cpu_times)
        info["cpu_times"] = cpu_times
        result("OK", "CPU (int8)", "  ".join(f"{t:.3f}s" for t in cpu_times)
               + f"  (best {cpu_best:.3f}s)")
        log()
        speedup = cpu_best / gpu_best if gpu_best > 0 else 0
        result("INFO", "how much faster the GPU is", f"{speedup:.2f}x")
        info["speedup"] = speedup
        if speedup < 1.2:
            log("       -> The GPU is barely faster than the CPU here. That is a")
            log("          legitimate result and may mean AMD support is not worth")
            log("          shipping. Please report it as-is.")
    except Exception:
        result("WARN", "CPU comparison failed", "we will go on the GPU numbers alone")
        log(redact(traceback.format_exc()))
    finally:
        # ここでは解放しない。解放そのものが Stage D の測定対象であり、
        # RX 7900 XTX の実機で帰ってこないことを確認している (2026-09-21)。
        # 1要素のリストに入れて渡し、Stage D がそこから参照を落とす。
        info["gpu_box"] = [gpu_model] if gpu_model is not None else []
        info["cpu_box"] = [cpu_model] if cpu_model is not None else []
    return info


# ----------------------------------------------------------------------------
# Stage E -- compute type と 2台目の GPU
# ----------------------------------------------------------------------------

# 小さいモデル。ここで見たいのは「その compute type でカーネルが動くか」で
# あって精度でも速度でもないので、turbo を何度も載せ直す必要はない。
_SMALL_MODEL = "Systran/faster-whisper-tiny"

# VRCT が AMD 向けに許可している型 (設計 §3)。実機の結果と突き合わせる。
_DESIGN_ALLOWS = ("float16", "float32")


def stage_e(audio: Path) -> dict:
    section("Stage E: which compute types actually work")
    log("       CTranslate2 advertises int8 and bfloat16 on this GPU, but VRCT's")
    log("       design only allows float16/float32 on AMD. If int8 works, the")
    log("       design is leaving VRAM and speed on the table. If it does not,")
    log("       the design is right to be conservative.")
    log(f"       Uses a small model ({_SMALL_MODEL}), so this is quick.")
    info: dict = {}
    import ctranslate2
    from faster_whisper import WhisperModel

    try:
        advertised = sorted(ctranslate2.get_supported_compute_types("cuda", 0))
    except Exception:
        result("WARN", "could not ask for the supported compute types", "skipping")
        return info

    log()
    working: list[str] = []
    for compute_type in advertised:
        try:
            model = WhisperModel(_SMALL_MODEL, device="cuda", device_index=0,
                                 compute_type=compute_type)
            # 解放はここでしない (Stage D の測定対象なので)。tiny なので
            # 全部抱えたままでも VRAM は数百 MB で収まる。
            _keep_alive.append(model)
            t0 = time.perf_counter()
            _transcribe_once(model, audio)
            elapsed = time.perf_counter() - t0
            working.append(compute_type)
            note = "" if compute_type in _DESIGN_ALLOWS else "  <- not in VRCT's list"
            result("OK", f"compute_type={compute_type}", f"{elapsed:.3f}s{note}")
        except Exception as exc:
            result("FAIL", f"compute_type={compute_type}", redact(f"{type(exc).__name__}: {exc}"))
    info["working_compute_types"] = working

    extra = [t for t in working if t not in _DESIGN_ALLOWS]
    missing = [t for t in _DESIGN_ALLOWS if t not in working]
    log()
    if missing:
        result("FAIL", "a type VRCT relies on does not work", ", ".join(missing))
        log("       This one matters -- it means the design picks a type that")
        log("       the hardware cannot run. Please report it.")
    if extra:
        result("INFO", "works but VRCT does not offer it", ", ".join(extra))

    # 2台目 (統合 GPU) に載せたらどうなるか。VRCT はアーキゲートで弾くが、
    # 「弾かなければ何が起きるのか」を知っておきたい。
    try:
        count = ctranslate2.get_cuda_device_count()
    except Exception:
        count = 0
    if count > 1:
        log()
        log("-- device 1 (the one VRCT's architecture gate rejects) --")
        try:
            model = WhisperModel(_SMALL_MODEL, device="cuda", device_index=1,
                                 compute_type="float16")
            _keep_alive.append(model)
            _transcribe_once(model, audio)
            result("WARN", "device 1 loaded and ran anyway",
                   "the gate may be stricter than it needs to be")
            info["device1"] = "works"
        except Exception as exc:
            result("OK", "device 1 refuses to run", redact(f"{type(exc).__name__}: {exc}"))
            log("       Good -- this is what the architecture gate protects users from.")
            info["device1"] = redact(f"{type(exc).__name__}: {exc}")
    return info


# ----------------------------------------------------------------------------
# Stage F -- 翻訳 (ctranslate2.Translator)。VRCT の CT2 利用はこちらが本数
# ----------------------------------------------------------------------------

# VRCT の既定の翻訳モデル (translation_utils.py の ctranslate2_weights)。
_TRANSLATION_REPO = "jncraton/m2m100_418M-ct2-int8"

# 語彙に実在するトークンで組んだ英文 ("Hello the world is a big place.")。
# 本来は transformers の tokenizer が作るが、診断 exe には transformers を
# 入れていない (check_amd.spec の excludes)。測りたいのは翻訳の中身ではなく
# 所要時間なので、語彙にあるトークンを並べれば足りる。
# CPU 版 CTranslate2 で日本語が出ることを確認済み (2026-09-21)。
_SOURCE_TOKENS = ["__en__", "▁Hello", "▁the", "▁world", "▁is",
                  "▁a", "▁big", "▁place", ".", "</s>"]
_TARGET_PREFIX = ["__ja__"]


def _checkVocabulary(model_dir: Path) -> bool:
    """組んだトークンがこのモデルの語彙に実在するかを先に確かめる。

    語彙が違えば <unk> だらけになり、デコードが即終了して
    「速い」という誤った結果になる。
    """
    vocab_file = model_dir / "shared_vocabulary.json"
    if not vocab_file.exists():
        return True  # 確認できないだけ。測定は続ける
    try:
        vocab = set(json.loads(vocab_file.read_text(encoding="utf-8")))
    except Exception:
        return True
    unknown = [t for t in _SOURCE_TOKENS + _TARGET_PREFIX if t not in vocab]
    if unknown:
        result("WARN", "some tokens are not in this model's vocabulary",
               f"{len(unknown)} of {len(_SOURCE_TOKENS) + 1}")
        return False
    result("OK", "the test sentence is valid for this model")
    return True


def _translateOnce(translator) -> float:
    start = time.perf_counter()
    translator.translate_batch([_SOURCE_TOKENS], target_prefix=[_TARGET_PREFIX])
    return time.perf_counter() - start


def stage_f(runs: int, whisper_box: list, audio: Path) -> dict:
    section("Stage F: translation (ctranslate2.Translator)")
    log("       VRCT uses CTranslate2 for translation as well as speech, and")
    log("       translation runs on every single message. Stage C only covered")
    log("       faster-whisper, which is a different CTranslate2 class.")
    log(f"       model: {_TRANSLATION_REPO} (about 500 MB, downloaded once)")
    info: dict = {}
    try:
        import ctranslate2
        from huggingface_hub import snapshot_download
    except Exception:
        result("WARN", "cannot import what this stage needs", "skipping")
        return info

    try:
        model_dir = Path(snapshot_download(_TRANSLATION_REPO))
        result("OK", "translation model downloaded")
    except Exception as exc:
        result("FAIL", "downloading the translation model",
               redact(f"{type(exc).__name__}: {exc}"))
        log("       Probably a network problem rather than an AMD one.")
        return info
    _checkVocabulary(model_dir)

    # --- F1: GPU にロード ---
    log()
    log("-- loading the translator on the GPU (float16) --")
    gpu_box: list = []
    try:
        gpu_box.append(ctranslate2.Translator(
            str(model_dir), device="cuda", device_index=0, compute_type="float16",
            inter_threads=1, intra_threads=4))
        result("OK", "translator loaded on GPU")
    except Exception as exc:
        result("FAIL", "loading the translator on the GPU", type(exc).__name__)
        log(redact(traceback.format_exc()))
        info["gpu_load_error"] = redact(f"{type(exc).__name__}: {exc}")
        log("       This is a big deal: it would mean AMD users get GPU speech")
        log("       but CPU translation. Please report it.")
        return info
    info["gpu_box"] = gpu_box

    # --- F2: レイテンシ ---
    log()
    try:
        _translateOnce(gpu_box[0])  # ウォームアップ
        gpu_times = [_translateOnce(gpu_box[0]) for _ in range(runs)]
        gpu_best = min(gpu_times)
        info["gpu_times"] = gpu_times
        result("OK", "GPU", "  ".join(f"{t:.3f}s" for t in gpu_times)
               + f"  (best {gpu_best:.3f}s)")
    except Exception as exc:
        result("FAIL", "translating on the GPU", type(exc).__name__)
        log(redact(traceback.format_exc()))
        info["gpu_infer_error"] = redact(f"{type(exc).__name__}: {exc}")
        return info

    # --- F3: 同時実行。translation_translator.py:144 の RLock が守る経路 ---
    log()
    log("-- concurrent use (mic and speaker share one translator in VRCT) --")
    errors: list[str] = []

    def worker(translator) -> None:
        try:
            for _ in range(2):
                _translateOnce(translator)
        except Exception as exc:
            errors.append(redact(f"{type(exc).__name__}: {exc}"))

    threads = [threading.Thread(target=worker, args=(gpu_box[0],), daemon=True)
               for _ in range(2)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    budget = max(60.0, gpu_best * 20)
    for t in threads:
        t.join(timeout=budget)
    if any(t.is_alive() for t in threads):
        result("FAIL", "concurrent use", f"did not finish within {budget:.0f}s -- looks like a hang")
        info["thread_safety"] = "hang"
    elif errors:
        result("FAIL", "concurrent use", "; ".join(errors))
        info["thread_safety"] = errors
    else:
        result("OK", "concurrent use",
               f"2 threads x 2 runs finished in {time.perf_counter() - t0:.1f}s")
        info["thread_safety"] = "ok"

    # --- F4: 音声認識と翻訳を同時に。VRCT が実際に置かれている状態 ---
    if whisper_box:
        log()
        log("-- speech and translation on the GPU at the same time (what VRCT does) --")
        both_errors: list[str] = []

        def speech_worker(model) -> None:
            try:
                for _ in range(2):
                    _transcribe_once(model, audio)
            except Exception as exc:
                both_errors.append(redact(f"whisper: {type(exc).__name__}: {exc}"))

        pair = [threading.Thread(target=speech_worker, args=(whisper_box[0],), daemon=True),
                threading.Thread(target=worker, args=(gpu_box[0],), daemon=True)]
        t0 = time.perf_counter()
        for t in pair:
            t.start()
        for t in pair:
            t.join(timeout=120.0)
        if any(t.is_alive() for t in pair):
            result("FAIL", "both models at once", "did not finish within 120s -- looks like a hang")
            info["both"] = "hang"
        elif both_errors or errors:
            result("FAIL", "both models at once", "; ".join(both_errors + errors))
            info["both"] = both_errors + errors
        else:
            result("OK", "both models at once",
                   f"finished in {time.perf_counter() - t0:.1f}s")
            info["both"] = "ok"

    # --- F5: CPU と比べる ---
    log()
    log("-- for comparison: CPU (int8, the path VRCT has today) --")
    cpu_box: list = []
    try:
        cpu_box.append(ctranslate2.Translator(
            str(model_dir), device="cpu", compute_type="int8",
            inter_threads=1, intra_threads=4))
        _translateOnce(cpu_box[0])
        cpu_times = [_translateOnce(cpu_box[0]) for _ in range(runs)]
        cpu_best = min(cpu_times)
        info["cpu_times"] = cpu_times
        info["cpu_box"] = cpu_box
        result("OK", "CPU (int8)", "  ".join(f"{t:.3f}s" for t in cpu_times)
               + f"  (best {cpu_best:.3f}s)")
        speedup = cpu_best / gpu_best if gpu_best > 0 else 0
        result("INFO", "how much faster the GPU is at translation", f"{speedup:.2f}x")
        info["speedup"] = speedup
        if speedup < 1.2:
            log("       -> Not faster. For scale, the same measurement on an")
            log("          NVIDIA RTX 2080 Ti gives 0.54x -- the GPU loses there")
            log("          too, because one short sentence is too small a job to")
            log("          pay back the cost of going to the GPU. So this is")
            log("          probably NOT an AMD problem. Please report it as-is.")
    except Exception:
        result("WARN", "CPU comparison failed", "we will go on the GPU numbers alone")
        log(redact(traceback.format_exc()))
    return info


# ----------------------------------------------------------------------------
# Stage D -- 後片付け。ハングしうるので必ず最後に置く
# ----------------------------------------------------------------------------

def _releaseInThread(label: str, box: list, budget: float = 60.0) -> bool:
    """box が持つ最後の参照を落とし、デストラクタが返るまでを測る。

    返ってこない実績があるので、必ず別スレッドで落とす。daemon なので
    返らなくてもこのツール自体は先に進める。
    """
    if not box:
        result("--", f"release {label}", "nothing to release")
        return True
    done = threading.Event()
    errors: list[str] = []

    def drop() -> None:
        try:
            box.clear()  # 最後の参照。ここでデストラクタが走る
            gc.collect()
        except Exception as exc:
            errors.append(redact(f"{type(exc).__name__}: {exc}"))
        finally:
            done.set()

    t0 = time.perf_counter()
    threading.Thread(target=drop, daemon=True).start()
    finished = done.wait(budget)
    elapsed = time.perf_counter() - t0
    if not finished:
        result("FAIL", f"release {label}", f"did not return within {budget:.0f}s -- HANG")
        return False
    if errors:
        result("WARN", f"release {label}", "; ".join(errors))
        return False
    result("OK", f"release {label}", f"{elapsed:.2f}s")
    return True


def stage_d(model_id: str, c_info: dict, f_info: dict) -> dict:
    section("Stage D: releasing models")
    log("       On 2026-09-21 this is where an RX 7900 XTX stopped responding,")
    log("       after every measurement had already succeeded.")
    log("       It matters because VRCT rebuilds the transcriber whenever the")
    log("       model or the device changes, which releases the old model. If")
    log("       that does not return, changing a setting freezes the app.")
    log("       Every release below runs in its own thread with a timeout, so")
    log("       this stage cannot hang the tool itself.")
    info: dict = {}

    # CPU から。GPU 固有の問題なのかどうかが最初の切り分け。
    log()
    log("-- CPU models (is this specific to the GPU?) --")
    info["cpu_whisper"] = _releaseInThread("the CPU speech model", c_info.get("cpu_box", []))
    info["cpu_translator"] = _releaseInThread("the CPU translator", f_info.get("cpu_box", []))

    # VRCT の実際の手順: 新しいモデルを載せてから、古い方を落とす。
    log()
    log("-- the sequence VRCT actually performs when you change the model --")
    second: list = []
    try:
        from faster_whisper import WhisperModel
        t0 = time.perf_counter()
        second.append(WhisperModel(model_id, device="cuda", device_index=0,
                                   compute_type="float16"))
        result("OK", "loaded a second speech model on the GPU",
               f"{time.perf_counter() - t0:.1f}s")
    except Exception as exc:
        result("WARN", "could not load a second model",
               redact(f"{type(exc).__name__}: {exc}"))
    info["switch"] = _releaseInThread(
        "the first GPU speech model, while the second is loaded",
        c_info.get("gpu_box", []))

    # 最後の1つを落とす。ここだけが駄目なら、影響はアプリ終了時に限られる。
    log()
    log("-- releasing the rest --")
    info["translator"] = _releaseInThread("the GPU translator", f_info.get("gpu_box", []))
    info["last"] = _releaseInThread("the last GPU speech model", second)

    log()
    if info.get("switch") and info.get("last"):
        result("OK", "conclusion", "releasing models returns -- no problem here")
    elif info.get("switch") and not info.get("last"):
        result("WARN", "conclusion", "only the very last release hangs")
        log("       That would affect shutting VRCT down, not changing settings.")
    else:
        result("FAIL", "conclusion", "releasing a model hangs")
        log("       This is the important result. It means VRCT has to avoid")
        log("       releasing models, or release them with a timeout.")
    return info


# ----------------------------------------------------------------------------

def main() -> int:
    # ctranslate2 を import する前に済ませる必要がある (関数の docstring 参照)。
    _setup_frozen_rocm_paths()
    _setup_console()
    parser = argparse.ArgumentParser(
        description="VRCT: check whether AMD GPU (ROCm) inference works")
    parser.add_argument("--stage", choices=["a", "ab", "abc"], default="abc",
                        help="how far to go (default: abc)")
    parser.add_argument("--model", default="deepdml/faster-whisper-large-v3-turbo-ct2",
                        help="model for Stage C. For a quick first pass use "
                             "Systran/faster-whisper-tiny")
    parser.add_argument("--audio", type=Path, default=None,
                        help="wav to use for Stage C (16kHz mono). "
                             "Omit to generate a synthetic one")
    parser.add_argument("--runs", type=int, default=3,
                        help="how many timed runs (default: 3)")
    args = parser.parse_args()

    _openReport()
    log("VRCT -- AMD GPU check (issue #88)")
    log(f"started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("This script does not send anything anywhere. It only writes a local file.")
    log("The report is written as it goes, so nothing is lost if this stops early.")

    a_info = stage_a()
    if not _stage_failed and args.stage in ("ab", "abc"):
        stage_b(a_info)
    if not _stage_failed and args.stage == "abc":
        c_info = stage_c(args.model, args.audio, args.runs)
        if not _stage_failed:
            audio = args.audio or Path("amd_spike_test_audio.wav")
            stage_e(audio)
            f_info = stage_f(args.runs, c_info.get("gpu_box", []), audio)
            # Stage D は最後。解放がハングすると以降の GPU 作業が当てに
            # ならなくなるので、測り終えてから触る。
            stage_d(args.model, c_info, f_info)

    section("Summary")
    if _stage_failed:
        log("Stopped early. See the '!!' line above and the FAIL just before it.")
        log("Partial results are still genuinely useful -- please share the report.")
    else:
        log("Everything ran. Please share the report.")
    log()
    # 実パスはコンソールにだけ出す (検証者がファイルを見つける必要がある)。
    # log() 側は redact を通るので、レポートには伏せ字で載る。
    print(f"report written to: {REPORT_PATH.resolve()}", flush=True)
    log("Please read the report before sharing. Paths are redacted, but do check.")
    if _report is not None:
        try:
            _report.close()
        except Exception:
            pass

    # 凍結 exe をエクスプローラからダブルクリックで起動すると、終了と同時に
    # コンソールが閉じて何も読めない。協力者には「動かなかった」ように見える
    # (レポートは残るが、そこまで気付けない)。対話的なときだけ待つ。
    # パイプ越しや CI では止めない。
    if getattr(sys, "frozen", False):
        try:
            if sys.stdin is not None and sys.stdin.isatty():
                input("\nPress Enter to close this window...")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    _code = main()
    # 普通に終了するとインタプリタ終了時にモデルのデストラクタが走り、ROCm では
    # そこで帰ってこない (stage_c の finally 参照)。レポートは書き終えているので、
    # 後片付けを待たずにプロセスを落とす。os._exit はバッファを流さないため、
    # log() が毎行 flush していることに依存している。
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_code)
