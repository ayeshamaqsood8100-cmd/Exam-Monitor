[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,

    [Parameter(Mandatory = $true)]
    [string]$ExamId,

    [Parameter(Mandatory = $true)]
    [string]$OutputLabel
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildConfigPath = Join-Path $RepoRoot "agent\build_config.py"
$BuildVenvPath = Join-Path $RepoRoot ".build-venv-windows"
$BuildDir = Join-Path $RepoRoot "build"
$DistDir = Join-Path $RepoRoot "dist"
$ReleaseDir = Join-Path $RepoRoot "release"
$SafeLabel = ($OutputLabel -replace "[^A-Za-z0-9_-]", "-").Trim("-")

if ([string]::IsNullOrWhiteSpace($SafeLabel)) {
    throw "OutputLabel must contain at least one letter or number."
}

$ArtifactName = "MarkazSentinel-$SafeLabel"
$ExePath = Join-Path $DistDir "$ArtifactName.exe"
$ZipPath = Join-Path $ReleaseDir "$ArtifactName.zip"

function Get-BootstrapPython {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            & py -3.12 -c "print('ok')" | Out-Null
            return @{ Command = "py"; Arguments = @("-3.12") }
        } catch {
        }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Command = "python"; Arguments = @() }
    }

    throw "Could not find a Python interpreter. Install Python 3.12 or ensure 'py'/'python' is on PATH."
}

function Write-BuildConfig {
    $escapedBackendUrl = $BackendUrl.Replace("'", "''")
    $escapedExamId = $ExamId.Replace("'", "''")

    $content = @"
"""Generated during Windows packaging. Do not edit manually."""
BACKEND_URL = '$escapedBackendUrl'
EXAM_ID = '$escapedExamId'
"@

    Set-Content -Path $BuildConfigPath -Value $content -Encoding UTF8
}

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

$bootstrapPython = Get-BootstrapPython

if (-not (Test-Path $BuildVenvPath)) {
    & $bootstrapPython.Command @($bootstrapPython.Arguments + @("-m", "venv", $BuildVenvPath))
}

$VenvPython = Join-Path $BuildVenvPath "Scripts\python.exe"

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $RepoRoot "agent\requirements.txt") pyinstaller

Write-BuildConfig

if (Test-Path $ExePath) {
    Remove-Item $ExePath -Force
}

if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

$pyInstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--noconsole",
    "--name", $ArtifactName,
    "--distpath", $DistDir,
    "--workpath", $BuildDir,
    "--specpath", $BuildDir,
    "--paths", $RepoRoot,
    "--collect-submodules", "pynput",
    "--hidden-import", "pygetwindow",
    "--hidden-import", "pyperclip",
    (Join-Path $RepoRoot "agent\windows_entry.py")
)

Push-Location $RepoRoot
try {
    & $VenvPython @pyInstallerArgs
} finally {
    Pop-Location
}

if (-not (Test-Path $ExePath)) {
    throw "Build did not produce the expected executable at $ExePath"
}

Compress-Archive -Path $ExePath -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "Build complete."
Write-Host "EXE: $ExePath"
Write-Host "ZIP: $ZipPath"
