# bootstrap.ps1 — VideoNews environment setup
# Run: powershell -ExecutionPolicy Bypass -File bootstrap.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "=== VideoNews Bootstrap ===" -ForegroundColor Cyan
Write-Host "Python: $(python --version)" -ForegroundColor Green

# 1. Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating .venv..." -ForegroundColor Yellow
    python -m venv .venv
}

# 2. Upgrade pip
$pip = Join-Path $ProjectRoot ".venv" "Scripts" "pip"
& $pip install --upgrade pip setuptools wheel

# 3. Install project
Write-Host "Installing project dependencies..." -ForegroundColor Yellow
& $pip install -e ".[dev]"

# 4. Install akumaimageeffect with --no-deps (Pillow conflict workaround)
Write-Host "Installing akumaimageeffect (no-deps)..." -ForegroundColor Yellow
& $pip install akumaimageeffect --no-deps

# 5. Download spaCy Spanish model
Write-Host "Downloading spaCy model..." -ForegroundColor Yellow
$python = Join-Path $ProjectRoot ".venv" "Scripts" "python"
& $python -m spacy download es_core_news_sm

# 6. Verify imports
Write-Host "Verifying core imports..." -ForegroundColor Yellow
& $python -c "from bot.config import get_telegram_token; print('OK - bot.config')"
& $python -c "from scripts.utils.app_logger import setup_logging; print('OK - scripts.utils')"
& $python -c "from scripts.pipeline import VideoProcessingPipeline; print('OK - scripts.pipeline')"
& $python -c "from scripts.factory import PipelineFactory; print('OK - scripts.factory')"
& $python -c "from news_video_processor import NewsVideoProcessor; print('OK - NewsVideoProcessor')"
& $python -c "from scripts.services.video_assembler import VideoAssembler; print('OK - services.video_assembler')"

Write-Host "=== Bootstrap complete ===" -ForegroundColor Green
Write-Host "Run: .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "Then: python telegram_bot.py" -ForegroundColor Cyan
