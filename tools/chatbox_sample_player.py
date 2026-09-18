"""Play multilingual training samples into the local VRChat chatbox over OSC.

Default: press Enter to start, shuffled samples, 6 seconds between messages,
repeat until Q/Ctrl+C. P=pause/resume, R=status (console focused).
--dry-run never opens a socket. UDP submission does not confirm display.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import re
import socket
import sys
import time
import unicodedata
import uuid


@dataclass(frozen=True)
class Sample:
    id: str
    language: str
    text: str
    tags: tuple[str, ...]

    @property
    def units(self) -> int:
        return len(self.text.encode("utf-16-le")) // 2

    @property
    def length(self) -> str:
        return "tiny" if self.units <= 5 else "short" if self.units <= 30 else "medium" if self.units <= 80 else "long"


def load_samples(folder: Path) -> list[Sample]:
    """Fail before sending anything if any editable sample file is invalid."""
    files = sorted(folder.glob("*.json"))
    if not files:
        raise ValueError(f"No sample JSON files found in {folder}")
    samples, languages = [], set()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError(f"{path.name}: expected a language-to-samples object")
        for language, rows in data.items():
            if not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z]+)?|mixed", language) or language in languages:
                raise ValueError(f"{path.name}: invalid or repeated language {language!r}")
            languages.add(language)
            if not isinstance(rows, list) or not rows:
                raise ValueError(f"{path.name}: {language} needs a nonempty list")
            for index, row in enumerate(rows, 1):
                identity = f"{language}_{index:03d}"
                if not isinstance(row, dict) or not isinstance(row.get("text"), str):
                    raise ValueError(f"{identity}: text must be a string")
                text, tags = row["text"], row.get("tags", [])
                if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                    raise ValueError(f"{identity}: tags must be a list of strings")
                if not text.strip() or any(unicodedata.category(c).startswith("C") and c != "\n" for c in text):
                    raise ValueError(f"{identity}: blank text or unsupported control character")
                sample = Sample(identity, language, text, tuple(tags))
                if sample.units > 144 or text.count("\n") >= 9:
                    raise ValueError(f"{identity}: exceeds 144 UTF-16 units or 9 explicit lines")
                samples.append(sample)
    return samples


def message_bytes(text: str) -> bytes:
    # Reuse the same OSC library as VRCT. Booleans must be OSC T/F, not integers.
    from pythonosc.osc_message_builder import OscMessageBuilder

    builder = OscMessageBuilder(address="/chatbox/input")
    for value in (text, True, False):
        builder.add_arg(value)
    return builder.build().dgram


class Playback:
    """Single-threaded playback: no catch-up bursts and no send after pause/quit."""

    def __init__(self, samples, send, *, interval=6, once=False, max_messages=0,
                 ordered=False, seed=None, clock=time.monotonic, emit=print):
        self.order = list(samples)
        self.send, self.clock, self.emit = send, clock, emit
        self.interval, self.once, self.max_messages = interval, once, max_messages
        self.ordered, self.rng = ordered, random.Random(seed)
        if not ordered:
            self.rng.shuffle(self.order)
        self.index = self.count = 0
        self.cycle = 1
        self.paused = self.stopped = False
        self.deadline = clock()

    def command(self, key: str):
        if key == "q":
            self.stopped = True
        elif key == "p":
            self.paused = not self.paused
            self.deadline = self.clock() + self.interval
            self.emit("[paused] P to resume" if self.paused else "[resumed]")
        elif key == "r":
            self.emit(f"[status] count={self.count}, cycle={self.cycle}, paused={self.paused}")

    def tick(self):
        if self.stopped or self.paused or self.clock() < self.deadline:
            return
        sample = self.order[self.index]
        self.send(sample)
        self.count += 1
        self.index += 1
        # Completion time, not a previous deadline, bounds the next send.
        self.deadline = self.clock() + self.interval
        if self.max_messages and self.count >= self.max_messages:
            self.stopped = True
        if self.index == len(self.order):
            if self.once:
                self.stopped = True
            else:
                self.index = 0
                self.cycle += 1
                if not self.ordered:
                    self.rng.shuffle(self.order)


def base_directory() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, default=base_directory() / "chatbox_samples")
    # Run on the PC logged into the sending account; no remote/broadcast target.
    parser.add_argument("--port", type=int, default=9000, help="Local VRChat OSC input UDP port")
    parser.add_argument("--interval", type=float, default=6, help="Seconds between submissions (minimum 3)")
    parser.add_argument("--languages", help="Comma-separated codes, e.g. ja,en,ko,zh-Hans; mixed=layout cases")
    parser.add_argument("--length", choices=("tiny", "short", "medium", "long"))
    parser.add_argument("--ordered", action="store_true", help="Keep catalog order instead of shuffling")
    parser.add_argument("--seed", type=int, help="Repeatable shuffle order")
    parser.add_argument("--once", action="store_true", help="Stop after one pass")
    parser.add_argument("--max-messages", type=int, default=0, help="Stop after N submissions; 0=unlimited")
    parser.add_argument("--dry-run", action="store_true", help="Preview without opening a socket or writing a log")
    parser.add_argument("--list", action="store_true", help="Show catalog counts without sending")
    parser.add_argument("--start", action="store_true", help="Start sending without the interactive Enter prompt")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535 or args.max_messages < 0:
        parser.error("--port must be 1..65535; --max-messages must be nonnegative")
    if not math.isfinite(args.interval) or args.interval < 3:
        parser.error("--interval must be finite and at least 3 seconds")
    return args


def read_key() -> str:
    if not sys.stdin.isatty():
        return ""
    import msvcrt

    if not msvcrt.kbhit():
        return ""
    key = msvcrt.getwch()
    if key in ("\x00", "\xe0"):
        msvcrt.getwch()
        return ""
    return key.lower()


def main(argv=None) -> int:
    args = parse_args(argv)
    samples = load_samples(args.samples)
    if args.languages:
        wanted = {s.strip() for s in args.languages.split(",")}
        unknown = wanted - {s.language for s in samples}
        if unknown:
            raise ValueError(f"Unknown languages: {', '.join(sorted(unknown))}")
        samples = [s for s in samples if s.language in wanted]
    if args.length:
        samples = [s for s in samples if s.length == args.length]
    if not samples:
        raise ValueError("No samples match the selected filters")
    print(f"Samples: {len(samples)}, languages: {dict(sorted(Counter(s.language for s in samples).items()))}")
    print(f"Lengths (UTF-16 units): {dict(sorted(Counter(s.length for s in samples).items()))}")
    if args.list:
        return 0
    if sys.platform != "win32":
        raise RuntimeError("Interactive playback requires Windows")
    print(f"{'DRY RUN (no network)' if args.dry_run else 'OSC -> 127.0.0.1:' + str(args.port)}, interval={args.interval}s")
    print("P=pause/resume  Q=quit  R=status (console focused, no Enter required)")
    if not args.dry_run and not args.start:
        if not sys.stdin.isatty():
            raise ValueError("Use --start to send from a non-interactive terminal, or --dry-run to preview")
        if input("Press Enter to START sending, or type Q then Enter to cancel: ").strip():
            print("Cancelled; nothing sent.")
            return 0
    log = sock = None
    player = None
    try:
        if not args.dry_run:
            directory = base_directory() / "sent_logs"
            directory.mkdir(exist_ok=True)
            identity = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid.uuid4().hex[:8]
            log = (directory / f"{identity}.jsonl").open("x", encoding="utf-8")
            print(f"Submission log: {log.name}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)

        def send(sample):
            if sock is not None:
                packet = message_bytes(sample.text)
                if sock.sendto(packet, ("127.0.0.1", args.port)) != len(packet):
                    raise OSError("Incomplete UDP datagram")
                record = {"submitted_at_utc": datetime.now(timezone.utc).isoformat(),
                          "event": "udp_submitted", "id": sample.id, "language": sample.language,
                          "text": sample.text, "utf16_units": sample.units,
                          "explicit_lines": sample.text.count("\n") + 1,
                          "target": f"127.0.0.1:{args.port}", "tags": list(sample.tags)}
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
                log.flush()
            preview = sample.text.replace("\n", " \\n ")
            print(f"[{'preview' if args.dry_run else 'submitted'}] {sample.id} {sample.length} {sample.units}/144: {preview}", flush=True)

        player = Playback(samples, send, interval=args.interval, once=args.once,
                          max_messages=args.max_messages, ordered=args.ordered, seed=args.seed)
        while not player.stopped:
            player.command(read_key())
            player.tick()
            if not player.stopped:
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        if sock is not None:
            sock.close()
        if log is not None:
            log.close()
    print(f"done: {'previewed' if args.dry_run else 'submitted'}={player.count if player else 0}")
    return 0


def entrypoint() -> int:
    # Some Windows pipe encodings cannot display all scripts. The OSC text and
    # UTF-8 log remain intact even if the console needs escaped characters.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    try:
        return main()
    except KeyboardInterrupt:
        print("Cancelled; no further submissions.")
        return 0
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
