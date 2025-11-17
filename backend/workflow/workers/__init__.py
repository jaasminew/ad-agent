"""Workers for AD Agent Workflow"""

from .state import WorkflowState, ShotState
from .script_writer import write_ad_script  # Legacy: Simple LLM call
from .script_gen_agent_worker import write_ad_script_with_agent  # NEW: ReAct Agent
from .storyboard_agent_worker import run_storyboard_agent
from .sequential_video_generator import generate_videos_sequentially
from .result_aggregator import aggregate_results
from .video_concatenator import concatenate_videos
from .bgm_generator import generate_and_add_bgm

# Legacy workers (步骤 2-6,已被 Storyboard Agent 替代)
from .style_searcher import search_style_image
from .palette_extractor import extract_palette
from .midjourney_generator import generate_midjourney_image
from .distortion_checker import check_distortion
from .product_composer import compose_with_product
from .video_generator import generate_video

__all__ = [
    "WorkflowState",
    "ShotState",
    "write_ad_script",  # Legacy: Simple LLM call
    "write_ad_script_with_agent",  # NEW: Step 1 - Script Generation Agent (ReAct)
    "run_storyboard_agent",  # NEW: Step 2 - Replaces steps 2-6
    "generate_videos_sequentially",  # NEW: Step 3 - Sequential video generation
    "aggregate_results",
    "concatenate_videos",
    "generate_and_add_bgm",
    # Legacy workers (kept for reference/debugging)
    "search_style_image",
    "extract_palette",
    "generate_midjourney_image",
    "check_distortion",
    "compose_with_product",
    "generate_video",
]
