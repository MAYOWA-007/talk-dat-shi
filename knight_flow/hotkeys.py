from __future__ import annotations

import ctypes
import threading
from collections.abc import Callable
from typing import Any

from pynput import keyboard, mouse


Callback = Callable[[], None]


ALIASES = {
    "win": "cmd",
    "windows": "cmd",
    "super": "cmd",
    "command": "cmd",
    "option": "alt",
    "opt": "alt",
    "escape": "esc",
    "return": "enter",
    "mouse4": "mouse4",
    "x1": "mouse4",
    "mouse5": "mouse5",
    "x2": "mouse5",
    "middle_click": "middle",
    "middleclick": "middle",
}


TAP_ACTIONS = [
    "cancel",
    "panic",
    "hands_free",
    "paste_last",
    "copy_last",
    "polish",
    "prompt_engineer",
    "turn_to_list",
    "view_diff",
    "scratchpad",
]
HOLD_ACTIONS = ["command_mode", "push_to_talk"]
WATCHDOG_INTERVAL_SECONDS = 0.025


VK_BY_NAME = {
    "ctrl": (0x11, 0xA2, 0xA3),
    "alt": (0x12, 0xA4, 0xA5),
    "shift": (0x10, 0xA0, 0xA1),
    "cmd": (0x5B, 0x5C),
    "space": (0x20,),
    "esc": (0x1B,),
    "enter": (0x0D,),
    "tab": (0x09,),
    "backspace": (0x08,),
    "delete": (0x2E,),
    "home": (0x24,),
    "end": (0x23,),
    "page_up": (0x21,),
    "page_down": (0x22,),
    "middle": (0x04,),
    "mouse4": (0x05,),
    "mouse5": (0x06,),
}


def physical_key_down(name: str) -> bool | None:
    try:
        user32 = ctypes.windll.user32
    except Exception:
        return None

    codes = VK_BY_NAME.get(name)
    if codes is None and len(name) == 1 and name.isalnum():
        codes = (ord(name.upper()),)
    elif codes is None and name.startswith("f") and name[1:].isdigit():
        number = int(name[1:])
        if 1 <= number <= 24:
            codes = (0x70 + number - 1,)
    elif codes is None and name.isdigit():
        codes = (int(name),)
    if codes is None:
        return None

    return any(bool(user32.GetAsyncKeyState(code) & 0x8000) for code in codes)


def canonical(name: str) -> str:
    name = name.strip().lower().replace(" ", "_")
    return ALIASES.get(name, name)


def key_name(key: keyboard.Key | keyboard.KeyCode) -> str | None:
    special = {
        keyboard.Key.ctrl_l: "ctrl",
        keyboard.Key.ctrl_r: "ctrl",
        keyboard.Key.ctrl: "ctrl",
        keyboard.Key.alt_l: "alt",
        keyboard.Key.alt_r: "alt",
        keyboard.Key.alt: "alt",
        keyboard.Key.shift_l: "shift",
        keyboard.Key.shift_r: "shift",
        keyboard.Key.shift: "shift",
        keyboard.Key.cmd_l: "cmd",
        keyboard.Key.cmd_r: "cmd",
        keyboard.Key.cmd: "cmd",
        keyboard.Key.space: "space",
        keyboard.Key.esc: "esc",
        keyboard.Key.enter: "enter",
        keyboard.Key.tab: "tab",
        keyboard.Key.backspace: "backspace",
        keyboard.Key.delete: "delete",
        keyboard.Key.home: "home",
        keyboard.Key.end: "end",
        keyboard.Key.page_up: "page_up",
        keyboard.Key.page_down: "page_down",
    }
    if key in special:
        return special[key]
    if isinstance(key, keyboard.KeyCode):
        if key.char:
            return canonical(key.char)
        if key.vk is not None:
            return str(key.vk)
    name = getattr(key, "name", None)
    return canonical(name) if name else None


def mouse_name(button: mouse.Button) -> str | None:
    if button == mouse.Button.middle:
        return "middle"
    if getattr(mouse.Button, "x1", None) is not None and button == mouse.Button.x1:
        return "mouse4"
    if getattr(mouse.Button, "x2", None) is not None and button == mouse.Button.x2:
        return "mouse5"
    return None


def normalize_hotkeys(hotkeys: dict[str, Any]) -> dict[str, list[set[str]]]:
    normalized: dict[str, list[set[str]]] = {}
    for action, shortcuts in hotkeys.items():
        action_shortcuts: list[set[str]] = []
        for shortcut in shortcuts or []:
            if not isinstance(shortcut, list):
                continue
            chord = {canonical(str(key)) for key in shortcut if str(key).strip()}
            if chord:
                action_shortcuts.append(chord)
        normalized[action] = action_shortcuts
    return normalized


class HotkeyController:
    def __init__(
        self,
        hotkeys: dict[str, Any],
        callbacks: dict[str, Callback],
        *,
        hold_debounce_ms: int = 140,
    ) -> None:
        self.hotkeys = normalize_hotkeys(hotkeys)
        self.callbacks = callbacks
        self.hold_debounce_ms = hold_debounce_ms
        self.pressed: set[str] = set()
        self.latched: set[str] = set()
        self.active_hold: str | None = None
        self.pending_hold: str | None = None
        self.pending_timer: threading.Timer | None = None
        self.lock = threading.RLock()
        self.keyboard_listener: keyboard.Listener | None = None
        self.mouse_listener: mouse.Listener | None = None
        self.watchdog_stop = threading.Event()
        self.watchdog_thread: threading.Thread | None = None

    def start(self) -> None:
        self.keyboard_listener = keyboard.Listener(on_press=self._on_key_press, on_release=self._on_key_release)
        self.mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
        self.keyboard_listener.start()
        self.mouse_listener.start()
        self.watchdog_stop.clear()
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()

    def update_config(self, hotkeys: dict[str, Any], *, hold_debounce_ms: int | None = None) -> None:
        stop_action: str | None = None
        with self.lock:
            if self.active_hold:
                stop_action = f"{self.active_hold}_stop"
            self.hotkeys = normalize_hotkeys(hotkeys)
            if hold_debounce_ms is not None:
                self.hold_debounce_ms = hold_debounce_ms
            self.latched.clear()
            self.active_hold = None
            self._cancel_pending()
        if stop_action:
            self._trigger(stop_action)

    def stop(self) -> None:
        self.watchdog_stop.set()
        self._cancel_pending()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.watchdog_thread and self.watchdog_thread.is_alive():
            self.watchdog_thread.join(timeout=0.2)
        with self.lock:
            self.pressed.clear()
            self.latched.clear()
            self.active_hold = None
            self.pending_hold = None

    def _matches(self, action: str) -> bool:
        return any(chord.issubset(self.pressed) for chord in self.hotkeys.get(action, []))

    def _physically_matches(self, action: str) -> bool:
        for chord in self.hotkeys.get(action, []):
            if not chord.issubset(self.pressed):
                continue
            if all(self._pressed_key_is_physically_down(name) for name in chord):
                return True
        return False

    def _pressed_key_is_physically_down(self, name: str) -> bool:
        physical = physical_key_down(name)
        if physical is None:
            return name in self.pressed
        return physical

    def _hold_key_names(self) -> set[str]:
        names: set[str] = set()
        for action in (self.active_hold, self.pending_hold):
            if not action:
                continue
            for chord in self.hotkeys.get(action, []):
                names.update(chord)
        return names

    def _matching_chord_size(self, action: str) -> int:
        matches = [len(chord) for chord in self.hotkeys.get(action, []) if chord.issubset(self.pressed)]
        return max(matches, default=0)

    def _best_tap_action(self) -> str | None:
        candidates: list[tuple[int, int, str]] = []
        for priority, action in enumerate(TAP_ACTIONS):
            if action in self.latched:
                continue
            chord_size = self._matching_chord_size(action)
            if chord_size:
                candidates.append((chord_size, -priority, action))
        if not candidates:
            return None
        return max(candidates)[2]

    def _trigger(self, action: str) -> None:
        callback = self.callbacks.get(action)
        if callback:
            try:
                callback()
            except Exception:
                pass

    def _on_key_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        name = key_name(key)
        if not name:
            return
        with self.lock:
            self.pressed.add(name)
            self._evaluate_press()

    def _on_key_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        name = key_name(key)
        if not name:
            return
        with self.lock:
            self.pressed.discard(name)
            self._evaluate_release()

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        name = mouse_name(button)
        if not name:
            return
        with self.lock:
            if pressed:
                self.pressed.add(name)
                self._evaluate_press()
            else:
                self.pressed.discard(name)
                self._evaluate_release()

    def _evaluate_press(self) -> None:
        tap_action = self._best_tap_action()
        if tap_action:
            self._cancel_pending()
            if self.active_hold:
                self.active_hold = None
            self.latched.add(tap_action)
            self._trigger(tap_action)
            return

        if self.active_hold:
            return

        for action in HOLD_ACTIONS:
            if self._matches(action):
                self._schedule_hold(action)
                return

    def _evaluate_release(self) -> None:
        for action in list(self.latched):
            if not self._matches(action):
                self.latched.discard(action)

        if self.pending_hold and not self._matches(self.pending_hold):
            self._cancel_pending()

        if self.active_hold and not self._matches(self.active_hold):
            action = self.active_hold
            self.active_hold = None
            self._trigger(f"{action}_stop")

    def _schedule_hold(self, action: str) -> None:
        if self.pending_hold == action:
            return
        self._cancel_pending()
        self.pending_hold = action
        self.pending_timer = threading.Timer(self.hold_debounce_ms / 1000, self._start_hold_if_still_down)
        self.pending_timer.daemon = True
        self.pending_timer.start()

    def _start_hold_if_still_down(self) -> None:
        with self.lock:
            action = self.pending_hold
            self.pending_hold = None
            self.pending_timer = None
            if not action or self.active_hold or not self._physically_matches(action):
                return
            for tap_action in TAP_ACTIONS:
                if tap_action != "cancel" and self._matches(tap_action):
                    return
            self.active_hold = action
            self._trigger(action)

    def _cancel_pending(self) -> None:
        if self.pending_timer:
            self.pending_timer.cancel()
        self.pending_timer = None
        self.pending_hold = None

    def _watchdog_loop(self) -> None:
        while not self.watchdog_stop.wait(WATCHDOG_INTERVAL_SECONDS):
            stop_action: str | None = None
            with self.lock:
                if not self.active_hold and not self.pending_hold:
                    continue

                for name in list(self._hold_key_names() & self.pressed):
                    physical = physical_key_down(name)
                    if physical is False:
                        self.pressed.discard(name)

                for action in list(self.latched):
                    if not self._matches(action):
                        self.latched.discard(action)

                if self.pending_hold and not self._physically_matches(self.pending_hold):
                    self._cancel_pending()

                if self.active_hold and not self._physically_matches(self.active_hold):
                    action = self.active_hold
                    self.active_hold = None
                    stop_action = f"{action}_stop"

            if stop_action:
                self._trigger(stop_action)
