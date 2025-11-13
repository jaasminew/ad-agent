"""LangChain tools for distortion checking."""

import logging
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Lazy import to avoid initialization overhead
_checker_instance = None


def get_distortion_checker():
    """Get or create the DistortionChecker singleton instance"""
    global _checker_instance
    if _checker_instance is None:
        try:
            from .checker import DistortionChecker
            _checker_instance = DistortionChecker()
            logger.info("✓ DistortionChecker initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import DistortionChecker: {e}")
            raise ImportError(
                "Could not import distortion checker dependencies. "
                "Please install with: pip install mediapipe opencv-python pillow numpy"
            ) from e
    return _checker_instance


# Input schemas for tools
class CheckImageDistortionInput(BaseModel):
    """Input schema for check_image_distortion tool"""
    image_path: str = Field(description="Path to the image file to check. Supported formats include JPEG, PNG, WebP, and BMP. Can also be a base64-encoded image string (with 'data:image/...' prefix or 'base64:...' prefix).")


# Implementation functions
def _check_image_distortion_impl(image_path: str) -> str:
    """Implementation for check_image_distortion tool"""
    logger.info(f"🔍 [check_image_distortion] Called - image_path: '{image_path}'")
    
    checker = None
    try:
        # Get the checker instance
        checker = get_distortion_checker()
        
        # Run distortion detection
        result = checker.check_image(image_path)
        
        # Format the result as a human-readable string
        if result.has_distortion:
            output = f"✗ Found {len(result.distortions)} distortion(s)\n\n"
            
            for i, distortion in enumerate(result.distortions, 1):
                output += f"{i}. **{distortion.label}**\n"
                output += f"   - Confidence: {distortion.confidence:.2f}\n"
                output += f"   - Location: (x={distortion.bounding_box.x}, "
                output += f"y={distortion.bounding_box.y}, "
                output += f"w={distortion.bounding_box.w}, "
                output += f"h={distortion.bounding_box.h})\n"
                output += f"   - Details: {distortion.details}\n\n"
            
            output += f"Processing time: {result.processing_time_ms:.1f}ms\n"
            output += f"Image size: {result.image_width}×{result.image_height}px\n\n"
            
            # Add JSON representation for programmatic access
            import json
            result_dict = result.model_dump()
            output += f"JSON Output:\n```json\n{json.dumps(result_dict, indent=2)}\n```"
            
            logger.info(f"✓ [check_image_distortion] Found {len(result.distortions)} distortion(s)")
        else:
            output = f"✓ No distortions detected\n\n"
            output += f"Processing time: {result.processing_time_ms:.1f}ms\n"
            output += f"Image size: {result.image_width}×{result.image_height}px"
            
            logger.info("✓ [check_image_distortion] No distortions found")
        
        return output
        
    except FileNotFoundError as e:
        error_msg = f"Image file not found: {image_path}"
        logger.error(f"❌ [check_image_distortion] {error_msg}")
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Failed to check image distortion: {str(e)}"
        logger.error(f"❌ [check_image_distortion] {error_msg}")
        return f"Error: {error_msg}"
    finally:
        # Clean up resources after each call to avoid hanging
        if checker is not None:
            try:
                checker.cleanup()
            except Exception:
                pass  # Ignore cleanup errors


def _get_distortion_labels_impl() -> str:
    """Implementation for get_distortion_labels tool"""
    logger.info("📋 [get_distortion_labels] Called")
    
    labels = {
        "extra_fingers": "More than 5 fingers detected on a hand",
        "extra_hands": "More than 2 hands detected in the image",
        "warped_hand": "Hand landmark geometry violates anatomical constraints",
        "warped_limbs": "Pose landmarks show impossible joint angles or proportions",
        "elongated_limbs": "Limb length ratios exceed normal thresholds",
        "extra_limbs": "More body parts detected than anatomically possible",
        "deformed_face": "Face mesh geometry distorted beyond threshold (eyes, nose, mouth, or overall proportions)",
    }
    
    output = "Available Distortion Labels:\n\n"
    for label, description in labels.items():
        output += f"- **{label}**: {description}\n"
    
    logger.info("✓ [get_distortion_labels] Returned label information")
    return output


def _get_distortion_stats_impl() -> str:
    """Implementation for get_distortion_stats tool"""
    logger.info("📊 [get_distortion_stats] Called")
    
    output = """Distortion Checker Statistics

Detection Categories:
- **Hands**: extra_fingers, extra_hands, warped_hand
- **Pose**: warped_limbs, elongated_limbs, extra_limbs
- **Face**: deformed_face

Performance:
- Target processing time: 100-200ms per image on CPU
- Hardware: CPU optimized (no GPU required)
- Supported formats: JPEG, PNG, WebP, BMP

Detection Thresholds:

Hand Analyzer:
- Max hands: 2
- Max fingers per hand: 5
- Palm aspect ratio range: 0.6 - 1.8

Pose Analyzer:
- Limb length ratio max: 2.5
- Elongation threshold: 3.0

Face Analyzer:
- Eye symmetry threshold: 0.15
- Face aspect ratio range: 1.2 - 2.0

For detailed analysis of a specific image, use the check_image_distortion tool.
"""
    
    logger.info("✓ [get_distortion_stats] Returned statistics")
    return output


# Create StructuredTool instances
check_image_distortion = StructuredTool.from_function(
    func=_check_image_distortion_impl,
    name="check_image_distortion",
    description="Check an image for anatomical distortions using MediaPipe detection. Detects: extra_fingers, extra_hands, warped_hand, warped_limbs, elongated_limbs, extra_limbs, deformed_face. For each detected distortion, provides: Label, Confidence (0.0-1.0), Bounding box (x, y, width, height), Details (human-readable description).",
    args_schema=CheckImageDistortionInput,
)

get_distortion_labels = StructuredTool.from_function(
    func=_get_distortion_labels_impl,
    name="get_distortion_labels",
    description="Get information about all possible distortion labels and their meanings. Returns a comprehensive list of all distortion types that can be detected by the distortion checker, along with their descriptions.",
)

get_distortion_stats = StructuredTool.from_function(
    func=_get_distortion_stats_impl,
    name="get_distortion_stats",
    description="Get detection statistics and configuration information about the distortion checker. Provides information about detection capabilities for each category (hands, pose, face), performance characteristics, and detection thresholds and parameters.",
)

