"""Utility functions for storyboard generation."""

import json
import logging
from typing import Any, List, Optional

from .models import Beat

logger = logging.getLogger(__name__)


def normalize_beat(beat: Beat) -> str:
    """
    Normalize a beat into a single shot_text description.
    
    Combines: "{heading} — {shot description}. Action: {action}"
    
    Args:
        beat: Beat object to normalize
        
    Returns:
        Normalized shot text string
    """
    shot_text = f"{beat.heading} — {beat.shot_description}. Action: {beat.action}"
    logger.debug(f"Normalized beat {beat.beat} to: {shot_text}")
    return shot_text


def format_global_memory_notes(notes: Optional[List[Any]]) -> str:
    """
    Present global memory entries in a consistent, compact format for prompts.
    """
    if not notes:
        return "(none)"
    
    lines: List[str] = []
    iterator = list(notes)
    if not iterator:
        return "(none)"
    
    first = iterator[0]
    if isinstance(first, list):
        if first:
            lines.append("- Uploaded final URLs:")
            for url in first:
                if not url:
                    continue
                lines.append(f"  • {url}")
        else:
            lines.append("- Uploaded final URLs: (none)")
    elif isinstance(first, str):
        lines.append(f"- {first.strip()}")
    
    for entry in iterator[1:]:
        if isinstance(entry, list) and len(entry) == 5:
            title, character, style, palette, description = [
                (segment or "").strip() for segment in entry
            ]
            title_label = title or "(untitled)"
            lines.append(f"- {title_label}")
            if character:
                lines.append(f"  • Main character: {character}")
            if style:
                lines.append(f"  • Style: {style}")
            if palette:
                lines.append(f"  • Palette: {palette}")
            if description:
                lines.append(f"  • Description: {description}")
        elif isinstance(entry, str):
            cleaned = entry.strip()
            if cleaned:
                lines.append(f"- {cleaned}")
    
    return "\n".join(lines) or "(none)"


def build_global_memory_with_uploaded_urls(
    base_memory: Optional[List[List[str]]], uploaded_urls: Optional[List[str]]
) -> List[List[str]]:
    """
    Prefix the controller's global memory with the uploaded URL list so it always
    appears first when rendered or seeded into shot memory.
    """
    base: List[List[str]] = [list(entry) for entry in (base_memory or [])]
    return [list(uploaded_urls or [])] + base


def extract_color_palette(image_url: str, num_colors: int = 4) -> Optional[List[str]]:
    """
    Extract dominant color palette from an image.
    
    Uses the PaletteExtractor from tools.palette_extractor to extract
    dominant colors and convert them to hex codes.
    
    Args:
        image_url: URL of the image to analyze
        num_colors: Number of dominant colors to extract (default: 4)
        
    Returns:
        List of hex color codes (e.g., ["#FF5733", "#3366FF"]) or None if extraction fails
    """
    logger.info(f"Extracting color palette from: {image_url}")
    
    try:
        # Import palette extractor utilities
        from tools.palette_extractor import get_palette_extractor, rgb_to_hex
        
        # Get the extractor and extract palette
        extractor = get_palette_extractor()
        rgb_palette = extractor.extract_palette(image_url, num_colors=num_colors)
        
        # Convert RGB tuples to hex codes
        hex_palette = [rgb_to_hex(rgb) for rgb in rgb_palette]
        
        logger.info(f"✓ Extracted palette: {hex_palette}")
        return hex_palette
        
    except Exception as e:
        logger.error(f"Failed to extract color palette: {e}")
        logger.warning(f"Returning None - palette extraction failed")
        return None


def build_midjourney_prompt(
    reference_image_url: str,
    shot_text: str,
    palette: Optional[List[str]] = None,
    negative_prompts: Optional[List[str]] = None,
    max_words: int = 50
) -> str:
    """
    Build a complete MidJourney prompt with all components.
    
    Format: {reference_url} {shot_text_with_style_and_quality_cues} --no {negatives}
    
    Note: `palette` is accepted so upstream planners can pass continuity data,
    but the resulting prompt intentionally omits explicit palette language.
    
    Args:
        reference_image_url: Style reference image URL
        shot_text: Main description of the scene
        palette: Optional color palette (hex codes)
        negative_prompts: Optional list of things to avoid
        max_words: Target word count for the descriptive part (default: 50)
        
    Returns:
        Complete MidJourney prompt string
    """
    # Start with reference URL
    prompt_parts = [reference_image_url]
    
    # Add shot text with style modifiers
    descriptive_text = f"{shot_text}, cinematic composition, natural light, realistic proportions"
    
    if palette:
        joined_palette = ", ".join(palette)
        logger.debug(
            "Palette available for continuity (omitted from prompt by design): %s",
            joined_palette,
        )
    
    # Add correct anatomy reminders
    descriptive_text += ", correct anatomy of hands, no extra fingers or distorted hands"
    
    prompt_parts.append(descriptive_text)
    
    # Add negative prompts if provided
    if negative_prompts:
        # Convert distortion labels to MidJourney negative prompt format
        negatives = ", ".join(negative_prompts)
        prompt_parts.append(f"--no {negatives}")
    
    final_prompt = " ".join(prompt_parts)
    logger.debug(f"Built MidJourney prompt: {final_prompt[:100]}...")
    
    return final_prompt


def distortion_label_to_negative_prompt(label: str) -> str:
    """
    Convert a distortion label to a negative prompt phrase.
    
    Args:
        label: Distortion label (e.g., "extra_fingers")
        
    Returns:
        Human-readable negative prompt phrase
    """
    # Map distortion labels to negative prompt phrases
    mapping = {
        "extra_fingers": "extra fingers",
        "extra_hands": "extra hands",
        "warped_hand": "warped hands",
        "warped_limbs": "warped limbs",
        "elongated_limbs": "elongated limbs",
        "extra_limbs": "extra limbs",
        "deformed_face": "deformed face",
    }
    
    return mapping.get(label, label.replace("_", " "))


def parse_midjourney_result(result_text: str) -> dict:
    """
    Parse the result string from midjourney_imagine tool.
    
    Args:
        result_text: Result string from midjourney_imagine tool
        
    Returns:
        Dictionary with parsed task_id and image_url
    """
    lines = result_text.strip().split("\n")
    parsed = {}
    
    for line in lines:
        if line.startswith("Task ID:"):
            parsed["task_id"] = line.split(":", 1)[1].strip()
        elif line.startswith("Image URL:"):
            parsed["image_url"] = line.split(":", 1)[1].strip()
    
    return parsed


def parse_distortion_result(result_text: str) -> dict:
    """
    Parse the result string from check_image_distortion tool.
    
    Args:
        result_text: Result string from check_image_distortion tool
        
    Returns:
        Dictionary with parsed has_distortion, count, and labels
    """
    import json
    
    # Try to extract JSON from the result
    parsed = {
        "has_distortion": False,
        "count": 0,
        "labels": [],
        "distortions": []
    }
    
    # Check if no distortions
    if "No distortions detected" in result_text or "✓ No distortions" in result_text:
        return parsed
    
    # Try to extract JSON block
    if "```json" in result_text:
        json_start = result_text.find("```json") + 7
        json_end = result_text.find("```", json_start)
        json_text = result_text[json_start:json_end].strip()
        
        try:
            json_data = json.loads(json_text)
            parsed["has_distortion"] = json_data.get("has_distortion", False)
            distortions = json_data.get("distortions", [])
            parsed["count"] = len(distortions)
            parsed["labels"] = [d["label"] for d in distortions]
            parsed["distortions"] = distortions
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse distortion JSON: {e}")
    
    return parsed

