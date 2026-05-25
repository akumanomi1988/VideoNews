"""Send /help to bot and poll for response."""
import json, urllib.request, time

with open('settings.json', encoding='utf-8') as f:
    token = json.load(f)['telegram']['bot_token']

chat_id = "1956860053"

# Send /help
url = f'https://api.telegram.org/bot{token}/sendMessage'
data = json.dumps({'chat_id': chat_id, 'text': '/help'}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(f'Sent /help: {result["ok"]}')

# Wait for bot to process
time.sleep(3)

# Check bot log instead of getUpdates (to avoid conflict)
try:
    with open('bot_output.log', encoding='utf-8') as f:
        lines = f.readlines()
        # Find recent lines mentioning help or handler
        for line in lines[-30:]:
            if 'help' in line.lower() or 'handler' in line.lower() or 'message' in line.lower():
                print(line.rstrip())
except Exception as e:
    print(f'Log error: {e}')
