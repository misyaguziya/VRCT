"""Write THIRD_PARTY_LICENSES.txt for a native crate from its Cargo.lock.

    python tools/collect_rust_licenses.py native/vrct-graphics
    python tools/collect_rust_licenses.py native/vrct-backend   (a workspace member)

Uses `cargo metadata --locked --offline` (crates must already be fetched) and
copies each dependency's LICENSE*/COPYING*/NOTICE* files from the cargo
registry. Identical texts are written once, preceded by the crates using them.
Fails when a dependency ships no license file, so nothing is silently omitted.
Only what the crate builds with (normal and build dependencies, through the
workspace's own crates) is listed; the local crates themselves are VRCT's.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

PATTERNS = ("LICENSE", "LICENCE", "COPYING", "NOTICE")
# crates without a license file at their root (see the file)
SUPPLEMENTS = json.loads((Path(__file__).with_name("rust_license_supplements.json")).read_text(encoding="utf-8"))


def supplement(package, root):
    """(source, text) of the supplemented license files of a package, [] when none is listed."""
    entry = SUPPLEMENTS.get(f'{package["name"]} {package["version"]}', {})
    found = [(None, (root / f).read_text(encoding="utf-8", errors="replace")) for f in entry.get("files", [])]
    for url in entry.get("urls", []):
        with urllib.request.urlopen(url, timeout=60) as response:
            found.append((url, response.read().decode("utf-8", errors="replace")))
    return found


def main():
    crate = Path(sys.argv[1]).resolve()
    meta = json.loads(subprocess.run(
        ["cargo", "metadata", "--format-version", "1", "--locked", "--offline",
         "--manifest-path", str(crate / "Cargo.toml"), "--filter-platform", "x86_64-pc-windows-msvc"],
        check=True, capture_output=True, text=True, encoding="utf-8").stdout)
    root_id = next(p["id"] for p in meta["packages"] if Path(p["manifest_path"]).parent == crate)
    nodes = {n["id"]: n for n in meta["resolve"]["nodes"]}
    reachable, todo = set(), [root_id]
    while todo:
        node = nodes[todo.pop()]
        for dep in node["deps"]:
            kinds = {k["kind"] for k in dep["dep_kinds"]}
            if (None in kinds or "build" in kinds) and dep["pkg"] not in reachable:
                reachable.add(dep["pkg"])
                todo.append(dep["pkg"])
    texts, users, missing = {}, {}, []
    for package in sorted(meta["packages"], key=lambda p: (p["name"], p["version"])):
        # the local crates (path dependencies) are VRCT's own
        if package["id"] not in reachable or package["source"] is None:
            continue
        root = Path(package["manifest_path"]).parent
        files = sorted(f for f in root.iterdir() if f.is_file() and f.name.upper().startswith(PATTERNS))
        found = [(None, f.read_text(encoding="utf-8", errors="replace")) for f in files] or supplement(package, root)
        if not found:
            missing.append(f'{package["name"]} {package["version"]}')
            continue
        label = f'{package["name"]} {package["version"]} ({package.get("license") or "see text"})'
        for source, text in found:
            text = text.strip()
            if source:
                text = f"Source: {source}\n\n{text}"
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
