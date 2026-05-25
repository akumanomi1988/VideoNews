"""Check for new handler logs after /help was sent."""
import sqlite3, time

conn = sqlite3.connect('logs/log_2026-05-25.db')
cur = conn.execute("SELECT timestamp, logger_name, message FROM app_logs WHERE level='INFO' AND timestamp > '2026-05-25T08:45:' ORDER BY timestamp")
rows = cur.fetchall()
for ts, name, msg in rows:
    short = name.split('.')[-1]
    print(f'{ts} [{short}] {msg[:200]}')
if not rows:
    print('No new INFO logs after 08:45')
conn.close()
