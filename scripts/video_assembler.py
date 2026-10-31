import os
import re
import json
import math
import time
import uuid
import textwrap
import subprocess
import logging
import gc
import contextlib
import shutil
from typing import List, Optional, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from colorama import init, Fore

import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import (
    TextClip, CompositeVideoClip, ImageClip, VideoFileClip
)
from moviepy.video.fx import resize, crop

from scripts.helpers.media_helper import ImageHelper, Position, Style, SubtitleHelper
from .interfaces import VideoAssembler as VideoAssemblerInterface, VideoMetadata
from .utils.app_logger import trace
# Subtitles are rendered directly by FFmpeg; no external subtitler import required.

# Initialize colorama for colored terminal output
init(autoreset=True)

# Constants for configuration and supported formats
SUPPORTED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
DEFAULT_FPS = 30
DEFAULT_BG_COLOR = (255, 255, 255)

class VideoAssemblerError(Exception):
    """Custom exception for video assembly errors"""
    pass

class ResourceManager:
    """Manages video processing resources and cleanup"""
    
    @trace()
    def __init__(self):
        self.clips = []
        self.audio_clips = []
        self.logger = logging.getLogger(__name__)

    def register_clip(self, clip):
        """Register a clip for cleanup"""
        self.clips.append(clip)
        return clip

    def register_audio(self, audio):
        """Register an audio clip for cleanup"""
        self.audio_clips.append(audio)
        return audio

    def cleanup(self):
        """Clean up all registered resources"""
        for clip in self.clips:
            try:
                clip.close()
            except Exception as e:
                self.logger.warning(f"Error closing clip: {e}")

        for audio in self.audio_clips:
            try:
                audio.close()
            except Exception as e:
                self.logger.warning(f"Error closing audio: {e}")

        self.clips.clear()
        self.audio_clips.clear()
        gc.collect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

class VideoAssembler(VideoAssemblerInterface):
    """Handles video assembly with memory management"""

    _font_cache: Dict[str, ImageFont.FreeTypeFont] = {}

    @trace()
    def __init__(
        self,
        subtitle_file: Optional[str] = None,
        voiceover_file: Optional[str] = None,
        output_file: Optional[str] = None,
        media_images: Optional[List[str]] = None,
        media_videos: Optional[List[str]] = None,
        aspect_ratio: str = "16:9",
        background_music: Optional[str] = None,
        image_durations: Optional[List[float]] = None,
        scene_motions: Optional[List[str]] = None,
        scene_transitions: Optional[List[str]] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.subtitle_file = subtitle_file
        self.voiceover_file = voiceover_file
        self.output_file = output_file
        self.media_images = media_images or []
        self.media_videos = media_videos or []
        self.aspect_ratio = aspect_ratio
        self.background_music = background_music
        self.image_durations = image_durations
        self.scene_motions = scene_motions or []
        self.scene_transitions = scene_transitions or []
        if any(value not in {"slow_push_in", "slow_pull_out", "subtle_pan_left", "subtle_pan_right", "static"}
               for value in self.scene_motions):
            raise ValueError("Unsupported scene camera movement")
        if any(value not in {"crossfade", "dissolve", "fade"} for value in self.scene_transitions):
            raise ValueError("Unsupported scene transition")
        self._check_dependencies()

    @staticmethod
    def _check_dependencies():
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                Fore.RED + "❌ ffmpeg not found in PATH. "
                "Install ffmpeg (https://ffmpeg.org/download.html) and ensure it's in your system PATH."
            )

    @trace()
    def get_target_dimensions(self) -> Tuple[int, int]:
        """Render 360p / 720p / 1080p while preserving platform aspect ratio."""
        preset = os.getenv("VIDEO_RENDER_RESOLUTION", "1080p").lower()
        dimensions = {
            "360p": (640, 360),
            "720p": (1280, 720),
            "1080p": (1920, 1080),
        }
        if preset not in dimensions:
            raise ValueError("VIDEO_RENDER_RESOLUTION must be 360p, 720p or 1080p")
        w, h = dimensions[preset]
        if self.aspect_ratio == "16:9":
            return w, h
        if self.aspect_ratio == "9:16":
            return h, w
        raise ValueError("Invalid aspect ratio; expected 9:16 or 16:9")

    @trace()
    def adjust_aspect_ratio(self, clip: VideoFileClip) -> VideoFileClip:
        """
        Resize and crop the video/image clip to match the target aspect ratio.
        """
        target_w, target_h = self.get_target_dimensions()
        clip_aspect_ratio = clip.w / clip.h
        target_aspect_ratio = target_w / target_h

        if clip_aspect_ratio > target_aspect_ratio:
            resized_clip = resize.resize(clip, height=target_h)
        else:
            resized_clip = resize.resize(clip, width=target_w)

        cropped_clip = crop.crop(
            resized_clip,
            width=target_w,
            height=target_h,
            x_center=resized_clip.w // 2,
            y_center=resized_clip.h // 2
        )
        return cropped_clip

    def process_video_files(self) -> List[VideoFileClip]:
        """
        Process and adjust video files to match the aspect ratio.
        """
        adjusted_clips = []
        for media_file in self.media_videos:
            try:
                print(Fore.CYAN + f"Processing video: {media_file}")
                video_clip = VideoFileClip(media_file)
                adjusted_clips.append(self.adjust_aspect_ratio(video_clip))
            except Exception as e:
                print(Fore.RED + f"Error processing video {media_file}: {e}")
        return adjusted_clips

    def process_image_files(self, audio_duration: float) -> List[VideoFileClip]:
        """
        Process and convert images to video clips with zoom effect, matching the aspect ratio.
        Uses moviepy ImageClip directly (avoids slow AkumaEngine per-image rendering).
        """
        adjusted_clips = []
        num_images = len(self.media_images)
        if num_images == 0:
            return adjusted_clips

        duration_per_image = audio_duration / num_images

        for image_file in self.media_images:
            if not self._is_valid_image_file(image_file):
                continue
            try:
                clip = self._create_zoom_clip(image_file, duration_per_image)
                adjusted_clips.append(self.adjust_aspect_ratio(clip))
            except Exception as e:
                print(Fore.RED + f"Error processing image {image_file}: {e}")
        return adjusted_clips

    def _create_zoom_clip(self, image_file: str, duration: float) -> ImageClip:
        """Create an ImageClip with a subtle Ken Burns zoom-in effect."""
        clip = ImageClip(image_file).set_duration(duration)
        clip = clip.resize(lambda t: 1 + 0.15 * (t / duration))
        return clip

    def _is_valid_image_file(self, image_file: str) -> bool:
        """
        Check if the image file exists and has a supported format.
        """
        if not os.path.isfile(image_file):
            print(Fore.YELLOW + f"File not found: {image_file}. Skipping.")
            return False
        if not image_file.lower().endswith(SUPPORTED_IMAGE_FORMATS):
            print(Fore.YELLOW + f"Unsupported image format: {image_file}. Skipping.")
            return False
        return True

    def adjust_media(self) -> List[VideoFileClip]:
        """
        Process and adjust all media files (videos and images) to match the aspect ratio.
        """
        if not self.voiceover_file:
            raise ValueError(Fore.RED + "❌ Voiceover audio file is missing.")
        audio_duration = mp.AudioFileClip(self.voiceover_file).duration
        video_clips = self.process_video_files()
        image_clips = self.process_image_files(audio_duration)
        return video_clips + image_clips

    def _ffprobe_duration(self, file_path: str) -> float:
        """Get media duration via ffprobe (fast, no memory load)."""
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        info = json.loads(result.stdout)
        return float(info['format']['duration'])

    @staticmethod
    def _has_audible_audio(file_path: str) -> bool:
        """Detect silent fixtures before applying EBU loudness normalization."""
        result = subprocess.run(
            ['ffmpeg', '-hide_banner', '-i', file_path, '-af', 'volumedetect',
             '-f', 'null', os.devnull], capture_output=True, text=True, timeout=60,
        )
        match = re.search(r'mean_volume:\s*([^\s]+)\s+dB', result.stderr)
        if not match:
            return False
        try:
            return math.isfinite(float(match.group(1))) and float(match.group(1)) > -60.0
        except ValueError:
            return False

    @staticmethod
    def _allocate_frame_counts(durations: List[float], total_frames: int) -> List[int]:
        """Allocate every output frame to a scene in proportion to its narration time."""
        if not durations or any(duration <= 0 for duration in durations):
            raise ValueError("Image durations must contain positive values")
        if total_frames < len(durations):
            raise ValueError("Output needs at least one frame per image")
        total_duration = sum(durations)
        exact = [total_frames * duration / total_duration for duration in durations]
        counts = [max(1, int(value)) for value in exact]
        while sum(counts) < total_frames:
            index = max(range(len(counts)), key=lambda i: (exact[i] - int(exact[i]), -i))
            counts[index] += 1
            exact[index] = int(exact[index])
        while sum(counts) > total_frames:
            candidates = [i for i, count in enumerate(counts) if count > 1]
            if not candidates:
                raise ValueError("Cannot allocate frames to the requested scene durations")
            index = max(candidates, key=lambda i: counts[i])
            counts[index] -= 1
        return counts

    def _escape_filter_path(self, path: str) -> str:
        """Escape a path for use in ffmpeg filter graph options."""
        p = Path(os.path.abspath(path)).as_posix()
        p = re.sub(r'^([a-zA-Z]):', lambda m: m.group(1) + '\\:', p)
        return p

    @trace()
    def _assemble_with_ffmpeg(
        self,
        style: Style = Style.DEFAULT,
        position: Position = Position.MIDDLE_CENTER
    ) -> None:
        """
        Assemble video using a single direct ffmpeg subprocess.
        10-50x faster than MoviePy's write_videofile pipe-based rendering.

        Uses filter_complex concat with per-image zoompan for Ken Burns,
        amix for audio mixing, and subtitles filter for SRT burning.
        """
        valid_images = [img for img in self.media_images if os.path.isfile(img)]
        if not valid_images:
            raise ValueError(Fore.RED + "🚨 No valid image files found.")
        if not self.voiceover_file or not os.path.isfile(self.voiceover_file):
            raise ValueError(Fore.RED + "❌ Voiceover audio file is missing.")

        IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif'}
        filtered = []
        for media in valid_images:
            ext = os.path.splitext(media)[1].lower()
            if ext in IMAGE_EXTS:
                filtered.append(media)
            else:
                self.logger.warning(f"Skipping non-image media: {os.path.basename(media)}")
        if not filtered:
            raise ValueError(Fore.RED + "🚨 All media files are non-image (videos?). Use photos only.")
        valid_images = filtered

        target_w, target_h = self.get_target_dimensions()
        fps = 24

        audio_duration = self._ffprobe_duration(self.voiceover_file)
        num_images = len(valid_images)
        if self.scene_motions and len(self.scene_motions) != num_images:
            raise ValueError("scene_motions must have one entry per image")
        if self.scene_transitions and len(self.scene_transitions) != num_images:
            raise ValueError("scene_transitions must have one entry per image")
        transition_seconds = min(0.35, max(0.0, audio_duration / max(2, num_images * 4)))
        overlap_frames = int(round(transition_seconds * fps))
        # Quantize fades to the same frame clock as scene lengths. Otherwise
        # fractional overlap errors accumulate and shorten the final narration.
        transition_seconds = overlap_frames / fps
        target_frames = max(num_images, int(round(audio_duration * fps)))
        if self.image_durations is None:
            frame_counts = self._allocate_frame_counts([1.0] * num_images,
                                                       target_frames + overlap_frames * (num_images - 1))
        else:
            # Preserve spoken boundaries; add overlap locally rather than
            # redistributing it proportionally across all narration segments.
            base_counts = self._allocate_frame_counts(self.image_durations, target_frames)
            frame_counts = [count + (overlap_frames if i < num_images - 1 else 0)
                            for i, count in enumerate(base_counts)]
            if len(frame_counts) != num_images:
                raise ValueError("image_durations must have one entry per valid image")

        # --- Build filter_complex ---
        filters = []
        concat_labels = []

        for i, img in enumerate(valid_images):
            self.logger.info(f"  Image {i+1}/{num_images}: {os.path.basename(img)}")
            fc = frame_counts[i]
            # Deterministic, restrained Ken Burns motion: alternating slow push/pull
            # with centered framing keeps the composition away from title-safe edges.
            motion = self.scene_motions[i] if self.scene_motions else (
                "slow_push_in" if i % 2 == 0 else "slow_pull_out")
            if fc > 1 and motion == "slow_push_in":
                zoom_expr = f"1+0.035*on/({fc}-1)"
                x_expr = "iw/2-(iw/zoom/2)"
            elif fc > 1 and motion == "slow_pull_out":
                zoom_expr = f"1.035-0.035*on/({fc}-1)"
                x_expr = "iw/2-(iw/zoom/2)"
            elif fc > 1 and motion in ("subtle_pan_left", "subtle_pan_right"):
                zoom_expr = "1.025"
                progress = f"on/({fc}-1)" if motion == "subtle_pan_right" else f"1-on/({fc}-1)"
                x_expr = f"(iw-iw/zoom)*({progress})"
            else:
                zoom_expr, x_expr = "1", "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
            filters.append(
                f"[{i}:v]scale=w={target_w}:h={target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h},setsar=1,zoompan=z='{zoom_expr}':"
                f"x='{x_expr}':y='{y_expr}':"
                f"d={fc}:fps={fps}:"
                f"s={target_w}x{target_h},"
                f"scale=w={target_w}:h={target_h}:force_original_aspect_ratio=1,"
                f"pad=w={target_w}:h={target_h}:x=(ow-iw)/2:y=(oh-ih)/2:color=black,"
                f"setsar=1,eq=contrast=1.025:saturation=0.98,setpts=PTS-STARTPTS[s{i}]"
            )
            concat_labels.append(f"[s{i}]")

        n = len(concat_labels)
        if n == 1:
            filters.append(f"{concat_labels[0]}fade=t=in:st=0:d=0.45,fade=t=out:st={max(0.0,audio_duration-0.55):.3f}:d=0.55[vid]")
        else:
            current_duration = frame_counts[0] / fps
            current_label = concat_labels[0]
            for i in range(1, n):
                offset = max(0.0, current_duration - transition_seconds)
                out_label = f"[xf{i}]" if i < n - 1 else "[xfinal]"
                requested = self.scene_transitions[i] if self.scene_transitions else "crossfade"
                transition_name = {"crossfade": "fade", "dissolve": "dissolve", "fade": "fadeblack"}[requested]
                filters.append(f"{current_label}{concat_labels[i]}xfade=transition={transition_name}:duration={transition_seconds:.3f}:offset={offset:.3f}{out_label}")
                current_duration += frame_counts[i] / fps - transition_seconds
                current_label = out_label
            filters.append(f"{current_label}fade=t=in:st=0:d=0.45,fade=t=out:st={max(0.0,audio_duration-0.55):.3f}:d=0.55[vid]")

        # Voiceover audio
        a_main = num_images
        fade_start = max(0.0, audio_duration - 2.0)
        filters.append(
            f"[{a_main}:a]adelay=0,afade=t=out:st={fade_start}:d=2[voice]"
        )
        audio_map = "[voice]"
        a_total = a_main + 1

        # Background music
        if self.background_music and os.path.isfile(self.background_music):
            bg_idx = a_total
            a_total += 1
            filters.append("[voice]asplit=2[voicemix][voicekey]")
            filters.append(
                f"[{bg_idx}:a]volume=0.24,afade=t=in:st=0:d=0.8,"
                f"afade=t=out:st={fade_start}:d=2[bgsource]"
            )
            filters.append("[bgsource][voicekey]sidechaincompress=threshold=0.035:ratio=8:attack=15:release=300[ducked]")
            filters.append("[voicemix][ducked]amix=inputs=2:duration=first:dropout_transition=2[mix]")
            audio_map = "[mix]"

        if self._has_audible_audio(str(self.voiceover_file)):
            filters.append(f"{audio_map}loudnorm=I=-16:TP=-1.5:LRA=11[outa]")
            audio_map = "[outa]"
        else:
            self.logger.warning("Audio is silent or unmeasurable; skipping loudness normalization")

        # --- Subtitles: copy to CWD with simple name (no colons) + quoted force_style (for commas) ---
        has_subtitles = False
        _local_srt = None
        if self.subtitle_file and os.path.isfile(self.subtitle_file):
            srt_size = os.path.getsize(self.subtitle_file)
            self.logger.info(f"SRT: path={self.subtitle_file!r}, size={srt_size}")
            if srt_size == 0:
                self.logger.warning("SRT is empty (0 bytes), skipping subtitles")
            else:
                is_short = self.aspect_ratio == '9:16'
                style_params = SubtitleHelper.get_style_parameters(style)
                font_name = Path(style_params['font_path']).stem
                # SRT has libass's default 384x288 virtual canvas. A large
                # MarginV moves captions toward the TOP on that canvas; use a
                # modest value so vertical captions sit in the lower safe zone.
                font_size = 11 if is_short else 14
                margin_h = 36 if is_short else 54
                # Leave the bottom 15-20% clear of Shorts controls and titles.
                margin_v = 48 if is_short else 28
                align_map = {
                    Position.BOTTOM_CENTER: '2',
                    Position.BOTTOM_LEFT: '1',
                    Position.BOTTOM_RIGHT: '3',
                    Position.MIDDLE_CENTER: '10',
                    Position.MIDDLE_LEFT: '4',
                    Position.MIDDLE_RIGHT: '6',
                    Position.TOP_CENTER: '8',
                    Position.TOP_LEFT: '7',
                    Position.TOP_RIGHT: '9',
                }
                alignment = align_map.get(position, '2')
                # Copy SRT to a simple name in CWD (guarantees no colons, no path issues in filter)
                _local_srt = f"_vid_srt_{uuid.uuid4().hex[:8]}.srt"
                shutil.copy2(self.subtitle_file, _local_srt)
                # Simple basename in filter, force_style quoted for comma protection
                sub_filter = (
                    f"[vid]subtitles={_local_srt}:"
                    f"force_style='FontName={font_name},"
                    f"FontSize={font_size},"
                    f"PrimaryColour=&H00FFFFFF,"
                    f"OutlineColour=&H00000000,"
                    f"Outline=2,Shadow=1,BorderStyle=1,WrapStyle=0,"
                    f"MarginL={margin_h},MarginR={margin_h},MarginV={margin_v},"
                    f"Alignment={alignment}'"
                    f"[outv]"
                )
                self.logger.info(f"Subtitle filter: {sub_filter}")
                filters.append(sub_filter)
                has_subtitles = True

        last_video_label = "[outv]" if has_subtitles else "[vid]"
        self.logger.info(f"Subtitles: {'ON' if has_subtitles else 'OFF'} (map label: {last_video_label})")

        # --- Build command ---
        cmd = ['ffmpeg', '-y']

        for img in valid_images:
            cmd.extend(['-i', img])
        cmd.extend(['-i', str(self.voiceover_file)])

        if self.background_music and os.path.isfile(self.background_music):
            cmd.extend(['-stream_loop', '-1', '-i', str(self.background_music)])

        cmd.extend(['-filter_complex', ';'.join(filters)])
        cmd.extend(['-map', last_video_label, '-map', audio_map])

        cmd.extend([
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', os.getenv('VIDEO_RENDER_PRESET', 'veryfast'),
            '-crf', str(max(16, min(28, int(os.getenv('VIDEO_RENDER_CRF', '20'))))),
            '-c:a', 'aac',
            '-ar', '48000',
            '-ac', '2',
            '-b:a', '192k',
            '-shortest',
            '-movflags', '+faststart',
            str(self.output_file)
        ])

        # --- Execute ---
        self.logger.info(f"FFmpeg assembly: {len(valid_images)} images, "
                         f"{audio_duration:.1f}s audio, "
                         f"{target_w}x{target_h} @ {fps}fps")
        self.logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        debug_log = os.path.join(os.path.dirname(self.output_file or '.'), '_ffmpeg_debug.log')
        try:
            with open(debug_log, 'w', encoding='utf-8') as df:
                df.write(f"Command: {' '.join(cmd)}\n\n")
                df.write(f"Filter complex:\n{';'.join(filters)}\n\n")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            with open(debug_log, 'a', encoding='utf-8') as df:
                df.write(f"\nExit code: {result.returncode}\n")
                df.write(f"\nStderr:\n{result.stderr}\n")
                df.write(f"\nStdout:\n{result.stdout}\n")
        except subprocess.TimeoutExpired:
            raise RuntimeError(Fore.RED + "❌ FFmpeg timed out (>10min).")
        finally:
            if _local_srt and os.path.isfile(_local_srt):
                os.remove(_local_srt)

        if result.returncode != 0:
            self.logger.error(f"FFmpeg failed (exit {result.returncode}). "
                              f"Details in: {debug_log}")
            self.logger.error(f"FFmpeg stderr (last 3K): {result.stderr[-3000:]}")
            raise RuntimeError(
                Fore.RED + f"❌ FFmpeg assembly failed (exit {result.returncode}). "
                f"See {debug_log} for details."
            )
        print(Fore.GREEN + f"Video assembled using ffmpeg: {self.output_file}")

    def split_subtitles(self, subtitle_text: str, width: int = 15) -> str:
        """
        Split long subtitles into shorter lines for better readability.
        """
        return '\n'.join(textwrap.wrap(subtitle_text, width=width))

    @trace()
    def assemble_video(
        self,
        style: Style = Style.DEFAULT,
        position: Position = Position.MIDDLE_CENTER
    ) -> None:
        """
        Assemble and create the final video using direct ffmpeg subprocess.
        """
        self._assemble_with_ffmpeg(style, position)

    def generate_subtitle(
        self,
        txt: str,
        video_size: Tuple[int, int],
        position: Position = Position.MIDDLE_CENTER,
        style: Style = Style.BOLD,
        bg_color: Optional[str] = None,
        text_color: str = 'yellow'
    ) -> CompositeVideoClip:
        """
        Generate a styled subtitle clip for overlaying on the video.
        """
        txt = txt.encode('utf-8').decode('utf-8')
        style_params = SubtitleHelper.get_style_parameters(style)
        font = style_params['font_path']
        fontsize = style_params['fontsize']
        stroke_color = style_params['stroke_color']
        stroke_width = style_params['stroke_width']
        text_color = style_params['text_color']
        bg_color = style_params['bg_color']

        max_text_width = int(video_size[0] * 0.9)
        cache_key = f"{font}_{fontsize}"
        pil_font = VideoAssembler._font_cache.get(cache_key)
        if pil_font is None:
            pil_font = ImageFont.truetype(font, fontsize)
            VideoAssembler._font_cache[cache_key] = pil_font
        temp_img = Image.new('RGB', (1, 1))
        from PIL import ImageDraw
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.multiline_textbbox((0, 0), txt, font=pil_font)
        while (bbox[2] - bbox[0]) > max_text_width and fontsize > 10:
            fontsize = int(fontsize * 0.9)
            cache_key = f"{font}_{fontsize}"
            pil_font = VideoAssembler._font_cache.get(cache_key)
            if pil_font is None:
                pil_font = ImageFont.truetype(font, fontsize)
                VideoAssembler._font_cache[cache_key] = pil_font
            bbox = temp_draw.multiline_textbbox((0, 0), txt, font=pil_font)

        text_clip = TextClip(
            txt,
            font=font,
            fontsize=fontsize,
            color=text_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method='caption',
            size=(max_text_width, None),
            align='center',
        )

        text_width, text_height = text_clip.size
        padding_x, padding_y = 20, 10
        box_width = text_width + 2 * padding_x
        box_height = text_height + 2 * padding_y

        max_height = video_size[1] / 3
        if text_height > max_height:
            scale_factor = max_height / text_height
            text_clip = text_clip.resize(newsize=(int(text_width * scale_factor), int(max_height)))
            box_width = int(text_width * scale_factor) + 2 * padding_x
            box_height = int(max_height) + 2 * padding_y

        image_clip = None
        if bg_color:
            image = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            radius = 25
            fill_color = (0, 0, 0, int(255 * 0.6)) if bg_color == 'blue' else bg_color
            draw.rounded_rectangle(
                [(0, 0), (box_width, box_height)],
                radius=radius,
                fill=fill_color
            )
            image_np = np.array(image)
            image_clip = ImageClip(image_np).set_duration(text_clip.duration)

        final_position = SubtitleHelper.calculate_text_position_video(
            position=position,
            img_width=video_size[0],
            img_height=video_size[1],
            max_text_width=0.8 * video_size[0],
            total_text_height=max_height
        )

        if image_clip:
            subtitle_clip = CompositeVideoClip([image_clip, text_clip]).set_position(final_position)
        else:
            subtitle_clip = text_clip.set_position(final_position)

        return subtitle_clip

    def _check_memory_requirements(self):
        """Check if system has enough memory for video processing"""
        try:
            import psutil
        except ImportError:
            self.logger.warning("psutil not available, skipping memory check")
            return
        memory = psutil.virtual_memory()
        if memory.available < 2 * 1024 * 1024 * 1024:  # 2GB minimum
            self.logger.warning("Low memory available, performance may be affected")

    @trace()
    def assemble(
        self,
        media_paths: List[str],
        audio_path: str,
        subtitles_path: str,
        metadata: VideoMetadata
    ) -> str:
        """Assemble video with resource management"""
        with ResourceManager() as resources:
            try:
                self.logger.info("Starting video assembly...")
                
                # Update instance paths
                self.media_images = media_paths
                self.voiceover_file = audio_path
                self.subtitle_file = subtitles_path
                self.output_file = str(Path(audio_path).parent / f"{metadata.title[:50]}.mp4")

                # Process media files in parallel
                adjusted_clips = self._process_media_files(resources)
                if not adjusted_clips:
                    raise VideoAssemblerError("No valid media files to process")

                # Combine clips
                video = resources.register_clip(self._combine_clips(adjusted_clips))
                if not video:
                    raise VideoAssemblerError("Failed to combine video clips")

                # Add audio with resource management
                video = self._add_audio(video, resources)

                # Add subtitles
                video = self._add_subtitles(video)

                # Write final video
                self._write_video(video)

                return self.output_file

            except Exception as e:
                self.logger.error(f"Video assembly failed: {e}")
                raise VideoAssemblerError(f"Failed to assemble video: {e}")

    def _process_media_files(self, resources: ResourceManager):
        """Process media files with parallel processing"""
        adjusted_clips = []
        
        try:
            # Get audio duration for timing
            audio = resources.register_audio(mp.AudioFileClip(self.voiceover_file))
            audio_duration = audio.duration
            clip_duration = audio_duration / (len(self.media_images) or 1)

            # Process files in parallel
            with ThreadPoolExecutor(max_workers=min(4, len(self.media_images))) as executor:
                future_to_file = {
                    executor.submit(
                        self._create_clip_from_media,
                        media_file,
                        clip_duration,
                        resources
                    ): media_file for media_file in self.media_images
                }
                
                for future in as_completed(future_to_file):
                    media_file = future_to_file[future]
                    try:
                        clip = future.result()
                        if clip:
                            adjusted_clips.append(clip)
                    except Exception as e:
                        self.logger.warning(f"Failed to process {media_file}: {e}")

            return adjusted_clips
        except Exception as e:
            self.logger.error(f"Failed to process media files: {e}")
            raise

    def _create_clip_from_media(self, media_file: str, duration: float, resources: ResourceManager):
        """Create and adjust a clip from media file"""
        try:
            if media_file.lower().endswith(('.mp4', '.avi', '.mov')):
                clip = resources.register_clip(VideoFileClip(media_file))
            else:
                clip = resources.register_clip(ImageClip(media_file).set_duration(duration))

            return self._adjust_aspect_ratio(clip)
        except Exception as e:
            self.logger.error(f"Failed to create clip from {media_file}: {e}")
            return None

    def _adjust_aspect_ratio(self, clip):
        """Adjust clip to target aspect ratio"""
        try:
            target_w, target_h = self._get_dimensions()
            clip_ratio = clip.w / clip.h
            target_ratio = target_w / target_h

            if clip_ratio > target_ratio:
                clip = clip.resize(height=target_h)
            else:
                clip = clip.resize(width=target_w)

            # Crop to exact dimensions
            x_center = clip.w // 2
            y_center = clip.h // 2
            return clip.crop(
                x_center=x_center,
                y_center=y_center,
                width=target_w,
                height=target_h
            )
        except Exception as e:
            self.logger.error(f"Failed to adjust aspect ratio: {e}")
            raise

    def _get_dimensions(self) -> tuple:
        """Get target dimensions based on aspect ratio"""
        if self.aspect_ratio == "16:9":
            return 1920, 1080
        elif self.aspect_ratio == "9:16":
            return 1080, 1920
        else:
            return 1920, 1080  # Default to 16:9

    def _combine_clips(self, clips: List[mp.VideoClip]) -> mp.VideoClip:
        """Combine clips into single video"""
        try:
            return mp.concatenate_videoclips(clips, method="compose")
        except Exception as e:
            self.logger.error(f"Failed to combine clips: {e}")
            raise

    def _add_audio(self, video: mp.VideoClip, resources: ResourceManager) -> mp.VideoClip:
        """Add audio to video"""
        try:
            audio = mp.AudioFileClip(self.voiceover_file)
            
            if self.background_music:
                bg_music = mp.AudioFileClip(self.background_music)
                bg_music = bg_music.volumex(0.1)  # Lower background volume
                audio = mp.CompositeAudioClip([audio, bg_music])

            return video.set_audio(audio)
        except Exception as e:
            self.logger.error(f"Failed to add audio: {e}")
            raise

    def _add_subtitles(self, video: mp.VideoClip) -> mp.VideoClip:
        """Add subtitles to video"""
        if not self.subtitle_file:
            return video

        try:
            position = Position.BOTTOM_CENTER if self.aspect_ratio == "16:9" else Position.MIDDLE_CENTER
            style = Style.FORMAL if self.aspect_ratio == "16:9" else Style.DEFAULT
            
            subtitles = SubtitlesClip(
                self.subtitle_file,
                lambda txt: self.generate_subtitle(
                    txt,
                    video.size,
                    position=position,
                    style=style
                )
            )
            
            return CompositeVideoClip([video, subtitles])
        except Exception as e:
            self.logger.error(f"Failed to add subtitles: {e}")
            raise

    def _write_video(self, video: mp.VideoClip) -> None:
        """Write final video file with optimized encoding"""
        try:
            video.write_videofile(
                self.output_file,
                codec='libx264',
                audio_codec='aac',
                fps=24,
                threads=cpu_count(),
                preset='ultrafast',
                bitrate='4M',
                write_logfile=False
            )
            self.logger.info(f"Video saved to: {self.output_file}")
        except Exception as e:
            self.logger.error(f"Failed to write video: {e}")
            raise

