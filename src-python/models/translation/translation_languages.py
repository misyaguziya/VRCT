"""Load translation language code mappings from YAML.

YAML ファイル: languages/languages.yml
構造:
  <BackendName>:
    source: { DisplayName: Code, ... }
    target: { DisplayName: Code, ... }
  CTranslate2:
    <ModelName>:
      source: {...}
      target: {...}
"""

import os
import threading
from typing import Any, Dict
import yaml
try:
    from utils import printLog, errorLogging
except ImportError:
    def printLog(data, *args, **kwargs):
        print(data, *args, **kwargs)

    def errorLogging():
        import traceback
        traceback.print_exc()


# 型: translation_lang[backend][(model)?]['source'|'target'][display_name] = code
translation_lang: Dict[str, Dict[str, Dict[str, str]]] = {}
_loaded = False
_lock = threading.Lock()


def _load_languages(path: str, filename: str) -> str:
    """Get absolute path to resource file relative to this module.

    Args:
        filename: relative filename from this module's directory

    Returns:
        Absolute path to the resource file
    """
    if os.path.exists(os.path.join(path, "_internal", "languages", "languages.yml")):
        languages_path =  os.path.join(path, "_internal", "languages", "languages.yml")
    elif os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "translation", "languages", "languages.yml")):
        languages_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "translation", "languages", "languages.yml")
    elif os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages", "languages.yml")):
        languages_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages", "languages.yml")
    else:
        raise FileNotFoundError(f"Prompt file not found: {filename}")
    with open(languages_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _validate_source_target(backend: str, mapping: Any) -> None:
    """Validate that a backend mapping has proper source/target structure.

    Args:
        backend: backend name for error messages
        mapping: mapping to validate

    Raises:
        ValueError: If mapping structure is invalid
    """
    if not isinstance(mapping, dict):
        raise ValueError(f"{backend}: 値は dict である必要があります。")
    if "source" not in mapping or "target" not in mapping:
        raise ValueError(f"{backend}: 'source' と 'target' が必要です。")

    for key in ("source", "target"):
        if not isinstance(mapping[key], dict):
            raise ValueError(f"{backend}: '{key}' は dict である必要があります。")
        # value は str を想定
        for disp, code in mapping[key].items():
            if not isinstance(disp, str) or not isinstance(code, str):
                raise ValueError(
                    f"{backend}: '{key}' のエントリは str: str である必要があります。 ({disp} => {code})"
                )

def loadTranslationLanguages(path: str, force: bool = False) -> Dict[str, Any]:
    """Load translation language mappings from YAML file.

    Args:
        path: Path to the YAML file
        force: If True, reload even if already loaded

    Returns:
        Dictionary of translation language mappings

    Raises:
        FileNotFoundError: If languages/languages.yml is not found
        ValueError: If YAML structure is invalid
    """
    global _loaded, translation_lang
    if _loaded and not force:
        return translation_lang

    with _lock:
        if _loaded and not force:
            return translation_lang

        data = _load_languages(path, "languages/languages.yml")

        if not isinstance(data, dict):
            raise ValueError(
                "languages/languages.yml のルートはマッピング(dict)である必要があります。"
            )

        # 検証と正規化
        validated: Dict[str, Dict[str, Dict[str, str]]] = {}
        for backend, value in data.items():
            if backend == "CTranslate2":
                # NOTE: CTranslate2 はモデルごとに異なる言語セットを持つ
                if not isinstance(value, dict):
                    raise ValueError(
                        "CTranslate2 の値はモデル名→ {source:, target:} の dict である必要があります。"
                    )
                validated["CTranslate2"] = {}
                for model_name, model_map in value.items():
                    _validate_source_target(
                        backend=f"CTranslate2/{model_name}", mapping=model_map
                    )
                    validated["CTranslate2"][model_name] = {
                        "source": model_map["source"],
                        "target": model_map["target"],
                    }
            else:
                _validate_source_target(backend=backend, mapping=value)
                validated[backend] = {
                    "source": value["source"],
                    "target": value["target"],
                }

        translation_lang = validated
        _loaded = True
        return translation_lang

if __name__ == "__main__":
    try:
        langs = loadTranslationLanguages(path=".", force=True)
        printLog("Loaded translation languages:")
        printLog(langs)
    except Exception:
        errorLogging()