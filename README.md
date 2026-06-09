# Talk Dat Shi

Talk Dat Shi is a Windows-first local dictation overlay. It stays as a small always-on-top animated pill, records only when you trigger it, sends audio to the speech-to-text provider you configure, cleans up the result, and pastes it into the active app.

This is a bring-your-own-key project. The repository does not include API keys, private config, transcript history, or built binaries.

> Talk Dat Shi is an independent project and is not affiliated with Wispr, Wispr Flow, Deepgram, OpenAI, ElevenLabs, AssemblyAI, Google, or any other provider.

## Features

- Push-to-talk dictation with `Ctrl+Win`.
- Hands-free toggle with `Ctrl+Win+Space`.
- Pill click toggles hands-free on/off; pressing a trigger combo ends a pill-click session.
- Command/edit mode with `Ctrl+Win+Alt`.
- Panic stop with `Ctrl+Win+Esc`.
- Animated bottom overlay that is idle until activated.
- Soft hover glow with a delayed translucent fade when the pill is covering screen content.
- First-run onboarding for provider, model, mode, language, API base, and API key.
- Right-click overlay menu for Settings and History.
- Local transcript history and live draft files.
- Smart leading space, snippets, custom dictionary words, replacements, cleanup transforms, and optional local Ollama rewrites.
- Provider framework with Deepgram streaming plus several batch transcription adapters.

## Install

Download the installer from a GitHub Release when one is published, then launch Talk Dat Shi. First-run onboarding will ask for your provider key and model.

For a no-installer portable run, download `Talk Dat Shi.exe` from a release and run it directly. Startup registration is optional.

## Run From Source

Requirements:

- Windows 10 or newer
- Python 3.11 or newer
- A microphone
- Your own speech-to-text provider key

```powershell
git clone https://github.com/YOUR-ORG/talk-dat-shi.git
cd talk-dat-shi
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

The app saves local user config here:

```text
%APPDATA%\TalkDatShi\config.json
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

Build the Inno Setup installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
```

The installer output is written to `release\Talk-Dat-Shi-Setup.exe`.

## Provider Support

See [docs/PROVIDERS.md](docs/PROVIDERS.md). Current wired adapters include:

- Deepgram streaming
- OpenAI-compatible batch transcription
- ElevenLabs batch transcription
- AssemblyAI batch transcription
- Google Gemini batch transcription

Other providers appear in the settings framework for planning and configuration, but still need dedicated adapters before they can transcribe inside the app.

## Public Repo Safety

Before publishing or tagging a release:

```powershell
python .\scripts\prepublish_check.py
```

Also read [docs/PUBLIC_RELEASE_CHECKLIST.md](docs/PUBLIC_RELEASE_CHECKLIST.md). The scanner is a guardrail, not a substitute for reviewing your commit.

When you are ready to create the public repository, follow [docs/GITHUB_PUBLISH.md](docs/GITHUB_PUBLISH.md).

## Privacy

Talk Dat Shi does not run a server. Audio is captured locally only after a trigger, then sent to the selected STT provider for transcription. Transcript history is local and can be disabled in Settings.

Local files:

```text
%APPDATA%\TalkDatShi\config.json
%APPDATA%\TalkDatShi\history.jsonl
%APPDATA%\TalkDatShi\full-transcript-history.txt
%APPDATA%\TalkDatShi\live-transcript-draft.txt
```

Do not commit these files.

## License

No open-source license has been selected yet. Until a license is added, all rights are reserved by the project owner. Choose a license deliberately before inviting outside contributors.
