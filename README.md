# YouTube Video Splitter 🎬

Split long YouTube videos into 30-60 second clips with HD quality, captions, and no watermark.

## Features ✨

- **HD Quality**: Download and process videos in up to 1080p quality
- **Smart Splitting**: Automatic detection of natural split points (scene changes, silence)
- **Caption Support**: Automatic subtitle downloading and burning
- **No Watermark**: Clean output without any watermarks
- **Batch Processing**: Process multiple videos at once
- **Web Interface**: User-friendly Streamlit web interface
- **Docker Support**: Easy deployment with Docker

## Installation 🚀

### Prerequisites
- Python 3.8+
- FFmpeg installed on your system
- Git

### Method 1: Local Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/youtube-video-splitter.git
cd youtube-video-splitter

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (Ubuntu/Debian)
sudo apt-get install ffmpeg

# Install FFmpeg (macOS)
brew install ffmpeg

# Install FFmpeg (Windows)
# Download from https://ffmpeg.org/download.html
# Add to PATH
