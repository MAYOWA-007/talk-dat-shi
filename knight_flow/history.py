from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any

from .config import app_dir, history_db_path, history_path


HISTORY_BACKENDS = ("jsonl", "sqlite")

COMMON_WORDS = frozenset(
    "the and for with that this from have will your you are was were has had can could would should "
    "about just like into over under then than them they their there here when what where which while "
    "been being our out not but all any some more most very much many each other after before because "
    "his her him she he it its is am be do does did done get got make made go went come came say said "
    "see saw know knew think thought take took good great new old big small first last next one two "
    "three today tomorrow yesterday please thanks thank hello okay yes no maybe also really still "
    "monday tuesday wednesday thursday friday saturday sunday january february march april may june "
    "july august september october november december".split()
)

_COLUMNS = ("type", "text", "original", "command", "transform", "url", "send_enter", "created_at")

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    type TEXT NOT NULL DEFAULT 'entry',
    text TEXT NOT NULL DEFAULT '',
    original TEXT NOT NULL DEFAULT '',
    command TEXT NOT NULL DEFAULT '',
    transform TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    send_enter INTEGER NOT NULL DEFAULT 0,
    extra TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at);
"""

_sqlite_lock = threading.Lock()


class JsonlHistoryStore:
    backend = "jsonl"

    def append(self, entry: dict[str, Any]) -> None:
        path = history_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=True) + "\n")

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        path = history_path()
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        entries: list[dict[str, Any]] = []
        for line in lines[-max(1, limit):]:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                entries.append(item)
        return entries

    def last_text(self) -> str:
        for entry in reversed(self.recent(500)):
            text = str(entry.get("text", "")).strip()
            if text:
                return text
        return ""

    def search(self, query: str, limit: int = 100) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        if not needle:
            return self.recent(limit)
        matches = [
            entry
            for entry in self.recent(10000)
            if needle in str(entry.get("text", "")).lower()
            or needle in str(entry.get("original", "")).lower()
            or needle in str(entry.get("command", "")).lower()
        ]
        return matches[-max(1, limit):]

    def trim(self, limit: int) -> None:
        if limit <= 0:
            return
        path = history_path()
        if not path.exists():
            return
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) > limit:
                path.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")
        except OSError:
            pass

    def clear(self) -> None:
        path = history_path()
        if path.exists():
            path.write_text("", encoding="utf-8")


class SqliteHistoryStore:
    backend = "sqlite"

    def _connect(self) -> sqlite3.Connection:
        path = history_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(_SQLITE_SCHEMA)
        return connection

    def append(self, entry: dict[str, Any]) -> None:
        extra = {key: value for key, value in entry.items() if key not in _COLUMNS}
        with _sqlite_lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO history (created_at, type, text, original, command, transform, url, send_enter, extra)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    float(entry.get("created_at") or time.time()),
                    str(entry.get("type", "entry")),
                    str(entry.get("text", "")),
                    str(entry.get("original", "")),
                    str(entry.get("command", "")),
                    str(entry.get("transform", "")),
                    str(entry.get("url", "")),
                    1 if entry.get("send_enter") else 0,
                    json.dumps(extra, ensure_ascii=True),
                ),
            )

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with _sqlite_lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT created_at, type, text, original, command, transform, url, send_enter, extra"
                " FROM history ORDER BY id DESC LIMIT ?",
                (max(1, limit),),
            ).fetchall()
        return [self._row_to_entry(row) for row in reversed(rows)]

    def last_text(self) -> str:
        with _sqlite_lock, self._connect() as connection:
            row = connection.execute(
                "SELECT text FROM history WHERE TRIM(text) != '' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return str(row[0]).strip() if row else ""

    def search(self, query: str, limit: int = 100) -> list[dict[str, Any]]:
        needle = query.strip()
        if not needle:
            return self.recent(limit)
        pattern = f"%{needle}%"
        with _sqlite_lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT created_at, type, text, original, command, transform, url, send_enter, extra"
                " FROM history WHERE text LIKE ? OR original LIKE ? OR command LIKE ?"
                " ORDER BY id DESC LIMIT ?",
                (pattern, pattern, pattern, max(1, limit)),
            ).fetchall()
        return [self._row_to_entry(row) for row in reversed(rows)]

    def trim(self, limit: int) -> None:
        if limit <= 0:
            return
        with _sqlite_lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)",
                (limit,),
            )

    def clear(self) -> None:
        with _sqlite_lock, self._connect() as connection:
            connection.execute("DELETE FROM history")

    def import_jsonl_once(self) -> None:
        with _sqlite_lock, self._connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        if count:
            return
        for entry in JsonlHistoryStore().recent(10000):
            try:
                self.append(entry)
            except sqlite3.Error:
                return

    @staticmethod
    def _row_to_entry(row: tuple[Any, ...]) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "created_at": row[0],
            "type": row[1],
            "text": row[2],
            "original": row[3],
            "command": row[4],
            "transform": row[5],
            "url": row[6],
            "send_enter": bool(row[7]),
        }
        try:
            extra = json.loads(row[8])
        except (json.JSONDecodeError, TypeError):
            extra = {}
        if isinstance(extra, dict):
            for key, value in extra.items():
                entry.setdefault(key, value)
        return {key: value for key, value in entry.items() if value not in ("", None)}


def history_backend(config: dict[str, Any]) -> str:
    backend = str(config.get("privacy", {}).get("history_backend", "jsonl")).strip().lower()
    return backend if backend in HISTORY_BACKENDS else "jsonl"


def create_history_store(config: dict[str, Any]) -> JsonlHistoryStore | SqliteHistoryStore:
    if history_backend(config) == "sqlite":
        store = SqliteHistoryStore()
        try:
            store.import_jsonl_once()
            return store
        except sqlite3.Error:
            return JsonlHistoryStore()
    return JsonlHistoryStore()


def clear_all_history() -> None:
    JsonlHistoryStore().clear()
    if history_db_path().exists():
        try:
            SqliteHistoryStore().clear()
        except sqlite3.Error:
            pass


def pinned_path():
    return app_dir() / "pinned.json"


def pinned_entries() -> list[dict[str, Any]]:
    path = pinned_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [entry for entry in data if isinstance(entry, dict)] if isinstance(data, list) else []


def pin_text(text: str) -> None:
    text = str(text).strip()
    if not text:
        return
    entries = pinned_entries()
    if any(entry.get("text") == text for entry in entries):
        return
    entries.append({"text": text, "created_at": time.time()})
    pinned_path().write_text(json.dumps(entries, ensure_ascii=True, indent=2), encoding="utf-8")


def unpin_text(text: str) -> None:
    entries = [entry for entry in pinned_entries() if entry.get("text") != text]
    pinned_path().write_text(json.dumps(entries, ensure_ascii=True, indent=2), encoding="utf-8")


def history_stats(config: dict[str, Any]) -> dict[str, Any]:
    entries = create_history_store(config).recent(20000)
    total = len(entries)
    words = sum(len(str(entry.get("text", "")).split()) for entry in entries)
    days: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for entry in entries:
        created = entry.get("created_at")
        if isinstance(created, (int, float)):
            day = time.strftime("%Y-%m-%d", time.localtime(float(created)))
            days[day] = days.get(day, 0) + 1
        kind = str(entry.get("type", "entry"))
        by_type[kind] = by_type.get(kind, 0) + 1
    streak = 0
    probe = time.time()
    while time.strftime("%Y-%m-%d", time.localtime(probe)) in days:
        streak += 1
        probe -= 86400
    # Speaking averages ~150 wpm against ~40 wpm typing.
    minutes_saved = max(0.0, words / 40 - words / 150)
    return {
        "entries": total,
        "words": words,
        "active_days": len(days),
        "streak_days": streak,
        "minutes_saved": round(minutes_saved),
        "by_type": by_type,
        "busiest_day": max(days, key=days.get) if days else "",
        "today": days.get(time.strftime("%Y-%m-%d"), 0),
    }


def suggest_vocabulary(config: dict[str, Any], existing: list[str], limit: int = 20) -> list[str]:
    known = {str(word).strip().lower() for word in existing}
    counts: dict[str, int] = {}
    for entry in create_history_store(config).recent(5000):
        for token in str(entry.get("text", "")).split():
            word = token.strip(".,!?;:()[]\"'")
            if len(word) < 4 or not word[0].isupper() or not word.isalpha():
                continue
            lower = word.lower()
            if lower in COMMON_WORDS or lower in known:
                continue
            counts[word] = counts.get(word, 0) + 1
    frequent = [word for word, count in counts.items() if count >= 3]
    frequent.sort(key=lambda word: -counts[word])
    return frequent[:limit]


def export_history(config: dict[str, Any], fmt: str = "md"):
    entries = create_history_store(config).recent(20000)
    exports = app_dir() / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    fmt = fmt if fmt in {"md", "txt", "srt"} else "md"
    path = exports / f"talk-dat-history-{stamp}.{fmt}"
    lines: list[str] = []
    if fmt == "srt":
        for index, entry in enumerate(entries, 1):
            created = float(entry.get("created_at") or 0)
            start = time.strftime("%H:%M:%S", time.localtime(created))
            lines.extend([str(index), f"{start},000 --> {start},999", str(entry.get("text", "")).strip(), ""])
    else:
        if fmt == "md":
            lines.append(f"# Talk Dat! history export - {time.strftime('%Y-%m-%d %H:%M')}\n")
        for entry in entries:
            created = entry.get("created_at")
            stamp_text = (
                time.strftime("%Y-%m-%d %H:%M", time.localtime(float(created)))
                if isinstance(created, (int, float))
                else ""
            )
            text = str(entry.get("text", "")).strip()
            if not text:
                continue
            if fmt == "md":
                lines.append(f"## {stamp_text} - {str(entry.get('type', 'entry')).replace('_', ' ')}\n\n{text}\n")
            else:
                lines.append(f"[{stamp_text}] {text}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path
