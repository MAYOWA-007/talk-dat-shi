from __future__ import annotations

import ctypes
import json
import math
import os
import sys
import threading
import tkinter as tk
import time
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageTk

from .config import (
    config_path,
    full_history_path,
    history_db_path,
    history_path,
    live_draft_path,
    scratchpad_path,
    scratchpad_tabs_path,
)
from .history import HISTORY_BACKENDS, clear_all_history, create_history_store, history_backend
from .icon import ensure_icon_file
from .local_stt import (
    DEFAULT_LOCAL_MODEL_ID,
    LOCAL_MODELS,
    delete_model as delete_local_model,
    download_model as download_local_model,
    downloaded_size_mb as local_downloaded_size_mb,
    is_downloaded as local_model_downloaded,
    models_dir as local_models_dir,
)
from .stt_registry import (
    PROVIDER_BY_ID,
    model_for_id,
    model_id_for_label,
    model_label,
    model_labels,
    provider_capability_summary,
    provider_id_for_label,
    provider_label,
    provider_labels,
    provider_settings,
    selected_model_id,
    selected_provider_id,
    selected_variant,
    sync_legacy_deepgram,
)
from .version import APP_VERSION


Callback = Callable[[], None]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


TRANSPARENT_COLOR = "#010203"
LIVE_STATES = {"starting", "connected", "listening", "command"}
SETTINGS_THEME_FAMILIES = (
    "Flow",
    "Ember Glass",
    "Teal Circuit",
    "Solar Ribbon",
    "Crimson Bloom",
    "Aqua Noir",
    "Champagne Glass",
    "Violet Signal",
    "Graphite Pulse",
    "Ivory Halo",
)
SETTINGS_THEME_PALETTE_KEYS = (
    "bg",
    "panel",
    "surface",
    "field",
    "text",
    "muted",
    "accent",
    "accent2",
    "warm",
    "button",
    "select",
    "stroke",
    "glass",
)
SETTINGS_THEME_PALETTES: dict[str, dict[str, dict[str, str]]] = {
    "Flow": {
        "Dark": {
            "bg": "#061012",
            "panel": "#0b181b",
            "surface": "#111f23",
            "field": "#16272b",
            "text": "#edf7f3",
            "muted": "#93aaa5",
            "accent": "#37e2c0",
            "accent2": "#ffca68",
            "warm": "#ff4f73",
            "button": "#16282d",
            "select": "#173c39",
            "stroke": "#244648",
            "glass": "#091719",
        },
        "Light": {
            "bg": "#eef7f3",
            "panel": "#f8fffb",
            "surface": "#ffffff",
            "field": "#ffffff",
            "text": "#122420",
            "muted": "#58706a",
            "accent": "#008f7f",
            "accent2": "#b97908",
            "warm": "#c92b52",
            "button": "#dcebe6",
            "select": "#c9efe5",
            "stroke": "#abcac1",
            "glass": "#ffffff",
        },
    },
    "Ember Glass": {
        "Dark": {
            "bg": "#130c09",
            "panel": "#1d130f",
            "surface": "#2a1b15",
            "field": "#322018",
            "text": "#fff4e8",
            "muted": "#d4ad97",
            "accent": "#ff8a52",
            "accent2": "#ffe090",
            "warm": "#15d7c0",
            "button": "#322019",
            "select": "#4a2b20",
            "stroke": "#6d3b29",
            "glass": "#190f0b",
        },
        "Light": {
            "bg": "#fff1e6",
            "panel": "#fffaf4",
            "surface": "#ffffff",
            "field": "#fffdf9",
            "text": "#2b1810",
            "muted": "#7b5d4f",
            "accent": "#b94c1e",
            "accent2": "#946108",
            "warm": "#008b7c",
            "button": "#f1d9c7",
            "select": "#ffd9c1",
            "stroke": "#d4a284",
            "glass": "#fff8ef",
        },
    },
    "Teal Circuit": {
        "Dark": {
            "bg": "#021416",
            "panel": "#071f22",
            "surface": "#0e2d31",
            "field": "#12383d",
            "text": "#eafffb",
            "muted": "#91c2bc",
            "accent": "#23e7ce",
            "accent2": "#7cf7d4",
            "warm": "#ffbd6d",
            "button": "#103035",
            "select": "#104740",
            "stroke": "#1a6667",
            "glass": "#061a1d",
        },
        "Light": {
            "bg": "#e8fbf8",
            "panel": "#f5fffd",
            "surface": "#ffffff",
            "field": "#ffffff",
            "text": "#0f2928",
            "muted": "#4d706d",
            "accent": "#008b81",
            "accent2": "#168b61",
            "warm": "#b76513",
            "button": "#d2f0eb",
            "select": "#bceee5",
            "stroke": "#92cfc6",
            "glass": "#f9fffd",
        },
    },
    "Solar Ribbon": {
        "Dark": {
            "bg": "#100f07",
            "panel": "#1b190c",
            "surface": "#29240e",
            "field": "#342c12",
            "text": "#fff8df",
            "muted": "#d3bd80",
            "accent": "#ffd36f",
            "accent2": "#ff674d",
            "warm": "#28dcc3",
            "button": "#332711",
            "select": "#4b3316",
            "stroke": "#705324",
            "glass": "#171308",
        },
        "Light": {
            "bg": "#fff7df",
            "panel": "#fffdf4",
            "surface": "#ffffff",
            "field": "#fffef8",
            "text": "#2a210c",
            "muted": "#706239",
            "accent": "#9d6500",
            "accent2": "#c43a25",
            "warm": "#008b7b",
            "button": "#f2dfad",
            "select": "#ffe7aa",
            "stroke": "#d7b767",
            "glass": "#fffbe9",
        },
    },
    "Crimson Bloom": {
        "Dark": {
            "bg": "#16070e",
            "panel": "#230d16",
            "surface": "#321520",
            "field": "#3b1a28",
            "text": "#fff0f4",
            "muted": "#d8a2b0",
            "accent": "#ff466f",
            "accent2": "#ffc773",
            "warm": "#31d6c3",
            "button": "#351723",
            "select": "#511d2e",
            "stroke": "#743047",
            "glass": "#1c0a11",
        },
        "Light": {
            "bg": "#fff0f4",
            "panel": "#fff9fb",
            "surface": "#ffffff",
            "field": "#ffffff",
            "text": "#32131f",
            "muted": "#7c5260",
            "accent": "#bf2149",
            "accent2": "#a66b08",
            "warm": "#008c80",
            "button": "#f3d6df",
            "select": "#ffd7e3",
            "stroke": "#d79aac",
            "glass": "#fff7fa",
        },
    },
    "Aqua Noir": {
        "Dark": {
            "bg": "#03101f",
            "panel": "#071a2e",
            "surface": "#0d2740",
            "field": "#12314d",
            "text": "#edf9ff",
            "muted": "#99bfd1",
            "accent": "#3fe8ff",
            "accent2": "#20d4aa",
            "warm": "#ff7060",
            "button": "#112d45",
            "select": "#0e4a57",
            "stroke": "#1d657b",
            "glass": "#061626",
        },
        "Light": {
            "bg": "#eaf8ff",
            "panel": "#f7fdff",
            "surface": "#ffffff",
            "field": "#ffffff",
            "text": "#102537",
            "muted": "#527284",
            "accent": "#007f96",
            "accent2": "#00896f",
            "warm": "#bf3a2d",
            "button": "#d8edf7",
            "select": "#c5f2f7",
            "stroke": "#9bc7d8",
            "glass": "#fbfeff",
        },
    },
    "Champagne Glass": {
        "Dark": {
            "bg": "#11100b",
            "panel": "#1c1a12",
            "surface": "#29251a",
            "field": "#302c1f",
            "text": "#fff8e7",
            "muted": "#d2c199",
            "accent": "#e7c989",
            "accent2": "#fff0bc",
            "warm": "#16bfa9",
            "button": "#2f2a1c",
            "select": "#433923",
            "stroke": "#6a5b34",
            "glass": "#17150d",
        },
        "Light": {
            "bg": "#faf3df",
            "panel": "#fffaf0",
            "surface": "#ffffff",
            "field": "#fffef9",
            "text": "#282111",
            "muted": "#6e6346",
            "accent": "#967333",
            "accent2": "#806006",
            "warm": "#007f72",
            "button": "#ebe0bf",
            "select": "#f5e6bb",
            "stroke": "#cab574",
            "glass": "#fff9eb",
        },
    },
    "Violet Signal": {
        "Dark": {
            "bg": "#100b1e",
            "panel": "#1b1230",
            "surface": "#281b45",
            "field": "#312253",
            "text": "#f7f0ff",
            "muted": "#bfaee2",
            "accent": "#b88cff",
            "accent2": "#54dfff",
            "warm": "#ffcd73",
            "button": "#2a1e47",
            "select": "#3f2865",
            "stroke": "#62469a",
            "glass": "#160f29",
        },
        "Light": {
            "bg": "#f4eeff",
            "panel": "#fbf8ff",
            "surface": "#ffffff",
            "field": "#ffffff",
            "text": "#26183b",
            "muted": "#67587c",
            "accent": "#7244b8",
            "accent2": "#007d96",
            "warm": "#9b6500",
            "button": "#e5d8f7",
            "select": "#e3d2ff",
            "stroke": "#b79bdc",
            "glass": "#fdfaff",
        },
    },
    "Graphite Pulse": {
        "Dark": {
            "bg": "#0b0d12",
            "panel": "#131720",
            "surface": "#1f2632",
            "field": "#262f3d",
            "text": "#f1f5fb",
            "muted": "#a9b5c4",
            "accent": "#8ea4ff",
            "accent2": "#39d7c6",
            "warm": "#ffd067",
            "button": "#222b37",
            "select": "#26394f",
            "stroke": "#45576d",
            "glass": "#10141b",
        },
        "Light": {
            "bg": "#f0f3f7",
            "panel": "#fbfcfe",
            "surface": "#ffffff",
            "field": "#ffffff",
            "text": "#1a222e",
            "muted": "#596675",
            "accent": "#405bbb",
            "accent2": "#00877c",
            "warm": "#9b6600",
            "button": "#dfe6ee",
            "select": "#d8e5f7",
            "stroke": "#abb8c8",
            "glass": "#ffffff",
        },
    },
    "Ivory Halo": {
        "Dark": {
            "bg": "#12110d",
            "panel": "#1d1b15",
            "surface": "#2b281f",
            "field": "#342f23",
            "text": "#fffaf0",
            "muted": "#cfc4ac",
            "accent": "#d7b56d",
            "accent2": "#72d9cb",
            "warm": "#ff8666",
            "button": "#302c20",
            "select": "#3d3a26",
            "stroke": "#665d3b",
            "glass": "#181711",
        },
        "Light": {
            "bg": "#fffaf0",
            "panel": "#fffdf8",
            "surface": "#ffffff",
            "field": "#ffffff",
            "text": "#2a2417",
            "muted": "#6f644d",
            "accent": "#8a6a26",
            "accent2": "#007f76",
            "warm": "#ba482f",
            "button": "#efe6d1",
            "select": "#f3e8c7",
            "stroke": "#c9b887",
            "glass": "#fffdf7",
        },
    },
}


class Overlay:
    def __init__(self, config: dict[str, Any], callbacks: dict[str, Callback]) -> None:
        self.config = config
        self.callbacks = callbacks
        overlay_config = config.get("overlay", {})
        self.active_pill_width = int(overlay_config.get("active_pill_width", overlay_config.get("width", 320)))
        self.active_pill_height = int(overlay_config.get("active_pill_height", overlay_config.get("height", 58)))
        self.active_width = int(overlay_config.get("active_width", self.active_pill_width))
        self.active_height = int(overlay_config.get("active_height", self.active_pill_height))
        self.expanded_width = self.active_width
        self.expanded_height = self.active_height
        self.compact_width = int(overlay_config.get("compact_width", max(1, round(self.active_pill_width / 2))))
        self.compact_height = int(overlay_config.get("compact_height", max(1, round(self.active_pill_height / 2))))
        self.current_width = self.compact_width
        self.current_height = self.compact_height
        self._last_geometry = ""
        self.bottom_margin = int(overlay_config.get("bottom_margin", 68))
        self.result_hold_ms = int(overlay_config.get("result_hold_ms", 2400))
        self.error_hold_ms = int(overlay_config.get("error_hold_ms", 5200))
        self.active_frame_ms = int(overlay_config.get("active_frame_ms", 16))
        self.idle_frame_ms = int(overlay_config.get("idle_frame_ms", 33))
        self.resize_frame_ms = int(overlay_config.get("resize_frame_ms", 12))
        self.active_loop_seconds = float(overlay_config.get("active_loop_seconds", 3.84))
        self.idle_loop_seconds = float(overlay_config.get("idle_loop_seconds", 8.0))
        self.fixed_position = bool(overlay_config.get("fixed_position", True))
        self.no_activate = bool(overlay_config.get("no_activate", True))
        self.opacity = float(overlay_config.get("opacity", 0.94))
        self.hover_fade_delay_ms = int(overlay_config.get("hover_fade_delay_ms", 2000))
        self.hover_fade_opacity = float(overlay_config.get("hover_fade_opacity", 0.38))
        self.hide_over_fullscreen_media = bool(overlay_config.get("hide_over_fullscreen_media", True))
        self.show_session_over_fullscreen = bool(overlay_config.get("show_session_over_fullscreen", False))
        self.fullscreen_poll_ms = int(overlay_config.get("fullscreen_poll_ms", 450))
        self.current_alpha = self.opacity

        self.root = tk.Tk()
        self.root.title("Talk Dat!")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.opacity)
        self.root.configure(bg=TRANSPARENT_COLOR)
        try:
            self.root.attributes("-transparentcolor", TRANSPARENT_COLOR)
        except Exception:
            pass
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        try:
            self.root.iconbitmap(str(ensure_icon_file()))
        except Exception:
            pass

        self.state = "idle"
        self.level = 0.0
        self.display_level = 0.0
        self.hover_level = 0.0
        self.hover_translucent_level = 0.0
        self.hovered = False
        self.hover_started_at: float | None = None
        self.phase = 0
        self.started_at = time.perf_counter()
        self.drag_origin: tuple[int, int] | None = None
        self.pill_click_origin: tuple[int, int] | None = None
        self.pill_click_dragged = False
        self.compact = True
        self.last_status = "Mic off. Hold Ctrl+Win to record."
        self.last_preview = ""
        self.resize_after_id: str | None = None
        self.idle_after_id: str | None = None
        self.utility_windows: dict[str, tk.Toplevel] = {}
        self.context_menu_window: tk.Toplevel | None = None
        self.context_menu_canvas: tk.Canvas | None = None
        self.context_menu_photo: ImageTk.PhotoImage | None = None
        self.context_menu_after_id: str | None = None
        self.context_menu_hover = ""
        self.settings_header_photo: ImageTk.PhotoImage | None = None
        self.settings_header_photos: dict[int, ImageTk.PhotoImage] = {}
        self.visual_photo: ImageTk.PhotoImage | None = None
        self.visual_canvas_item: int | None = None
        self.flow_loop_strip: Image.Image | None = None
        self.flow_loop_meta: dict[str, int | float] = {}
        self.flow_frame_cache: dict[tuple[int, int], list[Image.Image]] = {}
        self.flow_single_frame_cache: dict[tuple[int, int, int], Image.Image] = {}
        self.active_render_cache: dict[tuple[int, ...], Image.Image] = {}
        self.active_photo_cache: dict[tuple[int, ...], ImageTk.PhotoImage] = {}
        self.idle_render_cache: dict[tuple[int, ...], Image.Image] = {}
        self.idle_photo_cache: dict[tuple[int, ...], ImageTk.PhotoImage] = {}
        self.hover_halo_cache: dict[tuple[int, int, int, int], Image.Image] = {}
        self.pill_lift_cache: dict[tuple[int, int, int, int, int, int, int], Image.Image] = {}
        self.last_flow_render_key: tuple[int, int] | None = None
        self.last_animation_tick = time.perf_counter()
        self.utility_drag_origin: tuple[int, int, int, int] | None = None
        self.fullscreen_hidden = False
        self.fullscreen_session_visible = False
        self.compact_wave_strip: Image.Image | None = None
        self.compact_wave_reference: Image.Image | None = None
        self.compact_wave_meta: dict[str, int | float] = {}
        self.compact_mask_cache: dict[tuple[int, int], Image.Image] = {}
        self.wave_loop_start = int(overlay_config.get("wave_loop_start", 0))
        self.wave_loop_end = int(overlay_config.get("wave_loop_end", 50))
        self._load_flow_loop_assets()
        self._load_compact_wave_assets()

        self.container = tk.Frame(
            self.root,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.container, bg=TRANSPARENT_COLOR, bd=0, highlightthickness=0)
        self.canvas.place(x=0, y=0, width=self.current_width, height=self.current_height)

        for widget in (self.root, self.container, self.canvas):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-3>", self._open_context_menu_from_event)
        for widget in (self.root, self.container, self.canvas):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)
            widget.bind("<ButtonRelease-1>", self._end_drag)
        self.root.bind("<Configure>", lambda _event: self._repaint())

        self.root.update_idletasks()
        self._layout_compact()
        self._position()
        self.root.after(80, self._post_init)
        self.root.after(220, self.force_visible)
        self.root.after(560, self._warm_visual_caches)
        self.root.after(480, self._refresh_fullscreen_visibility)
        self.root.after(80, self._animate)

    def _asset_path(self, filename: str) -> Path:
        local_path = Path(__file__).resolve().parent / "assets" / filename
        if local_path.exists():
            return local_path
        bundle_root = getattr(sys, "_MEIPASS", "")
        if bundle_root:
            bundled_path = Path(bundle_root) / "knight_flow" / "assets" / filename
            if bundled_path.exists():
                return bundled_path
        return local_path

    def _load_asset_image(self, filename: str) -> Image.Image | None:
        try:
            return Image.open(self._asset_path(filename)).convert("RGBA")
        except Exception:
            return None

    def _load_flow_loop_assets(self) -> None:
        asset_name = "flow_pill_60.png"
        for candidate in ("flow_pill_240.png", "flow_pill_120.png", "flow_pill_60.png"):
            if self._asset_path(candidate).exists():
                asset_name = candidate
                break
        meta_name = asset_name.replace(".png", ".json")
        self.flow_loop_strip = self._load_asset_image(asset_name)
        meta_path = self._asset_path(meta_name)
        loaded_meta: dict[str, Any] = {}
        try:
            if meta_path.exists():
                loaded_meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            loaded_meta = {}

        strip = self.flow_loop_strip
        if strip is None:
            self.flow_loop_meta = {}
            return

        frame_width = max(1, min(int(loaded_meta.get("frame_width", self.active_pill_width)), strip.width))
        frame_height = max(1, min(int(loaded_meta.get("frame_height", self.active_pill_height)), strip.height))
        columns = max(1, int(loaded_meta.get("columns", max(1, strip.width // frame_width))))
        rows = max(1, strip.height // frame_height)
        capacity = max(1, columns * rows)
        frame_count = max(1, min(int(loaded_meta.get("frame_count", capacity)), capacity))
        self.flow_loop_meta = {
            "columns": columns,
            "frame_count": frame_count,
            "frame_width": frame_width,
            "frame_height": frame_height,
            "fps": float(loaded_meta.get("fps", 60.0)),
            "bridge_start_frame": int(loaded_meta.get("bridge_start_frame", frame_count)),
            "source": str(loaded_meta.get("source", "")),
            "direction": str(loaded_meta.get("direction", "")),
            "no_pingpong": bool(loaded_meta.get("no_pingpong", False)),
            "transparent_background": bool(loaded_meta.get("transparent_background", False)),
        }

    def _warm_visual_caches(self, start_index: int = 0) -> None:
        if self.flow_loop_strip is None:
            return
        try:
            frame_width = int(self.flow_loop_meta.get("frame_width", self.active_pill_width))
            frame_height = int(self.flow_loop_meta.get("frame_height", self.active_pill_height))
            columns = int(self.flow_loop_meta.get("columns", 1))
            frame_count = int(self.flow_loop_meta.get("frame_count", 1))
            clean_count = self._clean_loop_frame_count(frame_count)
            end_index = min(clean_count, max(0, int(start_index)) + 24)
            for index in range(max(0, int(start_index)), end_index):
                self._flow_cached_frame_for_size(
                    index,
                    self.compact_width,
                    self.compact_height,
                    frame_width,
                    frame_height,
                    columns,
                )
                self._flow_cached_frame_for_size(
                    index,
                    self.active_pill_width,
                    self.active_pill_height,
                    frame_width,
                    frame_height,
                    columns,
                )
            if end_index < clean_count:
                self.root.after(24, lambda next_index=end_index: self._warm_visual_caches(next_index))
        except Exception:
            pass

    def _load_compact_wave_assets(self) -> None:
        self.compact_wave_reference = self._load_asset_image("wave_reference.png")
        self.compact_wave_strip = self._load_asset_image("wave_strip.png")
        meta_path = self._asset_path("wave_strip.json")
        loaded_meta: dict[str, Any] = {}
        try:
            if meta_path.exists():
                loaded_meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            loaded_meta = {}

        strip = self.compact_wave_strip
        frame_width = int(loaded_meta.get("frame_width", self.compact_width))
        frame_height = int(loaded_meta.get("frame_height", self.compact_height))
        if strip is not None:
            frame_width = max(1, min(frame_width, strip.width))
            frame_height = max(1, min(frame_height, strip.height))
            columns = max(1, int(loaded_meta.get("columns", max(1, strip.width // frame_width))))
            rows = max(1, strip.height // frame_height)
            capacity = max(1, columns * rows)
            frame_count = max(1, min(int(loaded_meta.get("frame_count", capacity)), capacity))
        else:
            columns = 1
            frame_count = 1

        self.compact_wave_meta = {
            "columns": columns,
            "frame_count": frame_count,
            "frame_width": frame_width,
            "frame_height": frame_height,
            "fps": float(loaded_meta.get("fps", 24.0)),
        }

    def _callback(self, name: str) -> Callback:
        return self.callbacks.get(name, lambda: None)

    def apply_runtime_config(self) -> None:
        overlay_config = self.config.get("overlay", {})
        self.active_pill_width = int(overlay_config.get("active_pill_width", overlay_config.get("width", 320)))
        self.active_pill_height = int(overlay_config.get("active_pill_height", overlay_config.get("height", 58)))
        self.active_width = int(overlay_config.get("active_width", self.active_pill_width))
        self.active_height = int(overlay_config.get("active_height", self.active_pill_height))
        self.expanded_width = self.active_width
        self.expanded_height = self.active_height
        self.compact_width = int(overlay_config.get("compact_width", max(1, round(self.active_pill_width / 2))))
        self.compact_height = int(overlay_config.get("compact_height", max(1, round(self.active_pill_height / 2))))
        self.bottom_margin = int(overlay_config.get("bottom_margin", self.bottom_margin))
        self.result_hold_ms = int(overlay_config.get("result_hold_ms", self.result_hold_ms))
        self.error_hold_ms = int(overlay_config.get("error_hold_ms", self.error_hold_ms))
        self.active_frame_ms = int(overlay_config.get("active_frame_ms", self.active_frame_ms))
        self.idle_frame_ms = int(overlay_config.get("idle_frame_ms", self.idle_frame_ms))
        self.resize_frame_ms = int(overlay_config.get("resize_frame_ms", self.resize_frame_ms))
        self.active_loop_seconds = float(overlay_config.get("active_loop_seconds", self.active_loop_seconds))
        self.idle_loop_seconds = float(overlay_config.get("idle_loop_seconds", self.idle_loop_seconds))
        self.fixed_position = bool(overlay_config.get("fixed_position", self.fixed_position))
        self.no_activate = bool(overlay_config.get("no_activate", self.no_activate))
        self.opacity = float(overlay_config.get("opacity", self.opacity))
        self.hover_fade_delay_ms = int(overlay_config.get("hover_fade_delay_ms", self.hover_fade_delay_ms))
        self.hover_fade_opacity = float(overlay_config.get("hover_fade_opacity", self.hover_fade_opacity))
        self.hide_over_fullscreen_media = bool(
            overlay_config.get("hide_over_fullscreen_media", self.hide_over_fullscreen_media)
        )
        self.show_session_over_fullscreen = bool(
            overlay_config.get("show_session_over_fullscreen", self.show_session_over_fullscreen)
        )
        self.fullscreen_poll_ms = int(overlay_config.get("fullscreen_poll_ms", self.fullscreen_poll_ms))
        self.wave_loop_start = int(overlay_config.get("wave_loop_start", self.wave_loop_start))
        self.wave_loop_end = int(overlay_config.get("wave_loop_end", self.wave_loop_end))
        self.idle_render_cache.clear()
        self.idle_photo_cache.clear()
        self.active_render_cache.clear()
        self.active_photo_cache.clear()
        self.hover_halo_cache.clear()
        self.flow_single_frame_cache.clear()
        self._apply_root_alpha(self.opacity, force=True)
        self._set_compact(self.state == "idle", animate=True)
        self.root.after(320, self._warm_visual_caches)

    def _post_init(self) -> None:
        if self.no_activate:
            self._make_no_activate(self.root)
        self._repaint()
        self.force_visible()

    def _make_no_activate(self, window: tk.Tk | tk.Toplevel) -> None:
        try:
            hwnd = int(window.winfo_id())
            user32 = ctypes.windll.user32
            gwl_exstyle = -20
            ws_ex_toolwindow = 0x00000080
            ws_ex_noactivate = 0x08000000
            style = user32.GetWindowLongW(hwnd, gwl_exstyle)
            user32.SetWindowLongW(hwnd, gwl_exstyle, style | ws_ex_toolwindow | ws_ex_noactivate)
        except Exception:
            pass

    def _position(self) -> None:
        self._apply_geometry(self.current_width, self.current_height)

    def _apply_geometry(self, width: int, height: int, *, finalize: bool = True) -> None:
        width = max(1, int(round(width)))
        height = max(1, int(round(height)))
        left, top, right, bottom = self._logical_work_area()
        screen_w = right - left
        x = left + int((screen_w - width) / 2)
        y = bottom - height - self.bottom_margin
        self.current_width = width
        self.current_height = height
        geometry = f"{width}x{height}+{x}+{y}"
        if geometry != self._last_geometry:
            self.root.geometry(geometry)
            self.canvas.place(x=0, y=0, width=width, height=height)
            if finalize:
                self.root.minsize(width, height)
                self.root.update_idletasks()
            self._apply_pill_region(width, height, redraw=finalize)
            self._last_geometry = geometry
        self._draw_visual()

    def _apply_pill_region(self, width: int, height: int, *, redraw: bool = True) -> None:
        self._apply_window_region(self.root, width, height, max(1, height // 2), redraw=redraw)

    def _apply_window_region(
        self, window: tk.Tk | tk.Toplevel, width: int, height: int, radius: int, *, redraw: bool = True
    ) -> None:
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            hwnd = int(window.winfo_id())
            handles = {hwnd}
            try:
                ancestor = int(user32.GetAncestor(hwnd, 2))
                if ancestor:
                    handles.add(ancestor)
            except Exception:
                pass
            try:
                parent = int(user32.GetParent(hwnd))
                if parent:
                    handles.add(parent)
            except Exception:
                pass
            for handle in handles:
                corner = max(1, int(radius) * 2)
                region = gdi32.CreateRoundRectRgn(0, 0, int(width) + 1, int(height) + 1, corner, corner)
                if region:
                    user32.SetWindowRgn(handle, region, redraw)
        except Exception:
            pass

    def _set_compact(self, compact: bool, *, animate: bool = True) -> None:
        if self.compact == compact and self.resize_after_id is None:
            self._layout_compact()
            self._position()
            return

        self.compact = compact
        if compact:
            self._layout_compact()
            target_width = self.compact_width
            target_height = self.compact_height
        else:
            self._layout_compact()
            target_width = self.active_width
            target_height = self.active_height

        if self.resize_after_id:
            try:
                self.root.after_cancel(self.resize_after_id)
            except Exception:
                pass
            self.resize_after_id = None

        if not animate:
            self._apply_geometry(target_width, target_height)
            return

        steps = int(self._clamp(self.config.get("overlay", {}).get("resize_steps", 12), 6, 24))
        # Time-based animation: Windows Tk timers fire at ~15.6 ms granularity, so
        # progress is driven by real elapsed time, not step counts. Late frames skip
        # ahead instead of stretching the animation, which is what caused the chop.
        duration_ms = self._clamp(self.resize_frame_ms * steps * 2.2, 150.0, 600.0)
        self._animate_resize(
            self.current_width,
            self.current_height,
            target_width,
            target_height,
            time.perf_counter(),
            duration_ms / 1000.0,
        )

    def _animate_resize(
        self,
        start_width: int,
        start_height: int,
        target_width: int,
        target_height: int,
        started_at: float,
        duration_seconds: float,
    ) -> None:
        progress = min(1.0, (time.perf_counter() - started_at) / max(0.01, duration_seconds))
        eased = 1 - pow(1 - progress, 3)
        width = int(round(start_width + (target_width - start_width) * eased))
        height = int(round(start_height + (target_height - start_height) * eased))
        if progress >= 1.0:
            self._apply_geometry(target_width, target_height)
            self.resize_after_id = None
            return
        self._apply_geometry(width, height, finalize=False)
        self.resize_after_id = self.root.after(
            8,
            lambda: self._animate_resize(start_width, start_height, target_width, target_height, started_at, duration_seconds),
        )

    def _layout_compact(self) -> None:
        self.canvas.place(x=0, y=0, width=self.current_width, height=self.current_height)

    def _layout_expanded(self) -> None:
        self._layout_compact()

    def _logical_work_area(self) -> tuple[int, int, int, int]:
        tk_width = max(1, int(self.root.winfo_screenwidth()))
        tk_height = max(1, int(self.root.winfo_screenheight()))
        left, top, right, bottom = self._primary_work_area()
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            return 0, 0, tk_width, tk_height

        try:
            user32 = ctypes.windll.user32
            physical_width = int(user32.GetSystemMetrics(0))
            physical_height = int(user32.GetSystemMetrics(1))
        except Exception:
            physical_width = 0
            physical_height = 0

        if physical_width > 0 and physical_height > 0:
            scale_x = tk_width / physical_width
            scale_y = tk_height / physical_height
            if abs(scale_x - 1.0) > 0.01 or abs(scale_y - 1.0) > 0.01:
                return (
                    int(left * scale_x),
                    int(top * scale_y),
                    int(right * scale_x),
                    int(bottom * scale_y),
                )

        if right > tk_width or bottom > tk_height:
            return 0, 0, tk_width, tk_height
        return left, top, right, bottom

    def _primary_work_area(self) -> tuple[int, int, int, int]:
        try:
            rect = RECT()
            spi_getworkarea = 0x0030
            ctypes.windll.user32.SystemParametersInfoW(spi_getworkarea, 0, ctypes.byref(rect), 0)
            if rect.right > rect.left and rect.bottom > rect.top:
                return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            pass
        return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def force_visible(self) -> None:
        try:
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            self.root.lift()
            self._position()
            hwnd = int(self.root.winfo_id())
            hwnd_topmost = -1
            swp_showwindow = 0x0040
            swp_noownerzorder = 0x0200
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                hwnd_topmost,
                self.root.winfo_x(),
                self.root.winfo_y(),
                self.current_width,
                self.current_height,
                swp_showwindow | swp_noownerzorder,
            )
            ctypes.windll.user32.BringWindowToTop(hwnd)
        except Exception:
            pass

    def show(self) -> None:
        self.root.after(0, self.force_visible)

    def hide(self) -> None:
        self.root.after(0, self.root.withdraw)

    def set_session_visible(self, visible: bool) -> None:
        self.root.after(0, lambda value=bool(visible): self._set_session_visible_now(value))

    def _set_session_visible_now(self, visible: bool) -> None:
        self.fullscreen_session_visible = visible
        if visible:
            if self._stay_hidden_during_session():
                # A fullscreen game/video owns the screen: keep recording and pasting,
                # but never touch its z-order or pop the pill over it.
                self._sync_fullscreen_visibility()
                return
            self.fullscreen_hidden = False
            self.force_visible()
            return
        self._sync_fullscreen_visibility()

    def _stay_hidden_during_session(self) -> bool:
        return (
            self.hide_over_fullscreen_media
            and not self.show_session_over_fullscreen
            and self._foreground_is_fullscreen()
        )

    def _own_window_handles(self) -> set[int]:
        handles: set[int] = set()
        user32 = ctypes.windll.user32
        windows: list[tk.Misc] = [self.root]
        windows.extend(window for window in self.utility_windows.values() if window.winfo_exists())
        if self.context_menu_window is not None and self.context_menu_window.winfo_exists():
            windows.append(self.context_menu_window)
        for window in windows:
            try:
                hwnd = int(window.winfo_id())
            except Exception:
                continue
            if not hwnd:
                continue
            handles.add(hwnd)
            try:
                ancestor = int(user32.GetAncestor(hwnd, 2))
                if ancestor:
                    handles.add(ancestor)
            except Exception:
                pass
            try:
                parent = int(user32.GetParent(hwnd))
                if parent:
                    handles.add(parent)
            except Exception:
                pass
        return handles

    def _foreground_class_name(self, hwnd: int) -> str:
        try:
            buffer = ctypes.create_unicode_buffer(128)
            ctypes.windll.user32.GetClassNameW(hwnd, buffer, len(buffer))
            return str(buffer.value)
        except Exception:
            return ""

    def _foreground_is_fullscreen(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            user32 = ctypes.windll.user32
            hwnd = int(user32.GetForegroundWindow())
            if not hwnd or hwnd in self._own_window_handles():
                return False
            class_name = self._foreground_class_name(hwnd)
            if class_name in {"Progman", "WorkerW", "Shell_TrayWnd"}:
                return False
            if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                return False

            rect = RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return False
            width = int(rect.right - rect.left)
            height = int(rect.bottom - rect.top)
            if width < 320 or height < 240:
                return False

            monitor = user32.MonitorFromWindow(hwnd, 2)
            if not monitor:
                return False
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return False
            monitor_rect = info.rcMonitor
            monitor_width = int(monitor_rect.right - monitor_rect.left)
            monitor_height = int(monitor_rect.bottom - monitor_rect.top)
            if monitor_width <= 0 or monitor_height <= 0:
                return False

            tolerance = int(self._clamp(self.config.get("overlay", {}).get("fullscreen_tolerance_px", 8), 0, 32))
            covers_monitor = (
                rect.left <= monitor_rect.left + tolerance
                and rect.top <= monitor_rect.top + tolerance
                and rect.right >= monitor_rect.right - tolerance
                and rect.bottom >= monitor_rect.bottom - tolerance
            )
            if not covers_monitor:
                return False
            window_area = max(0, width) * max(0, height)
            monitor_area = monitor_width * monitor_height
            return window_area >= monitor_area * 0.88
        except Exception:
            return False

    def _should_hide_for_fullscreen(self) -> bool:
        if not self.hide_over_fullscreen_media:
            return False
        if self.fullscreen_session_visible or self.state in LIVE_STATES:
            if self.show_session_over_fullscreen:
                return False
            return self._foreground_is_fullscreen()
        return self._foreground_is_fullscreen()

    def _sync_fullscreen_visibility(self) -> None:
        should_hide = self._should_hide_for_fullscreen()
        if should_hide:
            if not self.fullscreen_hidden:
                self.fullscreen_hidden = True
                try:
                    self.root.withdraw()
                except Exception:
                    pass
            return
        if self.fullscreen_hidden:
            self.fullscreen_hidden = False
            self.force_visible()

    def _refresh_fullscreen_visibility(self) -> None:
        try:
            self._sync_fullscreen_visibility()
        finally:
            delay = int(self._clamp(self.fullscreen_poll_ms, 120, 3000))
            self.root.after(delay, self._refresh_fullscreen_visibility)

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        self._set_hovered(True)

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self.root.after(60, self._refresh_hover)

    def _refresh_hover(self) -> None:
        try:
            pointer_x = self.root.winfo_pointerx()
            pointer_y = self.root.winfo_pointery()
            x = self.root.winfo_rootx()
            y = self.root.winfo_rooty()
            self._set_hovered(x <= pointer_x <= x + self.current_width and y <= pointer_y <= y + self.current_height)
        except Exception:
            self._set_hovered(False)

    def _set_hovered(self, hovered: bool) -> None:
        if hovered == self.hovered:
            return
        self.hovered = hovered
        self.hover_started_at = time.perf_counter() if hovered else None

    def _start_drag(self, event: tk.Event) -> None:
        self.pill_click_origin = (int(event.x_root), int(event.y_root))
        self.pill_click_dragged = False
        if self.fixed_position:
            self._position()
            return
        self.drag_origin = (event.x, event.y)

    def _drag(self, event: tk.Event) -> None:
        if self.pill_click_origin:
            dx = abs(int(event.x_root) - self.pill_click_origin[0])
            dy = abs(int(event.y_root) - self.pill_click_origin[1])
            if dx > 6 or dy > 6:
                self.pill_click_dragged = True
        if self.fixed_position:
            return
        if self.drag_origin is None:
            return
        dx = event.x - self.drag_origin[0]
        dy = event.y - self.drag_origin[1]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def _end_drag(self, event: tk.Event) -> None:
        should_toggle = False
        if self.pill_click_origin:
            dx = abs(int(event.x_root) - self.pill_click_origin[0])
            dy = abs(int(event.y_root) - self.pill_click_origin[1])
            should_toggle = not self.pill_click_dragged and dx <= 6 and dy <= 6
        self.pill_click_origin = None
        self.pill_click_dragged = False
        self.drag_origin = None
        if self.fixed_position:
            self._position()
        if should_toggle:
            self._toggle_from_pill_click()

    def _toggle_from_pill_click(self) -> None:
        callback = self.callbacks.get("hands_free")
        if callback:
            callback()

    def set_state(self, state: str, message: str | None = None, preview: str | None = None) -> None:
        self.root.after(0, lambda: self._set_state_now(state, message, preview))

    def _set_state_now(self, state: str, message: str | None, preview: str | None) -> None:
        self.state = state
        if message is not None:
            self.last_status = message[:160]
        if preview is not None:
            self.last_preview = preview[:240]
        self._set_compact(state not in LIVE_STATES, animate=True)
        self._schedule_idle_return(state)
        self._repaint()
        self._sync_fullscreen_visibility()

    def _schedule_idle_return(self, state: str) -> None:
        if self.idle_after_id:
            try:
                self.root.after_cancel(self.idle_after_id)
            except Exception:
                pass
            self.idle_after_id = None

        delay = 0
        if state == "captured":
            delay = self.result_hold_ms
        elif state == "error":
            delay = self.error_hold_ms

        if delay > 0:
            self.idle_after_id = self.root.after(delay, lambda expected=state: self._return_to_idle_if_same(expected))

    def _return_to_idle_if_same(self, expected_state: str) -> None:
        self.idle_after_id = None
        if self.state != expected_state:
            return
        self._set_state_now(
            "idle",
            "Hold Ctrl+Win to talk. Toggle only with Ctrl+Win+Space or Mic.",
            "Mic is off. Deepgram is idle.",
        )

    def set_level(self, level: float) -> None:
        self.level = max(0.0, min(1.0, float(level)))

    def _repaint(self) -> None:
        self.container.configure(bg=TRANSPARENT_COLOR)
        self.canvas.configure(bg=TRANSPARENT_COLOR)

    def _animate(self) -> None:
        tick_start = time.perf_counter()
        self.phase = (self.phase + 1) % 1_000_000
        live = self.state in LIVE_STATES
        target_level = self.level if live else 0.0
        self.display_level += (target_level - self.display_level) * (0.18 if live else 0.08)
        self.hover_level += ((1.0 if self.hovered else 0.0) - self.hover_level) * 0.16
        now = time.perf_counter()
        hover_age_ms = 0.0
        if self.hovered and self.hover_started_at is not None:
            hover_age_ms = max(0.0, (now - self.hover_started_at) * 1000.0)
        long_hover = 1.0 if hover_age_ms >= max(0, self.hover_fade_delay_ms) else 0.0
        self.hover_translucent_level += (long_hover - self.hover_translucent_level) * (0.10 if long_hover else 0.18)
        target_alpha = self.opacity + (self.hover_fade_opacity - self.opacity) * self.hover_translucent_level
        self._apply_root_alpha(target_alpha)
        self._draw_visual()
        delay = self.active_frame_ms if live else self.idle_frame_ms
        elapsed_ms = int((time.perf_counter() - tick_start) * 1000)
        self.last_animation_tick = tick_start
        self.root.after(max(4, int(delay) - elapsed_ms), self._animate)

    def _apply_root_alpha(self, alpha: float, *, force: bool = False) -> None:
        alpha = self._clamp(float(alpha), 0.18, 1.0)
        if not force and abs(alpha - self.current_alpha) < 0.006:
            return
        self.current_alpha = alpha
        try:
            self.root.attributes("-alpha", alpha)
        except Exception:
            pass

    def _draw_visual(self) -> None:
        width = max(1, int(self.current_width))
        height = max(1, int(self.current_height))
        self._draw_compact_reference_visual(width, height, active=not self.compact)

    def _draw_compact_reference_visual(self, width: int, height: int, *, active: bool = False) -> None:
        body_width = min(width, self.active_pill_width) if active else width
        body_height = min(height, self.active_pill_height) if active else height
        field = self._compact_wave_frame(body_width, body_height, active=active) or self._compact_reference_fallback(
            body_width, body_height
        )
        idle_cache_key = None
        active_cache_key = None
        if active:
            field = self._finish_compact_wave_frame(field, body_width, body_height, active=active)
            if width != body_width or height != body_height:
                field = self._compose_active_visual(field, width, height, body_width, body_height)
        elif not active and self.hover_level < 0.01 and self.last_flow_render_key is not None:
            idle_cache_key = (body_width, body_height, *self.last_flow_render_key)
            cached = self.idle_render_cache.get(idle_cache_key)
            if cached is not None:
                field = cached
            else:
                field = self._finish_compact_wave_frame(field, body_width, body_height, active=active)
                self.idle_render_cache[idle_cache_key] = field
        else:
            field = self._finish_compact_wave_frame(field, body_width, body_height, active=active)
        cached_photo = None
        if active_cache_key is not None:
            cached_photo = self.active_photo_cache.get(active_cache_key)
        elif idle_cache_key is not None:
            cached_photo = self.idle_photo_cache.get(idle_cache_key)
        if cached_photo is None:
            cached_photo = ImageTk.PhotoImage(field)
            if active_cache_key is not None:
                self.active_photo_cache[active_cache_key] = cached_photo
            elif idle_cache_key is not None:
                self.idle_photo_cache[idle_cache_key] = cached_photo
        self.visual_photo = cached_photo
        if self.visual_canvas_item is None:
            self.visual_canvas_item = int(
                self.canvas.create_image(0, 0, image=self.visual_photo, anchor="nw", tags="visual")
            )
        else:
            try:
                self.canvas.itemconfigure(self.visual_canvas_item, image=self.visual_photo)
                self.canvas.coords(self.visual_canvas_item, 0, 0)
            except tk.TclError:
                self.visual_canvas_item = int(
                    self.canvas.create_image(0, 0, image=self.visual_photo, anchor="nw", tags="visual")
                )

    def _compact_wave_frame(self, width: int, height: int, *, active: bool = False) -> Image.Image | None:
        flow_frame = self._flow_loop_frame(width, height, active=active)
        if flow_frame is not None:
            return flow_frame

        strip = self.compact_wave_strip
        if strip is None:
            return None

        frame_width = int(self.compact_wave_meta.get("frame_width", self.compact_width))
        frame_height = int(self.compact_wave_meta.get("frame_height", self.compact_height))
        columns = int(self.compact_wave_meta.get("columns", 1))
        frame_count = int(self.compact_wave_meta.get("frame_count", 1))
        fps = float(self.compact_wave_meta.get("fps", 24.0))
        if frame_width <= 0 or frame_height <= 0 or columns <= 0 or frame_count <= 0:
            return None

        loop_start = int(self._clamp(self.wave_loop_start, 0, frame_count - 1))
        loop_end = int(self._clamp(self.wave_loop_end, loop_start + 1, frame_count - 1))
        segment_count = int(loop_end - loop_start + 1)
        speed = 7.0 if active else 1.0
        ticks_per_loop = max(1.0, (segment_count * (1000.0 / max(1.0, fps)) / 16.0) / speed)
        frame_pos = ((self.phase % ticks_per_loop) / ticks_per_loop) * segment_count
        frame = self._wave_frame_at(frame_pos, frame_width, frame_height, columns, frame_count, loop_start, segment_count)
        if frame is None:
            return None

        if frame.size != (width, height):
            frame = frame.resize((width, height), Image.Resampling.LANCZOS)
        return frame

    def _flow_loop_frame(self, width: int, height: int, *, active: bool = False) -> Image.Image | None:
        strip = self.flow_loop_strip
        if strip is None:
            return None

        frame_width = int(self.flow_loop_meta.get("frame_width", self.active_pill_width))
        frame_height = int(self.flow_loop_meta.get("frame_height", self.active_pill_height))
        columns = int(self.flow_loop_meta.get("columns", 1))
        frame_count = int(self.flow_loop_meta.get("frame_count", 1))
        if frame_width <= 0 or frame_height <= 0 or columns <= 0 or frame_count <= 0:
            return None

        elapsed = max(0.0, time.perf_counter() - self.started_at)
        loop_seconds = max(0.10, self.active_loop_seconds if active else self.idle_loop_seconds)
        frame_pos = (elapsed / loop_seconds) * frame_count

        if (width, height) in {
            (self.compact_width, self.compact_height),
            (self.active_pill_width, self.active_pill_height),
        }:
            first_index = int(math.floor(frame_pos)) % frame_count
            second_index = (first_index + 1) % frame_count
            first = self._flow_cached_frame_for_size(first_index, width, height, frame_width, frame_height, columns)
            second = self._flow_cached_frame_for_size(second_index, width, height, frame_width, frame_height, columns)
            if first is None or second is None:
                return None
            alpha = self._smoothstep(0.0, 1.0, frame_pos - math.floor(frame_pos))
            if not active:
                alpha_steps = 6
                alpha_bucket = int(round(alpha * alpha_steps))
                if alpha_bucket <= 0:
                    self.last_flow_render_key = (first_index, 0)
                    return first
                if alpha_bucket >= alpha_steps:
                    self.last_flow_render_key = (second_index, 0)
                    return second
                self.last_flow_render_key = (first_index, alpha_bucket)
                return Image.blend(first, second, alpha_bucket / alpha_steps)
            else:
                alpha_steps = 16
                alpha_bucket = int(round(alpha * alpha_steps))
                self.last_flow_render_key = (first_index, alpha_bucket)
                return Image.blend(first, second, alpha)

        self.last_flow_render_key = None
        frame = self._loop_frame_at(strip, frame_pos, frame_width, frame_height, columns, frame_count)
        if frame is None:
            return None
        if frame.size != (width, height):
            frame = frame.resize((width, height), Image.Resampling.LANCZOS)
        return frame

    def _clean_loop_frame_count(self, frame_count: int) -> int:
        source = str(self.flow_loop_meta.get("source", "")).lower()
        if self.flow_loop_meta.get("transparent_background") or "seamless" in source:
            return frame_count
        bridge_start = int(self.flow_loop_meta.get("bridge_start_frame", frame_count))
        if 16 <= bridge_start < frame_count:
            return bridge_start
        return frame_count

    def _pingpong_frame_position(self, elapsed: float, loop_seconds: float, frame_count: int) -> float:
        if frame_count <= 1:
            return 0.0
        cycle = float((frame_count - 1) * 2)
        position = ((elapsed / max(0.10, loop_seconds)) * cycle) % cycle
        if position <= frame_count - 1:
            return position
        return cycle - position

    def _flow_cached_frame_for_size(
        self,
        index: int,
        width: int,
        height: int,
        frame_width: int,
        frame_height: int,
        columns: int,
    ) -> Image.Image | None:
        key = (width, height, index)
        cached = self.flow_single_frame_cache.get(key)
        if cached is not None:
            return cached
        strip = self.flow_loop_strip
        if strip is None:
            return None
        frame = self._strip_frame_from(strip, index, frame_width, frame_height, columns)
        if frame is None:
            return None
        if frame.size != (width, height):
            frame = frame.resize((width, height), Image.Resampling.LANCZOS)
        if len(self.flow_single_frame_cache) > 760:
            self.flow_single_frame_cache.clear()
        self.flow_single_frame_cache[key] = frame
        return frame

    def _flow_frames_for_size(
        self,
        width: int,
        height: int,
        frame_width: int,
        frame_height: int,
        columns: int,
        frame_count: int,
    ) -> list[Image.Image] | None:
        if (width, height) not in {
            (self.compact_width, self.compact_height),
            (self.active_pill_width, self.active_pill_height),
        }:
            return None
        key = (width, height)
        cached = self.flow_frame_cache.get(key)
        if cached is not None:
            return cached
        strip = self.flow_loop_strip
        if strip is None:
            return None
        frames: list[Image.Image] = []
        for index in range(frame_count):
            frame = self._strip_frame_from(strip, index, frame_width, frame_height, columns)
            if frame is None:
                return None
            if frame.size != (width, height):
                frame = frame.resize((width, height), Image.Resampling.LANCZOS)
            frames.append(frame)
        self.flow_frame_cache[key] = frames
        return frames

    def _loop_frame_at(
        self,
        strip: Image.Image,
        frame_pos: float,
        frame_width: int,
        frame_height: int,
        columns: int,
        frame_count: int,
    ) -> Image.Image | None:
        first_index = int(math.floor(frame_pos)) % frame_count
        second_index = (first_index + 1) % frame_count
        alpha = self._smoothstep(0.0, 1.0, frame_pos - math.floor(frame_pos))
        first = self._strip_frame_from(strip, first_index, frame_width, frame_height, columns)
        second = self._strip_frame_from(strip, second_index, frame_width, frame_height, columns)
        if first is None or second is None:
            return None
        return Image.blend(first, second, alpha)

    def _source_frame_at(
        self,
        strip: Image.Image,
        frame_pos: float,
        frame_width: int,
        frame_height: int,
        columns: int,
        frame_count: int,
    ) -> Image.Image | None:
        first_index = max(0, min(frame_count - 1, int(math.floor(frame_pos))))
        second_index = min(frame_count - 1, first_index + 1)
        alpha = self._smoothstep(0.0, 1.0, frame_pos - math.floor(frame_pos))
        first = self._strip_frame_from(strip, first_index, frame_width, frame_height, columns)
        second = self._strip_frame_from(strip, second_index, frame_width, frame_height, columns)
        if first is None or second is None:
            return None
        return Image.blend(first, second, alpha)

    def _strip_frame_from(
        self,
        strip: Image.Image,
        index: int,
        frame_width: int,
        frame_height: int,
        columns: int,
    ) -> Image.Image | None:
        column = index % columns
        row = index // columns
        left = column * frame_width
        top = row * frame_height
        if left + frame_width > strip.width or top + frame_height > strip.height:
            return None
        return strip.crop((left, top, left + frame_width, top + frame_height))

    def _wave_frame_at(
        self,
        frame_pos: float,
        frame_width: int,
        frame_height: int,
        columns: int,
        frame_count: int,
        loop_start: int = 0,
        segment_count: int | None = None,
    ) -> Image.Image | None:
        strip = self.compact_wave_strip
        if strip is None:
            return None
        segment = max(1, segment_count if segment_count is not None else frame_count)
        first_local = int(math.floor(frame_pos)) % segment
        second_local = (first_local + 1) % segment
        first_index = min(frame_count - 1, loop_start + first_local)
        second_index = min(frame_count - 1, loop_start + second_local)
        alpha = self._smoothstep(0.0, 1.0, frame_pos - math.floor(frame_pos))
        first = self._strip_frame(first_index, frame_width, frame_height, columns)
        second = self._strip_frame(second_index, frame_width, frame_height, columns)
        if first is None or second is None:
            return None
        return Image.blend(first, second, alpha)

    def _strip_frame(self, index: int, frame_width: int, frame_height: int, columns: int) -> Image.Image | None:
        strip = self.compact_wave_strip
        if strip is None:
            return None
        column = index % columns
        row = index // columns
        left = column * frame_width
        top = row * frame_height
        if left + frame_width > strip.width or top + frame_height > strip.height:
            return None
        return strip.crop((left, top, left + frame_width, top + frame_height))

    def _compact_reference_fallback(self, width: int, height: int) -> Image.Image:
        if self.compact_wave_reference is not None:
            return self.compact_wave_reference.resize((width, height), Image.Resampling.LANCZOS)

        scale = 2
        scaled_w = max(2, width * scale)
        scaled_h = max(2, height * scale)
        phase = self.phase / 18.0

        field = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))
        pixels = field.load()
        for y_index in range(scaled_h):
            y = y_index / max(1, scaled_h - 1)
            for x_index in range(scaled_w):
                x = x_index / max(1, scaled_w - 1)
                r, g, b = self._reference_pixel_rgb(x, y, phase)
                pixels[x_index, y_index] = (r, g, b, 255)

        ribs = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))
        rib_draw = ImageDraw.Draw(ribs)
        glow = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        pitch = max(10, int(10.5 * scale))
        offset = int((phase * 2.4) % pitch)
        for x_index in range(-pitch + offset, scaled_w + pitch, pitch):
            t = self._clamp(x_index / max(1, scaled_w - 1), 0.0, 1.0)
            color = self._reference_pill_rgb(t)
            hot = self._mix_rgb(color, (255, 245, 180), 0.55 if t < 0.78 else 0.28)
            shadow_alpha = 84 if t < 0.75 else 118
            rib_draw.rectangle(
                (x_index - int(3.5 * scale), 0, x_index - int(1.0 * scale), scaled_h),
                fill=(0, 12, 16, shadow_alpha),
            )
            glow_draw.rectangle(
                (x_index - int(2.5 * scale), 0, x_index + int(2.5 * scale), scaled_h),
                fill=(*hot, 108),
            )
            rib_draw.line((x_index, 0, x_index, scaled_h), fill=(*hot, 220), width=max(1, scale))
            rib_draw.line(
                (x_index + int(1.6 * scale), 0, x_index + int(1.6 * scale), scaled_h),
                fill=(*self._mix_rgb(color, (255, 255, 255), 0.18), 92),
                width=max(1, scale),
            )

        field = Image.alpha_composite(field, glow.filter(ImageFilter.GaussianBlur(radius=2.2 * scale)))
        field = Image.alpha_composite(field, ribs)

        sheen = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))
        sheen_draw = ImageDraw.Draw(sheen)
        sweep_x = int(((phase * 16) % (scaled_w + 80 * scale)) - 40 * scale)
        sheen_draw.rectangle(
            (sweep_x - 8 * scale, int(4 * scale), sweep_x + 11 * scale, scaled_h - int(4 * scale)),
            fill=(255, 226, 142, 42),
        )
        field = Image.alpha_composite(field, sheen.filter(ImageFilter.GaussianBlur(radius=4.0 * scale)))

        return field.resize((width, height), Image.Resampling.LANCZOS)

    def _finish_compact_wave_frame(self, field: Image.Image, width: int, height: int, *, active: bool = False) -> Image.Image:
        if field.mode != "RGBA":
            field = field.convert("RGBA")
        if field.size != (width, height):
            field = field.resize((width, height), Image.Resampling.LANCZOS)

        hover = self.hover_level
        active_level = 1.0 if active else 0.0
        voice_level = self._clamp(self.display_level, 0.0, 1.0) if active else 0.0
        pulse = 0.5 + 0.5 * math.sin(self.phase / 12.0)
        field = ImageEnhance.Color(field).enhance(1.08 + active_level * 0.18 + voice_level * 0.18 + hover * 0.08)
        field = ImageEnhance.Contrast(field).enhance(
            1.06 + active_level * 0.10 + voice_level * 0.08 + hover * 0.04
        )
        field = ImageEnhance.Brightness(field).enhance(
            1.00 + active_level * (0.06 + pulse * 0.025) + voice_level * 0.13 + hover * 0.05
        )

        soft = field.filter(ImageFilter.GaussianBlur(radius=0.45))
        field = Image.blend(field, soft, 0.12 if active else 0.22)

        if active:
            shine = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            shine_draw = ImageDraw.Draw(shine)
            colors = [(255, 68, 105), (255, 218, 112), (35, 225, 187), (78, 148, 255)]
            for index, color in enumerate(colors):
                cx = width * (0.16 + index * 0.24 + 0.04 * math.sin(self.phase / 17.0 + index * 1.7))
                cy = height * (0.52 + 0.18 * math.sin(self.phase / 21.0 + index * 1.2))
                rx = width * (0.28 + 0.04 * math.sin(self.phase / 25.0 + index))
                ry = height * (0.90 + 0.10 * math.cos(self.phase / 19.0 + index))
                alpha = int(12 + pulse * 7 + voice_level * 28)
                shine_draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(*color, alpha))
            shine = shine.filter(ImageFilter.GaussianBlur(radius=max(3, int(height * 0.16))))
            field = Image.alpha_composite(field, shine)

        glass = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass)
        radius = max(1, height // 2)
        glow_alpha = int(18 + active_level * (24 + pulse * 8) + voice_level * 36 + hover * 26)
        outer_alpha = int((10 if active else 46) + voice_level * 16 + hover * 18)
        inner_alpha = int((0 if active else 22) + voice_level * 6)
        if outer_alpha > 0:
            glass_draw.rounded_rectangle(
                (1, 1, width - 2, height - 2),
                radius=max(1, radius - 1),
                outline=(255, 220, 132, outer_alpha),
                width=1,
            )
        if inner_alpha > 0:
            glass_draw.rounded_rectangle(
                (3, 3, width - 4, height - 4),
                radius=max(1, radius - 4),
                outline=(8, 52, 50, inner_alpha),
                width=1,
            )

        sheen = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        sheen_draw = ImageDraw.Draw(sheen)
        cool_alpha = int(active_level * (5 + pulse * 3) + voice_level * 18)
        for y_index in range(height):
            y_t = y_index / max(1, height - 1)
            top_fade = 1.0 - self._smoothstep(0.08, 0.58, y_t)
            bottom_fade = self._smoothstep(0.52, 0.92, y_t) * (1.0 - self._smoothstep(0.92, 1.0, y_t))
            top_alpha = int(glow_alpha * top_fade)
            bottom_alpha = int(cool_alpha * bottom_fade)
            if top_alpha > 0:
                sheen_draw.line((5, y_index, width - 6, y_index), fill=(255, 237, 177, top_alpha))
            if bottom_alpha > 0:
                sheen_draw.line((6, y_index, width - 7, y_index), fill=(22, 255, 201, bottom_alpha))
        glass = Image.alpha_composite(glass, sheen)
        glass = glass.filter(ImageFilter.GaussianBlur(radius=1.0 if active else 0.8))
        field = Image.alpha_composite(field, glass)

        body_x, body_y, body_width, body_height = self._pill_body_box(width, height)
        if (body_width, body_height) != field.size:
            field = field.resize((body_width, body_height), Image.Resampling.LANCZOS)
        mask = self._compact_mask(body_width, body_height)
        keyed = Image.new("RGBA", (width, height), (*self._rgb(TRANSPARENT_COLOR), 255))
        lift = self._pill_lift_layer(width, height, body_x, body_y, body_width, body_height, active=active)
        keyed = Image.alpha_composite(keyed, lift)
        hover_halo = self._hover_halo(width, height, active=active)
        if hover_halo is not None:
            keyed = Image.alpha_composite(keyed, hover_halo)
        keyed.paste(field, (body_x, body_y), mask)
        return keyed.convert("RGB")

    def _pill_body_box(self, width: int, height: int) -> tuple[int, int, int, int]:
        inset = max(2, min(3, int(round(height * 0.052))))
        body_width = max(1, width - inset * 2)
        body_height = max(1, height - inset * 2)
        return inset, inset, body_width, body_height

    def _hover_halo(self, width: int, height: int, *, active: bool = False) -> Image.Image | None:
        hover = self._clamp(self.hover_level, 0.0, 1.0)
        if hover <= 0.01:
            return None

        bucket = int(round(hover * 12))
        phase_bucket = int((self.phase // (2 if active else 3)) % 120)
        key = (width, height, bucket, phase_bucket)
        cached = self.hover_halo_cache.get(key)
        if cached is not None:
            return cached

        scale = 2
        scaled_w = max(2, width * scale)
        scaled_h = max(2, height * scale)
        key_rgb = self._rgb(TRANSPARENT_COLOR)
        halo = Image.new("RGBA", (scaled_w, scaled_h), (*key_rgb, 255))

        mask = Image.new("L", (scaled_w, scaled_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        pad = max(1, int(1.3 * scale))
        mask_draw.rounded_rectangle(
            (pad, pad, scaled_w - pad - 1, scaled_h - pad - 1),
            radius=max(1, scaled_h // 2 - pad),
            fill=255,
        )
        blur_radius = max(5.0, scaled_h * (0.24 if active else 0.20))
        glow_mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        inner_cut = mask.filter(ImageFilter.GaussianBlur(radius=max(1.5, scaled_h * 0.04)))
        glow_mask = ImageChops.subtract(glow_mask, inner_cut.point(lambda value: int(value * 0.42)))
        glow_mask = glow_mask.point(lambda value: int(value * hover * (0.78 if active else 0.62)))

        colors = [
            (255, 70, 104),
            (255, 215, 107),
            (32, 230, 190),
            (82, 150, 255),
            (219, 93, 255),
        ]
        gradient = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        phase = (self.phase / (72.0 if active else 115.0)) % 1.0
        for x_index in range(scaled_w):
            t = (x_index / max(1, scaled_w - 1) + phase) % 1.0
            segment = t * len(colors)
            left_index = int(math.floor(segment)) % len(colors)
            right_index = (left_index + 1) % len(colors)
            amount = self._smoothstep(0.0, 1.0, segment - math.floor(segment))
            color = self._mix_rgb(colors[left_index], colors[right_index], amount)
            gradient_draw.line((x_index, 0, x_index, scaled_h), fill=(*color, 255))

        glow = Image.new("RGBA", (scaled_w, scaled_h), (*key_rgb, 255))
        glow.paste(gradient, (0, 0), glow_mask)
        shimmer = Image.new("L", (scaled_w, scaled_h), 0)
        shimmer_draw = ImageDraw.Draw(shimmer)
        sweep_x = int(((self.phase * (2.4 if active else 1.2)) % (scaled_w + scaled_h)) - scaled_h)
        shimmer_draw.rounded_rectangle(
            (sweep_x, int(scaled_h * 0.18), sweep_x + int(scaled_w * 0.34), int(scaled_h * 0.82)),
            radius=max(1, scaled_h // 3),
            fill=int(58 * hover),
        )
        shimmer = shimmer.filter(ImageFilter.GaussianBlur(radius=max(4.0, scaled_h * 0.15)))
        glow.paste(Image.new("RGBA", (scaled_w, scaled_h), (255, 247, 198, 255)), (0, 0), shimmer)

        if glow.size != (width, height):
            glow = glow.resize((width, height), Image.Resampling.LANCZOS)
        if len(self.hover_halo_cache) > 160:
            self.hover_halo_cache.clear()
        self.hover_halo_cache[key] = glow
        return glow

    def _compose_active_visual(
        self,
        body: Image.Image,
        width: int,
        height: int,
        body_width: int,
        body_height: int,
    ) -> Image.Image:
        key_rgb = self._rgb(TRANSPARENT_COLOR)
        full = Image.new("RGB", (width, height), key_rgb)
        body_x = max(0, (width - body_width) // 2)
        body_y = max(0, (height - body_height) // 2)

        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            (body_x, body_y, body_x + body_width - 1, body_y + body_height - 1),
            radius=max(1, body_height // 2),
            fill=255,
        )
        blurred = mask.filter(ImageFilter.GaussianBlur(radius=max(2.0, body_height * 0.14)))
        halo_mask = blurred.point(lambda value: int(value * 0.34))

        halo = Image.new("RGB", (width, height), key_rgb)
        halo_draw = ImageDraw.Draw(halo)
        pulse = 0.5 + 0.5 * math.sin(self.phase / 8.0)
        for x_index in range(width):
            x_t = (x_index / max(1, width - 1) + self.phase / 180.0) % 1.0
            ruby = (255, 54, 88)
            gold = (255, 218, 106)
            teal = (31, 229, 190)
            blue = (82, 157, 255)
            if x_t < 0.28:
                color = self._mix_rgb(ruby, gold, x_t / 0.28)
            elif x_t < 0.58:
                color = self._mix_rgb(gold, teal, (x_t - 0.28) / 0.30)
            else:
                color = self._mix_rgb(teal, blue, (x_t - 0.58) / 0.42)
            halo_draw.line(
                (x_index, 0, x_index, height),
                fill=self._mix_rgb(color, (255, 246, 194), 0.22 + 0.18 * pulse),
            )

        full.paste(halo, (0, 0), halo_mask)

        body_mask = self._compact_mask(body_width, body_height)
        full.paste(body.convert("RGB"), (body_x, body_y), body_mask)
        return full

    def _pill_lift_layer(
        self,
        width: int,
        height: int,
        body_x: int,
        body_y: int,
        body_width: int,
        body_height: int,
        *,
        active: bool = False,
    ) -> Image.Image:
        key = (width, height, body_x, body_y, body_width, body_height, 1 if active else 0)
        cached = self.pill_lift_cache.get(key)
        if cached is not None:
            return cached

        scale = 4
        scaled_w = max(2, width * scale)
        scaled_h = max(2, height * scale)
        sx = body_x * scale
        sy = body_y * scale
        sw = max(1, body_width * scale)
        sh = max(1, body_height * scale)
        radius = max(1, sh // 2)

        mask = Image.new("L", (scaled_w, scaled_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((sx, sy, sx + sw - 1, sy + sh - 1), radius=radius, fill=255)

        layer = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))

        contact_mask = Image.new("L", (scaled_w, scaled_h), 0)
        contact_mask.paste(mask, (0, max(1, int(1.35 * scale))))
        contact_mask = contact_mask.filter(ImageFilter.GaussianBlur(radius=max(2.2 * scale, sh * 0.075)))
        contact_mask = contact_mask.point(lambda value: int(value * (0.30 if active else 0.24)))
        layer.paste(Image.new("RGBA", (scaled_w, scaled_h), (0, 5, 8, 255)), (0, 0), contact_mask)

        ambient_mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1.4 * scale, sh * 0.045)))
        ambient_mask = ImageChops.subtract(ambient_mask, mask.point(lambda value: int(value * 0.54)))
        ambient_mask = ambient_mask.point(lambda value: int(value * (0.42 if active else 0.34)))
        ambient = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))
        ambient_draw = ImageDraw.Draw(ambient)
        phase = 0.0
        ruby = (255, 62, 80)
        gold = (255, 220, 122)
        teal = (28, 225, 196)
        blue = (72, 154, 255)
        for x_index in range(scaled_w):
            t = (x_index / max(1, scaled_w - 1) + phase) % 1.0
            if t < 0.28:
                color = self._mix_rgb(ruby, gold, t / 0.28)
            elif t < 0.62:
                color = self._mix_rgb(gold, teal, (t - 0.28) / 0.34)
            else:
                color = self._mix_rgb(teal, blue, (t - 0.62) / 0.38)
            ambient_draw.line((x_index, 0, x_index, scaled_h), fill=(*color, 255))
        layer.paste(ambient, (0, 0), ambient_mask)

        rim_outer = mask.filter(ImageFilter.MaxFilter(max(3, int(1.15 * scale) * 2 + 1)))
        rim_inner = mask.filter(ImageFilter.MinFilter(max(3, int(0.75 * scale) * 2 + 1)))
        rim_mask = ImageChops.subtract(rim_outer, rim_inner)
        rim_mask = rim_mask.filter(ImageFilter.GaussianBlur(radius=max(0.55 * scale, 1.0)))
        rim_mask = rim_mask.point(lambda value: int(value * (0.24 if active else 0.18)))
        layer.paste(Image.new("RGBA", (scaled_w, scaled_h), (255, 235, 178, 255)), (0, 0), rim_mask)

        top_highlight = Image.new("L", (scaled_w, scaled_h), 0)
        top_draw = ImageDraw.Draw(top_highlight)
        top_draw.rounded_rectangle(
            (sx + int(1.4 * scale), sy + int(0.9 * scale), sx + sw - int(1.4 * scale), sy + int(5.2 * scale)),
            radius=max(1, int(4 * scale)),
            fill=62 if active else 44,
        )
        top_highlight = top_highlight.filter(ImageFilter.GaussianBlur(radius=max(1.2 * scale, sh * 0.025)))
        layer.paste(Image.new("RGBA", (scaled_w, scaled_h), (255, 248, 207, 255)), (0, 0), top_highlight)

        if layer.size != (width, height):
            layer = layer.resize((width, height), Image.Resampling.LANCZOS)
        if len(self.pill_lift_cache) > 80:
            self.pill_lift_cache.clear()
        self.pill_lift_cache[key] = layer
        return layer

    def _compact_mask(self, width: int, height: int) -> Image.Image:
        key = (width, height)
        mask = self.compact_mask_cache.get(key)
        if mask is not None:
            return mask
        scale = 4
        scaled_w = max(2, width * scale)
        scaled_h = max(2, height * scale)
        mask = Image.new("L", (scaled_w, scaled_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, scaled_w - 1, scaled_h - 1), radius=max(1, scaled_h // 2), fill=255)
        mask = mask.resize((width, height), Image.Resampling.LANCZOS)
        self.compact_mask_cache[key] = mask
        return mask

    def _reference_pixel_rgb(self, x: float, y: float, phase: float) -> tuple[int, int, int]:
        teal = self._smoothstep(0.40, 0.96, x)
        warm = 1.0 - self._smoothstep(0.46, 0.98, x)
        base = self._mix_rgb((16, 60, 57), (6, 38, 45), teal)

        red_center = 0.67 - 0.28 * x + 0.045 * math.sin(phase * 0.55 + x * 9.0)
        red = math.exp(-((y - red_center) ** 2) / 0.035) * warm
        red += 0.42 * math.exp(-((x - 0.22) ** 2) / 0.040) * math.exp(-((y - 0.44) ** 2) / 0.090)

        gold_center = 0.46 + 0.12 * math.sin(phase * 0.32 + x * 7.0)
        gold = math.exp(-((x - 0.53) ** 2) / 0.055) * math.exp(-((y - gold_center) ** 2) / 0.150)
        gold += warm * self._smoothstep(0.52, 1.0, y) * 0.62

        cream_center = 0.24 + 0.30 * x + 0.06 * math.sin(phase * 0.45 + x * 11.0)
        cream = math.exp(-((y - cream_center) ** 2) / 0.080) * (1.0 - self._smoothstep(0.34, 0.80, x))
        left_glow = (1.0 - self._smoothstep(0.02, 0.22, x)) * 0.56

        result = base
        result = self._mix_rgb(result, (255, 224, 126), self._clamp(left_glow + gold * 0.55, 0.0, 0.92))
        result = self._mix_rgb(result, (255, 31, 66), self._clamp(red * 0.88, 0.0, 0.90))
        result = self._mix_rgb(result, (255, 199, 103), self._clamp(gold * 0.74 + cream * 0.58, 0.0, 0.88))
        result = self._mix_rgb(result, (18, 138, 119), self._clamp(teal * 0.44, 0.0, 0.55))
        result = self._mix_rgb(result, (5, 28, 39), self._clamp(self._smoothstep(0.78, 1.0, x) * 0.58, 0.0, 0.70))
        return result

    def _reference_pill_rgb(self, t: float) -> tuple[int, int, int]:
        stops = [
            (0.0, (255, 228, 132)),
            (0.14, (255, 38, 67)),
            (0.34, (156, 8, 35)),
            (0.53, (255, 214, 113)),
            (0.68, (255, 178, 91)),
            (0.82, (30, 181, 139)),
            (1.0, (7, 76, 70)),
        ]
        for (left_t, left_color), (right_t, right_color) in zip(stops, stops[1:]):
            if left_t <= t <= right_t:
                local = (t - left_t) / max(0.001, right_t - left_t)
                return self._mix_rgb(left_color, right_color, local)
        return stops[-1][1]

    def _mix_rgb(self, left: tuple[int, int, int], right: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        amount = self._clamp(amount, 0.0, 1.0)
        return (
            int(left[0] + (right[0] - left[0]) * amount),
            int(left[1] + (right[1] - left[1]) * amount),
            int(left[2] + (right[2] - left[2]) * amount),
        )

    def _smoothstep(self, edge0: float, edge1: float, value: float) -> float:
        x = self._clamp((value - edge0) / max(0.0001, edge1 - edge0), 0.0, 1.0)
        return x * x * (3 - 2 * x)

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _rgb(self, color: str) -> tuple[int, int, int]:
        value = color.lstrip("#")
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)

    def _hex_rgba(self, color: str, alpha: int) -> tuple[int, int, int, int]:
        return (*self._rgb(color), int(self._clamp(alpha, 0, 255)))

    def _open_context_menu_from_event(self, event: tk.Event | None = None) -> str:
        x = int(getattr(event, "x_root", self.root.winfo_rootx() + self.current_width // 2))
        y = int(getattr(event, "y_root", self.root.winfo_rooty()))
        self._open_context_menu(x, y)
        return "break"

    def _open_context_menu(self, x_root: int, y_root: int) -> None:
        self._close_context_menu()
        width = 318
        height = 206
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.attributes("-alpha", 0.98)
        window.configure(bg=TRANSPARENT_COLOR)
        try:
            window.attributes("-transparentcolor", TRANSPARENT_COLOR)
        except Exception:
            pass

        left, top, right, bottom = self._logical_work_area()
        x = min(max(left + 8, x_root - width // 2), right - width - 8)
        preferred_y = y_root - height - 12
        y = preferred_y if preferred_y > top + 8 else min(bottom - height - 8, y_root + 12)
        window.geometry(f"{width}x{height}+{x}+{y}")
        canvas = tk.Canvas(window, width=width, height=height, bg=TRANSPARENT_COLOR, bd=0, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self.context_menu_window = window
        self.context_menu_canvas = canvas
        self.context_menu_hover = ""

        window.bind("<Escape>", lambda _event: self._close_context_menu())
        window.bind("<FocusOut>", lambda _event: window.after(80, self._close_context_menu))
        window.bind("<Destroy>", lambda event: self._forget_context_menu(event), add="+")
        canvas.bind("<Motion>", self._context_menu_motion)
        canvas.bind("<Leave>", self._context_menu_leave)
        canvas.bind("<Button-1>", self._context_menu_click)
        canvas.bind("<Button-3>", lambda _event: self._close_context_menu())

        window.update_idletasks()
        self._apply_window_region(window, width, height, 28)
        self._draw_context_menu()
        window.after(30, window.focus_force)
        self._animate_context_menu()

    def _forget_context_menu(self, event: tk.Event | None = None) -> None:
        if event is not None and event.widget is not self.context_menu_window:
            return
        self.context_menu_window = None
        self.context_menu_canvas = None
        self.context_menu_photo = None
        self.context_menu_hover = ""
        self.context_menu_after_id = None

    def _close_context_menu(self) -> None:
        if self.context_menu_after_id and self.context_menu_window is not None:
            try:
                self.context_menu_window.after_cancel(self.context_menu_after_id)
            except Exception:
                pass
        window = self.context_menu_window
        self.context_menu_after_id = None
        self.context_menu_window = None
        self.context_menu_canvas = None
        self.context_menu_photo = None
        self.context_menu_hover = ""
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass

    def _context_menu_motion(self, event: tk.Event) -> None:
        action = self._context_menu_action_at(int(event.y))
        if action != self.context_menu_hover:
            self.context_menu_hover = action
            self._draw_context_menu()

    def _context_menu_leave(self, _event: tk.Event | None = None) -> None:
        if self.context_menu_hover:
            self.context_menu_hover = ""
            self._draw_context_menu()

    def _context_menu_click(self, event: tk.Event) -> str:
        action = self._context_menu_action_at(int(event.y))
        self._close_context_menu()
        if action == "settings":
            self.open_settings()
        elif action == "history":
            self.open_history()
        elif action == "scratchpad":
            self.open_scratchpad()
        return "break"

    def _context_menu_action_at(self, y: int) -> str:
        if 18 <= y <= 66:
            return "settings"
        if 78 <= y <= 126:
            return "history"
        if 138 <= y <= 186:
            return "scratchpad"
        return ""

    def _animate_context_menu(self) -> None:
        if self.context_menu_window is None or self.context_menu_canvas is None:
            return
        self._draw_context_menu()
        self.context_menu_after_id = self.context_menu_window.after(34, self._animate_context_menu)

    def _draw_context_menu(self) -> None:
        canvas = self.context_menu_canvas
        if canvas is None:
            return
        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 1:
            width = int(float(canvas.cget("width") or 260))
        if height <= 1:
            height = int(float(canvas.cget("height") or 126))
        width = max(1, width)
        height = max(1, height)
        image = self._context_menu_background(width, height, self.context_menu_hover)
        self.context_menu_photo = ImageTk.PhotoImage(image)
        canvas.delete("all")
        canvas.create_image(0, 0, image=self.context_menu_photo, anchor="nw")
        settings_active = self.context_menu_hover == "settings"
        history_active = self.context_menu_hover == "history"
        scratchpad_active = self.context_menu_hover == "scratchpad"
        palette = self._settings_palette(self._settings_theme_key())
        rows = [
            ("settings", 42, "Settings", "Controls, providers, themes", settings_active, self._draw_gear_icon),
            ("history", 102, "History", "Private local transcript archive", history_active, self._draw_history_icon),
            ("scratchpad", 162, "Scratchpad", "Tabbed local notes", scratchpad_active, self._draw_scratchpad_icon),
        ]
        for _name, cy, title, subtitle, active, icon_drawer in rows:
            icon_drawer(canvas, 48, cy, active)
            canvas.create_text(
                82,
                cy - 8,
                text=title,
                anchor="w",
                fill=palette["warm"] if active else palette["text"],
                font=("Segoe UI Semibold", 12),
            )
            canvas.create_text(
                82,
                cy + 10,
                text=subtitle,
                anchor="w",
                fill=palette["muted"] if not active else "#d8fdf2",
                font=("Segoe UI", 9),
            )

    def _context_menu_background(self, width: int, height: int, hover: str) -> Image.Image:
        key_rgb = self._rgb(TRANSPARENT_COLOR)
        palette = self._settings_palette(self._settings_theme_key())
        light = palette["mode"] == "light"
        field = self._compact_wave_frame(width, height, active=True) or self._compact_reference_fallback(width, height)
        if field.mode != "RGBA":
            field = field.convert("RGBA")
        field = ImageEnhance.Color(field).enhance(1.16)
        field = ImageEnhance.Contrast(field).enhance(1.06)
        field = field.filter(ImageFilter.GaussianBlur(radius=0.85))

        panel = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=28, fill=255)
        panel.paste(field, (0, 0), mask)

        veil_color = (246, 251, 248, 154) if light else (3, 12, 15, 170)
        veil = Image.new("RGBA", (width, height), veil_color)
        panel = Image.alpha_composite(panel, veil)
        draw = ImageDraw.Draw(panel)
        pulse = 0.5 + 0.5 * math.sin(self.phase / 16.0)

        wash = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        wash_draw = ImageDraw.Draw(wash)
        wash_draw.rounded_rectangle((8, 8, width - 9, height - 9), radius=24, fill=(0, 0, 0, 44 if light else 86))
        wash_draw.rounded_rectangle((12, 12, 112, height - 13), radius=21, fill=(255, 75, 33, 34))
        wash_draw.rounded_rectangle((width - 118, 12, width - 13, height - 13), radius=21, fill=(0, 210, 205, 26))
        panel = Image.alpha_composite(panel, wash)
        draw = ImageDraw.Draw(panel)

        rows = (("settings", 18), ("history", 78), ("scratchpad", 138))
        for name, top in rows:
            active = hover == name
            if light:
                fill = (255, 255, 255, 230 if active else 206)
            else:
                fill = (8, 19, 21, 242 if active else 228)
            outline = self._hex_rgba(palette["accent"], int(92 + pulse * 38)) if active else (197, 235, 222, 42)
            draw.rounded_rectangle((14, top, width - 14, top + 48), radius=15, fill=fill, outline=outline, width=1)
            draw.line((30, top + 47, width - 30, top + 47), fill=(255, 225, 158, 18 if not active else 34), width=1)
            if active:
                glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.rounded_rectangle(
                    (12, top - 1, width - 12, top + 49),
                    radius=17,
                    outline=self._hex_rgba(palette["warm"], 96),
                    width=2,
                )
                panel = Image.alpha_composite(panel, glow.filter(ImageFilter.GaussianBlur(radius=1.6)))
                draw = ImageDraw.Draw(panel)
        draw.rounded_rectangle(
            (1, 1, width - 2, height - 2),
            radius=28,
            outline=self._hex_rgba(palette["accent"], int(80 + pulse * 18)),
            width=1,
        )
        draw.rounded_rectangle((7, 7, width - 8, 36), radius=20, fill=(255, 255, 255, 24 if light else 8))

        halo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        halo_draw = ImageDraw.Draw(halo)
        halo_draw.rounded_rectangle((2, 2, width - 3, height - 3), radius=28, outline=self._hex_rgba(palette["warm"], 58), width=2)
        panel = Image.alpha_composite(panel, halo.filter(ImageFilter.GaussianBlur(radius=1.5)))
        keyed = Image.new("RGBA", (width, height), (*key_rgb, 255))
        keyed.paste(panel, (0, 0), panel.split()[-1])
        return keyed.convert("RGB")

    def _draw_gear_icon(self, canvas: tk.Canvas, cx: int, cy: int, active: bool) -> None:
        color = "#ffe39a" if active else "#cfe8e1"
        for index in range(8):
            angle = math.tau * index / 8.0
            x1 = cx + math.cos(angle) * 9
            y1 = cy + math.sin(angle) * 9
            x2 = cx + math.cos(angle) * 13
            y2 = cy + math.sin(angle) * 13
            canvas.create_line(x1, y1, x2, y2, fill=color, width=2, capstyle="round")
        canvas.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, outline=color, width=2)
        canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, outline=color, width=2)

    def _draw_history_icon(self, canvas: tk.Canvas, cx: int, cy: int, active: bool) -> None:
        color = "#ffe39a" if active else "#cfe8e1"
        canvas.create_arc(cx - 14, cy - 14, cx + 14, cy + 14, start=42, extent=286, style="arc", outline=color, width=2)
        canvas.create_line(cx - 11, cy - 8, cx - 16, cy - 8, fill=color, width=2, capstyle="round")
        canvas.create_line(cx - 11, cy - 8, cx - 11, cy - 13, fill=color, width=2, capstyle="round")
        canvas.create_line(cx, cy, cx, cy - 8, fill=color, width=2, capstyle="round")
        canvas.create_line(cx, cy, cx + 7, cy + 4, fill=color, width=2, capstyle="round")

    def _draw_scratchpad_icon(self, canvas: tk.Canvas, cx: int, cy: int, active: bool) -> None:
        color = "#ffe39a" if active else "#cfe8e1"
        muted = "#ffb45d" if active else "#6fc8be"
        canvas.create_rectangle(cx - 12, cy - 15, cx + 12, cy + 15, outline=color, width=2)
        canvas.create_line(cx - 6, cy - 7, cx + 6, cy - 7, fill=muted, width=2, capstyle="round")
        canvas.create_line(cx - 6, cy, cx + 7, cy, fill=color, width=2, capstyle="round")
        canvas.create_line(cx - 6, cy + 7, cx + 4, cy + 7, fill=color, width=2, capstyle="round")

    def _focus_utility_window(self, name: str) -> bool:
        window = self.utility_windows.get(name)
        if not window:
            return False
        try:
            if not window.winfo_exists():
                self.utility_windows.pop(name, None)
                return False
            window.deiconify()
            window.attributes("-topmost", True)
            window.lift()
            window.focus_force()
            return True
        except tk.TclError:
            self.utility_windows.pop(name, None)
            return False

    def _parse_geometry_size(self, geometry: str) -> tuple[int, int]:
        raw = str(geometry).split("+", 1)[0].strip()
        if "x" not in raw:
            return 720, 520
        left, right = raw.lower().split("x", 1)
        try:
            return max(280, int(left)), max(180, int(right))
        except ValueError:
            return 720, 520

    def _utility_geometry(self, geometry: str) -> str:
        width, height = self._parse_geometry_size(geometry)
        left, top, right, bottom = self._logical_work_area()
        x = left + max(8, ((right - left) - width) // 2)
        y = top + max(8, ((bottom - top) - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _apply_glass_effect(self, window: tk.Toplevel, bg: str) -> None:
        window.configure(bg=bg)
        try:
            window.attributes("-alpha", 0.965)
        except Exception:
            pass
        try:
            window.attributes("-toolwindow", True)
        except Exception:
            pass
        try:
            hwnd = int(window.winfo_id())
            dwm = ctypes.windll.dwmapi
            enabled = ctypes.c_int(1)
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(enabled), ctypes.sizeof(enabled))
            backdrop = ctypes.c_int(3)
            dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop))
        except Exception:
            pass

    def _bind_utility_drag_handle(self, window: tk.Toplevel, *widgets: tk.Widget) -> None:
        def press(event: tk.Event) -> None:
            self.utility_drag_origin = (
                int(getattr(event, "x_root", window.winfo_pointerx())),
                int(getattr(event, "y_root", window.winfo_pointery())),
                int(window.winfo_x()),
                int(window.winfo_y()),
            )

        def drag(event: tk.Event) -> None:
            if self.utility_drag_origin is None:
                return
            start_x, start_y, window_x, window_y = self.utility_drag_origin
            pointer_x = int(getattr(event, "x_root", window.winfo_pointerx()))
            pointer_y = int(getattr(event, "y_root", window.winfo_pointery()))
            window.geometry(f"+{window_x + pointer_x - start_x}+{window_y + pointer_y - start_y}")

        def release(_event: tk.Event) -> None:
            self.utility_drag_origin = None

        for widget in widgets:
            widget.bind("<ButtonPress-1>", press, add="+")
            widget.bind("<B1-Motion>", drag, add="+")
            widget.bind("<ButtonRelease-1>", release, add="+")

    def _make_glass_titlebar(self, window: tk.Toplevel, title: str, bg: str, fg: str = "#eef8f3") -> tk.Frame:
        bar = tk.Frame(window, bg=bg, height=44, bd=0, highlightthickness=0)
        bar.pack(fill="x", padx=14, pady=(12, 0))
        label = tk.Label(
            bar,
            text=title,
            bg=bg,
            fg=fg,
            font=("Segoe UI Semibold", 12),
            anchor="w",
        )
        label.pack(side="left", fill="x", expand=True)
        close = tk.Button(
            bar,
            text="X",
            command=window.destroy,
            bg="#16282d",
            fg="#f5e7bd",
            activebackground="#22413f",
            activeforeground="#ffffff",
            bd=0,
            highlightthickness=0,
            font=("Segoe UI Semibold", 9),
            width=3,
            cursor="hand2",
        )
        close.pack(side="right", padx=(8, 0))
        self._bind_utility_drag_handle(window, bar, label)
        return bar

    def _utility_window(self, name: str, title: str, geometry: str, *, bg: str) -> tk.Toplevel | None:
        if self._focus_utility_window(name):
            return None
        window = tk.Toplevel(self.root)
        window.title(title)
        window.overrideredirect(True)
        window.geometry(self._utility_geometry(geometry))
        window.resizable(False, False)
        self._apply_glass_effect(window, bg)
        try:
            self._style_settings_widgets(window, self._settings_palette(self._settings_theme_key()))
        except Exception:
            pass
        window.attributes("-topmost", True)
        self.utility_windows[name] = window

        def forget(event: tk.Event | None = None) -> None:
            if event is not None and event.widget is not window:
                return
            self.utility_windows.pop(name, None)

        window.bind("<Destroy>", forget, add="+")
        window.bind("<Escape>", lambda _event: window.destroy(), add="+")
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        try:
            window.iconbitmap(str(ensure_icon_file()))
        except Exception:
            pass
        def apply_region_once() -> None:
            try:
                window.update_idletasks()
                self._apply_window_region(window, window.winfo_width(), window.winfo_height(), 28)
            except Exception:
                pass

        window.after(80, apply_region_once)
        return window

    def _open_settings_legacy(self) -> None:
        self.force_visible()
        window = self._utility_window("settings", "Talk Dat! Settings", "820x680", bg="#f5f6f8")
        if window is None:
            return
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(window)
        notebook.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        general = ttk.Frame(notebook, padding=14)
        dictation = ttk.Frame(notebook, padding=14)
        hotkeys_tab = ttk.Frame(notebook, padding=14)
        dictionary_tab = ttk.Frame(notebook, padding=14)
        snippets_tab = ttk.Frame(notebook, padding=14)
        transforms_tab = ttk.Frame(notebook, padding=14)
        notebook.add(general, text="General")
        notebook.add(dictation, text="Dictation")
        notebook.add(hotkeys_tab, text="Hotkeys")
        notebook.add(dictionary_tab, text="Dictionary")
        notebook.add(snippets_tab, text="Snippets")
        notebook.add(transforms_tab, text="Transforms")

        def add_row(parent: ttk.Frame, row: int, label: str, widget: tk.Widget) -> None:
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
            widget.grid(row=row, column=1, sticky="ew", pady=5)
            parent.columnconfigure(1, weight=1)

        deepgram = self.config.setdefault("deepgram", {})
        cleanup = self.config.setdefault("cleanup", {})
        privacy = self.config.setdefault("privacy", {})
        dictation_config = self.config.setdefault("dictation", {})
        transforms = self.config.setdefault("transforms", {})
        ollama = transforms.setdefault("ollama", {})

        key_var = tk.StringVar(value=str(self.config.get("deepgram", {}).get("api_key", "")))
        key_entry = ttk.Entry(general, textvariable=key_var, show="*", width=70)
        add_row(general, 0, "Deepgram API key", key_entry)

        model_var = tk.StringVar(value=str(deepgram.get("model", "nova-3")))
        model_options = [
            "nova-3",
            "nova-3-general",
            "nova-3-medical",
            "nova-2",
            "nova-2-general",
            "nova-2-meeting",
            "nova-2-phonecall",
            "nova-2-finance",
            "nova-2-conversationalai",
            "nova-2-voicemail",
            "nova-2-video",
            "nova-2-medical",
            "nova-2-drivethru",
            "nova-2-automotive",
            "nova-2-atc",
            "enhanced",
            "enhanced-general",
            "enhanced-meeting",
            "enhanced-phonecall",
            "enhanced-finance",
            "base",
            "base-general",
            "base-meeting",
            "base-phonecall",
            "base-finance",
            "base-conversationalai",
            "base-voicemail",
            "base-video",
            "whisper",
            "whisper-tiny",
            "whisper-base",
            "whisper-small",
            "whisper-medium",
            "whisper-large",
            "flux-general-en",
            "flux-general-multi",
        ]
        model_box = ttk.Combobox(general, textvariable=model_var, values=model_options, width=32)
        add_row(general, 1, "Deepgram model", model_box)

        language_var = tk.StringVar(value=str(deepgram.get("language", "en-US")))
        add_row(general, 2, "Language", ttk.Entry(general, textvariable=language_var, width=20))

        level_var = tk.StringVar(value=str(cleanup.get("level", "medium")))
        level_box = ttk.Combobox(general, textvariable=level_var, values=["none", "light", "medium", "high"], width=20)
        add_row(general, 3, "Cleanup level", level_box)

        save_history_var = tk.BooleanVar(value=bool(privacy.get("save_history", True)))
        play_sounds_var = tk.BooleanVar(value=bool(dictation_config.get("play_sounds", True)))
        auto_paste_var = tk.BooleanVar(value=bool(dictation_config.get("auto_paste", True)))
        smart_space_var = tk.BooleanVar(value=bool(dictation_config.get("smart_leading_space", True)))
        ttk.Checkbutton(general, text="Save local transcript history", variable=save_history_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Checkbutton(general, text="Play start/stop sounds", variable=play_sounds_var).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Checkbutton(general, text="Auto paste transcript", variable=auto_paste_var).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Checkbutton(general, text="Smart leading space", variable=smart_space_var).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Label(general, text=f"Config: {config_path()}", wraplength=720).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(18, 0)
        )

        def string_int(value: Any) -> tk.StringVar:
            return tk.StringVar(value=str(value))

        tail_var = string_int(dictation_config.get("tail_capture_ms", 520))
        debounce_var = string_int(dictation_config.get("hold_debounce_ms", 50))
        hold_max_var = string_int(dictation_config.get("hold_max_seconds", 30 * 60))
        no_speech_var = string_int(dictation_config.get("hold_no_speech_timeout_seconds", 120))
        silence_var = string_int(dictation_config.get("hold_silence_timeout_seconds", 300))
        add_row(dictation, 0, "Tail capture ms", ttk.Entry(dictation, textvariable=tail_var, width=12))
        add_row(dictation, 1, "Hold debounce ms", ttk.Entry(dictation, textvariable=debounce_var, width=12))
        add_row(dictation, 2, "Hold max seconds", ttk.Entry(dictation, textvariable=hold_max_var, width=12))
        add_row(dictation, 3, "No-speech guard seconds", ttk.Entry(dictation, textvariable=no_speech_var, width=12))
        add_row(dictation, 4, "Silence guard seconds", ttk.Entry(dictation, textvariable=silence_var, width=12))

        hotkey_entries: dict[str, tk.StringVar] = {}
        hotkey_labels = [
            ("push_to_talk", "Push-to-talk"),
            ("hands_free", "Hands-free toggle"),
            ("command_mode", "Command mode"),
            ("panic", "Panic stop"),
            ("cancel", "Cancel"),
            ("paste_last", "Paste last"),
            ("copy_last", "Copy last"),
            ("polish", "Polish"),
            ("prompt_engineer", "Prompt engineer"),
            ("turn_to_list", "Turn to list"),
            ("view_diff", "Copy cleanup diff"),
            ("scratchpad", "Scratchpad"),
        ]
        for row, (action, label) in enumerate(hotkey_labels):
            var = tk.StringVar(value=self._format_shortcuts(self.config.get("hotkeys", {}).get(action, [])))
            hotkey_entries[action] = var
            add_row(hotkeys_tab, row, label, ttk.Entry(hotkeys_tab, textvariable=var, width=48))

        words_text = tk.Text(dictionary_tab, height=12, wrap="word", font=("Consolas", 10))
        words_text.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        words_text.insert("1.0", "\n".join(str(word) for word in self.config.get("dictionary", {}).get("words", [])))
        replacements_text = tk.Text(dictionary_tab, height=12, wrap="word", font=("Consolas", 10))
        replacements_text.grid(row=0, column=1, sticky="nsew")
        replacements_text.insert(
            "1.0",
            json.dumps(self.config.get("dictionary", {}).get("replacements", []), indent=2, ensure_ascii=False),
        )
        ttk.Label(dictionary_tab, text="Words, one per line").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(dictionary_tab, text="Replacements JSON").grid(row=1, column=1, sticky="w", pady=(6, 0))
        dictionary_tab.columnconfigure(0, weight=1)
        dictionary_tab.columnconfigure(1, weight=1)
        dictionary_tab.rowconfigure(0, weight=1)

        snippets_text = tk.Text(snippets_tab, height=18, wrap="word", font=("Consolas", 10))
        snippets_text.pack(fill="both", expand=True)
        snippets_text.insert("1.0", json.dumps(self.config.get("snippets", []), indent=2, ensure_ascii=False))

        transforms_enabled_var = tk.BooleanVar(value=bool(transforms.get("enabled", True)))
        ollama_enabled_var = tk.BooleanVar(value=bool(ollama.get("enabled", False)))
        ollama_url_var = tk.StringVar(value=str(ollama.get("url", "http://localhost:11434/api/generate")))
        ollama_model_var = tk.StringVar(value=str(ollama.get("model", "llama3.1")))
        ttk.Checkbutton(transforms_tab, text="Enable transforms", variable=transforms_enabled_var).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Checkbutton(transforms_tab, text="Use Ollama for rewrites", variable=ollama_enabled_var).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=6
        )
        add_row(transforms_tab, 2, "Ollama URL", ttk.Entry(transforms_tab, textvariable=ollama_url_var, width=60))
        add_row(transforms_tab, 3, "Ollama model", ttk.Entry(transforms_tab, textvariable=ollama_model_var, width=30))

        button_row = ttk.Frame(window)
        button_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        save_status_var = tk.StringVar(value="")

        def parse_int(var: tk.StringVar, fallback: int, low: int, high: int) -> int:
            try:
                value = int(str(var.get()).strip())
            except ValueError:
                value = fallback
            return int(self._clamp(value, low, high))

        def parse_json_list(widget: tk.Text, label: str) -> list[Any]:
            raw = widget.get("1.0", "end-1c").strip()
            if not raw:
                return []
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                raise ValueError(f"{label} must be valid JSON.")
            if not isinstance(value, list):
                raise ValueError(f"{label} must be a JSON list.")
            return value

        def save() -> None:
            try:
                replacements = parse_json_list(replacements_text, "Replacements")
                snippets = parse_json_list(snippets_text, "Snippets")
            except ValueError as error:
                save_status_var.set(str(error))
                self.set_state("error", "Settings not saved.", str(error))
                return

            deepgram["api_key"] = key_var.get().strip()
            deepgram["model"] = model_var.get().strip() or "nova-3"
            deepgram["language"] = language_var.get().strip() or "en-US"
            cleanup["level"] = level_var.get().strip() or "medium"
            privacy["save_history"] = bool(save_history_var.get())
            dictation_config["play_sounds"] = bool(play_sounds_var.get())
            dictation_config["auto_paste"] = bool(auto_paste_var.get())
            dictation_config["smart_leading_space"] = bool(smart_space_var.get())
            dictation_config["tail_capture_ms"] = parse_int(tail_var, 520, 0, 3000)
            dictation_config["hold_debounce_ms"] = parse_int(debounce_var, 50, 0, 1000)
            dictation_config["hold_max_seconds"] = parse_int(hold_max_var, 30 * 60, 5, 60 * 60)
            dictation_config["hold_no_speech_timeout_seconds"] = parse_int(no_speech_var, 120, 1, 60 * 60)
            dictation_config["hold_silence_timeout_seconds"] = parse_int(silence_var, 300, 1, 60 * 60)
            self.config.setdefault("hotkeys", {}).update(
                {action: self._parse_shortcuts(var.get()) for action, var in hotkey_entries.items()}
            )
            dictionary = self.config.setdefault("dictionary", {})
            dictionary["words"] = [
                line.strip()
                for line in words_text.get("1.0", "end-1c").splitlines()
                if line.strip()
            ]
            dictionary["replacements"] = replacements
            self.config["snippets"] = snippets
            transforms["enabled"] = bool(transforms_enabled_var.get())
            ollama["enabled"] = bool(ollama_enabled_var.get())
            ollama["url"] = ollama_url_var.get().strip() or "http://localhost:11434/api/generate"
            ollama["model"] = ollama_model_var.get().strip() or "llama3.1"
            callback = self.callbacks.get("save_settings")
            if callback:
                callback()
            save_status_var.set("Saved.")
            self.set_state("captured", "Settings saved.", f"Saved to {config_path()}")

        ttk.Button(button_row, text="Save", command=save, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="Status", command=self.open_status, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="History", command=self.open_history, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="Scratchpad", command=self.open_scratchpad, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Label(button_row, textvariable=save_status_var, style="Flow.Muted.TLabel").pack(side="left", padx=(4, 0))
        ttk.Button(button_row, text="Close", command=window.destroy, style="Flow.TButton").pack(side="right")

    def _settings_theme_options(self) -> list[str]:
        return [f"{family} {mode}" for family in SETTINGS_THEME_FAMILIES for mode in ("Dark", "Light")]

    def _settings_theme_key(self, value: str | None = None) -> str:
        raw = str(value or "").strip()
        if not raw:
            raw = str(self.config.setdefault("ui", {}).get("settings_theme") or self.config.get("ui", {}).get("theme") or "Flow Dark")
        aliases = {
            "dark": "Flow Dark",
            "light": "Flow Light",
            "flow": "Flow Dark",
            "noir": "Aqua Noir Dark",
        }
        normalized = aliases.get(raw.lower(), raw)
        options = self._settings_theme_options()
        for option in options:
            if option.lower() == normalized.lower():
                return option
        return "Flow Light" if normalized.lower().endswith("light") else "Flow Dark"

    def _settings_palette(self, theme: str) -> dict[str, str]:
        theme = self._settings_theme_key(theme)
        family = theme.removesuffix(" Dark").removesuffix(" Light")
        mode = "Light" if theme.endswith("Light") else "Dark"
        base = SETTINGS_THEME_PALETTES.get(family, SETTINGS_THEME_PALETTES["Flow"]).get(mode)
        if base is None:
            base = SETTINGS_THEME_PALETTES["Flow"][mode]
        palette = dict(base)
        palette["name"] = theme
        palette["mode"] = mode.lower()
        return palette

    def _provider_status_text(self, provider_id: str) -> str:
        provider = PROVIDER_BY_ID.get(provider_id, PROVIDER_BY_ID["deepgram"])
        if provider.api_kind == "external":
            details = provider.notes or "Adapter pending. The settings are saved, but transcription is not wired yet."
            return f"Adapter pending: {details}"
        if provider.id == "deepgram":
            return "Wired: live streaming transcription. Starts only after a trigger or pill click."
        if provider.api_kind == "openai_batch":
            return "Wired: batch transcription through an OpenAI-compatible /v1/audio/transcriptions endpoint."
        if provider.id == "elevenlabs":
            return "Wired: batch speech-to-text conversion endpoint."
        if provider.id == "assemblyai":
            return "Wired: batch upload, transcript job creation, and polling."
        if provider.id == "google_gemini":
            return "Wired: batch audio understanding through Gemini generateContent."
        return "Registered provider. Check docs and adapter status before relying on it."

    def _style_settings_widgets(self, window: tk.Toplevel, palette: dict[str, str]) -> None:
        style = ttk.Style(window)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Flow.TNotebook", background=palette["bg"], borderwidth=0, tabmargins=(0, 2, 0, 0))
        style.configure(
            "Flow.TNotebook.Tab",
            background=palette["button"],
            foreground=palette["muted"],
            padding=(10, 9),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Flow.TNotebook.Tab",
            background=[("selected", palette["surface"])],
            foreground=[("selected", palette["text"])],
        )
        style.configure("Flow.TFrame", background=palette["panel"])
        style.configure("Flow.TLabel", background=palette["panel"], foreground=palette["text"])
        style.configure("Flow.Muted.TLabel", background=palette["panel"], foreground=palette["muted"])
        style.configure("Flow.TCheckbutton", background=palette["panel"], foreground=palette["text"])
        style.map("Flow.TCheckbutton", background=[("active", palette["panel"])])
        style.configure("Flow.TButton", background=palette["button"], foreground=palette["text"], padding=(10, 7))
        style.map("Flow.TButton", background=[("active", palette["select"])])
        style.configure(
            "Flow.TEntry",
            fieldbackground=palette["field"],
            foreground=palette["text"],
            insertcolor=palette["text"],
            borderwidth=1,
        )
        style.configure(
            "Flow.TCombobox",
            fieldbackground=palette["field"],
            background=palette["button"],
            foreground=palette["text"],
            arrowcolor=palette["accent"],
        )
        style.configure(
            "Flow.Horizontal.TScale",
            background=palette["panel"],
            troughcolor=palette["field"],
            borderwidth=0,
        )

    def _draw_settings_header(
        self,
        canvas: tk.Canvas,
        width: int,
        height: int,
        theme: str,
        *,
        title: str = "Talk Dat!",
        subtitle: str | None = None,
    ) -> None:
        width = max(320, int(width))
        height = max(72, int(height))
        palette = self._settings_palette(theme)
        light = palette["mode"] == "light"
        key_rgb = self._rgb(TRANSPARENT_COLOR)
        field = Image.new("RGBA", (width, height), (*key_rgb, 255))
        panel = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(panel)
        glass_fill = (255, 255, 255, 214) if light else (7, 18, 20, 224)
        stroke = self._hex_rgba(palette["stroke"], 130 if light else 118)
        draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=24, fill=glass_fill, outline=stroke, width=1)

        accent_width = min(210, max(150, width // 4))
        accent = self._compact_wave_frame(accent_width, max(42, height - 30), active=True) or self._compact_reference_fallback(
            accent_width, max(42, height - 30)
        )
        if accent.mode != "RGBA":
            accent = accent.convert("RGBA")
        accent = ImageEnhance.Color(accent).enhance(1.22)
        accent = ImageEnhance.Contrast(accent).enhance(1.08)
        accent_mask = Image.new("L", accent.size, 0)
        accent_draw = ImageDraw.Draw(accent_mask)
        accent_draw.rounded_rectangle((0, 0, accent.width - 1, accent.height - 1), radius=accent.height // 2, fill=188)
        accent_x = 18
        accent_y = max(8, (height - accent.height) // 2)
        panel.paste(accent, (accent_x, accent_y), accent_mask)

        aura = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        aura_draw = ImageDraw.Draw(aura)
        aura_draw.rounded_rectangle(
            (accent_x - 4, accent_y - 4, accent_x + accent.width + 4, accent_y + accent.height + 4),
            radius=accent.height // 2 + 4,
            outline=self._hex_rgba(palette["accent"], 110),
            width=2,
        )
        aura = aura.filter(ImageFilter.GaussianBlur(radius=2.4))
        panel = Image.alpha_composite(panel, aura)

        sheen = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        sheen_draw = ImageDraw.Draw(sheen)
        sheen_draw.rounded_rectangle((2, 2, width - 3, 34), radius=22, fill=(255, 255, 255, 22 if not light else 68))
        panel = Image.alpha_composite(panel, sheen)
        field = Image.alpha_composite(field, panel)
        self.settings_header_photo = ImageTk.PhotoImage(field.convert("RGB"))
        try:
            self.settings_header_photos[int(canvas.winfo_id())] = self.settings_header_photo
        except tk.TclError:
            pass
        canvas.delete("all")
        canvas.configure(bg=palette["bg"], highlightthickness=0, bd=0)
        canvas.create_image(0, 0, image=self.settings_header_photo, anchor="nw")
        canvas.create_text(
            accent_x + accent_width + 22,
            32,
            text=title,
            anchor="w",
            fill=palette["text"],
            font=("Segoe UI Semibold", 17),
        )
        canvas.create_text(
            accent_x + accent_width + 22,
            58,
            text=subtitle or f"Settings - {palette['name']} - local private config",
            anchor="w",
            fill=palette["muted"],
            font=("Segoe UI", 10),
        )
        close_left = width - 55
        canvas.create_oval(
            close_left,
            20,
            close_left + 28,
            48,
            outline=palette["warm"],
            width=1,
            fill=palette["button"],
        )
        canvas.create_text(
            close_left + 14,
            34,
            text="X",
            fill=palette["warm"],
            font=("Segoe UI Semibold", 9),
        )

    def _schedule_settings_header_animation(
        self,
        canvas: tk.Canvas,
        theme_getter: Callable[[], str],
        height: int,
        *,
        title: str = "Talk Dat!",
        subtitle_getter: Callable[[], str | None] | None = None,
    ) -> None:
        def tick() -> None:
            try:
                if not bool(canvas.winfo_exists()):
                    return
                subtitle = subtitle_getter() if subtitle_getter else None
                self._draw_settings_header(
                    canvas,
                    max(1, canvas.winfo_width()),
                    height,
                    theme_getter(),
                    title=title,
                    subtitle=subtitle,
                )
                canvas.after(max(16, min(42, self.idle_frame_ms)), tick)
            except tk.TclError:
                pass

        tick()

    def open_onboarding(self) -> None:
        self.force_visible()
        ui = self.config.setdefault("ui", {})
        theme = self._settings_theme_key(str(ui.get("settings_theme") or ui.get("theme") or "Flow Dark"))
        palette = self._settings_palette(theme)
        window = self._utility_window("onboarding", "Talk Dat! Setup", "860x690", bg=palette["bg"])
        if window is None:
            return
        window.configure(bg=palette["bg"])
        self._style_settings_widgets(window, palette)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = tk.Canvas(window, height=136, bg=palette["bg"], bd=0, highlightthickness=0)
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        self._bind_utility_drag_handle(window, header)

        def redraw_header(_event: tk.Event | None = None) -> None:
            width = max(1, header.winfo_width())
            self._draw_settings_header(
                header,
                width,
                136,
                theme,
                title="Talk Dat! Setup",
                subtitle="Choose a speech provider, paste your own key, then trigger only when you want to talk.",
            )

        def header_click(event: tk.Event) -> str | None:
            if int(getattr(event, "x", 0)) >= max(0, header.winfo_width() - 62) and int(getattr(event, "y", 0)) <= 62:
                window.destroy()
                return "break"
            return None

        header.bind("<Configure>", redraw_header)
        header.bind("<ButtonPress-1>", header_click, add="+")
        self._schedule_settings_header_animation(
            header,
            lambda: theme,
            136,
            title="Talk Dat! Setup",
            subtitle_getter=lambda: "Choose a speech provider, paste your own key, then trigger only when you want to talk.",
        )

        panel = ttk.Frame(window, padding=18, style="Flow.TFrame")
        panel.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        panel.columnconfigure(1, weight=1)
        ttk.Label(
            panel,
            text="1. Pick a wired provider. 2. Paste your own key. 3. Save setup. The microphone stays off until a trigger is pressed.",
            wraplength=720,
            style="Flow.Muted.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        def add_row(row: int, label: str, widget: tk.Widget) -> None:
            ttk.Label(panel, text=label, style="Flow.TLabel").grid(row=row, column=0, sticky="w", pady=7, padx=(0, 14))
            widget.grid(row=row, column=1, sticky="ew", pady=7)

        def combo(variable: tk.StringVar, values: list[str], width: int = 32) -> ttk.Combobox:
            return ttk.Combobox(panel, textvariable=variable, values=values, width=width, style="Flow.TCombobox")

        def entry(variable: tk.StringVar, width: int = 48, show: str | None = None) -> ttk.Entry:
            return ttk.Entry(panel, textvariable=variable, width=width, show=show or "", style="Flow.TEntry")

        active_provider_id = selected_provider_id(self.config)
        active_model_id = selected_model_id(self.config, active_provider_id)
        active_settings = provider_settings(self.config, active_provider_id)
        provider_holder = {"id": active_provider_id}

        provider_var = tk.StringVar(value=provider_label(active_provider_id))
        model_var = tk.StringVar(value=model_label(active_provider_id, active_model_id))
        variant_var = tk.StringVar(value=selected_variant(self.config, active_provider_id))
        key_var = tk.StringVar(value=str(active_settings.get("api_key", "")))
        base_var = tk.StringVar(value=str(active_settings.get("api_base") or PROVIDER_BY_ID[active_provider_id].api_base))
        language_var = tk.StringVar(value=str(active_settings.get("language") or self.config.get("deepgram", {}).get("language", "en-US")))
        key_label_var = tk.StringVar(value=PROVIDER_BY_ID[active_provider_id].key_label)
        capability_var = tk.StringVar(value=provider_capability_summary(active_provider_id, active_model_id))
        docs_var = tk.StringVar(value=str(PROVIDER_BY_ID[active_provider_id].docs_url or "Custom/local provider"))

        provider_box = combo(provider_var, provider_labels(), 32)
        model_box = combo(model_var, model_labels(active_provider_id), 40)
        variant_box = combo(variant_var, list(model_for_id(active_provider_id, active_model_id).variants), 26)
        key_entry = entry(key_var, 64, show="*")

        def remember_provider_fields(provider_id: str) -> None:
            settings = provider_settings(self.config, provider_id)
            settings["api_key"] = key_var.get().strip()
            settings["api_base"] = base_var.get().strip()
            settings["language"] = language_var.get().strip() or "en-US"
            settings["model"] = model_id_for_label(provider_id, model_var.get())
            model = model_for_id(provider_id, settings["model"])
            settings["variant"] = variant_var.get().strip() or model.variants[0]

        def refresh_provider_fields(*, keep_model: bool = False) -> None:
            provider_id = provider_id_for_label(provider_var.get())
            provider = PROVIDER_BY_ID[provider_id]
            settings = provider_settings(self.config, provider_id)
            current_model_id = str(settings.get("model") or provider.models[0].id)
            model_box.configure(values=model_labels(provider_id))
            if not keep_model:
                model_var.set(model_label(provider_id, current_model_id))
            chosen_model_id = model_id_for_label(provider_id, model_var.get())
            chosen_model = model_for_id(provider_id, chosen_model_id)
            variant_box.configure(values=list(chosen_model.variants))
            if variant_var.get() not in chosen_model.variants:
                variant_var.set(str(settings.get("variant") or chosen_model.variants[0]))
            if variant_var.get() not in chosen_model.variants:
                variant_var.set(chosen_model.variants[0])
            key_var.set(str(settings.get("api_key", "")))
            base_var.set(str(settings.get("api_base") or provider.api_base))
            language_var.set(str(settings.get("language") or self.config.get("deepgram", {}).get("language", "en-US")))
            key_label_var.set(provider.key_label)
            capability_var.set(provider_capability_summary(provider_id, chosen_model_id))
            docs_var.set(str(provider.docs_url or "Custom/local provider"))
            provider_holder["id"] = provider_id

        def on_provider_change(_event: tk.Event | None = None) -> None:
            remember_provider_fields(provider_holder["id"])
            refresh_provider_fields()

        def on_model_change(_event: tk.Event | None = None) -> None:
            provider_id = provider_id_for_label(provider_var.get())
            chosen_model_id = model_id_for_label(provider_id, model_var.get())
            chosen_model = model_for_id(provider_id, chosen_model_id)
            variant_box.configure(values=list(chosen_model.variants))
            if variant_var.get() not in chosen_model.variants:
                variant_var.set(chosen_model.variants[0])
            capability_var.set(provider_capability_summary(provider_id, chosen_model_id))

        provider_box.bind("<<ComboboxSelected>>", on_provider_change)
        model_box.bind("<<ComboboxSelected>>", on_model_change)

        add_row(1, "Provider", provider_box)
        add_row(2, "Model", model_box)
        add_row(3, "Mode / trim", variant_box)
        add_row(4, "Language", entry(language_var, 18))
        add_row(5, "API base", entry(base_var, 64))
        add_row(6, "API key", key_entry)
        ttk.Label(panel, textvariable=key_label_var, style="Flow.Muted.TLabel").grid(row=7, column=1, sticky="w")
        ttk.Label(panel, textvariable=capability_var, style="Flow.Muted.TLabel").grid(row=8, column=1, sticky="w", pady=(6, 0))
        ttk.Label(panel, textvariable=docs_var, wraplength=580, style="Flow.Muted.TLabel").grid(
            row=9, column=1, sticky="ew", pady=(4, 8)
        )
        ttk.Label(
            panel,
            text=f"Private local config: {config_path()}",
            wraplength=720,
            style="Flow.Muted.TLabel",
        ).grid(row=10, column=0, columnspan=2, sticky="w", pady=(4, 8))
        ttk.Label(
            panel,
            text="Recommended first test: open Notepad, click the pill or hold Ctrl+Win, speak one sentence, then stop.",
            wraplength=720,
            style="Flow.Muted.TLabel",
        ).grid(row=11, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(
            panel,
            text="Wired today: Deepgram streaming, OpenAI-compatible batch, ElevenLabs, AssemblyAI, and Gemini. Other brands show adapter-pending status in full settings.",
            wraplength=720,
            style="Flow.Muted.TLabel",
        ).grid(row=12, column=0, columnspan=2, sticky="w", pady=(4, 0))

        button_row = tk.Frame(window, bg=palette["bg"])
        button_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        status_var = tk.StringVar(value="")

        def save_setup(*, close: bool = True) -> None:
            remember_provider_fields(provider_holder["id"])
            provider_id = provider_id_for_label(provider_var.get())
            settings = provider_settings(self.config, provider_id)
            self.config.setdefault("stt", {})["provider"] = provider_id
            self.config.setdefault("deepgram", {})["language"] = language_var.get().strip() or "en-US"
            settings["language"] = language_var.get().strip() or "en-US"
            if provider_id == "deepgram":
                deepgram = self.config.setdefault("deepgram", {})
                deepgram["api_key"] = settings.get("api_key", "")
                deepgram["model"] = settings.get("model", "nova-3")
                deepgram["language"] = settings.get("language", "en-US")
            sync_legacy_deepgram(self.config)
            self.config.setdefault("onboarding", {})["completed"] = True
            self.apply_runtime_config()
            callback = self.callbacks.get("save_settings")
            if callback:
                callback()
            status_var.set("Saved.")
            self.set_state("captured", "Setup saved.", f"Saved to {config_path()}")
            if close:
                window.destroy()

        def skip_setup() -> None:
            self.config.setdefault("onboarding", {})["completed"] = True
            callback = self.callbacks.get("save_settings")
            if callback:
                callback()
            self.set_state("idle", "Setup skipped. Add a provider key in Settings before dictating.", "")
            window.destroy()

        def full_settings() -> None:
            window.destroy()
            self.root.after(80, self.open_settings)

        ttk.Button(button_row, text="Save Setup", command=save_setup, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="Full Settings", command=full_settings, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="Skip", command=skip_setup, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Label(button_row, textvariable=status_var, style="Flow.Muted.TLabel").pack(side="left", padx=(6, 0))
        ttk.Button(button_row, text="Close", command=window.destroy, style="Flow.TButton").pack(side="right")

        try:
            key_entry.focus_set()
        except Exception:
            pass

    def open_settings(self) -> None:
        self.force_visible()
        ui = self.config.setdefault("ui", {})
        theme = self._settings_theme_key(str(ui.get("settings_theme") or ui.get("theme") or "Flow Dark"))
        palette = self._settings_palette(theme)
        window = self._utility_window("settings", "Talk Dat! Settings", "1120x760", bg=palette["bg"])
        if window is None:
            return
        window.configure(bg=palette["bg"])
        self._style_settings_widgets(window, palette)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        theme_text_widgets: list[tk.Text] = []

        header = tk.Canvas(window, height=96, bg=palette["bg"], bd=0, highlightthickness=0)
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        self._bind_utility_drag_handle(window, header)

        notebook = ttk.Notebook(window, style="Flow.TNotebook")
        notebook.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))

        def make_tab(title: str) -> ttk.Frame:
            frame = ttk.Frame(notebook, padding=16, style="Flow.TFrame")
            notebook.add(frame, text=title)
            return frame

        core_tab = make_tab("Core")
        providers_tab = make_tab("Providers")
        deepgram_tab = make_tab("Deepgram")
        dictation_tab = make_tab("Dictation")
        overlay_tab = make_tab("Overlay")
        hotkeys_tab = make_tab("Hotkeys")
        dictionary_tab = make_tab("Dictionary")
        snippets_tab = make_tab("Snippets")
        transforms_tab = make_tab("Transforms")
        privacy_tab = make_tab("Privacy")

        def redraw_header(_event: tk.Event | None = None) -> None:
            self._draw_settings_header(header, max(1, header.winfo_width()), 96, theme_var.get())

        def add_row(parent: ttk.Frame, row: int, label: str, widget: tk.Widget) -> None:
            ttk.Label(parent, text=label, style="Flow.TLabel").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 14))
            widget.grid(row=row, column=1, sticky="ew", pady=5)
            parent.columnconfigure(1, weight=1)

        def entry(parent: ttk.Frame, variable: tk.StringVar, width: int = 18, show: str | None = None) -> ttk.Entry:
            return ttk.Entry(parent, textvariable=variable, width=width, show=show or "", style="Flow.TEntry")

        def combo(parent: ttk.Frame, variable: tk.StringVar, values: list[str], width: int = 28) -> ttk.Combobox:
            return ttk.Combobox(parent, textvariable=variable, values=values, width=width, style="Flow.TCombobox")

        def check(parent: ttk.Frame, text: str, variable: tk.BooleanVar, row: int) -> None:
            ttk.Checkbutton(parent, text=text, variable=variable, style="Flow.TCheckbutton").grid(
                row=row, column=0, columnspan=2, sticky="w", pady=5
            )

        def text_box(parent: ttk.Frame, height: int, *, font: tuple[str, int] = ("Consolas", 10)) -> tk.Text:
            widget = tk.Text(
                parent,
                height=height,
                wrap="word",
                font=font,
                bg=palette["field"],
                fg=palette["text"],
                insertbackground=palette["text"],
                selectbackground=palette["select"],
                bd=0,
                padx=12,
                pady=10,
            )
            theme_text_widgets.append(widget)
            return widget

        deepgram = self.config.setdefault("deepgram", {})
        stt_config = self.config.setdefault("stt", {})
        cleanup = self.config.setdefault("cleanup", {})
        privacy = self.config.setdefault("privacy", {})
        dictation_config = self.config.setdefault("dictation", {})
        overlay_config = self.config.setdefault("overlay", {})
        updates_config = self.config.setdefault("updates", {})
        transforms = self.config.setdefault("transforms", {})
        ollama = transforms.setdefault("ollama", {})

        theme_var = tk.StringVar(value=self._settings_theme_key(theme))
        header.bind("<Configure>", redraw_header)
        def header_click(event: tk.Event) -> str | None:
            if int(getattr(event, "x", 0)) >= max(0, header.winfo_width() - 62) and int(getattr(event, "y", 0)) <= 58:
                window.destroy()
                return "break"
            return None

        header.bind("<ButtonPress-1>", header_click, add="+")
        self._schedule_settings_header_animation(header, lambda: theme_var.get(), 96)

        key_var = tk.StringVar(value=str(deepgram.get("api_key", "")))
        model_var = tk.StringVar(value=str(deepgram.get("model", "nova-3")))
        language_var = tk.StringVar(value=str(deepgram.get("language", "en-US")))
        level_var = tk.StringVar(value=str(cleanup.get("level", "high")))
        save_history_var = tk.BooleanVar(value=bool(privacy.get("save_history", True)))
        play_sounds_var = tk.BooleanVar(value=bool(dictation_config.get("play_sounds", True)))
        auto_paste_var = tk.BooleanVar(value=bool(dictation_config.get("auto_paste", True)))
        smart_space_var = tk.BooleanVar(value=bool(dictation_config.get("smart_leading_space", True)))
        check_updates_on_start_var = tk.BooleanVar(value=bool(updates_config.get("check_on_start", True)))
        auto_download_updates_var = tk.BooleanVar(value=bool(updates_config.get("auto_download", False)))
        latest_version_var = tk.StringVar(value=str(updates_config.get("latest_version") or "not checked yet"))

        deepgram_model_options = [model.id for model in PROVIDER_BY_ID["deepgram"].models]

        active_provider_id = selected_provider_id(self.config)
        active_model_id = selected_model_id(self.config, active_provider_id)
        active_settings = provider_settings(self.config, active_provider_id)
        provider_holder = {"id": active_provider_id}

        stt_provider_var = tk.StringVar(value=provider_label(active_provider_id))
        stt_model_var = tk.StringVar(value=model_label(active_provider_id, active_model_id))
        stt_variant_var = tk.StringVar(value=selected_variant(self.config, active_provider_id))
        stt_key_var = tk.StringVar(value=str(active_settings.get("api_key", "")))
        stt_base_var = tk.StringVar(value=str(active_settings.get("api_base") or PROVIDER_BY_ID[active_provider_id].api_base))
        stt_key_label_var = tk.StringVar(value=PROVIDER_BY_ID[active_provider_id].key_label)
        stt_env_var = tk.StringVar(value=PROVIDER_BY_ID[active_provider_id].env_key or "No key required")
        stt_docs_var = tk.StringVar(value=str(PROVIDER_BY_ID[active_provider_id].docs_url or "Custom/local provider"))
        stt_capability_var = tk.StringVar(value=provider_capability_summary(active_provider_id, active_model_id))
        stt_status_var = tk.StringVar(value=self._provider_status_text(active_provider_id))
        stt_extra_text: tk.Text | None = None

        def remember_provider_fields(provider_id: str) -> None:
            settings = provider_settings(self.config, provider_id)
            settings["api_key"] = stt_key_var.get().strip()
            settings["api_base"] = stt_base_var.get().strip()
            settings["model"] = model_id_for_label(provider_id, stt_model_var.get())
            model = model_for_id(provider_id, settings["model"])
            settings["variant"] = stt_variant_var.get().strip() or model.variants[0]
            if stt_extra_text is not None:
                raw = stt_extra_text.get("1.0", "end-1c").strip()
                if not raw:
                    settings["extra"] = {}
                else:
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        parsed = None
                    if isinstance(parsed, dict):
                        settings["extra"] = parsed

        def refresh_provider_fields(*, keep_model: bool = False) -> None:
            provider_id = provider_id_for_label(stt_provider_var.get())
            settings = provider_settings(self.config, provider_id)
            provider = PROVIDER_BY_ID[provider_id]
            current_model_id = str(settings.get("model") or provider.models[0].id)
            model_options_for_provider = model_labels(provider_id)
            stt_model_box.configure(values=model_options_for_provider)
            if not keep_model:
                stt_model_var.set(model_label(provider_id, current_model_id))
            chosen_model_id = model_id_for_label(provider_id, stt_model_var.get())
            chosen_model = model_for_id(provider_id, chosen_model_id)
            stt_variant_box.configure(values=list(chosen_model.variants))
            if stt_variant_var.get() not in chosen_model.variants:
                stt_variant_var.set(str(settings.get("variant") or chosen_model.variants[0]))
            if stt_variant_var.get() not in chosen_model.variants:
                stt_variant_var.set(chosen_model.variants[0])
            stt_key_var.set(str(settings.get("api_key", "")))
            stt_base_var.set(str(settings.get("api_base") or provider.api_base))
            stt_key_label_var.set(provider.key_label)
            stt_env_var.set(provider.env_key or "No key required")
            stt_docs_var.set(str(provider.docs_url or "Custom/local provider"))
            stt_capability_var.set(provider_capability_summary(provider_id, chosen_model_id))
            stt_status_var.set(self._provider_status_text(provider_id))
            if stt_extra_text is not None:
                stt_extra_text.delete("1.0", "end")
                stt_extra_text.insert("1.0", json.dumps(settings.get("extra", {}), indent=2, ensure_ascii=False))
            provider_holder["id"] = provider_id

        def on_provider_change(_event: tk.Event | None = None) -> None:
            remember_provider_fields(provider_holder["id"])
            refresh_provider_fields()

        def on_model_change(_event: tk.Event | None = None) -> None:
            provider_id = provider_id_for_label(stt_provider_var.get())
            chosen_model_id = model_id_for_label(provider_id, stt_model_var.get())
            chosen_model = model_for_id(provider_id, chosen_model_id)
            stt_variant_box.configure(values=list(chosen_model.variants))
            if stt_variant_var.get() not in chosen_model.variants:
                stt_variant_var.set(chosen_model.variants[0])
            stt_capability_var.set(provider_capability_summary(provider_id, chosen_model_id))

        provider_intro = tk.Canvas(providers_tab, height=86, bg=palette["panel"], bd=0, highlightthickness=0)
        provider_intro.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        def redraw_provider_intro(_event: tk.Event | None = None) -> None:
            width = max(1, provider_intro.winfo_width())
            provider_intro.configure(bg=palette["panel"])
            provider_intro.delete("all")
            provider_intro.create_rectangle(0, 0, width, 86, fill=palette["panel"], outline="")
            provider_intro.create_line(0, 84, width, 84, fill=palette["stroke"])
            provider_intro.create_oval(-34, -62, 126, 98, outline=palette["accent"], width=2)
            provider_intro.create_oval(width - 164, -58, width + 40, 126, outline=palette["warm"], width=2)
            provider_intro.create_text(
                18,
                22,
                text="Speech model routing",
                anchor="w",
                fill=palette["text"],
                font=("Segoe UI Semibold", 15),
            )
            provider_intro.create_text(
                18,
                52,
                text="Choose a brand, model, and mode. Streaming providers start live; batch providers record locally first, then transcribe after release.",
                anchor="w",
                fill=palette["muted"],
                font=("Segoe UI", 10),
            )

        provider_intro.bind("<Configure>", redraw_provider_intro)
        redraw_provider_intro()

        stt_provider_box = combo(providers_tab, stt_provider_var, provider_labels(), 30)
        stt_model_box = combo(providers_tab, stt_model_var, model_labels(active_provider_id), 36)
        stt_variant_box = combo(
            providers_tab,
            stt_variant_var,
            list(model_for_id(active_provider_id, active_model_id).variants),
            24,
        )
        stt_provider_box.bind("<<ComboboxSelected>>", on_provider_change)
        stt_model_box.bind("<<ComboboxSelected>>", on_model_change)
        stt_extra_text = text_box(providers_tab, 7)
        stt_extra_text.insert("1.0", json.dumps(active_settings.get("extra", {}), indent=2, ensure_ascii=False))
        add_row(providers_tab, 1, "Brand", stt_provider_box)
        add_row(providers_tab, 2, "Model", stt_model_box)
        add_row(providers_tab, 3, "Mode / trim", stt_variant_box)
        add_row(providers_tab, 4, "Secret / credential", entry(providers_tab, stt_key_var, 72, show="*"))
        add_row(providers_tab, 5, "API base", entry(providers_tab, stt_base_var, 72))
        ttk.Label(providers_tab, textvariable=stt_key_label_var, style="Flow.Muted.TLabel").grid(
            row=6, column=1, sticky="w", pady=(2, 2)
        )
        ttk.Label(providers_tab, textvariable=stt_env_var, style="Flow.Muted.TLabel").grid(
            row=7, column=1, sticky="w", pady=(2, 8)
        )
        ttk.Label(providers_tab, textvariable=stt_capability_var, style="Flow.Muted.TLabel").grid(
            row=8, column=1, sticky="w", pady=(2, 4)
        )
        ttk.Label(providers_tab, textvariable=stt_status_var, wraplength=700, style="Flow.Muted.TLabel").grid(
            row=9, column=1, sticky="ew", pady=(0, 8)
        )
        ttk.Label(providers_tab, text="Docs", style="Flow.TLabel").grid(row=10, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Label(providers_tab, textvariable=stt_docs_var, wraplength=650, style="Flow.Muted.TLabel").grid(
            row=10, column=1, sticky="ew", pady=5
        )
        ttk.Label(providers_tab, text="Advanced options JSON", style="Flow.TLabel").grid(
            row=11, column=0, columnspan=2, sticky="w", pady=(12, 4)
        )
        stt_extra_text.grid(row=12, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        ttk.Label(
            providers_tab,
            text="Credentials, dictionaries, snippets, transcripts, and provider options are private user config in AppData. Public GitHub downloads start with empty settings.",
            wraplength=850,
            style="Flow.Muted.TLabel",
        ).grid(row=13, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(
            providers_tab,
            text="Local models: download / manage on-device models",
            command=self.open_local_models,
            style="Flow.TButton",
        ).grid(row=14, column=0, columnspan=2, sticky="w", pady=(10, 0))
        providers_tab.columnconfigure(1, weight=1)
        providers_tab.rowconfigure(12, weight=1)

        add_row(core_tab, 0, "Active brand", ttk.Label(core_tab, textvariable=stt_provider_var, style="Flow.TLabel"))
        add_row(core_tab, 1, "Active model", ttk.Label(core_tab, textvariable=stt_model_var, style="Flow.TLabel"))
        add_row(core_tab, 2, "Language", entry(core_tab, language_var, 20))
        add_row(core_tab, 3, "Auto Cleanup", combo(core_tab, level_var, ["none", "light", "medium", "high"], 20))
        theme_box = combo(core_tab, theme_var, self._settings_theme_options(), 28)
        theme_box.configure(state="readonly")
        add_row(core_tab, 4, "Settings menu theme", theme_box)
        add_row(core_tab, 5, "Installed version", ttk.Label(core_tab, text=f"v{APP_VERSION}", style="Flow.TLabel"))
        add_row(core_tab, 6, "Latest seen", ttk.Label(core_tab, textvariable=latest_version_var, style="Flow.TLabel"))
        add_row(
            core_tab,
            7,
            "Updater",
            ttk.Button(core_tab, text="Check / install latest", command=self._callback("check_updates"), style="Flow.TButton"),
        )
        check(core_tab, "Check for updates on start", check_updates_on_start_var, 8)
        check(core_tab, "Auto-download update installer when a new release exists", auto_download_updates_var, 9)
        check(core_tab, "Save local transcript history", save_history_var, 10)
        check(core_tab, "Play start and stop sounds", play_sounds_var, 11)
        check(core_tab, "Auto paste transcript", auto_paste_var, 12)
        check(core_tab, "Smart leading space", smart_space_var, 13)
        ttk.Label(core_tab, text=f"Config: {config_path()}", wraplength=850, style="Flow.Muted.TLabel").grid(
            row=14, column=0, columnspan=2, sticky="w", pady=(16, 0)
        )

        def string_var(value: Any) -> tk.StringVar:
            return tk.StringVar(value=str(value))

        sample_rate_var = string_var(deepgram.get("sample_rate", 16000))
        channels_var = string_var(deepgram.get("channels", 1))
        encoding_var = string_var(deepgram.get("encoding", "linear16"))
        endpointing_var = string_var(deepgram.get("endpointing", 300))
        utterance_var = string_var(deepgram.get("utterance_end_ms", 1000))
        smart_format_var = tk.BooleanVar(value=bool(deepgram.get("smart_format", True)))
        punctuate_var = tk.BooleanVar(value=bool(deepgram.get("punctuate", True)))
        interim_var = tk.BooleanVar(value=bool(deepgram.get("interim_results", True)))
        vad_var = tk.BooleanVar(value=bool(deepgram.get("vad_events", True)))
        filler_var = tk.BooleanVar(value=bool(deepgram.get("filler_words", False)))
        dg_dictation_var = tk.BooleanVar(value=bool(deepgram.get("dictation", True)))
        numerals_var = tk.BooleanVar(value=bool(deepgram.get("numerals", True)))
        mip_var = tk.BooleanVar(value=bool(deepgram.get("mip_opt_out", True)))
        extra_text = text_box(deepgram_tab, 8)
        extra_text.insert("1.0", json.dumps(deepgram.get("extra", {}), indent=2, ensure_ascii=False))

        add_row(deepgram_tab, 0, "Deepgram API key", entry(deepgram_tab, key_var, 72, show="*"))
        add_row(deepgram_tab, 1, "Deepgram model", combo(deepgram_tab, model_var, deepgram_model_options, 34))
        add_row(deepgram_tab, 2, "Sample rate", entry(deepgram_tab, sample_rate_var, 12))
        add_row(deepgram_tab, 3, "Channels", entry(deepgram_tab, channels_var, 12))
        add_row(deepgram_tab, 4, "Encoding", combo(deepgram_tab, encoding_var, ["linear16", "mulaw", "alaw", "opus"], 18))
        add_row(deepgram_tab, 5, "Endpointing ms", entry(deepgram_tab, endpointing_var, 12))
        add_row(deepgram_tab, 6, "Utterance end ms", entry(deepgram_tab, utterance_var, 12))
        check(deepgram_tab, "Smart format", smart_format_var, 7)
        check(deepgram_tab, "Punctuation", punctuate_var, 8)
        check(deepgram_tab, "Interim results", interim_var, 9)
        check(deepgram_tab, "VAD speech events", vad_var, 10)
        check(deepgram_tab, "Filler words", filler_var, 11)
        check(deepgram_tab, "Dictation mode", dg_dictation_var, 12)
        check(deepgram_tab, "Numerals", numerals_var, 13)
        check(deepgram_tab, "Deepgram MIP opt-out", mip_var, 14)
        ttk.Label(deepgram_tab, text="Extra Deepgram params JSON", style="Flow.TLabel").grid(
            row=15, column=0, columnspan=2, sticky="w", pady=(12, 4)
        )
        extra_text.grid(row=16, column=0, columnspan=2, sticky="nsew")
        deepgram_tab.rowconfigure(16, weight=1)

        tail_var = string_var(dictation_config.get("tail_capture_ms", 520))
        debounce_var = string_var(dictation_config.get("hold_debounce_ms", 35))
        max_var = string_var(dictation_config.get("max_seconds", 5 * 60))
        no_speech_var = string_var(dictation_config.get("no_speech_timeout_seconds", 15))
        silence_var = string_var(dictation_config.get("silence_timeout_seconds", 45))
        hold_max_var = string_var(dictation_config.get("hold_max_seconds", 30 * 60))
        hold_no_speech_var = string_var(dictation_config.get("hold_no_speech_timeout_seconds", 120))
        hold_silence_var = string_var(dictation_config.get("hold_silence_timeout_seconds", 300))
        restore_clipboard_var = tk.BooleanVar(value=bool(dictation_config.get("restore_clipboard_after_paste", False)))
        press_enter_var = tk.BooleanVar(value=bool(dictation_config.get("press_enter_command", True)))
        mute_output_var = tk.BooleanVar(value=bool(dictation_config.get("mute_output_while_recording", True)))

        add_row(dictation_tab, 0, "Tail capture ms", entry(dictation_tab, tail_var, 12))
        add_row(dictation_tab, 1, "Hold debounce ms", entry(dictation_tab, debounce_var, 12))
        add_row(dictation_tab, 2, "Hands-free max seconds", entry(dictation_tab, max_var, 12))
        add_row(dictation_tab, 3, "Hands-free no speech", entry(dictation_tab, no_speech_var, 12))
        add_row(dictation_tab, 4, "Hands-free silence", entry(dictation_tab, silence_var, 12))
        add_row(dictation_tab, 5, "Hold max seconds", entry(dictation_tab, hold_max_var, 12))
        add_row(dictation_tab, 6, "Hold no speech", entry(dictation_tab, hold_no_speech_var, 12))
        add_row(dictation_tab, 7, "Hold silence", entry(dictation_tab, hold_silence_var, 12))
        check(dictation_tab, "Restore clipboard after paste", restore_clipboard_var, 8)
        check(dictation_tab, "Spoken press-enter command", press_enter_var, 9)
        check(dictation_tab, "Mute speaker output while recording", mute_output_var, 10)

        show_start_var = tk.BooleanVar(value=bool(overlay_config.get("show_on_start", True)))
        opacity_var = string_var(overlay_config.get("opacity", 0.94))
        hover_fade_delay_var = string_var(overlay_config.get("hover_fade_delay_ms", 2000))
        hover_fade_opacity_var = string_var(overlay_config.get("hover_fade_opacity", 0.38))
        active_pill_w_var = string_var(overlay_config.get("active_pill_width", 320))
        active_pill_h_var = string_var(overlay_config.get("active_pill_height", 58))
        active_w_var = string_var(overlay_config.get("active_width", 320))
        active_h_var = string_var(overlay_config.get("active_height", 58))
        compact_w_var = string_var(overlay_config.get("compact_width", 110))
        compact_h_var = string_var(overlay_config.get("compact_height", 38))
        bottom_margin_var = string_var(overlay_config.get("bottom_margin", 68))
        active_frame_var = string_var(overlay_config.get("active_frame_ms", 16))
        idle_frame_var = string_var(overlay_config.get("idle_frame_ms", 33))
        resize_frame_var = string_var(overlay_config.get("resize_frame_ms", 6))
        resize_steps_var = string_var(overlay_config.get("resize_steps", 12))
        active_loop_var = string_var(overlay_config.get("active_loop_seconds", 3.84))
        idle_loop_var = string_var(overlay_config.get("idle_loop_seconds", 8.0))
        result_hold_var = string_var(overlay_config.get("result_hold_ms", 900))
        error_hold_var = string_var(overlay_config.get("error_hold_ms", 5200))
        wave_start_var = string_var(overlay_config.get("wave_loop_start", 0))
        wave_end_var = string_var(overlay_config.get("wave_loop_end", 50))
        fixed_var = tk.BooleanVar(value=bool(overlay_config.get("fixed_position", True)))
        no_activate_var = tk.BooleanVar(value=bool(overlay_config.get("no_activate", True)))
        fullscreen_hide_var = tk.BooleanVar(value=bool(overlay_config.get("hide_over_fullscreen_media", True)))
        fullscreen_session_show_var = tk.BooleanVar(value=bool(overlay_config.get("show_session_over_fullscreen", False)))
        fullscreen_poll_var = string_var(overlay_config.get("fullscreen_poll_ms", 450))

        add_row(overlay_tab, 0, "Opacity", entry(overlay_tab, opacity_var, 12))
        add_row(overlay_tab, 1, "Hover fade delay ms", entry(overlay_tab, hover_fade_delay_var, 12))
        add_row(overlay_tab, 2, "Hover fade opacity", entry(overlay_tab, hover_fade_opacity_var, 12))
        add_row(overlay_tab, 3, "Active pill width", entry(overlay_tab, active_pill_w_var, 12))
        add_row(overlay_tab, 4, "Active pill height", entry(overlay_tab, active_pill_h_var, 12))
        add_row(overlay_tab, 5, "Active window width", entry(overlay_tab, active_w_var, 12))
        add_row(overlay_tab, 6, "Active window height", entry(overlay_tab, active_h_var, 12))
        add_row(overlay_tab, 7, "Resting width", entry(overlay_tab, compact_w_var, 12))
        add_row(overlay_tab, 8, "Resting height", entry(overlay_tab, compact_h_var, 12))
        add_row(overlay_tab, 9, "Bottom margin", entry(overlay_tab, bottom_margin_var, 12))
        add_row(overlay_tab, 10, "Active frame ms", entry(overlay_tab, active_frame_var, 12))
        add_row(overlay_tab, 11, "Idle frame ms", entry(overlay_tab, idle_frame_var, 12))
        add_row(overlay_tab, 12, "Resize frame ms", entry(overlay_tab, resize_frame_var, 12))
        add_row(overlay_tab, 13, "Resize steps", entry(overlay_tab, resize_steps_var, 12))
        add_row(overlay_tab, 14, "Active loop seconds", entry(overlay_tab, active_loop_var, 12))
        add_row(overlay_tab, 15, "Idle loop seconds", entry(overlay_tab, idle_loop_var, 12))
        add_row(overlay_tab, 16, "Result hold ms", entry(overlay_tab, result_hold_var, 12))
        add_row(overlay_tab, 17, "Error hold ms", entry(overlay_tab, error_hold_var, 12))
        add_row(overlay_tab, 18, "Wave loop start", entry(overlay_tab, wave_start_var, 12))
        add_row(overlay_tab, 19, "Wave loop end", entry(overlay_tab, wave_end_var, 12))
        check(overlay_tab, "Show overlay on start", show_start_var, 20)
        check(overlay_tab, "Always same bottom position", fixed_var, 21)
        check(overlay_tab, "Do not steal focus", no_activate_var, 22)
        check(overlay_tab, "Hide pill over fullscreen media", fullscreen_hide_var, 23)
        check(overlay_tab, "Show pill while dictating over fullscreen apps", fullscreen_session_show_var, 24)
        add_row(overlay_tab, 25, "Fullscreen check ms", entry(overlay_tab, fullscreen_poll_var, 12))

        hotkey_entries: dict[str, tk.StringVar] = {}
        hotkey_labels = [
            ("push_to_talk", "Push-to-talk"),
            ("hands_free", "Hands-free toggle"),
            ("command_mode", "Command mode"),
            ("panic", "Panic stop"),
            ("cancel", "Cancel"),
            ("paste_last", "Paste last"),
            ("copy_last", "Copy last"),
            ("polish", "Polish"),
            ("prompt_engineer", "Prompt engineer"),
            ("turn_to_list", "Turn to list"),
            ("view_diff", "Copy cleanup diff"),
            ("scratchpad", "Scratchpad"),
        ]
        for row, (action, label) in enumerate(hotkey_labels):
            var = tk.StringVar(value=self._format_shortcuts(self.config.get("hotkeys", {}).get(action, [])))
            hotkey_entries[action] = var
            add_row(hotkeys_tab, row, label, entry(hotkeys_tab, var, 54))

        words_text = text_box(dictionary_tab, 17)
        replacements_text = text_box(dictionary_tab, 17)
        words_text.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        replacements_text.grid(row=0, column=1, sticky="nsew")
        words_text.insert("1.0", "\n".join(str(word) for word in self.config.get("dictionary", {}).get("words", [])))
        replacements_text.insert(
            "1.0",
            json.dumps(self.config.get("dictionary", {}).get("replacements", []), indent=2, ensure_ascii=False),
        )
        ttk.Label(dictionary_tab, text="Words, one per line", style="Flow.Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(dictionary_tab, text="Replacements JSON", style="Flow.Muted.TLabel").grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )
        dictionary_tab.columnconfigure(0, weight=1)
        dictionary_tab.columnconfigure(1, weight=1)
        dictionary_tab.rowconfigure(0, weight=1)

        snippets_text = text_box(snippets_tab, 22)
        snippets_text.pack(fill="both", expand=True)
        snippets_text.insert("1.0", json.dumps(self.config.get("snippets", []), indent=2, ensure_ascii=False))

        transforms_enabled_var = tk.BooleanVar(value=bool(transforms.get("enabled", True)))
        ollama_enabled_var = tk.BooleanVar(value=bool(ollama.get("enabled", False)))
        ollama_url_var = tk.StringVar(value=str(ollama.get("url", "http://localhost:11434/api/generate")))
        ollama_model_var = tk.StringVar(value=str(ollama.get("model", "llama3.1")))
        custom_text = text_box(transforms_tab, 11)
        custom_text.insert("1.0", json.dumps(transforms.get("custom", []), indent=2, ensure_ascii=False))
        check(transforms_tab, "Enable transforms", transforms_enabled_var, 0)
        check(transforms_tab, "Use Ollama for rewrites", ollama_enabled_var, 1)
        add_row(transforms_tab, 2, "Ollama URL", entry(transforms_tab, ollama_url_var, 70))
        add_row(transforms_tab, 3, "Ollama model", entry(transforms_tab, ollama_model_var, 30))
        ttk.Label(transforms_tab, text="Custom transforms JSON", style="Flow.TLabel").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(12, 4)
        )
        custom_text.grid(row=5, column=0, columnspan=2, sticky="nsew")
        transforms_tab.rowconfigure(5, weight=1)

        history_limit_var = string_var(privacy.get("history_limit", 0))
        history_backend_var = tk.StringVar(value=history_backend(self.config))
        add_row(privacy_tab, 0, "History limit", entry(privacy_tab, history_limit_var, 12))
        add_row(privacy_tab, 1, "History storage", combo(privacy_tab, history_backend_var, list(HISTORY_BACKENDS), 14))
        ttk.Label(
            privacy_tab,
            text="jsonl keeps history in a plain text file. sqlite keeps it in a local searchable database.",
            wraplength=880,
            style="Flow.Muted.TLabel",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Label(privacy_tab, text=f"History: {history_path()}", wraplength=880, style="Flow.Muted.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Label(privacy_tab, text=f"History database: {history_db_path()}", wraplength=880, style="Flow.Muted.TLabel").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Label(privacy_tab, text=f"Full history: {full_history_path()}", wraplength=880, style="Flow.Muted.TLabel").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=6
        )
        ttk.Label(privacy_tab, text=f"Live draft: {live_draft_path()}", wraplength=880, style="Flow.Muted.TLabel").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=6
        )

        button_row = tk.Frame(window, bg=palette["bg"])
        button_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        save_status_var = tk.StringVar(value="")

        def apply_settings_theme(_event: tk.Event | None = None) -> None:
            nonlocal theme, palette
            theme = self._settings_theme_key(theme_var.get())
            palette = self._settings_palette(theme)
            if theme_var.get() != theme:
                theme_var.set(theme)
            ui["settings_theme"] = theme
            ui["theme"] = "light" if theme.endswith("Light") else "dark"
            window.configure(bg=palette["bg"])
            button_row.configure(bg=palette["bg"])
            self._style_settings_widgets(window, palette)
            for widget in theme_text_widgets:
                try:
                    widget.configure(
                        bg=palette["field"],
                        fg=palette["text"],
                        insertbackground=palette["text"],
                        selectbackground=palette["select"],
                    )
                except tk.TclError:
                    pass
            redraw_header()
            redraw_provider_intro()
            callback = self.callbacks.get("save_settings")
            if callback:
                callback()
            save_status_var.set(f"Theme changed to {theme}.")

        theme_box.bind("<<ComboboxSelected>>", apply_settings_theme)
        theme_box.bind("<FocusOut>", apply_settings_theme, add="+")

        def parse_int(var: tk.StringVar, fallback: int, low: int, high: int) -> int:
            try:
                value = int(float(str(var.get()).strip()))
            except ValueError:
                value = fallback
            return int(self._clamp(value, low, high))

        def parse_float(var: tk.StringVar, fallback: float, low: float, high: float) -> float:
            try:
                value = float(str(var.get()).strip())
            except ValueError:
                value = fallback
            return float(self._clamp(value, low, high))

        def parse_endpointing(var: tk.StringVar) -> int | bool:
            raw = str(var.get()).strip().lower()
            if raw in {"false", "off", "disabled", "no"}:
                return False
            if raw in {"true", "on", "enabled", "yes"}:
                return True
            return parse_int(var, 300, 0, 5000)

        def parse_json_list(widget: tk.Text, label: str) -> list[Any]:
            raw = widget.get("1.0", "end-1c").strip()
            if not raw:
                return []
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                raise ValueError(f"{label} must be valid JSON.")
            if not isinstance(value, list):
                raise ValueError(f"{label} must be a JSON list.")
            return value

        def parse_json_object(widget: tk.Text, label: str) -> dict[str, Any]:
            raw = widget.get("1.0", "end-1c").strip()
            if not raw:
                return {}
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                raise ValueError(f"{label} must be valid JSON.")
            if not isinstance(value, dict):
                raise ValueError(f"{label} must be a JSON object.")
            return value

        def save() -> None:
            try:
                replacements = parse_json_list(replacements_text, "Replacements")
                snippets = parse_json_list(snippets_text, "Snippets")
                custom_transforms = parse_json_list(custom_text, "Custom transforms")
                deepgram_extra = parse_json_object(extra_text, "Extra Deepgram params")
                provider_extra = parse_json_object(stt_extra_text, "Provider advanced options") if stt_extra_text else {}
            except ValueError as error:
                save_status_var.set(str(error))
                self.set_state("error", "Settings not saved.", str(error))
                return

            ui["settings_theme"] = self._settings_theme_key(theme_var.get())
            ui["theme"] = "light" if ui["settings_theme"].endswith("Light") else "dark"
            deepgram["api_key"] = key_var.get().strip()
            deepgram["model"] = model_var.get().strip() or "nova-3"
            deepgram["language"] = language_var.get().strip() or "en-US"
            deepgram["sample_rate"] = parse_int(sample_rate_var, 16000, 8000, 192000)
            deepgram["channels"] = parse_int(channels_var, 1, 1, 8)
            deepgram["encoding"] = encoding_var.get().strip() or "linear16"
            deepgram["smart_format"] = bool(smart_format_var.get())
            deepgram["punctuate"] = bool(punctuate_var.get())
            deepgram["interim_results"] = bool(interim_var.get())
            deepgram["endpointing"] = parse_endpointing(endpointing_var)
            deepgram["utterance_end_ms"] = parse_int(utterance_var, 1000, 0, 10000)
            deepgram["vad_events"] = bool(vad_var.get())
            deepgram["filler_words"] = bool(filler_var.get())
            deepgram["dictation"] = bool(dg_dictation_var.get())
            deepgram["numerals"] = bool(numerals_var.get())
            deepgram["mip_opt_out"] = bool(mip_var.get())
            deepgram["extra"] = deepgram_extra
            deepgram_provider_settings = provider_settings(self.config, "deepgram")
            deepgram_provider_settings["api_key"] = deepgram["api_key"]
            deepgram_provider_settings["model"] = deepgram["model"]
            deepgram_provider_settings["variant"] = "streaming"
            deepgram_provider_settings["language"] = deepgram["language"]

            remember_provider_fields(provider_holder["id"])
            active_provider = provider_id_for_label(stt_provider_var.get())
            active_settings = provider_settings(self.config, active_provider)
            active_settings["language"] = language_var.get().strip() or "en-US"
            active_settings["extra"] = provider_extra
            if active_provider == "deepgram":
                if stt_key_var.get().strip():
                    active_settings["api_key"] = stt_key_var.get().strip()
                    deepgram["api_key"] = stt_key_var.get().strip()
                active_model = model_id_for_label("deepgram", stt_model_var.get())
                active_settings["model"] = active_model
                deepgram["model"] = active_model
            stt_config["provider"] = active_provider
            sync_legacy_deepgram(self.config)

            cleanup["level"] = level_var.get().strip().lower() or "high"
            privacy["save_history"] = bool(save_history_var.get())
            privacy["history_limit"] = parse_int(history_limit_var, 0, 0, 100000)
            backend_choice = history_backend_var.get().strip().lower()
            privacy["history_backend"] = backend_choice if backend_choice in HISTORY_BACKENDS else "jsonl"
            dictation_config["play_sounds"] = bool(play_sounds_var.get())
            dictation_config["auto_paste"] = bool(auto_paste_var.get())
            dictation_config["smart_leading_space"] = bool(smart_space_var.get())
            dictation_config["tail_capture_ms"] = parse_int(tail_var, 520, 0, 3000)
            dictation_config["hold_debounce_ms"] = parse_int(debounce_var, 35, 0, 1000)
            dictation_config["max_seconds"] = parse_int(max_var, 5 * 60, 5, 60 * 60)
            dictation_config["no_speech_timeout_seconds"] = parse_int(no_speech_var, 15, 1, 60 * 60)
            dictation_config["silence_timeout_seconds"] = parse_int(silence_var, 45, 1, 60 * 60)
            dictation_config["hold_max_seconds"] = parse_int(hold_max_var, 30 * 60, 5, 60 * 60)
            dictation_config["hold_no_speech_timeout_seconds"] = parse_int(hold_no_speech_var, 120, 1, 60 * 60)
            dictation_config["hold_silence_timeout_seconds"] = parse_int(hold_silence_var, 300, 1, 60 * 60)
            dictation_config["restore_clipboard_after_paste"] = bool(restore_clipboard_var.get())
            dictation_config["press_enter_command"] = bool(press_enter_var.get())
            dictation_config["mute_output_while_recording"] = bool(mute_output_var.get())
            updates_config["check_on_start"] = bool(check_updates_on_start_var.get())
            updates_config["auto_download"] = bool(auto_download_updates_var.get())
            updates_config["current_version"] = APP_VERSION

            overlay_config["show_on_start"] = bool(show_start_var.get())
            overlay_config["opacity"] = parse_float(opacity_var, 0.94, 0.20, 1.00)
            overlay_config["hover_fade_delay_ms"] = parse_int(hover_fade_delay_var, 2000, 0, 10000)
            overlay_config["hover_fade_opacity"] = parse_float(hover_fade_opacity_var, 0.38, 0.18, 1.00)
            overlay_config["active_pill_width"] = parse_int(active_pill_w_var, 320, 120, 1200)
            overlay_config["active_pill_height"] = parse_int(active_pill_h_var, 58, 28, 260)
            overlay_config["active_width"] = parse_int(active_w_var, 320, 120, 1400)
            overlay_config["active_height"] = parse_int(active_h_var, 58, 28, 320)
            overlay_config["compact_width"] = parse_int(compact_w_var, 110, 40, 800)
            overlay_config["compact_height"] = parse_int(compact_h_var, 38, 20, 180)
            overlay_config["bottom_margin"] = parse_int(bottom_margin_var, 68, 0, 400)
            overlay_config["active_frame_ms"] = parse_int(active_frame_var, 16, 8, 200)
            overlay_config["idle_frame_ms"] = parse_int(idle_frame_var, 33, 8, 500)
            overlay_config["resize_frame_ms"] = parse_int(resize_frame_var, 6, 4, 120)
            overlay_config["resize_steps"] = parse_int(resize_steps_var, 12, 6, 24)
            overlay_config["active_loop_seconds"] = parse_float(active_loop_var, 3.84, 0.10, 20.0)
            overlay_config["idle_loop_seconds"] = parse_float(idle_loop_var, 8.0, 0.10, 60.0)
            overlay_config["result_hold_ms"] = parse_int(result_hold_var, 900, 0, 30000)
            overlay_config["error_hold_ms"] = parse_int(error_hold_var, 5200, 0, 60000)
            overlay_config["wave_loop_start"] = parse_int(wave_start_var, 0, 0, 10000)
            overlay_config["wave_loop_end"] = parse_int(wave_end_var, 50, 0, 10000)
            overlay_config["fixed_position"] = bool(fixed_var.get())
            overlay_config["no_activate"] = bool(no_activate_var.get())
            overlay_config["hide_over_fullscreen_media"] = bool(fullscreen_hide_var.get())
            overlay_config["show_session_over_fullscreen"] = bool(fullscreen_session_show_var.get())
            overlay_config["fullscreen_poll_ms"] = parse_int(fullscreen_poll_var, 450, 120, 3000)

            self.config.setdefault("hotkeys", {}).update(
                {action: self._parse_shortcuts(var.get()) for action, var in hotkey_entries.items()}
            )
            dictionary = self.config.setdefault("dictionary", {})
            dictionary["words"] = [
                line.strip()
                for line in words_text.get("1.0", "end-1c").splitlines()
                if line.strip()
            ]
            dictionary["replacements"] = replacements
            self.config["snippets"] = snippets
            transforms["enabled"] = bool(transforms_enabled_var.get())
            transforms["custom"] = custom_transforms
            ollama["enabled"] = bool(ollama_enabled_var.get())
            ollama["url"] = ollama_url_var.get().strip() or "http://localhost:11434/api/generate"
            ollama["model"] = ollama_model_var.get().strip() or "llama3.1"

            self.apply_runtime_config()
            callback = self.callbacks.get("save_settings")
            if callback:
                callback()
            save_status_var.set("Saved.")
            self.set_state("captured", "Settings saved.", f"Saved to {config_path()}")

        ttk.Button(button_row, text="Save", command=save, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="Status", command=self.open_status, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="History", command=self.open_history, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="Scratchpad", command=self.open_scratchpad, style="Flow.TButton").pack(
            side="left", padx=(0, 8)
        )
        ttk.Label(button_row, textvariable=save_status_var, style="Flow.Muted.TLabel").pack(side="left", padx=(4, 0))
        ttk.Button(button_row, text="Close", command=window.destroy, style="Flow.TButton").pack(side="right")

    def _format_shortcuts(self, shortcuts: Any) -> str:
        if not isinstance(shortcuts, list):
            return ""
        values: list[str] = []
        for shortcut in shortcuts:
            if isinstance(shortcut, str):
                values.append(shortcut)
            elif isinstance(shortcut, list):
                values.append("+".join(str(part).strip() for part in shortcut if str(part).strip()))
        return ", ".join(value for value in values if value)

    def _parse_shortcuts(self, raw: str) -> list[list[str]]:
        shortcuts: list[list[str]] = []
        for chunk in str(raw).replace("\n", ",").split(","):
            parts = [part.strip().lower() for part in chunk.replace("+", " ").split() if part.strip()]
            if parts:
                shortcuts.append(parts[:3])
        return shortcuts[:4]

    def open_status(self) -> None:
        self.force_visible()
        window = self._utility_window("status", "Talk Dat! Status", "620x460", bg="#071113")
        if window is None:
            return
        self._make_glass_titlebar(window, "Status", "#071113")
        text = tk.Text(
            window,
            wrap="word",
            font=("Consolas", 10),
            bg="#102126",
            fg="#f2f5fb",
            insertbackground="#ffffff",
            selectbackground="#27514d",
            bd=0,
            padx=12,
            pady=12,
        )
        text.pack(fill="both", expand=True, padx=14, pady=(10, 8))

        def snapshot_text() -> str:
            provider = self.callbacks.get("status_provider")
            data = provider() if provider else {}
            if not isinstance(data, dict):
                data = {}
            lines = ["Talk Dat! status", "=" * 48, ""]
            for key in sorted(data):
                lines.append(f"{key}: {data[key]}")
            lines.extend(
                [
                    "",
                    "Credit safety",
                    "=" * 48,
                    f"Overlay state: {self.state}",
                    f"Last message: {self.last_status}",
                    f"Last preview: {self.last_preview}",
                    "Mic/Deepgram are active only when session_active is true.",
                    "Panic stop: Ctrl+Win+Esc or tray menu.",
                ]
            )
            return "\n".join(lines) + "\n"

        def refresh() -> None:
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("1.0", snapshot_text())
            text.configure(state="disabled")

        controls = tk.Frame(window, bg="#071113")
        controls.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(controls, text="Refresh", command=refresh, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Check updates", command=self._callback("check_updates"), style="Flow.TButton").pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(controls, text="Panic stop", command=self._callback("panic"), style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Close", command=window.destroy, style="Flow.TButton").pack(side="right")
        refresh()

    def _open_history_from_event(self, _event: tk.Event | None = None) -> str:
        self.open_history()
        return "break"

    def open_history(self) -> None:
        self.force_visible()
        window = self._utility_window("history", "Talk Dat! History", "900x640", bg="#071113")
        if window is None:
            return
        self._make_glass_titlebar(window, "History", "#071113")

        header = tk.Frame(window, bg="#071113")
        header.pack(fill="x", padx=14, pady=(8, 6))
        tk.Label(
            header,
            text="Full dictation history",
            bg="#071113",
            fg="#f4f6fb",
            font=("Segoe UI Semibold", 12),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            header,
            text=str(full_history_path()),
            bg="#071113",
            fg="#9aa3b5",
            font=("Segoe UI", 9),
            anchor="e",
        ).pack(side="right")

        body = tk.Frame(window, bg="#071113")
        body.pack(fill="both", expand=True, padx=14)
        scrollbar = ttk.Scrollbar(body)
        scrollbar.pack(side="right", fill="y")
        text = tk.Text(
            body,
            wrap="word",
            undo=False,
            font=("Consolas", 10),
            bg="#102126",
            fg="#f2f5fb",
            insertbackground="#ffffff",
            selectbackground="#27514d",
            bd=0,
            padx=12,
            pady=12,
            yscrollcommand=scrollbar.set,
        )
        text.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=text.yview)

        def load_text() -> None:
            text.configure(state="normal")
            text.delete("1.0", "end")
            content = self._history_window_text()
            text.insert("1.0", content)
            text.configure(state="disabled")
            text.see("end")

        def copy_value(value: str) -> None:
            self.root.clipboard_clear()
            self.root.clipboard_append(value)
            self.set_state("captured", "History copied. Mic off.", "")

        def copy_all() -> None:
            copy_value(text.get("1.0", "end-1c"))

        def copy_selection() -> None:
            try:
                selected = text.get("sel.first", "sel.last")
            except tk.TclError:
                selected = text.get("1.0", "end-1c")
            copy_value(selected)

        def open_file(path: Path) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("", encoding="utf-8")
            try:
                os.startfile(str(path))  # type: ignore[attr-defined]
            except OSError:
                copy_value(str(path))

        def clear_history() -> None:
            try:
                clear_all_history()
            except OSError:
                pass
            for path in (full_history_path(), live_draft_path()):
                try:
                    if path.exists():
                        path.write_text("", encoding="utf-8")
                except OSError:
                    pass
            load_text()
            self.set_state("captured", "History cleared. Mic off.", "")

        controls = tk.Frame(window, bg="#071113")
        controls.pack(fill="x", padx=14, pady=12)
        ttk.Button(controls, text="Copy all", command=copy_all, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Copy selection", command=copy_selection, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Refresh", command=load_text, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Open history file", command=lambda: open_file(full_history_path()), style="Flow.TButton").pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(controls, text="Open live draft", command=lambda: open_file(live_draft_path()), style="Flow.TButton").pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(controls, text="Clear history", command=clear_history, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Close", command=window.destroy, style="Flow.TButton").pack(side="right")

        load_text()

    def open_local_models(self) -> None:
        self.force_visible()
        window = self._utility_window("local_models", "Talk Dat! Local Models", "900x660", bg="#071113")
        if window is None:
            return
        self._make_glass_titlebar(window, "Local Models", "#071113")
        self._local_model_downloads = getattr(self, "_local_model_downloads", set())

        header = tk.Frame(window, bg="#071113")
        header.pack(fill="x", padx=14, pady=(8, 4))
        tk.Label(
            header,
            text="On-device speech models",
            bg="#071113",
            fg="#f4f6fb",
            font=("Segoe UI Semibold", 12),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            header,
            text=str(local_models_dir()),
            bg="#071113",
            fg="#9aa3b5",
            font=("Segoe UI", 9),
            anchor="e",
        ).pack(side="right")
        tk.Label(
            window,
            text=(
                "Models download once, then transcribe with no API key and no internet. "
                "The active local model also auto-downloads on first use."
            ),
            bg="#071113",
            fg="#9aa3b5",
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=14)

        body = tk.Frame(window, bg="#071113")
        body.pack(fill="both", expand=True, padx=14, pady=(8, 0))
        canvas = tk.Canvas(body, bg="#071113", bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, command=canvas.yview)
        rows_frame = tk.Frame(canvas, bg="#071113")
        rows_window = canvas.create_window((0, 0), window=rows_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        rows_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(rows_window, width=e.width))

        def on_wheel(event: tk.Event) -> str:
            canvas.yview_scroll(-1 if getattr(event, "delta", 0) > 0 else 1, "units")
            return "break"

        window.bind("<MouseWheel>", on_wheel)

        def active_local_model_id() -> str:
            settings = provider_settings(self.config, "local")
            return str(settings.get("model") or DEFAULT_LOCAL_MODEL_ID)

        def set_active(model: Any) -> None:
            settings = provider_settings(self.config, "local")
            settings["model"] = model.id
            settings["variant"] = "auto"
            self.config.setdefault("stt", {})["provider"] = "local"
            self._callback("save_settings")()
            self.set_state("captured", f"Local model set: {model.label}", "Local / On-Device is now the active brand.")
            refresh()

        def start_download(model: Any) -> None:
            if model.id in self._local_model_downloads:
                return
            self._local_model_downloads.add(model.id)
            refresh()

            def worker() -> None:
                error = ""
                try:
                    download_local_model(model)
                except Exception as exc:
                    error = str(exc) or exc.__class__.__name__

                def done() -> None:
                    self._local_model_downloads.discard(model.id)
                    if error:
                        self.set_state("error", f"Model download failed: {error[:90]}")
                    else:
                        self.set_state("captured", f"{model.label} downloaded and ready.", "")
                    refresh()

                self.root.after(0, done)

            threading.Thread(target=worker, name=f"TalkDatModelDL-{model.id}", daemon=True).start()

        def remove(model: Any) -> None:
            delete_local_model(model)
            refresh()

        def refresh() -> None:
            if not window.winfo_exists():
                return
            for child in rows_frame.winfo_children():
                child.destroy()
            active_id = active_local_model_id()
            for model in LOCAL_MODELS:
                downloading = model.id in self._local_model_downloads
                downloaded = local_model_downloaded(model)
                row = tk.Frame(rows_frame, bg="#0d1c20")
                row.pack(fill="x", pady=3)
                title = model.label + ("   - active" if model.id == active_id else "")
                tk.Label(
                    row,
                    text=title,
                    bg="#0d1c20",
                    fg="#7ee2c3" if model.recommended else "#f2f5fb",
                    font=("Segoe UI Semibold", 10),
                    anchor="w",
                ).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))
                detail = f"{model.languages}  -  ~{model.size_mb} MB"
                if model.notes:
                    detail += f"  -  {model.notes}"
                tk.Label(
                    row,
                    text=detail,
                    bg="#0d1c20",
                    fg="#9aa3b5",
                    font=("Segoe UI", 9),
                    anchor="w",
                ).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 6))
                if downloading:
                    status = "Downloading..."
                elif downloaded:
                    status = f"Ready - {local_downloaded_size_mb(model)} MB on disk"
                else:
                    status = "Not downloaded"
                tk.Label(
                    row,
                    text=status,
                    bg="#0d1c20",
                    fg="#7ee2c3" if downloaded else "#9aa3b5",
                    font=("Segoe UI", 9),
                ).grid(row=0, column=1, rowspan=2, sticky="e", padx=10)
                actions = tk.Frame(row, bg="#0d1c20")
                actions.grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, 10))
                if downloaded:
                    ttk.Button(actions, text="Set active", command=lambda m=model: set_active(m), style="Flow.TButton").pack(
                        side="left", padx=(0, 6)
                    )
                    ttk.Button(actions, text="Delete", command=lambda m=model: remove(m), style="Flow.TButton").pack(side="left")
                elif not downloading:
                    download_button = ttk.Button(
                        actions, text="Download", command=lambda m=model: start_download(m), style="Flow.TButton"
                    )
                    download_button.pack(side="left", padx=(0, 6))
                    ttk.Button(actions, text="Set active", command=lambda m=model: set_active(m), style="Flow.TButton").pack(
                        side="left"
                    )
                row.columnconfigure(0, weight=1)

        controls = tk.Frame(window, bg="#071113")
        controls.pack(fill="x", padx=14, pady=12)
        ttk.Button(controls, text="Refresh", command=refresh, style="Flow.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Close", command=window.destroy, style="Flow.TButton").pack(side="right")
        refresh()

    def _history_window_text(self) -> str:
        sections: list[str] = []
        draft_path = live_draft_path()
        if draft_path.exists():
            draft = draft_path.read_text(encoding="utf-8", errors="replace").strip()
            if draft:
                sections.append("LIVE DRAFT\n" + "=" * 72 + "\n" + draft)

        full_path = full_history_path()
        full_text = ""
        if full_path.exists():
            full_text = full_path.read_text(encoding="utf-8", errors="replace").strip()
            if full_text:
                sections.append("FULL HISTORY\n" + "=" * 72 + "\n" + full_text)

        if not full_text:
            try:
                entries = create_history_store(self.config).recent(100)
            except OSError:
                entries = []
            if entries:
                blocks = []
                for entry in entries:
                    created = entry.get("created_at")
                    stamp = (
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(created)))
                        if isinstance(created, (int, float))
                        else ""
                    )
                    entry_type = str(entry.get("type", "entry")).replace("_", " ")
                    lines = [f"{stamp} - {entry_type}".strip(" -")]
                    for label, key in (("Command", "command"), ("Raw / original", "original"), ("Final / pasted", "text"), ("URL", "url")):
                        value = str(entry.get(key, "")).strip()
                        if value:
                            lines.append(f"{label}: {value}")
                    blocks.append("\n".join(lines))
                sections.append("STORED HISTORY\n" + "=" * 72 + "\n" + "\n\n".join(blocks))

        if not sections:
            sections.append(
                "No dictation history yet.\n\n"
                f"Full history file: {full_history_path()}\n"
                f"Live draft file: {live_draft_path()}\n"
            )
        return "\n\n".join(sections) + "\n"

    def _scratchpad_timestamp(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    def _new_scratchpad_tab(self, index: int, text: str = "") -> dict[str, Any]:
        now = self._scratchpad_timestamp()
        return {
            "id": f"note-{int(time.time() * 1000)}-{index}",
            "title": f"Note {index}",
            "text": text,
            "created_at": now,
            "updated_at": now,
        }

    def _clean_scratchpad_tab(self, raw: Any, index: int) -> dict[str, Any]:
        now = self._scratchpad_timestamp()
        if not isinstance(raw, dict):
            return self._new_scratchpad_tab(index)
        title = str(raw.get("title") or f"Note {index}").strip()[:64] or f"Note {index}"
        tab_id = str(raw.get("id") or f"note-{index}-{int(time.time() * 1000)}").strip()
        return {
            "id": tab_id,
            "title": title,
            "text": str(raw.get("text") or ""),
            "created_at": str(raw.get("created_at") or now),
            "updated_at": str(raw.get("updated_at") or raw.get("created_at") or now),
        }

    def _load_scratchpad_tabs(self) -> dict[str, Any]:
        path = scratchpad_tabs_path()
        legacy_path = scratchpad_path()
        raw_doc: dict[str, Any] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                raw_doc = loaded if isinstance(loaded, dict) else {}
            except (OSError, json.JSONDecodeError):
                raw_doc = {}

        raw_tabs = raw_doc.get("tabs")
        tabs = [
            self._clean_scratchpad_tab(tab, index + 1)
            for index, tab in enumerate(raw_tabs[:99] if isinstance(raw_tabs, list) else [])
        ]
        if not tabs:
            legacy_text = ""
            if legacy_path.exists():
                try:
                    legacy_text = legacy_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    legacy_text = ""
            tabs = [self._new_scratchpad_tab(1, legacy_text)]

        ids = {tab["id"] for tab in tabs}
        last_tab_id = str(raw_doc.get("last_tab_id") or tabs[0]["id"])
        if last_tab_id not in ids:
            last_tab_id = tabs[0]["id"]
        return {"version": 1, "last_tab_id": last_tab_id, "tabs": tabs[:99]}

    def _save_scratchpad_tabs(self, doc: dict[str, Any]) -> None:
        path = scratchpad_tabs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(path)

    def open_scratchpad(self) -> None:
        self.force_visible()
        doc = self._load_scratchpad_tabs()
        window = self._utility_window("scratchpad", "Talk Dat! Scratchpad", "980x680", bg="#040b0e")
        if window is None:
            return
        self._make_glass_titlebar(window, "Scratchpad", "#040b0e", "#fff2cf")

        active_id = {"value": str(doc["last_tab_id"])}
        pending_save = {"id": None}
        loading = {"value": False}
        refreshing_tabs = {"value": False}

        shell = tk.Frame(window, bg="#040b0e", bd=0, highlightthickness=0)
        shell.pack(fill="both", expand=True, padx=16, pady=(10, 14))
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        sidebar = tk.Frame(shell, bg="#061114", bd=0, highlightthickness=1, highlightbackground="#164b49")
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        sidebar.rowconfigure(1, weight=1)

        tk.Label(
            sidebar,
            text="Notes",
            bg="#061114",
            fg="#ffe1a3",
            font=("Segoe UI Semibold", 11),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))

        tab_list = tk.Listbox(
            sidebar,
            width=26,
            height=18,
            activestyle="none",
            exportselection=False,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            bg="#061114",
            fg="#d7f8f0",
            selectbackground="#123f3e",
            selectforeground="#fff2cf",
            font=("Segoe UI Semibold", 9),
        )
        tab_scroll = ttk.Scrollbar(sidebar, orient="vertical", command=tab_list.yview)
        tab_list.configure(yscrollcommand=tab_scroll.set)
        tab_list.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 8))
        tab_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))

        side_buttons = tk.Frame(sidebar, bg="#061114")
        side_buttons.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 12))

        main = tk.Frame(shell, bg="#040b0e", bd=0, highlightthickness=1, highlightbackground="#183b3d")
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        title_var = tk.StringVar()
        meta_var = tk.StringVar()
        save_var = tk.StringVar(value="Autosave ready")

        title_entry = tk.Entry(
            main,
            textvariable=title_var,
            bg="#071316",
            fg="#fff4d7",
            insertbackground="#ffdd91",
            relief="flat",
            font=("Segoe UI Semibold", 16),
            bd=0,
        )
        title_entry.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))

        meta = tk.Label(
            main,
            textvariable=meta_var,
            bg="#040b0e",
            fg="#8dbfba",
            font=("Segoe UI", 9),
            anchor="w",
        )
        meta.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        text_shell = tk.Frame(main, bg="#071316", bd=0, highlightthickness=1, highlightbackground="#1d5652")
        text_shell.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 10))
        text_shell.columnconfigure(0, weight=1)
        text_shell.rowconfigure(0, weight=1)

        text = tk.Text(
            text_shell,
            wrap="word",
            undo=True,
            font=("Cascadia Mono", 12),
            bg="#071316",
            fg="#f7f0dd",
            insertbackground="#ffd476",
            selectbackground="#255d58",
            selectforeground="#ffffff",
            bd=0,
            padx=18,
            pady=16,
            spacing1=3,
            spacing2=1,
            spacing3=7,
        )
        text_scroll = ttk.Scrollbar(text_shell, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=text_scroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        text_scroll.grid(row=0, column=1, sticky="ns")
        text.tag_configure("focus_line", background="#0d282b")
        text.tag_configure("recent_input", foreground="#ffe1a3")

        footer = tk.Frame(main, bg="#040b0e")
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        footer.columnconfigure(0, weight=1)
        save_label = tk.Label(
            footer,
            textvariable=save_var,
            bg="#040b0e",
            fg="#8dbfba",
            font=("Segoe UI", 9),
            anchor="w",
        )
        save_label.grid(row=0, column=0, sticky="ew")

        def active_tab() -> dict[str, Any]:
            tabs = doc["tabs"]
            for tab in tabs:
                if tab["id"] == active_id["value"]:
                    return tab
            active_id["value"] = tabs[0]["id"]
            return tabs[0]

        def tab_label(tab: dict[str, Any], index: int) -> str:
            updated = str(tab.get("updated_at", ""))[5:16].replace("-", "/")
            return f"{index + 1:02d}  {str(tab.get('title') or 'Untitled')[:18]:<18} {updated}"

        def refresh_tab_list() -> None:
            refreshing_tabs["value"] = True
            selected_index = 0
            tab_list.delete(0, "end")
            for index, tab in enumerate(doc["tabs"]):
                if tab["id"] == active_id["value"]:
                    selected_index = index
                tab_list.insert("end", tab_label(tab, index))
            tab_list.selection_clear(0, "end")
            tab_list.selection_set(selected_index)
            tab_list.activate(selected_index)
            tab_list.see(selected_index)
            refreshing_tabs["value"] = False

        def set_editor_from_tab(tab: dict[str, Any]) -> None:
            loading["value"] = True
            title_var.set(str(tab.get("title") or "Untitled"))
            text.delete("1.0", "end")
            text.insert("1.0", str(tab.get("text") or ""))
            meta_var.set(f"Created {tab.get('created_at', '')}   Updated {tab.get('updated_at', '')}")
            loading["value"] = False
            highlight_current_line()

        def save_now(mark_updated: bool = True, quiet: bool = False) -> None:
            if pending_save["id"] is not None:
                try:
                    window.after_cancel(pending_save["id"])
                except tk.TclError:
                    pass
                pending_save["id"] = None
            tab = active_tab()
            tab["title"] = title_var.get().strip()[:64] or "Untitled"
            tab["text"] = text.get("1.0", "end-1c")
            if mark_updated:
                tab["updated_at"] = self._scratchpad_timestamp()
            doc["last_tab_id"] = tab["id"]
            self._save_scratchpad_tabs(doc)
            meta_var.set(f"Created {tab.get('created_at', '')}   Updated {tab.get('updated_at', '')}")
            save_var.set(f"Saved {self._scratchpad_timestamp()} to {scratchpad_tabs_path()}")
            refresh_tab_list()
            if not quiet:
                self.set_state("captured", "Scratchpad saved.", str(scratchpad_tabs_path()))

        def schedule_save(_event: tk.Event | None = None) -> None:
            if loading["value"]:
                return
            save_var.set("Autosaving...")
            highlight_current_line(karaoke=True)
            if pending_save["id"] is not None:
                try:
                    window.after_cancel(pending_save["id"])
                except tk.TclError:
                    pass
            pending_save["id"] = window.after(520, lambda: save_now(mark_updated=True, quiet=True))

        def select_tab_by_index(index: int) -> None:
            if index < 0 or index >= len(doc["tabs"]):
                return
            save_now(mark_updated=True, quiet=True)
            active_id["value"] = doc["tabs"][index]["id"]
            doc["last_tab_id"] = active_id["value"]
            set_editor_from_tab(doc["tabs"][index])
            refresh_tab_list()
            save_now(mark_updated=False, quiet=True)
            text.focus_set()

        def on_tab_select(_event: tk.Event | None = None) -> None:
            if refreshing_tabs["value"]:
                return
            selection = tab_list.curselection()
            if not selection:
                return
            select_tab_by_index(int(selection[0]))

        def add_tab() -> None:
            if len(doc["tabs"]) >= 99:
                save_var.set("99 tabs max.")
                return
            save_now(mark_updated=True, quiet=True)
            tab = self._new_scratchpad_tab(len(doc["tabs"]) + 1)
            doc["tabs"].append(tab)
            active_id["value"] = tab["id"]
            doc["last_tab_id"] = tab["id"]
            set_editor_from_tab(tab)
            refresh_tab_list()
            save_now(mark_updated=False, quiet=True)
            text.focus_set()

        def delete_tab() -> None:
            tabs = doc["tabs"]
            current = active_tab()
            if len(tabs) <= 1:
                current["title"] = "Note 1"
                current["text"] = ""
                current["updated_at"] = self._scratchpad_timestamp()
                set_editor_from_tab(current)
                save_now(mark_updated=False, quiet=True)
                return
            index = tabs.index(current)
            del tabs[index]
            next_index = min(index, len(tabs) - 1)
            active_id["value"] = tabs[next_index]["id"]
            doc["last_tab_id"] = active_id["value"]
            set_editor_from_tab(tabs[next_index])
            refresh_tab_list()
            save_now(mark_updated=False, quiet=True)

        def highlight_current_line(karaoke: bool = False) -> None:
            text.tag_remove("focus_line", "1.0", "end")
            text.tag_add("focus_line", "insert linestart", "insert lineend+1c")
            if karaoke:
                text.tag_remove("recent_input", "1.0", "end")
                text.tag_add("recent_input", "insert linestart", "insert lineend+1c")
                window.after(260, lambda: text.tag_remove("recent_input", "1.0", "end"))

        def close_window() -> None:
            save_now(mark_updated=True, quiet=True)
            window.destroy()

        ttk.Button(side_buttons, text="New", command=add_tab, style="Flow.TButton").pack(
            side="left", padx=(0, 6), pady=4
        )
        ttk.Button(side_buttons, text="Delete", command=delete_tab, style="Flow.TButton").pack(
            side="left", padx=6, pady=4
        )
        ttk.Button(footer, text="Save", command=lambda: save_now(mark_updated=True), style="Flow.TButton").grid(
            row=0, column=1, padx=(10, 0)
        )
        ttk.Button(footer, text="Close", command=close_window, style="Flow.TButton").grid(row=0, column=2, padx=(8, 0))

        tab_list.bind("<<ListboxSelect>>", on_tab_select)
        title_var.trace_add("write", lambda *_args: schedule_save())
        text.bind("<KeyRelease>", schedule_save)
        text.bind("<<Paste>>", lambda _event: window.after(20, schedule_save))
        text.bind("<ButtonRelease-1>", lambda _event: highlight_current_line())
        window.protocol("WM_DELETE_WINDOW", close_window)

        set_editor_from_tab(active_tab())
        refresh_tab_list()
        text.focus_set()

    def close(self) -> None:
        callback = self.callbacks.get("quit")
        if callback:
            callback()
        else:
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()

    def destroy(self) -> None:
        self.root.after(0, self.root.destroy)
