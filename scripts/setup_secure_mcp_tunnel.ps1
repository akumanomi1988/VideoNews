# Install OpenAI tunnel-client and start a private VideoNews stdio tunnel.
[CmdletBinding()]
param(
    [string]$TunnelId,
    [string]$ProfileName = 'videonews-studio',
    [switch]$InstallOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program returned exit code $LASTEXITCODE"
    }
}

if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'This installer currently supports Windows x64 only.'
}
if ($ProfileName -notmatch '^[A-Za-z0-9_-]{1,48}$') {
    throw 'ProfileName may contain only ASCII letters, digits, underscore and hyphen.'
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Run bootstrap.ps1 first to create the Python 3.11 environment.'
}
& $python -c 'import mcp'
if ($LASTEXITCODE -ne 0) {
    throw 'Install the local MCP runtime with .\.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt.'
}

# Resolve the current official release and verify its exact GitHub asset digest.
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/openai/tunnel-client/releases/latest' `
    -Headers @{ Accept = 'application/vnd.github+json'; 'User-Agent' = 'VideoNews-Studio' }
$assetName = "tunnel-client-$($release.tag_name)-windows-amd64.zip"
$asset = $release.assets | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
if (-not $asset -or $asset.digest -notmatch '^sha256:([0-9a-fA-F]{64})$') {
    throw "The official release did not provide the expected Windows x64 asset and SHA-256 digest ($assetName)."
}

$installRoot = Join-Path $env:LOCALAPPDATA 'VideoNews\tunnel-client'
$installDir = Join-Path $installRoot $release.tag_name
$client = Join-Path $installDir 'tunnel-client.exe'
if (-not (Test-Path -LiteralPath $client)) {
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    $zipPath = Join-Path $env:TEMP ("VideoNewsTunnelSetup-" + [guid]::NewGuid().ToString('N') + '.zip')
    Invoke-Checked -Program 'curl.exe' -Arguments @('--fail', '--location', '--silent', '--show-error',
        $asset.browser_download_url, '--output', $zipPath)
    $actualDigest = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
    $expectedDigest = $Matches[1]
    if ($actualDigest -ine $expectedDigest) {
        throw 'The downloaded tunnel-client archive did not match the official SHA-256 digest.'
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        $names = @($archive.Entries | ForEach-Object { $_.FullName })
        if ($names -contains '../' -or ($names | Where-Object { $_ -match '(^/|(^|/)\.\.(\/|$))' })) {
            throw 'The tunnel-client archive contains an unsafe path.'
        }
        if ($names -notcontains 'tunnel-client.exe' -or $names -notcontains 'cloudflared.exe') {
            throw 'The official Windows release is missing required executables.'
        }
    } finally {
        $archive.Dispose()
    }
    Expand-Archive -LiteralPath $zipPath -DestinationPath $installDir -Force
}

if ($InstallOnly) {
    Write-Output "Installed tunnel-client $($release.tag_name) at $client"
    return
}

if (-not $TunnelId) {
    $TunnelId = Read-Host 'Enter the tunnel ID from OpenAI Platform (not an API key)'
}
if ($TunnelId -notmatch '^tunnel_[A-Za-z0-9_-]{8,100}$') {
    throw 'TunnelId does not have the expected tunnel_ identifier format.'
}

$profileDir = Join-Path $env:LOCALAPPDATA 'VideoNews\tunnel-client\profiles'
$profileFile = Join-Path $profileDir ($ProfileName + '.yaml')
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
if (Test-Path -LiteralPath $profileFile) {
    throw "Profile already exists: $profileFile. Choose another -ProfileName or inspect it before changing it."
}

# Restrict the local profile folder to the current Windows identity. The profile
# contains only a secret reference (env:CONTROL_PLANE_API_KEY), never the key.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $profileDir '/inheritance:r' '/grant:r' ("{0}:(OI)(CI)F" -f $identity) | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict profile directory permissions with icacls.' }

$pythonCommand = $python.Replace('\', '/')
$mcpCommand = $pythonCommand + ' -m scripts.studio_server'
Invoke-Checked -Program $client -Arguments @('init', '--sample', 'sample_mcp_stdio_local',
    '--profile', $ProfileName, '--profile-dir', $profileDir, '--tunnel-id', $TunnelId,
    '--control-plane-api-key-ref', 'env:CONTROL_PLANE_API_KEY', '--mcp-command', $mcpCommand)

$secureKey = Read-Host 'Enter the OpenAI runtime API key with Tunnels Read + Use' -AsSecureString
$keyPointer = [IntPtr]::Zero
$runtimeKey = $null
$previousKey = [Environment]::GetEnvironmentVariable('CONTROL_PLANE_API_KEY', 'Process')
try {
    $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $runtimeKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    $env:CONTROL_PLANE_API_KEY = $runtimeKey
    Invoke-Checked -Program $client -Arguments @('doctor', '--profile', $ProfileName,
        '--profile-dir', $profileDir, '--explain')
    Write-Output "Starting private VideoNews tunnel profile '$ProfileName'. Keep this process running for ChatGPT MCP calls."
    Write-Output 'In ChatGPT, add a custom MCP server using Connection: Tunnel and select this tunnel ID.'
    & $client run --profile $ProfileName --profile-dir $profileDir
    if ($LASTEXITCODE -ne 0) { throw "tunnel-client run returned exit code $LASTEXITCODE" }
} finally {
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    $secureKey.Dispose()
    $runtimeKey = $null
    if ($null -eq $previousKey) {
        Remove-Item Env:\CONTROL_PLANE_API_KEY -ErrorAction SilentlyContinue
    } else {
        $env:CONTROL_PLANE_API_KEY = $previousKey
    }
}
