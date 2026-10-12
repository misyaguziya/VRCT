"""config.py の設定項目 (ManagedProperty / ValidatedProperty) の並び・種類・型・保存の仕方と既定値を書き出す。

    python native/reference/export_config_schema.py   ->  native/data/config_schema.json

Rust 版 (vrct-backend/src/config.rs) はこれを取り込み、検証の関数だけを Rust で持つ (error_codes.json と同じ)。
既定値は init_config() の値。PC で変わるもの (デバイス・計算デバイス・トークン・言語の一覧) は "env" に名前だけ残す。
config.json は読まない (load_config を呼ばない)。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src-python"))

# PC (接続中のデバイス、GPU) や起動ごと (乱数) で変わる既定値
ENVIRONMENT = {
    "PATH_LOCAL", "PATH_CONFIG", "PATH_LOGS", "SELECTABLE_COMPUTE_DEVICE_LIST", "COMPUTE_MODE",
    "SELECTED_TRANSLATION_COMPUTE_DEVICE", "SELECTED_TRANSCRIPTION_COMPUTE_DEVICE", "SELECTED_MIC_HOST",
    "SELECTED_MIC_DEVICE", "SELECTED_SPEAKER_DEVICE", "WEBSOCKET_AUTH_TOKEN",
}


def type_names(type_):
    if type_ is None:
        return None
    types = type_ if isinstance(type_, tuple) else (type_,)
    return [t.__name__ for t in types]


def main():
    import config as c

    defaults = object.__new__(c.Config)
    defaults.init_config()
    props = []
    for name, obj in c.Config.__dict__.items():
        if isinstance(obj, c.ManagedProperty):
            entry = {"name": name, "kind": "managed", "type": type_names(obj.type_),
                     "allowed": None if obj.allowed is None else ("callable" if callable(obj.allowed) else list(obj.allowed)),
                     "readonly": obj.readonly, "serialize": obj.serialize, "immediate_save": obj.immediate_save,
                     "mutable_tracking": obj.mutable_tracking}
        elif isinstance(obj, c.ValidatedProperty):
            entry = {"name": name, "kind": "validated", "validator": getattr(obj.validator, "__name__", "<lambda>"),
                     "serialize": obj.serialize, "immediate_save": obj.immediate_save}
        else:
            continue
        value = getattr(defaults, "_" + name)
        if name in ENVIRONMENT:
            entry["env"] = True
        else:
            entry["default"] = list(value) if not isinstance(value, (dict, list, str, int, float, bool, type(None))) else value
        props.append(entry)
    out = ROOT / "native" / "data" / "config_schema.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"properties": props, "serialized_order": list(c.json_serializable_vars)},
                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out, len(props))


if __name__ == "__main__":
    main()
