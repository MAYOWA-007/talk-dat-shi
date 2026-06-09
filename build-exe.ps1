param(
    [switch]$CreateDesktopShortcut
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$ExePath = Join-Path $Root "dist\Talk Dat Shi.exe"
$AssetsPath = Join-Path $Root "knight_flow\assets"
$RuntimeAssets = @(
    "flow_pill_240.png",
    "flow_pill_240.json"
)

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $Root ".venv")
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")
& $Python -m pip install pyinstaller

$IconPath = (& $Python -c "from knight_flow.icon import ensure_icon_file; print(ensure_icon_file())").Trim()

$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "Talk Dat Shi",
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

$PyInstallerArgs += (Join-Path $Root "talk_dat_shi.py")

& $Python @PyInstallerArgs

Write-Output "Built:"
Write-Output $ExePath

if ($CreateDesktopShortcut) {
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $Desktop "Talk Dat Shi.lnk"
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = Split-Path -Parent $ExePath
    $Shortcut.IconLocation = "$ExePath,0"
    $Shortcut.Description = "Launch Talk Dat Shi dictation overlay."
    $Shortcut.Save()
    Write-Output "Desktop shortcut:"
    Write-Output $ShortcutPath
}
