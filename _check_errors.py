"""Check ERROR and WARNING logs from today."""
import sqlite3

conn = sqlite3.connect('logs/log_2026-05-25.db')
cur = conn.execute("SELECT timestamp, logger_name, level, message FROM app_logs WHERE level IN ('ERROR','WARNING') ORDER BY timestamp DESC LIMIT 40")
rows = cur.fetchall()
for ts, name, lvl, msg in rows:
    short = name.split('.')[-1]
    print(f'{ts} [{lvl}] [{short}] {msg[:250]}')
if not rows:
    print('No ERROR/WARNING logs')
conn.close()
