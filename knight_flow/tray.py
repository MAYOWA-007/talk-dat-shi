from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from .icon import make_tray_image


Callback = Callable[[], None]


class TrayController:
    def __init__(self, callbacks: dict[str, Callback]) -> None:
        self.callbacks = callbacks
        self.icon: Any = None
        self.thread: threading.Thread | None = None
        self.paused = False
        self.update_available = ""

    def _pause_label(self, _item: Any = None) -> str:
        return "Resume dictation" if self.paused else "Pause dictation"

    def _update_label(self, _item: Any = None) -> str:
        return f"Install update {self.update_available}" if self.update_available else "Check for updates"

    def set_paused(self, paused: bool) -> None:
        self.paused = bool(paused)
        self._refresh_menu()

    def set_update_available(self, version: str) -> None:
        self.update_available = str(version or "")
        self._refresh_menu()

    def _refresh_menu(self) -> None:
        try:
            if self.icon is not None:
                self.icon.update_menu()
        except Exception:
            pass

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, name="TalkDatTray", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        try:
            if self.icon:
                self.icon.stop()
        except Exception:
            pass

    def _run(self) -> None:
        try:
            import pystray

            menu = pystray.Menu(
                pystray.MenuItem("Show overlay", lambda _icon, _item: self._call("show")),
                pystray.MenuItem("Hide overlay", lambda _icon, _item: self._call("hide")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Hands-free toggle", lambda _icon, _item: self._call("hands_free")),
                pystray.MenuItem(self._pause_label, lambda _icon, _item: self._call("pause")),
                pystray.MenuItem("Cancel current", lambda _icon, _item: self._call("cancel")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Settings", lambda _icon, _item: self._call("settings")),
                pystray.MenuItem("Status", lambda _icon, _item: self._call("status")),
                pystray.MenuItem("Stats", lambda _icon, _item: self._call("stats")),
                pystray.MenuItem("History", lambda _icon, _item: self._call("history")),
                pystray.MenuItem("Local models", lambda _icon, _item: self._call("local_models")),
                pystray.MenuItem("Scratchpad", lambda _icon, _item: self._call("scratchpad")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(self._update_label, lambda _icon, _item: self._call("install_update")),
                pystray.MenuItem("Restart Talk Dat!", lambda _icon, _item: self._call("restart")),
                pystray.MenuItem("Panic stop", lambda _icon, _item: self._call("panic")),
                pystray.MenuItem("Quit", lambda _icon, _item: self._call("quit")),
            )
            self.icon = pystray.Icon("Talk Dat!", make_tray_image(), "Talk Dat!", menu)
            self.icon.run()
        except Exception:
            return

    def _call(self, name: str) -> None:
        callback = self.callbacks.get(name)
        if callback:
            callback()
