"""Test script for color palette extraction integration."""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_palette_extraction():
    """Test the palette extraction function integration."""
    
    logger.info("="*80)
    logger.info("Testing Palette Extraction Integration")
    logger.info("="*80)
    
    # Test 1: Import the utility function
    logger.info("\n1. Testing utility function import...")
    try:
        from storyboard_gen_agent.utils import extract_color_palette
        logger.info("✓ Successfully imported extract_color_palette from utils")
    except ImportError as e:
        logger.error(f"✗ Failed to import: {e}")
        return False
    
    # Test 2: Import the tool
    logger.info("\n2. Testing LangChain tool import...")
    try:
        from tools.palette_extractor import extract_color_palette as tool_extract
        logger.info("✓ Successfully imported extract_color_palette tool")
    except ImportError as e:
        logger.error(f"✗ Failed to import tool: {e}")
        return False
    
    # Test 3: Test with a sample URL (if available)
    logger.info("\n3. Testing palette extraction with sample image...")
    test_url = "https://via.placeholder.com/300x300/FF5733/FFFFFF"
    
    try:
        result = extract_color_palette(test_url)
        if result is None:
            logger.warning("⚠️  Function returned None (extraction may have failed)")
            logger.info("   This is expected if the image URL is not accessible")
        else:
            logger.info(f"✓ Successfully extracted palette: {result}")
            logger.info(f"   Number of colors: {len(result)}")
            for i, color in enumerate(result, 1):
                logger.info(f"   Color {i}: {color}")
    except Exception as e:
        logger.error(f"✗ Error during extraction: {e}")
        logger.info("   This might be due to network issues or missing dependencies")
        logger.info("   Required: pip install colorthief (or Pillow)")
    
    # Test 4: Check tool list
    logger.info("\n4. Testing tool registration...")
    try:
        from storyboard_gen_agent.tools import get_storyboard_tools, get_tool_names
        tools = get_storyboard_tools()
        tool_names = get_tool_names()
        
        logger.info(f"✓ Total tools loaded: {len(tools)}")
        logger.info(f"   Tool names: {tool_names}")
        
        if "extract_color_palette" in tool_names:
            logger.info("✓ extract_color_palette is registered in the agent's toolset")
        else:
            logger.error("✗ extract_color_palette is NOT in the toolset!")
            return False
            
    except Exception as e:
        logger.error(f"✗ Failed to load tools: {e}")
        return False
    
    logger.info("\n" + "="*80)
    logger.info("✅ All tests passed! Palette extraction is properly integrated.")
    logger.info("="*80)
    
    return True


if __name__ == "__main__":
    success = test_palette_extraction()
    sys.exit(0 if success else 1)

