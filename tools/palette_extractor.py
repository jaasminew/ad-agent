# tools/palette_extractor.py
import ast
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests
from io import BytesIO
from langchain.tools import tool
from pydantic import BaseModel, Field, ValidationError, model_validator

logger = logging.getLogger(__name__)

# ==================== Configuration ====================
PALETTE_CONFIG = {
    "default_num_colors": 4,  # Default number of colors to extract
    "quality": 10,  # Quality/speed tradeoff (1-10, higher is faster but less precise)
}


# ==================== Palette Extractor ====================
class PaletteExtractor:
    """Extract dominant color palette from images"""

    def __init__(self):
        """Initialize the palette extractor"""
        # Try to import colorthief, fall back to PIL if not available
        try:
            from colorthief import ColorThief
            self.use_colorthief = True
            logger.info("✓ Palette extractor initialized with ColorThief")
        except ImportError:
            self.use_colorthief = False
            try:
                from PIL import Image
                logger.info("✓ Palette extractor initialized with PIL (ColorThief not available)")
            except ImportError:
                raise ImportError(
                    "Neither colorthief nor PIL is available. "
                    "Please install one of them: 'pip install colorthief' or 'pip install Pillow'"
                )

    def _fetch_image(self, image_url: str) -> BytesIO:
        """Fetch image from URL"""
        logger.info(f"Fetching image from: {image_url}")
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return BytesIO(response.content)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch image: {e}")
            raise

    def _extract_with_colorthief(
        self, image_file: BytesIO, num_colors: int
    ) -> List[Tuple[int, int, int]]:
        """Extract palette using ColorThief library"""
        from colorthief import ColorThief
        
        color_thief = ColorThief(image_file)
        palette = color_thief.get_palette(
            color_count=num_colors,
            quality=PALETTE_CONFIG["quality"]
        )
        return palette

    def _extract_with_pil(
        self, image_file: BytesIO, num_colors: int
    ) -> List[Tuple[int, int, int]]:
        """Extract palette using PIL/Pillow"""
        from PIL import Image
        
        image = Image.open(image_file)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize image for faster processing
        image.thumbnail((200, 200))
        
        # Get colors using quantization
        paletted = image.quantize(colors=num_colors)
        palette = paletted.getpalette()
        
        # Convert flat palette list to list of RGB tuples
        colors = []
        for i in range(num_colors):
            r = palette[i * 3]
            g = palette[i * 3 + 1]
            b = palette[i * 3 + 2]
            colors.append((r, g, b))
        
        return colors

    def extract_palette(
        self, image_url: str, num_colors: Optional[int] = None
    ) -> List[Tuple[int, int, int]]:
        """
        Extract dominant color palette from an image URL
        
        Args:
            image_url: URL of the image to analyze
            num_colors: Number of dominant colors to extract (default: 4)
        
        Returns:
            List of RGB tuples representing the dominant colors
        """
        if num_colors is None:
            num_colors = PALETTE_CONFIG["default_num_colors"]
        
        logger.info(f"Extracting {num_colors} dominant colors from image")
        
        try:
            # Fetch the image
            image_file = self._fetch_image(image_url)
            
            # Extract palette using the available method
            if self.use_colorthief:
                palette = self._extract_with_colorthief(image_file, num_colors)
            else:
                palette = self._extract_with_pil(image_file, num_colors)
            
            logger.info(f"Successfully extracted {len(palette)} colors")
            return palette
            
        except Exception as e:
            logger.error(f"Failed to extract palette: {e}")
            raise


# Lazy initialization of palette extractor
_palette_extractor = None


def get_palette_extractor() -> PaletteExtractor:
    """Get or create the palette extractor singleton"""
    global _palette_extractor
    if _palette_extractor is None:
        _palette_extractor = PaletteExtractor()
    return _palette_extractor


# ==================== LangChain Tool ====================

class PaletteInput(BaseModel):
    """Args schema for extract_color_palette tool."""

    image_url: str
    num_colors: int = Field(default=PALETTE_CONFIG["default_num_colors"], ge=1, le=16)

    @staticmethod
    def _coerce_action_input(raw_value: str) -> Dict[str, Any]:
        cleaned = raw_value.strip()
        if cleaned.startswith("{") and cleaned.endswith("}"):
            for loader in (json.loads, ast.literal_eval):
                try:
                    parsed = loader(cleaned)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    continue
        return {"image_url": cleaned}

    @staticmethod
    def _coerce_str(value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value

    @staticmethod
    def _coerce_int(value: Any) -> Any:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return value

    @model_validator(mode="before")
    @classmethod
    def parse_router_payload(cls, value: Any):
        if isinstance(value, str):
            return cls._coerce_action_input(value)
        if isinstance(value, dict):
            coerced = value.copy()
            raw_image_url = coerced.get("image_url")
            if isinstance(raw_image_url, str):
                stripped = raw_image_url.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    nested = cls._coerce_action_input(stripped)
                    coerced.update(nested)
                else:
                    coerced["image_url"] = cls._coerce_str(raw_image_url)
            if "num_colors" in coerced:
                coerced["num_colors"] = cls._coerce_int(coerced["num_colors"])
            return coerced
        return value


@tool("extract_color_palette", args_schema=PaletteInput)
def extract_color_palette(image_url: str, num_colors: int = 4) -> str:
    """Extract the dominant color palette from an image URL. Returns 4 dominant colors.
    
    Args:
        image_url: URL of the image to analyze
    
    Returns:
        A string describing the dominant colors with RGB values and hex codes.
    """
    logger.info(f"🎨 [extract_color_palette] Called - URL: '{image_url}'")
    
    try:
        clean_image_url = image_url.strip()
        extractor = get_palette_extractor()
        palette = extractor.extract_palette(clean_image_url, num_colors=num_colors or 4)
        
        # Format the result
        result_lines = [f"Extracted {len(palette)} dominant colors:"]
        result_lines.append("")
        
        for i, (r, g, b) in enumerate(palette, 1):
            hex_code = f"#{r:02x}{g:02x}{b:02x}"
            result_lines.append(f"Color {i}: RGB({r}, {g}, {b}) - Hex: {hex_code}")
        
        result_text = "\n".join(result_lines)
        logger.info(f"✓ [extract_color_palette] Successfully extracted palette")
        return result_text
        
    except ValidationError as ve:
        logger.error(f"❌ [extract_color_palette] Validation error: {ve}")
        return f"Error extracting color palette: {ve}"
    except Exception as e:
        logger.error(f"❌ [extract_color_palette] Exception: {e}")
        return f"Error extracting color palette: {str(e)}"


# ==================== Utility Functions ====================

def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color code"""
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Convert hex color code to RGB tuple"""
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

