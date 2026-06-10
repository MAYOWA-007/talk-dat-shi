from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .config import app_dir
from .version import APP_LATEST_RELEASE_API_URL, APP_RELEASES_URL, APP_VERSION, INSTALLER_ASSET_NAME


ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    available: bool
    release_url: str
    installer_url: str
    installer_name: str
    published_at: str
    release_notes: str


class UpdateError(RuntimeError):
    pass


def version_parts(version: str) -> tuple[int, ...]:
    raw = str(version).strip().lower()
    raw = raw[1:] if raw.startswith("v") else raw
    parts = [int(part) for part in re.findall(r"\d+", raw)]
    return tuple(parts or [0])


def is_newer_version(latest: str, current: str) -> bool:
    latest_parts = list(version_parts(latest))
    current_parts = list(version_parts(current))
    width = max(len(latest_parts), len(current_parts))
    latest_parts.extend([0] * (width - len(latest_parts)))
    current_parts.extend([0] * (width - len(current_parts)))
    return tuple(latest_parts) > tuple(current_parts)


def _request(url: str, timeout: float) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"TalkDatShi/{APP_VERSION}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


def _download_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": f"TalkDatShi/{APP_VERSION}",
        },
    )


def _latest_release_payload(timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(_request(APP_LATEST_RELEASE_API_URL, timeout), timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise UpdateError("No public GitHub release has been published yet.") from error
        raise UpdateError(f"GitHub release check failed: HTTP {error.code}.") from error
    except urllib.error.URLError as error:
        raise UpdateError(f"Could not reach GitHub releases: {error.reason}.") from error
    except (TimeoutError, json.JSONDecodeError, OSError) as error:
        raise UpdateError(f"Could not read GitHub release information: {error}.") from error
    if not isinstance(payload, dict):
        raise UpdateError("GitHub returned an unexpected release response.")
    return payload


def check_for_update(current_version: str = APP_VERSION, timeout: float = 8.0) -> UpdateInfo:
    payload = _latest_release_payload(timeout)
    tag_name = str(payload.get("tag_name") or "").strip()
    latest_version = tag_name[1:] if tag_name.lower().startswith("v") else tag_name
    if not latest_version:
        raise UpdateError("The latest GitHub release has no version tag.")

    assets = payload.get("assets", [])
    installer_url = ""
    installer_name = INSTALLER_ASSET_NAME
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name") or "")
            if name.lower() == INSTALLER_ASSET_NAME.lower():
                installer_name = name
                installer_url = str(asset.get("browser_download_url") or "")
                break

    release_url = str(payload.get("html_url") or APP_RELEASES_URL)
    return UpdateInfo(
        current_version=current_version,
        latest_version=latest_version,
        available=is_newer_version(latest_version, current_version),
        release_url=release_url,
        installer_url=installer_url,
        installer_name=installer_name,
        published_at=str(payload.get("published_at") or ""),
        release_notes=str(payload.get("body") or ""),
    )


def updates_dir() -> Path:
    path = app_dir() / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_installer(info: UpdateInfo, progress: ProgressCallback | None = None, timeout: float = 30.0) -> Path:
    if not info.installer_url:
        raise UpdateError("The latest release does not include the Windows setup EXE yet.")
    safe_version = re.sub(r"[^0-9A-Za-z._-]+", "-", info.latest_version).strip("-") or "latest"
    destination = updates_dir() / f"Talk-Dat-Shi-Setup-{safe_version}.exe"
    temp_destination = destination.with_suffix(".part")
    try:
        with urllib.request.urlopen(_download_request(info.installer_url), timeout=timeout) as response:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            with temp_destination.open("wb") as file:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    file.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress(downloaded, total)
        temp_destination.replace(destination)
    except urllib.error.URLError as error:
        raise UpdateError(f"Could not download update: {error.reason}.") from error
    except OSError as error:
        raise UpdateError(f"Could not save update installer: {error}.") from error
    finally:
        try:
            if temp_destination.exists():
                temp_destination.unlink()
        except OSError:
            pass
    return destination


def launch_installer(path: Path) -> None:
    if not path.exists():
        raise UpdateError(f"Installer was not found: {path}")
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except OSError as error:
        raise UpdateError(f"Could not launch installer: {error}.") from error


def record_version_seen(config: dict[str, Any]) -> None:
    updates = config.setdefault("updates", {})
    now = int(time.time())
    updates.setdefault("first_seen_version", APP_VERSION)
    updates["current_version"] = APP_VERSION
    updates["last_run_at"] = now
