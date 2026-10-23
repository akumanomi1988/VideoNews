"""VideoNews launcher; ImageMagick is optional and never hardcoded to Windows."""
import os
from pathlib import Path

configured = os.getenv("IMAGEMAGICK_BINARY")
if configured and Path(configured).is_file():
    from moviepy.config import change_settings
    change_settings({"IMAGEMAGICK_BINARY": configured})

from bot.main import main

if __name__ == "__main__":
    main()
