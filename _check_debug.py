"""Check DEBUG logs from bot polling for getUpdates."""
import sqlite3

conn = sqlite3.connect('logs/log_2026-05-25.db')
cur = conn.execute(
    "SELECT timestamp, level, message FROM app_logs "
    "WHERE level='DEBUG' AND message LIKE '%getUpdates%' "
    "ORDER BY timestamp DESC LIMIT 10"
)
rows = cur.fetchall()
for ts, lvl, msg in rows:
    print(f'{ts} [{lvl}] {msg[:250]}')
if not rows:
    print('No getUpdates DEBUG logs')
    # Check what DEBUG logs exist
    cur = conn.execute(
        "SELECT message FROM app_logs WHERE level='DEBUG' ORDER BY timestamp DESC LIMIT 5"
    )
    for msg, in cur.fetchall():
        print(f'  DEBUG: {msg[:200]}')
conn.close()
