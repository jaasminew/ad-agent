# tools/seedance_video.py
import os
import time
import logging
import tempfile
import requests
from typing import Optional
from pathlib import Path
from datetime import datetime
from langchain.tools import tool
from volcenginesdkarkruntime import Ark

logger = logging.getLogger(__name__)

# ==================== Configuration ====================
SEEDANCE_CONFIG = {
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "doubao-seedance-1-0-pro-250528",
    "poll_interval": 3,  # Poll every 3 seconds
    "timeout": 600,  # Maximum wait time in seconds (10 minutes)
    "default_resolution": "1080p",
    "default_duration": 5,
}


# ==================== SeeDance Video Client ====================
class SeeDanceVideoClient:
    """Client for generating videos using Doubao SeeDance API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("ARK_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "ARK_API_KEY environment variable must be set"
            )

        self.base_url = base_url or SEEDANCE_CONFIG["base_url"]
        self.model = SEEDANCE_CONFIG["model"]
        
        # Initialize Ark client
        self.client = Ark(
            base_url=self.base_url,
            api_key=self.api_key,
        )
        
        logger.info(f"✓ SeeDance Video client initialized with model: {self.model}")

        # Initialize COS uploader (lazy import to avoid dependency if not needed)
        self.cos_uploader = None
        self._cos_available = None

    def generate_video(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        resolution: str = "1080p",
        duration: int = 5,
        camera_fixed: bool = False,
        watermark: bool = True,
        upload_to_cos: bool = True,
    ) -> dict:
        """
        Generate video from text prompt or text + image using SeeDance API.

        Args:
            prompt: Text description for video generation
            image_url: Optional first frame image URL (if None, text-to-video mode)
            resolution: Video resolution, e.g., "1080p", "720p" (default: "1080p")
            duration: Video duration in seconds (default: 5)
            camera_fixed: Whether camera is fixed (default: False)
            watermark: Whether to add watermark (default: True)
            upload_to_cos: Whether to upload the generated video to COS

        Returns:
            Dictionary containing:
            - success: bool
            - task_id: str (SeeDance task ID)
            - local_path: str (path to saved video)
            - cos_url: str (if uploaded to COS)
            - error: str (if failed)
        """
        try:
            # Step 1: Create video generation task
            logger.info(f"Creating SeeDance video generation task...")
            logger.info(f"  Prompt: {prompt}")
            if image_url:
                logger.info(f"  Image URL: {image_url}")
                logger.info(f"  Mode: Image-to-Video")
            else:
                logger.info(f"  Mode: Text-to-Video")
            logger.info(f"  Resolution: {resolution}, Duration: {duration}s")

            # Build content array
            content = []
            
            # Add text prompt with parameters
            text_content = f"{prompt} --resolution {resolution} --duration {duration} --camerafixed {str(camera_fixed).lower()} --watermark {str(watermark).lower()}"
            content.append({
                "type": "text",
                "text": text_content
            })
            
            # Add image if provided (image-to-video mode)
            if image_url:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                })

            # Create task
            create_result = self.client.content_generation.tasks.create(
                model=self.model,
                content=content
            )
            
            task_id = create_result.id
            logger.info(f"✓ Task created successfully: {task_id}")

            # Step 2: Poll task status until completed
            video_url = self._poll_task_status(task_id)
            
            if not video_url:
                return {
                    "success": False,
                    "error": "Failed to get video URL from task result",
                }

            # Step 3: Download video
            logger.info(f"Downloading video from: {video_url}")
            video_response = requests.get(video_url, timeout=120)
            video_response.raise_for_status()

            # Save video locally
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = tempfile.gettempdir()
            local_path = os.path.join(temp_dir, f"seedance_video_{timestamp}.mp4")
            
            with open(local_path, "wb") as f:
                f.write(video_response.content)
            
            logger.info(f"✓ Video saved locally: {local_path}")

            result = {
                "success": True,
                "task_id": task_id,
                "local_path": local_path,
            }

            # Step 4: Upload to COS if enabled
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
                        # Generate COS key with seedance prefix
                        filename = Path(local_path).name
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        cos_key = f"seedance/{timestamp}_{filename}"
                        
                        cos_url = self.cos_uploader.upload_file(local_path, cos_key=cos_key)
                        result["cos_url"] = cos_url
                        logger.info(f"✓ Video uploaded to COS: {cos_url}")
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

    def _poll_task_status(self, task_id: str) -> Optional[str]:
        """
        Poll task status until it's completed or failed.

        Args:
            task_id: SeeDance task ID

        Returns:
            Video URL if successful, None if failed
        """
        start_time = time.time()
        timeout = SEEDANCE_CONFIG["timeout"]
        poll_interval = SEEDANCE_CONFIG["poll_interval"]

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"Task polling timed out after {timeout} seconds")
                return None

            try:
                get_result = self.client.content_generation.tasks.get(task_id=task_id)
                status = get_result.status
                
                logger.info(f"Task status: {status} (elapsed: {int(elapsed)}s)")

                if status == "succeeded":
                    # Extract video URL
                    logger.info(f"✓ Video generation succeeded!")
                    
                    # Get video URL from result
                    if hasattr(get_result, 'output') and get_result.output:
                        # Try to get video URL from output
                        if hasattr(get_result.output, 'video_url'):
                            return get_result.output.video_url
                        elif isinstance(get_result.output, dict) and 'video_url' in get_result.output:
                            return get_result.output['video_url']
                        elif isinstance(get_result.output, list) and len(get_result.output) > 0:
                            first_output = get_result.output[0]
                            if hasattr(first_output, 'url'):
                                return first_output.url
                            elif isinstance(first_output, dict) and 'url' in first_output:
                                return first_output['url']
                    
                    logger.error(f"Could not extract video URL from result: {get_result}")
                    return None

                elif status == "failed":
                    error_msg = get_result.error if hasattr(get_result, 'error') else "Unknown error"
                    logger.error(f"Task failed: {error_msg}")
                    return None

                else:
                    # Task is still processing
                    logger.info(f"Waiting for video generation to complete...")
                    time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling task status: {e}")
                time.sleep(poll_interval)


# Lazy initialization of SeeDance Video client
_seedance_video_client = None


def get_seedance_video_client() -> SeeDanceVideoClient:
    """Get or create the SeeDance Video client singleton"""
    global _seedance_video_client
    if _seedance_video_client is None:
        _seedance_video_client = SeeDanceVideoClient()
    return _seedance_video_client


# ==================== LangChain Tools ====================

@tool("seedance_generate_video")
def seedance_generate_video(
    prompt: str,
    image_url: Optional[str] = None,
    resolution: str = "1080p",
    duration: int = 5,
    camera_fixed: bool = False,
    watermark: bool = True,
    upload_to_cos: bool = True,
) -> str:
    """Generate a video using Doubao SeeDance API (text-to-video or image-to-video).
    The generated video will be saved locally and optionally uploaded to Tencent Cloud COS.

    This tool supports both text-to-video and image-to-video generation.
    SeeDance specializes in high-quality video generation with camera control.
    
    Args:
        prompt: Text description for the video generation. Be creative and detailed!
        image_url: Optional first frame image URL (if provided, uses image-to-video mode)
        resolution: Video resolution, e.g., "1080p", "720p" (default: "1080p")
        duration: Video duration in seconds (default: 5)
        camera_fixed: Whether camera is fixed (default: False)
        watermark: Whether to add watermark (default: True)
        upload_to_cos: Whether to upload the generated video to Tencent Cloud COS (default: True)

    Returns:
        The URL of the uploaded video (if COS is enabled) or the local file path.
    """
    logger.info(
        f"🎬 [seedance_generate_video] Called - "
        f"Prompt: '{prompt}', "
        f"Image: '{image_url}', "
        f"Resolution: {resolution}, Duration: {duration}s, "
        f"Camera Fixed: {camera_fixed}, Watermark: {watermark}, Upload: {upload_to_cos}"
    )

    try:
        client = get_seedance_video_client()
        result = client.generate_video(
            prompt=prompt,
            image_url=image_url,
            resolution=resolution,
            duration=duration,
            camera_fixed=camera_fixed,
            watermark=watermark,
            upload_to_cos=upload_to_cos,
        )

        if result["success"]:
            # Return COS URL if available, otherwise return local path
            if result.get("cos_url"):
                logger.info(f"✓ [seedance_generate_video] Video uploaded to COS: {result['cos_url']}")
                return result["cos_url"]
            else:
                logger.info(f"✓ [seedance_generate_video] Video saved locally: {result['local_path']}")
                return result["local_path"]
        else:
            error_msg = f"Failed to generate video: {result.get('error', 'Unknown error')}"
            logger.error(f"❌ [seedance_generate_video] {error_msg}")
            return f"Error: {error_msg}"

    except Exception as e:
        logger.error(f"❌ [seedance_generate_video] Exception: {e}")
        return f"Error: {str(e)}"

