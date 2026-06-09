from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BANNED_TOP_LEVEL = {
    ".serena",
    ".venv",
    "build",
    "dist",
    "release",
}

SKIP_DIRS = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".serena",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "release",
}

TEXT_EXTENSIONS = {
    ".css",
    ".env",
    ".example",
    ".gitignore",
    ".gitattributes",
    ".html",
    ".iss",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".txt",
    ".yml",
    ".yaml",
}

SECRET_PATTERNS = (
    ("non-placeholder api key assignment", re.compile(r'(?i)(api[_ -]?key|secret|token|password)\s*[:=]\s*["\'](?!your-|put-your|<|$)([^"\']{12,})["\']')),
    ("long hex token", re.compile(r"(?<![a-fA-F0-9])[a-fA-F0-9]{40,128}(?![a-fA-F0-9])")),
    ("bearer token", re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}")),
)


def is_text_file(path: Path) -> bool:
    if path.name in {".gitignore", ".gitattributes"}:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def iter_repo_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts[:-1]):
            continue
        if path.is_file():
            files.append(path)
    return files


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    for name in sorted(BANNED_TOP_LEVEL):
        if (ROOT / name).exists():
            warnings.append(f"ignored generated/local folder exists: {name}/")

    for path in iter_repo_files():
        relative = path.relative_to(ROOT)
        if path.name.startswith("tmp-"):
            failures.append(f"temporary file exists: {relative}")
        if not is_text_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if "PUT-YOUR-" in line or "your-key-here" in line or "your_api_key" in line:
                continue
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    failures.append(f"{label}: {relative}:{line_number}")

    if failures:
        print("Prepublish check failed:")
        for failure in failures:
            print(f"- {failure}")
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"- {warning}")
        return 1

    if warnings:
        print("Prepublish check passed with warnings:")
        for warning in warnings:
            print(f"- {warning}")
        print("These paths are ignored by git, but delete them before creating source archives by hand.")
        return 0

    print("Prepublish check passed. No obvious local artifacts or key-shaped secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
