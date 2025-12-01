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

def test_video_concat_with_reencode():
    """Test video concatenation with re-encoding (more reliable)"""
    logger.info("=" * 80)
    logger.info("Testing Video Concatenation Tool (with re-encoding)")
    logger.info("=" * 80)
    
    # Test video URLs - 5 videos from SeeDance
    video_urls = [
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_150940_seedance_video_20251201_150940.mp4",
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_151050_seedance_video_20251201_151050.mp4",
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_151208_seedance_video_20251201_151208.mp4",
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_151327_seedance_video_20251201_151327.mp4",
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_151443_seedance_video_20251201_151443.mp4"
    ]
    
    logger.info(f"\nConcatenating {len(video_urls)} videos:")
    for i, url in enumerate(video_urls, 1):
        logger.info(f"  {i}. {url}")
    
    try:
        # Concatenate videos with re-encoding
        final_url = concat_videos(
            video_urls=video_urls,
            output_filename="test_seedance_concat_reencode",
            re_encode=True  # Re-encode for compatibility
        )
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ Video concatenation test PASSED (with re-encoding)")
        logger.info("=" * 80)
        logger.info(f"\nFinal concatenated video URL:")
        logger.info(f"  {final_url}")
        logger.info("\n" + "=" * 80)
        
        return final_url
        
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("✗ Video concatenation test FAILED (with re-encoding)")
        logger.error("=" * 80)
        logger.error(f"Error: {e}", exc_info=True)
        raise


def test_video_concat_copy_mode():
    """Test video concatenation with copy mode (faster but may have issues)"""
    logger.info("\n\n")
    logger.info("=" * 80)
    logger.info("Testing Video Concatenation Tool (copy mode - no re-encoding)")
    logger.info("=" * 80)
    
    # Test video URLs - 5 videos from SeeDance
    video_urls = [
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_150940_seedance_video_20251201_150940.mp4",
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_151050_seedance_video_20251201_151050.mp4",
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_151208_seedance_video_20251201_151208.mp4",
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_151327_seedance_video_20251201_151327.mp4",
        "https://ad-agent-tko-1309327302.cos.ap-tokyo.myqcloud.com/seedance/20251201_151443_seedance_video_20251201_151443.mp4"
    ]
    
    logger.info(f"\nConcatenating {len(video_urls)} videos:")
    for i, url in enumerate(video_urls, 1):
        logger.info(f"  {i}. {url}")
    
    try:
        # Concatenate videos without re-encoding (copy mode)
        final_url = concat_videos(
            video_urls=video_urls,
            output_filename="test_seedance_concat_copy",
            re_encode=False  # Copy mode - faster but may fail
        )
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ Video concatenation test PASSED (copy mode)")
        logger.info("=" * 80)
        logger.info(f"\nFinal concatenated video URL:")
        logger.info(f"  {final_url}")
        logger.info("\n" + "=" * 80)
        
        return final_url
        
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("✗ Video concatenation test FAILED (copy mode)")
        logger.error("=" * 80)
        logger.error(f"Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info("Testing video concatenation with 5 SeeDance videos")
    logger.info("This will test both re-encode mode and copy mode for comparison")
    logger.info("")
    
    try:
        # Test with re-encoding (recommended for reliability)
        logger.info(">>> Test 1: With re-encoding (slower but more reliable)")
        result_reencode = test_video_concat_with_reencode()
        print(f"\n🎬 Re-encode mode success! Final video: {result_reencode}")
        
        # Test with copy mode (faster but may have compatibility issues)
        logger.info("\n\n>>> Test 2: Copy mode (faster but may have issues)")
        result_copy = test_video_concat_copy_mode()
        print(f"\n🎬 Copy mode success! Final video: {result_copy}")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Re-encode mode result: {result_reencode}")
        print(f"Copy mode result:      {result_copy}")
        print("\nRecommendation: Compare both videos to see which works better.")
        print("If copy mode shows static frames, use re-encode mode.")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
