import os
import re
import shutil
from pathlib import Path
from typing import List, Optional
import hashlib

def validate_url(url: str) -> bool:
    """Validate YouTube URL"""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    
    match = re.match(youtube_regex, url)
    return match is not None

def get_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_duration(seconds: float) -> str:
    """Format seconds to HH:MM:SS"""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def format_file_size(bytes_size: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def create_output_directory(base_dir: str = "output") -> str:
    """Create unique output directory"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(base_dir, f"clips_{timestamp}")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return output_dir

def cleanup_temp_files(temp_dir: str):
    """Clean up temporary files"""
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temp directory: {str(e)}")

def get_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_video_metadata(video_path: str) -> dict:
    """Get video metadata using FFprobe"""
    try:
        import subprocess
        import json
        
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        metadata = json.loads(result.stdout)
        
        video_info = {
            'duration': float(metadata['format']['duration']),
            'size': int(metadata['format']['size']),
            'format': metadata['format']['format_name'],
            'bit_rate': int(metadata['format']['bit_rate'])
        }
        
        # Get video stream info
        for stream in metadata['streams']:
            if stream['codec_type'] == 'video':
                video_info.update({
                    'width': stream['width'],
                    'height': stream['height'],
                    'codec': stream['codec_name'],
                    'fps': eval(stream['avg_frame_rate'])
                })
            elif stream['codec_type'] == 'audio':
                video_info.update({
                    'audio_codec': stream['codec_name'],
                    'audio_channels': stream['channels'],
                    'audio_sample_rate': stream['sample_rate']
                })
        
        return video_info
        
    except Exception as e:
        return {'error': str(e)}
