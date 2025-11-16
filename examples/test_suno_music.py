#!/usr/bin/env python3
"""
Test script for Suno music generation tool.

This script demonstrates how to use the Suno music generation client and tool
to generate music from text prompts.

Usage:
    python examples/test_suno_music.py

Environment Variables Required:
    - SUNO_API_TOKEN: Your Suno API token
    
Optional Environment Variables:
    - COS_SECRET_ID: Tencent Cloud COS Secret ID (for uploading)
    - COS_SECRET_KEY: Tencent Cloud COS Secret Key (for uploading)
    - COS_BUCKET: COS bucket name (for uploading)
    - COS_REGION: COS region (for uploading)
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.suno_music import SunoMusicClient, suno_generate_music

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_client_basic():
    """Test basic music generation with SunoMusicClient"""
    logger.info("=" * 80)
    logger.info("Test 1: Basic Music Generation (Instrumental Piano)")
    logger.info("=" * 80)
    
    try:
        client = SunoMusicClient()
        
        result = client.generate_music(
            prompt="一段平静舒缓的钢琴曲，带有柔和的旋律",
            style="古典",
            title="宁静钢琴冥想",
            instrumental=True,
            model="V3_5",
            upload_to_cos=False,  # Disable COS upload for testing
        )
        
        if result["success"]:
            logger.info(f"✓ Music generation successful!")
            logger.info(f"  Task ID: {result['task_id']}")
            logger.info(f"  Generated {len(result['tracks'])} track(s)")
            
            for idx, track in enumerate(result["tracks"], 1):
                logger.info(f"\n  Track {idx}:")
                logger.info(f"    Title: {track.get('title')}")
                logger.info(f"    Duration: {track.get('duration')}s")
                logger.info(f"    Tags: {track.get('tags')}")
                logger.info(f"    Local Path: {track['local_path']}")
        else:
            logger.error(f"✗ Music generation failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")


def test_client_with_lyrics():
    """Test music generation with lyrics"""
    logger.info("\n" + "=" * 80)
    logger.info("Test 2: Music Generation with Lyrics (Pop Song)")
    logger.info("=" * 80)
    
    try:
        client = SunoMusicClient()
        
        result = client.generate_music(
            prompt="一首关于城市夜晚的流行歌曲，充满活力和希望",
            style="流行",
            title="城市夜曲",
            instrumental=False,  # Enable lyrics
            model="V3_5",
            vocal_gender="f",  # Female vocals
            negative_tags="重金属, 强节奏鼓点",
            upload_to_cos=False,
        )
        
        if result["success"]:
            logger.info(f"✓ Music generation successful!")
            logger.info(f"  Task ID: {result['task_id']}")
            logger.info(f"  Generated {len(result['tracks'])} track(s)")
            
            for idx, track in enumerate(result["tracks"], 1):
                logger.info(f"\n  Track {idx}:")
                logger.info(f"    Title: {track.get('title')}")
                logger.info(f"    Duration: {track.get('duration')}s")
                logger.info(f"    Tags: {track.get('tags')}")
                logger.info(f"    Prompt: {track.get('prompt', 'N/A')[:100]}...")
                logger.info(f"    Local Path: {track['local_path']}")
        else:
            logger.error(f"✗ Music generation failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")


def test_langchain_tool():
    """Test the LangChain tool wrapper"""
    logger.info("\n" + "=" * 80)
    logger.info("Test 3: LangChain Tool Wrapper")
    logger.info("=" * 80)
    
    try:
        # Test using the tool function directly
        result = suno_generate_music.invoke({
            "prompt": "一段轻快的电子音乐，适合作为视频背景音乐",
            "style": "电子",
            "title": "科技未来",
            "instrumental": True,
            "model": "V3_5",
            "upload_to_cos": False,
        })
        
        logger.info(f"Tool result:\n{result}")
        
    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")


def test_rock_music():
    """Test rock music generation"""
    logger.info("\n" + "=" * 80)
    logger.info("Test 4: Rock Music Generation")
    logger.info("=" * 80)
    
    try:
        client = SunoMusicClient()
        
        result = client.generate_music(
            prompt="一首充满能量的摇滚乐，带有强烈的吉他独奏",
            style="摇滚",
            title="燃烧的青春",
            instrumental=False,
            model="V3_5",
            vocal_gender="m",  # Male vocals
            upload_to_cos=False,
        )
        
        if result["success"]:
            logger.info(f"✓ Music generation successful!")
            logger.info(f"  Generated {len(result['tracks'])} track(s)")
            
            for idx, track in enumerate(result["tracks"], 1):
                logger.info(f"\n  Track {idx}: {track.get('title')}")
                logger.info(f"    Duration: {track.get('duration')}s")
                logger.info(f"    Local Path: {track['local_path']}")
        else:
            logger.error(f"✗ Music generation failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")


def main():
    """Run all tests"""
    logger.info("Starting Suno Music Generation Tests")
    logger.info("=" * 80)
    
    # Check if API token is set
    if not os.environ.get("SUNO_API_TOKEN"):
        logger.error("SUNO_API_TOKEN environment variable is not set!")
        logger.error("Please set it before running tests:")
        logger.error("  export SUNO_API_TOKEN='your-token-here'")
        return
    
    # Run tests
    try:
        # Test 1: Basic instrumental music
        test_client_basic()
        
        # Test 2: Music with lyrics
        test_client_with_lyrics()
        
        # Test 3: LangChain tool wrapper
        test_langchain_tool()
        
        # Test 4: Rock music
        test_rock_music()
        
        logger.info("\n" + "=" * 80)
        logger.info("All tests completed!")
        logger.info("=" * 80)
        
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()

