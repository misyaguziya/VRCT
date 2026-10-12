"""config.py の検証 (ManagedProperty の型・allowed、ValidatedProperty の validator) に色々な値を通した結果を記録する。

    python native/reference/export_config_checks.py   ->  native/testdata/config/checks.json

既定値の Config (config.json は読まない) に、項目ごとに値を順に代入し、拒否されたか・保存された値を残す。
検証は今の値に依存する (旧値へのフォールバック) ので、Rust 版も同じ順に代入して比べる (vrct-backend/tests/config.rs)。
保存 (saveConfig) は止める。録音デバイスの項目は PC で変わるので含めない。
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src-python"))

SKIP = {"SELECTED_MIC_HOST", "SELECTED_MIC_DEVICE", "SELECTED_SPEAKER_DEVICE"}
SCALARS = [None, True, False, 0, 1, 80, -1, 99, 100, 5000, 5001, 0.5, 2.5, 0.85, 1.0, "", "ja", "en", "x", "show",
           "stable", "beta", "auto", "Arabic", "VRChat", "127.0.0.1", "0.0.0.0", "::1", "::", "192.168.0.10", "1", "4",
           "Google", "Whisper", "CTranslate2", "base", "nllb-200-distilled-600M-ct2-int8", "float32", "int8", [], ["a"],
           ["a", 1, "a", "b"], {}, {"a": 1}]


def variants(default):
    """dict の既定値から、一部だけ壊したもの・キーを足したもの・減らしたもの。"""
    out = [copy.deepcopy(default)]
    if isinstance(default, dict) and default:
        keys = list(default)
        for bad in (None, "x", 1, 2.5, True, [], {}):
            v = copy.deepcopy(default)
            v[keys[0]] = bad
            out.append(v)
            v = copy.deepcopy(default)
            v[keys[-1]] = bad
            out.append(v)
        extra = copy.deepcopy(default)
        extra["unknown_key"] = 1
        out.append(extra)
        out.append({k: v for k, v in default.items() if k != keys[0]})
        for k, v in default.items():
            if isinstance(v, dict):
                nested = copy.deepcopy(default)
                nested[k] = {**v, "language": "Klingon"} if "language" in v else {}
                out.append(nested)
                nested = copy.deepcopy(default)
                nested[k] = "not a dict"
                out.append(nested)
    return out


def main():
    import config as c

    cfg = object.__new__(c.Config)
    cfg.init_config()
    cfg.saveConfig = lambda *args, **kwargs: None
    env = {"SELECTABLE_COMPUTE_DEVICE_LIST": cfg.SELECTABLE_COMPUTE_DEVICE_LIST}
    language_sets = [
        {"1": {"1": {"language": "English", "country": "United States", "enable": False}}},
        {"1": {"1": {"language": "Japanese", "country": "Japan", "enable": "yes"}}, "2": {"1": {"language": "French", "country": "France", "enable": True}}},
    ]
    cases = []
    for name, obj in c.Config.__dict__.items():
        if not isinstance(obj, (c.ManagedProperty, c.ValidatedProperty)) or name in SKIP:
            continue
        if getattr(obj, "readonly", False):
            continue
        # plain JSON (the mutable-tracked properties hand out wrappers that do not copy)
        default = json.loads(json.dumps(getattr(cfg, name), default=list))
        values = SCALARS + variants(default)
        if name in ("SELECTED_YOUR_LANGUAGES", "SELECTED_TARGET_LANGUAGES"):
            values += language_sets
        if name in ("SELECTED_TRANSLATION_COMPUTE_DEVICE", "SELECTED_TRANSCRIPTION_COMPUTE_DEVICE"):
            values += copy.deepcopy(cfg.SELECTABLE_COMPUTE_DEVICE_LIST)
        if name == "SELECTED_TRANSLATION_ENGINES":
            values += [{"1": "DeepL", "2": "nope", "4": "Google"}]
        for value in values:
            try:
                setattr(cfg, name, value)
                result = {"stored": json.loads(json.dumps(getattr(cfg, name), default=list))}
            except c.ConfigValidationError:
                result = {"rejected": True}
            cases.append({"name": name, "value": value, **result})
    out = ROOT / "native" / "testdata" / "config" / "checks.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"env": env, "cases": cases}, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out, len(cases))


if __name__ == "__main__":
    main()
