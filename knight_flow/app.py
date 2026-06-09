from __future__ import annotations

import json
import logging
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from .chimes import play_chime
from .config import config_path, full_history_path, history_path, live_draft_path, load_config, save_config
from .hotkeys import HotkeyController
from .logger import configure_logging
from .overlay import Overlay
from .paste import copy_selected_text, copy_text, paste_text, restore_clipboard
from .single_instance import already_running, show_already_running_message
from .stt_registry import PROVIDER_BY_ID, provider_label, selected_model_id, selected_provider_id
from .stt_sessions import create_stt_session, selected_stt_api_key
from .text_pipeline import (
    command_to_transform,
    process_dictation,
    transform_text,
    unified_diff,
)
from .tray import TrayController


log = logging.getLogger(__name__)


class TalkDatShiApp:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[1]
        self.config = load_config(self.project_root)
        self.lock = threading.RLock()
        self.session: Any | None = None
        self.session_token: object | None = None
        self.session_chime_token: object | None = None
        self.session_mode = "idle"
        self.session_control = "idle"
        self.last_transcript = ""
        self.last_original = ""
        self.last_diff = ""

        callbacks = {
            "hands_free": self.toggle_hands_free,
            "cancel": self.cancel,
            "panic": self.panic_stop,
            "polish": lambda: self.run_transform("polish"),
            "prompt_engineer": lambda: self.run_transform("prompt_engineer"),
            "turn_to_list": lambda: self.run_transform("turn_to_list"),
            "view_diff": self.copy_last_diff,
            "scratchpad": self.open_scratchpad,
            "paste_last": self.paste_last,
            "copy_last": self.copy_last,
            "push_to_talk": self.start_push_to_talk,
            "push_to_talk_stop": self.stop_session,
            "command_mode": self.start_command_mode,
            "command_mode_stop": self.stop_session,
            "save_settings": self.save_settings,
            "quit": self.quit,
            "show": self.show_overlay,
            "hide": self.hide_overlay,
            "settings": self.open_settings,
            "status": self.open_status,
            "history": self.open_history,
            "status_provider": self.status_snapshot,
        }
        self.overlay = Overlay(self.config, callbacks)
        self.tray = TrayController(callbacks)
        self.hotkeys = HotkeyController(
            self.config.get("hotkeys", {}),
            callbacks,
            hold_debounce_ms=int(self.config.get("dictation", {}).get("hold_debounce_ms", 140)),
        )

    def run(self) -> None:
        log.info("Talk Dat Shi starting")
        provider_id = selected_provider_id(self.config)
        log.info(
            "Config loaded: stt_provider=%s model=%s cleanup=%s",
            provider_id,
            selected_model_id(self.config, provider_id),
            self.config.get("cleanup", {}).get("level"),
        )
        self.tray.start()
        self.hotkeys.start()
        self.overlay.set_state(
            "idle",
            "Hold Ctrl+Win to talk. Toggle only with Ctrl+Win+Space or Mic.",
            "Mic is off. STT is idle.",
        )
        self.overlay.force_visible()
        if self.needs_onboarding():
            self.overlay.root.after(450, self.overlay.open_onboarding)
        self.overlay.run()

    def needs_onboarding(self) -> bool:
        onboarding = self.config.setdefault("onboarding", {})
        if bool(onboarding.get("completed", False)):
            return False
        provider_id = selected_provider_id(self.config)
        provider = PROVIDER_BY_ID[provider_id]
        if provider.api_kind == "external":
            return False
        return not bool(selected_stt_api_key(self.config, provider_id))

    def start_push_to_talk(self) -> None:
        log.info("push_to_talk start")
        if self.stop_hands_free_if_active("push_to_talk"):
            return
        self.start_session("dictation", "Hold mode: release to stop.", control="hold")

    def start_command_mode(self) -> None:
        log.info("command_mode start")
        if self.stop_hands_free_if_active("command_mode"):
            return
        self.start_session("command", "Command: release keys to stop.", control="command_hold")

    def toggle_hands_free(self) -> None:
        with self.lock:
            active = self.session is not None
        if active:
            self.stop_session()
        else:
            log.info("hands_free start")
            self.start_session("dictation", "Hands-free: toggle to stop.", control="hands_free")

    def stop_hands_free_if_active(self, source: str) -> bool:
        with self.lock:
            should_stop = self.session is not None and self.session_control == "hands_free"
        if not should_stop:
            return False
        log.info("%s requested while hands_free active; stopping session", source)
        self.stop_session()
        return True

    def start_session(self, mode: str, message: str, *, control: str = "hold") -> None:
        with self.lock:
            if self.session is not None:
                log.info("session start ignored: already active")
                self.overlay.set_state("processing", "Still processing the previous dictation.")
                return

            provider_id = selected_provider_id(self.config)
            provider = PROVIDER_BY_ID[provider_id]
            model_id = selected_model_id(self.config, provider_id)
            api_key = selected_stt_api_key(self.config, provider_id)
            if not api_key and provider.api_kind != "external":
                log.error("missing STT API key for provider=%s", provider_id)
                self.overlay.set_state(
                    "error",
                    f"Missing {provider.label} API key.",
                    f"Add it in Settings > Providers or set {provider.env_key}.",
                )
                return

            token = object()
            self.session_token = token
            self.session_mode = mode
            self.session_control = control
            state = "command" if mode == "command" else "starting"
            self.overlay.set_state(state, message, "")
            limits = self.session_limits(control)

            session = create_stt_session(
                config=self.config,
                max_seconds=limits["max_seconds"],
                no_speech_timeout_seconds=limits["no_speech_timeout_seconds"],
                silence_timeout_seconds=limits["silence_timeout_seconds"],
                tail_capture_ms=int(self.config.get("dictation", {}).get("tail_capture_ms", 520)),
                on_update=lambda text, is_final, t=token, m=mode: self.on_session_update(t, m, text, is_final),
                on_status=lambda status, t=token, m=mode, c=control: self.on_session_status(t, m, status, c),
                on_level=lambda level: self.overlay.set_level(level),
                on_done=lambda text, t=token, m=mode: self.on_session_done(t, m, text),
                on_error=lambda error, t=token: self.on_session_error(t, error),
            )
            self.session = session

        try:
            session.start()
            log.info("session started: mode=%s provider=%s model=%s", mode, provider_id, model_id)
        except Exception as exc:
            with self.lock:
                if self.session is session:
                    self.session = None
                    self.session_token = None
                    self.session_chime_token = None
            self.overlay.set_state("error", f"Could not start {provider.label}: {exc}")
            log.exception("could not start STT provider=%s model=%s", provider_id, model_id)

    def session_limits(self, control: str) -> dict[str, int]:
        dictation = self.config.get("dictation", {})
        if control in {"hold", "command_hold"}:
            return {
                "max_seconds": int(dictation.get("hold_max_seconds", 30 * 60)),
                "no_speech_timeout_seconds": int(dictation.get("hold_no_speech_timeout_seconds", 120)),
                "silence_timeout_seconds": int(dictation.get("hold_silence_timeout_seconds", 300)),
            }
        return {
            "max_seconds": int(dictation.get("max_seconds", 5 * 60)),
            "no_speech_timeout_seconds": int(dictation.get("no_speech_timeout_seconds", 15)),
            "silence_timeout_seconds": int(dictation.get("silence_timeout_seconds", 45)),
        }

    def stop_session(self) -> None:
        with self.lock:
            session = self.session
        if session is None:
            return
        self.overlay.set_state("processing", "Finalizing. Mic closing.")
        self.play_sound("off")
        log.info("session stop requested")
        session.stop()

    def cancel(self) -> None:
        with self.lock:
            session = self.session
            self.session = None
            self.session_token = None
            self.session_chime_token = None
            self.session_mode = "idle"
            self.session_control = "idle"
        if session:
            session.cancel()
            self.play_sound("off")
            log.info("session cancelled")
        self.overlay.set_state("idle", "Hold Ctrl+Win to talk. Toggle only with Ctrl+Win+Space or Mic.", "")
        self.overlay.set_level(0)

    def on_session_status(self, token: object, mode: str, status: str, control: str) -> None:
        if not self.is_current(token):
            return
        if status == "warming":
            should_play = False
            with self.lock:
                if self.session_chime_token is not token:
                    self.session_chime_token = token
                    should_play = True
            if should_play:
                self.play_sound("on")
            self.overlay.set_state("starting", "Opening microphone.")
        elif status == "listening":
            state = "command" if mode == "command" else "listening"
            if mode == "command":
                message = "Command: release keys to stop."
            elif control == "hands_free":
                message = "Hands-free: toggle to stop."
            else:
                message = "Hold mode: release to stop."
            self.overlay.set_state(state, message)
        elif status == "connected":
            self.overlay.set_state("starting", "Connected. Opening microphone.")
        elif status == "transcribing":
            self.overlay.set_state("processing", "Transcribing audio.")
        elif status == "time_limit":
            self.overlay.set_state("processing", "Time limit reached. Finalizing.")
        elif status == "no_speech_timeout":
            self.overlay.set_state("processing", "No speech heard. Closing mic to protect credits.")
            log.info("credit guard: no speech timeout")
        elif status == "silence_timeout":
            self.overlay.set_state("processing", "Silence timeout. Closing mic to protect credits.")
            log.info("credit guard: silence timeout")
        else:
            self.overlay.set_state("starting", "Starting voice session.")

    def on_session_update(self, token: object, mode: str, text: str, is_final: bool) -> None:
        if not self.is_current(token):
            return
        state = "command" if mode == "command" else "listening"
        label = "Command" if mode == "command" else ("Captured" if is_final else "Hearing")
        self.write_live_draft(mode, text, is_final)
        self.overlay.set_state(state, f"{label}: {preview(text, 58)}", preview(text, 112))

    def on_session_error(self, token: object, error: str) -> None:
        if not self.is_current(token):
            return
        provider_id = selected_provider_id(self.config)
        self.overlay.set_state("error", f"{provider_label(provider_id)} error: {preview(error, 82)}")
        log.error("STT error provider=%s: %s", provider_id, error)

    def on_session_done(self, token: object, mode: str, raw_text: str) -> None:
        if not self.is_current(token):
            return
        with self.lock:
            self.session = None
            self.session_token = None
            self.session_chime_token = None
            self.session_mode = "idle"
            self.session_control = "idle"

        self.overlay.set_level(0)
        raw_text = raw_text.strip()
        self.write_live_draft(mode, raw_text, True)
        if not raw_text:
            self.overlay.set_state("idle", "No speech captured. Ready again.", "")
            log.info("session done: no speech captured")
            return

        if mode == "command":
            self.handle_command(raw_text)
        else:
            self.handle_dictation(raw_text)

    def handle_dictation(self, raw_text: str) -> None:
        self.overlay.set_state("processing", "Cleaning up transcript.", preview(raw_text, 112))
        processed = process_dictation(raw_text, self.config)
        log.info("dictation processed: raw_chars=%s final_chars=%s", len(raw_text), len(processed.text))
        self.last_original = processed.original
        self.last_transcript = processed.text
        self.last_diff = unified_diff(processed.original, processed.text)

        if not processed.text and not processed.send_enter:
            self.overlay.set_state("idle", "Nothing to paste. Ready again.", "")
            return

        if self.config.get("privacy", {}).get("save_history", True):
            self.add_history(
                {
                    "type": "dictation",
                    "original": processed.original,
                    "text": processed.text,
                    "send_enter": processed.send_enter,
                    "created_at": time.time(),
                }
            )

        pasted = True
        if self.config.get("dictation", {}).get("auto_paste", True):
            pasted = paste_text(
                processed.text,
                send_enter=processed.send_enter,
                restore_clipboard=bool(self.config.get("dictation", {}).get("restore_clipboard_after_paste", False)),
                smart_leading_space=bool(self.config.get("dictation", {}).get("smart_leading_space", True)),
            )
        if pasted:
            self.overlay.set_state("captured", "Pasted. Mic off.", preview(processed.text, 112))
        else:
            copy_text(processed.text)
            self.overlay.set_state("captured", "Copied. Mic off.", preview(processed.text, 112))

    def handle_command(self, command: str) -> None:
        self.overlay.set_state("processing", f"Running command: {preview(command, 72)}")
        selected, previous_clipboard = copy_selected_text()
        selected = selected.strip()

        if selected:
            transform_id = command_to_transform(command)
            output = transform_text(selected, transform_id, self.config, instruction=command)
            self.last_original = selected
            self.last_transcript = output
            self.last_diff = unified_diff(selected, output)
            paste_text(output, restore_clipboard=bool(self.config.get("dictation", {}).get("restore_clipboard_after_paste", False)))
            self.add_history(
                {
                    "type": "command_transform",
                    "command": command,
                    "original": selected,
                    "text": output,
                    "created_at": time.time(),
                }
            )
            self.overlay.set_state("captured", f"Applied {transform_id}.", preview(output, 112))
            return

        restore_clipboard(previous_clipboard)
        url = "https://www.perplexity.ai/search?q=" + quote_plus(command)
        webbrowser.open(url)
        self.add_history({"type": "command_search", "command": command, "url": url, "created_at": time.time()})
        self.overlay.set_state("captured", "Opened command search.", preview(command, 112))

    def run_transform(self, transform_id: str) -> None:
        selected, previous_clipboard = copy_selected_text()
        selected = selected.strip()
        source = selected or self.last_transcript
        if not source:
            restore_clipboard(previous_clipboard)
            self.overlay.set_state("error", "No selected text or last transcript to transform.")
            return

        output = transform_text(source, transform_id, self.config)
        self.last_original = source
        self.last_transcript = output
        self.last_diff = unified_diff(source, output)

        if selected:
            paste_text(output, restore_clipboard=bool(self.config.get("dictation", {}).get("restore_clipboard_after_paste", False)))
            message = f"Applied {transform_id} to selection."
        else:
            copy_text(output)
            restore_clipboard(previous_clipboard)
            copy_text(output)
            message = f"Copied {transform_id} result from last transcript."

        self.add_history(
            {
                "type": "transform",
                "transform": transform_id,
                "original": source,
                "text": output,
                "created_at": time.time(),
            }
        )
        self.overlay.set_state("captured", message, preview(output, 112))

    def paste_last(self) -> None:
        if not self.last_transcript:
            self.last_transcript = self.read_last_history_text()
        if not self.last_transcript:
            self.overlay.set_state("error", "No previous transcript to paste.")
            return
        paste_text(
            self.last_transcript,
            restore_clipboard=bool(self.config.get("dictation", {}).get("restore_clipboard_after_paste", False)),
            smart_leading_space=bool(self.config.get("dictation", {}).get("smart_leading_space", True)),
        )
        self.overlay.set_state("captured", "Pasted last transcript.", preview(self.last_transcript, 112))

    def copy_last(self) -> None:
        if not self.last_transcript:
            self.last_transcript = self.read_last_history_text()
        if not self.last_transcript:
            self.overlay.set_state("error", "No previous transcript to copy.")
            return
        copy_text(self.last_transcript)
        self.overlay.set_state("captured", "Copied last transcript.", preview(self.last_transcript, 112))

    def copy_last_diff(self) -> None:
        if not self.last_diff:
            self.overlay.set_state("error", "No cleanup diff yet.")
            return
        copy_text(self.last_diff)
        self.overlay.set_state("captured", "Copied last cleanup diff.", preview(self.last_diff, 112))

    def open_scratchpad(self) -> None:
        self.overlay.open_scratchpad()

    def open_settings(self) -> None:
        self.overlay.root.after(0, self.overlay.open_settings)

    def open_status(self) -> None:
        self.overlay.root.after(0, self.overlay.open_status)

    def open_history(self) -> None:
        self.overlay.root.after(0, self.overlay.open_history)

    def show_overlay(self) -> None:
        self.overlay.show()

    def hide_overlay(self) -> None:
        self.overlay.hide()

    def save_settings(self) -> None:
        save_config(self.config)
        self.hotkeys.update_config(
            self.config.get("hotkeys", {}),
            hold_debounce_ms=int(self.config.get("dictation", {}).get("hold_debounce_ms", 50)),
        )

    def panic_stop(self) -> None:
        log.info("panic stop requested")
        self.cancel()

    def status_snapshot(self) -> dict[str, Any]:
        with self.lock:
            session = self.session
            session_mode = self.session_mode
            session_control = self.session_control
        return {
            "app": "running",
            "overlay_state": self.overlay.state,
            "session_active": session is not None,
            "session_running": bool(session and session.running),
            "session_mode": session_mode,
            "session_control": session_control,
            "stt_provider": provider_label(selected_provider_id(self.config)),
            "model": selected_model_id(self.config, selected_provider_id(self.config)),
            "language": self.config.get("deepgram", {}).get("language", "en-US"),
            "auto_paste": bool(self.config.get("dictation", {}).get("auto_paste", True)),
            "save_history": bool(self.config.get("privacy", {}).get("save_history", True)),
            "config_path": str(config_path()),
            "history_path": str(history_path()),
            "live_draft_path": str(live_draft_path()),
            "full_history_path": str(full_history_path()),
        }

    def play_sound(self, kind: str) -> None:
        play_chime(kind, enabled=bool(self.config.get("dictation", {}).get("play_sounds", True)))

    def write_live_draft(self, mode: str, text: str, is_final: bool) -> None:
        text = text.strip()
        if not text:
            return
        try:
            path = live_draft_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            status = "final-ish" if is_final else "interim"
            path.write_text(
                f"Talk Dat Shi live draft\n"
                f"Updated: {timestamp()}\n"
                f"Mode: {mode}\n"
                f"Status: {status}\n\n"
                f"{text}\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def add_history(self, entry: dict[str, Any]) -> None:
        try:
            path = history_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(entry, ensure_ascii=True) + "\n")
            self.append_full_history(entry)
            self.trim_history(path)
        except OSError:
            pass

    def append_full_history(self, entry: dict[str, Any]) -> None:
        try:
            path = full_history_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            entry_type = str(entry.get("type", "entry")).replace("_", " ")
            lines = [
                "",
                "=" * 72,
                f"{timestamp()} - {entry_type}",
                "=" * 72,
            ]
            original = str(entry.get("original", "")).strip()
            command = str(entry.get("command", "")).strip()
            text = str(entry.get("text", "")).strip()
            url = str(entry.get("url", "")).strip()
            transform = str(entry.get("transform", "")).strip()
            if command:
                lines.extend(["", "Command:", command])
            if transform:
                lines.extend(["", "Transform:", transform])
            if original:
                lines.extend(["", "Raw / original:", original])
            if text:
                lines.extend(["", "Final / pasted:", text])
            if url:
                lines.extend(["", "Opened URL:", url])
            if not any([original, command, text, url, transform]):
                lines.extend(["", json.dumps(entry, ensure_ascii=False, indent=2)])
            with path.open("a", encoding="utf-8") as file:
                file.write("\n".join(lines).rstrip() + "\n")
        except OSError:
            pass


    def trim_history(self, path: Path) -> None:
        limit = int(self.config.get("privacy", {}).get("history_limit", 500))
        if limit <= 0:
            return
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) > limit:
                path.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")
        except OSError:
            pass

    def read_last_history_text(self) -> str:
        path = history_path()
        if not path.exists():
            return ""
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return ""
        for line in reversed(lines):
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = str(item.get("text", "")).strip()
            if text:
                return text
        return ""

    def is_current(self, token: object) -> bool:
        with self.lock:
            return token is self.session_token

    def quit(self) -> None:
        log.info("Talk Dat Shi quitting")
        with self.lock:
            session = self.session
            self.session = None
            self.session_token = None
        if session:
            session.cancel()
        self.hotkeys.stop()
        self.tray.stop()
        self.overlay.root.after(0, self.overlay.root.destroy)


def preview(text: str, limit: int) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)].rstrip() + "..."


def timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def main() -> None:
    configure_logging()
    if already_running():
        show_already_running_message()
        return
    app = TalkDatShiApp()
    app.run()
