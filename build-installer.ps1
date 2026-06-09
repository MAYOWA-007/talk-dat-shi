param(
    [switch]$SkipExeBuild
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallerScript = Join-Path $Root "installer\TalkDatShi.iss"

if (-not $SkipExeBuild) {
    & (Join-Path $Root "build-exe.ps1")
}

$IsccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
$IsccPath = if ($IsccCommand) { $IsccCommand.Source } else { "" }
if (-not $IsccPath) {
    $Candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($Candidate in $Candidates) {
        if ($Candidate -and (Test-Path $Candidate)) {
            $IsccPath = $Candidate
            break
        }
    }
}

if (-not $IsccPath) {
    throw "Inno Setup Compiler was not found. Install Inno Setup 6 or add ISCC.exe to PATH."
}

& $IsccPath $InstallerScript

Write-Output "Installer output:"
Write-Output (Join-Path $Root "release\Talk-Dat-Shi-Setup.exe")
