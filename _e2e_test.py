"""
End-to-end pipeline test with Ollama LLM + Azure images + ImageMagick video assembly.
"""
import os
import json
import sys
import time

MAGICK_HOME = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI"
os.environ["MAGICK_HOME"] = MAGICK_HOME
os.environ["IMAGEMAGICK_BINARY"] = os.path.join(MAGICK_HOME, "magick.exe")
from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": os.path.join(MAGICK_HOME, "magick.exe")})

with open("settings.json", "r", encoding="utf-8") as f:
    config = json.load(f)

from scripts.factory import PipelineFactory

output_path = None
start = time.time()

def progress_callback(data: dict):
    global output_path
    cs = data.get("current_stage", {})
    elapsed = time.time() - start
    stage = cs.get("name", "?").ljust(22)
    status = cs.get("status", "?").ljust(12)
    pct = data["total_progress"]
    msg = cs.get("message", "")
    print(f"[{elapsed:6.1f}s] {stage} {status} {pct:5.1f}%  {msg}")

    meta = data.get("stages", {}).get("video_assembly", {}).get("metadata", {})
    if meta.get("output_path"):
        output_path = meta["output_path"]

url = "https://en.wikipedia.org/wiki/Python_(programming_language)"

print(f"=== E2E Test ===")
print(f"URL: {url}")
print(f"Format: short (9:16, ~60s)")
print()

factory = PipelineFactory()
pipeline = factory.create_pipeline_from_config(
    config,
    pipeline_type="short",
    skip_validation=True,
    progress_callback=progress_callback,
)

try:
    upload_result = pipeline.execute({"url": url})
    elapsed = time.time() - start
    print(f"\n=== COMPLETED in {elapsed:.0f}s ===")
    print(f"Upload result: {upload_result}")
    if output_path:
        print(f"Local video: {output_path}")
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Video size: {size_mb:.1f} MB")
except Exception as e:
    elapsed = time.time() - start
    print(f"\n=== FAILED after {elapsed:.0f}s ===", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
