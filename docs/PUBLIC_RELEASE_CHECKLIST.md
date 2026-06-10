# Public Release Checklist

Use this before creating the public GitHub repository, before the first commit, and before every release.

## GitHub Ownership

A GitHub repository has one owner: a user account or an organization. If personal and business accounts both need control, create the repository under a GitHub organization and add both accounts as organization owners or repo admins.

## Never Commit

- API keys or tokens
- `.env`
- `%APPDATA%\TalkDatShi\config.json`
- `%APPDATA%\TalkDatShi\history.jsonl`
- `%APPDATA%\TalkDatShi\full-transcript-history.txt`
- `%APPDATA%\TalkDatShi\live-transcript-draft.txt`
- `build/`
- `dist/`
- `release/`
- `.venv/`
- `tmp-*.png`, screenshots, local generated previews, or test videos

## Before First Public Commit

1. Delete local generated preview files from the project root.
2. Confirm `.gitignore` is present.
3. Run:

```powershell
python .\scripts\prepublish_check.py
```

4. Review every staged file:

```powershell
git status --short
git diff --staged
```

5. Confirm `README.md` does not contain local machine paths or private keys.
6. Decide whether the project is open source, source-available, or private-source/public-binary. Add a license only after making that decision.

## Release Build

### Automated GitHub Release

1. Run the prepublish check locally.
2. Commit all release-ready source changes.
3. Push `main`.
4. Create and push a version tag:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

5. Confirm GitHub Actions ran `Build Windows Release`.
6. Confirm the GitHub Release has:
   - `Talk-Dat-Shi-Setup.exe` custom glass installer
   - `Talk-Dat-Shi-Windows-Portable.zip`
   - `SHA256SUMS.txt`
7. Download the release from GitHub on a clean machine or temp folder.
8. Run the installer and confirm it creates Start/Desktop shortcuts, optional startup remains off unless selected, and Windows Apps shows the uninstaller.
9. Confirm onboarding appears on a fresh config with no API key.
10. Confirm Status shows the app idle and `session_active: False`.
11. Confirm dictation only starts after a trigger or pill click.
12. Run the custom uninstaller and confirm `%APPDATA%\TalkDatShi` is kept unless the private-data removal option is selected.

### Local Release Build

1. Run the prepublish check.
2. Build the EXE:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-exe.ps1
```

3. Build the custom glass installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-custom-installer.ps1
```

4. Launch the built EXE locally.
5. Confirm Status shows the app idle and `session_active: False`.
6. Confirm onboarding appears on a fresh config with no API key.
7. Create a portable ZIP containing:
   - `dist\Talk Dat Shi.exe`
   - `docs\START_HERE_WINDOWS.md`
   - `docs\INSTALL.md`
   - `docs\PROVIDERS.md`
8. Attach `release\Talk-Dat-Shi-Setup.exe`, the portable ZIP, and `SHA256SUMS.txt` to the GitHub release.
9. Include first-run, privacy, and checksum notes in the release notes.

## Safety Notes

- The repo should contain source and intentional assets only.
- The installer should never bake in a provider key.
- The uninstaller should keep private user data by default.
- User keys belong only in local AppData config or environment variables.
- Logs should not include API key values.
- The app should not open a microphone or provider connection until a trigger is pressed.
