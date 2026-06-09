from __future__ import annotations

import math
import threading
import wave
from pathlib import Path

from .config import app_dir


SAMPLE_RATE = 48000
CHIME_VERSION = 4
OUTPUT_GAIN = 0.5


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _smoothstep(edge0: float, edge1: float, value: float) -> float:
    x = _clamp((value - edge0) / max(0.0001, edge1 - edge0), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _bell_env(t: float, start: float, attack: float, release: float, duration: float) -> float:
    local = t - start
    if local < 0.0 or local > duration:
        return 0.0
    up = _smoothstep(0.0, attack, local)
    down = 1.0 - _smoothstep(duration - release, duration, local)
    return up * down


def _soft_clip(value: float) -> float:
    return math.tanh(value * 1.35) / math.tanh(1.35)


def _add_stereo(
    samples: list[tuple[float, float]],
    index: int,
    value: float,
    pan: float = 0.0,
) -> None:
    pan = _clamp(pan, -1.0, 1.0)
    left_gain = math.cos((pan + 1.0) * math.pi / 4.0)
    right_gain = math.sin((pan + 1.0) * math.pi / 4.0)
    left, right = samples[index]
    samples[index] = (left + value * left_gain, right + value * right_gain)


def _add_reverb(samples: list[tuple[float, float]], delays: tuple[tuple[float, float], ...]) -> None:
    original = samples[:]
    total = len(samples)
    for delay_seconds, decay in delays:
        offset = int(SAMPLE_RATE * delay_seconds)
        if offset <= 0:
            continue
        for index in range(offset, total):
            left, right = samples[index]
            source_left, source_right = original[index - offset]
            samples[index] = (left + source_right * decay, right + source_left * decay)


def _write_wav(path: Path, samples: list[tuple[float, float]]) -> Path:
    frames = bytearray()
    for left, right in samples:
        left_sample = int(_clamp(_soft_clip(left * OUTPUT_GAIN)) * 32767)
        right_sample = int(_clamp(_soft_clip(right * OUTPUT_GAIN)) * 32767)
        frames.extend(left_sample.to_bytes(2, "little", signed=True))
        frames.extend(right_sample.to_bytes(2, "little", signed=True))

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(bytes(frames))
    return path


def _activation_chime(path: Path) -> Path:
    duration = 0.18
    total = int(SAMPLE_RATE * duration)
    samples = [(0.0, 0.0) for _ in range(total)]
    chord = [
        (329.63, 0.000, 0.017, -0.12),
        (493.88, 0.018, 0.013, 0.10),
    ]
    for index in range(total):
        t = index / SAMPLE_RATE
        swell = _smoothstep(0.0, 0.035, t) * (1.0 - _smoothstep(0.105, duration, t))
        felt = math.sin(2.0 * math.pi * 123.47 * t) * 0.0045 * swell
        _add_stereo(samples, index, felt, 0.0)
        for freq, start, gain, pan in chord:
            env = _bell_env(t, start, 0.018, 0.105, duration - start)
            if env <= 0.0:
                continue
            shimmer = 1.0 + 0.0018 * math.sin(2.0 * math.pi * 5.1 * t)
            tone = math.sin(2.0 * math.pi * freq * shimmer * t)
            tone += 0.10 * math.sin(2.0 * math.pi * freq * 2.002 * t + 0.22)
            tone += 0.020 * math.sin(2.0 * math.pi * freq * 3.004 * t + 1.1)
            _add_stereo(samples, index, tone * env * gain, pan)
    _add_reverb(samples, ((0.014, 0.055),))
    return _write_wav(path, samples)


def _deactivation_chime(path: Path) -> Path:
    duration = 0.15
    total = int(SAMPLE_RATE * duration)
    samples = [(0.0, 0.0) for _ in range(total)]
    phase_left = 0.0
    phase_right = 0.0
    for index in range(total):
        t = index / SAMPLE_RATE
        drop = 1.0 - _smoothstep(0.0, duration, t)
        bend = 1.0 - _smoothstep(0.0, 0.095, t)
        freq = 246.94 + 150.0 * bend
        phase_left += 2.0 * math.pi * freq / SAMPLE_RATE
        phase_right += 2.0 * math.pi * (freq * 0.997) / SAMPLE_RATE
        env = _bell_env(t, 0.0, 0.004, 0.110, duration)
        glass = math.sin(phase_left) + 0.12 * math.sin(phase_left * 2.01 + 0.7)
        glass += 0.035 * math.sin(phase_right * 4.01 + 1.4)
        _add_stereo(samples, index, glass * env * drop * 0.018, -0.05)

        low_env = math.exp(-t * 15.0) * (1.0 - _smoothstep(0.095, duration, t))
        low = math.sin(2.0 * math.pi * 73.42 * t) * low_env * 0.009
        _add_stereo(samples, index, low, 0.0)

        sparkle_env = _bell_env(t, 0.018, 0.004, 0.070, 0.11)
        sparkle = math.sin(2.0 * math.pi * 740.0 * t) + 0.10 * math.sin(2.0 * math.pi * 1110.0 * t)
        _add_stereo(samples, index, sparkle * sparkle_env * 0.0035, 0.20)
    _add_reverb(samples, ((0.012, 0.045),))
    return _write_wav(path, samples)


def _done_chime(path: Path) -> Path:
    duration = 0.55
    total = int(SAMPLE_RATE * duration)
    samples = [(0.0, 0.0) for _ in range(total)]
    notes = [(523.25, 0.0, 0.032, -0.22), (783.99, 0.055, 0.026, 0.22), (1046.50, 0.110, 0.018, 0.0)]
    for index in range(total):
        t = index / SAMPLE_RATE
        for freq, start, gain, pan in notes:
            env = _bell_env(t, start, 0.030, 0.30, duration - start)
            if env <= 0.0:
                continue
            tone = math.sin(2.0 * math.pi * freq * t)
            tone += 0.22 * math.sin(2.0 * math.pi * freq * 2.0 * t + 0.45)
            _add_stereo(samples, index, tone * env * gain, pan)
    _add_reverb(samples, ((0.039, 0.16), (0.077, 0.11)))
    return _write_wav(path, samples)


def ensure_chime(kind: str) -> Path | None:
    path = app_dir() / f"talk_dat_shi_chime_{kind}_v{CHIME_VERSION}.wav"
    if path.exists():
        return path
    if kind == "on":
        return _activation_chime(path)
    if kind == "off":
        return _deactivation_chime(path)
    return None


def play_chime(kind: str, *, enabled: bool = True) -> None:
    if not enabled:
        return

    def worker() -> None:
        try:
            import winsound

            path = ensure_chime(kind)
            if path is None:
                return
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            return

    threading.Thread(target=worker, name="TalkDatShiChime", daemon=True).start()
