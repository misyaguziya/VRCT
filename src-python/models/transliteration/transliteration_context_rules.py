from typing import List, Dict, Any
import re

"""Contextual transliteration rules for tokenized results.

This module provides a compact rule engine that can modify token
readings (kana) based on neighboring tokens. Rules are embedded in
``DEFAULT_RULES`` to simplify packaging (no external JSON required).

Key points
- Rules are applied in descending ``priority`` order.
- Supported match modes: ``equals`` (exact match) and ``regex``.
- ``direction`` chooses whether to inspect the next or previous token.
- When a rule sets ``kana``, the engine overwrites ``kana`` and clears
  ``hira``/``hepburn``; callers should recompute them after rules run.

The engine mutates the provided ``results`` list in-place and also
returns it for convenience.
"""
DEFAULT_RULES = {
    "rules": [
        {
            "name": "nan_next_tdna",
            "target": "何",
            "match_mode": "equals",
            "direction": "next",
            "kana_set": list("タチツテトダヂヅデドナニヌネノ"),
            "on_true": {"kana": "ナン"},
            "on_false": {"kana": "ナニ"}
        }
    ]
}



def apply_context_rules(results: List[Dict[str, Any]], use_macron: bool = False) -> List[Dict[str, Any]]:
    """Apply contextual rewrite rules to `results`.

    Parameters
    - results: list of token dicts produced by Transliterator.split_kanji_okurigana
        where each entry contains at least the keys: 'orig', 'kana', 'hira', 'hepburn'.
    - use_macron: passed through for compatibility; rules themselves don't use it

    Returns
    - The (possibly modified) `results` list. The list is also modified in-place.

    The engine supports 'equals' and 'regex' match modes, next/prev neighbor
    inspection, and simple actions that overwrite `kana` (caller must recalc
    `hira`/`hepburn` afterwards).
    """

    # prepare rules: sort by priority (desc) and precompile regex where provided
    raw_rules: List[Dict[str, Any]] = DEFAULT_RULES.get("rules", [])
    rules = sorted(raw_rules, key=lambda r: r.get("priority", 0), reverse=True)
    for r in rules:
        if r.get("match_mode") == "regex" and r.get("pattern"):
            try:
                r["_re"] = re.compile(r["pattern"])
            except Exception:
                r["_re"] = None

    i = 0
    n = len(results)
    while i < n:
        entry = results[i]
        orig = entry.get("orig", "")
        # skip tokens with empty orig (symbols, whitespace, etc.)
        if not orig:
            i += 1
            continue

        for rule in rules:
            target = rule.get("target")
            mode = rule.get("match_mode", "equals")
            direction = rule.get("direction", "next")
            kana_set = set(rule.get("kana_set", []))
            on_true = rule.get("on_true", {})
            on_false = rule.get("on_false", {})

            matched = False
            if mode == "equals" and orig == target:
                matched = True
            elif mode == "regex":
                cre = rule.get("_re")
                if cre and cre.search(orig):
                    matched = True
            # regex or other modes can be added later

            if not matched:
                continue

            # decide neighbor token based on direction
            neighbor_entry = None
            if direction == "next":
                j = i + 1
                while j < n:
                    if results[j].get("orig"):
                        neighbor_entry = results[j]
                        break
                    j += 1
            elif direction == "prev":
                j = i - 1
                while j >= 0:
                    if results[j].get("orig"):
                        neighbor_entry = results[j]
                        break
                    j -= 1

            condition = False
            if neighbor_entry:
                nk = neighbor_entry.get("kana", "")
                if nk:
                    first = nk[0]
                    if first in kana_set:
                        condition = True
                else:
                    # fallback to orig-first-char check
                    fo = neighbor_entry.get("orig", "")[:1]
                    if fo and 'ァ' <= fo <= 'ン' and fo in kana_set:
                        condition = True

            # Apply action: simple overwrite of kana/hira/hepburn for the matched token
            action = on_true if condition else on_false
            if "kana" in action:
                entry["kana"] = action["kana"]
                entry["hira"] = ""
                entry["hepburn"] = ""
                # once a rule applied, do not apply further rules to this token
                break

        i += 1

    # return the (possibly modified) results for convenience/pure-function style usage
    return results
