"""Video Concatenation Tool - Merge multiple videos into one"""

import os
import logging
import tempfile
import subprocess
from typing import List
from pathlib import Path
import requests
from workflow.utils.cos_uploader import get_cos_uploader

logger = logging.getLogger(__name__)


class VideoConcatClient:
    """Client for concatenating multiple videos into a single video"""
    
    def __init__(self):
        """Initialize video concatenation client"""
        self.temp_dir = tempfile.gettempdir()
        logger.info("✓ Video concatenation client initialized")
    
    def download_video(self, url: str, output_path: str) -> None:
        """
        Download video from URL to local path.
        
        Args:
            url: Video URL
            output_path: Local path to save video
        """
        logger.info(f"Downloading video from: {url}")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"✓ Video downloaded to: {output_path}")
    
    def concat_videos(
        self,
        video_urls: List[str],
        output_filename: str = None
    ) -> str:
        """
        Concatenate multiple videos into a single video.
        
        Args:
            video_urls: List of video URLs to concatenate
            output_filename: Optional custom output filename (without extension)
        
        Returns:
            COS URL of the concatenated video
        
        Raises:
            ValueError: If video_urls is empty or contains less than 1 video
            RuntimeError: If ffmpeg fails
        """
        if not video_urls or len(video_urls) < 1:
            raise ValueError("Need at least 1 video URL to concatenate")
        
        logger.info(f"Starting video concatenation for {len(video_urls)} videos")
        
        # If only one video, just upload it directly
        if len(video_urls) == 1:
            logger.info("Only one video provided, uploading directly")
            temp_video = os.path.join(self.temp_dir, "single_video.mp4")
            self.download_video(video_urls[0], temp_video)
            
            # Upload to COS
            uploader = get_cos_uploader()
            if output_filename:
                cos_key = f"videos/{output_filename}.mp4"
                cos_url = uploader.upload_file(temp_video, cos_key=cos_key)
            else:
                cos_url = uploader.upload_file(temp_video, prefix="videos")
            
            # Cleanup
            os.remove(temp_video)
            
            return cos_url
        
        # Download all videos
        temp_videos = []
        for i, url in enumerate(video_urls):
            temp_path = os.path.join(self.temp_dir, f"video_{i}.mp4")
            self.download_video(url, temp_path)
            temp_videos.append(temp_path)
        
        # Create concat list file for ffmpeg
        concat_list_path = os.path.join(self.temp_dir, "concat_list.txt")
        with open(concat_list_path, 'w') as f:
            for video_path in temp_videos:
                # Use absolute path and escape single quotes
                abs_path = os.path.abspath(video_path)
                f.write(f"file '{abs_path}'\n")
        
        logger.info(f"Created concat list: {concat_list_path}")
        
        # Output path for concatenated video
        output_path = os.path.join(self.temp_dir, "concatenated_output.mp4")
        
        # Use ffmpeg to concatenate videos
        logger.info("Running ffmpeg to concatenate videos...")
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_list_path,
            '-c', 'copy',  # Copy streams without re-encoding (faster)
            '-y',  # Overwrite output file if exists
            output_path
        ]
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("✓ Videos concatenated successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e.stderr}")
            raise RuntimeError(f"Video concatenation failed: {e.stderr}")
        
        # Upload concatenated video to COS
        logger.info("Uploading concatenated video to COS...")
        uploader = get_cos_uploader()
        
        if output_filename:
            cos_key = f"videos/{output_filename}.mp4"
            cos_url = uploader.upload_file(output_path, cos_key=cos_key)
        else:
            cos_url = uploader.upload_file(output_path, prefix="videos")
        
        # Cleanup temporary files
        logger.info("Cleaning up temporary files...")
        for temp_video in temp_videos:
            os.remove(temp_video)
        os.remove(concat_list_path)
        os.remove(output_path)
        
        logger.info(f"✓ Concatenated video uploaded: {cos_url}")
        return cos_url


# Singleton instance
_client = None


def get_video_concat_client() -> VideoConcatClient:
    """Get or create singleton video concatenation client"""
    global _client
    if _client is None:
        _client = VideoConcatClient()
    return _client


def concat_videos(video_urls: List[str], output_filename: str = None) -> str:
    """
    Convenience function to concatenate videos.
    
    Args:
        video_urls: List of video URLs to concatenate
        output_filename: Optional custom output filename (without extension)
    
    Returns:
        COS URL of the concatenated video
    """
    client = get_video_concat_client()
    return client.concat_videos(video_urls, output_filename)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Test with sample videos
    test_urls = [
        "https://example.com/video1.mp4",
        "https://example.com/video2.mp4",
        "https://example.com/video3.mp4"
    ]
    
    try:
        result_url = concat_videos(test_urls, output_filename="test_concat")
        print(f"\nConcatenated video URL: {result_url}")
    except Exception as e:
        print(f"Error: {e}")

