# tools/midjourney.py
import os
import time
import logging
import re
import json
from typing import Dict, Any, Optional, Tuple, Union
from urllib.parse import urlparse
import requests
from langchain.tools import tool

logger = logging.getLogger(__name__)

PROMPT_PATTERN = re.compile(r"^(https?://\S+)\s+(.+)$", re.DOTALL)
PROMPT_FORMAT_HELP = (
    "MidJourney prompt must start with the reference image URL followed by the "
    "full scene description on the same line. Example:\n"
    "https://example.com/reference.jpg A concise but vivid description of the shot with pre-defined palette --ar 16:9"
)


def _canonicalize_midjourney_prompt(raw_prompt: str) -> str:
    """
    Validate and normalize the prompt so it always follows `<reference_url> <description>`.
    """
    if not isinstance(raw_prompt, str):
        raise ValueError("Prompt must be a string.")

    prompt = raw_prompt.strip()
    if not prompt:
        raise ValueError("Prompt cannot be empty.")

    match = PROMPT_PATTERN.match(prompt)
    if not match:
        raise ValueError(PROMPT_FORMAT_HELP)

    reference_url, description = match.groups()
    parsed = urlparse(reference_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Reference image URL must be a valid http(s) URL.")

    cleaned_description = " ".join(description.strip().split())
    if not cleaned_description:
        raise ValueError("Prompt must include descriptive text after the URL.")

    return f"{reference_url} {cleaned_description}"


def _normalize_upscale_inputs(
    task_input: Union[str, Dict[str, Any]],
    index: Optional[int],
) -> Tuple[str, int]:
    """
    Accept slightly malformed inputs (e.g., JSON encoded into task_id) coming from agents
    and normalize them into a proper (task_id, index) tuple.
    """

    def _coerce_index(value: Optional[Any]) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        try:
            coerced = int(str(value).strip())
        except (TypeError, ValueError):
            raise ValueError(f"Index must be an integer, received: {value!r}")
        return coerced

    resolved_task_id: Optional[str] = None
    resolved_index: Optional[int] = _coerce_index(index)

    def _ingest_mapping(mapping: Dict[str, Any]):
        nonlocal resolved_task_id, resolved_index
        if not isinstance(mapping, dict):
            return
        if resolved_task_id is None:
            resolved_task_id = (
                mapping.get("task_id")
                or mapping.get("taskId")
                or mapping.get("taskID")
                or mapping.get("id")
            )
        if resolved_index is None and "index" in mapping:
            resolved_index = _coerce_index(mapping.get("index"))

    if isinstance(task_input, dict):
        _ingest_mapping(task_input)
    elif isinstance(task_input, str):
        candidate = task_input.strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                resolved_task_id = candidate
            else:
                if isinstance(parsed, dict):
                    _ingest_mapping(parsed)
                if resolved_task_id is None and isinstance(parsed, (str, int)):
                    resolved_task_id = str(parsed).strip()
        else:
            resolved_task_id = candidate
    else:
        resolved_task_id = str(task_input).strip()

    if not resolved_task_id:
        raise ValueError("task_id is required but was not provided or could not be parsed.")
    if resolved_index is None:
        raise ValueError("index is required. Provide it separately or include it in the JSON payload.")

    return resolved_task_id, resolved_index


def _submit_imagine_and_poll(canonical_prompt: str) -> Tuple[str, Dict[str, Any]]:
    """Submit an imagine task and block until completion."""
    client = get_midjourney_client()
    submit_response = client.submit_imagine(canonical_prompt)

    code = submit_response.get("code")
    if code not in [1, 21, 22]:
        description = submit_response.get("description", "Unknown error")
        raise RuntimeError(f"Failed to submit imagine task: {description} (code: {code})")

    task_id = submit_response.get("result")
    if not task_id:
        raise RuntimeError("Midjourney imagine response did not include a task ID.")

    if code == 21:
        properties = submit_response.get("properties", {})
        if properties.get("status") == "SUCCESS":
            return task_id, properties

    task = client.poll_task_until_complete(task_id)
    return task_id, task


def _submit_upscale_and_poll(task_id: str, index: int) -> Tuple[str, Dict[str, Any]]:
    """Submit an upscale task and block until completion."""
    client = get_midjourney_client()
    submit_response = client.submit_change(task_id, "UPSCALE", index)

    code = submit_response.get("code")
    if code not in [1, 21, 22]:
        description = submit_response.get("description", "Unknown error")
        raise RuntimeError(f"Failed to submit upscale task: {description} (code: {code})")

    upscale_task_id = submit_response.get("result")
    if not upscale_task_id:
        raise RuntimeError("Midjourney upscale response did not include a task ID.")

    if code == 21:
        properties = submit_response.get("properties", {})
        if properties.get("status") == "SUCCESS":
            return upscale_task_id, properties

    task = client.poll_task_until_complete(upscale_task_id)
    return upscale_task_id, task


def _parse_generate_upscaled_params(
    params: Union[str, Dict[str, Any]]
) -> Tuple[str, int]:
    """Extract prompt and index values for the combined controller tool."""
    prompt_value: Optional[str] = None
    index_value: Optional[Any] = None

    if isinstance(params, dict):
        prompt_value = params.get("prompt")
        index_value = params.get("index")
    elif isinstance(params, str):
        candidate = params.strip()
        if not candidate:
            raise ValueError("Prompt cannot be empty.")
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                prompt_value = candidate
            else:
                if isinstance(parsed, dict):
                    prompt_value = parsed.get("prompt")
                    index_value = parsed.get("index")
                else:
                    prompt_value = str(parsed)
        else:
            prompt_value = candidate
    else:
        prompt_value = str(params).strip()

    if not prompt_value:
        raise ValueError("Prompt is required. Provide it directly or via a JSON payload.")

    if index_value is None:
        index_value = 1

    try:
        index_int = int(index_value)
    except (TypeError, ValueError):
        raise ValueError(f"Index must be an integer between 1-4, received: {index_value!r}")

    if not (1 <= index_int <= 4):
        raise ValueError(f"Index must be between 1-4, received: {index_int}")

    return prompt_value, index_int

# ==================== Configuration ====================
MIDJOURNEY_CONFIG = {
    "poll_interval": 2,  # Poll interval in seconds
    "max_poll_time": 300,  # Maximum poll time (5 minutes)
}


# ==================== Midjourney Client ====================
class MidjourneyClient:
    """Client for interacting with Midjourney Proxy API"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get("MIDJOURNEY_PROXY_BASE_URL")
        if not self.base_url:
            raise ValueError("MIDJOURNEY_PROXY_BASE_URL environment variable is not set")
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

    def poll_task_until_complete(self, task_id: str) -> Dict[str, Any]:
        """Poll task until it's complete (SUCCESS or FAILURE)"""
        logger.info(f"Starting to poll task: {task_id}")
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.max_poll_time:
                raise TimeoutError(f"Task {task_id} exceeded maximum poll time of {self.max_poll_time}s")

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
    logger.info(f"🎨 [midjourney_imagine] Called - Raw Prompt: '{prompt}'")
    
    try:
        canonical_prompt = _canonicalize_midjourney_prompt(prompt)
    except ValueError as format_error:
        logger.error(f"❌ [midjourney_imagine] Invalid prompt: {format_error}")
        return f"Invalid MidJourney prompt: {format_error}"
    
    if canonical_prompt != prompt.strip():
        logger.debug(f"Normalized MidJourney prompt: '{canonical_prompt}'")
    
    try:
        task_id, task = _submit_imagine_and_poll(canonical_prompt)
        logger.info(f"Imagine task completed successfully: task_id={task_id}")
        
        # Extract result information
        image_url = task.get("imageUrl")
        progress = task.get("progress")
        prompt_en = task.get("promptEn", canonical_prompt)
        
        result_text = f"""Image generation completed!

Task ID: {task_id}
Prompt: {canonical_prompt}
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
def midjourney_upscale(task_id: Union[str, Dict[str, Any]], index: Optional[int] = None) -> str:
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
    
    try:
        resolved_task_id, resolved_index = _normalize_upscale_inputs(task_id, index)
    except ValueError as normalize_error:
        logger.error(f"❌ [midjourney_upscale] Invalid inputs: {normalize_error}")
        return f"Error: {normalize_error}"
    
    # Validate index range
    if not (1 <= resolved_index <= 4):
        error_msg = f"Index must be between 1-4, received: {resolved_index}"
        logger.error(f"❌ [midjourney_upscale] {error_msg}")
        return f"Error: {error_msg}"
    
    try:
        upscale_task_id, task = _submit_upscale_and_poll(resolved_task_id, resolved_index)
        logger.info(f"Upscale task completed successfully: task_id={upscale_task_id}")
        
        # Extract result information
        image_url = task.get("imageUrl")
        progress = task.get("progress")
        
        result_text = f"""Image upscale completed!

Original Task ID: {resolved_task_id}
Upscale Task ID: {upscale_task_id}
Selected Index: {resolved_index}
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


@tool("midjourney_generate_upscaled")
def midjourney_generate_upscaled(params: Union[str, Dict[str, Any]]) -> str:
    """Generate and automatically upscale a Midjourney image in one call.

    Args:
        params: Either a raw Midjourney prompt string or a JSON/dict payload with
                {"prompt": "...", "index": 1-4}. The index defaults to 1.

    Returns:
        JSON-formatted string containing imagine and upscale metadata.
    """
    logger.info(f"🧩 [midjourney_generate_upscaled] Called with params: {params}")

    try:
        raw_prompt, upscale_index = _parse_generate_upscaled_params(params)
        canonical_prompt = _canonicalize_midjourney_prompt(raw_prompt)
    except ValueError as format_error:
        logger.error(f"❌ [midjourney_generate_upscaled] Invalid input: {format_error}")
        return f"Error: {format_error}"

    if canonical_prompt != str(raw_prompt).strip():
        logger.debug(f"[midjourney_generate_upscaled] Normalized prompt: '{canonical_prompt}'")

    try:
        imagine_task_id, imagine_task = _submit_imagine_and_poll(canonical_prompt)
        logger.info(f"[midjourney_generate_upscaled] Imagine complete: {imagine_task_id}")

        upscale_task_id, upscale_task = _submit_upscale_and_poll(imagine_task_id, upscale_index)
        logger.info(f"[midjourney_generate_upscaled] Upscale complete: {upscale_task_id}")

        response_payload = {
            "prompt": canonical_prompt,
            "upscale_index": upscale_index,
            "imagine_task_id": imagine_task_id,
            "imagine_image_url": imagine_task.get("imageUrl"),
            "imagine_progress": imagine_task.get("progress"),
            "imagine_prompt_en": imagine_task.get("promptEn", canonical_prompt),
            "upscale_task_id": upscale_task_id,
            "upscaled_image_url": upscale_task.get("imageUrl"),
            "upscale_progress": upscale_task.get("progress"),
        }

        return json.dumps(response_payload, indent=2, ensure_ascii=False)

    except TimeoutError as e:
        logger.error(f"⏱️ [midjourney_generate_upscaled] Timeout: {e}")
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ [midjourney_generate_upscaled] Exception: {e}")
        return f"Error: {str(e)}"

