"""Compare poc-ct2's rust.json (or rust-cuda.json) with reference.py's python.json.

    python native/poc-ct2/compare.py <data dir> [rust.json]
"""

import json
import sys
from pathlib import Path

data = Path(sys.argv[1])
py = json.loads((data / "python.json").read_text(encoding="utf-8"))
rs = json.loads((data / (sys.argv[2] if len(sys.argv) > 2 else "rust.json")).read_text(encoding="utf-8"))
ok = True

print(f"device={rs['device']} whisper load {rs['whisper']['load_ms']} ms")
for name, p in py["whisper"].items():
    r = rs["whisper"]["results"][name]
    ps, rseg = p["segments"][0] if p["segments"] else None, r["segments"][0]
    same_text = p["text"] == r["text"]
    same_tokens = ps is not None and ps["tokens"] == [t for t in rseg["tokens"]]
    line = (f"{name:8s} lang {p['language']}/{r['language']} p {p['language_probability']:.4f}/{r['language_probability']:.4f}"
            f" text={'same' if same_text else 'DIFF'} tokens={'same' if same_tokens else 'diff'}"
            f" mel_diff={r['mel_max_abs_diff']:.2e} {r['ms']} ms")
    if ps is not None:
        line += (f" avg_logprob {ps['avg_logprob']:.4f}/{rseg['avg_logprob']:.4f}"
                 f" no_speech {ps['no_speech_prob']:.4f}/{rseg['no_speech_prob']:.4f}")
    print(line)
    if not same_text:
        ok = False
        print(f"    python: {p['text']!r}\n    rust:   {r['text']!r}")

for p, r in zip(py["nllb"], rs["nllb"]):
    same_src = p["source_tokens"] == r["source_tokens"]
    same = p["translation"] == r["translation"]
    print(f"{p['source_language']}->{p['target_language']} source_tokens={'same' if same_src else 'DIFF'}"
          f" translation={'same' if same else 'DIFF'} {r['ms']} ms  {r['translation']!r}")
    if not (same_src and same):
        ok = False
        if not same_src:
            print(f"    python: {p['source_tokens']}\n    rust:   {r['source_tokens']}")
        if not same:
            print(f"    python: {p['translation']!r}")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
