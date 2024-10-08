import moviepy.editor as mp
from moviepy.editor import ImageClip, VideoFileClip
from moviepy.video.fx import resize, crop

from scripts.MediaManagers.audio_manager import AudioManager

from colorama import init, Fore

from scripts.MediaManagers.subtitle_manager import SubtitlesManager

# Initialize colorama
init(autoreset=True)

class VideoManager:
    """Handles video assembly, including video and audio processing, aspect ratio adjustments, and subtitle generation."""

    def __init__(self, subtitle_file, voiceover_file, output_file, media_videos=None, media_images=None, aspect_ratio="9:16", background_music=""):
        self.output_file = output_file
        self.media_videos = media_videos or []
        self.media_images = media_images or []
        self.aspect_ratio = aspect_ratio

        # Use AudioManager and SubtitlesManager
        self.audio_manager = AudioManager(voiceover_file, background_music)
        self.subtitles_manager = SubtitlesManager(subtitle_file)

    def get_target_dimensions(self):
        """Return target dimensions based on the specified aspect ratio."""
        if self.aspect_ratio == '9:16':
            return 1080, 1920  # Vertical aspect ratio
        elif self.aspect_ratio == '16:9':
            return 1920, 1080  # Horizontal aspect ratio
        else:
            raise ValueError(Fore.RED + "❌ Invalid aspect ratio. Use '9:16' or '16:9'.")

    def adjust_aspect_ratio(self, clip):
        """Resize and crop the video/image clip to match the target aspect ratio."""
        target_w, target_h = self.get_target_dimensions()
        clip_aspect_ratio = clip.w / clip.h
        target_aspect_ratio = target_w / target_h

        if clip_aspect_ratio > target_aspect_ratio:
            resized_clip = resize.resize(clip, height=target_h)
        else:
            resized_clip = resize.resize(clip, width=target_w)

        return crop.crop(resized_clip, width=target_w, height=target_h, 
                         x_center=resized_clip.w // 2, y_center=resized_clip.h // 2)

    def adjust_media(self):
        """Process and adjust media files (videos and images) to match the aspect ratio."""
        adjusted_clips = []

        for media_file in self.media_videos:
            try:
                print(Fore.CYAN + f"📹 Processing video: {media_file}")
                video_clip = VideoFileClip(media_file)
                adjusted_clip = self.adjust_aspect_ratio(video_clip)
                adjusted_clips.append(adjusted_clip)
            except Exception as e:
                print(Fore.RED + f"❌ Error processing video {media_file}: {e}")

        for media_file in self.media_images:
            try:
                print(Fore.CYAN + f"🖼️ Processing image: {media_file}")
                image_clip = ImageClip(media_file, duration=5)
                adjusted_clip = self.adjust_aspect_ratio(image_clip)
                adjusted_clips.append(adjusted_clip)
            except Exception as e:
                print(Fore.RED + f"❌ Error processing image {media_file}: {e}")

        return adjusted_clips

    def assemble_video(self):
        """Assemble the final video with media, subtitles, voiceover, and background music."""
        adjusted_clips = self.adjust_media()
        final_clip = mp.concatenate_videoclips(adjusted_clips, method="compose")

        # Add voiceover and background music
        final_clip = final_clip.set_audio(self.audio_manager.get_voiceover_audio())
        final_clip = self.audio_manager.add_background_music(final_clip, final_clip.duration)

        # Add subtitles
        final_clip = self.subtitles_manager.add_subtitles(final_clip)

        final_clip.write_videofile(self.output_file, fps=24, codec='libx264', audio_codec='aac')
        return final_clip
