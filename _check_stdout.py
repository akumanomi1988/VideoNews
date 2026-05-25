"""Check bot_output.log for latest output."""
import time
from pathlib import Path

log = Path('bot_output.log')
if log.exists():
    content = log.read_text(encoding='utf-8', errors='replace')
    # Show last 30 lines
    lines = content.strip().split('\n')
    for line in lines[-30:]:
        print(line[:300])
else:
    print("Log file not found")
