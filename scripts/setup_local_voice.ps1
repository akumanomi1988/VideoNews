# Install CPU production speech and alignment without altering Studio dependencies.
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
& $python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8', cpu_threads=4, download_root=r'$repoRoot\output\voice_lab\models\alignment')"
if ($LASTEXITCODE -ne 0) { throw 'CPU forced-alignment model could not be installed.' }
Write-Output 'Kokoro CPU speech and acoustic forced alignment are ready. Edge remains an explicit alternative.'
