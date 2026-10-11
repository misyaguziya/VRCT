"""OBS ブラウザソースのページ (obs_browser_source_server._build_overlay_html) を、今の Python 版のコードで記録する。

    python native/reference/export_obs.py
        ->  native/vrct-backend/src/obs_overlay.html   (値の所を @@name@@ にしたテンプレート)
            native/testdata/obs/obs.json                (設定ごとのページと、各パスへの応答)
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))

KEYS = ["WEBSOCKET_PORT", "OBS_BROWSER_SOURCE_MAX_MESSAGES", "OBS_BROWSER_SOURCE_DISPLAY_DURATION",
        "OBS_BROWSER_SOURCE_FADEOUT_DURATION", "OBS_BROWSER_SOURCE_FONT_SIZE", "OBS_BROWSER_SOURCE_FONT_COLOR",
        "OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS", "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR"]

CASES = [
    {},
    {"WEBSOCKET_PORT": 2231, "OBS_BROWSER_SOURCE_MAX_MESSAGES": 14, "OBS_BROWSER_SOURCE_DISPLAY_DURATION": 60,
     "OBS_BROWSER_SOURCE_FADEOUT_DURATION": 12, "OBS_BROWSER_SOURCE_FONT_SIZE": 40,
     "OBS_BROWSER_SOURCE_FONT_COLOR": "#FFFFFF", "OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS": 3,
     "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR": "#000000"},
    {"WEBSOCKET_PORT": 70000, "OBS_BROWSER_SOURCE_MAX_MESSAGES": 0, "OBS_BROWSER_SOURCE_DISPLAY_DURATION": 500,
     "OBS_BROWSER_SOURCE_FADEOUT_DURATION": -3, "OBS_BROWSER_SOURCE_FONT_SIZE": 5,
     "OBS_BROWSER_SOURCE_FONT_COLOR": " #a1B2c3 ", "OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS": 99,
     "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR": "red"},
    {"WEBSOCKET_PORT": "8080", "OBS_BROWSER_SOURCE_MAX_MESSAGES": 7.9, "OBS_BROWSER_SOURCE_DISPLAY_DURATION": True,
     "OBS_BROWSER_SOURCE_FADEOUT_DURATION": "x", "OBS_BROWSER_SOURCE_FONT_SIZE": None,
     "OBS_BROWSER_SOURCE_FONT_COLOR": 123, "OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS": " 4 ",
     "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR": "#12345"},
    {"OBS_BROWSER_SOURCE_FONT_COLOR": "#ABCDEF\n", "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR": "#abcdefg"},
]
TOKENS = ["", "AbC-_123xyz"]


def main():
    import models.obs.obs_browser_source_server as obs
    from config import config

    def set_config(case):
        for k in KEYS:
            if k in case:
                setattr(type(config), k, property(lambda self, v=case[k]: v))
            else:  # getattr(config, k, default) takes the default
                setattr(type(config), k, property(lambda self, v=None: (_ for _ in ()).throw(AttributeError())))

    # the template: every value replaced by a marker
    markers = {k: f"@@{k}@@" for k in KEYS}
    clamp, color = obs._clamp_int, obs._normalize_hex_color
    obs._clamp_int = lambda v, lo, hi: v
    obs._normalize_hex_color = lambda v, fallback="#FFFFFF": v
    set_config(markers)
    template = obs._build_overlay_html("@@ws_token@@")
    obs._clamp_int, obs._normalize_hex_color = clamp, color
    out_template = ROOT / "native" / "vrct-backend" / "src" / "obs_overlay.html"
    out_template.write_bytes(template.encode("utf-8"))

    pages = []
    for case in CASES:
        set_config(case)
        for token in TOKENS:
            pages.append({"config": case, "ws_token": token, "html": obs._build_overlay_html(token)})

    set_config(CASES[1])
    server = obs.ObsBrowserSourceServer("127.0.0.1", 0, ws_token="tok")
    # port 0: ThreadingHTTPServer binds any free port
    server.start()
    port = server._server.server_address[1]
    responses = []
    for method, path in [("GET", "/"), ("GET", "/obs"), ("GET", "/obs?x=1"), ("GET", "/health"),
                         ("GET", "/health/"), ("GET", "/x"), ("GET", "/OBS"), ("POST", "/"), ("HEAD", "/")]:
        request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method,
                                         data=b"" if method == "POST" else None)
        try:
            with urllib.request.urlopen(request, timeout=5) as r:
                status, headers, body = r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            status, headers, body = e.code, dict(e.headers), e.read()
        responses.append({"method": method, "path": path, "status": status,
                          "content_type": headers.get("Content-Type"), "cache_control": headers.get("Cache-Control"),
                          "body": body.decode("utf-8", "replace") if status == 200 and method != "HEAD" else None})
    server.stop()
    out = ROOT / "native" / "testdata" / "obs" / "obs.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"pages": pages, "responses": responses}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out_template, out, len(pages), [(r["path"], r["status"]) for r in responses])


if __name__ == "__main__":
    main()
