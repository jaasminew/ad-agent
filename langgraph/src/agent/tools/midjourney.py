# tools/midjourney.py
import os
import time
import logging
from typing import Dict, Any, Optional
import requests
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ==================== Configuration ====================
MIDJOURNEY_CONFIG = {
    "poll_interval": 2,  # Poll interval in seconds
    "max_poll_time": 180,  # Maximum poll time (3 minutes) for image generation
}


# ==================== Midjourney Client ====================
class MidjourneyClient:
    """Client for interacting with Midjourney Proxy API"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get("MIDJOURNEY_PROXY_BASE_URL")
        if not self.base_url:
            raise ValueError("MIDJOURNEY_PROXY_BASE_URL environment variable is not set")
        
        # Add https:// if no scheme is present
        if not self.base_url.startswith(("http://", "https://")):
            self.base_url = f"https://{self.base_url}"
        
        self.base_url = self.base_url.rstrip("/")
        self.poll_interval = MIDJOURNEY_CONFIG["poll_interval"]
        self.max_poll_time = MIDJOURNEY_CONFIG["max_poll_time"]
        logger.info(f"✓ Midjourney client initialized with base_url: {self.base_url}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Midjourney Proxy API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def submit_imagine(self, prompt: str) -> Dict[str, Any]:
        """Submit an imagine task"""
        logger.info(f"Submitting imagine task with prompt: {prompt}")
        return self._make_request(
            "POST",
            "/mj/submit/imagine",
            json={"prompt": prompt},
            headers={"Content-Type": "application/json"}
        )

    def submit_change(self, task_id: str, action: str, index: Optional[int] = None) -> Dict[str, Any]:
        """Submit a change task (UPSCALE, VARIATION, REROLL)"""
        logger.info(f"Submitting change task: action={action}, task_id={task_id}, index={index}")
        payload = {
            "taskId": task_id,
            "action": action,
        }
        if index is not None:
            payload["index"] = index
        return self._make_request(
            "POST",
            "/mj/submit/change",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

    def fetch_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Fetch task status by ID"""
        logger.info(f"Fetching task status: {task_id}")
        return self._make_request("GET", f"/mj/task/{task_id}/fetch")

    def poll_task_until_complete(self, task_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Poll task until it's complete (SUCCESS or FAILURE)
        
        Args:
            task_id: The task ID to poll
            timeout: Maximum time to wait in seconds (default: self.max_poll_time)
        """
        logger.info(f"Starting to poll task: {task_id}")
        start_time = time.time()
        max_time = timeout if timeout is not None else self.max_poll_time

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_time:
                raise TimeoutError(f"Task {task_id} exceeded maximum poll time of {max_time}s")

            task = self.fetch_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            status = task.get("status")
            progress = task.get("progress", "N/A")
            logger.info(f"Task {task_id} status: {status}, progress: {progress}")

            if status == "SUCCESS":
                logger.info(f"Task {task_id} completed successfully")
                return task
            elif status == "FAILURE":
                fail_reason = task.get("failReason", "Unknown error")
                logger.error(f"Task {task_id} failed: {fail_reason}")
                raise RuntimeError(f"Task failed: {fail_reason}")

            # Status is NOT_START, SUBMITTED, or IN_PROGRESS
            time.sleep(self.poll_interval)


# Lazy initialization of Midjourney client
_midjourney_client = None


def get_midjourney_client() -> MidjourneyClient:
    """Get or create the Midjourney client singleton"""
    global _midjourney_client
    if _midjourney_client is None:
        _midjourney_client = MidjourneyClient()
    return _midjourney_client


# ==================== LangChain Tools ====================

@tool("midjourney_imagine")
def midjourney_imagine(prompt: str) -> str:
    """Generate an image using Midjourney. This is a synchronous operation that polls until the task completes.
    Returns the task ID and image URL.
    
    Args:
        prompt: The prompt to generate the image. Can include Midjourney parameters like --ar 16:9, --v 6, etc.
    
    Returns:
        A string containing task information including task ID and image URL.
    """
    logger.info(f"🎨 [midjourney_imagine] Called - Prompt: '{prompt}'")
    
    try:
        client = get_midjourney_client()
        
        # Submit the imagine task
        submit_response = client.submit_imagine(prompt)
        
        # Check if submission was successful
        code = submit_response.get("code")
        if code not in [1, 21, 22]:
            # Handle error codes
            description = submit_response.get("description", "Unknown error")
            logger.error(f"Failed to submit imagine task: code={code}, description={description}")
            return f"Failed to submit task: {description} (code: {code})"
        
        task_id = submit_response.get("result")
        logger.info(f"Imagine task submitted successfully: task_id={task_id}")
        
        # If task already exists and is complete (code 21)
        if code == 21:
            properties = submit_response.get("properties", {})
            if properties.get("status") == "SUCCESS":
                image_url = properties.get("imageUrl")
                return f"Task already exists and completed.\nTask ID: {task_id}\nImage URL: {image_url}"
        
        # Poll until the task completes
        task = client.poll_task_until_complete(task_id)
        
        # Extract result information
        image_url = task.get("imageUrl")
        progress = task.get("progress")
        prompt_en = task.get("promptEn", prompt)
        
        result_text = f"""Image generation completed!

Task ID: {task_id}
Prompt: {prompt}
English Prompt: {prompt_en}
Progress: {progress}
Image URL: {image_url}

You can now use the task ID with midjourney_upscale to select and upscale one of the 4 images (index 1-4)."""
        
        logger.info(f"✓ [midjourney_imagine] Image generation successful")
        return result_text
        
    except TimeoutError as e:
        logger.error(f"❌ [midjourney_imagine] Timeout: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ [midjourney_imagine] Exception: {e}")
        return f"Error: {str(e)}"


@tool("midjourney_upscale")
def midjourney_upscale(task_id: str, index: int) -> str:
    """Upscale a specific image from a completed Midjourney task. The original task generates 4 images,
    and you can select one by index (1-4) to upscale. This is a synchronous operation that polls until
    the upscale completes.
    
    Args:
        task_id: The task ID from a completed imagine/variation/reroll task. You can get this from
                 the midjourney_imagine result.
        index: The index of the image to upscale (1-4). Each task generates 4 images arranged in a 2x2 grid:
               1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right.
    
    Returns:
        Upscaled image information including the new task ID and image URL.
    """
    logger.info(f"🔍 [midjourney_upscale] Called - task_id: '{task_id}', index: {index}")
    
    # Validate index range
    if not (1 <= index <= 4):
        error_msg = f"Index must be between 1-4, received: {index}"
        logger.error(f"❌ [midjourney_upscale] {error_msg}")
        return f"Error: {error_msg}"
    
    try:
        client = get_midjourney_client()
        
        # Submit the upscale task
        submit_response = client.submit_change(task_id, "UPSCALE", index)
        
        # Check if submission was successful
        code = submit_response.get("code")
        if code not in [1, 21, 22]:
            # Handle error codes
            description = submit_response.get("description", "Unknown error")
            logger.error(f"Failed to submit upscale task: code={code}, description={description}")
            return f"Failed to submit upscale task: {description} (code: {code})"
        
        upscale_task_id = submit_response.get("result")
        logger.info(f"Upscale task submitted successfully: task_id={upscale_task_id}")
        
        # If task already exists and is complete (code 21)
        if code == 21:
            properties = submit_response.get("properties", {})
            if properties.get("status") == "SUCCESS":
                image_url = properties.get("imageUrl")
                return f"Upscale task already exists and completed.\nTask ID: {upscale_task_id}\nImage URL: {image_url}"
        
        # Poll until the task completes
        task = client.poll_task_until_complete(upscale_task_id)
        
        # Extract result information
        image_url = task.get("imageUrl")
        progress = task.get("progress")
        
        result_text = f"""Image upscale completed!

Original Task ID: {task_id}
Upscale Task ID: {upscale_task_id}
Selected Index: {index}
Progress: {progress}
Upscaled Image URL: {image_url}"""
        
        logger.info(f"✓ [midjourney_upscale] Image upscale successful")
        return result_text
        
    except TimeoutError as e:
        logger.error(f"❌ [midjourney_upscale] Timeout: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ [midjourney_upscale] Exception: {e}")
        return f"Error: {str(e)}"

