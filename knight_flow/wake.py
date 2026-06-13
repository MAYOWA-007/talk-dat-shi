"""Wake word listener (beta, opt-in).

Uses openWakeWord ONNX models when the optional `openwakeword` package is
installed. The microphone is only opened while the feature is enabled in
Settings; detection triggers the hands-free toggle.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class WakeWordListener:
    def __init__(self, config: dict[str, Any], *, on_wake: Callable[[], None], on_status: Callable[[str], None]) -> None:
        self.config = config
        self.on_wake = on_wake
        self.on_status = on_status
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="TalkDatWakeWord", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        settings = self.config.get("wake_word", {})
        model_name = str(settings.get("model", "hey_jarvis")) or "hey_jarvis"
        threshold = float(settings.get("threshold", 0.55))
        try:
            import numpy as np
            import sounddevice as sd
            from openwakeword.model import Model
        except ImportError:
            self.on_status("Wake word needs the openwakeword package: pip install openwakeword")
            return
        try:
            model = Model(wakeword_models=[model_name], inference_framework="onnx")
        except Exception:
            try:
                import openwakeword.utils

                openwakeword.utils.download_models()
                model = Model(wakeword_models=[model_name], inference_framework="onnx")
            except Exception as exc:
                self.on_status(f"Wake word model failed to load: {exc}")
                return

        last_fired = 0.0
        chunk = 1280  # 80 ms at 16 kHz, openWakeWord's expected frame

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            nonlocal last_fired
            if self._stop_event.is_set():
                raise sd.CallbackStop
            audio = np.frombuffer(bytes(indata), dtype=np.int16)
            scores = model.predict(audio)
            if max(scores.values(), default=0.0) >= threshold and time.monotonic() - last_fired > 2.5:
                last_fired = time.monotonic()
                self.on_wake()

        try:
            with sd.RawInputStream(samplerate=16000, channels=1, dtype="int16", blocksize=chunk, callback=callback):
                self.on_status(f"Wake word listening for '{model_name}'.")
                while not self._stop_event.is_set():
                    time.sleep(0.25)
        except Exception as exc:
            self.on_status(f"Wake word stopped: {exc}")
