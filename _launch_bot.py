"""Launch the Telegram bot as a completely detached process."""
import subprocess
import sys
import os

venv_python = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
bot_script = os.path.join(os.path.dirname(__file__), "telegram_bot.py")
log_file = os.path.join(os.path.dirname(__file__), "bot_output.log")

env = os.environ.copy()
env["MAGICK_HOME"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI"
env["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
env["PYTHONUNBUFFERED"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

with open(log_file, "a") as f:
    f.write(f"\n--- Launching bot at {__import__('datetime').datetime.now()} ---\n")

proc = subprocess.Popen(
    [venv_python, bot_script],
    cwd=os.path.dirname(__file__),
    env=env,
    stdout=open(log_file, "a"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW,
)

print(f"Bot launched with PID: {proc.pid}")
print(f"Log file: {log_file}")
