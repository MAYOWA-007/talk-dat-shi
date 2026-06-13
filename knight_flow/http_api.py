"""Opt-in local control API for automation (Stream Deck, AutoHotkey, Raycast-style launchers).

Binds to 127.0.0.1 only. Enable via config remote.enabled; if remote.token is
set, requests must send it as a Bearer token or ?token= query value.

Endpoints: GET /status, POST (or GET) /toggle /cancel /paste-last /copy-last.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


class ControlServer:
    def __init__(self, config: dict[str, Any], callbacks: dict[str, Any]) -> None:
        self.config = config
        self.callbacks = callbacks
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._server is not None

    def start(self) -> None:
        remote = self.config.get("remote", {})
        if not remote.get("enabled", False) or self.running:
            return
        port = int(remote.get("port", 4670))
        token = str(remote.get("token", "")).strip()
        callbacks = self.callbacks

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                pass

            def _authorized(self, query: dict[str, list[str]]) -> bool:
                if not token:
                    return True
                header = self.headers.get("Authorization", "")
                if header == f"Bearer {token}":
                    return True
                return query.get("token", [""])[0] == token

            def _respond(self, code: int, body: dict[str, Any]) -> None:
                payload = json.dumps(body).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _handle(self) -> None:
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                if not self._authorized(query):
                    self._respond(401, {"error": "unauthorized"})
                    return
                route = parsed.path.rstrip("/") or "/status"
                actions = {
                    "/toggle": "hands_free",
                    "/cancel": "panic",
                    "/paste-last": "paste_last",
                    "/copy-last": "copy_last",
                }
                if route == "/status":
                    snapshot = callbacks.get("status_provider")
                    self._respond(200, snapshot() if callable(snapshot) else {"app": "running"})
                    return
                if route == "/last-text":
                    provider = callbacks.get("last_text")
                    self._respond(200, {"text": provider() if callable(provider) else ""})
                    return
                action = actions.get(route)
                if action and callable(callbacks.get(action)):
                    callbacks[action]()
                    self._respond(200, {"ok": True, "action": action})
                    return
                self._respond(404, {"error": f"unknown route {route}"})

            def do_GET(self) -> None:  # noqa: N802
                self._handle()

            def do_POST(self) -> None:  # noqa: N802
                self._handle()

        try:
            self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        except OSError:
            self._server = None
            return
        self._thread = threading.Thread(target=self._server.serve_forever, name="TalkDatControlAPI", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
            self._server = None
