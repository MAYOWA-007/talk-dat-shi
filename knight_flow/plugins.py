"""User plugin loader.

Plugins are Python files in %APPDATA%/TalkDat/plugins. Each may define:

    def register(api):
        api.add_transform("shout", lambda text, config: text.upper())
        api.add_text_filter(lambda text, config: text.replace("teh", "the"))

Loading is opt-in (config plugins.enabled, default off) because plugins are
arbitrary local code. Failures in one plugin never break dictation.
"""

from __future__ import annotations

import importlib.util
import threading
from collections.abc import Callable
from typing import Any

from .config import app_dir


TransformFn = Callable[[str, dict[str, Any]], str]
FilterFn = Callable[[str, dict[str, Any]], str]


class PluginAPI:
    def __init__(self) -> None:
        self.transforms: dict[str, TransformFn] = {}
        self.text_filters: list[FilterFn] = []

    def add_transform(self, transform_id: str, fn: TransformFn) -> None:
        clean = str(transform_id).strip().lower()
        if clean and callable(fn):
            self.transforms[clean] = fn

    def add_text_filter(self, fn: FilterFn) -> None:
        if callable(fn):
            self.text_filters.append(fn)


_lock = threading.Lock()
_api: PluginAPI | None = None
_load_errors: list[str] = []


def plugins_dir():
    path = app_dir() / "plugins"
    path.mkdir(parents=True, exist_ok=True)
    return path


def plugins_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("plugins", {}).get("enabled", False))


def load_errors() -> list[str]:
    return list(_load_errors)


def _load_all() -> PluginAPI:
    global _api
    with _lock:
        if _api is not None:
            return _api
        api = PluginAPI()
        _load_errors.clear()
        for path in sorted(plugins_dir().glob("*.py")):
            try:
                spec = importlib.util.spec_from_file_location(f"talkdat_plugin_{path.stem}", path)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                register = getattr(module, "register", None)
                if callable(register):
                    register(api)
            except Exception as exc:
                _load_errors.append(f"{path.name}: {exc}")
        _api = api
        return api


def reload_plugins() -> None:
    global _api
    with _lock:
        _api = None


def plugin_transform(transform_id: str, text: str, config: dict[str, Any]) -> str | None:
    if not plugins_enabled(config):
        return None
    fn = _load_all().transforms.get(transform_id)
    if fn is None:
        return None
    try:
        output = str(fn(text, config)).strip()
        return output or None
    except Exception:
        return None


def plugin_text_filters(config: dict[str, Any]) -> list[FilterFn]:
    if not plugins_enabled(config):
        return []
    return list(_load_all().text_filters)
