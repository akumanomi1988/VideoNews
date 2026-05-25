"""Debug stdout encoding."""
import sys, os

print(f"PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', 'NOT SET')}")
print(f"stdout encoding: {sys.stdout.encoding}")
print(f"stdout type: {type(sys.stdout).__name__}")

import colorama
colorama.init(autoreset=True)

print(f"after colorama - stdout type: {type(sys.stdout).__name__}")
print(f"after colorama - encoding: {sys.stdout.encoding}")

# Try to get underlying stream
try:
    underlying = sys.stdout if not hasattr(sys.stdout, 'wrapped') else sys.stdout.wrapped
    while hasattr(underlying, 'wrapped'):
        underlying = underlying.wrapped
    print(f"underlying stream: {type(underlying).__name__}")
    print(f"underlying encoding: {getattr(underlying, 'encoding', 'N/A')}")
except:
    pass

# Test emoji
print("\u2705 test emoji")
print("\u274c test x mark")
print("All OK")
