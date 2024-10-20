import moviepy.editor as mp
from moviepy.editor import CompositeVideoClip
from colorama import Fore
from moviepy.video.tools.subtitles import SubtitlesClip
from scripts.helpers.media_helper import AudioHelper, Position, Style, SubtitleHelper

class MediaManager:
    """Handles media assembly, including video, audio processing, aspect ratio adjustments, and subtitle generation."""

    def __init__(self, subtitle_file, voiceover_file, output_file, media_videos=None, media_images=None, aspect_ratio="9:16", background_music=""):
        self.output_file = output_file
        self.media_videos = media_videos or []
        self.media_images = media_images or []
        self.aspect_ratio = aspect_ratio
        self.subtitle_file = subtitle_file
        self.voiceover_file = voiceover_file
        self.background_music = background_music

        # Initialize audio and subtitles helpers
        self.audio_helper = AudioHelper()
        self.subtitle_helper = SubtitleHelper()

    def adjust_media(self):
        """Adjusts media clips for the specified aspect ratio."""
        adjusted_clips = []
        
        for video_path in self.media_videos:
            clip = mp.VideoFileClip(video_path)
            adjusted_clips.append(self.adjust_video(clip))

        for image_path in self.media_images:
            clip = mp.ImageClip(image_path)
            adjusted_clips.append(self.adjust_image(clip))

        return adjusted_clips

    def adjust_video(self, clip):
        """Adjusts a video clip for the specified aspect ratio."""
        return clip.resize(newsize=(self.get_width(), self.get_height()))

    def adjust_image(self, clip):
        """Adjusts an image clip for the specified aspect ratio."""
        return clip.resize(newsize=(self.get_width(), self.get_height())).set_duration(2)  # Adjust duration as needed

    def get_width(self):
        """Calculates width based on aspect ratio."""
        ratio = self.aspect_ratio.split(':')
        return 720 * int(ratio[0]) // int(ratio[1])  # Adjust base width as needed

    def get_height(self):
        """Calculates height based on aspect ratio."""
        ratio = self.aspect_ratio.split(':')
        return 720  # Adjust base height as needed

    def add_subtitles(self, video, style=Style.BOLD, position=Position.MIDDLE_CENTER):
        """Add subtitles to the video based on the provided subtitle file."""
        try:
            subtitles = SubtitlesClip(
                self.subtitle_file, 
                lambda txt: self.subtitle_helper.generate_subtitle(txt, video.size, position=position, style=style)
            )
            return CompositeVideoClip([video, subtitles])
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error adding subtitles: {e}")

    def assemble_video(self):
        """Assembles the final video with media, subtitles, voiceover, and background music."""
        try:
            # Adjust media (videos and images)
            adjusted_clips = self.adjust_media()

            if not adjusted_clips:
                raise ValueError(Fore.RED + "❌ No valid media files to process. Ensure video or image files are provided.")

            # Concatenate the adjusted clips into a final video clip
            final_clip = mp.concatenate_videoclips(adjusted_clips, method="compose")

            # Add voiceover and background music
            voiceover_audio = self.audio_helper.get_voiceover_audio(self.voiceover_file)
            final_clip = final_clip.set_audio(voiceover_audio)

            # Add background music if provided
            if self.background_music:
                final_clip = self.audio_helper.add_background_music(final_clip, self.background_music, final_clip.duration)

            # Add subtitles to the final video
            final_clip = self.add_subtitles(final_clip)

            # Write the final video to the specified output file
            final_clip.write_videofile(self.output_file, fps=24, codec='libx264', audio_codec='aac')
            print(Fore.GREEN + f"✅ Video assembled successfully: {self.output_file}")

        except Exception as e:
            print(Fore.RED + f"❌ Error assembling video: {e}")
