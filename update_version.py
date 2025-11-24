import json
from pathlib import Path

def update_versions():
    root = Path(__file__).parent

    # package.jsonからバージョンを読み取る
    with open(root / "package.json", "r", encoding="utf-8") as f:
        package_json = json.load(f)
        version = package_json["version"]

    # tauri.conf.jsonを更新
    tauri_conf_path = root / "src-tauri" / "tauri.conf.json"
    with open(tauri_conf_path, "r", encoding="utf-8") as f:
        tauri_conf = json.load(f)

    tauri_conf["version"] = version

    with open(tauri_conf_path, "w", encoding="utf-8") as f:
        json.dump(tauri_conf, f, indent=4, ensure_ascii=False)

    # config.pyを更新
    config_path = root / "src-python" / "config.py"
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # VERSION行を置換
    import re
    pattern = r'(self\._VERSION = ")[^"]+(")'
    replacement = rf'\g<1>{version}\g<2>'
    new_content = re.sub(pattern, replacement, content)

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✓ バージョン {version} に更新しました")

if __name__ == "__main__":
    update_versions()