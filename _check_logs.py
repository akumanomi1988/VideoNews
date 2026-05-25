"""Quick log analysis - show recent errors and handler activity."""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('logs/log_2026-05-25.db')

# Last 30 mins
cutoff = (datetime.now() - timedelta(minutes=30)).isoformat()

# Errors
cur = conn.execute(
    "SELECT timestamp, logger_name, message FROM app_logs "
    "WHERE level='ERROR' AND timestamp > ? ORDER BY timestamp",
    (cutoff,)
)
errors = cur.fetchall()
if errors:
    print(f"=== ERRORS ({len(errors)}) ===")
    for ts, name, msg in errors:
        print(f"  {ts} [{name.split('.')[-1]}] {msg[:200]}")
else:
    print("No errors")

# Handler activity
cur = conn.execute(
    "SELECT timestamp, logger_name, message FROM app_logs "
    "WHERE level='INFO' AND timestamp > ? AND logger_name NOT LIKE 'bot.main' "
    "ORDER BY timestamp", (cutoff,)
)
handlers = cur.fetchall()
print(f"\n=== HANDLER/INFO logs ({len(handlers)}) ===")
for ts, name, msg in handlers:
    print(f"  {ts} [{name.split('.')[-1]}] {msg[:200]}")

conn.close()
