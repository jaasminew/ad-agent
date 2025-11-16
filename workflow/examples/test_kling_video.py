"""
Example script for testing Kling AI image2video generation.

This script demonstrates how to use the Kling Video tool to generate
videos from images with text prompts.

Requirements:
    - KLING_ACCESS_KEY and KLING_SECRET_KEY environment variables must be set
    - COS credentials (optional, for uploading to Tencent Cloud COS)

Usage:
    python examples/test_kling_video.py
"""
import logging
from dotenv import load_dotenv
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.kling_video import get_kling_video_client


def test_video_generation():
    """Test basic video generation from image URL and prompt"""
    logger.info("=" * 60)
    logger.info("Kling AI Video Generation Test")
    logger.info("=" * 60)
    
    # Example image URL
    image_url = "https://ad-agent-1309327302.cos.ap-guangzhou.myqcloud.com/nanobanana/20251115_211032_nanobanana_generated_20251115_211032.png"
    
    # Text prompt for video generation
    prompt = "camera dolly into the laptop to make it the focal point"
    
    logger.info(f"Image URL: {image_url}")
    logger.info(f"Prompt: {prompt}")
    logger.info("")
    
    # Get client and generate video
    try:
        client = get_kling_video_client()
        
        logger.info("Starting video generation...")
        result = client.generate_video(
            image_url=image_url,
            prompt=prompt,
            duration="5",
            mode="pro",
            cfg_scale=0.5,
            upload_to_cos=True
        )
        
        logger.info("")
        logger.info("=" * 60)
        if result["success"]:
            logger.info("✓ Video generated successfully!")
            logger.info(f"  Task ID: {result.get('task_id')}")
            logger.info(f"  Local Path: {result.get('local_path')}")
            if result.get('cos_url'):
                logger.info(f"  COS URL: {result.get('cos_url')}")
            if result.get('cos_upload_error'):
                logger.warning(f"  COS Upload Error: {result.get('cos_upload_error')}")
        else:
            logger.error(f"✗ Video generation failed: {result.get('error')}")
        logger.info("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    logger.info("Starting Kling Video Test")
    logger.info("")
    
    try:
        test_video_generation()
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\n\nTest failed with error: {e}", exc_info=True)
    finally:
        logger.info("\n" + "=" * 60)
        logger.info("✓ Test completed!")
        logger.info("=" * 60)


