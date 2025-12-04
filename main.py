import os
import sys
from typing import Optional
import streamlit as st
from downloader import YouTubeDownloader
from splitter import VideoSplitter
from utils import validate_url, cleanup_temp_files
import yaml

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

class YouTubeVideoSplitter:
    def __init__(self):
        self.downloader = YouTubeDownloader()
        self.splitter = VideoSplitter()
        
    def process_video(
        self,
        url: str,
        clip_duration: tuple = (30, 60),
        output_dir: str = "output",
        quality: str = "best",
        add_captions: bool = True,
        caption_style: str = "standard"
    ):
        """
        Main processing pipeline
        """
        try:
            # Step 1: Download video
            st.info("📥 Downloading video...")
            video_info, video_path, subtitle_path = self.downloader.download_video(
                url=url,
                quality=quality,
                download_subtitles=add_captions
            )
            
            # Step 2: Split video
            st.info("✂️ Splitting video into clips...")
            clips = self.splitter.split_video(
                video_path=video_path,
                clip_duration=clip_duration,
                output_dir=output_dir,
                subtitle_path=subtitle_path if add_captions else None,
                caption_style=caption_style
            )
            
            # Step 3: Generate summary
            st.success("✅ Processing completed!")
            
            return {
                "original_video": video_info,
                "clips": clips,
                "total_clips": len(clips),
                "output_directory": output_dir
            }
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            raise

def main():
    st.set_page_config(
        page_title="YouTube Video Splitter",
        page_icon="🎬",
        layout="wide"
    )
    
    st.title("🎬 YouTube Video Splitter")
    st.markdown("Split long YouTube videos into 30-60 second clips with HD quality and captions")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
        
        col1, col2 = st.columns(2)
        with col1:
            min_duration = st.number_input("Min Clip Duration (s)", 30, 300, 30)
        with col2:
            max_duration = st.number_input("Max Clip Duration (s)", 30, 300, 60)
        
        quality = st.selectbox(
            "Video Quality",
            ["best", "1080p", "720p", "480p", "360p"]
        )
        
        add_captions = st.checkbox("Add Captions", value=True)
        
        caption_style = st.selectbox(
            "Caption Style",
            ["standard", "minimal", "bold", "outline"],
            disabled=not add_captions
        )
        
        output_dir = st.text_input("Output Directory", "output_clips")
        
        process_btn = st.button("🚀 Process Video", type="primary")
    
    # Main content area
    if process_btn and url:
        if not validate_url(url):
            st.error("Please enter a valid YouTube URL")
            return
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize processor
        processor = YouTubeVideoSplitter()
        
        # Process video
        with st.spinner("Processing video..."):
            try:
                result = processor.process_video(
                    url=url,
                    clip_duration=(min_duration, max_duration),
                    output_dir=output_dir,
                    quality=quality,
                    add_captions=add_captions,
                    caption_style=caption_style
                )
                
                # Display results
                st.header("📊 Results")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Original Duration", f"{result['original_video']['duration']}s")
                with col2:
                    st.metric("Total Clips", result['total_clips'])
                with col3:
                    st.metric("Output Directory", result['output_directory'])
                
                # Display clip list
                st.subheader("📁 Generated Clips")
                for i, clip in enumerate(result['clips']):
                    with st.expander(f"Clip {i+1}: {clip['name']}"):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.video(clip['path'])
                        with col2:
                            st.write(f"**Duration:** {clip['duration']}s")
                            st.write(f"**Size:** {clip['size_mb']:.2f} MB")
                            st.write(f"**Path:** `{clip['path']}`")
                            
                            # Download button for each clip
                            with open(clip['path'], 'rb') as f:
                                st.download_button(
                                    label="⬇️ Download Clip",
                                    data=f,
                                    file_name=clip['name'],
                                    mime="video/mp4"
                                )
                
                # Download all button
                st.success("✅ All clips generated successfully!")
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.info("💡 Troubleshooting tips:")
                st.write("1. Check if the YouTube URL is valid and accessible")
                st.write("2. Ensure you have FFmpeg installed")
                st.write("3. Check your internet connection")
                st.write("4. Try a different video quality setting")
    
    elif process_btn:
        st.warning("Please enter a YouTube URL first")

if __name__ == "__main__":
    main()
