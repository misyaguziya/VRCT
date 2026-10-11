"""DeepL が送る HTTP 要求を、今の Python 版のコード (Translator) で記録する。

    python native/reference/export_deepl.py   ->  native/testdata/deepl/deepl.json

Translator.authenticationDeepLAuthKey と Translator.translate("DeepL_API", ...) を呼ぶ。無料キー (":fx")
と有料キー、言語の変種 (English / Portuguese の国による振り分け)、403 (認証失敗)、456 (上限)、
429 の後の再試行、表に無い言語 (None) を含む。応答は responder が返す決まった値。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC / "models" / "translation"))
sys.path.insert(0, str(Path(__file__).parent))

from http_capture import capture  # noqa: E402

state = {"busy": 0}


def responder(entry):
    auth = entry["headers"].get("authorization", "")
    body = (entry["body"] or {}).get("json") or {}
    if "bad" in auth:
        return 403, {}, {"message": "Wrong endpoint"}
    if "quota" in auth:
        return 456, {}, {"message": "Quota exceeded"}
    if "busy" in auth and state["busy"] < 1:
        state["busy"] += 1
        return 429, {}, {"message": "Too many requests"}
    texts = body.get("text", [])
    return 200, {}, {"translations": [{"detected_source_language": "JA", "text": f"[{body.get('target_lang')}] {t}", "billed_characters": len(t)}
                                      for t in texts]}


def main():
    from translation_languages import loadTranslationLanguages
    import translation_translator as tt
    loadTranslationLanguages(str(SRC))
    tt.ENABLE_TRANSLATORS = True
    steps = []

    def step(label, call):
        with capture(responder) as records:
            try:
                result = call()
            except Exception as e:
                result = {"error": type(e).__name__}
        steps.append({"step": label, "result": result, "requests": records})
        print(label, repr(result)[:60], len(records))

    t = tt.Translator()
    t.is_enable_translators = True
    step("auth_bad", lambda: t.authenticationDeepLAuthKey("bad-key:fx"))
    step("auth_free", lambda: t.authenticationDeepLAuthKey("free-key:fx"))
    for source, target, country in [("Japanese", "English", "United States"), ("Japanese", "English", "Japan"),
                                    ("English", "Portuguese", "Portugal"), ("English", "Portuguese", "Brazil"),
                                    ("English", "Chinese Simplified", "China"), ("English", "Japanese", "Japan"),
                                    ("Japanese", "Klingon", "Japan"), ("English", "English", "Japan")]:
        step(f"translate {source}->{target} ({country})",
             lambda: t.translate("DeepL_API", None, source, target, country, "こんにちは、\n世界！ & <tag>"))
    step("auth_pro", lambda: t.authenticationDeepLAuthKey("pro-key"))
    step("translate_pro", lambda: t.translate("DeepL_API", None, "Japanese", "English", "Japan", "テスト"))
    step("auth_quota", lambda: t.authenticationDeepLAuthKey("quota-key"))
    step("translate_no_client", lambda: t.translate("DeepL_API", None, "Japanese", "English", "Japan", "テスト"))
    step("auth_busy", lambda: t.authenticationDeepLAuthKey("busy-key"))
    out = ROOT / "native" / "testdata" / "deepl" / "deepl.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"steps": steps}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
