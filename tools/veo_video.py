# tools/veo_video.py
import os
import time
import logging
import tempfile
from typing import Optional
from pathlib import Path
from datetime import datetime
from google import genai
from PIL import Image
import requests
from langchain.tools import tool

logger = logging.getLogger(__name__)

# ==================== Configuration ====================
VEO_CONFIG = {
    "model": "veo-3.1-generate-preview",
    "poll_interval": 10,  # Poll every 10 seconds
    "timeout": 600,  # Maximum wait time in seconds (10 minutes)
}


# ==================== Veo Video Client ====================
class VeoVideoClient:
    """Client for generating videos using Google Veo 3.1 with image + text input"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")

        # Initialize Gemini client
        self.client = genai.Client(api_key=self.api_key)
        self.model = VEO_CONFIG["model"]
        logger.info(f"✓ Veo Video client initialized with model: {self.model}")

        # Initialize COS uploader (lazy import to avoid dependency if not needed)
        self.cos_uploader = None
        self._cos_available = None

    def generate_video(
        self, 
        prompt: str, 
        image_url: str, 
        upload_to_cos: bool = True
    ) -> dict:
        """
        Generate video based on text prompt and input image.

        Args:
            prompt: Text description for video generation
            image_url: URL or local path to the input reference image
            upload_to_cos: Whether to upload the generated video to COS

        Returns:
            Dictionary containing:
            - success: bool
            - local_path: str (path to saved video)
            - cos_url: str (if uploaded to COS)
            - error: str (if failed)
        """
        try:
            # Load input image using genai.types.Image
            logger.info(f"Loading input image: {image_url}")
            
            from google.genai import types
            
            # Download image to local file if it's a URL
            image_path = self._get_image_path(image_url)
            
            # Load image using genai.types.Image.from_file()
            logger.info(f"Loading image from: {image_path}")
            image = types.Image.from_file(location=image_path)
            logger.info(f"Image loaded successfully")

            # Generate video with Veo 3.1
            logger.info(f"Generating video with prompt: {prompt}")
            
            operation = self.client.models.generate_videos(
                model=self.model,
                prompt=prompt,
                image=image,
            )

            # Poll the operation status until the video is ready
            start_time = time.time()
            timeout = VEO_CONFIG["timeout"]
            poll_interval = VEO_CONFIG["poll_interval"]

            while not operation.done:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    return {
                        "success": False,
                        "error": f"Video generation timed out after {timeout} seconds",
                    }

                logger.info(
                    f"Waiting for video generation to complete... "
                    f"(elapsed: {int(elapsed)}s)"
                )
                time.sleep(poll_interval)
                operation = self.client.operations.get(operation)

            # Check if operation completed successfully or with error
            logger.info("Video generation operation completed")
            
            # Check for errors first
            if hasattr(operation, 'error') and operation.error:
                error_msg = f"Veo API error (code {operation.error.code}): {operation.error.message}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                }
            
            # Extract generated video
            logger.info("Video generation successful!")
            
            # Debug: Check operation response structure
            logger.info(f"Operation response type: {type(operation.response)}")
            
            # Check if response exists
            if not operation.response:
                logger.error("Operation response is None")
                return {
                    "success": False,
                    "error": "Operation response is None - video may have been generated but response format unexpected",
                }
            
            # Check if generated_videos exists
            if not hasattr(operation.response, 'generated_videos'):
                logger.error(f"Operation response has no 'generated_videos' attribute. Available attributes: {dir(operation.response)}")
                return {
                    "success": False,
                    "error": f"Response missing 'generated_videos' attribute. Response type: {type(operation.response)}",
                }
            
            video = operation.response.generated_videos[0]

            # Download the video
            logger.info("Downloading video...")
            self.client.files.download(file=video.video)

            # Save video locally
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = tempfile.gettempdir()
            local_path = os.path.join(temp_dir, f"veo3_video_{timestamp}.mp4")
            video.video.save(local_path)
            logger.info(f"Saved generated video: {local_path}")

            result = {
                "success": True,
                "local_path": local_path,
            }

            # Upload to COS if enabled
            if upload_to_cos:
                try:
                    # Lazy import COS uploader
                    if self.cos_uploader is None:
                        from utils import COSUploader, is_cos_available
                        
                        if is_cos_available():
                            self.cos_uploader = COSUploader()
                            self._cos_available = True
                        else:
                            self._cos_available = False
                            logger.warning("COS credentials not configured")
                    
                    if self._cos_available and self.cos_uploader:
                        # Generate COS key with veo prefix
                        filename = Path(local_path).name
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        cos_key = f"veo/{timestamp}_{filename}"
                        
                        cos_url = self.cos_uploader.upload_file(local_path, cos_key=cos_key)
                        result["cos_url"] = cos_url
                    else:
                        result["cos_upload_error"] = "COS credentials not configured"
                        
                except Exception as e:
                    logger.error(f"Failed to upload to COS: {e}")
                    result["cos_upload_error"] = str(e)

            return result

        except Exception as e:
            logger.error(f"Error generating video: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _get_image_path(self, image_url: str) -> str:
        """
        Get local file path for the image, downloading it if it's a URL.

        Args:
            image_url: Local file path or URL to the image

        Returns:
            Local file path to the image
        """
        # Check if it's a URL
        if image_url.startswith(("http://", "https://")):
            logger.info(f"Downloading image from URL: {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"veo_input_{int(time.time())}.png")
            with open(temp_path, "wb") as f:
                f.write(response.content)
            logger.info(f"Image downloaded to: {temp_path}")
            return temp_path

        # Check if local file exists
        if not os.path.exists(image_url):
            raise FileNotFoundError(f"Input image not found: {image_url}")

        return image_url


# Lazy initialization of Veo Video client
_veo_video_client = None


def get_veo_video_client() -> VeoVideoClient:
    """Get or create the Veo Video client singleton"""
    global _veo_video_client
    if _veo_video_client is None:
        _veo_video_client = VeoVideoClient()
    return _veo_video_client


# ==================== LangChain Tools ====================

@tool("veo_generate_video")
def veo_generate_video(prompt: str, image_url: str, upload_to_cos: bool = True) -> str:
    """Generate a video based on text prompt and reference image using Google Veo 3.1.
    The generated video will be saved locally and optionally uploaded to Tencent Cloud COS.

    This tool is perfect for creating videos from a single image with text descriptions.
    For example: "Panning wide shot of a calico kitten sleeping in the sunshine"
    
    The image URL can be either a web URL (http/https) or a local file path.

    Args:
        prompt: Text description for the video generation. Be creative and detailed!
        image_url: URL or local file path to the input reference image
        upload_to_cos: Whether to upload the generated video to Tencent Cloud COS (default: True)

    Returns:
        The URL of the uploaded video (if COS is enabled) or the local file path.
    """
    logger.info(
        f"🎬 [veo_generate_video] Called - Prompt: '{prompt}', "
        f"Image: '{image_url}', Upload: {upload_to_cos}"
    )

    try:
        client = get_veo_video_client()
        result = client.generate_video(prompt, image_url, upload_to_cos)

        if result["success"]:
            # Return COS URL if available, otherwise return local path
            if result.get("cos_url"):
                logger.info(f"✓ [veo_generate_video] Video uploaded to COS: {result['cos_url']}")
                return result["cos_url"]
            else:
                logger.info(f"✓ [veo_generate_video] Video saved locally: {result['local_path']}")
                return result["local_path"]
        else:
            error_msg = f"Failed to generate video: {result.get('error', 'Unknown error')}"
            logger.error(f"❌ [veo_generate_video] {error_msg}")
            return f"Error: {error_msg}"

    except Exception as e:
        logger.error(f"❌ [veo_generate_video] Exception: {e}")
        return f"Error: {str(e)}"

