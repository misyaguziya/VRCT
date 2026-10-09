"""Write THIRD_PARTY_LICENSES.txt for a native crate from its Cargo.lock.

    python tools/collect_rust_licenses.py native/vrct-graphics

Uses `cargo metadata --locked --offline` (crates must already be fetched) and
copies each dependency's LICENSE*/COPYING*/NOTICE* files from the cargo
registry. Identical texts are written once, preceded by the crates using them.
Fails when a dependency ships no license file, so nothing is silently omitted.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

PATTERNS = ("LICENSE", "LICENCE", "COPYING", "NOTICE")


def main():
    crate = Path(sys.argv[1]).resolve()
    meta = json.loads(subprocess.run(
        ["cargo", "metadata", "--format-version", "1", "--locked", "--offline",
         "--manifest-path", str(crate / "Cargo.toml")],
        check=True, capture_output=True, text=True).stdout)
    own = {p["id"] for p in meta["packages"] if Path(p["manifest_path"]).parent == crate}
    texts, users, missing = {}, {}, []
    for package in sorted(meta["packages"], key=lambda p: (p["name"], p["version"])):
        if package["id"] in own:
            continue
        root = Path(package["manifest_path"]).parent
        files = sorted(f for f in root.iterdir() if f.is_file() and f.name.upper().startswith(PATTERNS))
        if not files:
            missing.append(f'{package["name"]} {package["version"]}')
            continue
        label = f'{package["name"]} {package["version"]} ({package.get("license") or "see text"})'
        for file in files:
            text = file.read_text(encoding="utf-8", errors="replace").strip()
            key = hashlib.sha256(text.encode()).hexdigest()
            texts[key] = text
            users.setdefault(key, []).append(label)
    if missing:
        raise SystemExit("no license file in: " + ", ".join(missing))
    out = [f"Third-party notices for the dependencies pinned by {crate.name}/Cargo.lock.",
           "Includes build dependencies; duplicate license texts are collected once.", ""]
    for key, text in texts.items():
        out += ["", "=" * 78, *sorted(set(users[key])), "", text, ""]
    (crate / "THIRD_PARTY_LICENSES.txt").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"{crate / 'THIRD_PARTY_LICENSES.txt'}: {len(texts)} texts for {sum(len(u) for u in users.values())} files")


if __name__ == "__main__":
    main()
