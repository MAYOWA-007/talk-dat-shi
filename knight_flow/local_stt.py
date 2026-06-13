"""On-device speech-to-text: model catalog, downloader, and inference engines.

Engines are optional pip dependencies, imported lazily:
- onnx-asr (Parakeet, Canary, GigaAM) for the best CPU speed/accuracy.
- faster-whisper (Whisper + Distil-Whisper families) for deep multilingual coverage.

Models download once into %APPDATA%/TalkDat/models/<model-id> and never leave the machine.
"""

from __future__ import annotations

import contextlib
import shutil
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import app_dir


StatusCallback = Callable[[str], None]

READY_MARKER = ".talkdat-ready"


@dataclass(frozen=True)
class LocalModel:
    id: str
    label: str
    engine: str  # "onnx_asr" | "faster_whisper"
    engine_id: str
    size_mb: int
    languages: str
    recommended: bool = False
    notes: str = ""


DEFAULT_LOCAL_MODEL_ID = "parakeet-tdt-0.6b-v3"

LOCAL_MODELS: tuple[LocalModel, ...] = (
    LocalModel(
        "parakeet-tdt-0.6b-v3",
        "Parakeet TDT 0.6B v3 (recommended)",
        "onnx_asr",
        "nemo-parakeet-tdt-0.6b-v3",
        460,
        "25 European languages, auto-detect",
        recommended=True,
        notes="Best speed/accuracy on plain CPU. CC-BY-4.0.",
    ),
    LocalModel(
        "parakeet-tdt-0.6b-v2",
        "Parakeet TDT 0.6B v2",
        "onnx_asr",
        "nemo-parakeet-tdt-0.6b-v2",
        460,
        "English",
        notes="Slightly better English WER than v3. CC-BY-4.0.",
    ),
    LocalModel(
        "canary-1b-v2",
        "Canary 1B v2",
        "onnx_asr",
        "nemo-canary-1b-v2",
        700,
        "25 European languages",
        notes="Higher accuracy, slower on CPU. CC-BY-4.0.",
    ),
    LocalModel(
        "canary-180m-flash",
        "Canary 180M Flash",
        "onnx_asr",
        "istupakov/canary-180m-flash-onnx",
        150,
        "en, de, es, fr",
        notes="Small and quick. CC-BY-4.0.",
    ),
    LocalModel(
        "gigaam-v3-e2e-ctc",
        "GigaAM v3",
        "onnx_asr",
        "gigaam-v3-e2e-ctc",
        160,
        "Russian",
    ),
    LocalModel(
        "whisper-large-v3-turbo",
        "Whisper Large v3 Turbo",
        "faster_whisper",
        "large-v3-turbo",
        1600,
        "99 languages",
        notes="Best broad multilingual coverage. MIT.",
    ),
    LocalModel(
        "distil-large-v3.5",
        "Distil-Whisper Large v3.5",
        "faster_whisper",
        "distil-large-v3.5",
        1500,
        "English",
        notes="Newest distil release. MIT.",
    ),
    LocalModel(
        "whisper-large-v3",
        "Whisper Large v3",
        "faster_whisper",
        "large-v3",
        3100,
        "99 languages",
        notes="Maximum Whisper accuracy; heavy on CPU.",
    ),
    LocalModel("whisper-medium", "Whisper Medium", "faster_whisper", "medium", 1500, "99 languages"),
    LocalModel("whisper-medium.en", "Whisper Medium EN", "faster_whisper", "medium.en", 1500, "English"),
    LocalModel("whisper-small", "Whisper Small", "faster_whisper", "small", 480, "99 languages"),
    LocalModel("whisper-small.en", "Whisper Small EN", "faster_whisper", "small.en", 480, "English"),
    LocalModel("distil-medium.en", "Distil-Whisper Medium EN", "faster_whisper", "distil-medium.en", 750, "English"),
    LocalModel("distil-small.en", "Distil-Whisper Small EN", "faster_whisper", "distil-small.en", 330, "English"),
    LocalModel("whisper-base", "Whisper Base", "faster_whisper", "base", 145, "99 languages"),
    LocalModel("whisper-base.en", "Whisper Base EN", "faster_whisper", "base.en", 145, "English"),
    LocalModel("whisper-tiny", "Whisper Tiny", "faster_whisper", "tiny", 75, "99 languages"),
    LocalModel("whisper-tiny.en", "Whisper Tiny EN", "faster_whisper", "tiny.en", 75, "English"),
)

LOCAL_MODEL_BY_ID = {model.id: model for model in LOCAL_MODELS}

_ENGINES: dict[str, Any] = {}
_ENGINE_LOCK = threading.Lock()


class LocalSTTError(RuntimeError):
    pass


def models_dir() -> Path:
    root = app_dir() / "models"
    root.mkdir(parents=True, exist_ok=True)
    return root


def model_dir(model: LocalModel) -> Path:
    return models_dir() / model.id


def local_model_for_id(model_id: str) -> LocalModel:
    model = LOCAL_MODEL_BY_ID.get(str(model_id).strip())
    if model is None:
        return LOCAL_MODEL_BY_ID[DEFAULT_LOCAL_MODEL_ID]
    return model


def is_downloaded(model: LocalModel) -> bool:
    return (model_dir(model) / READY_MARKER).exists()


def downloaded_size_mb(model: LocalModel) -> int:
    root = model_dir(model)
    if not root.exists():
        return 0
    total = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    return int(total / (1024 * 1024))


def delete_model(model: LocalModel) -> None:
    with _ENGINE_LOCK:
        _ENGINES.pop(model.id, None)
        _ENGINES.pop(f"{model.id}:gpu", None)
    root = model_dir(model)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


def _gpu_providers() -> list[str]:
    try:
        import onnxruntime

        available = set(onnxruntime.get_available_providers())
    except Exception:
        return []
    preferred = [name for name in ("CUDAExecutionProvider", "DmlExecutionProvider") if name in available]
    return preferred + ["CPUExecutionProvider"] if preferred else []


def _load_onnx_asr(model: LocalModel, gpu: bool = False) -> Any:
    try:
        import onnx_asr
    except ImportError as exc:
        raise LocalSTTError(
            "Local models need the onnx-asr package. Install with: pip install \"onnx-asr[cpu,hub]\""
        ) from exc
    target = model_dir(model)
    target.mkdir(parents=True, exist_ok=True)
    quantization = "int8" if model.engine_id.startswith(("nemo-", "istupakov/")) else None
    providers = _gpu_providers() if gpu else None
    kwargs: dict[str, Any] = {"quantization": quantization}
    if providers:
        kwargs["providers"] = providers
    try:
        return onnx_asr.load_model(model.engine_id, str(target), **kwargs)
    except Exception:
        if quantization or providers:
            return onnx_asr.load_model(model.engine_id, str(target))
        raise


def _load_faster_whisper(model: LocalModel, gpu: bool = False) -> Any:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise LocalSTTError(
            "Local Whisper models need the faster-whisper package. Install with: pip install faster-whisper"
        ) from exc
    target = model_dir(model)
    target.mkdir(parents=True, exist_ok=True)
    device = "cuda" if gpu else "auto"
    try:
        return WhisperModel(model.engine_id, device=device, compute_type="int8", download_root=str(target))
    except Exception:
        if gpu:
            return WhisperModel(model.engine_id, device="auto", compute_type="int8", download_root=str(target))
        raise


def ensure_loaded(model: LocalModel, status_cb: StatusCallback | None = None, *, gpu: bool = False) -> Any:
    cache_key = f"{model.id}:gpu" if gpu else model.id
    with _ENGINE_LOCK:
        engine = _ENGINES.get(cache_key)
        if engine is not None:
            return engine
        if status_cb:
            status_cb("downloading_model" if not is_downloaded(model) else "loading_model")
        if model.engine == "onnx_asr":
            engine = _load_onnx_asr(model, gpu)
        elif model.engine == "faster_whisper":
            engine = _load_faster_whisper(model, gpu)
        else:
            raise LocalSTTError(f"Unknown local engine: {model.engine}")
        (model_dir(model) / READY_MARKER).write_text("ok", encoding="utf-8")
        _ENGINES[cache_key] = engine
        return engine


def download_model(model: LocalModel, status_cb: StatusCallback | None = None) -> None:
    ensure_loaded(model, status_cb)


def _pcm16_to_float32(pcm16: bytes, channels: int) -> Any:
    import numpy as np

    audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        usable = len(audio) - (len(audio) % channels)
        audio = audio[:usable].reshape(-1, channels).mean(axis=1)
    return audio


def _recognize_onnx(engine: Any, audio: Any, sample_rate: int) -> str:
    # Most onnx-asr models cap out around 20-30s per utterance; chain VAD for longer takes.
    if len(audio) > sample_rate * 25:
        with contextlib.suppress(Exception):
            import onnx_asr

            vad = onnx_asr.load_vad("silero")
            results = engine.with_vad(vad).recognize(audio, sample_rate=sample_rate)
            parts = []
            for result in results:
                text = getattr(result, "text", result)
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            if parts:
                return " ".join(parts)
    result = engine.recognize(audio, sample_rate=sample_rate)
    return result if isinstance(result, str) else str(getattr(result, "text", "") or "")


def _recognize_faster_whisper(engine: Any, audio: Any, language: str, task: str = "") -> str:
    lang = language.split("-")[0].lower() if language else None
    kwargs: dict[str, Any] = {"language": lang or None, "vad_filter": True}
    if task == "translate":
        kwargs["task"] = "translate"
        kwargs["language"] = None
    segments, _info = engine.transcribe(audio, **kwargs)
    return " ".join(segment.text.strip() for segment in segments if segment.text.strip())


def transcribe(
    *,
    model_id: str,
    pcm16: bytes,
    sample_rate: int,
    channels: int,
    language: str,
    gpu: bool = False,
    task: str = "",
    status_cb: StatusCallback | None = None,
) -> str:
    model = local_model_for_id(model_id)
    engine = ensure_loaded(model, status_cb, gpu=gpu)
    if status_cb:
        status_cb("transcribing")
    audio = _pcm16_to_float32(pcm16, max(1, channels))
    if model.engine == "onnx_asr":
        return _recognize_onnx(engine, audio, sample_rate)
    return _recognize_faster_whisper(engine, audio, language, task)
