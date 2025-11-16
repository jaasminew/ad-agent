"""Video BGM Tool - Add background music to videos"""

import os
import logging
import tempfile
import subprocess
from typing import Optional
from datetime import datetime
import requests
from agent.utils.cos_uploader import get_cos_uploader
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ==================== Video BGM Client ====================

class VideoAddBGMClient:
    """Client for adding background music to videos"""
    
    def __init__(self):
        """Initialize video BGM client"""
        self.temp_dir = tempfile.gettempdir()
        logger.info("✓ Video BGM client initialized")
    
    def download_file(self, url: str, output_path: str) -> None:
        """
        Download file from URL to local path.
        
        Args:
            url: File URL
            output_path: Local path to save file
        """
        logger.info(f"Downloading file from: {url}")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"✓ File downloaded to: {output_path}")
    
    def add_bgm_to_video(
        self,
        video_url: str,
        audio_url: str,
        output_filename: Optional[str] = None,
        audio_volume: float = 0.3,
        fade_out_duration: float = 2.0,
    ) -> str:
        """
        Add background music to a video file using ffmpeg.

        Args:
            video_url: URL or local path to the input video file
            audio_url: URL or local path to the audio file
            output_filename: Optional custom output filename (without extension)
            audio_volume: Volume of the background music, 0.0-1.0 (default: 0.3)
            fade_out_duration: Duration of fade out effect at the end in seconds (default: 2.0)

        Returns:
            COS URL of the video with BGM

        Raises:
            RuntimeError: If ffmpeg fails or is not installed
        """
        logger.info(f"Starting BGM addition to video")
        logger.info(f"  Audio volume: {audio_volume * 100}%")
        logger.info(f"  Fade out: last {fade_out_duration}s")
        
        # Check if ffmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("ffmpeg is not installed or not found in PATH. Please install ffmpeg first.")

        # Download video if it's a URL
        if video_url.startswith("http://") or video_url.startswith("https://"):
            video_path = os.path.join(self.temp_dir, f"temp_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            self.download_file(video_url, video_path)
        else:
            video_path = video_url

        # Download audio if it's a URL
        if audio_url.startswith("http://") or audio_url.startswith("https://"):
            audio_path = os.path.join(self.temp_dir, f"temp_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")
            self.download_file(audio_url, audio_path)
        else:
            audio_path = audio_url

        # Output path for video with BGM
        output_path = os.path.join(self.temp_dir, f"video_with_bgm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")

        # Get video duration using ffprobe
        logger.info("Getting video duration...")
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        try:
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            video_duration = float(probe_result.stdout.strip())
            logger.info(f"Video duration: {video_duration:.2f}s")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed: {e.stderr}")
            raise RuntimeError(f"Failed to get video duration: {e.stderr}")

        # Calculate fade out start time
        fade_out_start = max(0, video_duration - fade_out_duration)

        # Check if video has audio stream
        probe_audio_cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        probe_audio_result = subprocess.run(probe_audio_cmd, capture_output=True, text=True)
        has_audio = bool(probe_audio_result.stdout.strip())

        # Build ffmpeg command
        logger.info("Adding background music to video...")
        
        if has_audio:
            # Video has audio, mix it with BGM
            logger.info("Video has audio track, mixing with BGM...")
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", video_path,
                "-i", audio_path,
                "-filter_complex",
                f"[1:a]volume={audio_volume},afade=t=out:st={fade_out_start}:d={fade_out_duration}[a1];"
                f"[0:a][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-y",
                output_path
            ]
        else:
            # Video has no audio, just add BGM
            logger.info("Video has no audio track, adding BGM only...")
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", video_path,
                "-i", audio_path,
                "-filter_complex",
                f"[1:a]volume={audio_volume},afade=t=out:st={fade_out_start}:d={fade_out_duration}[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-y",
                output_path
            ]

        # Run ffmpeg
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("✓ BGM added successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e.stderr}")
            raise RuntimeError(f"Video BGM addition failed: {e.stderr}")

        # Upload to COS
        logger.info("Uploading video with BGM to COS...")
        uploader = get_cos_uploader()
        
        if output_filename:
            cos_key = f"videos/{output_filename}_with_bgm.mp4"
            cos_url = uploader.upload_file(output_path, cos_key=cos_key)
        else:
            cos_url = uploader.upload_file(output_path, prefix="videos")
        
        # Cleanup temporary files
        logger.info("Cleaning up temporary files...")
        if video_url.startswith("http"):
            os.remove(video_path)
        if audio_url.startswith("http"):
            os.remove(audio_path)
        os.remove(output_path)
        
        logger.info(f"✓ Video with BGM uploaded: {cos_url}")
        return cos_url


# Singleton instance
_client = None


def get_video_add_bgm_client() -> VideoAddBGMClient:
    """Get or create singleton video BGM client"""
    global _client
    if _client is None:
        _client = VideoAddBGMClient()
    return _client


def add_bgm_to_video(
    video_url: str,
    audio_url: str,
    output_filename: Optional[str] = None,
    audio_volume: float = 0.3,
    fade_out_duration: float = 2.0,
) -> str:
    """
    Convenience function to add BGM to video.
    
    Args:
        video_url: URL or local path to the input video file
        audio_url: URL or local path to the audio file
        output_filename: Optional custom output filename (without extension)
        audio_volume: Volume of the background music, 0.0-1.0 (default: 0.3)
        fade_out_duration: Duration of fade out effect at the end in seconds (default: 2.0)
    
    Returns:
        COS URL of the video with BGM
    """
    client = get_video_add_bgm_client()
    return client.add_bgm_to_video(video_url, audio_url, output_filename, audio_volume, fade_out_duration)


# ==================== LangChain Tool ====================

@tool("video_add_bgm")
def video_add_bgm_tool(
    video_url: str,
    audio_url: str,
    audio_volume: float = 0.3,
    fade_out_duration: float = 2.0,
) -> str:
    """Add background music (BGM) to a video file.
    
    This tool combines a video with an audio file to create a new video with background music.
    The BGM will be mixed with the video's original audio (if any), and will fade out at the end.
    The audio will be automatically trimmed to match the video duration.
    The resulting video will be uploaded to Tencent Cloud COS.

    Args:
        video_url: URL or local path to the input video file
        audio_url: URL or local path to the audio file (MP3, WAV, etc.)
        audio_volume: Volume of the background music, 0.0-1.0 (default: 0.3, which is 30% volume)
        fade_out_duration: Duration of fade out effect at the end in seconds (default: 2.0)

    Returns:
        The COS URL of the video with background music added.
    """
    logger.info(
        f"🎵 [video_add_bgm] Called - "
        f"Video: '{video_url}', Audio: '{audio_url}', "
        f"Volume: {audio_volume * 100}%, Fade out: {fade_out_duration}s"
    )

    try:
        result_url = add_bgm_to_video(
            video_url=video_url,
            audio_url=audio_url,
            audio_volume=audio_volume,
            fade_out_duration=fade_out_duration,
        )
        logger.info(f"✓ [video_add_bgm] Video with BGM uploaded: {result_url}")
        return result_url

    except Exception as e:
        logger.error(f"❌ [video_add_bgm] Exception: {e}")
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Test with sample video and audio
    test_video = "https://example.com/video.mp4"
    test_audio = "https://example.com/audio.mp3"
    
    try:
        result_url = add_bgm_to_video(
            video_url=test_video,
            audio_url=test_audio,
            output_filename="test_with_bgm"
        )
        print(f"\nVideo with BGM URL: {result_url}")
    except Exception as e:
        print(f"Error: {e}")
