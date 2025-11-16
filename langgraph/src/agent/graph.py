"""AD Agent Workflow - Generate advertising videos using AI with LangGraph.

This graph defines a complete workflow for generating advertising videos:
1. Script Writing: Generate ad script based on product info
2. Style Search: Find reference style images
3. Palette Extraction: Extract color palette
4. Image Generation: Generate images via Midjourney
5. Distortion Check: Verify image quality
6. Product Composition: Compose with product images
7. Video Generation: Generate videos from composed images
8. Result Aggregation: Collect all results
9. Video Concatenation: Combine all videos
10. BGM Generation: Add background music
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

from agent.workers import (
    WorkflowState,
    ShotState,
    write_ad_script,
    search_style_image,
    extract_palette,
    generate_midjourney_image,
    check_distortion,
    compose_with_product,
    generate_video as generate_video_node,
    aggregate_results,
    concatenate_videos,
    generate_and_add_bgm,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==================== Runtime Context ====================

class Context(TypedDict):
    """Runtime context parameters for the AD Agent.

    Set these when creating assistants OR when invoking the graph.
    See: https://docs.langchain.com/oss/python/langgraph/add-memory
    
    These parameters can be configured per-invocation to customize behavior:
    - Product information (name, brand, images)
    - Video generation settings
    - Required shots/scenes
    - Number of shots to generate
    """
    
    product_name: str
    """Product name to generate ads for"""
    
    brand_identity: str
    """Brand identity/values/positioning"""
    
    product_images: str
    """Product image URL(s)"""
    
    must_have_shots: str
    """Required shots/scenes (comma-separated)"""
    
    num_shots: int
    """Number of shots to generate (default: 3)"""
    
    generate_video: bool
    """Whether to generate actual videos (default: False)"""
    
    video_model: str
    """Video generation model: 'veo', 'kling', or 'seedance' (default: 'veo')"""


class InputState(TypedDict):
    """Input state for the workflow.
    
    This defines what users can provide when invoking the graph.
    Only includes initial input fields, not intermediate state.
    """
    
    product_name: str
    """Product name to generate ads for"""
    
    brand_identity: str
    """Brand identity/values/positioning"""
    
    product_images: str
    """Product image URL(s)"""
    
    must_have_shots: str
    """Required shots/scenes (comma-separated)"""
    
    num_shots: int
    """Number of shots to generate (default: 3)"""
    
    generate_video: bool
    """Whether to generate actual videos (default: False)"""
    
    video_model: str
    """Video generation model: 'veo', 'kling', or 'seedance' (default: 'veo')"""


# ==================== Single Shot Workflow ====================

def build_shot_workflow() -> StateGraph:
    """
    Build workflow for processing a single shot (steps 2-7).
    
    This sub-workflow handles:
    - Style image search
    - Color palette extraction
    - Midjourney image generation (with retry on distortion)
    - Distortion checking
    - Product composition
    - Video generation
    """
    graph = StateGraph(ShotState)
    
    # Add nodes for single shot processing
    graph.add_node("search_style", search_style_image)
    graph.add_node("extract_palette", extract_palette)
    graph.add_node("generate_image", generate_midjourney_image)
    graph.add_node("check_distortion", check_distortion)
    graph.add_node("compose_product", compose_with_product)
    graph.add_node("generate_video", generate_video_node)
    
    # Build linear flow with conditional loop for distortion check
    graph.add_edge(START, "search_style")
    graph.add_edge("search_style", "extract_palette")
    graph.add_edge("extract_palette", "generate_image")
    graph.add_edge("generate_image", "check_distortion")
    
    # Conditional edge: retry if distortion detected
    def should_retry_midjourney(state: ShotState) -> str:
        max_retries = 3
        retry_count = state.get("distortion_retry_count", 0)
        check_result = state.get("distortion_check_result", {})
        has_distortion = check_result.get("has_distortion", False)
        
        if has_distortion and retry_count < max_retries:
            logger.warning("Distortion detected, retrying Midjourney (attempt %d/%d)", retry_count, max_retries)
            return "retry"
        elif has_distortion and retry_count >= max_retries:
            logger.warning("Max retries reached, proceeding despite distortion")
            return "compose"
        else:
            logger.info("No distortion detected, proceeding to composition")
            return "compose"
    
    graph.add_conditional_edges(
        "check_distortion",
        should_retry_midjourney,
        {
            "retry": "generate_image",
            "compose": "compose_product"
        }
    )
    
    graph.add_edge("compose_product", "generate_video")
    graph.add_edge("generate_video", END)
    
    return graph


# ==================== Main Workflow with Fan-out/Fan-in ====================

def process_single_shot_wrapper(state: ShotState) -> Dict[str, Any]:
    """
    Wrapper function that executes the shot workflow and formats the result.
    
    This wrapper:
    1. Takes a ShotState as input (dispatched via Send)
    2. Runs it through the shot processing subgraph
    3. Returns the result in WorkflowState format for aggregation
    """
    shot_index = state.get("shot_index", 0)
    shot = state.get("shot", "")
    
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Processing Shot {shot_index + 1}")
    logger.info(f"{'=' * 80}")
    logger.info(f"Shot description: {shot}")
    
    # Build and execute shot workflow
    shot_workflow = build_shot_workflow().compile()
    result = shot_workflow.invoke(state)
    
    logger.info(f"\n✓ Shot {shot_index + 1} completed")
    if result.get("generate_video") and result.get("video_url"):
        logger.info(f"  Video: {result.get('video_url')}")
    else:
        logger.info(f"  Video prompt: {result.get('video_prompt', 'N/A')[:80]}...")
        logger.info(f"  Composed image: {result.get('nanobanana_image_url', 'N/A')}")
    
    # Return result in WorkflowState format
    # The reducer will merge this with other shot results
    return {
        "shot_results": [result]
    }


def fan_out_shots(state: WorkflowState, runtime: Runtime[Context]):
    """
    Fan-out: Create parallel tasks for each shot.
    
    This function uses LangGraph's Send API to dispatch each shot
    to the shot processing subgraph for parallel execution.
    """
    # Get context parameters
    context = runtime.context or {}
    
    logger.info("\n" + "=" * 80)
    logger.info("Fan-out: Dispatching shots for parallel processing")
    logger.info("=" * 80)
    
    shots = state["shots"]
    product_name = state.get("product_name") or context.get("product_name", "")
    brand_identity = state.get("brand_identity") or context.get("brand_identity", "")
    product_images = state.get("product_images") or context.get("product_images", "")
    generate_video_flag = state.get("generate_video", context.get("generate_video", False))
    video_model = state.get("video_model") or context.get("video_model", "veo")
    
    logger.info(f"Total shots to dispatch: {len(shots)}")
    logger.info(f"Video generation: {'ENABLED' if generate_video_flag else 'DISABLED'}")
    logger.info(f"Video model: {video_model.upper()}")
    
    # Create Send tasks for each shot
    sends = []
    for i, shot in enumerate(shots):
        logger.info(f"  Dispatching shot {i+1}: {shot[:60]}...")
        
        # Determine previous and next shots for smooth transitions
        previous_shot = shots[i-1] if i > 0 else None
        next_shot = shots[i+1] if i < len(shots) - 1 else None
        
        # Create initial state for this shot
        shot_state: ShotState = {
            "shot": shot,
            "shot_index": i,
            "product_name": product_name,
            "brand_identity": brand_identity,
            "product_images": product_images,
            "generate_video": generate_video_flag,
            "video_model": video_model,
            "previous_shot": previous_shot,
            "next_shot": next_shot,
            "distortion_retry_count": 0,
            "midjourney_retry_count": 0,
            "messages": [],
        }
        
        # Send this shot to the process_single_shot subgraph
        sends.append(Send("process_single_shot", shot_state))
    
    return sends


# ==================== Build Main Application Graph ====================

def build_graph() -> StateGraph:
    """
    Build the main AD Agent workflow graph with runtime context support.
    
    The workflow consists of:
    1. Script writing
    2. Fan-out: Dispatch shots for parallel processing
    3. Shot processing subgraph: Each shot goes through complete workflow
       - Style search → Palette extraction → Midjourney → Distortion check → 
         Product composition → Video generation
    4. Fan-in: Aggregate results (automatic via state reducer)
    5. Video concatenation
    6. BGM generation and addition
    
    Runtime context allows configuring product info and video settings per invocation.
    InputState defines user inputs, WorkflowState tracks internal state.
    """
    graph = StateGraph(WorkflowState, input=InputState, context_schema=Context)
    
    # Add nodes
    graph.add_node("write_script", write_ad_script)
    # Add the wrapper function that processes each shot
    graph.add_node("process_single_shot", process_single_shot_wrapper)
    graph.add_node("aggregate_results", aggregate_results)
    graph.add_node("concatenate_videos", concatenate_videos)
    graph.add_node("generate_bgm", generate_and_add_bgm)
    
    # Add edges
    graph.add_edge(START, "write_script")
    # Conditional edge: fan_out_shots returns Send[] to dispatch parallel tasks
    graph.add_conditional_edges("write_script", fan_out_shots, ["process_single_shot"])
    # After all shots are processed, aggregate results (reducer merges shot_results)
    graph.add_edge("process_single_shot", "aggregate_results")
    graph.add_edge("aggregate_results", "concatenate_videos")
    graph.add_edge("concatenate_videos", "generate_bgm")
    graph.add_edge("generate_bgm", END)
    
    return graph


# Compile the graph - this is what LangGraph Server will use
app = build_graph().compile(name="AD Agent")
