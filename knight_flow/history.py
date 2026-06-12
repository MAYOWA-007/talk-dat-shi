from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any

from .config import history_db_path, history_path


HISTORY_BACKENDS = ("jsonl", "sqlite")

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
