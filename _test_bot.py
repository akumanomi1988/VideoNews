"""Send a test command to the bot via Telegram API."""
import json, urllib.request

with open('settings.json', encoding='utf-8') as f:
    token = json.load(f)['telegram']['bot_token']

# My chat ID (from previous log: 1956860053)
chat_id = "1956860053"

# Send /start command
url = f'https://api.telegram.org/bot{token}/sendMessage'
data = json.dumps({
    'chat_id': chat_id,
    'text': '/start'
}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print('Sent /start:', result['ok'])

# Check for updates to see bot response
import time
time.sleep(3)
url = f'https://api.telegram.org/bot{token}/getUpdates?timeout=2'
resp = urllib.request.urlopen(url)
updates = json.loads(resp.read())
msgs = updates.get('result', [])
if msgs:
    last = msgs[-1]
    if 'message' in last:
        print('Bot response:', last['message'].get('text', '(non-text)')[:200])
    else:
        print('Last update type:', list(last.keys()))
else:
    print('No updates yet')
