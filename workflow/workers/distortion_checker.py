"""Distortion Checker Worker - Check for image distortions"""

import logging
import os
import tempfile
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from workflow.tools.distortion_checker.checker import DistortionChecker
from .state import ShotState

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, ConnectionError, TimeoutError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Distortion Checker (Download): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _download_image_with_retry(image_url: str, temp_path: str) -> None:
    """Download image with retry mechanism."""
    response = requests.get(image_url, timeout=30)
    response.raise_for_status()
    
    with open(temp_path, "wb") as f:
        f.write(response.content)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=3, max=15),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Distortion Checker (Check): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _check_image_with_retry(checker: DistortionChecker, temp_path: str):
    """Check image with retry mechanism."""
    return checker.check_image(temp_path)


def check_distortion(state: ShotState) -> dict:
    """
    Check generated image for anatomical distortions.
    
    Inputs:
    - midjourney_image_url: Midjourney generated image URL
    - distortion_retry_count: Current retry count (optional)
    
    Outputs:
    - distortion_check_result: Check result dict with has_distortion flag
    - distortion_retry_count: Updated retry count
    
    The workflow will route to regeneration if distortion is detected,
    or proceed to next step if image is clean.
    """
    logger.info("=== Distortion Checker: Analyzing image quality ===")
    
    midjourney_image_url = state["midjourney_image_url"]
    retry_count = state.get("distortion_retry_count", 0)
    
    # Initialize checker
    checker = DistortionChecker()
    
    # Save to temp file
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"distortion_check_{retry_count}.png")
    
    try:
        # Download image to temp file for checking with retry
        _download_image_with_retry(midjourney_image_url, temp_path)
        
        # Run distortion check with retry
        result = _check_image_with_retry(checker, temp_path)
        
        # Convert to dict for state storage
        result_dict = result.model_dump()
        
        if result.has_distortion:
            logger.warning("Found %d distortion(s):", len(result.distortions))
            for i, distortion in enumerate(result.distortions, 1):
                logger.warning("  %d. %s (confidence: %.2f)", i, distortion.label, distortion.confidence)
            
            message = "✗ Distortion Checker: Found {} distortion(s), retry count: {}".format(
                len(result.distortions), retry_count + 1
            )
        else:
            logger.info("No distortions detected, image looks good!")
            message = "✓ Distortion Checker: No distortions detected"
        
        return {
            "distortion_check_result": result_dict,
            "distortion_retry_count": retry_count + 1,
            "messages": [message]
        }
        
    finally:
        # Cleanup checker resources
        checker.cleanup()

