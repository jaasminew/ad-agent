# tools/nanobanana.py
import os
import logging
import tempfile
from typing import Optional, Union, List
from pathlib import Path
from datetime import datetime
from google import genai
from google.genai import types
from PIL import Image
from langchain.tools import tool

logger = logging.getLogger(__name__)

# ==================== Configuration ====================
NANOBANANA_CONFIG = {
    "model": "gemini-2.5-flash-image",
    "timeout": 180,  # Timeout in seconds (3 minutes) for image composition
}


# ==================== Nanobanana Client ====================
class NanobananaClient:
    """Client for generating images using Google Gemini and uploading to COS"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")

        # Initialize Gemini client
        self.client = genai.Client(api_key=self.api_key)
        self.model = NANOBANANA_CONFIG["model"]
        logger.info(f"✓ Nanobanana client initialized with model: {self.model}")

        # Initialize COS uploader (lazy import to avoid dependency if not needed)
        self.cos_uploader = None
        self._cos_available = None

    def generate_image(
        self, prompt: str, input_image_paths: Union[str, List[str]], upload_to_cos: bool = True
    ) -> dict:
        """
        Generate image based on text prompt and input image(s).

        Args:
            prompt: Text description for image generation
            input_image_paths: Path or URL to the input reference image, or a list of paths/URLs
            upload_to_cos: Whether to upload the generated image to COS

        Returns:
            Dictionary containing:
            - success: bool
            - local_path: str (path to saved image)
            - cos_url: str (if uploaded to COS)
            - error: str (if failed)
        """
        try:
            # Normalize input to list
            if isinstance(input_image_paths, str):
                input_image_paths = [input_image_paths]
            
            if not input_image_paths:
                raise ValueError("At least one input image is required")
            
            # Load input images
            images = []
            for idx, input_image_path in enumerate(input_image_paths):
                if not os.path.exists(input_image_path):
                    # Try to download if it's a URL
                    if input_image_path.startswith(("http://", "https://")):
                        logger.info(f"Downloading image {idx + 1}/{len(input_image_paths)} from URL: {input_image_path}")
                        import requests
                        response = requests.get(input_image_path, timeout=30)
                        response.raise_for_status()
                        
                        # Save to temporary file
                        temp_dir = tempfile.gettempdir()
                        temp_input = os.path.join(temp_dir, f"nanobanana_input_{idx}.png")
                        with open(temp_input, "wb") as f:
                            f.write(response.content)
                        input_image_path = temp_input
                    else:
                        raise FileNotFoundError(f"Input image not found: {input_image_path}")

                logger.info(f"Loading input image {idx + 1}/{len(input_image_paths)}: {input_image_path}")
                image = Image.open(input_image_path)
                images.append(image)

            # Generate image
            logger.info(f"Generating image with prompt: {prompt} and {len(images)} input image(s)")
            
            # Build contents list: [image1, image2, ..., prompt]
            contents = images + [prompt]
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
            )

            # Extract generated image
            generated_image = None
            text_response = None

            for part in response.parts:
                if part.text is not None:
                    text_response = part.text
                    logger.info(f"Received text response: {text_response}")
                elif part.inline_data is not None:
                    generated_image = part.as_image()
                    logger.info("Received generated image")

            if generated_image is None:
                return {
                    "success": False,
                    "error": "No image generated in response",
                    "text_response": text_response,
                }

            # Save generated image locally
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = tempfile.gettempdir()
            local_path = os.path.join(temp_dir, f"nanobanana_generated_{timestamp}.png")
            generated_image.save(local_path)
            logger.info(f"Saved generated image: {local_path}")

            result = {
                "success": True,
                "local_path": local_path,
                "text_response": text_response,
            }

            # Upload to COS if enabled
            if upload_to_cos:
                try:
                    # Lazy import COS uploader
                    if self.cos_uploader is None:
                        from workflow.utils import COSUploader, is_cos_available
                        
                        if is_cos_available():
                            self.cos_uploader = COSUploader()
                            self._cos_available = True
                        else:
                            self._cos_available = False
                            logger.warning("COS credentials not configured")
                    
                    if self._cos_available and self.cos_uploader:
                        # Generate COS key with nanobanana prefix
                        filename = Path(local_path).name
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        cos_key = f"nanobanana/{timestamp}_{filename}"
                        
                        cos_url = self.cos_uploader.upload_file(local_path, cos_key=cos_key)
                        result["cos_url"] = cos_url
                    else:
                        result["cos_upload_error"] = "COS credentials not configured"
                        
                except Exception as e:
                    logger.error(f"Failed to upload to COS: {e}")
                    result["cos_upload_error"] = str(e)

            return result

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return {
                "success": False,
                "error": str(e),
            }


# Lazy initialization of Nanobanana client
_nanobanana_client = None


def get_nanobanana_client() -> NanobananaClient:
    """Get or create the Nanobanana client singleton"""
    global _nanobanana_client
    if _nanobanana_client is None:
        _nanobanana_client = NanobananaClient()
    return _nanobanana_client


# ==================== LangChain Tools ====================

@tool("nanobanana_generate")
def nanobanana_generate(prompt: str, input_image_paths: Union[str, List[str]], upload_to_cos: bool = True) -> str:
    """Generate an image based on text prompt and reference image(s) using Google Gemini.
    The generated image will be saved locally and optionally uploaded to Tencent Cloud COS.

    This tool is perfect for creating variations or modifications of existing images based on text descriptions.
    For example: "Create a picture of my cat eating a nano-banana in a fancy restaurant under the Gemini constellation"
    
    You can also provide multiple reference images for more complex image generation tasks.

    Args:
        prompt: Text description for the image generation. Be creative and detailed!
        input_image_paths: Path or URL to the input reference image, or a list of paths/URLs for multiple images
        upload_to_cos: Whether to upload the generated image to Tencent Cloud COS (default: True)

    Returns:
        The URL of the uploaded image (if COS is enabled) or the local file path.
    """
    # Format image paths for logging
    if isinstance(input_image_paths, str):
        image_info = f"Image: '{input_image_paths}'"
    else:
        image_info = f"Images: {len(input_image_paths)} files"
    
    logger.info(
        f"🍌 [nanobanana_generate] Called - Prompt: '{prompt}', "
        f"{image_info}, Upload: {upload_to_cos}"
    )

    try:
        client = get_nanobanana_client()
        result = client.generate_image(prompt, input_image_paths, upload_to_cos)

        if result["success"]:
            # Return COS URL if available, otherwise return local path
            if result.get("cos_url"):
                logger.info(f"✓ [nanobanana_generate] Image uploaded to COS: {result['cos_url']}")
                return result["cos_url"]
            else:
                logger.info(f"✓ [nanobanana_generate] Image saved locally: {result['local_path']}")
                return result["local_path"]
        else:
            error_msg = f"Failed to generate image: {result.get('error', 'Unknown error')}"
            logger.error(f"❌ [nanobanana_generate] {error_msg}")
            return f"Error: {error_msg}"

    except Exception as e:
        logger.error(f"❌ [nanobanana_generate] Exception: {e}")
        return f"Error: {str(e)}"

