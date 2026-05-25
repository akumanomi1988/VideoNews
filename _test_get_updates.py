"""Get updates from Telegram API to see if bot received messages."""
import json, urllib.request

with open('settings.json', encoding='utf-8') as f:
    token = json.load(f)['telegram']['bot_token']

# Check if we received any messages
url = f'https://api.telegram.org/bot{token}/getUpdates'
req = urllib.request.Request(url)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
print(f'ok: {data["ok"]}')
print(f'updates count: {len(data["result"])}')
for update in data["result"]:
    uid = update.get('update_id')
    msg = update.get('message', update.get('callback_query', {}).get('message', {}))
    text = msg.get('text', 'no text')
    chat = msg.get('chat', {})
    print(f'  update_id={uid} chat_id={chat.get("id")} text="{text}"')
