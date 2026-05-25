"""Direct pipeline test - runs the full short-news pipeline without Telegram."""
import os, sys, json, traceback

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["MAGICK_HOME"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI"
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})

from news_video_processor import NewsVideoProcessor
from colorama import Fore, init
init(autoreset=True)

ARTICLE_TITLE = "The Booing Will Continue Until Commencement Speeches Improve - Gizmodo"
ARTICLE_DESC = "According to Gizmodo, the problem is not the graduates but the commencement speeches that are often long, predictable, and uninspiring."

print(f"{Fore.CYAN}{'='*60}")
print(f"{Fore.CYAN}PIPELINE TEST: short-news format")
print(f"{Fore.CYAN}Title: {ARTICLE_TITLE}")
print(f"{Fore.CYAN}{'='*60}\n")

processor = NewsVideoProcessor()
news_data = {"title": ARTICLE_TITLE, "description": ARTICLE_DESC}

try:
    print(f"{Fore.YELLOW}Starting pipeline...")
    sys.stdout.flush()
    result = processor.process_latest_news_in_short_format(news_data)
    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"{Fore.GREEN}PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"{Fore.GREEN}Result: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
    print(f"{Fore.GREEN}{'='*60}")
except Exception as e:
    print(f"\n{Fore.RED}{'='*60}")
    print(f"{Fore.RED}PIPELINE FAILED!")
    print(f"{Fore.RED}Error: {e}")
    print(f"{Fore.RED}{'='*60}")
    traceback.print_exc()
    sys.exit(1)
