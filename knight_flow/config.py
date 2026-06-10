from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any


APP_NAME = "TalkDatShi"


DEFAULT_CONFIG: dict[str, Any] = {
    "deepgram": {
        "api_key": "",
        "model": "nova-3",
        "language": "en-US",
        "sample_rate": 16000,
        "channels": 1,
        "encoding": "linear16",
        "smart_format": True,
        "punctuate": True,
        "interim_results": True,
        "endpointing": 300,
        "utterance_end_ms": 1000,
        "vad_events": True,
        "filler_words": False,
        "dictation": True,
        "numerals": True,
        "mip_opt_out": True,
        "extra": {},
    },
    "stt": {
        "provider": "deepgram",
        "providers": {
            "deepgram": {"api_key": "", "model": "nova-3", "variant": "streaming", "extra": {}},
            "openai": {"api_key": "", "model": "gpt-4o-transcribe", "variant": "json", "extra": {}},
            "elevenlabs": {"api_key": "", "model": "scribe_v2", "variant": "default", "extra": {}},
            "xai": {"api_key": "", "model": "grok-speech-to-text", "variant": "json", "extra": {}},
            "groq": {"api_key": "", "model": "whisper-large-v3", "variant": "json", "extra": {}},
            "mistral": {"api_key": "", "model": "voxtral-mini-transcribe-latest", "variant": "json", "extra": {}},
            "assemblyai": {"api_key": "", "model": "universal-3-pro", "variant": "default", "extra": {}},
            "google_gemini": {"api_key": "", "model": "gemini-2.5-pro", "variant": "default", "extra": {}},
            "custom_openai": {"api_key": "", "api_base": "", "model": "custom-model", "variant": "json", "extra": {}},
        },
    },
    "hotkeys": {
        "push_to_talk": [["ctrl", "cmd"]],
        "hands_free": [["ctrl", "cmd", "space"]],
        "command_mode": [["ctrl", "cmd", "alt"]],
        "cancel": [["esc"]],
        "panic": [["ctrl", "cmd", "esc"]],
        "paste_last": [["shift", "alt", "z"]],
        "copy_last": [["shift", "alt", "x"]],
        "polish": [["cmd", "alt", "1"]],
        "prompt_engineer": [["cmd", "alt", "2"]],
        "turn_to_list": [["cmd", "alt", "3"]],
        "view_diff": [["cmd", "alt", "o"]],
        "scratchpad": [],
    },
    "dictation": {
        "max_seconds": 5 * 60,
        "no_speech_timeout_seconds": 15,
        "silence_timeout_seconds": 45,
        "hold_max_seconds": 30 * 60,
        "hold_no_speech_timeout_seconds": 120,
        "hold_silence_timeout_seconds": 300,
        "tail_capture_ms": 520,
        "hold_debounce_ms": 35,
        "auto_paste": True,
        "smart_leading_space": True,
        "restore_clipboard_after_paste": False,
        "press_enter_command": True,
        "play_sounds": True,
        "mute_output_while_recording": True,
    },
    "cleanup": {
        "level": "high",
        "auto_rewrite": True,
        "remove_fillers": True,
        "backtrack": True,
        "smart_newlines": True,
    },
    "dictionary": {
        "words": [
            "Deepgram",
            "OpenAI",
            "AssemblyAI",
        ],
        "replacements": [],
    },
    "snippets": [
        {"trigger": "my email signature", "text": "Best regards,\nYour Name"},
        {"trigger": "meeting link", "text": "Join the meeting: "},
    ],
    "transforms": {
        "enabled": True,
        "ollama": {
            "enabled": False,
            "url": "http://localhost:11434/api/generate",
            "model": "llama3.1",
        },
        "custom": [],
    },
    "overlay": {
        "show_on_start": True,
        "opacity": 0.94,
        "hover_fade_delay_ms": 2000,
        "hover_fade_opacity": 0.38,
        "width": 320,
        "height": 58,
        "active_pill_width": 320,
        "active_pill_height": 58,
        "active_width": 320,
        "active_height": 58,
        "compact_width": 110,
        "compact_height": 38,
        "wave_loop_start": 0,
        "wave_loop_end": 50,
        "active_frame_ms": 12,
        "idle_frame_ms": 33,
        "resize_frame_ms": 6,
        "resize_steps": 22,
        "active_loop_seconds": 2.6,
        "idle_loop_seconds": 8.0,
        "bottom_margin": 68,
        "result_hold_ms": 900,
        "error_hold_ms": 5200,
        "fixed_position": True,
        "no_activate": True,
        "hide_over_fullscreen_media": True,
        "fullscreen_poll_ms": 450,
        "fullscreen_tolerance_px": 8,
    },
    "privacy": {
        "save_audio": False,
        "save_history": True,
        "history_limit": 0,
    },
    "ui": {
        "theme": "dark",
        "settings_theme": "Flow Dark",
    },
    "onboarding": {
        "completed": False,
    },
    "updates": {
        "check_on_start": True,
        "auto_download": False,
        "current_version": "0.1.0",
        "last_checked_at": 0,
        "latest_version": "",
        "latest_release_url": "",
    },
}


def app_dir() -> Path:
    override = os.environ.get("TALK_DAT_SHI_HOME")
    if override:
        root = Path(override).expanduser()
    else:
        root = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def config_path() -> Path:
    return app_dir() / "config.json"


def history_path() -> Path:
    return app_dir() / "history.jsonl"


def full_history_path() -> Path:
    return app_dir() / "full-transcript-history.txt"


def live_draft_path() -> Path:
    return app_dir() / "live-transcript-draft.txt"


def scratchpad_path() -> Path:
    return app_dir() / "scratchpad.md"


def scratchpad_tabs_path() -> Path:
    return app_dir() / "scratchpad-tabs.json"


def load_project_env(start: Path | None = None) -> None:
    root = start or Path.cwd()
    candidates = [root / ".env", root / ".env.local", root / ".env.example"]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ and "put-your" not in value.lower():
                os.environ[key] = value


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def normalize_shortcuts(config: dict[str, Any]) -> dict[str, Any]:
    hotkeys = config.setdefault("hotkeys", {})
    for action, shortcuts in list(hotkeys.items()):
        if not isinstance(shortcuts, list):
            hotkeys[action] = []
            continue
        normalized: list[list[str]] = []
        for shortcut in shortcuts:
            if isinstance(shortcut, str):
                keys = [part.strip().lower() for part in shortcut.replace("+", " ").split()]
            elif isinstance(shortcut, list):
                keys = [str(part).strip().lower() for part in shortcut]
            else:
                continue
            keys = [key for key in keys if key]
            if keys:
                normalized.append(keys[:3])
        hotkeys[action] = normalized[:4]
    return config


def load_config(project_root: Path | None = None) -> dict[str, Any]:
    load_project_env(project_root)
    path = config_path()
    if not path.exists():
        save_config(DEFAULT_CONFIG)

    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        loaded = {}

    config = normalize_shortcuts(deep_merge(DEFAULT_CONFIG, loaded if isinstance(loaded, dict) else {}))
    env_key = os.environ.get("DEEPGRAM_API_KEY", "").strip()
    if env_key and not str(config.get("deepgram", {}).get("api_key", "")).strip():
        config["deepgram"]["api_key"] = env_key
    stt = config.setdefault("stt", {})
    providers = stt.setdefault("providers", {})
    deepgram_settings = providers.setdefault("deepgram", {})
    if str(config.get("deepgram", {}).get("api_key", "")).strip() and not str(deepgram_settings.get("api_key", "")).strip():
        deepgram_settings["api_key"] = config["deepgram"]["api_key"]
    if str(config.get("deepgram", {}).get("model", "")).strip() and not str(deepgram_settings.get("model", "")).strip():
        deepgram_settings["model"] = config["deepgram"]["model"]
    env_map = {
        "OPENAI_API_KEY": "openai",
        "ELEVENLABS_API_KEY": "elevenlabs",
        "XAI_API_KEY": "xai",
        "GROQ_API_KEY": "groq",
        "MISTRAL_API_KEY": "mistral",
        "ASSEMBLYAI_API_KEY": "assemblyai",
        "GEMINI_API_KEY": "google_gemini",
    }
    for env_name, provider_id in env_map.items():
        value = os.environ.get(env_name, "").strip()
        settings = providers.setdefault(provider_id, {})
        if value and not str(settings.get("api_key", "")).strip():
            settings["api_key"] = value
    return config


def save_config(config: dict[str, Any]) -> None:
    path = config_path()
    path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")


def deepgram_params(config: dict[str, Any]) -> dict[str, Any]:
    dg = config.get("deepgram", {})
    deepgram_stt = config.get("stt", {}).get("providers", {}).get("deepgram", {})
    params = {
        "model": deepgram_stt.get("model") or dg.get("model", "nova-3"),
        "language": dg.get("language", "en-US"),
        "encoding": dg.get("encoding", "linear16"),
        "sample_rate": int(dg.get("sample_rate", 16000)),
        "channels": int(dg.get("channels", 1)),
        "smart_format": bool(dg.get("smart_format", True)),
        "punctuate": bool(dg.get("punctuate", True)),
        "interim_results": bool(dg.get("interim_results", True)),
        "endpointing": dg.get("endpointing", 300),
        "utterance_end_ms": dg.get("utterance_end_ms", 1000),
        "vad_events": bool(dg.get("vad_events", True)),
        "filler_words": bool(dg.get("filler_words", False)),
        "dictation": bool(dg.get("dictation", True)),
        "numerals": bool(dg.get("numerals", True)),
        "mip_opt_out": bool(dg.get("mip_opt_out", True)),
    }
    words = config.get("dictionary", {}).get("words", [])
    if words:
        params["keyterm"] = [str(word) for word in words if str(word).strip()]
    extra = dg.get("extra", {})
    if isinstance(extra, dict):
        for key, value in extra.items():
            clean_key = str(key).strip()
            if clean_key:
                params[clean_key] = value
    return params
