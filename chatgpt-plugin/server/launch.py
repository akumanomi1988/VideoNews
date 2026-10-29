"""Launch the VideoNews repository MCP server from a local plugin install.

Requires VIDEONEWS_REPO_PATH to point at the cloned repository on Windows.
No logs are emitted to stdout: it is reserved for JSON-RPC.
"""
import os
import sys
from pathlib import Path

repo_var = os.environ.get("VIDEONEWS_REPO_PATH", "")
if not repo_var:
    print("Set VIDEONEWS_REPO_PATH to your Windows VideoNews checkout", file=sys.stderr)
    sys.exit(2)

repo = Path(repo_var).expanduser().resolve()
entrypoint = repo / "scripts" / "studio_server.py"
python = repo / ".venv" / "Scripts" / "python.exe"

if not entrypoint.is_file() or not python.is_file():
    print("Run bootstrap.ps1 and install MCP requirements in VIDEONEWS_REPO_PATH", file=sys.stderr)
    sys.exit(2)

os.chdir(repo)
os.execv(str(python), [str(python), "-m", "scripts.studio_server"])
