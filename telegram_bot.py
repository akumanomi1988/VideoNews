"""Compatibility launcher for the VideoNews bot."""

import os

MAGICK_HOME = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI"
os.environ.setdefault("MAGICK_HOME", MAGICK_HOME)
os.environ.setdefault("IMAGEMAGICK_BINARY", os.path.join(MAGICK_HOME, "magick.exe"))

from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": os.path.join(MAGICK_HOME, "magick.exe")})

from bot.main import main

if __name__ == "__main__":
    main()
