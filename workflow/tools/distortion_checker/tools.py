"""LangChain tools for distortion checking."""

import logging
from langchain.tools import tool

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


@tool("check_image_distortion")
def check_image_distortion(image_path: str) -> str:
    """Check an image for anatomical distortions using MediaPipe detection.
    
    This tool detects the following types of distortions:
    - extra_fingers: More than 5 fingers detected on a hand
    - extra_hands: More than 2 hands detected in the image
    - warped_hand: Hand landmark geometry violates anatomical constraints
    - warped_limbs: Pose landmarks show impossible joint angles
    - elongated_limbs: Limb length ratios exceed normal thresholds
    - extra_limbs: More body parts detected than anatomically possible
    - deformed_face: Face mesh geometry distorted beyond threshold
    
    For each detected distortion, the tool provides:
    - Label: Type of distortion
    - Confidence: Detection confidence score (0.0-1.0)
    - Bounding box: Location in pixels (x, y, width, height)
    - Details: Human-readable description
    
    Args:
        image_path: Path to the image file to check. Supported formats include
                   JPEG, PNG, WebP, and BMP. Can also be a base64-encoded image
                   string (with 'data:image/...' prefix or 'base64:...' prefix).
    
    Returns:
        A detailed string report of detected distortions including:
        - Summary of findings (count of distortions)
        - List of each distortion with confidence, location, and details
        - Processing time and image dimensions
        - JSON formatted results for programmatic access
    """
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


@tool("get_distortion_labels")
def get_distortion_labels(_: str = "") -> str:
    """Get information about all possible distortion labels and their meanings.
    
    This tool returns a comprehensive list of all distortion types that can be
    detected by the distortion checker, along with their descriptions.
    
    Args:
        _: Unused parameter (for compatibility with tool interface)
    
    Returns:
        A formatted string containing all distortion labels and their descriptions.
    """
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


@tool("get_distortion_stats")
def get_distortion_stats(_: str = "") -> str:
    """Get detection statistics and configuration information about the distortion checker.
    
    This tool provides information about:
    - Detection capabilities for each category (hands, pose, face)
    - Performance characteristics
    - Detection thresholds and parameters
    
    Args:
        _: Unused parameter (for compatibility with tool interface)
    
    Returns:
        A formatted string containing detection statistics and configuration.
    """
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

