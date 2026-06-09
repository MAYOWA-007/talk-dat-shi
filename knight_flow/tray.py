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

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, name="TalkDatShiTray", daemon=True)
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
                pystray.MenuItem("Cancel current", lambda _icon, _item: self._call("cancel")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Settings", lambda _icon, _item: self._call("settings")),
                pystray.MenuItem("Status", lambda _icon, _item: self._call("status")),
                pystray.MenuItem("History", lambda _icon, _item: self._call("history")),
                pystray.MenuItem("Scratchpad", lambda _icon, _item: self._call("scratchpad")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Panic stop", lambda _icon, _item: self._call("panic")),
                pystray.MenuItem("Quit", lambda _icon, _item: self._call("quit")),
            )
            self.icon = pystray.Icon("Talk Dat Shi", make_tray_image(), "Talk Dat Shi", menu)
            self.icon.run()
        except Exception:
            return

    def _call(self, name: str) -> None:
        callback = self.callbacks.get(name)
        if callback:
            callback()
