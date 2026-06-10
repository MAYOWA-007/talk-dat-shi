from __future__ import annotations

import datetime as dt
import json
import math
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog

try:
    import winreg
except ImportError:  # pragma: no cover - this installer is Windows-only.
    winreg = None  # type: ignore[assignment]

from PIL import Image, ImageDraw, ImageFilter, ImageTk

try:
    from knight_flow.version import APP_VERSION
except Exception:  # pragma: no cover - standalone installer fallback.
    APP_VERSION = "0.1.0"

APP_NAME = "Talk Dat!"
PUBLISHER = "MAYOWA-007"
APP_EXE_NAME = "Talk Dat!.exe"
UNINSTALL_EXE_NAME = "Talk Dat! Uninstaller.exe"
MANIFEST_NAME = "install-manifest.json"
UNINSTALL_REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\TalkDat"
LEGACY_SUFFIX = "".join(chr(value) for value in (83, 104, 105))
LEGACY_APP_NAME = f"Talk Dat {LEGACY_SUFFIX}"
LEGACY_APP_EXE_NAME = f"{LEGACY_APP_NAME}.exe"
LEGACY_UNINSTALL_REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\TalkDat" + LEGACY_SUFFIX
TRANSPARENT_COLOR = "#010203"

Report = Callable[[float, str], None]


def _creation_flags() -> int:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return int(flags)


def _detached_flags() -> int:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    return int(flags)


def resource_path(*parts: str) -> Path:
    roots: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        roots.append(Path(bundle_root))
    here = Path(__file__).resolve().parent
    roots.extend([here, here.parent, Path.cwd()])
    for root in roots:
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return candidate
    return roots[0].joinpath(*parts)


def payload_path(name: str) -> Path:
    return resource_path("payload", name)


def asset_path(name: str) -> Path:
    return resource_path("knight_flow", "assets", name)


def default_install_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Programs" / APP_NAME
    return Path.home() / "AppData" / "Local" / "Programs" / APP_NAME


def user_data_dir() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data) / "TalkDat"
    return Path.home() / "AppData" / "Roaming" / "TalkDat"


def legacy_user_data_dir() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data) / ("TalkDat" + LEGACY_SUFFIX)
    return Path.home() / "AppData" / "Roaming" / ("TalkDat" + LEGACY_SUFFIX)


def copy_missing_items(source_root: Path, destination_root: Path) -> None:
    destination_root.mkdir(parents=True, exist_ok=True)
    for item in source_root.iterdir():
        destination = destination_root / item.name
        if destination.exists():
            continue
        try:
            if item.is_dir():
                shutil.copytree(item, destination)
            else:
                shutil.copy2(item, destination)
        except OSError:
            pass


def rename_legacy_user_data(legacy_root: Path) -> None:
    backup = legacy_root.with_name("TalkDatLegacyBackup")
    candidate = backup
    index = 2
    while candidate.exists():
        candidate = backup.with_name(f"{backup.name}{index}")
        index += 1
    try:
        legacy_root.rename(candidate)
    except OSError:
        pass


def migrate_legacy_user_data() -> None:
    root = user_data_dir()
    legacy_root = legacy_user_data_dir()
    if not legacy_root.exists():
        return
    if not root.exists():
        try:
            legacy_root.rename(root)
            return
        except OSError:
            pass
    copy_missing_items(legacy_root, root)
    rename_legacy_user_data(legacy_root)


def desktop_shortcut_path() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop" / f"{APP_NAME}.lnk"


def start_menu_shortcut_path() -> Path:
    app_data = Path(os.environ.get("APPDATA", str(Path.home())))
    return app_data / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk"


def startup_shortcut_path() -> Path:
    app_data = Path(os.environ.get("APPDATA", str(Path.home())))
    return app_data / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{APP_NAME}.lnk"


def legacy_shortcut_paths() -> list[Path]:
    app_data = Path(os.environ.get("APPDATA", str(Path.home())))
    user_profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
    return [
        user_profile / "Desktop" / f"{LEGACY_APP_NAME}.lnk",
        app_data / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{LEGACY_APP_NAME}.lnk",
        app_data / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{LEGACY_APP_NAME}.lnk",
    ]


def norm_path(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def is_under(path: Path, parent: Path) -> bool:
    child_value = norm_path(path)
    parent_value = norm_path(parent)
    return child_value == parent_value or child_value.startswith(parent_value + os.sep)


def is_dangerous_install_dir(path: Path) -> bool:
    resolved = Path(os.path.abspath(os.path.expanduser(str(path))))
    if len(resolved.parts) <= 2:
        return True
    sensitive = {
        norm_path(Path.home()),
        norm_path(Path(os.environ.get("LOCALAPPDATA", str(Path.home())))),
        norm_path(Path(os.environ.get("APPDATA", str(Path.home())))),
        norm_path(Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"),
    }
    return norm_path(resolved) in sensitive


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_powershell(script: str) -> None:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=_creation_flags(),
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "PowerShell command failed."
        raise RuntimeError(detail)


def create_shortcut(shortcut_path: Path, target_path: Path, description: str) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    script = f"""
$shortcutPath = {ps_quote(str(shortcut_path))}
$targetPath = {ps_quote(str(target_path))}
$workingDirectory = {ps_quote(str(target_path.parent))}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.WorkingDirectory = $workingDirectory
$shortcut.IconLocation = "$targetPath,0"
$shortcut.Description = {ps_quote(description)}
$shortcut.Save()
"""
    run_powershell(script)


def remove_shortcut(shortcut_path: Path) -> None:
    try:
        if shortcut_path.exists():
            shortcut_path.unlink()
    except OSError:
        pass


def directory_size_kb(path: Path) -> int:
    total = 0
    if path.exists():
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except OSError:
                    pass
    return max(1, math.ceil(total / 1024))


def register_uninstaller(install_dir: Path, app_exe: Path, uninstaller: Path) -> None:
    if winreg is None:
        raise RuntimeError("Windows registry is not available.")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_REGISTRY_KEY) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{app_exe},0")
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller}"')
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, directory_size_kb(install_dir))


def unregister_uninstaller() -> None:
    if winreg is None:
        return
    for key_name in (UNINSTALL_REGISTRY_KEY, LEGACY_UNINSTALL_REGISTRY_KEY):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_name)
        except OSError:
            pass


def installed_location() -> Path:
    if winreg is not None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_REGISTRY_KEY) as key:
                value, _kind = winreg.QueryValueEx(key, "InstallLocation")
                if isinstance(value, str) and value.strip():
                    return Path(value)
        except OSError:
            pass
    return default_install_dir()


def load_manifest(install_dir: Path) -> dict[str, Any]:
    path = install_dir / MANIFEST_NAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_manifest(install_dir: Path, files: list[Path], shortcuts: list[Path]) -> None:
    manifest_path = install_dir / MANIFEST_NAME
    all_files = [*files, manifest_path]
    data = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "publisher": PUBLISHER,
        "installed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "install_dir": str(install_dir),
        "user_data_dir": str(user_data_dir()),
        "files": [str(path) for path in all_files],
        "shortcuts": [str(path) for path in shortcuts],
        "keeps_private_data_by_default": True,
    }
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def stop_running_app(install_dir: Path) -> None:
    script = f"""
$installDir = {ps_quote(str(install_dir))}
$appName = {ps_quote(APP_NAME)}
$legacyName = {ps_quote(LEGACY_APP_NAME)}
Get-Process |
  Where-Object {{ $_.Path -and (($_.ProcessName -eq $appName -and $_.Path.StartsWith($installDir, [System.StringComparison]::OrdinalIgnoreCase)) -or $_.ProcessName -eq $legacyName) }} |
  Stop-Process -Force
"""
    try:
        run_powershell(script)
    except RuntimeError:
        pass


def copy_payload_file(source: Path, destination: Path) -> None:
    if not source.exists():
        raise RuntimeError(f"Missing installer payload: {source.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def safe_delete_file(path: Path, install_dir: Path, current_exe: Path, skipped_self: list[Path]) -> None:
    if not is_under(path, install_dir):
        return
    try:
        if norm_path(path) == norm_path(current_exe):
            skipped_self.append(path)
            return
        if path.exists() and path.is_file():
            path.unlink()
    except OSError:
        pass


def remove_empty_dirs(paths: list[Path], install_dir: Path) -> None:
    for directory in sorted(set(paths), key=lambda item: len(str(item)), reverse=True):
        if not is_under(directory, install_dir):
            continue
        try:
            if directory.exists() and directory.is_dir():
                directory.rmdir()
        except OSError:
            pass


def schedule_self_cleanup(current_exe: Path, install_dir: Path) -> None:
    if not is_under(current_exe, install_dir):
        return
    cmd = (
        "ping 127.0.0.1 -n 3 > nul "
        f'& del /f /q "{current_exe}" > nul 2> nul '
        f'& rmdir "{install_dir}" > nul 2> nul'
    )
    subprocess.Popen(["cmd", "/c", cmd], creationflags=_detached_flags())


def install_app(options: dict[str, Any], report: Report) -> None:
    install_dir = Path(str(options["install_dir"])).expanduser()
    if is_dangerous_install_dir(install_dir):
        raise RuntimeError("Choose a normal app folder, not a drive, home, AppData, or Desktop root.")

    install_dir = Path(os.path.abspath(str(install_dir)))
    app_exe = install_dir / APP_EXE_NAME
    uninstaller = install_dir / UNINSTALL_EXE_NAME
    docs_dir = install_dir / "docs"
    installed_files: list[Path] = []
    shortcuts: list[Path] = []

    report(0.08, "Preparing install folder...")
    install_dir.mkdir(parents=True, exist_ok=True)
    stop_running_app(install_dir)

    report(0.22, "Copying Talk Dat!...")
    try:
        copy_payload_file(payload_path(APP_EXE_NAME), app_exe)
        installed_files.append(app_exe)
        copy_payload_file(payload_path(UNINSTALL_EXE_NAME), uninstaller)
        installed_files.append(uninstaller)
    except PermissionError as error:
        raise RuntimeError("Quit Talk Dat!, then run the installer again.") from error

    report(0.36, "Adding local help files...")
    for source_name, output_name in (
        ("START_HERE_WINDOWS.md", "START-HERE.md"),
        ("INSTALL.md", "INSTALL.md"),
        ("PROVIDERS.md", "PROVIDERS.md"),
    ):
        source = resource_path("payload", "docs", source_name)
        if source.exists():
            destination = docs_dir / output_name
            copy_payload_file(source, destination)
            installed_files.append(destination)

    migrate_legacy_user_data()

    report(0.52, "Creating shortcuts...")
    if bool(options.get("start_menu", True)):
        shortcut = start_menu_shortcut_path()
        create_shortcut(shortcut, app_exe, "Launch Talk Dat! dictation overlay.")
        shortcuts.append(shortcut)
    if bool(options.get("desktop", True)):
        shortcut = desktop_shortcut_path()
        create_shortcut(shortcut, app_exe, "Launch Talk Dat! dictation overlay.")
        shortcuts.append(shortcut)
    if bool(options.get("startup", False)):
        shortcut = startup_shortcut_path()
        create_shortcut(shortcut, app_exe, "Start Talk Dat! when Windows signs in.")
        shortcuts.append(shortcut)
    else:
        remove_shortcut(startup_shortcut_path())
    for legacy_shortcut in legacy_shortcut_paths():
        remove_shortcut(legacy_shortcut)

    report(0.70, "Registering Windows uninstaller...")
    write_manifest(install_dir, installed_files, shortcuts)
    register_uninstaller(install_dir, app_exe, uninstaller)

    report(0.86, "Finalizing...")
    if bool(options.get("launch", True)):
        subprocess.Popen([str(app_exe)], cwd=str(install_dir), creationflags=_detached_flags())

    report(1.0, "Installed. Your API keys stay private in local AppData.")


def uninstall_app(options: dict[str, Any], report: Report) -> None:
    install_dir = installed_location()
    if is_dangerous_install_dir(install_dir):
        raise RuntimeError("Install folder looks unsafe. Uninstall manually from Windows Apps.")
    install_dir = Path(os.path.abspath(str(install_dir)))
    manifest = load_manifest(install_dir)
    current_exe = Path(sys.executable).resolve()
    skipped_self: list[Path] = []

    report(0.12, "Stopping Talk Dat!...")
    stop_running_app(install_dir)

    report(0.28, "Removing shortcuts...")
    if bool(options.get("remove_shortcuts", True)):
        for raw_path in manifest.get("shortcuts", []):
            if isinstance(raw_path, str):
                remove_shortcut(Path(raw_path))
        for path in (desktop_shortcut_path(), start_menu_shortcut_path(), startup_shortcut_path()):
            remove_shortcut(path)
        for path in legacy_shortcut_paths():
            remove_shortcut(path)

    report(0.48, "Removing installed app files...")
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        raw_files = [
            str(install_dir / APP_EXE_NAME),
            str(install_dir / UNINSTALL_EXE_NAME),
            str(install_dir / "docs" / "START-HERE.md"),
            str(install_dir / "docs" / "INSTALL.md"),
            str(install_dir / "docs" / "PROVIDERS.md"),
            str(install_dir / MANIFEST_NAME),
        ]
    file_paths = [Path(raw) for raw in raw_files if isinstance(raw, str)]
    for path in file_paths:
        safe_delete_file(path, install_dir, current_exe, skipped_self)

    report(0.68, "Cleaning empty folders...")
    remove_empty_dirs([path.parent for path in file_paths], install_dir)
    try:
        if install_dir.exists():
            install_dir.rmdir()
    except OSError:
        pass

    report(0.80, "Removing Windows registration...")
    unregister_uninstaller()

    if bool(options.get("remove_user_data", False)):
        report(0.90, "Removing private local user data...")
        data_dir = user_data_dir()
        if data_dir.name == "TalkDat" and data_dir.exists():
            shutil.rmtree(data_dir, ignore_errors=True)
        legacy_data_dir = legacy_user_data_dir()
        if legacy_data_dir.exists():
            shutil.rmtree(legacy_data_dir, ignore_errors=True)

    if skipped_self:
        schedule_self_cleanup(current_exe, install_dir)

    report(1.0, "Uninstalled. Private user data was kept unless you selected removal.")


def rounded_rectangle(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: Any, outline: Any = None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def make_panel_image(width: int, height: int) -> Image.Image:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    rounded_rectangle(shadow_draw, (20, 24, width - 20, height - 14), 32, (0, 0, 0, 170))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))

    panel = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    rounded_rectangle(draw, (26, 20, width - 26, height - 22), 30, (5, 24, 27, 236), (31, 221, 200, 116), 1)
    rounded_rectangle(draw, (34, 28, width - 34, height - 30), 24, (255, 255, 255, 10), (255, 227, 174, 38), 1)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-100, 120, 420, height + 180), fill=(255, 38, 30, 60))
    glow_draw.ellipse((width - 520, -160, width + 120, 300), fill=(0, 220, 210, 58))
    panel.alpha_composite(glow.filter(ImageFilter.GaussianBlur(58)))

    for x in range(48, width - 54, 32):
        alpha = 24 if x % 64 else 42
        draw.line((x, 44, x, 178), fill=(255, 232, 160, alpha), width=1)
        draw.line((x + 6, 44, x + 6, 178), fill=(0, 210, 205, 28), width=1)

    draw.line((52, 194, width - 52, 194), fill=(153, 255, 237, 60), width=1)
    draw.line((52, height - 86, width - 52, height - 86), fill=(153, 255, 237, 44), width=1)

    image.alpha_composite(panel)
    return image


def load_logo(size: int) -> ImageTk.PhotoImage | None:
    for name in ("app_icon.png", "logo.png"):
        path = asset_path(name)
        if path.exists():
            image = Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(image)
    return None


def make_fallback_pill(width: int, height: int, phase: float = 0.0) -> Image.Image:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pill = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(pill)
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((8, 8, width - 8, height - 8), radius=(height - 16) // 2, fill=255)

    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    for x in range(width):
        t = (x / max(1, width - 1) + phase) % 1.0
        if t < 0.28:
            color = (255, 31, 54, 255)
        elif t < 0.52:
            color = (255, 178, 92, 255)
        elif t < 0.78:
            color = (0, 126, 129, 255)
        else:
            color = (5, 34, 45, 255)
        gradient_draw.line((x, 0, x, height), fill=color)
    for x in range(-30, width + 30, 18):
        gradient_draw.line((x, 0, x + 16, height), fill=(255, 232, 150, 138), width=2)
        gradient_draw.line((x + 6, 0, x + 22, height), fill=(0, 28, 34, 150), width=8)
    pill.alpha_composite(Image.composite(gradient, Image.new("RGBA", (width, height), (0, 0, 0, 0)), mask))
    glow = pill.filter(ImageFilter.GaussianBlur(10))
    image.alpha_composite(glow)
    image.alpha_composite(pill)
    draw.rounded_rectangle((10, 10, width - 10, height - 10), radius=(height - 20) // 2, outline=(232, 235, 200, 140), width=2)
    return image


def load_pill_frames(width: int, height: int) -> list[ImageTk.PhotoImage]:
    sprite_path = asset_path("flow_pill_240.png")
    meta_path = asset_path("flow_pill_240.json")
    if not sprite_path.exists() or not meta_path.exists():
        return [ImageTk.PhotoImage(make_fallback_pill(width, height, phase / 24)) for phase in range(24)]

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        columns = int(meta.get("columns", 16))
        frame_count = int(meta.get("frame_count", 240))
        frame_width = int(meta.get("frame_width", 320))
        frame_height = int(meta.get("frame_height", 58))
        sheet = Image.open(sprite_path).convert("RGBA")
    except (OSError, ValueError, json.JSONDecodeError):
        return [ImageTk.PhotoImage(make_fallback_pill(width, height, phase / 24)) for phase in range(24)]

    frames: list[ImageTk.PhotoImage] = []
    for frame_index in range(0, frame_count, 5):
        column = frame_index % columns
        row = frame_index // columns
        crop = sheet.crop(
            (
                column * frame_width,
                row * frame_height,
                (column + 1) * frame_width,
                (row + 1) * frame_height,
            )
        )
        glow = crop.filter(ImageFilter.GaussianBlur(7))
        composed = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        composed.alpha_composite(glow)
        composed.alpha_composite(crop)
        composed = composed.resize((width, height), Image.Resampling.LANCZOS)
        frames.append(ImageTk.PhotoImage(composed))
    return frames or [ImageTk.PhotoImage(make_fallback_pill(width, height, 0.0))]


class PillButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        width: int = 156,
        height: int = 42,
        variant: str = "primary",
    ) -> None:
        super().__init__(parent, width=width, height=height, bg=TRANSPARENT_COLOR, highlightthickness=0)
        self.text = text
        self.command = command
        self.variant = variant
        self.enabled = True
        self.hovered = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
        self._draw()

    def set_text(self, text: str) -> None:
        self.text = text
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._draw()

    def _colors(self) -> tuple[str, str, str]:
        if not self.enabled:
            return "#132c30", "#426a66", "#78928f"
        if self.variant == "ghost":
            return ("#08191b" if not self.hovered else "#102f30", "#2cd8c8", "#d7fff7")
        if self.variant == "danger":
            return ("#2f1215" if not self.hovered else "#57191d", "#ff735f", "#fff0dc")
        return ("#ffb45d" if not self.hovered else "#ffd07b", "#fff1bf", "#07191a")

    def _draw(self) -> None:
        self.delete("all")
        width = int(self["width"])
        height = int(self["height"])
        fill, outline, text_color = self._colors()
        self.create_oval(4, 6, 24, height - 6, fill="#ff2b35", outline="")
        self.create_oval(width - 24, 6, width - 4, height - 6, fill="#0fd5c8", outline="")
        self.create_rectangle(14, 6, width - 14, height - 6, fill=fill, outline="")
        self.create_rounded_rect(4, 6, width - 4, height - 6, radius=18, fill=fill, outline=outline, width=1)
        self.create_text(width // 2, height // 2, text=self.text, fill=text_color, font=("Segoe UI Semibold", 10))

    def create_rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs: Any) -> int:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _enter(self, _event: tk.Event) -> None:
        self.hovered = True
        self._draw()

    def _leave(self, _event: tk.Event) -> None:
        self.hovered = False
        self._draw()

    def _click(self, _event: tk.Event) -> None:
        if self.enabled:
            self.command()


class ToggleRow(tk.Canvas):
    def __init__(self, parent: tk.Misc, text: str, variable: tk.BooleanVar, width: int = 320) -> None:
        super().__init__(parent, width=width, height=42, bg=TRANSPARENT_COLOR, highlightthickness=0)
        self.text = text
        self.variable = variable
        self.hovered = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._toggle)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        value = bool(self.variable.get())
        bg = "#0b2528" if self.hovered else "#071d20"
        outline = "#1fe0d0" if value else "#325d5d"
        dot = "#ffd477" if value else "#16373b"
        self.create_rounded_rect(2, 4, int(self["width"]) - 2, 38, radius=14, fill=bg, outline=outline, width=1)
        self.create_oval(15, 14, 29, 28, fill=dot, outline="#fff0bd" if value else "#477878", width=1)
        if value:
            self.create_line(18, 21, 22, 25, 28, 17, fill="#07191a", width=2)
        self.create_text(42, 21, anchor="w", text=self.text, fill="#eafbf5", font=("Segoe UI", 9))

    def create_rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs: Any) -> int:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _enter(self, _event: tk.Event) -> None:
        self.hovered = True
        self._draw()

    def _leave(self, _event: tk.Event) -> None:
        self.hovered = False
        self._draw()

    def _toggle(self, _event: tk.Event) -> None:
        self.variable.set(not bool(self.variable.get()))
        self._draw()


class GlassInstaller:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.root = tk.Tk()
        self.width = 780
        self.height = 560
        self.running = False
        self.header_index = 0
        self.drag_start: tuple[int, int, int, int] | None = None
        self.animation_after_id: str | None = None

        self.root.title(f"{APP_NAME} {'Uninstaller' if mode == 'uninstall' else 'Installer'}")
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.overrideredirect(True)
        self.root.configure(bg=TRANSPARENT_COLOR)
        self.root.attributes("-alpha", 0.98)
        try:
            self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        except tk.TclError:
            pass
        icon = asset_path("app_icon.ico")
        if icon.exists():
            try:
                self.root.iconbitmap(str(icon))
            except tk.TclError:
                pass

        self._center()
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)

        self.panel_image = ImageTk.PhotoImage(make_panel_image(self.width, self.height))
        self.canvas.create_image(0, 0, image=self.panel_image, anchor="nw")
        self.header_frames = load_pill_frames(600, 108)
        self.header_item = self.canvas.create_image(100, 86, image=self.header_frames[0], anchor="nw")
        self.logo_image = load_logo(66)
        if self.logo_image:
            self.canvas.create_image(64, 58, image=self.logo_image, anchor="center")

        self._build_chrome()
        if mode == "uninstall":
            self._build_uninstall()
        else:
            self._build_install()
        self._animate_header()

    def _center(self) -> None:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, (screen_width - self.width) // 2)
        y = max(0, (screen_height - self.height) // 2)
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _build_chrome(self) -> None:
        title = "Custom Glass Installer" if self.mode == "install" else "Custom Glass Uninstaller"
        subtitle = "Fast per-user setup. No keys baked in." if self.mode == "install" else "Clean removal. Private data is optional."
        self.canvas.create_text(102, 45, anchor="w", text=APP_NAME, fill="#fff5d8", font=("Segoe UI Semibold", 22))
        self.canvas.create_text(104, 76, anchor="w", text=title, fill="#96fff2", font=("Segoe UI", 10))
        self.canvas.create_text(528, 50, anchor="w", text=subtitle, fill="#d8fff7", font=("Segoe UI", 9))
        close = PillButton(self.root, "x", self._close, width=38, height=34, variant="ghost")
        self.canvas.create_window(self.width - 62, 48, window=close)

    def _build_install(self) -> None:
        self.install_dir_var = tk.StringVar(value=str(default_install_dir()))
        self.desktop_var = tk.BooleanVar(value=True)
        self.start_menu_var = tk.BooleanVar(value=True)
        self.startup_var = tk.BooleanVar(value=False)
        self.launch_var = tk.BooleanVar(value=True)

        self.canvas.create_text(64, 218, anchor="w", text="Install location", fill="#fff3cc", font=("Segoe UI Semibold", 10))
        entry = tk.Entry(
            self.root,
            textvariable=self.install_dir_var,
            bg="#071c1f",
            fg="#ecfff9",
            insertbackground="#ffd477",
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.canvas.create_window(64, 250, anchor="nw", width=530, height=36, window=entry)
        browse = PillButton(self.root, "Browse", self._browse, width=112, height=38, variant="ghost")
        self.canvas.create_window(610, 249, anchor="nw", window=browse)

        toggles = [
            ToggleRow(self.root, "Desktop shortcut", self.desktop_var),
            ToggleRow(self.root, "Start menu shortcut", self.start_menu_var),
            ToggleRow(self.root, "Launch after install", self.launch_var),
            ToggleRow(self.root, "Start with Windows", self.startup_var),
        ]
        for index, toggle in enumerate(toggles):
            x = 64 if index % 2 == 0 else 396
            y = 318 + (index // 2) * 50
            self.canvas.create_window(x, y, anchor="nw", window=toggle)

        self.canvas.create_text(
            64,
            428,
            anchor="w",
            text="Privacy: the installer copies app files only. Users add their own provider keys during first-run setup.",
            fill="#b9d7d1",
            font=("Segoe UI", 9),
        )
        self._build_progress()
        self.primary_button = PillButton(self.root, "Install", self._start_install, width=150, height=42, variant="primary")
        self.secondary_button = PillButton(self.root, "Cancel", self._close, width=128, height=42, variant="ghost")
        self.canvas.create_window(520, 500, anchor="nw", window=self.secondary_button)
        self.canvas.create_window(648, 500, anchor="nw", window=self.primary_button)

    def _build_uninstall(self) -> None:
        self.remove_shortcuts_var = tk.BooleanVar(value=True)
        self.remove_user_data_var = tk.BooleanVar(value=False)
        install_dir = installed_location()

        self.canvas.create_text(64, 218, anchor="w", text="Installed location", fill="#fff3cc", font=("Segoe UI Semibold", 10))
        self.canvas.create_text(64, 250, anchor="w", text=str(install_dir), fill="#ecfff9", font=("Segoe UI", 10))
        self.canvas.create_text(
            64,
            292,
            anchor="w",
            text="User config, API keys, dictionaries, snippets, and transcript history are kept unless you choose removal.",
            fill="#b9d7d1",
            font=("Segoe UI", 9),
        )
        self.canvas.create_window(64, 336, anchor="nw", window=ToggleRow(self.root, "Remove shortcuts and startup entry", self.remove_shortcuts_var, width=410))
        self.canvas.create_window(64, 386, anchor="nw", window=ToggleRow(self.root, "Also remove private local user data", self.remove_user_data_var, width=410))
        self._build_progress()
        self.primary_button = PillButton(self.root, "Uninstall", self._start_uninstall, width=150, height=42, variant="danger")
        self.secondary_button = PillButton(self.root, "Cancel", self._close, width=128, height=42, variant="ghost")
        self.canvas.create_window(520, 500, anchor="nw", window=self.secondary_button)
        self.canvas.create_window(648, 500, anchor="nw", window=self.primary_button)

    def _build_progress(self) -> None:
        self.progress_canvas = tk.Canvas(self.root, width=660, height=28, bg=TRANSPARENT_COLOR, highlightthickness=0)
        self._canvas_rounded_rect(self.progress_canvas, 2, 7, 658, 21, radius=7, fill="#081517", outline="#245b57", width=1)
        self.progress_fill = self.progress_canvas.create_rectangle(4, 9, 4, 19, fill="#ffd477", outline="")
        self.status_id = self.canvas.create_text(64, 476, anchor="w", text="Ready.", fill="#d8fff7", font=("Segoe UI", 9))
        self.canvas.create_window(64, 458, anchor="nw", window=self.progress_canvas)

    def _canvas_rounded_rect(self, canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs: Any) -> int:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _browse(self) -> None:
        selected = filedialog.askdirectory(
            title="Choose Talk Dat! install folder",
            initialdir=str(Path(self.install_dir_var.get()).parent),
        )
        if selected:
            self.install_dir_var.set(selected)

    def _start_install(self) -> None:
        if self.running:
            return
        options = {
            "install_dir": self.install_dir_var.get(),
            "desktop": self.desktop_var.get(),
            "start_menu": self.start_menu_var.get(),
            "startup": self.startup_var.get(),
            "launch": self.launch_var.get(),
        }
        self._run_worker(lambda report: install_app(options, report), success_button="Close")

    def _start_uninstall(self) -> None:
        if self.running:
            return
        options = {
            "remove_shortcuts": self.remove_shortcuts_var.get(),
            "remove_user_data": self.remove_user_data_var.get(),
        }
        self._run_worker(lambda report: uninstall_app(options, report), success_button="Close")

    def _run_worker(self, work: Callable[[Report], None], success_button: str) -> None:
        self.running = True
        self.primary_button.set_enabled(False)
        self.secondary_button.set_enabled(False)

        def report(progress: float, text: str) -> None:
            self.root.after(0, lambda: self._set_progress(progress, text))

        def target() -> None:
            try:
                work(report)
            except Exception as error:  # noqa: BLE001 - surfaced to the installer UI.
                self.root.after(0, lambda: self._finish(False, str(error), success_button))
                return
            self.root.after(0, lambda: self._finish(True, "Done.", success_button))

        threading.Thread(target=target, daemon=True).start()

    def _finish(self, ok: bool, message: str, success_button: str) -> None:
        self.running = False
        self._set_progress(1.0 if ok else 0.0, message)
        self.primary_button.set_text(success_button if ok else "Retry")
        self.primary_button.command = self._close if ok else (self._start_uninstall if self.mode == "uninstall" else self._start_install)
        self.primary_button.set_enabled(True)
        self.secondary_button.set_text("Close")
        self.secondary_button.command = self._close
        self.secondary_button.set_enabled(True)

    def _set_progress(self, progress: float, text: str) -> None:
        progress = max(0.0, min(1.0, progress))
        width = 4 + int(652 * progress)
        self.progress_canvas.coords(self.progress_fill, 4, 9, width, 19)
        color = "#ffd477" if progress < 1 else "#30e3cf"
        self.progress_canvas.itemconfigure(self.progress_fill, fill=color)
        self.canvas.itemconfigure(self.status_id, text=text)

    def _animate_header(self) -> None:
        try:
            if not self.root.winfo_exists():
                return
            if self.header_frames:
                self.header_index = (self.header_index + 1) % len(self.header_frames)
                self.canvas.itemconfigure(self.header_item, image=self.header_frames[self.header_index])
            self.animation_after_id = self.root.after(42, self._animate_header)
        except tk.TclError:
            return

    def _start_drag(self, event: tk.Event) -> None:
        self.drag_start = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def _drag(self, event: tk.Event) -> None:
        if not self.drag_start:
            return
        start_x, start_y, window_x, window_y = self.drag_start
        self.root.geometry(f"+{window_x + event.x_root - start_x}+{window_y + event.y_root - start_y}")

    def run(self) -> None:
        self.root.mainloop()

    def _close(self) -> None:
        if self.running:
            return
        if self.animation_after_id:
            try:
                self.root.after_cancel(self.animation_after_id)
            except tk.TclError:
                pass
            self.animation_after_id = None
        try:
            self.root.destroy()
        except tk.TclError:
            pass


def main(default_mode: str | None = None) -> None:
    mode = default_mode
    args = {arg.lower() for arg in sys.argv[1:]}
    exe_name = Path(sys.argv[0]).stem.lower()
    if "--uninstall" in args or "uninstall" in exe_name:
        mode = "uninstall"
    if "--install" in args or mode is None:
        mode = mode or "install"

    if os.name != "nt":
        raise SystemExit("Talk Dat! installer is Windows-only.")
    GlassInstaller(mode).run()


if __name__ == "__main__":
    main()
