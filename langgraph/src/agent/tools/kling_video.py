# tools/kling_video.py
import os
import time
import logging
import tempfile
import jwt
import requests
from typing import Optional
from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ==================== Configuration ====================
KLING_CONFIG = {
    "api_base": "https://api-beijing.klingai.com",
    "model_name": "kling-v1",
    "mode": "pro",  # or "std"
    "duration": "5",  # 5 or 10 seconds
    "poll_interval": 10,  # Poll every 10 seconds
    "timeout": 600,  # Maximum wait time in seconds (10 minutes)
    "cfg_scale": 0.5,  # 0.0-1.0, controls adherence to prompt
}


# ==================== Kling Video Client ====================
class KlingVideoClient:
    """Client for generating videos using Kling AI image2video API"""

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        self.access_key = access_key or os.environ.get("KLING_ACCESS_KEY")
        self.secret_key = secret_key or os.environ.get("KLING_SECRET_KEY")
        
        if not self.access_key or not self.secret_key:
            raise ValueError(
                "KLING_ACCESS_KEY and KLING_SECRET_KEY environment variables must be set"
            )

        self.api_base = KLING_CONFIG["api_base"]
        logger.info(f"✓ Kling Video client initialized with API: {self.api_base}")

        # Initialize COS uploader (lazy import to avoid dependency if not needed)
        self.cos_uploader = None
        self._cos_available = None

    def _generate_token(self) -> str:
        """
        Generate JWT token for API authentication.
        
        Returns:
            JWT token string
        """
        headers = {
            "alg": "HS256",
            "typ": "JWT"
        }
        payload = {
            "iss": self.access_key,
            "exp": int(time.time()) + 1800,  # Valid for 30 minutes
            "nbf": int(time.time()) - 5  # Start 5 seconds ago
        }
        token = jwt.encode(payload, self.secret_key, headers=headers)
        return token

    def _get_headers(self) -> dict:
        """
        Get request headers with authentication.
        
        Returns:
            Dictionary of request headers
        """
        token = self._generate_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def generate_video(
        self,
        image_url: str,
        prompt: str,
        duration: str = "5",
        mode: str = "pro",
        cfg_scale: float = 0.5,
        upload_to_cos: bool = True,
    ) -> dict:
        """
        Generate video from image using Kling AI API.

        Args:
            image_url: URL of the input image
            prompt: Text description for video generation
            duration: Video duration, "5" or "10" seconds (default: "5")
            mode: Generation mode, "pro" or "std" (default: "pro")
            cfg_scale: Control adherence to prompt, 0.0-1.0 (default: 0.5)
            upload_to_cos: Whether to upload the generated video to COS

        Returns:
            Dictionary containing:
            - success: bool
            - task_id: str (Kling task ID)
            - local_path: str (path to saved video)
            - cos_url: str (if uploaded to COS)
            - error: str (if failed)
        """
        try:
            # Step 1: Create video generation task
            logger.info(f"Creating Kling video generation task...")
            logger.info(f"  Image: {image_url}")
            logger.info(f"  Prompt: {prompt}")
            logger.info(f"  Duration: {duration}s, Mode: {mode}, CFG Scale: {cfg_scale}")

            create_url = f"{self.api_base}/v1/videos/image2video"
            payload = {
                "model_name": KLING_CONFIG["model_name"],
                "mode": mode,
                "duration": duration,
                "image": image_url,
                "prompt": prompt,
                "cfg_scale": cfg_scale,
            }

            response = requests.post(
                create_url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )

            # Check for HTTP errors
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Failed to create task: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                }

            result = response.json()
            
            # Check for API errors
            if result.get("code") != 0:
                error_msg = f"API error (code {result.get('code')}): {result.get('message')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                }

            task_id = result["data"]["task_id"]
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
            local_path = os.path.join(temp_dir, f"kling_video_{timestamp}.mp4")
            
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
                        from agent.utils import COSUploader, is_cos_available
                        
                        if is_cos_available():
                            self.cos_uploader = COSUploader()
                            self._cos_available = True
                        else:
                            self._cos_available = False
                            logger.warning("COS credentials not configured")
                    
                    if self._cos_available and self.cos_uploader:
                        # Generate COS key with kling prefix
                        filename = Path(local_path).name
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        cos_key = f"kling/{timestamp}_{filename}"
                        
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
            task_id: Kling task ID

        Returns:
            Video URL if successful, None if failed
        """
        query_url = f"{self.api_base}/v1/videos/image2video/{task_id}"
        start_time = time.time()
        timeout = KLING_CONFIG["timeout"]
        poll_interval = KLING_CONFIG["poll_interval"]

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"Task polling timed out after {timeout} seconds")
                return None

            try:
                response = requests.get(
                    query_url,
                    headers=self._get_headers(),
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") != 0:
                    logger.error(f"Query task error: {result.get('message')}")
                    return None

                task_status = result["data"]["task_status"]
                logger.info(f"Task status: {task_status} (elapsed: {int(elapsed)}s)")

                if task_status == "succeed":
                    # Extract video URL
                    videos = result["data"]["task_result"]["videos"]
                    if videos and len(videos) > 0:
                        video_url = videos[0]["url"]
                        logger.info(f"✓ Video generation succeeded!")
                        return video_url
                    else:
                        logger.error("No videos found in result")
                        return None

                elif task_status == "failed":
                    error_msg = result["data"].get("task_status_msg", "Unknown error")
                    logger.error(f"Task failed: {error_msg}")
                    return None

                elif task_status in ["submitted", "processing"]:
                    # Continue polling
                    logger.info(f"Waiting for video generation to complete...")
                    time.sleep(poll_interval)

                else:
                    logger.warning(f"Unknown task status: {task_status}")
                    time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling task status: {e}")
                time.sleep(poll_interval)


# Lazy initialization of Kling Video client
_kling_video_client = None


def get_kling_video_client() -> KlingVideoClient:
    """Get or create the Kling Video client singleton"""
    global _kling_video_client
    if _kling_video_client is None:
        _kling_video_client = KlingVideoClient()
    return _kling_video_client


# ==================== LangChain Tools ====================

@tool("kling_generate_video")
def kling_generate_video(
    image_url: str,
    prompt: str,
    duration: str = "5",
    mode: str = "pro",
    cfg_scale: float = 0.5,
    upload_to_cos: bool = True,
) -> str:
    """Generate a video from an image using Kling AI image2video API.
    The generated video will be saved locally and optionally uploaded to Tencent Cloud COS.

    This tool is perfect for creating videos from a single image with text descriptions.
    Kling AI specializes in high-quality video generation with good motion coherence.
    
    The image must be provided as a web URL (http/https), not a local file path.

    Args:
        image_url: URL of the input image (must be a web URL, not local path)
        prompt: Text description for the video generation. Be creative and detailed!
        duration: Video duration, "5" or "10" seconds (default: "5")
        mode: Generation mode, "pro" (higher quality) or "std" (faster) (default: "pro")
        cfg_scale: Control adherence to prompt, 0.0-1.0, higher = more faithful to prompt (default: 0.5)
        upload_to_cos: Whether to upload the generated video to Tencent Cloud COS (default: True)

    Returns:
        The URL of the uploaded video (if COS is enabled) or the local file path.
    """
    logger.info(
        f"🎬 [kling_generate_video] Called - "
        f"Image: '{image_url}', Prompt: '{prompt}', "
        f"Duration: {duration}s, Mode: {mode}, CFG: {cfg_scale}, Upload: {upload_to_cos}"
    )

    try:
        client = get_kling_video_client()
        result = client.generate_video(
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            mode=mode,
            cfg_scale=cfg_scale,
            upload_to_cos=upload_to_cos,
        )

        if result["success"]:
            # Return COS URL if available, otherwise return local path
            if result.get("cos_url"):
                logger.info(f"✓ [kling_generate_video] Video uploaded to COS: {result['cos_url']}")
                return result["cos_url"]
            else:
                logger.info(f"✓ [kling_generate_video] Video saved locally: {result['local_path']}")
                return result["local_path"]
        else:
            error_msg = f"Failed to generate video: {result.get('error', 'Unknown error')}"
            logger.error(f"❌ [kling_generate_video] {error_msg}")
            return f"Error: {error_msg}"

    except Exception as e:
        logger.error(f"❌ [kling_generate_video] Exception: {e}")
        return f"Error: {str(e)}"

