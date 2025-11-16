"""Palette Extractor Worker - Extract dominant colors from style image"""

import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from workflow.tools.palette_extractor import get_palette_extractor
from .state import ShotState

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Palette Extractor: Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _extract_palette_with_retry(extractor, style_image_url: str, num_colors: int) -> list:
    """Extract palette with retry mechanism."""
    return extractor.extract_palette(style_image_url, num_colors=num_colors)


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
    
    # Use PaletteExtractor to extract colors with retry
    extractor = get_palette_extractor()
    palette = _extract_palette_with_retry(extractor, style_image_url, num_colors=4)
    
    logger.info(f"Extracted {len(palette)} dominant colors:")
    for i, (r, g, b) in enumerate(palette, 1):
        hex_code = f"#{r:02x}{g:02x}{b:02x}"
        logger.info(f"  Color {i}: RGB({r}, {g}, {b}) - {hex_code}")
    
    return {
        "palette": palette,
        "messages": [f"✓ Palette Extractor: Extracted {len(palette)} dominant colors"]
    }

