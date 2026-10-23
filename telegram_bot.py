"""Cross-platform launcher for the VideoNews Telegram bot."""

import os
import shutil

# MoviePy can use the system-installed ImageMagick; never force a Windows path
# when running in Linux/Docker. A missing executable is handled by the renderer.
magick = os.getenv("IMAGEMAGICK_BINARY") or shutil.which("magick") or shutil.which("convert")
if magick and os.path.isfile(magick):
    os.environ["IMAGEMAGICK_BINARY"] = magick
    from moviepy.config import change_settings
    change_settings({"IMAGEMAGICK_BINARY": magick})

from bot.main import main

if __name__ == "__main__":
    main()
