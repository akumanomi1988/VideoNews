"""Send /help to bot and check SQLite db for response."""
import json, urllib.request, time, sqlite3
from pathlib import Path

with open('settings.json', encoding='utf-8') as f:
    token = json.load(f)['telegram']['bot_token']

chat_id = "1956860053"

# Send /help via Telegram API
url = f'https://api.telegram.org/bot{token}/sendMessage'
data = json.dumps({'chat_id': chat_id, 'text': '/help'}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(f'Sent /help: {result["ok"]}')

# Wait for bot to process
time.sleep(5)

# Check SQLite db for recent logs
today = time.strftime('%Y-%m-%d')
db_path = Path('logs') / f'log_{today}.db'
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute(
        '''SELECT timestamp, level, message FROM app_logs
           WHERE timestamp > ? ORDER BY timestamp DESC LIMIT 20''',
        (time.strftime('%Y-%m-%d %H:%M:'),)
    )
    rows = cur.fetchall()
    if rows:
        for ts, level, msg in rows:
            print(f'{ts} [{level}] {msg[:150]}')
    else:
        print('No logs found for recent timestamp')
    conn.close()
else:
    print(f'DB not found: {db_path}')
