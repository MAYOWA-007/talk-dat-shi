# Repository Instructions

Guidance for contributors and AI coding agents working in this repository.

## Ground rules

- Never commit secrets, API keys, built binaries, virtual environments, or user-specific local config (anything under `%APPDATA%\TalkDat`).
- Run `python .\scripts\prepublish_check.py` and `python .\scripts\check_settings_themes.py` before opening a pull request or tagging a release.
- Keep user-facing docs (`README.md` and `docs/` provider/install guides) written for end users. Keep release and publishing mechanics in the maintainer docs under `docs/`.
- Match the existing code style; add a short `docs/` note for any user-visible feature.
