"""Check SQLite db for handler/help logs."""
import sqlite3, time
from pathlib import Path

today = time.strftime('%Y-%m-%d')
db_path = Path('logs') / f'log_{today}.db'
if not db_path.exists():
    print(f'DB not found: {db_path}')
else:
    conn = sqlite3.connect(str(db_path))
    # Check INFO level logs
    cur = conn.execute(
        "SELECT timestamp, logger_name, level, message FROM app_logs "
        "WHERE level = 'INFO' ORDER BY timestamp DESC LIMIT 30"
    )
    rows = cur.fetchall()
    print(f'=== INFO logs (last 30) ===')
    for ts, name, lvl, msg in rows:
        short_name = name.split('.')[-1] if '.' in name else name
        print(f'{ts} [{short_name}] {msg[:200]}')
    
    if not rows:
        print('No INFO logs found')
    
    # Check all levels count
    cur = conn.execute("SELECT level, COUNT(*) FROM app_logs GROUP BY level")
    print()
    for lvl, cnt in cur.fetchall():
        print(f'  {lvl}: {cnt}')
    
    conn.close()
