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


def _build_overlay_html() -> str:
    ws_port = _clamp_int(getattr(config, "WEBSOCKET_PORT", 2231), 1, 65535)

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
          const wsUrl = `ws://${{location.hostname}}:${{SETTINGS.wsPort}}`;
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
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A002
                # Avoid polluting stderr/stdout in production.
                return

            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path in ("/", "/obs"):
                    body = _build_overlay_html().encode("utf-8")
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
