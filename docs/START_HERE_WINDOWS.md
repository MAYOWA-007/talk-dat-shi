# Start Here: Talk Dat Shi for Windows

## Fast Path

1. If you downloaded the setup EXE, run `Talk-Dat-Shi-Setup.exe` and leave "Launch after install" enabled.
2. If you downloaded the portable ZIP, run `Talk Dat Shi.exe`.
3. In setup, choose a wired provider such as Deepgram, OpenAI, ElevenLabs, AssemblyAI, or Gemini.
4. Paste your own provider API key.
5. Save setup.
6. Open Notepad and test one sentence.

## Controls

- Hold `Ctrl+Win` to dictate while held.
- Click the pill to toggle hands-free dictation.
- Click the pill again, or press a trigger combo, to stop.
- Right-click the pill for Settings, History, and Scratchpad.
- Settings > Core changes the glass menu theme live while the window is open.
- Use `Ctrl+Win+Esc` as panic stop.

## Privacy

This download does not include API keys or private user data.

Your keys, provider options, dictionary, snippets, transcript history, live draft, and scratchpad tabs are saved locally under:

```text
%APPDATA%\TalkDatShi
```

The microphone does not open until you trigger dictation.

## Troubleshooting

- If Windows warns about an unsigned app, choose "More info" and "Run anyway" only if you downloaded it from the official GitHub release.
- If nothing pastes, check Settings > Core and make sure auto paste is enabled.
- If transcription fails, check Settings > Providers for the provider key, model, API base, and adapter status.
- If the pill blocks something, hover over it for two seconds and it fades translucent.
- If you used the installer, remove the app from Windows Apps. The custom uninstaller keeps private local data unless you select the removal option.
