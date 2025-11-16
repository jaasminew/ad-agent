"""
Example script for testing Doubao SeeDance video generation.

This script demonstrates how to use the SeeDance Video tool to generate
videos from text prompts or text + image.

Requirements:
    - ARK_API_KEY environment variable must be set
    - COS credentials (optional, for uploading to Tencent Cloud COS)

Usage:
    python examples/test_seedance_video.py
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

from tools.seedance_video import get_seedance_video_client


def test_text_to_video():
    """Test text-to-video generation"""
    logger.info("=" * 60)
    logger.info("SeeDance Text-to-Video Test")
    logger.info("=" * 60)
    
    # Text prompt for video generation
    prompt = "无人机以极快速度穿越复杂障碍或自然奇观，带来沉浸式飞行体验"
    
    logger.info(f"Prompt: {prompt}")
    logger.info("Mode: Text-to-Video")
    logger.info("")
    
    # Get client and generate video
    try:
        client = get_seedance_video_client()
        
        logger.info("Starting video generation...")
        result = client.generate_video(
            prompt=prompt,
            image_url=None,  # No image = text-to-video mode
            resolution="1080p",
            duration=5,
            camera_fixed=False,
            watermark=True,
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


def test_image_to_video():
    """Test image-to-video generation"""
    logger.info("=" * 60)
    logger.info("SeeDance Image-to-Video Test")
    logger.info("=" * 60)
    
    # Example image URL
    image_url = "https://ad-agent-1309327302.cos.ap-guangzhou.myqcloud.com/nanobanana/20251115_211032_nanobanana_generated_20251115_211032.png"
    
    # Text prompt for video generation
    prompt = "camera dolly into the laptop to make it the focal point"
    
    logger.info(f"Image URL: {image_url}")
    logger.info(f"Prompt: {prompt}")
    logger.info("Mode: Image-to-Video")
    logger.info("")
    
    # Get client and generate video
    try:
        client = get_seedance_video_client()
        
        logger.info("Starting video generation...")
        result = client.generate_video(
            prompt=prompt,
            image_url=image_url,  # With image = image-to-video mode
            resolution="1080p",
            duration=5,
            camera_fixed=False,
            watermark=True,
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
    logger.info("Starting SeeDance Video Test")
    logger.info("")
    
    try:
        # 默认测试图生视频
        test_image_to_video()
        
        # 如果想测试文生视频，取消下面的注释
        # logger.info("\n\n")
        # test_text_to_video()
        
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\n\nTest failed with error: {e}", exc_info=True)
    finally:
        logger.info("\n" + "=" * 60)
        logger.info("✓ Test completed!")
        logger.info("=" * 60)

