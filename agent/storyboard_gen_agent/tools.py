"""Tools configuration for the Storyboard Generation Agent."""

import logging
from typing import List
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


def get_storyboard_tools() -> List[BaseTool]:
    """
    Get all tools needed for the storyboard generation agent.
    
    Returns:
        List of LangChain tools
    """
    tools = []
    
    # Import PixelHub tools
    try:
        from tools.pixelhub import list_tags, search_images_by_tags
        tools.extend([list_tags, search_images_by_tags])
        logger.info("✓ Loaded PixelHub tools")
    except ImportError as e:
        logger.error(f"Failed to import PixelHub tools: {e}")
        raise
    
    # Import Palette Extractor tool
    try:
        from tools.palette_extractor import extract_color_palette
        tools.append(extract_color_palette)
        logger.info("✓ Loaded Palette Extractor tool")
    except ImportError as e:
        logger.error(f"Failed to import Palette Extractor tool: {e}")
        raise
    
    # Import MidJourney tools
    try:
        from tools.midjourney import (
            midjourney_imagine,
            midjourney_upscale,
            midjourney_generate_upscaled,
        )
        tools.extend([midjourney_imagine, midjourney_upscale, midjourney_generate_upscaled])
        logger.info("✓ Loaded MidJourney tools")
    except ImportError as e:
        logger.error(f"Failed to import MidJourney tools: {e}")
        raise
    
    # Import Distortion Checker tools
    try:
        from tools.distortion_checker.tools import check_image_distortion
        tools.append(check_image_distortion)
        logger.info("✓ Loaded Distortion Checker tools")
    except ImportError as e:
        logger.error(f"Failed to import Distortion Checker tools: {e}")
        raise
    
    # Import Nanobanana tools
    try:
        from tools.nanobanana import nanobanana_generate
        tools.append(nanobanana_generate)
        logger.info("✓ Loaded Nanobanana tools")
    except ImportError as e:
        logger.error(f"Failed to import Nanobanana tools: {e}")
        raise
    
    # Import Memory tools
    try:
        from tools.memory import remember, recall
        tools.extend([remember, recall])
        logger.info("✓ Loaded Memory tools")
    except ImportError as e:
        logger.error(f"Failed to import Memory tools: {e}")
        raise
    
    logger.info(f"✓ Total tools loaded: {len(tools)}")
    return tools


def get_tool_names() -> List[str]:
    """
    Get names of all available tools.
    
    Returns:
        List of tool names
    """
    tools = get_storyboard_tools()
    return [tool.name for tool in tools]

