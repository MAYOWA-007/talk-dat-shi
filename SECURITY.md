# Security Policy

## Reporting Issues

Do not post API keys, transcripts, or private config files in GitHub issues. If you need to report a security issue, contact the repository owner privately through the contact method listed on the GitHub profile or organization.

## Secrets

Talk Dat! is a bring-your-own-key application. The repo should never contain provider keys. User keys are stored locally in:

```text
%APPDATA%\TalkDat\config.json
```

Before publishing or releasing, run:

```powershell
python .\scripts\prepublish_check.py
```

## Runtime Privacy

The app records only after a trigger is pressed or hands-free mode is explicitly enabled. Audio is sent to the selected speech-to-text provider. Transcript history is local and can be disabled in Settings.

## Supported Versions

Public release support starts at `0.1.0` once the first GitHub release is published.
