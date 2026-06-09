# Installation

## Recommended: Windows Installer

1. Download `Talk-Dat-Shi-Setup.exe` from a release.
2. Run the installer.
3. Leave startup enabled only if you want Talk Dat Shi to launch when Windows signs in.
4. Launch the app.
5. Complete onboarding with your own provider key and model.

The installer does not contain API keys. It installs only the app executable and optional startup shortcut.

## Portable EXE

1. Download `Talk Dat Shi.exe` from a release.
2. Put it anywhere you trust, such as `%LOCALAPPDATA%\Programs\Talk Dat Shi`.
3. Run it.
4. Complete onboarding.

Optional startup registration from source:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-startup.ps1
```

Remove startup registration:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall-startup.ps1
```

## From Source

```powershell
git clone https://github.com/YOUR-ORG/talk-dat-shi.git
cd talk-dat-shi
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## Build A Release Locally

Build the EXE:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-exe.ps1
```

Build the installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
```

The installer helper requires Inno Setup 6.

## First-Run Onboarding

On a fresh config, Talk Dat Shi opens a setup window where the user chooses:

- Provider
- Model
- Mode / trim
- Language
- API base
- API key

The key is saved locally in `%APPDATA%\TalkDatShi\config.json`.

## Uninstall

If installed through the setup EXE, uninstall from Windows Apps. If using the portable EXE, quit Talk Dat Shi, delete the EXE, and optionally delete:

```text
%APPDATA%\TalkDatShi
```

Deleting that folder removes local config and transcript history.
