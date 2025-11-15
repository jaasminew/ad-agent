"""Palette Extractor Worker - Extract dominant colors from style image"""

import logging
from tools.palette_extractor import get_palette_extractor
from .state import ShotState

logger = logging.getLogger(__name__)


def extract_palette(state: ShotState) -> dict:
    """
    Extract dominant color palette from style image.
    
    Inputs:
    - style_image_url: Style reference image URL
    
    Outputs:
    - palette: List of 4 dominant colors as RGB tuples
    """
    logger.info("=== Palette Extractor: Extracting dominant colors ===")
    
    style_image_url = state["style_image_url"]
    
    # Use PaletteExtractor to extract colors
    extractor = get_palette_extractor()
    palette = extractor.extract_palette(style_image_url, num_colors=4)
    
    logger.info(f"Extracted {len(palette)} dominant colors:")
    for i, (r, g, b) in enumerate(palette, 1):
        hex_code = f"#{r:02x}{g:02x}{b:02x}"
        logger.info(f"  Color {i}: RGB({r}, {g}, {b}) - {hex_code}")
    
    return {
        "palette": palette,
        "messages": [f"✓ Palette Extractor: Extracted {len(palette)} dominant colors"]
    }

