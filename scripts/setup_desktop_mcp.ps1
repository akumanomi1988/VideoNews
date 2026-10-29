# Configure the Windows-only local VideoNews MCP connection for ChatGPT Desktop.
# Run: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_desktop_mcp.ps1
[CmdletBinding()]
param([switch]$SkipSmokeTest)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'configure_ffmpeg_path.ps1')
Add-VideoNewsFfmpegToPath
$python = Join-Path $repo '.venv\Scripts\python.exe'
$launcher = Join-Path $repo 'chatgpt-plugin\server\launch.py'
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'The plugin MCP manifest uses the Windows py launcher. Install the Python Launcher for Windows, then run this setup again.'
}
& py -3.11 --version
if ($LASTEXITCODE -ne 0) { throw 'py -3.11 must select Python 3.11 for this plugin.' }
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python venv missing. Run .\bootstrap.ps1 from $repo first."
}
if (-not (Test-Path -LiteralPath $launcher)) {
    throw 'The local plugin launcher is missing.'
}
$version = (& $python -c 'import sys; print(str(sys.version_info.major)+chr(46)+str(sys.version_info.minor))').Trim()
if ($LASTEXITCODE -ne 0 -or $version -ne '3.11') {
    throw 'The local plugin requires Python 3.11.'
}
Push-Location $repo
try {
    & $python -c 'import mcp; import scripts.studio_server'
    if ($LASTEXITCODE -ne 0) {
        throw 'Install MCP: .\.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt'
    }
    Write-Host 'MCP runtime: OK' -ForegroundColor Green
    $env:VIDEONEWS_REPO_PATH = $repo
    [Environment]::SetEnvironmentVariable('VIDEONEWS_REPO_PATH', $repo, 'User')
    Write-Host "VIDEONEWS_REPO_PATH configured: $repo" -ForegroundColor Green
    if (-not $SkipSmokeTest) {
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            # MCP server diagnostics are intentionally written to stderr. In
            # Windows PowerShell, that stream otherwise becomes a terminating
            # NativeCommandError despite a successful Python exit code.
            $ErrorActionPreference = 'Continue'
            & $python -m scripts.desktop_mcp_smoke
            $smokeExitCode = $LASTEXITCODE
            & $python -m scripts.doctor --mode studio
            $doctorExitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        if ($smokeExitCode -ne 0) { throw 'Local plugin launcher smoke test failed.' }
        if ($doctorExitCode -ne 0) { throw 'Studio doctor reported a required failure.' }
    }
} finally {
    Pop-Location
}
Write-Host 'Restart ChatGPT Desktop fully to reload this user environment variable.' -ForegroundColor Cyan
Write-Host 'Install VideoNews AI Studio in Plugins, use Work locally, and call studio_status.' -ForegroundColor Cyan
Write-Host 'This verifies local Python MCP, not the ChatGPT Desktop UI connection.' -ForegroundColor Yellow
