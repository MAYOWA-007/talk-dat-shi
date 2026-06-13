"""Meeting transcription mode (beta).

Captures system output audio via WASAPI loopback where the installed PortAudio
build supports it, falling back to the microphone otherwise, chunks the audio
on a timer, transcribes each chunk with the currently selected provider, and
appends timestamped lines to a per-meeting Markdown file under
%APPDATA%/TalkDat/meetings.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import app_dir
from .stt_sessions import transcribe_pcm


StatusCallback = Callable[[str], None]
LineCallback = Callable[[str], None]


def meetings_dir() -> Path:
    path = app_dir() / "meetings"
    path.mkdir(parents=True, exist_ok=True)
    return path


class MeetingRecorder:
    def __init__(
        self,
        config: dict[str, Any],
        *,
        on_status: StatusCallback,
        on_line: LineCallback,
    ) -> None:
        self.config = config
        self.on_status = on_status
        self.on_line = on_line
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_seconds = int(config.get("meeting", {}).get("chunk_seconds", 25))
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pending = bytearray()
        self._lock = threading.Lock()
        self.path: Path | None = None
        self.using_loopback = False

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self.path = meetings_dir() / time.strftime("meeting-%Y%m%d-%H%M.md")
        self.path.write_text(f"# Meeting transcript - {time.strftime('%Y-%m-%d %H:%M')}\n\n", encoding="utf-8")
        self._thread = threading.Thread(target=self._run, name="TalkDatMeeting", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _open_stream(self, callback: Any) -> Any:
        import sounddevice as sd

        try:
            extra = sd.WasapiSettings(loopback=True)
            stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=0,
                extra_settings=extra,
                callback=callback,
            )
            self.using_loopback = True
            return stream
        except Exception:
            self.using_loopback = False
            return sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=0,
                callback=callback,
            )

    def _run(self) -> None:
        try:
            def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
                with self._lock:
                    self._pending.extend(bytes(indata))

            stream = self._open_stream(callback)
            source = "system audio" if self.using_loopback else "microphone (loopback unavailable)"
            self.on_status(f"Meeting mode recording from {source}.")
            last_flush = time.monotonic()
            with stream:
                while not self._stop_event.is_set():
                    time.sleep(0.2)
                    if time.monotonic() - last_flush >= max(8, self.chunk_seconds):
                        last_flush = time.monotonic()
                        self._flush_chunk()
            self._flush_chunk()
            self.on_status(f"Meeting mode stopped. Transcript: {self.path}")
        except Exception as exc:
            self.on_status(f"Meeting mode error: {exc}")

    def _flush_chunk(self) -> None:
        with self._lock:
            chunk = bytes(self._pending)
            self._pending.clear()
        # skip chunks with under half a second of audio
        if len(chunk) < self.sample_rate:
            return
        try:
            text = transcribe_pcm(self.config, chunk, self.sample_rate, self.channels)
        except Exception as exc:
            self.on_status(f"Meeting chunk failed: {exc}")
            return
        if not text:
            return
        line = f"**[{time.strftime('%H:%M:%S')}]** {text}"
        try:
            if self.path is not None:
                with self.path.open("a", encoding="utf-8") as file:
                    file.write(line + "\n\n")
        except OSError:
            pass
        self.on_line(text)
