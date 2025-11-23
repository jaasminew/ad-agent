# tools/nanobanana.py
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union
from urllib.parse import urlparse

from google import genai
from google.genai import types
from PIL import Image
from langchain.tools import tool
from pydantic import BaseModel, Field, model_validator

try:
    from langchain_core.tools import ToolException
except ImportError:  # pragma: no cover - older langchain versions
    from langchain.tools.base import ToolException

from .cos_uploader import COSUploader, is_cos_available
from .upload_memory import register_uploaded_url

logger = logging.getLogger(__name__)

# Discord hosts we expect storyboard links to use.
_DISCORD_CDN_HOSTS = {"cdn.discordapp.com", "media.discordapp.net"}

# ==================== Configuration ====================
NANOBANANA_CONFIG = {
    "model": "gemini-2.5-flash-image",
    "timeout": 120,  # Timeout in seconds
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
        self, prompt: str, input_image_paths: Union[str, List[str]], upload_to_cos: bool = True, aspect_ratio: str = "16:9"
    ) -> dict:
        """
        Generate image based on text prompt and input image(s).

        Args:
            prompt: Text description for image generation
            input_image_paths: Path or URL to the input reference image, or a list of paths/URLs
            upload_to_cos: Whether to upload the generated image to COS
            aspect_ratio: Aspect ratio of the generated images. Supported values are "1:1", "3:4", "4:3", "9:16", and "16:9"

        Returns:
            Dictionary containing:
            - success: bool
            - local_path: str (path to saved image)
            - cos_url: str (if uploaded to COS)
            - error: str (if failed)
        """
        try:
            # Validate aspect ratio
            valid_aspect_ratios = ["1:1", "3:4", "4:3", "9:16", "16:9"]
            if aspect_ratio not in valid_aspect_ratios:
                # Fallback to 16:9 if invalid, or raise error? Let's log warning and fallback to 16:9 to be safe
                logger.warning(f"Invalid aspect ratio: {aspect_ratio}. Fallback to 16:9. Supported values are: {', '.join(valid_aspect_ratios)}")
                aspect_ratio = "16:9"

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
            logger.info(f"Generating image with prompt: {prompt} and {len(images)} input image(s), aspect ratio: {aspect_ratio}")
            
            # Build contents list: [image1, image2, ..., prompt]
            contents = images + [prompt]
            
            # Build generation config with aspect ratio
            generation_config = types.GenerateContentConfig(
                response_modalities=["image"],
                image_generation_config=types.ImageGenerationConfig(
                    aspect_ratio=aspect_ratio
                )
            )
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generation_config,
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
                        register_uploaded_url(cos_url)
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


def _payload_with_validation_error(
    payload: Optional[dict],
    message: str,
) -> dict:
    """Ensure payload satisfies schema while surfacing validation error."""
    safe_payload = dict(payload or {})
    prompt_value = safe_payload.get("prompt")
    if prompt_value is None:
        safe_payload["prompt"] = ""
    elif not isinstance(prompt_value, str):
        safe_payload["prompt"] = str(prompt_value)

    paths_value = safe_payload.get("input_image_paths")
    if isinstance(paths_value, list):
        normalized = [
            path.strip()
            for path in paths_value
            if isinstance(path, str) and path.strip()
        ]
    elif isinstance(paths_value, str):
        normalized = [paths_value.strip()] if paths_value.strip() else []
    else:
        normalized = []
    safe_payload["input_image_paths"] = normalized

    if "upload_to_cos" not in safe_payload:
        safe_payload["upload_to_cos"] = True
    
    if "aspect_ratio" not in safe_payload:
        safe_payload["aspect_ratio"] = "16:9"

    safe_payload["validation_error"] = message
    return safe_payload


class NanobananaToolInput(BaseModel):
    """Custom args schema with guardrails for malformed Action Inputs."""

    prompt: str = Field(..., description="Text description for the image generation.")
    input_image_paths: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Path or URL to the input reference image, or list of paths/URLs.",
    )
    upload_to_cos: bool = Field(
        default=True, description="Whether to upload the generated image to COS."
    )
    aspect_ratio: str = Field(
        default="16:9",
        description="Aspect ratio of the generated images. Supported values are '1:1', '3:4', '4:3', '9:16', and '16:9'.",
    )
    validation_error: Optional[str] = Field(
        default=None,
        description="Internal guardrail message surfaced back to the agent when inputs are invalid.",
    )

    @model_validator(mode="before")
    @classmethod
    def guard_and_normalize(cls, value):
        """Detect double-encoded payloads and enforce required keys."""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "nanobanana_generate guard rejected non-JSON string payload: %s",
                    exc,
                )
                return _payload_with_validation_error(
                    payload=None,
                    message=(
                        "Action Input must be a JSON object, not a plain string. "
                        "Provide raw JSON like "
                        '{"prompt": "...", "input_image_paths": ["storyboard_url", "product_url"]}.'
                    ),
                )

        if not isinstance(value, dict):
            return _payload_with_validation_error(
                payload=None,
                message=(
                    "Action Input must be a JSON object with prompt/input_image_paths."
                ),
            )

        payload = dict(value)

        # Attempt to auto-correct double-encoded payloads where prompt holds JSON.
        needs_paths = "input_image_paths" not in payload or not payload.get(
            "input_image_paths"
        )
        prompt_value = payload.get("prompt")
        if needs_paths and isinstance(prompt_value, str):
            stripped_prompt = prompt_value.strip()
            if stripped_prompt.startswith("{") and stripped_prompt.endswith("}"):
                try:
                    nested = json.loads(stripped_prompt)
                except json.JSONDecodeError:
                    pass
                else:
                    if "input_image_paths" in nested:
                        logger.warning(
                            "nanobanana_generate guard detected double-encoded Action Input; auto-extracting fields."
                        )
                        payload.setdefault("upload_to_cos", nested.get("upload_to_cos", True))
                        payload.setdefault("aspect_ratio", nested.get("aspect_ratio", "16:9"))
                        payload["input_image_paths"] = nested.get("input_image_paths")
                        payload["prompt"] = nested.get("prompt", prompt_value)

        # Allow input_image_paths provided as JSON stringified list.
        paths_value = payload.get("input_image_paths")
        if isinstance(paths_value, str):
            trimmed = paths_value.strip()
            if trimmed.startswith("[") and trimmed.endswith("]"):
                try:
                    payload["input_image_paths"] = json.loads(trimmed)
                except json.JSONDecodeError:
                    logger.warning(
                        "nanobanana_generate guard could not parse input_image_paths list: %s",
                        paths_value,
                    )

        paths = payload.get("input_image_paths")
        if isinstance(paths, list):
            normalized_paths = []
            for idx, path in enumerate(paths):
                if not isinstance(path, str) or not path.strip():
                    return _payload_with_validation_error(
                        payload,
                        f"input_image_paths[{idx}] must be a non-empty string.",
                    )
                normalized_paths.append(path.strip())
        elif isinstance(paths, str):
            if not paths.strip():
                return _payload_with_validation_error(
                    payload, "input_image_paths cannot be an empty string."
                )
            normalized_paths = [paths.strip()]
        else:
            return _payload_with_validation_error(
                payload,
                "input_image_paths must be a string or list of strings.",
            )

        if not normalized_paths:
            error_msg = (
                "nanobanana_generate requires `input_image_paths`. "
                "Ensure Action Input is raw JSON like "
                '{"prompt": "...", "input_image_paths": ["storyboard_url", "product_url"], "upload_to_cos": true}.'
            )
            logger.warning(
                "nanobanana_generate guard rejected payload: missing input_image_paths. Payload keys: %s",
                list(payload.keys()),
            )
            return _payload_with_validation_error(payload, error_msg)

        try:
            _validate_storyboard_path(normalized_paths[0])
        except ValueError as exc:
            logger.warning(
                "nanobanana_generate guard rejected storyboard URL: %s",
                exc,
            )
            payload["input_image_paths"] = normalized_paths
            return _payload_with_validation_error(payload, str(exc))

        payload["input_image_paths"] = normalized_paths
        return payload


def _recover_payload_from_prompt(prompt_value: Optional[str]):
    """
    Attempt to recover structured fields from a prompt string that actually holds
    JSON (common when the LLM double-encodes the Action Input).
    """
    if not isinstance(prompt_value, str):
        return None

    stripped_prompt = prompt_value.strip()
    if not (stripped_prompt.startswith("{") and stripped_prompt.endswith("}")):
        return None

    try:
        nested = json.loads(stripped_prompt)
    except json.JSONDecodeError:
        return None

    if "input_image_paths" not in nested:
        return None

    return nested


def _validate_storyboard_path(storyboard_url: str) -> None:
    """
    Ensure storyboard URL uses the full Discord attachments pattern so
    we don't lose the channel ID required for downloads.
    """
    parsed = urlparse(storyboard_url)
    if not parsed.scheme or not parsed.netloc:
        return

    host = parsed.netloc.lower()
    if host not in _DISCORD_CDN_HOSTS:
        return

    segments = [segment for segment in parsed.path.split("/") if segment]
    # Expected: attachments/<channel_id>/<attachment_id>/<filename>
    if len(segments) < 4 or segments[0] != "attachments":
        raise ValueError(
            "Discord storyboard URL must include both channel_id and attachment_id, "
            "e.g., https://cdn.discordapp.com/attachments/<channel>/<attachment>/<file>. "
            "Copy the Final Storyboard URL exactly."
        )


@tool("nanobanana_generate", args_schema=NanobananaToolInput)
def nanobanana_generate(
    prompt: str,
    input_image_paths: Optional[Union[str, List[str]]] = None,
    upload_to_cos: bool = True,
    validation_error: Optional[str] = None,
) -> str:
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
    if validation_error:
        logger.error(
            "❌ [nanobanana_generate] Guard validation failed: %s",
            validation_error,
        )
        raise ToolException(validation_error)

    # Attempt to recover arguments if the agent double-encoded the payload.
    if not input_image_paths:
        recovered = _recover_payload_from_prompt(prompt)
        if recovered:
            logger.warning(
                "nanobanana_generate recovered structured payload from prompt; "
                "ensure Action Input is raw JSON to avoid this fallback."
            )
            prompt = recovered.get("prompt", prompt)
            input_image_paths = recovered.get("input_image_paths")
            upload_to_cos = recovered.get("upload_to_cos", upload_to_cos)

    # Validate image paths before proceeding. This is defensive—under normal
    # circumstances the Pydantic args schema already guarantees a value, but
    # we still guard here so that even malformed double-encoded payloads won't
    # crash with a TypeError before we can surface a useful error message.
    if not input_image_paths:
        error_msg = (
            "nanobanana_generate requires `input_image_paths`. Ensure the Action "
            "Input is proper JSON like "
            '{"prompt": "...", "input_image_paths": ["storyboard_url", "product_url"]}.'
        )
        logger.error(f"❌ [nanobanana_generate] {error_msg}")
        return f"Error: {error_msg}"

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

