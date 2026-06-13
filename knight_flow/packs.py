"""Shared dictionary/snippet packs and settings backup.

Packs are plain JSON ({"name", "dictionary": {"words", "replacements"}, "snippets"})
so teams can share vocabulary without any server. Backups are ZIP files of the
local AppData content; they contain API keys, so treat them like secrets.
"""

from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path
from typing import Any

from .config import app_dir, config_path


PACK_VERSION = 1
BACKUP_FILES = ("config.json", "pinned.json", "scratchpad-tabs.json", "history.jsonl")


def export_pack(config: dict[str, Any], path: Path | str) -> Path:
    path = Path(path)
    pack = {
        "talkdat_pack": PACK_VERSION,
        "name": path.stem,
        "exported_at": time.strftime("%Y-%m-%d %H:%M"),
        "dictionary": {
            "words": list(config.get("dictionary", {}).get("words", [])),
            "replacements": list(config.get("dictionary", {}).get("replacements", [])),
        },
        "snippets": list(config.get("snippets", [])),
    }
    path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def import_pack(config: dict[str, Any], path: Path | str) -> dict[str, int]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or "talkdat_pack" not in data:
        raise ValueError("Not a Talk Dat! pack file.")
    dictionary = config.setdefault("dictionary", {})
    words = dictionary.setdefault("words", [])
    replacements = dictionary.setdefault("replacements", [])
    snippets = config.setdefault("snippets", [])

    added = {"words": 0, "replacements": 0, "snippets": 0}
    known_words = {str(word).lower() for word in words}
    for word in data.get("dictionary", {}).get("words", []):
        if str(word).strip() and str(word).lower() not in known_words:
            words.append(str(word))
            known_words.add(str(word).lower())
            added["words"] += 1
    known_sources = {str(item.get("from", "")).lower() for item in replacements if isinstance(item, dict)}
    for item in data.get("dictionary", {}).get("replacements", []):
        if isinstance(item, dict) and str(item.get("from", "")).strip() and str(item.get("from", "")).lower() not in known_sources:
            replacements.append({"from": str(item.get("from")), "to": str(item.get("to", ""))})
            added["replacements"] += 1
    known_triggers = {str(item.get("trigger", "")).lower() for item in snippets if isinstance(item, dict)}
    for item in data.get("snippets", []):
        if isinstance(item, dict) and str(item.get("trigger", "")).strip() and str(item.get("trigger", "")).lower() not in known_triggers:
            snippets.append({"trigger": str(item.get("trigger")), "text": str(item.get("text", ""))})
            added["snippets"] += 1
    return added


def export_backup(path: Path | str) -> Path:
    path = Path(path)
    root = app_dir()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in BACKUP_FILES:
            source = root / name
            if source.exists():
                archive.write(source, name)
    return path


def restore_backup(path: Path | str) -> list[str]:
    root = app_dir()
    restored: list[str] = []
    with zipfile.ZipFile(Path(path)) as archive:
        for name in archive.namelist():
            if name not in BACKUP_FILES:
                continue
            archive.extract(name, root)
            restored.append(name)
    return restored


def export_diagnostics() -> Path:
    """Diagnostics ZIP with a key-redacted config and basic environment info."""
    import platform
    import sys

    from .version import APP_VERSION

    root = app_dir()
    diagnostics = root / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    path = diagnostics / time.strftime("talk-dat-diagnostics-%Y%m%d-%H%M%S.zip")

    redacted = "{}"
    try:
        raw = json.loads(config_path().read_text(encoding="utf-8-sig"))

        def scrub(node: Any) -> Any:
            if isinstance(node, dict):
                return {
                    key: ("[redacted]" if "key" in key.lower() or "token" in key.lower() else scrub(value))
                    for key, value in node.items()
                }
            if isinstance(node, list):
                return [scrub(item) for item in node]
            return node

        redacted = json.dumps(scrub(raw), indent=2)
    except (OSError, json.JSONDecodeError):
        pass

    info = "\n".join(
        [
            f"Talk Dat! v{APP_VERSION}",
            f"Python {sys.version}",
            f"Platform {platform.platform()}",
            f"AppData {root}",
            f"Generated {time.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("config.redacted.json", redacted)
        archive.writestr("environment.txt", info)
        log_path = root / "talk-dat.log"
        if log_path.exists():
            archive.write(log_path, "talk-dat.log")
    return path
