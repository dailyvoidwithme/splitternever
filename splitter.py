import os
import subprocess
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from tqdm import tqdm
import json
from datetime import timedelta

class VideoSplitter:
    def __init__(self):
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.flv']
    
    def split_video(
        self,
        video_path: str,
        clip_duration: Tuple[int, int] = (30, 60),
        output_dir: str = "output",
        subtitle_path: Optional[str] = None,
        caption_style: str = "standard"
    ) -> List[Dict]:
        """
        Split video into clips of specified duration range
        """
        # Validate inputs
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Load video
        video = VideoFileClip(video_path)
        total_duration = video.duration
        
        # Calculate clip boundaries
        clip_boundaries = self._calculate_clip_boundaries(
            video_path=video_path,
            min_duration=clip_duration[0],
            max_duration=clip_duration[1],
            total_duration=total_duration
        )
        
        # Process each clip
        clips_info = []
        for i, (start, end) in enumerate(tqdm(clip_boundaries, desc="Processing clips")):
            try:
                clip_info = self._create_clip(
                    video=video,
                    start=start,
                    end=end,
                    clip_number=i+1,
                    output_dir=output_dir,
                    subtitle_path=subtitle_path,
                    caption_style=caption_style
                )
                clips_info.append(clip_info)
                
            except Exception as e:
                print(f"Error processing clip {i+1}: {str(e)}")
                continue
        
        # Close video
        video.close()
        
        return clips_info
    
    def _calculate_clip_boundaries(
        self,
        video_path: str,
        min_duration: int,
        max_duration: int,
        total_duration: float
    ) -> List[Tuple[float, float]]:
        """
        Calculate optimal clip boundaries based on content
        """
        boundaries = []
        
        # Strategy 1: Try to split at scene changes
        scene_boundaries = self._detect_scene_changes(video_path)
        
        if scene_boundaries:
            boundaries = self._merge_scenes_to_duration(
                scene_boundaries, min_duration, max_duration, total_duration
            )
        else:
            # Strategy 2: Split at silence boundaries
            silence_boundaries = self._detect_silence_boundaries(
                video_path, min_duration, max_duration
            )
            
            if silence_boundaries:
                boundaries = silence_boundaries
            else:
                # Strategy 3: Equal split with overlap prevention
                boundaries = self._calculate_equal_boundaries(
                    total_duration, min_duration, max_duration
                )
        
        return boundaries
    
    def _detect_scene_changes(self, video_path: str) -> List[float]:
        """
        Detect scene changes in video using FFmpeg
        """
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', 'select=gt(scene\,0.3),showinfo',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                stderr=subprocess.STDOUT
            )
            
            # Parse output for scene change timestamps
            boundaries = []
            for line in result.stdout.split('\n'):
                if 'pts_time:' in line:
                    try:
                        time_str = line.split('pts_time:')[1].split()[0]
                        boundaries.append(float(time_str))
                    except (IndexError, ValueError):
                        continue
            
            return boundaries
            
        except Exception:
            return []
    
    def _detect_silence_boundaries(
        self,
        video_path: str,
        min_duration: int,
        max_duration: int
    ) -> List[Tuple[float, float]]:
        """
        Detect silence boundaries for natural splitting points
        """
        try:
            # Extract audio
            audio = AudioSegment.from_file(video_path)
            
            # Detect non-silent chunks
            non_silent_chunks = detect_nonsilent(
                audio,
                min_silence_len=1000,
                silence_thresh=-40
            )
            
            boundaries = []
            current_start = 0
            
            for chunk_start, chunk_end in non_silent_chunks:
                chunk_duration = (chunk_end - chunk_start) / 1000  # Convert to seconds
                
                if chunk_duration >= min_duration:
                    if chunk_duration <= max_duration:
                        boundaries.append((current_start, chunk_end / 1000))
                        current_start = chunk_end / 1000
                    else:
                        # Split long chunk
                        num_splits = int(np.ceil(chunk_duration / max_duration))
                        split_duration = chunk_duration / num_splits
                        
                        for i in range(num_splits):
                            start = current_start + (i * split_duration)
                            end = start + split_duration
                            boundaries.append((start, end))
                        
                        current_start = end
            
            return boundaries
            
        except Exception:
            return []
    
    def _calculate_equal_boundaries(
        self,
        total_duration: float,
        min_duration: int,
        max_duration: int
    ) -> List[Tuple[float, float]]:
        """
        Calculate equal boundaries when no natural splits found
        """
        boundaries = []
        start = 0
        
        while start < total_duration:
            end = min(start + max_duration, total_duration)
            
            # Ensure minimum duration
            if (end - start) < min_duration and len(boundaries) > 0:
                # Merge with previous clip
                prev_start, prev_end = boundaries.pop()
                boundaries.append((prev_start, end))
            else:
                boundaries.append((start, end))
            
            start = end
        
        return boundaries
    
    def _create_clip(
        self,
        video: VideoFileClip,
        start: float,
        end: float,
        clip_number: int,
        output_dir: str,
        subtitle_path: Optional[str],
        caption_style: str
    ) -> Dict:
        """
        Create individual clip with optional captions
        """
        # Extract subclip
        clip = video.subclip(start, end)
        
        # Generate output filename
        base_name = Path(video.filename).stem
        output_filename = f"{base_name}_clip_{clip_number:03d}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        # Add captions if subtitles available
        if subtitle_path and os.path.exists(subtitle_path):
            clip = self._add_captions_to_clip(
                clip=clip,
                subtitle_path=subtitle_path,
                start_time=start,
                caption_style=caption_style
            )
        
        # Write clip
        clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            threads=4,
            preset='medium',
            ffmpeg_params=['-crf', '23']  # High quality
        )
        
        # Get clip info
        clip_info = {
            'name': output_filename,
            'path': output_path,
            'duration': round(end - start, 2),
            'start_time': round(start, 2),
            'end_time': round(end, 2),
            'size_mb': os.path.getsize(output_path) / (1024 * 1024),
            'resolution': f"{clip.size[0]}x{clip.size[1]}"
        }
        
        # Close clip
        clip.close()
        
        return clip_info
    
    def _add_captions_to_clip(
        self,
        clip: VideoFileClip,
        subtitle_path: str,
        start_time: float,
        caption_style: str
    ) -> CompositeVideoClip:
        """
        Add captions/subtitles to video clip
        """
        # Parse SRT file
        subtitles = self._parse_srt_file(subtitle_path)
        
        # Filter subtitles for this clip
        clip_subtitles = []
        for sub in subtitles:
            if (sub['end'] > start_time and 
                sub['start'] < (start_time + clip.duration)):
                # Adjust timing for clip
                adj_sub = {
                    'text': sub['text'],
                    'start': max(0, sub['start'] - start_time),
                    'end': min(clip.duration, sub['end'] - start_time)
                }
                clip_subtitles.append(adj_sub)
        
        # Create text clips
        text_clips = []
        for sub in clip_subtitles:
            duration = sub['end'] - sub['start']
            
            # Create text clip with style
            txt_clip = TextClip(
                sub['text'],
                fontsize=self._get_font_size(caption_style),
                color=self._get_text_color(caption_style),
                font=self._get_font(caption_style),
                stroke_color=self._get_stroke_color(caption_style),
                stroke_width=self._get_stroke_width(caption_style),
                size=(clip.w * 0.9, None),
                method='caption'
            )
            
            # Position at bottom center
            txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(duration).set_start(sub['start'])
            text_clips.append(txt_clip)
        
        # Combine video with text clips
        if text_clips:
            return CompositeVideoClip([clip] + text_clips)
        return clip
    
    def _parse_srt_file(self, srt_path: str) -> List[Dict]:
        """
        Parse SRT subtitle file
        """
        subtitles = []
        
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            blocks = content.strip().split('\n\n')
            
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    # Parse time
                    time_line = lines[1]
                    start_str, end_str = time_line.split(' --> ')
                    
                    # Convert time to seconds
                    start_seconds = self._time_to_seconds(start_str)
                    end_seconds = self._time_to_seconds(end_str)
                    
                    # Get text
                    text = ' '.join(lines[2:])
                    
                    subtitles.append({
                        'start': start_seconds,
                        'end': end_seconds,
                        'text': text
                    })
        
        except Exception as e:
            print(f"Error parsing SRT file: {str(e)}")
        
        return subtitles
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert SRT time format to seconds"""
        try:
            h, m, s = time_str.split(':')
            s, ms = s.split(',')
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        except:
            return 0.0
    
    def _get_font_size(self, style: str) -> int:
        sizes = {
            'standard': 28,
            'minimal': 24,
            'bold': 32,
            'outline': 30
        }
        return sizes.get(style, 28)
    
    def _get_text_color(self, style: str) -> str:
        colors = {
            'standard': 'white',
            'minimal': 'lightgray',
            'bold': 'white',
            'outline': 'white'
        }
        return colors.get(style, 'white')
    
    def _get_stroke_color(self, style: str) -> str:
        colors = {
            'standard': 'black',
            'minimal': None,
            'bold': 'black',
            'outline': 'black'
        }
        return colors.get(style, 'black')
    
    def _get_stroke_width(self, style: str) -> int:
        widths = {
            'standard': 1,
            'minimal': 0,
            'bold': 2,
            'outline': 3
        }
        return widths.get(style, 1)
    
    def _get_font(self, style: str) -> str:
        fonts = {
            'standard': 'Arial',
            'minimal': 'Helvetica',
            'bold': 'Arial-Bold',
            'outline': 'Arial'
        }
        return fonts.get(style, 'Arial')
