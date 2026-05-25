"""Watch bot logs in real-time."""
import time
import os

log_file = os.path.join(os.path.dirname(__file__), "bot_output.log")
last_size = 0

if os.path.exists(log_file):
    last_size = os.path.getsize(log_file)

print(f"Watching: {log_file}")
print("Bot is polling. Check Telegram and send commands.\n")

while True:
    try:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            if size > last_size:
                with open(log_file, "r") as f:
                    f.seek(last_size)
                    for line in f:
                        print(line.rstrip())
                last_size = size
        time.sleep(2)
    except KeyboardInterrupt:
        break
