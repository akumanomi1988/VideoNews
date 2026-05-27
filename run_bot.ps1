$BotDir = "C:\Users\mozot\source\repos\akumanomi1988\VideoNews"
$VenvPython = Join-Path $BotDir ".venv\Scripts\python.exe"
$BotScript = Join-Path $BotDir "telegram_bot.py"
$LogFile = Join-Path $BotDir "logs\bot_restart.log"

Set-Location -LiteralPath $BotDir

while ($true) {
    $date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    try {
        & $VenvPython $BotScript 2>&1
        $exitCode = $LASTEXITCODE
        "$date - Bot exited with code $exitCode. Restarting in 3 seconds..." | Out-File -FilePath $LogFile -Append
    } catch {
        "$date - Bot crashed: $_ . Restarting in 3 seconds..." | Out-File -FilePath $LogFile -Append
    }
    Start-Sleep -Seconds 3
}
