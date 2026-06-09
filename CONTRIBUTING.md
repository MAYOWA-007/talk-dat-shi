# Contributing

Thanks for helping improve Talk Dat Shi.

## Ground Rules

- Do not commit API keys, private config files, transcript history, logs, screenshots with private text, or built binaries.
- Run `python .\scripts\prepublish_check.py` before opening a PR.
- Keep provider adapters small and explicit. Each provider should document auth, request shape, supported modes, and failure behavior.
- Avoid logging secrets. Error messages should identify provider/model, not token values.
- Keep the overlay idle unless a user trigger starts recording.

## Local Setup

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-exe.ps1
```

## Pull Requests

Include:

- What changed
- Provider/model tested, if relevant
- Whether microphone activation, cancel, panic stop, and no-speech timeout were checked
- Screenshots only when they do not expose private text or keys
