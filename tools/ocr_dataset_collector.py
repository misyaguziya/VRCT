"""VRChat学習画像のローカル収集CLI。自動撮影は未分類で保存する。

python tools/ocr_dataset_collector.py [session_name]
既定: 自動選択(HWND/OpenVR D3D11)、左眼、2秒周期、10分で終了。
コンソールで P=一時停止/再開、Q=終了、R=状態表示（Enter不要）。
--manual: Enter=その場でpositive撮影、N=negative撮影、U=未分類撮影。
--wander: VRChatのOSC入力(/input/*)でアバターをランダムに歩かせる（要OSC有効化）。
撮影開始から保存・解放まで同じworkerが所有。VRCT本体へimportしない。
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import queue
import random
import socket
import struct
import sys
import threading
import time
import uuid

from PIL import Image

if __package__:
    from .ocr_capture_source import CaptureSource, CaptureUnavailable, Frame
else:
    from ocr_capture_source import CaptureSource, CaptureUnavailable, Frame


def session_name(value: str) -> str:
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)}
    if (not value or len(value) > 80 or value in (".", "..")
            or any(c in '<>:"/\\|?*' or ord(c) < 32 for c in value)
            or value.endswith((".", " ")) or value.split(".")[0].upper() in reserved):
        raise argparse.ArgumentTypeError("session_name must be a valid single folder name (1..80 characters)")
    return value


def next_deadline(previous: float, now: float, interval: float) -> float:
    """Keep the requested cadence, skipping missed slots instead of bursting."""
    return previous + max(1, math.floor((now - previous) / interval) + 1) * interval


def osc_message(address: str, value) -> bytes:
    """Minimal OSC 1.0 encoder for one int or float; keeps the exe free of python-osc."""
    def pad(raw: bytes) -> bytes:
        return raw + b"\0" * (4 - len(raw) % 4)
    tag, payload = (",i", struct.pack(">i", value)) if isinstance(value, int) else (",f", struct.pack(">f", value))
    return pad(address.encode()) + pad(tag.encode()) + payload


class Wanderer:
    """Random walk via VRChat OSC input. No obstacle sensing, so it just turns often."""
    # ponytail: blind random walk; add stuck detection (frame diff) if it hugs walls too long.

    def __init__(self, host: str = "127.0.0.1", port: int = 9000, rng=None, send=None) -> None:
        self.target = (host, port)
        self.rng = rng or random.Random()
        self._socket = None if send else socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send = send or (lambda address, value: self._socket.sendto(osc_message(address, value), self.target))
        self.stop_requested = threading.Event()
        self.paused = threading.Event()
        self.thread = threading.Thread(target=self.run, name="wander", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def toggle_pause(self) -> None:
        self.paused.clear() if self.paused.is_set() else self.paused.set()

    def _hold(self, address: str, value, seconds: float) -> None:
        self.send(address, value)
        self.stop_requested.wait(seconds)
        self.send(address, 0 if isinstance(value, int) else 0.0)

    def step(self) -> None:
        self._hold("/input/Vertical", 1.0, self.rng.uniform(2, 6))
        self._hold("/input/LookHorizontal", self.rng.choice((-1.0, 1.0)), self.rng.uniform(0.2, 1.2))
        if self.rng.random() < 0.2:
            self._hold("/input/Jump", 1, 0.1)

    def run(self) -> None:
        try:
            while not self.stop_requested.is_set():
                if self.paused.is_set():
                    self.stop_requested.wait(0.1)
                else:
                    self.step()
        finally:
            self.release()

    def release(self) -> None:
        """Always leave VRChat with all axes neutral, or the avatar keeps walking."""
        for address in ("/input/Vertical", "/input/LookHorizontal"):
            self.send(address, 0.0)
        self.send("/input/Jump", 0)

    def stop(self) -> None:
        self.stop_requested.set()
        if self.thread.is_alive():
            self.thread.join(2)
        else:
            self.release()
        if self._socket:
            self._socket.close()


class ImageStore:
    """Publish complete PNG/JSON pairs and count only successful saves."""

    def __init__(self, root: Path, session: str) -> None:
        self.directory = root.resolve() / session
        self.session = session
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid.uuid4().hex[:8]
        self.count = 0

    def save(self, frame: Frame, label: str, max_age: float) -> Path:
        if time.monotonic() - frame.captured_monotonic > max_age:
            raise CaptureUnavailable("Frame took too long to acquire; not saved")
        folder = self.directory / label
        folder.mkdir(parents=True, exist_ok=True)
        stem = f"{self.run_id}_{self.count:06d}"
        png, metadata = folder / f"{stem}.png", folder / f"{stem}.json"
        png_tmp, json_tmp = folder / f"{stem}.png.part", folder / f"{stem}.json.part"
        record = {**frame.metadata, "session": self.session, "run_id": self.run_id,
                  "label": label, "image": png.name, "width": frame.rgb.shape[1],
                  "height": frame.rgb.shape[0], "png_compress_level": 1}
        published = []
        try:
            with png_tmp.open("xb") as stream:
                Image.fromarray(frame.rgb).save(stream, format="PNG", compress_level=1)
            with json_tmp.open("x", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
            # Windows rename refuses to overwrite an existing destination.
            json_tmp.rename(metadata)
            published.append(metadata)
            png_tmp.rename(png)
            published.append(png)
        except BaseException:
            for path in (png_tmp, json_tmp, *published):
                path.unlink(missing_ok=True)
            raise
        self.count += 1
        return png


class Collector:
    """Commands cross threads; capture objects and their cleanup never do."""

    def __init__(self, source_factory, store: ImageStore, *, interval: float = 2,
                 duration: float = 600, manual: bool = False, max_frames: int = 0,
                 max_age: float = 2, emit=print) -> None:
        self.source_factory, self.store = source_factory, store
        self.interval, self.duration = interval, duration
        self.manual, self.max_frames, self.max_age = manual, max_frames, max_age
        self.emit = emit
        self.commands = queue.Queue(maxsize=16)
        self.stop_requested = threading.Event()
        self.done = threading.Event()
        self.thread = threading.Thread(target=self.run, name="dataset-capture", daemon=False)
        self.paused = False
        self.error = None
        self._last_warning = None

    def start(self) -> None:
        self.thread.start()

    def command(self, name: str) -> None:
        if name == "stop":
            self.stop_requested.set()
            return
        try:
            self.commands.put_nowait(name)
        except queue.Full:
            self.emit("[WARN] Command queue is full; wait for the current capture")

    def stop(self) -> None:
        self.stop_requested.set()
        self.thread.join()  # Never close a native resource while read() is active.

    def _save(self, source, label: str, end: float) -> None:
        if self.stop_requested.is_set() or time.monotonic() >= end:
            return
        try:
            frame = source.capture()  # Fresh request, no previous-frame cache.
            if self.stop_requested.is_set() or time.monotonic() >= end:
                return
            path = self.store.save(frame, label, self.max_age)
            self._last_warning = None
            self.emit(f"[saved {label}] {path} (this run: {self.store.count})")
        except CaptureUnavailable as exc:
            message = str(exc)
            if message != self._last_warning:
                self.emit(f"[waiting] {message}")
                self._last_warning = message

    def run(self) -> None:
        source = None
        try:
            source = self.source_factory()
            now = time.monotonic()
            end = now + self.duration if self.duration else math.inf
            deadline = now
            while not self.stop_requested.is_set():
                now = time.monotonic()
                if now >= end or (self.max_frames and self.store.count >= self.max_frames):
                    break
                timeout = min(0.1, max(0, end - now))
                if not self.manual and not self.paused:
                    timeout = min(timeout, max(0, deadline - now))
                try:
                    command = self.commands.get(timeout=timeout)
                except queue.Empty:
                    command = None
                if command == "pause":
                    self.paused = not self.paused
                    deadline = time.monotonic() + self.interval
                    self.emit("[paused] P to resume" if self.paused else "[resumed]")
                elif command == "status":
                    self.emit(f"[status] saved={self.store.count}, paused={self.paused}")
                elif self.manual and not self.paused and command in ("positive", "negative", "unlabeled"):
                    self._save(source, command, end)
                if (not self.manual and not self.paused and not self.stop_requested.is_set()
                        and time.monotonic() >= deadline and time.monotonic() < end):
                    self._save(source, "unlabeled", end)
                    deadline = next_deadline(deadline, time.monotonic(), self.interval)
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.emit(f"[ERROR] {self.error}")
        finally:
            try:
                if source is not None:
                    source.close()
            except Exception as exc:
                self.error = f"Cleanup failed: {type(exc).__name__}: {exc}"
                self.emit(f"[ERROR] {self.error}")
            finally:
                self.done.set()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", nargs="?", type=session_name,
                        default=datetime.now().strftime("session_%Y%m%d_%H%M%S"))
    output_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path.cwd()
    parser.add_argument("--out", type=Path, default=output_root / "dataset_collected",
                        help="Output folder (exe: beside the executable; Python: current directory)")
    parser.add_argument("--backend", choices=("auto", "openvr", "hwnd"), default="auto")
    parser.add_argument("--eye", choices=("left", "right"), default="left")
    parser.add_argument("--interval", type=float, default=2, help="Target capture interval in seconds")
    parser.add_argument("--duration", type=float, default=600, help="Wall-clock seconds including pauses; 0=unlimited")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after this many successful saves; 0=unlimited")
    parser.add_argument("--max-age", type=float, default=2, help="Reject captures older than this many seconds")
    parser.add_argument("--manual", action="store_true", help="Enter=positive, N=negative, U=unlabeled (fresh capture)")
    parser.add_argument("--wander", action="store_true", help="Walk the avatar randomly via VRChat OSC input")
    parser.add_argument("--osc-port", type=int, default=9000, help="VRChat OSC input port (127.0.0.1)")
    args = parser.parse_args(argv)
    if not math.isfinite(args.interval) or args.interval < 0.1:
        parser.error("--interval must be finite and at least 0.1")
    if not math.isfinite(args.duration) or args.duration < 0:
        parser.error("--duration must be finite and nonnegative")
    if not math.isfinite(args.max_age) or args.max_age <= 0 or args.max_frames < 0:
        parser.error("--max-age must be finite and positive; --max-frames must be nonnegative")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    if sys.platform != "win32":
        print("[ERROR] This capture tool requires Windows", flush=True)
        return 1
    store = ImageStore(args.out, args.session)
    collector = Collector(lambda: CaptureSource(args.backend, args.eye), store,
                          interval=args.interval, duration=args.duration,
                          manual=args.manual, max_frames=args.max_frames, max_age=args.max_age,
                          emit=lambda message: print(message, flush=True))
    print(f"session={args.session}, backend={args.backend}, interval={args.interval}s, duration={args.duration}s", flush=True)
    print(f"output={store.directory}", flush=True)
    print("P=pause/resume  Q=quit  R=status (console focused, no Enter required)", flush=True)
    print("Enter=positive  N=negative  U=unlabeled" if args.manual else "Automatic capture -> unlabeled/", flush=True)
    wanderer = Wanderer(port=args.osc_port) if args.wander else None
    if wanderer:
        print(f"Wandering via OSC 127.0.0.1:{args.osc_port} (P also pauses walking)", flush=True)
    collector.start()
    if wanderer:
        wanderer.start()
    try:
        import msvcrt

        while not collector.done.wait(0.05):
            if not sys.stdin.isatty() or not msvcrt.kbhit():
                continue
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue
            commands = {"p": "pause", "q": "stop", "r": "status",
                        "\r": "positive", "n": "negative", "u": "unlabeled"}
            if key.lower() in commands:
                collector.command(commands[key.lower()])
            if wanderer and key.lower() == "p":
                wanderer.toggle_pause()
    except KeyboardInterrupt:
        print("Stopping after the current operation...", flush=True)
    finally:
        if wanderer:
            wanderer.stop()
        collector.stop()
    print(f"{'ERROR' if collector.error else 'done'}: saved={store.count} in this run, output={store.directory}", flush=True)
    return 1 if collector.error else 0


def entrypoint() -> int:
    """Keep the result visible on an interactive, argument-free exe launch."""
    try:
        return main()
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", flush=True)
        return 1
    finally:
        if getattr(sys, "frozen", False) and len(sys.argv) == 1 and sys.stdin.isatty():
            try:
                input("Press Enter to close...")
            except (EOFError, KeyboardInterrupt):
                pass


if __name__ == "__main__":
    raise SystemExit(entrypoint())
