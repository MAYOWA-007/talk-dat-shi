from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import threading
import time
import wave
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import deepgram_params
from .deepgram_live import DeepgramLiveSession, rms_level
from .stt_registry import PROVIDER_BY_ID, provider_settings, selected_model_id, selected_provider_id, selected_variant


UpdateCallback = Callable[[str, bool], None]
StatusCallback = Callable[[str], None]
LevelCallback = Callable[[float], None]
DoneCallback = Callable[[str], None]
ErrorCallback = Callable[[str], None]


class BatchSTTSession:
    def __init__(
        self,
        *,
        provider_id: str,
        api_key: str,
        api_base: str,
        model: str,
        variant: str,
        language: str,
        sample_rate: int,
        channels: int,
        max_seconds: int,
        no_speech_timeout_seconds: int,
        silence_timeout_seconds: int,
        tail_capture_ms: int,
        extra: dict[str, Any],
        on_update: UpdateCallback,
        on_status: StatusCallback,
        on_level: LevelCallback,
        on_done: DoneCallback,
        on_error: ErrorCallback,
    ) -> None:
        self.provider_id = provider_id
        self.api_key = api_key.strip()
        self.api_base = api_base.strip().rstrip("/")
        self.model = model.strip()
        self.variant = variant.strip()
        self.language = language.strip()
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.max_seconds = max_seconds
        self.no_speech_timeout_seconds = no_speech_timeout_seconds
        self.silence_timeout_seconds = silence_timeout_seconds
        self.tail_capture_ms = tail_capture_ms
        self.extra = extra
        self.on_update = on_update
        self.on_status = on_status
        self.on_level = on_level
        self.on_done = on_done
        self.on_error = on_error

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._cancel_event = threading.Event()
        self._done_called = False
        self._heard_voice = False
        self._last_voice_at = 0.0
        self._current_text = ""
        self._audio = bytearray()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set())

    def start(self) -> None:
        if not self.api_key and self.provider_id not in {"local", "custom_openai"}:
            raise ValueError(f"{self.provider_id}_api_key_missing")
        if not self.model:
            raise ValueError(f"{self.provider_id}_model_missing")
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_main, name=f"TalkDatSTT-{self.provider_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def cancel(self) -> None:
        self._cancel_event.set()
        self.stop()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def current_text(self) -> str:
        return self._current_text.strip()

    def _thread_main(self) -> None:
        try:
            self._record_then_transcribe()
        except Exception as exc:
            self._safe_error(str(exc) or exc.__class__.__name__)
            self._finish("")

    def _record_then_transcribe(self) -> None:
        import sounddevice as sd

        self._safe_status("warming")
        self._last_voice_at = time.monotonic()

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if self._cancel_event.is_set():
                return
            data = bytes(indata)
            self._audio.extend(data)
            level = rms_level(data)
            if level >= 0.025:
                self._heard_voice = True
                self._last_voice_at = time.monotonic()
            self._safe_level(level)

        stream = sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=0,
            callback=callback,
        )

        started = time.monotonic()
        with stream:
            self._safe_status("listening")
            while not self._stop_event.is_set() and not self._cancel_event.is_set():
                now = time.monotonic()
                if now - started >= self.max_seconds:
                    self._safe_status("time_limit")
                    self.stop()
                    break
                if not self._heard_voice and now - started >= self.no_speech_timeout_seconds:
                    self._safe_status("no_speech_timeout")
                    self.stop()
                    break
                if self._heard_voice and now - self._last_voice_at >= self.silence_timeout_seconds:
                    self._safe_status("silence_timeout")
                    self.stop()
                    break
                time.sleep(0.025)
            if not self._cancel_event.is_set():
                time.sleep(max(0, self.tail_capture_ms) / 1000)

        self._safe_level(0)
        if self._cancel_event.is_set():
            return
        if len(self._audio) < max(512, self.sample_rate * self.channels):
            self._finish("")
            return

        self._safe_status("transcribing")
        wav_bytes = self._wav_bytes(bytes(self._audio))
        text = self._transcribe(wav_bytes).strip()
        self._current_text = text
        if text:
            self._safe_update(text, True)
        self._finish(text)

    def _wav_bytes(self, raw_pcm: bytes) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(self.channels)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(raw_pcm)
        return buffer.getvalue()

    def _transcribe(self, wav_bytes: bytes) -> str:
        if self.provider_id in {"openai", "groq", "xai", "mistral", "custom_openai"}:
            return self._transcribe_openai_compatible(wav_bytes)
        if self.provider_id == "elevenlabs":
            return self._transcribe_elevenlabs(wav_bytes)
        if self.provider_id == "assemblyai":
            return self._transcribe_assemblyai(wav_bytes)
        if self.provider_id == "google_gemini":
            return self._transcribe_gemini(wav_bytes)
        raise NotImplementedError(f"{self.provider_id} is registered, but its live adapter is not wired yet.")

    def _transcribe_openai_compatible(self, wav_bytes: bytes) -> str:
        base = self.api_base or "https://api.openai.com"
        if base.endswith("/openai"):
            url = base + "/v1/audio/transcriptions"
        else:
            url = base + "/v1/audio/transcriptions"
        response_format = self.variant if self.variant in {"json", "text", "verbose_json", "diarized_json"} else "json"
        fields: dict[str, str] = {"model": self.model, "response_format": response_format}
        if self.language:
            fields["language"] = self.language.split("-")[0]
        for key, value in self.extra.items():
            if isinstance(value, (str, int, float, bool)) and str(key).strip():
                fields[str(key)] = str(value).lower() if isinstance(value, bool) else str(value)
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload, content_type = multipart_form(fields, {"file": ("talk-dat.wav", wav_bytes, "audio/wav")})
        raw = http_request(url, method="POST", body=payload, headers={**headers, "Content-Type": content_type})
        if response_format == "text":
            return raw.decode("utf-8", errors="replace").strip()
        data = json.loads(raw.decode("utf-8", errors="replace"))
        return extract_text(data)

    def _transcribe_elevenlabs(self, wav_bytes: bytes) -> str:
        base = self.api_base or "https://api.elevenlabs.io"
        fields: dict[str, str] = {"model_id": self.model}
        if self.language:
            fields["language_code"] = self.language.split("-")[0]
        if self.variant == "diarize":
            fields["diarize"] = "true"
        if self.variant == "tag-audio-events":
            fields["tag_audio_events"] = "true"
        for key, value in self.extra.items():
            if isinstance(value, (str, int, float, bool)) and str(key).strip():
                fields[str(key)] = str(value).lower() if isinstance(value, bool) else str(value)
        payload, content_type = multipart_form(fields, {"file": ("talk-dat.wav", wav_bytes, "audio/wav")})
        raw = http_request(
            base + "/v1/speech-to-text",
            method="POST",
            body=payload,
            headers={"xi-api-key": self.api_key, "Content-Type": content_type},
        )
        data = json.loads(raw.decode("utf-8", errors="replace"))
        return extract_text(data)

    def _transcribe_assemblyai(self, wav_bytes: bytes) -> str:
        base = self.api_base or "https://api.assemblyai.com"
        headers = {"Authorization": self.api_key}
        upload_raw = http_request(
            base + "/v2/upload",
            method="POST",
            body=wav_bytes,
            headers={**headers, "Content-Type": "audio/wav"},
        )
        upload_url = json.loads(upload_raw.decode("utf-8", errors="replace")).get("upload_url")
        if not upload_url:
            raise RuntimeError("AssemblyAI upload did not return upload_url")
        body: dict[str, Any] = {"audio_url": upload_url, "speech_model": self.model}
        if self.language:
            body["language_code"] = self.language.split("-")[0]
        if self.variant == "speaker-labels":
            body["speaker_labels"] = True
        body.update(self.extra if isinstance(self.extra, dict) else {})
        transcript_raw = http_request(
            base + "/v2/transcript",
            method="POST",
            body=json.dumps(body).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
        )
        transcript_id = json.loads(transcript_raw.decode("utf-8", errors="replace")).get("id")
        if not transcript_id:
            raise RuntimeError("AssemblyAI transcript did not return id")
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline and not self._cancel_event.is_set():
            time.sleep(1.25)
            poll_raw = http_request(base + f"/v2/transcript/{transcript_id}", headers=headers)
            data = json.loads(poll_raw.decode("utf-8", errors="replace"))
            status = str(data.get("status", "")).lower()
            if status == "completed":
                return extract_text(data)
            if status == "error":
                raise RuntimeError(str(data.get("error") or "AssemblyAI transcription failed"))
        raise TimeoutError("AssemblyAI transcription timed out")

    def _transcribe_gemini(self, wav_bytes: bytes) -> str:
        base = self.api_base or "https://generativelanguage.googleapis.com"
        query = urlencode({"key": self.api_key})
        url = f"{base}/v1beta/models/{self.model}:generateContent?{query}"
        prompt = str(
            self.extra.get(
                "prompt",
                "Transcribe this audio exactly. Return only the spoken text, with punctuation and clean formatting.",
            )
        )
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(wav_bytes).decode("ascii")}},
                    ],
                }
            ]
        }
        raw = http_request(
            url,
            method="POST",
            body=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        data = json.loads(raw.decode("utf-8", errors="replace"))
        return extract_text(data)

    def _finish(self, text: str) -> None:
        if self._done_called or self._cancel_event.is_set():
            return
        self._done_called = True
        with contextlib.suppress(Exception):
            self.on_done(text.strip())

    def _safe_update(self, text: str, is_final: bool) -> None:
        with contextlib.suppress(Exception):
            self.on_update(text, is_final)

    def _safe_status(self, status: str) -> None:
        with contextlib.suppress(Exception):
            self.on_status(status)

    def _safe_level(self, level: float) -> None:
        with contextlib.suppress(Exception):
            self.on_level(level)

    def _safe_error(self, error: str) -> None:
        with contextlib.suppress(Exception):
            self.on_error(error)


def selected_stt_api_key(config: dict[str, Any], provider_id: str) -> str:
    settings = provider_settings(config, provider_id)
    provider = PROVIDER_BY_ID[provider_id]
    value = str(settings.get("api_key", "")).strip()
    if value:
        return value
    if provider_id == "deepgram":
        value = str(config.get("deepgram", {}).get("api_key", "")).strip()
        if value:
            return value
    return os.environ.get(provider.env_key, "").strip() if provider.env_key else ""


def create_stt_session(
    *,
    config: dict[str, Any],
    max_seconds: int,
    no_speech_timeout_seconds: int,
    silence_timeout_seconds: int,
    tail_capture_ms: int,
    on_update: UpdateCallback,
    on_status: StatusCallback,
    on_level: LevelCallback,
    on_done: DoneCallback,
    on_error: ErrorCallback,
) -> Any:
    provider_id = selected_provider_id(config)
    provider = PROVIDER_BY_ID[provider_id]
    settings = provider_settings(config, provider_id)
    api_key = selected_stt_api_key(config, provider_id)
    model = selected_model_id(config, provider_id)
    variant = selected_variant(config, provider_id)

    if provider_id == "deepgram" and provider.api_kind == "deepgram_stream":
        params = deepgram_params(config)
        params["model"] = model
        return DeepgramLiveSession(
            api_key=api_key,
            params=params,
            max_seconds=max_seconds,
            no_speech_timeout_seconds=no_speech_timeout_seconds,
            silence_timeout_seconds=silence_timeout_seconds,
            tail_capture_ms=tail_capture_ms,
            on_update=on_update,
            on_status=on_status,
            on_level=on_level,
            on_done=on_done,
            on_error=on_error,
        )

    if provider.api_kind == "external":
        details = provider.notes or "This provider needs a dedicated adapter before it can run inside Talk Dat!."
        raise NotImplementedError(f"{provider.label}: {details}")

    dg = config.get("deepgram", {})
    extra = settings.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}
    return BatchSTTSession(
        provider_id=provider_id,
        api_key=api_key,
        api_base=str(settings.get("api_base") or provider.api_base),
        model=model,
        variant=variant,
        language=str(settings.get("language") or dg.get("language", "en-US")),
        sample_rate=int(settings.get("sample_rate") or dg.get("sample_rate", 16000)),
        channels=int(settings.get("channels") or dg.get("channels", 1)),
        max_seconds=max_seconds,
        no_speech_timeout_seconds=no_speech_timeout_seconds,
        silence_timeout_seconds=silence_timeout_seconds,
        tail_capture_ms=tail_capture_ms,
        extra=extra,
        on_update=on_update,
        on_status=on_status,
        on_level=on_level,
        on_done=on_done,
        on_error=on_error,
    )


def multipart_form(fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    boundary = f"talkdat-{int(time.time() * 1000)}"
    parts: list[bytes] = []
    for key, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode("ascii"))
        parts.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        parts.append(str(value).encode("utf-8"))
        parts.append(b"\r\n")
    for key, (filename, content, content_type) in files.items():
        parts.append(f"--{boundary}\r\n".encode("ascii"))
        parts.append(
            f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
        )
        parts.append(content)
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def http_request(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 90.0,
) -> bytes:
    request = Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def extract_text(data: Any) -> str:
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return ""
    if isinstance(data.get("text"), str):
        return str(data["text"])
    if isinstance(data.get("transcript"), str):
        return str(data["transcript"])
    channel = data.get("channel")
    if isinstance(channel, dict):
        alternatives = channel.get("alternatives")
        if isinstance(alternatives, list) and alternatives:
            transcript = alternatives[0].get("transcript") if isinstance(alternatives[0], dict) else None
            if isinstance(transcript, str):
                return transcript
    candidates = data.get("candidates")
    if isinstance(candidates, list):
        texts: list[str] = []
        for candidate in candidates:
            content = candidate.get("content") if isinstance(candidate, dict) else None
            parts = content.get("parts") if isinstance(content, dict) else None
            if isinstance(parts, list):
                for part in parts:
                    text = part.get("text") if isinstance(part, dict) else None
                    if isinstance(text, str):
                        texts.append(text)
        if texts:
            return "\n".join(texts)
    return ""
