# VideoNews: Windows-first installer (PowerShell 5.1+)
# powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1
[CmdletBinding()]
param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

function Invoke-Checked {
    param([string]$program, [string[]]$arguments)
    & $program @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$program returned exit code $LASTEXITCODE ($($arguments -join ' '))"
    }
}

Write-Host 'VideoNews - Windows installation' -ForegroundColor Cyan
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue) -or
    -not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw 'FFmpeg + ffprobe missing in PATH. Install with: winget install -e --id Gyan.FFmpeg, then restart PowerShell.'
}
$filters = (& ffmpeg -hide_banner -filters 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0 -or $filters -notmatch '\bsubtitles\b') {
    throw 'FFmpeg is missing the libass subtitles filter. Use a full FFmpeg build.'
}
$encoders = (& ffmpeg -hide_banner -encoders 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0 -or $encoders -notmatch '\blibx264\b') {
    throw 'FFmpeg is missing the libx264 encoder. Use a full FFmpeg build.'
}

$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        Invoke-Checked -program 'py' -arguments @('-3.11', '-m', 'venv', '.venv')
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $version = (& python -c 'import sys; print("{}.{}".format(*sys.version_info[:2]))').Trim()
        if ($LASTEXITCODE -ne 0 -or $version -ne '3.11') {
            throw 'Install Python 3.11 (winget install -e --id Python.Python.3.11).'
        }
        Invoke-Checked -program 'python' -arguments @('-m', 'venv', '.venv')
    } else {
        throw 'Install Python 3.11 (winget install -e --id Python.Python.3.11).'
    }
}
if (-not (Test-Path -LiteralPath $venvPython)) { throw 'Virtual environment creation failed.' }
$venvVersion = (& $venvPython -c 'import sys; print("{}.{}".format(*sys.version_info[:2]))').Trim()
if ($LASTEXITCODE -ne 0 -or $venvVersion -ne '3.11') {
    throw "Existing .venv uses Python $venvVersion. Rename .venv and rerun installer."
}

Invoke-Checked -program $venvPython -arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-Checked -program $venvPython -arguments @('-m', 'pip', 'install', '-e', '.[dev]')
$envPath = Join-Path $root '.env'
if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath (Join-Path $root '.env.example') -Destination $envPath
    Write-Host 'Created .env. Add your own API credentials.' -ForegroundColor Yellow
} else {
    Write-Host 'Preserved existing .env file.' -ForegroundColor Green
}
foreach ($folder in @('output', 'metrics', '.temp', '.secrets')) {
    New-Item -ItemType Directory -Path (Join-Path $root $folder) -Force | Out-Null
}

Invoke-Checked -program $venvPython -arguments @('-c', 'import bot.main; import news_video_processor; import scripts.cli; print("Python imports OK")')
if (-not $SkipTests) {
    Invoke-Checked -program $venvPython -arguments @('-m', 'pytest', '-q')
}
Write-Host 'Windows installation complete.' -ForegroundColor Green
Write-Host 'Configure .env and keep VIDEO_UPLOAD_ENABLED=false for your first render.'
Write-Host 'Run .\.venv\Scripts\python.exe -m scripts.doctor --mode cli'
Write-Host 'Run .\.venv\Scripts\python.exe -m scripts.cli --title "VideoNews demonstration" --format short'
