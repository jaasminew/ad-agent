"""Test video concatenation tool with real video URLs"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path to import tools
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow.tools.video_concat import concat_videos
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_video_concat():
    """Test video concatenation with real video URLs"""
    logger.info("=" * 80)
    logger.info("Testing Video Concatenation Tool")
    logger.info("=" * 80)
    
    # Test video URLs
    video_urls = [
        "https://ad-agent-1309327302.cos.ap-guangzhou.myqcloud.com/veo/20251115_173914_veo3_video_20251115_173914.mp4",
        "https://ad-agent-1309327302.cos.ap-guangzhou.myqcloud.com/veo/20251115_173648_veo3_video_20251115_173648.mp4"
    ]
    
    logger.info(f"\nConcatenating {len(video_urls)} videos:")
    for i, url in enumerate(video_urls, 1):
        logger.info(f"  {i}. {url}")
    
    try:
        # Concatenate videos
        final_url = concat_videos(
            video_urls=video_urls,
            output_filename="test_concatenated_video"
        )
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ Video concatenation test PASSED")
        logger.info("=" * 80)
        logger.info(f"\nFinal concatenated video URL:")
        logger.info(f"  {final_url}")
        logger.info("\n" + "=" * 80)
        
        return final_url
        
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("✗ Video concatenation test FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        result = test_video_concat()
        print(f"\n🎬 Success! Final video: {result}")
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        sys.exit(1)
