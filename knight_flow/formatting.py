"""Wispr-Flow-style dictation formatting.

This is the layer that turns a raw speech-to-text transcript into clean written
text: correct punctuation (including question marks), capitalization, removed
fillers and false starts, and structure (bullets, numbered steps, paragraphs)
inferred from the logic of what was said.

It is model-agnostic: it runs after ANY speech-to-text provider. When an AI
rewrite backend is configured (transforms.llm), it uses a strong LLM prompt.
Otherwise it falls back to a heuristic formatter so dictation still gets real
punctuation and structure with no key and no network.
"""

from __future__ import annotations

import re
from typing import Any

from .llm import llm_complete, llm_configured


FORMAT_SYSTEM_PROMPT = (
    "You are the formatting layer of a voice dictation app, like Wispr Flow. "
    "You receive a raw speech-to-text transcript and rewrite it as clean, "
    "well-formatted written text - the way a thoughtful person would type it.\n\n"
    "Rules:\n"
    "- Preserve the speaker's meaning, wording, and voice. Do NOT add new ideas, "
    "answer questions, or invent content.\n"
    "- Fix capitalization and punctuation. End questions with '?', statements with "
    "'.', and clearly emphatic lines with '!'.\n"
    "- Remove fillers (um, uh, like, you know) and false starts. When the speaker "
    "corrects themselves, keep only the corrected version.\n"
    "- Apply structure from the logic of what was said:\n"
    "  - When the speaker lists things, format them as a '- ' bulleted list.\n"
    "  - When the speaker gives ordered steps or says 'first, second, third', use a "
    "numbered list.\n"
    "  - Break into paragraphs at topic shifts.\n"
    "- Honor spoken formatting commands ('new line', 'new paragraph', 'bullet point', "
    "'number one') by applying them, never by printing the words.\n"
    "- Keep it tight: do not pad or change the register.\n"
    "- Output ONLY the formatted text. No preamble, no quotes, no explanations, no code fences."
)

FORMAT_INSTRUCTION = "Format the following dictation as clean written text."

# Words that, when a sentence starts with them, signal a question.
_WH_WORDS = {"what", "when", "where", "why", "how", "who", "whom", "whose", "which"}
_AUX_WORDS = {
    "is", "are", "am", "was", "were", "do", "does", "did", "can", "could", "will",
    "would", "shall", "should", "may", "might", "have", "has", "had", "ought",
    "isn't", "aren't", "wasn't", "weren't", "don't", "doesn't", "didn't", "can't",
    "couldn't", "won't", "wouldn't", "shouldn't", "haven't", "hasn't", "hadn't",
}
# Subjects that complete a yes/no inversion ("do you", "is it", "are we").
_SUBJECTS = {"you", "we", "they", "i", "he", "she", "it", "there", "this", "that", "these", "those"}

# Discourse markers spoken before the real start of a sentence.
_LEADING_DISCOURSE = {"so", "well", "okay", "ok", "now", "and", "but", "yeah", "like", "basically", "actually", "hey"}

# Pseudo-cleft statements that start with a wh-word followed immediately by a
# subject pronoun are NOT questions ("what we need is more tests", "how it
# works", "why they left"). A wh-word followed by anything else ("what time is
# it", "how would flow do that") is treated as a question.
_CLEFT_RE = re.compile(
    r"^(what|where|how|why|who)\s+(i|we|you|he|she|they|it|this|that)\b",
    re.IGNORECASE,
)

_ORDINALS = ("first", "firstly", "second", "secondly", "third", "thirdly", "fourth", "fourthly", "fifth", "fifthly")


def _strip_terminal(sentence: str) -> tuple[str, str]:
    match = re.search(r"([.!?]+)$", sentence)
    if match:
        return sentence[: match.start()].rstrip(), match.group(1)
    return sentence, ""


def is_question(sentence: str) -> bool:
    body = sentence.strip()
    if not body:
        return False
    body, terminal = _strip_terminal(body)
    if "?" in terminal:
        return True
    lowered = body.lower()
    words = re.findall(r"[a-z']+", lowered)
    # Skip leading discourse markers ("so do you think..." is still a question).
    while words and words[0] in _LEADING_DISCOURSE:
        words = words[1:]
    if not words:
        return False
    first = words[0]
    # Tag questions: "..., right", "..., correct", "..., okay".
    if re.search(r",\s*(right|correct|okay|ok|yeah|no)$", lowered):
        return True
    if first in _WH_WORDS:
        # Exclude pseudo-cleft statements ("what we need is ...").
        cleft_probe = " ".join(words)
        return not _CLEFT_RE.match(cleft_probe)
    if first in _AUX_WORDS:
        # Yes/no inversion is a strong signal; require a plausible subject nearby
        # to avoid imperatives ("do the dishes").
        if len(words) > 1 and words[1] in _SUBJECTS:
            return True
        return first in {"is", "are", "am", "was", "were", "isn't", "aren't", "wasn't", "weren't"}
    return False


def _terminal_for(sentence: str) -> str:
    if is_question(sentence):
        return "?"
    return "."


def _is_list_run(sentences: list[str]) -> bool:
    """True when the sentences read as a spoken list (3+ short parallel clauses)."""
    if len(sentences) < 3:
        return False
    short = sum(1 for s in sentences if len(s.split()) <= 9)
    return short >= max(3, int(len(sentences) * 0.7))


def _ordinal_index(sentence: str) -> int | None:
    first = re.findall(r"[a-z]+", sentence.lower())
    if not first:
        return None
    mapping = {
        "first": 1, "firstly": 1, "second": 2, "secondly": 2, "third": 3, "thirdly": 3,
        "fourth": 4, "fourthly": 4, "fifth": 5, "fifthly": 5, "next": 0, "then": 0, "finally": 0, "lastly": 0,
    }
    return mapping.get(first[0])


_ORDINAL_SPLIT_RE = re.compile(
    r"\b(first|firstly|second|secondly|third|thirdly|fourth|fourthly|fifth|fifthly|next|then|finally|lastly)\b",
    re.IGNORECASE,
)


def _numbered_from_run_on(block: str) -> str | None:
    """Split a run-on 'first... second... third...' utterance into a numbered list.

    Only triggers on an explicit ordinal sequence so ordinary prose using 'then'
    or 'next' is left alone.
    """
    lowered = block.lower()
    has_first = re.search(r"\bfirst(ly)?\b", lowered)
    has_second = re.search(r"\bsecond(ly)?\b", lowered)
    if not (has_first and has_second):
        return None
    parts = _ORDINAL_SPLIT_RE.split(block)
    # re.split with a capturing group yields [lead, marker, seg, marker, seg, ...].
    lead = parts[0].strip()
    items: list[str] = []
    for index in range(1, len(parts) - 1, 2):
        segment = parts[index + 1].strip(" ,.;:-\t")
        if segment:
            items.append(segment)
    if len(items) < 2:
        return None
    rendered = "\n".join(f"{number}. {_finish_sentence(item)}" for number, item in enumerate(items, 1))
    if lead:
        return f"{_finish_sentence(lead)}\n{rendered}"
    return rendered


def heuristic_format(text: str) -> str:
    """Punctuation, capitalization, and structure without an LLM."""
    from .text_pipeline import normalize_spaces, split_sentences

    text = apply_smart_newlines_safe(text)
    blocks = [block.strip() for block in re.split(r"\n{2,}", text) if block.strip()]
    if not blocks:
        blocks = [text]

    formatted_blocks: list[str] = []
    for block in blocks:
        numbered = _numbered_from_run_on(block)
        if numbered is not None:
            formatted_blocks.append(numbered)
            continue

        # Respect explicit newlines the user dictated; format each line's sentences.
        lines = block.split("\n")
        multi_line = len(lines) > 1
        rendered_lines: list[str] = []
        all_sentences: list[str] = []
        for line in lines:
            sentences = split_sentences(line) or ([line.strip()] if line.strip() else [])
            all_sentences.extend(sentences)
            rendered_lines.append("\n".join(_finish_sentence(s) for s in sentences))

        if not multi_line and _is_list_run(all_sentences) and _looks_like_list(block):
            formatted_blocks.append("\n".join(f"- {_finish_sentence(s, terminal='')}" for s in all_sentences))
        else:
            formatted_blocks.append("\n".join(line for line in rendered_lines if line))

    result = "\n\n".join(formatted_blocks)
    return normalize_spaces(result).replace(" \n", "\n")


def apply_smart_newlines_safe(text: str) -> str:
    from .text_pipeline import apply_smart_newlines

    return apply_smart_newlines(text)


def _looks_like_list(block: str) -> bool:
    cues = re.search(r"\b(the following|these are|such as|including|a few things|couple of things|list)\b", block, re.IGNORECASE)
    return bool(cues)


def _render_numbered(sentences: list[str]) -> str:
    lines: list[str] = []
    counter = 1
    for sentence in sentences:
        cleaned = re.sub(
            r"^(first(ly)?|second(ly)?|third(ly)?|fourth(ly)?|fifth(ly)?|next|then|finally|lastly)[,\s]+",
            "",
            sentence.strip(),
            flags=re.IGNORECASE,
        )
        lines.append(f"{counter}. {_finish_sentence(cleaned)}")
        counter += 1
    return "\n".join(lines)


def _finish_sentence(sentence: str, terminal: str | None = None) -> str:
    from .text_pipeline import capitalize_sentences

    body, _existing = _strip_terminal(sentence.strip())
    if not body:
        return ""
    body = capitalize_sentences(body)
    if terminal == "":
        return body
    mark = terminal if terminal else _terminal_for(sentence)
    return body + mark


def smart_format(text: str, config: dict[str, Any]) -> str:
    """Format dictation. Uses the configured LLM when available, else heuristics."""
    cleanup = config.get("cleanup", {})
    mode = str(cleanup.get("format_mode", "auto")).lower()
    if mode == "off":
        from .text_pipeline import normalize_spaces

        return normalize_spaces(text)

    use_ai = mode == "ai" or (mode == "auto" and llm_configured(config))
    if use_ai:
        output = llm_complete(FORMAT_SYSTEM_PROMPT, f"{FORMAT_INSTRUCTION}\n\n{text}", config)
        if output:
            return _strip_fences(output)
    return heuristic_format(text)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()
