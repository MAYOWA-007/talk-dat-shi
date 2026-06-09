from __future__ import annotations

import time
import uuid
from contextlib import suppress

import pyautogui
import pyperclip


pyautogui.PAUSE = 0.025

NO_LEADING_SPACE_STARTS = set(" \t\r\n.,;:!?)]}%")
NO_SPACE_AFTER_LEFT = set(" \t\r\n([{")


def clipboard_text() -> str:
    with suppress(Exception):
        value = pyperclip.paste()
        return "" if value is None else str(value)
    return ""


def copy_text(text: str) -> bool:
    for _attempt in range(6):
        try:
            pyperclip.copy(text)
            time.sleep(0.025)
            if clipboard_text() == text:
                return True
        except Exception:
            time.sleep(0.04)
    return False


def needs_leading_space(text: str, left_context: str) -> bool:
    if not text or not left_context:
        return False
    first = text[0]
    left = left_context[-1]
    if first in NO_LEADING_SPACE_STARTS:
        return False
    if text.startswith(("- ", "* ", "1. ", "\n")):
        return False
    if left in NO_SPACE_AFTER_LEFT:
        return False
    return True


def should_prefix_space(text: str) -> bool:
    if not text:
        return False
    if text[0] in NO_LEADING_SPACE_STARTS:
        return False
    if text.startswith(("- ", "* ", "1. ", "\n")):
        return False
    return True


def left_context_char(previous_clipboard: str, timeout: float = 0.08) -> str:
    sentinel = f"__TALK_DAT_SHI_CONTEXT_{uuid.uuid4().hex}__"
    try:
        copy_text(sentinel)
        pyautogui.hotkey("shift", "left")
        time.sleep(timeout)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(timeout)
        selected = clipboard_text()
        if not selected or selected == sentinel:
            return ""
        copy_text(selected)
        time.sleep(timeout)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(timeout)
        return selected[-1]
    except Exception:
        return ""
    finally:
        copy_text(previous_clipboard)


def apply_smart_leading_space(text: str, previous_clipboard: str) -> str:
    if should_prefix_space(text):
        return " " + text
    return text


def paste_text(
    text: str,
    *,
    send_enter: bool = False,
    restore_clipboard: bool = False,
    smart_leading_space: bool = False,
) -> bool:
    if not text and not send_enter:
        return False
    previous = clipboard_text()
    if text and smart_leading_space:
        text = apply_smart_leading_space(text, previous)
    if text and not copy_text(text):
        return False
    if text:
        time.sleep(0.06)

    try:
        if text:
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.08)
        if send_enter:
            pyautogui.press("enter")
        return True
    finally:
        if restore_clipboard:
            time.sleep(0.2)
            copy_text(previous)


def copy_selected_text(timeout: float = 0.18) -> tuple[str, str]:
    previous = clipboard_text()
    sentinel = f"__TALK_DAT_SHI_NO_SELECTION_{uuid.uuid4().hex}__"
    copy_text(sentinel)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(timeout)
    selected = clipboard_text()
    if selected == sentinel:
        restore_clipboard(previous)
        selected = ""
    return selected, previous


def restore_clipboard(text: str) -> None:
    copy_text(text)
