
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import TextClip, CompositeVideoClip, ImageClip
import textwrap
from colorama import init, Fore
from PIL import Image, ImageDraw
import numpy as np
from enum import Enum

# Initialize colorama
init(autoreset=True)
class Position(Enum):
    TOP = 'top'
    MIDDLE = 'middle'
    BOTTOM = 'bottom'

class Style(Enum):
    DEFAULT = 'default'
    BOLD = 'bold'
    MINIMAL = 'minimal'
class SubtitlesManager:
    """Handles subtitles management, including adding subtitles to videos."""

    def __init__(self, subtitle_file):
        self.subtitle_file = subtitle_file

    def split_subtitles(self, subtitle_text):
        """Split long subtitles into shorter lines for better readability."""
        return '\n'.join(textwrap.wrap(subtitle_text, width=15))

    def generate_subtitle(self, txt, video_size, 
                          position=Position.MIDDLE,
                          style=Style.BOLD,
                          bg_color=None,
                          text_color='yellow'):
        """
        Generate subtitles with customizable styles and positioning.
        """
        txt = txt.encode('utf-8').decode('utf-8')

        if style == Style.BOLD:
            font = 'Impact'
            fontsize = 150
            stroke_color = 'black'
            stroke_width = 5
        elif style == Style.MINIMAL:
            font = 'Arial'
            fontsize = 100
            stroke_color = None
            stroke_width = 0
            bg_color = None
        else:
            font = 'Helvetica'
            fontsize = 120
            stroke_color = 'black'
            stroke_width = 3

        text_clip = TextClip(
            txt,
            font=font,
            fontsize=fontsize,
            color=text_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method='caption',
            size=(video_size[0] - 100, None),
            align='center'
        )

        text_width, text_height = text_clip.size
        padding_x = 20
        padding_y = 10
        box_width = text_width + 2 * padding_x
        box_height = text_height + 2 * padding_y

        max_height = video_size[1] / 3
        if text_height > max_height:
            scale_factor = max_height / text_height
            text_clip = text_clip.resize(newsize=(int(text_width * scale_factor), int(max_height)))

        if bg_color:
            image = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            radius = 25
            draw.rounded_rectangle(
                [(0, 0), (box_width, box_height)],
                radius=radius,
                fill=(0, 0, 0, int(255 * 0.6)) if bg_color == 'blue' else bg_color
            )
            image_np = np.array(image)
            image_clip = ImageClip(image_np).set_duration(text_clip.duration)
        else:
            image_clip = None

        if position == Position.TOP:
            final_position = ('center', 0.1 * video_size[1])
        elif position == Position.MIDDLE:
            final_position = ('center', 'center')
        else:
            final_position = ('center', 0.8 * video_size[1])

        if image_clip:
            subtitle_clip = CompositeVideoClip([image_clip, text_clip]).set_position(final_position)
        else:
            subtitle_clip = text_clip.set_position(final_position)

        return subtitle_clip

    def add_subtitles(self, video):
        """Add subtitles to the video based on the provided subtitle file."""
        try:
            subtitles = SubtitlesClip(self.subtitle_file, lambda txt: self.generate_subtitle(txt, video.size))
            subtitles = subtitles.set_position(('center', 'center'))
            return CompositeVideoClip([video, subtitles])
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error adding subtitles: {e}")
