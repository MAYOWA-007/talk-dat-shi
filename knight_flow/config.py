from __future__ import annotations

import copy
import json
import os
import shutil
from pathlib import Path
from typing import Any


APP_NAME = "TalkDat"
LEGACY_APP_NAME = APP_NAME + "".join(chr(value) for value in (83, 104, 105))


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
            "xai": {"api_key": "", "model": "grok-transcribe", "variant": "default", "extra": {}},
            "groq": {"api_key": "", "model": "whisper-large-v3", "variant": "json", "extra": {}},
            "mistral": {"api_key": "", "model": "voxtral-mini-2602", "variant": "json", "extra": {}},
            "assemblyai": {"api_key": "", "model": "universal-3-pro", "variant": "default", "extra": {}},
            "google_gemini": {"api_key": "", "model": "gemini-3.5-flash", "variant": "default", "extra": {}},
            "custom_openai": {"api_key": "", "api_base": "", "model": "custom-model", "variant": "json", "extra": {}},
            "local": {"api_key": "", "model": "parakeet-tdt-0.6b-v3", "variant": "auto", "extra": {}},
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
        "pin_last": [],
        "meeting_mode": [],
        "translate_last": [],
    },
    "meeting": {
        "chunk_seconds": 25,
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
        "censor_profanity": False,
        "smart_format": True,
        "format_mode": "auto",
    },
    "audio": {
        "input_device": "",
        "gain_boost": 1.0,
        "quiet_mode": False,
        "quiet_mode_boost": 3.0,
    },
    "profiles": [],
    "plugins": {
        "enabled": False,
    },
    "wake_word": {
        "enabled": False,
        "model": "hey_jarvis",
        "threshold": 0.55,
    },
    "remote": {
        "enabled": False,
        "port": 4670,
        "token": "",
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
        "translate_to": "English",
        "llm": {
            "provider": "none",
            "model": "",
            "api_key": "",
            "api_base": "",
            "timeout": 30,
        },
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
        "compact_width": 188,
        "compact_height": 44,
        "wave_loop_start": 0,
        "wave_loop_end": 50,
        "active_frame_ms": 12,
        "idle_frame_ms": 33,
        "resize_frame_ms": 6,
        "resize_steps": 12,
        "active_loop_seconds": 2.6,
        "idle_loop_seconds": 8.0,
        "bottom_margin": 68,
        "result_hold_ms": 900,
        "error_hold_ms": 5200,
        "fixed_position": True,
        "position": "bottom-center",
        "no_activate": True,
        "hide_over_fullscreen_media": True,
        "show_session_over_fullscreen": False,
        "fullscreen_poll_ms": 450,
        "fullscreen_tolerance_px": 8,
    },
    "privacy": {
        "save_audio": False,
        "save_history": True,
        "history_limit": 0,
        "history_backend": "jsonl",
        "redact_pii": False,
    },
    "ui": {
        "theme": "dark",
        "settings_theme": "Flow Dark",
        "reduce_motion": False,
    },
    "onboarding": {
        "completed": False,
    },
    "updates": {
        "check_on_start": True,
        "auto_download": False,
        "channel": "stable",
        "check_interval_hours": 24,
        "skip_version": "",
        "current_version": "0.1.1",
        "last_checked_at": 0,
        "latest_version": "",
        "latest_release_url": "",
    },
}


def _copy_missing_items(source_root: Path, destination_root: Path) -> None:
    destination_root.mkdir(parents=True, exist_ok=True)
    for item in source_root.iterdir():
        destination = destination_root / item.name
        if destination.exists():
            continue
        try:
            if item.is_dir():
                shutil.copytree(item, destination)
            else:
                shutil.copy2(item, destination)
        except OSError:
            pass


def _rename_legacy_root(legacy_root: Path) -> None:
    backup = legacy_root.with_name(f"{APP_NAME}LegacyBackup")
    candidate = backup
    index = 2
    while candidate.exists():
        candidate = backup.with_name(f"{backup.name}{index}")
        index += 1
    try:
        legacy_root.rename(candidate)
    except OSError:
        pass


def _migrate_legacy_app_dir(app_data: Path, root: Path) -> None:
    legacy_root = app_data / LEGACY_APP_NAME
    if not legacy_root.exists():
        return
    if not root.exists():
        try:
            legacy_root.rename(root)
            return
        except OSError:
            pass
    _copy_missing_items(legacy_root, root)
    _rename_legacy_root(legacy_root)


def _portable_root() -> Path | None:
    try:
        import sys

        base = Path(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]).resolve().parent
        if (base / "portable.flag").exists():
            return base / "TalkDatData"
    except Exception:
        return None
    return None


def app_dir() -> Path:
    override = os.environ.get("TALK_DAT_HOME")
    portable = _portable_root()
    if override:
        root = Path(override).expanduser()
    elif portable is not None:
        root = portable
    else:
        app_data = Path(os.environ.get("APPDATA", Path.home()))
        root = app_data / APP_NAME
        _migrate_legacy_app_dir(app_data, root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def config_path() -> Path:
    return app_dir() / "config.json"


def history_path() -> Path:
    return app_dir() / "history.jsonl"


def history_db_path() -> Path:
    return app_dir() / "history.db"


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


def _migrate_overlay_sizes(config: dict[str, Any], loaded: dict[str, Any]) -> None:
    """Bump the compact pill size for users still on the previous defaults, without
    touching configs where the size was customized."""
    overlay = config.setdefault("overlay", {})
    loaded_overlay = loaded.get("overlay", {}) if isinstance(loaded.get("overlay"), dict) else {}
    if int(loaded_overlay.get("compact_width", 110)) == 110 and int(loaded_overlay.get("compact_height", 38)) == 38:
        overlay["compact_width"] = 188
        overlay["compact_height"] = 44


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
    _migrate_overlay_sizes(config, loaded if isinstance(loaded, dict) else {})
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
