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
- Optional speaker-output mute while recording, with automatic restore on release/cancel/timeout.
- Fullscreen media/game guard keeps the pill hidden over fullscreen apps. Dictation and pasting keep working while hidden, so push-to-talk never disturbs a game or video; an option can show the pill instead.
- Fully local on-device dictation: 18 downloadable open-weight models (NVIDIA Parakeet and Canary, Whisper, Distil-Whisper, GigaAM) with an in-app downloader. Parakeet TDT 0.6B v3 is the recommended default, the same pick as Handy.
- First-run onboarding for provider, model, mode, language, API base, and API key.
- Right-click overlay menu for Settings, History, and a tabbed local Scratchpad.
- Glass settings UI with 10 named theme families, dark/light variants, and live theme preview.
- Version tracking plus GitHub Release update checks and installer download from inside the app.
- Local transcript history and live draft files, with a choice of plain JSONL or a local searchable SQLite database.
- Smart leading space, snippets, custom dictionary words, replacements, cleanup transforms, and optional local Ollama rewrites.
- Provider framework with Deepgram streaming, several cloud batch adapters, and a local on-device engine lane.

## Install

Go to [Releases](https://github.com/MAYOWA-007/talk-dat/releases) and download one Windows asset:

- Recommended: `Talk-Dat-Setup.exe`
- Portable/no installer: `Talk-Dat-Windows-Portable.zip`

Launch Talk Dat!, complete setup with your own provider key, then test in Notepad. The microphone stays off until you click the pill or press a trigger.

The setup EXE uses a custom glass installer. It installs per-user under `%LOCALAPPDATA%\Programs\Talk Dat!`, creates Start/Desktop shortcuts, optionally starts with Windows, registers a matching glass uninstaller in Windows Apps, and never includes API keys or private user data.

The portable ZIP includes `START-HERE.md`, `INSTALL.md`, and `PROVIDERS.md`.

## Updates

Talk Dat! tracks its installed app version locally and checks the public GitHub Releases feed when update checks are enabled. Settings > Core and the tray menu can check for the latest release, download `Talk-Dat-Setup.exe` into `%APPDATA%\TalkDat\updates`, and launch the installer.

Automatic startup checks are enabled by default. Automatic installer download is available as a setting, but it is off by default so users choose when to run a new installer.

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

## Public Repo Safety

Release assets are built by `.github/workflows/release-windows.yml` when a tag like `v0.1.0` is pushed, or manually from GitHub Actions.

Before publishing or tagging a release:

```powershell
python .\scripts\prepublish_check.py
python .\scripts\check_settings_themes.py
```

Also read [docs/PUBLIC_RELEASE_CHECKLIST.md](docs/PUBLIC_RELEASE_CHECKLIST.md). The scanner is a guardrail, not a substitute for reviewing your commit.

When you are ready to create the public repository, follow [docs/GITHUB_PUBLISH.md](docs/GITHUB_PUBLISH.md).

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
