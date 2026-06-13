"""Per-app dictation profiles.

config["profiles"] is a list of dicts:
{"match": "slack", "cleanup_level": "light", "tone": "", "language": "",
 "auto_enter": false, "enabled": true}

`match` is a case-insensitive substring of the foreground process executable
name (for example "slack" matches slack.exe). The first enabled match wins.
"""

from __future__ import annotations

import copy
import ctypes
import sys
from typing import Any


def foreground_process_name() -> str:
    if sys.platform != "win32":
        return ""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        process_query_limited_information = 0x1000
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid.value)
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(len(buffer))
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return buffer.value.replace("\\", "/").rsplit("/", 1)[-1].lower()
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return ""
    return ""


def active_profile(config: dict[str, Any], process_name: str | None = None) -> dict[str, Any]:
    profiles = config.get("profiles", [])
    if not isinstance(profiles, list) or not profiles:
        return {}
    name = (process_name if process_name is not None else foreground_process_name()).lower()
    if not name:
        return {}
    for profile in profiles:
        if not isinstance(profile, dict) or not profile.get("enabled", True):
            continue
        match = str(profile.get("match", "")).strip().lower()
        if match and match in name:
            return profile
    return {}


def apply_profile(config: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Return a config copy with the profile's overrides applied."""
    if not profile:
        return config
    merged = copy.deepcopy(config)
    level = str(profile.get("cleanup_level", "")).strip().lower()
    if level in {"none", "light", "medium", "high"}:
        merged.setdefault("cleanup", {})["level"] = level
    language = str(profile.get("language", "")).strip()
    if language:
        merged.setdefault("deepgram", {})["language"] = language
    if "auto_enter" in profile:
        merged.setdefault("dictation", {})["press_enter_command"] = bool(profile.get("auto_enter"))
    return merged
