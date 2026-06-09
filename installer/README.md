# Installer

This folder contains the Inno Setup definition for a per-user Windows installer.

Build the installer from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
```

Output:

```text
release\Talk-Dat-Shi-Setup.exe
```

The installer includes the packaged EXE only. It does not include API keys, user config, transcript history, or local logs. Users enter their own provider key during first-run onboarding.

The optional startup task creates a shortcut in the user's Startup folder so Talk Dat Shi launches when Windows signs in.
