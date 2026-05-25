"""Minimal bot test - runs polling in a thread, sends test message."""
import threading, time, json, urllib.request, logging, sqlite3
from pathlib import Path

with open('settings.json', encoding='utf-8') as f:
    token = json.load(f)['telegram']['bot_token']
chat_id = "1956860053"

def run_bot():
    import nest_asyncio
    nest_asyncio.apply()
    from telegram.ext import ApplicationBuilder, CommandHandler
    from telegram import Update
    from telegram.ext import ContextTypes
    
    app = ApplicationBuilder().token(token).build()
    
    async def test_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(f"GOT COMMAND: {update.message.text}")
        await update.message.reply_text("got it")
    
    app.add_handler(CommandHandler("test123", test_help))
    
    print("Starting polling...")
    app.run_polling(drop_pending_updates=True)

# Start bot in background thread
t = threading.Thread(target=run_bot, daemon=True)
t.start()
time.sleep(15)  # Wait for initialization

# Send test command via API
data = json.dumps({'chat_id': chat_id, 'text': '/test123'}).encode()
req = urllib.request.Request(
    f'https://api.telegram.org/bot{token}/sendMessage',
    data=data, headers={'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(f'Sent /test123: {result["ok"]}')

# Wait a bit for processing
time.sleep(10)
print("Done")
