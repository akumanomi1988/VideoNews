@echo off
cd /d "C:\Users\mozot\source\repos\akumanomi1988\VideoNews"
:restart
".venv\Scripts\python.exe" telegram_bot.py
echo %date% %time% - Bot exited with code %errorlevel%. Restarting in 12 seconds... >> logs\bot_restart.log 2>&1
timeout /t 12 /nobreak >nul
goto restart
