from __future__ import annotations

import difflib
import json
import re
import urllib.request
from dataclasses import dataclass
from typing import Any


FILLER_RE = re.compile(
    r"\b(?:um+|uh+|erm+|ah+|hmm+|you know|kind of|sort of)\b[\s,]*",
    re.IGNORECASE,
)
SPACING_RE = re.compile(r"\s+")
PUNCT_SPACE_RE = re.compile(r"\s+([,.;:!?])")
END_PRESS_ENTER_RE = re.compile(r"(?:\s+|^)(?:press|hit)\s+enter[\s.!?]*$", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+|www\.\S+|\[[^\]]+\]\([^)]+\)|<a\s+[^>]*>.*?</a>", re.IGNORECASE)
COMMON_CORRECTIONS = [
    (re.compile(r"\btheir going to\b", re.IGNORECASE), "they're going to"),
    (re.compile(r"\bthere not\b", re.IGNORECASE), "they're not"),
    (re.compile(r"\btommorow\b", re.IGNORECASE), "tomorrow"),
]


@dataclass
class ProcessedText:
    original: str
    text: str
    send_enter: bool = False


def normalize_spaces(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = PUNCT_SPACE_RE.sub(r"\1", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [part.strip(" -\t") for part in parts if part.strip(" -\t")]


def capitalize_sentences(text: str) -> str:
    if not text:
        return text

    def cap(match: re.Match[str]) -> str:
        prefix, char = match.group(1), match.group(2)
        return f"{prefix}{char.upper()}"

    text = re.sub(r"(^|[.!?]\s+|\n+)([a-z])", cap, text)
    text = re.sub(r"\bi\b", "I", text)
    return text


def add_terminal_punctuation(text: str) -> str:
    if not text:
        return text
    if text.endswith((".", "!", "?", ":", ";", ")", "]", '"', "'")):
        return text
    if "\n" in text or len(text.split()) <= 3:
        return text
    return text + "."


def apply_smart_newlines(text: str) -> str:
    replacements = [
        (r"\bnew paragraph\b", "\n\n"),
        (r"\bnew line\b", "\n"),
        (r"\bnext line\b", "\n"),
        (r"\btab key\b", "\t"),
    ]
    for pattern, value in replacements:
        text = re.sub(pattern, value, text, flags=re.IGNORECASE)

    text = re.sub(r"\bbullet point\b\s*", "\n- ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bnumber one\b\s*", "\n1. ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bnumber two\b\s*", "\n2. ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bnumber three\b\s*", "\n3. ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bnumber four\b\s*", "\n4. ", text, flags=re.IGNORECASE)
    return text


def remove_previous_phrase(text: str) -> str:
    text = text.rstrip()
    if not text:
        return ""

    sentence_boundaries = ".!?\n"
    stripped = text.rstrip(" \t")
    if stripped and stripped[-1] in sentence_boundaries:
        search_end = len(stripped) - 1
    else:
        search_end = len(stripped)

    boundary = max(stripped.rfind(mark, 0, search_end) for mark in sentence_boundaries)
    if boundary >= 0:
        return stripped[: boundary + 1].rstrip()
    return ""


def apply_backtrack(text: str) -> str:
    text = re.sub(r"^.*\bstart over\b", "", text, flags=re.IGNORECASE).strip()
    phrases = ["scratch that", "delete that", "remove that", "cancel that"]
    lowered = text.lower()
    for phrase in phrases:
        while phrase in lowered:
            index = lowered.index(phrase)
            before = text[:index].rstrip()
            after = text[index + len(phrase):].lstrip(" ,.;:-")
            before = remove_previous_phrase(before)
            text = normalize_spaces(f"{before} {after}")
            lowered = text.lower()
    return text


def replace_phrase(text: str, source: str, target: str) -> str:
    if not source:
        return text
    pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", re.IGNORECASE)
    return pattern.sub(target, text)


def apply_dictionary(text: str, config: dict[str, Any]) -> str:
    replacements = config.get("dictionary", {}).get("replacements", [])
    for item in replacements:
        source = str(item.get("from", "")).strip()
        target = str(item.get("to", "")).strip()
        if source and target:
            text = replace_phrase(text, source, target)
    return text


def apply_snippets(text: str, config: dict[str, Any]) -> str:
    snippets = config.get("snippets", [])
    ordered = sorted(snippets, key=lambda item: len(str(item.get("trigger", ""))), reverse=True)
    for item in ordered:
        trigger = str(item.get("trigger", "")).strip()
        expansion = str(item.get("text", ""))
        if not trigger:
            continue
        stripped = re.sub(r"[.!?]+$", "", text.strip(), flags=re.IGNORECASE)
        if stripped.lower() == trigger.lower():
            return expansion
        text = replace_phrase(text, trigger, expansion)
    return text


def cleanup_text(text: str, config: dict[str, Any]) -> str:
    cleanup = config.get("cleanup", {})
    level = str(cleanup.get("level", "medium")).lower()
    if level == "none":
        return normalize_spaces(text)

    if cleanup.get("backtrack", True):
        text = apply_backtrack(text)
    if cleanup.get("smart_newlines", True):
        text = apply_smart_newlines(text)
    if cleanup.get("remove_fillers", True):
        text = FILLER_RE.sub("", text)

    text = normalize_spaces(text)

    if level in {"light", "medium", "high"}:
        text = capitalize_sentences(text)

    if level in {"medium", "high"}:
        for pattern, replacement in COMMON_CORRECTIONS:
            text = pattern.sub(replacement, text)
        text = re.sub(r"\b(?:I think maybe|maybe we maybe|we maybe)\b", "I think", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(?:just wanted to|I just wanted to)\b", "I wanted to", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(?:really really|very very)\b", "very", text, flags=re.IGNORECASE)
        text = add_terminal_punctuation(text)

    if level == "high":
        text = re.sub(r"\b(?:could you please|can you please)\b", "Please", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*,\s*", ", ", text)
        text = capitalize_sentences(text)

    return normalize_spaces(text)


def process_dictation(raw: str, config: dict[str, Any]) -> ProcessedText:
    original = normalize_spaces(raw)
    text = original
    send_enter = False
    if config.get("dictation", {}).get("press_enter_command", True) and END_PRESS_ENTER_RE.search(text):
        send_enter = True
        text = END_PRESS_ENTER_RE.sub("", text).strip()

    text = apply_snippets(text, config)
    text = apply_dictionary(text, config)
    text = cleanup_text(text, config)
    return ProcessedText(original=original, text=text, send_enter=send_enter)


def protect_urls(text: str) -> tuple[str, dict[str, str]]:
    protected: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        token = f"__TALK_DAT_SHI_URL_{len(protected)}__"
        protected[token] = match.group(0)
        return token

    return URL_RE.sub(repl, text), protected


def restore_urls(text: str, protected: dict[str, str]) -> str:
    for token, value in protected.items():
        text = text.replace(token, value)
    return text


def transform_with_ollama(text: str, instruction: str, config: dict[str, Any]) -> str | None:
    ollama = config.get("transforms", {}).get("ollama", {})
    if not ollama.get("enabled"):
        return None

    payload = {
        "model": ollama.get("model", "llama3.1"),
        "stream": False,
        "prompt": (
            "Rewrite the text according to the instruction. Return only the rewritten text.\n\n"
            f"Instruction: {instruction}\n\nText:\n{text}"
        ),
    }
    data = json.dumps(payload).encode("utf-8")
    try:
        request = urllib.request.Request(
            str(ollama.get("url", "http://localhost:11434/api/generate")),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        output = str(body.get("response", "")).strip()
        return output or None
    except Exception:
        return None


def polish(text: str, config: dict[str, Any]) -> str:
    protected_text, urls = protect_urls(text)
    local_config = dict(config)
    local_config["cleanup"] = {**config.get("cleanup", {}), "level": "high"}
    output = cleanup_text(protected_text, local_config)
    return restore_urls(output, urls)


def make_concise(text: str) -> str:
    text = re.sub(r"\b(?:I wanted to|I am writing to)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:basically|honestly|actually|probably|maybe)\b[\s,]*", "", text, flags=re.IGNORECASE)
    return normalize_spaces(text)


def make_formal(text: str) -> str:
    replacements = {
        "hey": "Hello",
        "thanks": "Thank you",
        "got": "received",
        "thing": "item",
        "stuff": "details",
    }
    output = text
    for source, target in replacements.items():
        output = replace_phrase(output, source, target)
    output = capitalize_sentences(output)
    return add_terminal_punctuation(normalize_spaces(output))


def turn_to_list(text: str) -> str:
    pieces = split_sentences(text)
    if len(pieces) <= 1:
        pieces = [part.strip() for part in re.split(r"\s*(?:,|;|\band\b)\s*", text) if part.strip()]
    return "\n".join(f"- {capitalize_sentences(piece)}" for piece in pieces if piece)


def prompt_engineer(text: str) -> str:
    cleaned = normalize_spaces(text)
    return (
        "Task:\n"
        f"{cleaned}\n\n"
        "Context:\n"
        "- Use the available local project context.\n"
        "- Ask only if a missing detail blocks execution.\n\n"
        "Output:\n"
        "- Provide the completed work or a concise implementation plan.\n"
        "- Include verification steps."
    )


def empathize(text: str) -> str:
    text = normalize_spaces(text)
    if not text:
        return text
    return add_terminal_punctuation(
        "I hear you. " + text[0].lower() + text[1:] if text[0].isupper() else "I hear you. " + text
    )


def transform_text(text: str, transform_id: str, config: dict[str, Any], instruction: str | None = None) -> str:
    instruction = instruction or transform_id.replace("_", " ")
    ollama_output = transform_with_ollama(text, instruction, config)
    if ollama_output:
        return ollama_output

    transform_id = transform_id.lower()
    if transform_id in {"polish", "fix_grammar"}:
        return polish(text, config)
    if transform_id in {"prompt_engineer", "prompt"}:
        return prompt_engineer(text)
    if transform_id in {"turn_to_list", "list"}:
        return turn_to_list(text)
    if transform_id in {"formal", "make_formal"}:
        return make_formal(text)
    if transform_id in {"concise", "make_concise"}:
        return make_concise(text)
    if transform_id in {"empathize", "empathetic"}:
        return empathize(text)
    return polish(text, config)


def command_to_transform(command: str) -> str:
    command = command.lower()
    if "prompt" in command:
        return "prompt_engineer"
    if "list" in command or "bullets" in command or "bullet" in command:
        return "turn_to_list"
    if "formal" in command or "professional" in command or "polite" in command:
        return "formal"
    if "concise" in command or "short" in command or "brief" in command:
        return "concise"
    if "empath" in command or "kind" in command:
        return "empathize"
    return "polish"


def unified_diff(before: str, after: str) -> str:
    before_lines = before.splitlines() or [before]
    after_lines = after.splitlines() or [after]
    return "\n".join(
        difflib.unified_diff(before_lines, after_lines, fromfile="before", tofile="after", lineterm="")
    )
