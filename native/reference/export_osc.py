"""VRChat へ送る OSC (chatbox の入力・入力中) のバイト列を、今の Python 版と同じ python-osc で記録する。

    python native/reference/export_osc.py   ->  native/testdata/osc/osc.json

osc.OSCHandler.sendMessage / sendTyping が SimpleUDPClient に渡すのと同じ引数で組み立てる。送信はしない。
"""

import json
from pathlib import Path

from pythonosc.osc_message_builder import OscMessageBuilder

ROOT = Path(__file__).resolve().parents[2]


def build(addr, args):
    b = OscMessageBuilder(address=addr)
    for a in args:
        b.add_arg(a)
    return b.build().dgram.hex()


def main():
    cases = []
    for flag in (True, False):
        cases.append({"kind": "typing", "flag": flag, "bytes": build("/chatbox/typing", [flag])})
    for msg in ["a", "abc", "abcd", "Hello World", "こんにちは、世界！", "emoji 😀 and\nnewline", "x" * 144,
                "[en] translated / 原文"]:
        for n in (True, False):
            cases.append({"kind": "input", "message": msg, "notification": n,
                          "bytes": build("/chatbox/input", [msg, True, n])})
    out = ROOT / "native" / "testdata" / "osc" / "osc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cases, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(cases))


if __name__ == "__main__":
    main()
