"""errors.py の ErrorCode と ERROR_METADATA を、Rust のバックエンドが読む JSON に書き出す。

    python native/reference/export_error_codes.py   ->  native/data/error_codes.json

Rust 版は手で写さず、この JSON を取り込む (docs/rust_backend_design_2026-10-11.md §4.3)。
errors.py を変えたら再実行し、差分をコミットする。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src-python"))

from errors import ERROR_METADATA, ErrorCode  # noqa: E402

fallback = ERROR_METADATA[ErrorCode.GENERAL_UNKNOWN]
codes = []
for code in ErrorCode:
    meta = ERROR_METADATA.get(code)
    codes.append({
        "code": code.value,
        # create_error_response は表に無いコードに GENERAL_UNKNOWN の情報を使う
        "has_metadata": meta is not None,
        "category": (meta or fallback)["category"].value,
        "message": (meta or fallback)["message"],
        "severity": (meta or fallback)["severity"],
        "user_action_required": (meta or fallback).get("user_action_required", False),
    })
out = ROOT / "native" / "data" / "error_codes.json"
out.write_text(json.dumps({"codes": codes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"{len(codes)} codes -> {out}")
