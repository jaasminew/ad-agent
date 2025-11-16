"""State definition for AD Agent Workflow"""

from typing import TypedDict, List, Tuple, Annotated, Dict, Any
from operator import add


class WorkflowState(TypedDict, total=False):
    """
    State for the AD Agent Workflow (main workflow).
    
    Initial inputs:
    - product_name: Product name
    - brand_identity: Brand positioning
    - product_images: Product image URL
    - must_have_shots: Required shots (comma-separated)
    - generate_video: Whether to generate video (from environment variable)
    
    Intermediate states:
    - shots: List of shot descriptions
    - episode_result: EpisodeResult from Storyboard Agent (NEW)
    - nanobanana_images: List of final composed image URLs (NEW)
    - shot_results: List of results for each shot (for video generation)
    
    Messages for logging/debugging:
    - messages: List of workflow messages (logs output from each step)
    """
    
    # === Initial inputs ===
    product_name: str
    brand_identity: str
    product_images: str
    must_have_shots: str
    generate_video: bool  # Control whether to generate video
    
    # === Intermediate states ===
    shots: List[str]
    episode_result: Any  # EpisodeResult from Storyboard Agent (step 2)
    nanobanana_images: List[str]  # Final composed images from Storyboard Agent
    shot_results: List[Dict[str, Any]]  # Each shot's video result (step 3)
    
    # === Aggregated results ===
    aggregated_summary: Dict[str, Any]  # Summary of all results
    final_outputs: List[Dict[str, Any]]  # Final outputs for each shot
    
    # === Final video ===
    final_video_url: str  # URL of concatenated final video (only if generate_video=True)
    video_duration: float  # Duration of final video in seconds
    
    # === BGM (Background Music) ===
    music_prompt: str  # Generated music prompt
    music_style: str  # Music style (e.g., "电子", "古典")
    bgm_url: str  # URL of generated background music
    final_video_with_bgm_url: str  # URL of final video with BGM
    
    # === Message logs ===
    # Use Annotated with add operator to accumulate messages
    messages: Annotated[List[str], add]


class ShotState(TypedDict, total=False):
    """
    State for processing a single shot (sub-workflow).
    
    This represents the state for one shot going through steps 2-7.
    """
    
    # === Inputs (from parent workflow) ===
    shot: str  # Single shot description
    shot_index: int  # Index of this shot in the shots list
    product_name: str
    brand_identity: str
    product_images: str
    generate_video: bool  # Whether to generate video
    
    # === Context for smooth transitions ===
    previous_shot: str  # Previous shot description (if exists)
    next_shot: str  # Next shot description (if exists)
    
    # === Intermediate states ===
    style_image_url: str
    palette: List[Tuple[int, int, int]]
    midjourney_task_id: str
    midjourney_image_url: str
    midjourney_retry_count: int  # Number of retries due to sensitive words
    distortion_check_result: dict
    distortion_retry_count: int
    nanobanana_image_url: str
    
    # === Video generation (optional) ===
    video_prompt: str  # Video prompt (always generated)
    video_url: str  # Video URL (only if generate_video=True)
    
    # === Message logs ===
    messages: Annotated[List[str], add]
