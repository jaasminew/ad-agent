"""State definition for AD Agent Workflow"""

from typing import TypedDict, List, Tuple, Annotated
from operator import add


class WorkflowState(TypedDict, total=False):
    """
    State for the AD Agent Workflow.
    
    Initial inputs:
    - product_name: Product name
    - brand_identity: Brand positioning
    - product_images: Product image URL
    - must_have_shots: Required shots (comma-separated)
    
    Intermediate states:
    - shots: List of shot descriptions
    - style_image_url: Style reference image URL
    - palette: Dominant colors as list of RGB tuples
    - midjourney_task_id: Midjourney task ID
    - midjourney_image_url: Midjourney generated image URL
    - distortion_check_result: Distortion check result dict
    - distortion_retry_count: Number of retries for distortion issues
    - nanobanana_image_url: Nanobanana composed image URL
    - video_url: Final generated video URL
    
    Messages for logging/debugging:
    - messages: List of workflow messages (logs output from each step)
    """
    
    # === Initial inputs ===
    product_name: str
    brand_identity: str
    product_images: str
    must_have_shots: str
    
    # === Intermediate states ===
    shots: List[str]
    style_image_url: str
    palette: List[Tuple[int, int, int]]
    midjourney_task_id: str
    midjourney_image_url: str
    distortion_check_result: dict
    distortion_retry_count: int
    nanobanana_image_url: str
    video_url: str
    
    # === Message logs ===
    # Use Annotated with add operator to accumulate messages
    messages: Annotated[List[str], add]
