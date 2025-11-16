# tools/suno_music.py
import os
import time
import logging
import tempfile
import requests
from typing import Optional, List
from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ==================== Configuration ====================
SUNO_CONFIG = {
    "api_base": "https://api.sunoapi.org/api/v1",
    "poll_interval": 10,  # Poll every 10 seconds
    "timeout": 600,  # Maximum wait time in seconds (10 minutes)
    "default_model": "V3_5",
}


# ==================== Suno Music Client ====================
class SunoMusicClient:
    """Client for generating music using Suno API"""

    def __init__(
        self,
        api_token: Optional[str] = None,
    ):
        self.api_token = api_token or os.environ.get("SUNO_API_TOKEN")
        
        if not self.api_token:
            raise ValueError(
                "SUNO_API_TOKEN environment variable must be set"
            )

        self.api_base = SUNO_CONFIG["api_base"]
        logger.info(f"✓ Suno Music client initialized with API: {self.api_base}")

        # Initialize COS uploader (lazy import to avoid dependency if not needed)
        self.cos_uploader = None
        self._cos_available = None

    def _get_headers(self) -> dict:
        """
        Get request headers with authentication.
        
        Returns:
            Dictionary of request headers
        """
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def generate_music(
        self,
        prompt: str,
        style: Optional[str] = None,
        title: Optional[str] = None,
        custom_mode: bool = True,
        instrumental: bool = False,
        model: str = "V3_5",
        negative_tags: Optional[str] = None,
        vocal_gender: Optional[str] = None,
        style_weight: float = 0.65,
        weirdness_constraint: float = 0.65,
        audio_weight: float = 0.65,
        upload_to_cos: bool = True,
    ) -> dict:
        """
        Generate music using Suno API.

        Args:
            prompt: Text description for music generation (e.g., "一段平静舒缓的钢琴曲，带有柔和的旋律")
            style: Music style (e.g., "古典", "流行", "摇滚")
            title: Music title (optional, will be auto-generated if not provided)
            custom_mode: Whether to use custom mode (default: True)
            instrumental: Whether to generate instrumental music without lyrics (default: False)
            model: Model version, "V3_5" or others (default: "V3_5")
            negative_tags: Tags to avoid (e.g., "重金属, 强节奏鼓点")
            vocal_gender: Vocal gender, "m" (male), "f" (female), or None
            style_weight: Style adherence weight, 0.0-1.0 (default: 0.65)
            weirdness_constraint: Control creativity level, 0.0-1.0 (default: 0.65)
            audio_weight: Audio quality weight, 0.0-1.0 (default: 0.65)
            upload_to_cos: Whether to upload the generated music to COS

        Returns:
            Dictionary containing:
            - success: bool
            - task_id: str (Suno task ID)
            - tracks: list (list of generated music tracks with metadata)
            - local_paths: list (paths to saved music files)
            - cos_urls: list (if uploaded to COS)
            - error: str (if failed)
        """
        try:
            # Step 1: Create music generation task
            logger.info(f"Creating Suno music generation task...")
            logger.info(f"  Prompt: {prompt}")
            logger.info(f"  Style: {style}, Model: {model}, Instrumental: {instrumental}")

            create_url = f"{self.api_base}/generate"
            payload = {
                "prompt": prompt,
                "customMode": custom_mode,
                "instrumental": instrumental,
                "model": model,
                "styleWeight": style_weight,
                "weirdnessConstraint": weirdness_constraint,
                "audioWeight": audio_weight,
                "callBackUrl": "https://api.example.com/callback",
            }

            # Add optional parameters
            if style:
                payload["style"] = style
            if title:
                payload["title"] = title
            if negative_tags:
                payload["negativeTags"] = negative_tags
            if vocal_gender:
                payload["vocalGender"] = vocal_gender

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
            if result.get("code") != 200:
                error_msg = f"API error (code {result.get('code')}): {result.get('msg')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                }

            task_id = result["data"]["taskId"]
            logger.info(f"✓ Task created successfully: {task_id}")

            # Step 2: Poll task status until completed
            tracks_data = self._poll_task_status(task_id)
            
            if not tracks_data:
                return {
                    "success": False,
                    "error": "Failed to get music tracks from task result",
                }

            # Step 3: Download music files
            local_paths = []
            tracks_info = []
            
            for idx, track in enumerate(tracks_data):
                audio_url = track.get("audioUrl")
                if not audio_url:
                    logger.warning(f"No audio URL for track {idx}")
                    continue
                
                logger.info(f"Downloading music track {idx + 1}/{len(tracks_data)} from: {audio_url}")
                
                try:
                    audio_response = requests.get(audio_url, timeout=120)
                    audio_response.raise_for_status()

                    # Save music locally
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    temp_dir = tempfile.gettempdir()
                    track_title = track.get("title", f"track_{idx}").replace(" ", "_")
                    local_path = os.path.join(temp_dir, f"suno_music_{timestamp}_{track_title}.mp3")
                    
                    with open(local_path, "wb") as f:
                        f.write(audio_response.content)
                    
                    logger.info(f"✓ Music track saved locally: {local_path}")
                    local_paths.append(local_path)
                    
                    # Store track info
                    tracks_info.append({
                        "id": track.get("id"),
                        "title": track.get("title"),
                        "duration": track.get("duration"),
                        "tags": track.get("tags"),
                        "prompt": track.get("prompt"),
                        "local_path": local_path,
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to download track {idx}: {e}")
                    continue

            if not local_paths:
                return {
                    "success": False,
                    "error": "Failed to download any music tracks",
                }

            result = {
                "success": True,
                "task_id": task_id,
                "tracks": tracks_info,
                "local_paths": local_paths,
            }

            # Step 4: Upload to COS if enabled
            if upload_to_cos:
                cos_urls = []
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
                        for local_path in local_paths:
                            # Generate COS key with suno prefix
                            filename = Path(local_path).name
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            cos_key = f"suno/{timestamp}_{filename}"
                            
                            cos_url = self.cos_uploader.upload_file(local_path, cos_key=cos_key)
                            cos_urls.append(cos_url)
                            logger.info(f"✓ Music uploaded to COS: {cos_url}")
                        
                        result["cos_urls"] = cos_urls
                    else:
                        result["cos_upload_error"] = "COS credentials not configured"
                        
                except Exception as e:
                    logger.error(f"Failed to upload to COS: {e}")
                    result["cos_upload_error"] = str(e)

            return result

        except Exception as e:
            logger.error(f"Error generating music: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _poll_task_status(self, task_id: str) -> Optional[List[dict]]:
        """
        Poll task status until it's completed or failed.

        Args:
            task_id: Suno task ID

        Returns:
            List of track data if successful, None if failed
        """
        query_url = f"{self.api_base}/generate/record-info"
        start_time = time.time()
        timeout = SUNO_CONFIG["timeout"]
        poll_interval = SUNO_CONFIG["poll_interval"]

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"Task polling timed out after {timeout} seconds")
                return None

            try:
                # Query task status - note: API may require task_id as query parameter
                response = requests.get(
                    query_url,
                    headers=self._get_headers(),
                    params={"taskId": task_id},
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") != 200:
                    logger.error(f"Query task error: {result.get('msg')}")
                    return None

                data = result.get("data", {})
                task_status = data.get("status")
                logger.info(f"Task status: {task_status} (elapsed: {int(elapsed)}s)")

                # Check status
                if task_status == "SUCCESS":
                    # Extract music tracks
                    response_data = data.get("response", {})
                    tracks = response_data.get("sunoData", [])
                    
                    if tracks and len(tracks) > 0:
                        logger.info(f"✓ Music generation succeeded! Generated {len(tracks)} track(s)")
                        return tracks
                    else:
                        logger.error("No tracks found in result")
                        return None

                elif task_status in ["CREATE_TASK_FAILED", "GENERATE_AUDIO_FAILED", "SENSITIVE_WORD_ERROR"]:
                    error_msg = data.get("errorMessage", task_status)
                    logger.error(f"Task failed: {error_msg}")
                    return None

                elif task_status in ["PENDING", "TEXT_SUCCESS", "FIRST_SUCCESS"]:
                    # Continue polling
                    status_desc = {
                        "PENDING": "任务正在等待处理",
                        "TEXT_SUCCESS": "歌词/文本生成已完成",
                        "FIRST_SUCCESS": "第一首曲目已完成",
                    }.get(task_status, task_status)
                    logger.info(f"Waiting for music generation to complete... ({status_desc})")
                    time.sleep(poll_interval)

                else:
                    logger.warning(f"Unknown task status: {task_status}")
                    time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling task status: {e}")
                time.sleep(poll_interval)


# Lazy initialization of Suno Music client
_suno_music_client = None


def get_suno_music_client() -> SunoMusicClient:
    """Get or create the Suno Music client singleton"""
    global _suno_music_client
    if _suno_music_client is None:
        _suno_music_client = SunoMusicClient()
    return _suno_music_client


# ==================== LangChain Tools ====================

@tool("suno_generate_music")
def suno_generate_music(
    prompt: str,
    style: Optional[str] = None,
    title: Optional[str] = None,
    instrumental: bool = False,
    model: str = "V3_5",
    upload_to_cos: bool = True,
) -> str:
    """Generate music using Suno AI API.
    The generated music will be saved locally and optionally uploaded to Tencent Cloud COS.

    This tool is perfect for creating background music, soundtracks, or any audio content.
    Suno AI can generate music in various styles with or without lyrics.

    Args:
        prompt: Text description for music generation (e.g., "一段平静舒缓的钢琴曲，带有柔和的旋律")
        style: Music style (e.g., "古典", "流行", "摇滚", "电子", "爵士")
        title: Music title (optional, will be auto-generated if not provided)
        instrumental: Whether to generate instrumental music without lyrics (default: False)
        model: Model version, "V3_5" or others (default: "V3_5")
        upload_to_cos: Whether to upload the generated music to Tencent Cloud COS (default: True)

    Returns:
        The URLs of the uploaded music (if COS is enabled) or the local file paths.
        Note: Suno typically generates 2 variations of music per request.
    """
    logger.info(
        f"🎵 [suno_generate_music] Called - "
        f"Prompt: '{prompt}', Style: '{style}', Title: '{title}', "
        f"Instrumental: {instrumental}, Model: {model}, Upload: {upload_to_cos}"
    )

    try:
        client = get_suno_music_client()
        result = client.generate_music(
            prompt=prompt,
            style=style,
            title=title,
            instrumental=instrumental,
            model=model,
            upload_to_cos=upload_to_cos,
        )

        if result["success"]:
            tracks = result.get("tracks", [])
            output_lines = [f"Successfully generated {len(tracks)} music track(s):\n"]
            
            for idx, track in enumerate(tracks, 1):
                output_lines.append(f"\nTrack {idx}:")
                output_lines.append(f"  Title: {track.get('title', 'N/A')}")
                output_lines.append(f"  Duration: {track.get('duration', 0):.2f}s")
                output_lines.append(f"  Tags: {track.get('tags', 'N/A')}")
                
                # Return COS URL if available, otherwise return local path
                if result.get("cos_urls") and idx <= len(result["cos_urls"]):
                    cos_url = result["cos_urls"][idx - 1]
                    output_lines.append(f"  URL: {cos_url}")
                else:
                    output_lines.append(f"  Local Path: {track['local_path']}")
            
            output = "\n".join(output_lines)
            logger.info(f"✓ [suno_generate_music] {output}")
            return output
        else:
            error_msg = f"Failed to generate music: {result.get('error', 'Unknown error')}"
            logger.error(f"❌ [suno_generate_music] {error_msg}")
            return f"Error: {error_msg}"

    except Exception as e:
        logger.error(f"❌ [suno_generate_music] Exception: {e}")
        return f"Error: {str(e)}"

