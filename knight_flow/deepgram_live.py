from __future__ import annotations

import asyncio
import contextlib
import json
import math
import queue
import sys
import threading
import time
from array import array
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode


UpdateCallback = Callable[[str, bool], None]
StatusCallback = Callable[[str], None]
LevelCallback = Callable[[float], None]
DoneCallback = Callable[[str], None]
ErrorCallback = Callable[[str], None]


def bool_param(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_listen_url(params: dict[str, Any]) -> str:
    items: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None or value == "":
            continue
        if isinstance(value, list):
            for item in value:
                if str(item).strip():
                    items.append((key, str(item)))
        else:
            items.append((key, bool_param(value)))
    return "wss://api.deepgram.com/v1/listen?" + urlencode(items)


def rms_level(raw: bytes) -> float:
    if not raw:
        return 0.0
    sample_bytes = raw[: min(len(raw), 4096)]
    if len(sample_bytes) % 2:
        sample_bytes = sample_bytes[:-1]
    if not sample_bytes:
        return 0.0
    samples = array("h")
    samples.frombytes(sample_bytes)
    if sys.byteorder == "big":
        samples.byteswap()
    if not samples:
        return 0.0
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    return min(1.0, math.sqrt(mean_square) / 32768.0 * 6)


class DeepgramLiveSession:
    def __init__(
        self,
        *,
        api_key: str,
        params: dict[str, Any],
        max_seconds: int,
        no_speech_timeout_seconds: int,
        silence_timeout_seconds: int,
        tail_capture_ms: int,
        on_update: UpdateCallback,
        on_status: StatusCallback,
        on_level: LevelCallback,
        on_done: DoneCallback,
        on_error: ErrorCallback,
    ) -> None:
        self.api_key = api_key.strip()
        self.params = params
        self.max_seconds = max_seconds
        self.no_speech_timeout_seconds = no_speech_timeout_seconds
        self.silence_timeout_seconds = silence_timeout_seconds
        self.tail_capture_ms = tail_capture_ms
        self.on_update = on_update
        self.on_status = on_status
        self.on_level = on_level
        self.on_done = on_done
        self.on_error = on_error

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._cancel_event = threading.Event()
        self._audio_queue: queue.Queue[bytes | None] = queue.Queue(maxsize=240)
        self._final_parts: list[str] = []
        self._interim_text = ""
        self._done_called = False
        self._heard_voice = False
        self._last_voice_at = 0.0
        self._audio_closed = threading.Event()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set())

    def start(self) -> None:
        if not self.api_key:
            raise ValueError("deepgram_api_key_missing")
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_main, name="TalkDatDeepgram", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def cancel(self) -> None:
        self._cancel_event.set()
        self._audio_closed.set()
        self.stop()
        self._put_audio(None)

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def current_text(self) -> str:
        return " ".join([*self._final_parts, self._interim_text]).strip()

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:
            self._safe_error(str(exc) or exc.__class__.__name__)
            self._finish("")

    async def _run(self) -> None:
        import sounddevice as sd
        import websockets

        url = build_listen_url(self.params)
        headers = {"Authorization": f"Token {self.api_key}"}
        self._safe_status("starting")
        sample_rate = int(self.params.get("sample_rate", 16000))
        channels = int(self.params.get("channels", 1))

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if self._cancel_event.is_set() or self._audio_closed.is_set():
                return
            data = bytes(indata)
            self._put_audio(data)
            level = rms_level(data)
            if level >= 0.025:
                self._heard_voice = True
                self._last_voice_at = time.monotonic()
            self._safe_level(level)

        stream = sd.RawInputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            blocksize=0,
            callback=callback,
        )

        connect_kwargs = {"ping_interval": 20, "ping_timeout": 10, "close_timeout": 2}
        try:
            context = websockets.connect(url, additional_headers=headers, **connect_kwargs)
        except TypeError:
            context = websockets.connect(url, extra_headers=headers, **connect_kwargs)

        with stream:
            self._safe_status("warming")
            async with context as websocket:
                self._safe_status("connected")
                sender = asyncio.create_task(self._send_loop(websocket))
                receiver = asyncio.create_task(self._receive_loop(websocket))
                keepalive = asyncio.create_task(self._keepalive_loop(websocket))
                self._safe_status("listening")
                started = time.monotonic()
                self._last_voice_at = started

                while not self._stop_event.is_set():
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
                    await asyncio.sleep(0.04)

                await asyncio.sleep(max(0, self.tail_capture_ms) / 1000)
                self._audio_closed.set()
                self._put_audio(None)
                await asyncio.wait({sender}, timeout=1.5)
                with contextlib.suppress(Exception):
                    await websocket.send(json.dumps({"type": "CloseStream"}))
                await asyncio.wait({receiver}, timeout=2.0)
                keepalive.cancel()
                receiver.cancel()
                sender.cancel()

        self._finish(self.current_text())

    async def _send_loop(self, websocket: Any) -> None:
        while not self._cancel_event.is_set():
            chunk = await asyncio.to_thread(self._audio_queue.get)
            if chunk is None:
                break
            try:
                await websocket.send(chunk)
            except Exception:
                break

    async def _receive_loop(self, websocket: Any) -> None:
        async for raw in websocket:
            if isinstance(raw, bytes):
                continue
            self._handle_message(str(raw))

    async def _keepalive_loop(self, websocket: Any) -> None:
        while not self._stop_event.is_set() and not self._cancel_event.is_set():
            await asyncio.sleep(8)
            try:
                await websocket.send(json.dumps({"type": "KeepAlive"}))
            except Exception:
                return

    def _handle_message(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return

        msg_type = payload.get("type")
        if msg_type == "Results":
            transcript = str(
                payload.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
            ).strip()
            if not transcript:
                return
            if payload.get("is_final"):
                if not self._final_parts or self._final_parts[-1] != transcript:
                    self._final_parts.append(transcript)
                self._interim_text = ""
            else:
                self._interim_text = transcript

            combined = self.current_text()
            is_final = bool(payload.get("speech_final") or payload.get("from_finalize"))
            self._safe_update(combined, is_final)
            return

        if msg_type == "UtteranceEnd":
            self._safe_update(self.current_text(), True)
            return

        if msg_type in {"Error", "Warning"}:
            message = payload.get("message") or payload.get("description") or msg_type
            self._safe_error(str(message))

    def _put_audio(self, chunk: bytes | None) -> None:
        try:
            self._audio_queue.put_nowait(chunk)
        except queue.Full:
            if chunk is None:
                with contextlib.suppress(Exception):
                    self._audio_queue.get_nowait()
                    self._audio_queue.put_nowait(None)

    def _finish(self, text: str) -> None:
        if self._done_called or self._cancel_event.is_set():
            return
        self._done_called = True
        try:
            self.on_done(text.strip())
        except Exception:
            pass

    def _safe_update(self, text: str, is_final: bool) -> None:
        try:
            self.on_update(text, is_final)
        except Exception:
            pass

    def _safe_status(self, status: str) -> None:
        try:
            self.on_status(status)
        except Exception:
            pass

    def _safe_level(self, level: float) -> None:
        try:
            self.on_level(level)
        except Exception:
            pass

    def _safe_error(self, error: str) -> None:
        try:
            self.on_error(error)
        except Exception:
            pass
