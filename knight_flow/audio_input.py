"""Shared microphone input helpers: device selection and gain staging."""

from __future__ import annotations

from typing import Any


def resolve_input_device(setting: Any) -> int | None:
    """Map the audio.input_device config value to a sounddevice device index.

    Accepts an empty value (system default), a numeric index, or a case-insensitive
    name substring. Returns None for the default device or when no match exists.
    """
    raw = str(setting or "").strip()
    if not raw:
        return None
    if raw.lstrip("-").isdigit():
        return int(raw)
    try:
        import sounddevice as sd

        for index, device in enumerate(sd.query_devices()):
            if device.get("max_input_channels", 0) > 0 and raw.lower() in str(device.get("name", "")).lower():
                return index
    except Exception:
        return None
    return None


def list_input_devices() -> list[str]:
    try:
        import sounddevice as sd

        return [
            f"{index}: {device.get('name', '?')}"
            for index, device in enumerate(sd.query_devices())
            if device.get("max_input_channels", 0) > 0
        ]
    except Exception:
        return []


def effective_gain(config: dict[str, Any]) -> float:
    audio = config.get("audio", {})
    gain = float(audio.get("gain_boost", 1.0) or 1.0)
    if bool(audio.get("quiet_mode", False)):
        gain *= float(audio.get("quiet_mode_boost", 3.0) or 3.0)
    return max(0.1, min(16.0, gain))


def apply_gain(pcm16: bytes, gain: float) -> bytes:
    if abs(gain - 1.0) < 1e-3 or not pcm16:
        return pcm16
    try:
        import numpy as np

        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) * gain
        return np.clip(audio, -32768, 32767).astype(np.int16).tobytes()
    except Exception:
        return pcm16
