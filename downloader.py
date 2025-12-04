import yt_dlp
import os
from typing import Tuple, Dict, Optional
from pathlib import Path
import tempfile
from tqdm import tqdm

class YouTubeDownloader:
    def __init__(self, temp_dir: str = "temp"):
        self.temp_dir = tempfile.mkdtemp(prefix="youtube_splitter_")
        Path(self.temp_dir).mkdir(exist_ok=True)
    
    def download_video(
        self,
        url: str,
        quality: str = "best",
        download_subtitles: bool = True
    ) -> Tuple[Dict, str, Optional[str]]:
        """
        Download YouTube video with specified quality and subtitles
        """
        ydl_opts = {
            'format': self._get_format_selector(quality),
            'outtmpl': os.path.join(self.temp_dir, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
            'extract_flat': False,
            'progress_hooks': [self._progress_hook],
            'writesubtitles': download_subtitles,
            'writeautomaticsub': download_subtitles,
            'subtitleslangs': ['en', 'en-US', 'en-GB'],
            'subtitlesformat': 'srt',
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first
                info = ydl.extract_info(url, download=False)
                
                # Download video
                print(f"Downloading: {info['title']}")
                ydl.download([url])
                
                # Find downloaded files
                video_filename = ydl.prepare_filename(info)
                video_path = video_filename.replace('.webm', '.mp4').replace('.mkv', '.mp4')
                
                subtitle_path = None
                if download_subtitles:
                    # Look for subtitle file
                    base_name = os.path.splitext(video_path)[0]
                    subtitle_path = f"{base_name}.en.srt"
                    if not os.path.exists(subtitle_path):
                        subtitle_path = f"{base_name}.en-US.srt"
                    if not os.path.exists(subtitle_path):
                        subtitle_path = f"{base_name}.en-GB.srt"
                
                video_info = {
                    'title': info['title'],
                    'duration': info['duration'],
                    'uploader': info.get('uploader', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'description': info.get('description', '')[:200]
                }
                
                return video_info, video_path, subtitle_path
                
        except Exception as e:
            raise Exception(f"Failed to download video: {str(e)}")
    
    def _get_format_selector(self, quality: str) -> str:
        """
        Get format selector based on quality preference
        """
        quality_map = {
            'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]',
            '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]',
            '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]',
            '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]',
        }
        return quality_map.get(quality, quality_map['best'])
    
    def _progress_hook(self, d):
        """
        Progress hook for download
        """
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                downloaded = d.get('downloaded_bytes', 0)
                percent = (downloaded / total) * 100
                print(f"\rDownloading: {percent:.1f}%", end='')
    
    def cleanup(self):
        """
        Clean up temporary files
        """
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
