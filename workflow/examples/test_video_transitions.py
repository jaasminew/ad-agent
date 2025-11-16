"""Test video generation with transition context"""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.video_generator import generate_video
from workers.state import ShotState
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


def test_video_generation_with_context():
    """Test video generation with previous/next shot context"""
    logger.info("=" * 80)
    logger.info("Testing Video Generation with Transition Context")
    logger.info("=" * 80)
    
    # Simulate three shots
    shots = [
        "Close-up of a vintage Polaroid camera in creative hands against a vibrant backdrop.",
        "Friends laughing and posing together on a rooftop at sunset, camera in the foreground ready for a snapshot.",
        "Camera shutter clicks, capturing the friends' candid moment, emphasizing the instant nature of the Polaroid."
    ]
    
    # Test each shot with its context
    for i, shot in enumerate(shots):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Testing Shot {i+1}/3")
        logger.info(f"{'=' * 80}")
        
        # Create shot state
        state: ShotState = {
            "shot": shot,
            "shot_index": i,
            "previous_shot": shots[i-1] if i > 0 else None,
            "next_shot": shots[i+1] if i < len(shots) - 1 else None,
            "nanobanana_image_url": "https://example.com/image.jpg",  # Mock URL
            "generate_video": False,  # Just test prompt generation
            "product_name": "Polaroid Camera",
            "brand_identity": "Nostalgia, Artistic",
            "product_images": "https://example.com/product.jpg",
            "distortion_retry_count": 0,
            "messages": []
        }
        
        logger.info(f"Current shot: {shot}")
        if state.get("previous_shot"):
            logger.info(f"Previous: {state['previous_shot'][:60]}...")
        if state.get("next_shot"):
            logger.info(f"Next: {state['next_shot'][:60]}...")
        
        # Generate video prompt
        result = generate_video(state)
        
        logger.info(f"\n📹 Generated Video Prompt:")
        logger.info(f"  {result['video_prompt']}")
        logger.info("")


if __name__ == "__main__":
    test_video_generation_with_context()
    print("\n✓ Test completed! Check the generated prompts for transition continuity.")

