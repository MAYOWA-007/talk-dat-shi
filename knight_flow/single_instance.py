from __future__ import annotations

import ctypes
import sys
from typing import Any


_mutex_handle: Any = None


def already_running() -> bool:
    global _mutex_handle
    if sys.platform != "win32":
        return False
    kernel32 = ctypes.windll.kernel32
    _mutex_handle = kernel32.CreateMutexW(None, False, "Local\\TalkDatSingleInstance")
    return kernel32.GetLastError() == 183


def show_already_running_message() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.MessageBoxW(
            None,
            "Talk Dat! is already running. Check the bottom overlay or the system tray icon.",
            "Talk Dat!",
            0x40,
        )
    except Exception:
        pass
