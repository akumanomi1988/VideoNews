"""Check bot status via Telegram API."""
import json, urllib.request

with open('settings.json', encoding='utf-8') as f:
    token = json.load(f)['telegram']['bot_token']

url = f'https://api.telegram.org/bot{token}/getMe'
resp = urllib.request.urlopen(url)
data = json.loads(resp.read())
print('Bot username:', data['result']['username'])
print('Can connect:', data['ok'])

url = f'https://api.telegram.org/bot{token}/getUpdates?timeout=2'
resp = urllib.request.urlopen(url)
updates = json.loads(resp.read())
print(f'Pending updates: {len(updates.get("result", []))}')
