"""Video Concatenator Worker - Concatenate all shot videos into final video"""

import logging
import subprocess
from typing import List, Dict, Any
from datetime import datetime
from .state import WorkflowState
from tools.video_concat import concat_videos

logger = logging.getLogger(__name__)


def get_video_duration(video_path: str) -> float:
    """
    Get video duration using ffprobe.
    
    Args:
        video_path: Path or URL to the video file
        
    Returns:
        Duration in seconds
    """
    try:
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        logger.warning(f"Failed to get video duration: {e}")
        return 0.0


def concatenate_videos(state: WorkflowState) -> dict:
    """
    Concatenate all shot videos into a single final video.
    
    This worker runs after result aggregation. It only performs video concatenation
    if generate_video is True, otherwise it does nothing.
    
    Inputs:
    - shot_results: List of results from each shot
    - generate_video: Whether to generate and concatenate videos
    - product_name: Product name (for output filename)
    
    Outputs:
    - final_video_url: URL of the concatenated final video (only if generate_video=True)
    """
    logger.info("=== Video Concatenator: Checking if video concatenation is needed ===")
    
    generate_video_flag = state.get("generate_video", False)
    
    if not generate_video_flag:
        logger.info("Video generation is disabled (generate_video=False), skipping concatenation")
        return {
            "messages": ["✓ Video Concatenator: Skipped (video generation disabled)"]
        }
    
    # Video generation is enabled, proceed with concatenation
    logger.info("Video generation is enabled, proceeding with concatenation")
    
    shot_results = state.get("shot_results", [])
    product_name = state.get("product_name", "ad")
    
    if not shot_results:
        logger.warning("No shot results found, cannot concatenate videos")
        return {
            "messages": ["⚠ Video Concatenator: No shot results to concatenate"]
        }
    
    # Collect all video URLs from shot results
    video_urls = []
    for i, result in enumerate(shot_results, 1):
        video_url = result.get("video_url")
        if video_url:
            logger.info(f"Found video URL for shot {i}: {video_url}")
            video_urls.append(video_url)
        else:
            logger.warning(f"Shot {i} does not have a video URL, skipping")
    
    if not video_urls:
        logger.error("No video URLs found in shot results, cannot concatenate")
        return {
            "messages": ["✗ Video Concatenator: No videos to concatenate"]
        }
    
    if len(video_urls) < len(shot_results):
        logger.warning(
            f"Only {len(video_urls)}/{len(shot_results)} shots have videos, "
            f"concatenating available videos"
        )
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize product name for filename
    safe_product_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_product_name = safe_product_name.replace(' ', '_')
    output_filename = f"{safe_product_name}_final_{timestamp}"
    
    logger.info(f"Concatenating {len(video_urls)} videos...")
    logger.info(f"Output filename: {output_filename}")
    
    try:
        # Concatenate videos
        final_video_url = concat_videos(video_urls, output_filename=output_filename)
        
        # Get video duration
        video_duration = get_video_duration(final_video_url)
        
        logger.info("=" * 80)
        logger.info("✓ Video concatenation completed successfully!")
        logger.info(f"Final video URL: {final_video_url}")
        logger.info(f"Video duration: {video_duration:.2f} seconds")
        logger.info("=" * 80)
        
        return {
            "final_video_url": final_video_url,
            "video_duration": video_duration,
            "messages": [f"✓ Video Concatenator: Created final video from {len(video_urls)} shots ({video_duration:.1f}s)"]
        }
        
    except Exception as e:
        logger.error(f"Video concatenation failed: {e}", exc_info=True)
        return {
            "messages": [f"✗ Video Concatenator: Failed to concatenate videos - {str(e)}"]
        }

