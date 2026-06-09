# GitHub Publish Guide

Do this only when you are ready to create the new public repository.

## Recommended Ownership

Create a GitHub organization if both a personal and business account need control. Put the repository under that organization and add both accounts as owners/admins.

## Safe First Push

From the project root:

```powershell
python .\scripts\prepublish_check.py
git init
git add .gitignore .gitattributes .env.example README.md SECURITY.md CONTRIBUTING.md requirements.txt *.ps1 talk_dat_shi.py knight_flow docs installer scripts
git status --short
git diff --cached --stat
git diff --cached
git commit -m "Prepare public Talk Dat Shi release"
git branch -M main
git remote add origin https://github.com/YOUR-ORG/talk-dat-shi.git
git push -u origin main
```

Do not use `git add -A` until you have reviewed ignored files and confirmed no private local files are present.

## Release Uploads

Build locally:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
```

Upload `release\Talk-Dat-Shi-Setup.exe` to a GitHub Release. Do not commit `release/`, `dist/`, or `build/`.
