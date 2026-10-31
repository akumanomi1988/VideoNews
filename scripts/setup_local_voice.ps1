# Install the optional CPU voice audition runtime without altering Studio dependencies.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $repoRoot 'output\voice_lab\runtime'
$python = Join-Path $runtime 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    & py -3.11 -m venv $runtime
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 could not create the voice runtime.' }
}
& $python -m pip install --disable-pip-version-check -r (Join-Path $repoRoot 'requirements.voice.lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Optional voice dependencies could not be installed.' }
& $python (Join-Path $PSScriptRoot 'download_local_voice.py') --output-dir (Join-Path $repoRoot 'output\voice_lab\models')
if ($LASTEXITCODE -ne 0) { throw 'Official voice assets could not be verified.' }
$sample = Join-Path $repoRoot 'output\voice_lab\sample_es.txt'
if (-not (Test-Path -LiteralPath $sample)) {
    Copy-Item -LiteralPath (Join-Path $repoRoot 'examples\voice_audition_es.txt') -Destination $sample
}
Write-Output 'Local CPU voice audition is ready. Production voice and subtitle settings were not changed.'
