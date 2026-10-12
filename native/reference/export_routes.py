"""mainloop.py の振り分けの表 (mapping: エンドポイント・初期化中に答えるか・Controller のメソッド) と run_mapping (push の名前)、
controller.py の _SIMPLE_CONFIG_GETTERS を、構文木から読んで書き出す (import しないので Controller は作られない)。

    python native/reference/export_routes.py   ->  native/testdata/ipc/routes.json

Rust 版の表 (vrct-backend/src/endpoints) をこれと突き合わせる (tests/routes.rs)。
"""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def assigned_dict(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
    raise KeyError(name)


def main():
    mainloop = ast.parse((ROOT / "src-python" / "mainloop.py").read_text(encoding="utf-8"))
    routes = []
    mapping = assigned_dict(mainloop, "mapping")
    for key, value in zip(mapping.keys, mapping.values):
        entry = dict(zip((k.value for k in value.keys), value.values))
        routes.append({"endpoint": key.value, "during_init": entry["status"].value, "handler": entry["variable"].attr})
    run_mapping = assigned_dict(mainloop, "run_mapping")
    pushes = {k.value: v.value for k, v in zip(run_mapping.keys, run_mapping.values)}
    controller = ast.parse((ROOT / "src-python" / "controller.py").read_text(encoding="utf-8"))
    getters = assigned_dict(controller, "_SIMPLE_CONFIG_GETTERS")
    simple = {k.value: v.value for k, v in zip(getters.keys, getters.values)}
    out = ROOT / "native" / "testdata" / "ipc" / "routes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"routes": routes, "run_mapping": pushes, "simple_getters": simple}, indent=1) + "\n",
                   encoding="utf-8")
    print(out, len(routes), len(pushes), len(simple))


if __name__ == "__main__":
    main()
