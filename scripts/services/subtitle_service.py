from typing import List, Dict, Optional
import logging
from pathlib import Path
import re
from datetime import timedelta
import pysrt
from pydub import AudioSegment
import speech_recognition as sr
from ..utils.retry import retry_with_backoff, is_transient_error

class SubtitleError(Exception):
    """Custom exception for subtitle processing errors"""
    pass

class SubtitleEntry:
    """Represents a single subtitle entry"""
    def __init__(self, text: str, start_time: float, end_time: float):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time

class SubtitleProcessor:
    """Handles subtitle generation and synchronization"""
    
    def __init__(self, audio_file: str, output_dir: str):
        self.logger = logging.getLogger(__name__)
        self.audio_file = Path(audio_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def process_subtitles(
        self,
        text: str,
        max_chars_per_line: int = 42,
        min_duration: float = 1.0,
        max_duration: float = 4.0
    ) -> str:
        """Process text into synchronized subtitles"""
        try:
            # Split text into sentences
            sentences = self._split_into_sentences(text)
            
            # Format sentences into subtitle lines
            subtitle_lines = self._format_subtitle_lines(
                sentences,
                max_chars_per_line
            )
            
            # Get timing from audio analysis
            timings = self._analyze_audio_timing(subtitle_lines)
            
            # Generate subtitle entries
            subtitle_entries = self._create_subtitle_entries(
                subtitle_lines,
                timings,
                min_duration,
                max_duration
            )
            
            # Write SRT file
            output_path = self.output_dir / "subtitles.srt"
            self._write_srt_file(subtitle_entries, output_path)
            
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to process subtitles: {e}")
            raise SubtitleError(f"Subtitle processing failed: {e}")

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences with smart handling of abbreviations"""
        # Common abbreviations that shouldn't split sentences
        abbreviations = r'Mr\.|Mrs\.|Dr\.|Prof\.|Sr\.|Jr\.|vs\.|etc\.'
        
        # Replace periods in abbreviations temporarily
        for abbr in abbreviations.split('|'):
            text = text.replace(abbr, abbr.replace('.', '@'))
        
        # Split into sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        # Restore periods and clean up
        sentences = [s.replace('@', '.') + '.' for s in sentences]
        
        return sentences

    def _format_subtitle_lines(
        self,
        sentences: List[str],
        max_chars_per_line: int
    ) -> List[str]:
        """Format sentences into appropriate subtitle lines"""
        subtitle_lines = []
        
        for sentence in sentences:
            words = sentence.split()
            current_line = []
            current_length = 0
            
            for word in words:
                word_length = len(word) + 1  # +1 for space
                
                if current_length + word_length > max_chars_per_line:
                    if current_line:
                        subtitle_lines.append(' '.join(current_line))
                        current_line = [word]
                        current_length = word_length
                else:
                    current_line.append(word)
                    current_length += word_length
            
            if current_line:
                subtitle_lines.append(' '.join(current_line))
        
        return subtitle_lines

    @retry_with_backoff(
        retries=2,
        backoff_in_seconds=1,
        exceptions=(Exception,),
        should_retry=is_transient_error
    )
    def _analyze_audio_timing(self, subtitle_lines: List[str]) -> List[float]:
        """Analyze audio file to determine subtitle timings"""
        try:
            # Convert audio to WAV for speech recognition
            audio = AudioSegment.from_file(self.audio_file)
            wav_path = self.output_dir / "temp_audio.wav"
            audio.export(wav_path, format="wav")
            
            recognizer = sr.Recognizer()
            timings = []
            
            with sr.AudioFile(str(wav_path)) as source:
                audio = recognizer.record(source)
                
                # Use speech recognition to get word timings
                result = recognizer.recognize_google(
                    audio,
                    show_all=True
                )
                
                if result and 'alternative' in result:
                    words = result['alternative'][0].get('words', [])
                    timings = self._align_timings(words, subtitle_lines)
                else:
                    # Fallback to duration-based timing
                    total_duration = len(audio) / 1000  # Convert to seconds
                    avg_duration = total_duration / len(subtitle_lines)
                    timings = [i * avg_duration for i in range(len(subtitle_lines) + 1)]
            
            # Cleanup
            wav_path.unlink(missing_ok=True)
            return timings
            
        except Exception as e:
            self.logger.error(f"Failed to analyze audio timing: {e}")
            raise

    def _align_timings(
        self,
        word_timings: List[Dict],
        subtitle_lines: List[str]
    ) -> List[float]:
        """Align speech recognition timings with subtitle lines"""
        timings = [0.0]  # Start time
        current_time = 0.0
        
        for line in subtitle_lines:
            words = set(word.lower() for word in line.split())
            
            # Find matching words in timing data
            matching_times = []
            for word_data in word_timings:
                if word_data['word'].lower() in words:
                    matching_times.append(
                        float(word_data.get('start_time', 0))
                    )
            
            if matching_times:
                # Use average of matching word timings
                current_time = sum(matching_times) / len(matching_times)
            else:
                # Fallback: increment by estimated duration
                current_time += len(line) * 0.06  # ~60ms per character
            
            timings.append(current_time)
        
        return timings

    def _create_subtitle_entries(
        self,
        lines: List[str],
        timings: List[float],
        min_duration: float,
        max_duration: float
    ) -> List[SubtitleEntry]:
        """Create subtitle entries with appropriate timing constraints"""
        entries = []
        
        for i, line in enumerate(lines):
            start_time = timings[i]
            end_time = timings[i + 1]
            
            # Apply duration constraints
            duration = end_time - start_time
            if duration < min_duration:
                end_time = start_time + min_duration
            elif duration > max_duration:
                end_time = start_time + max_duration
            
            entries.append(SubtitleEntry(line, start_time, end_time))
        
        return entries

    def _write_srt_file(self, entries: List[SubtitleEntry], output_path: Path) -> None:
        """Write subtitle entries to SRT file"""
        try:
            subs = pysrt.SubRipFile()
            
            for i, entry in enumerate(entries, 1):
                start = self._seconds_to_timestamp(entry.start_time)
                end = self._seconds_to_timestamp(entry.end_time)
                
                sub = pysrt.SubRipItem(
                    index=i,
                    start=start,
                    end=end,
                    text=entry.text
                )
                subs.append(sub)
            
            subs.save(str(output_path), encoding='utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to write SRT file: {e}")
            raise

    def _seconds_to_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format"""
        td = timedelta(seconds=seconds)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        seconds = td.seconds % 60
        milliseconds = round(td.microseconds / 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"