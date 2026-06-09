# Installation

## Download From GitHub

1. Open the [GitHub Releases page](https://github.com/MAYOWA-007/talk-dat-shi/releases).
2. Download one Windows asset:
   - Recommended: `Talk-Dat-Shi-Setup.exe`
   - Portable/no installer: `Talk-Dat-Shi-Windows-Portable.zip`
3. Verify the checksum in `SHA256SUMS.txt` if you want an integrity check.

The release assets do not contain API keys, dictionaries, snippets, private config, or transcript history.

## Recommended: Windows Installer

1. Download `Talk-Dat-Shi-Setup.exe` from a release.
2. Run the installer.
3. Leave startup enabled only if you want Talk Dat Shi to launch when Windows signs in.
4. Launch the app.
5. Complete onboarding with your own provider key and model.

The installer does not contain API keys. It installs only the app executable and optional startup shortcut.

## Portable EXE

1. Download `Talk-Dat-Shi-Windows-Portable.zip`.
2. Extract it somewhere you trust, such as `%LOCALAPPDATA%\Programs\Talk Dat Shi`.
3. Open `START-HERE.md`.
4. Run `Talk Dat Shi.exe`.
5. Complete onboarding.

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
git clone https://github.com/MAYOWA-007/talk-dat-shi.git
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

The setup window also reminds users that the microphone stays off until a trigger is pressed. The key is saved locally in `%APPDATA%\TalkDatShi\config.json`.

Recommended first test:

1. Open Notepad.
2. Click the pill or hold `Ctrl+Win`.
3. Speak one sentence.
4. Click the pill again or release the trigger.
5. Confirm the cleaned transcript pasted into Notepad.

## Uninstall

If installed through the setup EXE, uninstall from Windows Apps. If using the portable EXE, quit Talk Dat Shi, delete the EXE, and optionally delete:

```text
%APPDATA%\TalkDatShi
```

Deleting that folder removes local config and transcript history.
