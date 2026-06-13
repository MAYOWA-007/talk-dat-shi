# Talk Dat!

Talk Dat! is a Windows-first local dictation overlay. It stays as a small always-on-top animated pill, records only when you trigger it, sends audio to the speech-to-text provider you configure, cleans up the result, and pastes it into the active app.

The visual system has two core pieces: **Talk Stone**, the matte black roman-clay app mark, and **The Pill**, the animated Flow dictation overlay.

Cloud providers are bring-your-own-key. The Local / On-Device brand needs no key at all: open-weight models download once and transcribe entirely on your PC. The repository does not include API keys, private config, transcript history, model weights, or built binaries.

> Talk Dat! is an independent project and is not affiliated with Wispr, Wispr Flow, Deepgram, OpenAI, ElevenLabs, AssemblyAI, Google, or any other provider.

## Features

- Push-to-talk dictation with `Ctrl+Win`.
- Hands-free toggle with `Ctrl+Win+Space`.
- Pill click toggles hands-free on/off; pressing a trigger combo ends a pill-click session.
- Command/edit mode with `Ctrl+Win+Alt`.
- Panic stop with `Ctrl+Win+Esc`.
- Animated bottom overlay that is idle until activated.
- Soft hover glow with a delayed translucent fade when the pill is covering screen content.
- Optional speaker-output ducking while recording: background sound fades down on activation and back up on release, with automatic restore on cancel/timeout.
- Pause/resume dictation and restart from the tray; pick clipboard paste or simulated typing for apps that block paste.
- One-click in-app updates: when a new version exists the tray shows "Install update", and the update window downloads and launches the installer for you.
- Fullscreen media/game guard keeps the pill hidden over fullscreen apps. Dictation and pasting keep working while hidden, so push-to-talk never disturbs a game or video; an option can show the pill instead.
- Fully local on-device dictation: 18 downloadable open-weight models (NVIDIA Parakeet and Canary, Whisper, Distil-Whisper, GigaAM) with an in-app downloader. Parakeet TDT 0.6B v3 is the recommended default, the same pick as Handy.
- First-run onboarding for provider, model, mode, language, API base, and API key.
- Right-click overlay menu for Settings, History, and a tabbed local Scratchpad.
- Glass settings UI with 10 named theme families, dark/light variants, and live theme preview.
- Version tracking plus GitHub Release update checks and installer download from inside the app.
- Local transcript history and live draft files, with a choice of plain JSONL or a local searchable SQLite database.
- Smart leading space, snippets with `{date}`/`{time}`/`{clipboard}` variables, custom dictionary words, replacements, and cleanup transforms.
- Smart formatting (Wispr-style): every dictation is reformatted into clean written text with correct punctuation (including question marks), capitalization, and bullets/numbered lists inferred from what you said. Runs after any STT model; uses your AI provider when configured, else a built-in offline formatter.
- AI rewrites with your own key: OpenAI, Anthropic, Gemini, Groq, or local Ollama power smart formatting, Polish, tone presets (formal, friendly, concise), and Translate.
- Per-app profiles: match a process name (for example `slack`) to its own cleanup level, tone, language, and auto-enter behavior.
- Voice editing commands ("scratch that", "delete last word", "new line"), optional PII redaction and profanity censoring.
- History search, pinned transcripts, Markdown/text/SRT export, and a local Stats window (words, streaks, estimated time saved).
- Audio controls: microphone picker, gain boost, whisper-quiet mode, mic test, and an opt-in wake word (beta, via openwakeword).
- Meeting mode (beta): chunked transcription of system audio (or mic fallback) into timestamped Markdown notes.
- Power-user platform: local control API + CLI flags for Stream Deck/AutoHotkey, a Chrome/Edge companion extension, dictionary/snippet packs, settings backup/restore, diagnostics export, portable mode via `portable.flag`, stable/beta update channels, user plugins, pill position presets, and a reduce-motion option.
- Provider framework with Deepgram streaming, several cloud batch adapters, and a local on-device engine lane.

## Install

Go to [Releases](https://github.com/MAYOWA-007/talk-dat/releases) and download one Windows asset:

- Recommended: `Talk-Dat-Setup.exe`
- Portable/no installer: `Talk-Dat-Windows-Portable.zip`

Launch Talk Dat!, complete setup with your own provider key, then test in Notepad. The microphone stays off until you click the pill or press a trigger.

The setup EXE uses a custom glass installer. It installs per-user under `%LOCALAPPDATA%\Programs\Talk Dat!`, creates Start/Desktop shortcuts, optionally starts with Windows, registers a matching glass uninstaller in Windows Apps, and never includes API keys or private user data.

The portable ZIP includes `START-HERE.md`, `INSTALL.md`, and `PROVIDERS.md`.

## Updates

Talk Dat! checks the public GitHub Releases feed on launch and every 24 hours while running. When a new version exists, a glass update window shows the version jump, release notes, and a one-click **Install now** with a live download progress bar; the app hands off to the installer and closes itself so the update completes cleanly. **Skip this version** and **Later** are always available, and `Settings > Core > Check / install latest` runs the same flow on demand.

Automatic startup checks are enabled by default. Automatic installer download is available as a setting (the update window then opens with the installer already fetched), but it is off by default so users choose when to run a new installer.

For what is coming next, see [docs/ROADMAP.md](docs/ROADMAP.md).

## Run From Source

Requirements:

- Windows 10 or newer
- Python 3.11 or newer
- A microphone
- Your own speech-to-text provider key

```powershell
git clone https://github.com/MAYOWA-007/talk-dat.git
cd talk-dat
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

The app saves local user config here:

```text
%APPDATA%\TalkDat\config.json
```

## Build

Build the one-file Windows EXE:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-exe.ps1
```

Build the EXE and create a desktop shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-exe.ps1 -CreateDesktopShortcut
```

Build the custom glass Windows installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
```

The installer output is written to `release\Talk-Dat-Setup.exe`. The compatibility command above delegates to `build-custom-installer.ps1`.

## Provider Support

See [docs/PROVIDERS.md](docs/PROVIDERS.md). Current wired adapters include:

- Deepgram streaming
- OpenAI-compatible batch transcription
- ElevenLabs batch transcription
- AssemblyAI batch transcription
- Google Gemini batch transcription
- Local / On-Device batch transcription (onnx-asr and faster-whisper engines, no API key)

Other providers appear in the settings framework for planning and configuration, but still need dedicated adapters before they can transcribe inside the app.

## For maintainers

Releasing and contributing notes live in the docs folder, so the rest of this README stays focused on using the app:

- Release builds are produced by `.github/workflows/release-windows.yml` when a `vX.Y.Z` tag is pushed (or a `release/vX.Y.Z` branch). It builds the installer and portable ZIP and publishes the GitHub release.
- Before tagging, run `python .\scripts\prepublish_check.py` and `python .\scripts\check_settings_themes.py`, then follow [docs/PUBLIC_RELEASE_CHECKLIST.md](docs/PUBLIC_RELEASE_CHECKLIST.md).
- Planned features and the roadmap are in [docs/ROADMAP.md](docs/ROADMAP.md).

## Privacy

Talk Dat! does not run a server. Audio is captured locally only after a trigger, then sent to the selected STT provider for transcription. Transcript history is local and can be disabled in Settings.

User API keys, dictionaries, snippets, provider advanced options, transcript history, and scratchpad content live under `%APPDATA%\TalkDat`. They are not part of the public GitHub repository or default download.

Uninstall keeps `%APPDATA%\TalkDat` by default. The custom uninstaller offers a separate option to remove that private local data.

Local files:

```text
%APPDATA%\TalkDat\config.json
%APPDATA%\TalkDat\history.jsonl
%APPDATA%\TalkDat\history.db
%APPDATA%\TalkDat\full-transcript-history.txt
%APPDATA%\TalkDat\live-transcript-draft.txt
%APPDATA%\TalkDat\scratchpad-tabs.json
%APPDATA%\TalkDat\models\
```

Downloaded local model weights live under `models\` and can be removed from Settings > Providers > Local models.

History storage defaults to the JSONL file. Settings > Privacy can switch it to a local SQLite database (`history.db`); existing JSONL entries are imported automatically the first time the database backend is used. Both stores stay on your machine.

Do not commit these files.

## License

No open-source license has been selected yet. Until a license is added, all rights are reserved by the project owner. Choose a license deliberately before inviting outside contributors.
