# GitHub Publish Guide

This repository is published at:

```text
https://github.com/MAYOWA-007/talk-dat
```

## Recommended Ownership

Create a GitHub organization if both a personal and business account need control. Put the repository under that organization and add both accounts as owners/admins.

## Safe First Push

This section is kept for future forks or new repos. For the current public repo, push normal updates to `main`.

From the project root:

```powershell
python .\scripts\prepublish_check.py
git init
git add .gitignore .gitattributes .env.example README.md SECURITY.md CONTRIBUTING.md requirements.txt *.ps1 talk_dat.py knight_flow docs installer scripts
git status --short
git diff --cached --stat
git diff --cached
git commit -m "Prepare public Talk Dat! release"
git branch -M main
git remote add origin https://github.com/MAYOWA-007/talk-dat.git
git push -u origin main
```

Do not use `git add -A` until you have reviewed ignored files and confirmed no private local files are present.

## Release Uploads

Automated release builds are handled by `.github/workflows/release-windows.yml`.

To create a public release:

```powershell
python .\scripts\prepublish_check.py
git status --short
git tag v0.1.0
git push origin v0.1.0
```

The workflow creates:

- `Talk-Dat-Setup.exe` custom glass installer
- `Talk-Dat-Windows-Portable.zip`
- `SHA256SUMS.txt`

For a local manual build:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-custom-installer.ps1
```

Upload `release\Talk-Dat-Setup.exe`, a portable ZIP, and checksums to a GitHub Release. Do not commit `release/`, `dist/`, `build/`, generated `.spec` files, API keys, private config, or transcript history.
