"""BYOK LLM rewrite backend for transforms.

Providers share one config shape under transforms.llm:
{"provider": "none|ollama|openai|anthropic|gemini|groq|custom",
 "model": "...", "api_key": "", "api_base": "", "timeout": 30}

API keys may also come from the matching environment variable. All requests
use stdlib urllib so no new dependencies are required.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "openai": {"api_base": "https://api.openai.com", "model": "gpt-5.2", "env_key": "OPENAI_API_KEY"},
    "anthropic": {"api_base": "https://api.anthropic.com", "model": "claude-haiku-4-5", "env_key": "ANTHROPIC_API_KEY"},
    "gemini": {
        "api_base": "https://generativelanguage.googleapis.com",
        "model": "gemini-3.1-flash-lite",
        "env_key": "GEMINI_API_KEY",
    },
    "groq": {"api_base": "https://api.groq.com/openai", "model": "llama-3.3-70b-versatile", "env_key": "GROQ_API_KEY"},
    "custom": {"api_base": "", "model": "", "env_key": "CUSTOM_LLM_API_KEY"},
}

SYSTEM_PROMPT = (
    "You rewrite dictated text. Follow the instruction exactly. "
    "Return only the rewritten text with no preamble, labels, or quotes."
)


def llm_settings(config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("transforms", {}).get("llm", {})
    return settings if isinstance(settings, dict) else {}

def _api_key(settings: dict[str, Any], provider: str) -> str:
    key = str(settings.get("api_key", "")).strip()
    if key:
        return key
    env_key = PROVIDER_DEFAULTS.get(provider, {}).get("env_key", "")
    return os.environ.get(env_key, "").strip() if env_key else ""


def _post_json(url: str, body: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _rewrite_openai_compatible(
    text: str, instruction: str, *, api_base: str, api_key: str, model: str, timeout: float
) -> str:
    payload = _post_json(
        api_base.rstrip("/") + "/v1/chat/completions",
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Instruction: {instruction}\n\nText:\n{text}"},
            ],
        },
        {"Authorization": f"Bearer {api_key}"},
        timeout,
    )
    choices = payload.get("choices", [])
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message", {})
        return str(message.get("content", "")).strip()
    return ""


def _rewrite_anthropic(text: str, instruction: str, *, api_base: str, api_key: str, model: str, timeout: float) -> str:
    payload = _post_json(
        api_base.rstrip("/") + "/v1/messages",
        {
            "model": model,
            "max_tokens": 2048,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": f"Instruction: {instruction}\n\nText:\n{text}"}],
        },
        {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        timeout,
    )
    content = payload.get("content", [])
    parts = [str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text"]
    return "\n".join(parts).strip()


def _rewrite_gemini(text: str, instruction: str, *, api_base: str, api_key: str, model: str, timeout: float) -> str:
    payload = _post_json(
        f"{api_base.rstrip('/')}/v1beta/models/{model}:generateContent?key={api_key}",
        {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": f"Instruction: {instruction}\n\nText:\n{text}"}]}],
        },
        {},
        timeout,
    )
    candidates = payload.get("candidates", [])
    texts: list[str] = []
    for candidate in candidates:
        parts = candidate.get("content", {}).get("parts", []) if isinstance(candidate, dict) else []
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(part["text"])
    return "\n".join(texts).strip()


def llm_rewrite(text: str, instruction: str, config: dict[str, Any]) -> str | None:
    settings = llm_settings(config)
    provider = str(settings.get("provider", "none")).strip().lower()
    if provider in {"", "none", "ollama"}:
        return None
    defaults = PROVIDER_DEFAULTS.get(provider)
    if defaults is None:
        return None
    api_key = _api_key(settings, provider)
    api_base = str(settings.get("api_base", "")).strip() or defaults["api_base"]
    model = str(settings.get("model", "")).strip() or defaults["model"]
    timeout = float(settings.get("timeout", 30))
    if not api_key or not api_base or not model:
        return None
    try:
        if provider == "anthropic":
            output = _rewrite_anthropic(
                text, instruction, api_base=api_base, api_key=api_key, model=model, timeout=timeout
            )
        elif provider == "gemini":
            output = _rewrite_gemini(text, instruction, api_base=api_base, api_key=api_key, model=model, timeout=timeout)
        else:
            output = _rewrite_openai_compatible(
                text, instruction, api_base=api_base, api_key=api_key, model=model, timeout=timeout
            )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, ValueError):
        return None
    return output or None
