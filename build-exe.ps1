param(
    [switch]$CreateDesktopShortcut
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$ExePath = Join-Path $Root "dist\Talk Dat!.exe"
$AssetsPath = Join-Path $Root "knight_flow\assets"
$AssetIconPath = Join-Path $AssetsPath "app_icon.ico"
$ShortcutIconPath = Join-Path (Split-Path -Parent $ExePath) "Talk Dat!.ico"
$RuntimeAssets = @(
    "app_icon.ico",
    "app_icon.png",
    "favicon.ico",
    "favicon.png",
    "flow_pill_240.png",
    "flow_pill_240.json",
    "logo.ico",
    "logo.png"
)

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $Root ".venv")
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")
& $Python -m pip install pyinstaller

$IconPath = $AssetIconPath
if (-not (Test-Path $IconPath)) {
    $IconPath = (& $Python -c "from knight_flow.icon import ensure_icon_file; print(ensure_icon_file())").Trim()
}

$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "Talk Dat!",
    "--icon", "$IconPath",
    "--hidden-import", "pystray._win32",
    "--hidden-import", "PIL._tkinter_finder"
)

if (Test-Path $AssetsPath) {
    foreach ($Asset in $RuntimeAssets) {
        $AssetPath = Join-Path $AssetsPath $Asset
        if (Test-Path $AssetPath) {
            $PyInstallerArgs += @("--add-data", "$AssetPath;knight_flow/assets")
        }
    }
}

$PyInstallerArgs += (Join-Path $Root "talk_dat.py")

& $Python @PyInstallerArgs

Copy-Item $IconPath $ShortcutIconPath -Force

Write-Output "Built:"
Write-Output $ExePath
Write-Output "Shortcut icon:"
Write-Output $ShortcutIconPath

if ($CreateDesktopShortcut) {
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $Desktop "Talk Dat!.lnk"
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = Split-Path -Parent $ExePath
    $Shortcut.IconLocation = "$ShortcutIconPath,0"
    $Shortcut.Description = "Launch Talk Dat! dictation overlay."
    $Shortcut.Save()
    Write-Output "Desktop shortcut:"
    Write-Output $ShortcutPath
}
