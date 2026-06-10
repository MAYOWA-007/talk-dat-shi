param(
    [switch]$SkipExeBuild
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$AppExe = Join-Path $Root "dist\Talk Dat!.exe"
$UninstallerExe = Join-Path $Root "dist\Talk Dat! Uninstaller.exe"
$InstallerExe = Join-Path $Root "dist\Talk Dat! Installer.exe"
$ReleaseDir = Join-Path $Root "release"
$ReleaseInstaller = Join-Path $ReleaseDir "Talk-Dat-Setup.exe"
$IconPath = Join-Path $Root "knight_flow\assets\app_icon.ico"
$StartHereDoc = Join-Path $Root "docs\START_HERE_WINDOWS.md"
$InstallDoc = Join-Path $Root "docs\INSTALL.md"
$ProvidersDoc = Join-Path $Root "docs\PROVIDERS.md"

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $Root ".venv")
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")
& $Python -m pip install pyinstaller

if (-not (Test-Path $IconPath)) {
    $IconPath = (& $Python -c "from knight_flow.icon import ensure_icon_file; print(ensure_icon_file())").Trim()
}

if (-not $SkipExeBuild) {
    & (Join-Path $Root "build-exe.ps1")
}

if (-not (Test-Path $AppExe)) {
    throw "Missing app EXE. Run .\build-exe.ps1 first, or omit -SkipExeBuild."
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

$CommonArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--icon", "$IconPath",
    "--hidden-import", "PIL._tkinter_finder"
)

$AssetAdds = @(
    @((Join-Path $Root "knight_flow\assets\app_icon.ico"), "knight_flow/assets"),
    @((Join-Path $Root "knight_flow\assets\app_icon.png"), "knight_flow/assets"),
    @((Join-Path $Root "knight_flow\assets\logo.png"), "knight_flow/assets"),
    @((Join-Path $Root "knight_flow\assets\flow_pill_240.png"), "knight_flow/assets"),
    @((Join-Path $Root "knight_flow\assets\flow_pill_240.json"), "knight_flow/assets")
)

$UninstallerArgs = @()
$UninstallerArgs += $CommonArgs
foreach ($AssetAdd in $AssetAdds) {
    if (Test-Path $AssetAdd[0]) {
        $UninstallerArgs += @("--add-data", "$($AssetAdd[0]);$($AssetAdd[1])")
    }
}
$UninstallerArgs += @("--name", "Talk Dat! Uninstaller", (Join-Path $Root "installer\uninstall_entry.py"))

& $Python $UninstallerArgs

if (-not (Test-Path $UninstallerExe)) {
    throw "Custom uninstaller build failed."
}

$InstallerArgs = @()
$InstallerArgs += $CommonArgs
foreach ($AssetAdd in $AssetAdds) {
    if (Test-Path $AssetAdd[0]) {
        $InstallerArgs += @("--add-data", "$($AssetAdd[0]);$($AssetAdd[1])")
    }
}
$InstallerArgs += @(
    "--add-data", "$AppExe;payload",
    "--add-data", "$UninstallerExe;payload",
    "--add-data", "$StartHereDoc;payload/docs",
    "--add-data", "$InstallDoc;payload/docs",
    "--add-data", "$ProvidersDoc;payload/docs",
    "--name", "Talk Dat! Installer",
    (Join-Path $Root "installer\install_entry.py")
)

& $Python $InstallerArgs

if (-not (Test-Path $InstallerExe)) {
    throw "Custom installer build failed."
}

Copy-Item $InstallerExe $ReleaseInstaller -Force

Write-Output "Custom installer output:"
Write-Output $ReleaseInstaller
