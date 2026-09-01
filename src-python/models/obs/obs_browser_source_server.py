import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from config import config


_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _clamp_int(value, min_value: int, max_value: int) -> int:
    try:
        number = int(value)
    except Exception:
        return min_value
    return max(min_value, min(max_value, number))


def _normalize_hex_color(value: str, fallback: str = "#FFFFFF") -> str:
    if not isinstance(value, str):
        return fallback
    value = value.strip()
    if _HEX_COLOR_RE.match(value):
        return value
    return fallback


def _build_overlay_html(ws_token: str = "") -> str:
    ws_port = _clamp_int(getattr(config, "WEBSOCKET_PORT", 2231), 1, 65535)
    # WebSocket サーバー側の token 検証 (websocket_server.py 参照) に
    # 必要な接続トークン。JS 文字列リテラルへそのまま埋め込むが、
    # secrets.token_urlsafe() の出力は URL-safe base64
    # ([A-Za-z0-9_-]) のみなので、クォートや HTML/JS を壊す文字は含まない。
    ws_token_js = ws_token if isinstance(ws_token, str) else ""

    max_messages = _clamp_int(
        getattr(config, "OBS_BROWSER_SOURCE_MAX_MESSAGES", 14), 1, 50
    )
    display_duration = _clamp_int(
        getattr(config, "OBS_BROWSER_SOURCE_DISPLAY_DURATION", 60), 1, 120
    )
    fadeout_duration = _clamp_int(
        getattr(config, "OBS_BROWSER_SOURCE_FADEOUT_DURATION", 12), 0, 120
    )

    font_size = _clamp_int(getattr(config, "OBS_BROWSER_SOURCE_FONT_SIZE", 40), 10, 200)
    font_color = _normalize_hex_color(
        getattr(config, "OBS_BROWSER_SOURCE_FONT_COLOR", "#FFFFFF")
    )
    outline_thickness = _clamp_int(
        getattr(config, "OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS", 3), 0, 20
    )
    outline_color = _normalize_hex_color(
        getattr(config, "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR", "#000000"),
        fallback="#000000",
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>VRCT OBS Browser Source</title>
    <style>
      :root {{
        --font-size: {font_size}px;
        --font-color: {font_color};
        --outline-size: {outline_thickness}px;
        --outline-color: {outline_color};
        --display-duration: {display_duration}s;
        --fadeout-duration: {fadeout_duration}s;
      }}

      html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
        background: transparent;
        overflow: hidden;
        color: var(--font-color);
        font-family:
          "Noto Sans CJK JP",
          "Noto Sans JP",
          "Noto Sans CJK",
          "Noto Sans",
          "Segoe UI",
          "Meiryo",
          system-ui,
          sans-serif;
        font-weight: 600;
        text-shadow: 0 2px 10px rgba(0,0,0,.85), 0 0 2px rgba(0,0,0,.95);
      }}

      #root {{
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        padding: 32px 48px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        pointer-events: none;
      }}

      .msg {{
        font-size: var(--font-size);
        line-height: 1.2;
        white-space: pre-wrap;
        opacity: 1;
        transform: translateY(0);
        animation: fadeout var(--fadeout-duration) ease var(--display-duration) forwards;
      }}

      .msg, .msg * {{
        -webkit-text-stroke-width: var(--outline-size);
        -webkit-text-stroke-color: var(--outline-color);
      }}

      .msg .translation {{
        font-weight: 700;
      }}

      .msg .original {{
        margin-top: 4px;
        font-size: calc(var(--font-size) * 0.75);
        opacity: 0.9;
      }}

      @keyframes fadeout {{
        to {{
          opacity: 0;
          transform: translateY(8px);
        }}
      }}
    </style>
  </head>
  <body>
    <div id="root"></div>

    <script>
      (() => {{
        const SETTINGS = {{
          wsPort: {ws_port},
          wsToken: "{ws_token_js}",
          maxMessages: {max_messages},
          displayDurationMs: {display_duration} * 1000,
          fadeoutDurationMs: {fadeout_duration} * 1000,
        }};

        const root = document.getElementById("root");
        let reconnectDelayMs = 500;
        let reconnectTimer = null;

        const asString = (v) => (typeof v === "string" ? v : "");
        const asStringArray = (v) =>
          Array.isArray(v) ? v.filter((x) => typeof x === "string" && x.length > 0) : [];

        const HEX_COLOR_RE = /^#[0-9a-fA-F]{{6}}$/;

        const applySettings = (settings) => {{
          if (!settings || typeof settings !== "object") return;
          const style = document.documentElement.style;

          if (Number.isFinite(settings.maxMessages) && settings.maxMessages > 0) {{
            SETTINGS.maxMessages = settings.maxMessages;
          }}
          if (Number.isFinite(settings.displayDuration) && settings.displayDuration >= 0) {{
            SETTINGS.displayDurationMs = settings.displayDuration * 1000;
            style.setProperty("--display-duration", `${{settings.displayDuration}}s`);
          }}
          if (Number.isFinite(settings.fadeoutDuration) && settings.fadeoutDuration >= 0) {{
            SETTINGS.fadeoutDurationMs = settings.fadeoutDuration * 1000;
            style.setProperty("--fadeout-duration", `${{settings.fadeoutDuration}}s`);
          }}
          if (Number.isFinite(settings.fontSize) && settings.fontSize > 0) {{
            style.setProperty("--font-size", `${{settings.fontSize}}px`);
          }}
          if (typeof settings.fontColor === "string" && HEX_COLOR_RE.test(settings.fontColor)) {{
            style.setProperty("--font-color", settings.fontColor);
          }}
          if (Number.isFinite(settings.outlineThickness) && settings.outlineThickness >= 0) {{
            style.setProperty("--outline-size", `${{settings.outlineThickness}}px`);
          }}
          if (typeof settings.outlineColor === "string" && HEX_COLOR_RE.test(settings.outlineColor)) {{
            style.setProperty("--outline-color", settings.outlineColor);
          }}
        }};

        const addMessage = (payload) => {{
          const type = asString(payload?.type) || "MESSAGE";
          const message = asString(payload?.message);
          const translations = asStringArray(payload?.translation);

          const translationText = translations.join("\\n");
          const primaryText = translationText || message;
          if (!primaryText) return;

          const msgEl = document.createElement("div");
          msgEl.className = `msg msg-${{type.toLowerCase()}}`;

          const translationEl = document.createElement("div");
          translationEl.className = "translation";
          translationEl.textContent = primaryText;
          msgEl.appendChild(translationEl);

          if (translationText && message && message !== translationText) {{
            const originalEl = document.createElement("div");
            originalEl.className = "original";
            originalEl.textContent = message;
            msgEl.appendChild(originalEl);
          }}

          root.appendChild(msgEl);

          while (root.childNodes.length > SETTINGS.maxMessages) {{
            root.removeChild(root.firstChild);
          }}

          window.setTimeout(() => {{
            msgEl.remove();
          }}, SETTINGS.displayDurationMs + SETTINGS.fadeoutDurationMs + 250);
        }};

        const scheduleReconnect = () => {{
          if (reconnectTimer) return;
          reconnectTimer = window.setTimeout(() => {{
            reconnectTimer = null;
            connect();
          }}, reconnectDelayMs);
          reconnectDelayMs = Math.min(reconnectDelayMs * 1.5, 8000);
        }};

        const connect = () => {{
          const wsUrl = SETTINGS.wsToken
            ? `ws://${{location.hostname}}:${{SETTINGS.wsPort}}/?token=${{encodeURIComponent(SETTINGS.wsToken)}}`
            : `ws://${{location.hostname}}:${{SETTINGS.wsPort}}`;
          let ws;
          try {{
            ws = new WebSocket(wsUrl);
          }} catch (e) {{
            scheduleReconnect();
            return;
          }}

          ws.addEventListener("open", () => {{
            reconnectDelayMs = 500;
          }});

          ws.addEventListener("message", (event) => {{
            try {{
              const payload = JSON.parse(event.data);
              if (asString(payload?.type) === "SETTINGS_UPDATED") {{
                applySettings(payload?.settings);
                return;
              }}
              addMessage(payload);
            }} catch (e) {{
              // ignore malformed messages
            }}
          }});

          ws.addEventListener("close", () => {{
            scheduleReconnect();
          }});

          ws.addEventListener("error", () => {{
            try {{ ws.close(); }} catch (e) {{}}
          }});
        }};

        connect();
      }})();
    </script>
  </body>
</html>
"""


class ObsBrowserSourceServer:
    def __init__(self, host: str, port: int, ws_token: str = "") -> None:
        self.host = host
        self.port = port
        # WebSocketServer 側で検証するトークン (websocket_server.py 参照)。
        # 生成されたページの JS が最初から知っている状態にすることで、
        # ユーザーが手動でコピー&ペーストする手間なく token 付き接続を
        # 実現する。
        self.ws_token = ws_token
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return

        ws_token = self.ws_token

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A002
                # Avoid polluting stderr/stdout in production.
                return

            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path in ("/", "/obs"):
                    body = _build_overlay_html(ws_token).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store, max-age=0")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                if parsed.path == "/health":
                    body = b"ok"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Cache-Control", "no-store, max-age=0")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                self.send_response(404)
                self.end_headers()

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="obs_browser_source_server",
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
            try:
                self._server.server_close()
            except Exception:
                pass

        if self._thread is not None:
            self._thread.join(timeout=2.0)

        self._server = None
        self._thread = None
