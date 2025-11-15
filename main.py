"""AD Agent Workflow - Generate advertising videos using AI"""

import os
import logging
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from workers import (
    WorkflowState,
    ShotState,
    write_ad_script,
    search_style_image,
    extract_palette,
    generate_midjourney_image,
    check_distortion,
    compose_with_product,
    generate_video,
    aggregate_results,
    concatenate_videos,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("=" * 80)
logger.info("AD Agent Workflow - Generate Advertising Videos")
logger.info("=" * 80)


# ==================== Single Shot Workflow ====================

def build_shot_workflow() -> StateGraph:
    """
    Build workflow for processing a single shot (steps 2-7).
    """
    graph = StateGraph(ShotState)
    
    # Add nodes for single shot processing
    graph.add_node("search_style", search_style_image)
    graph.add_node("extract_palette", extract_palette)
    graph.add_node("generate_image", generate_midjourney_image)
    graph.add_node("check_distortion", check_distortion)
    graph.add_node("compose_product", compose_with_product)
    graph.add_node("generate_video", generate_video)
    
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

def process_shots_concurrently(state: WorkflowState) -> dict:
    """
    Fan-out: Process each shot concurrently using the shot workflow.
    Fan-in: Collect all results.
    """
    logger.info("\n" + "=" * 80)
    logger.info("Processing shots concurrently (Fan-out/Fan-in)")
    logger.info("=" * 80)
    
    shots = state["shots"]
    product_name = state["product_name"]
    brand_identity = state["brand_identity"]
    product_images = state["product_images"]
    generate_video_flag = state["generate_video"]
    video_model = state.get("video_model", "veo")  # Get video_model from state
    
    logger.info(f"Total shots to process: {len(shots)}")
    logger.info(f"Video generation: {'ENABLED' if generate_video_flag else 'DISABLED'}")
    logger.info(f"Video model: {video_model.upper()}")
    
    # Build shot workflow
    shot_workflow = build_shot_workflow().compile()
    
    # Process each shot (currently sequential, can be made parallel with threading/async)
    shot_results = []
    for i, shot in enumerate(shots):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Processing Shot {i+1}/{len(shots)}")
        logger.info(f"{'=' * 80}")
        logger.info(f"Shot description: {shot}")
        
        # Determine previous and next shots for smooth transitions
        previous_shot = shots[i-1] if i > 0 else None
        next_shot = shots[i+1] if i < len(shots) - 1 else None
        
        if previous_shot:
            logger.info(f"  Previous shot: {previous_shot[:60]}...")
        if next_shot:
            logger.info(f"  Next shot: {next_shot[:60]}...")
        
        # Create initial state for this shot
        shot_state = {
            "shot": shot,
            "shot_index": i,
            "product_name": product_name,
            "brand_identity": brand_identity,
            "product_images": product_images,
            "generate_video": generate_video_flag,
            "video_model": video_model,  # Pass video_model to shot state
            "previous_shot": previous_shot,  # For smooth transitions
            "next_shot": next_shot,  # For planning camera movement
            "distortion_retry_count": 0,
            "midjourney_retry_count": 0,  # For sensitive word retries
            "messages": [],
        }
        
        # Execute shot workflow
        result = shot_workflow.invoke(shot_state)
        shot_results.append(result)
        
        logger.info(f"\n✓ Shot {i+1} completed")
        if generate_video_flag and result.get("video_url"):
            logger.info(f"  Video: {result.get('video_url')}")
        else:
            logger.info(f"  Video prompt: {result.get('video_prompt', 'N/A')}")
            logger.info(f"  Composed image: {result.get('nanobanana_image_url', 'N/A')}")
    
    return {
        "shot_results": shot_results,
        "messages": [f"✓ Processed {len(shots)} shots concurrently"]
    }


def run_ad_workflow(
    product_name: str,
    brand_identity: str,
    product_images: str,
    must_have_shots: str,
    generate_video: bool = False,
    video_model: str = "kling"
) -> dict:
    """
    Run the complete AD Agent workflow.
    
    Args:
        product_name: Product name
        brand_identity: Brand positioning/identity
        product_images: Product image URL
        must_have_shots: Required shots (comma-separated)
        generate_video: Whether to generate video (default: False)
        video_model: Which video generation model to use ("veo", "kling", or "seedance", default: "veo")
    
    Returns:
        Final state dict containing all shots' results
    """
    logger.info("\n" + "=" * 80)
    logger.info("Starting AD Agent Workflow")
    logger.info("=" * 80)
    logger.info(f"Product: {product_name}")
    logger.info(f"Brand Identity: {brand_identity}")
    logger.info(f"Product Images: {product_images}")
    logger.info(f"Must Have Shots: {must_have_shots}")
    logger.info(f"Generate Video: {generate_video}")
    logger.info(f"Video Model: {video_model.upper()}")
    logger.info("=" * 80 + "\n")
    
    # Build main workflow
    graph = StateGraph(WorkflowState)
    graph.add_node("write_script", write_ad_script)
    graph.add_node("process_shots", process_shots_concurrently)
    graph.add_node("aggregate_results", aggregate_results)
    graph.add_node("concatenate_videos", concatenate_videos)
    
    graph.add_edge(START, "write_script")
    graph.add_edge("write_script", "process_shots")
    graph.add_edge("process_shots", "aggregate_results")
    graph.add_edge("aggregate_results", "concatenate_videos")
    graph.add_edge("concatenate_videos", END)
    
    app = graph.compile()
    
    # Initialize state
    initial_state = {
        "product_name": product_name,
        "brand_identity": brand_identity,
        "product_images": product_images,
        "must_have_shots": must_have_shots,
        "generate_video": generate_video,
        "video_model": video_model,
        "messages": [],
    }
    
    # Execute workflow
    logger.info("Executing workflow...\n")
    final_state = app.invoke(initial_state)
    
    # Log completion
    logger.info("\n" + "=" * 80)
    logger.info("Workflow Completed Successfully!")
    logger.info("=" * 80)
    
    # Print summary
    logger.info("\nWorkflow Summary:")
    logger.info("  - Generated %d shots", len(final_state.get('shots', [])))
    logger.info("  - Processed %d shots", len(final_state.get('shot_results', [])))
    
    # Print aggregated summary
    summary = final_state.get('aggregated_summary', {})
    if summary:
        logger.info("\nAggregated Summary:")
        logger.info("  - Total shots: %d", summary.get('total_shots', 0))
        logger.info("  - Successful: %d", summary.get('successful_shots', 0))
        logger.info("  - Total distortion retries: %d", summary.get('total_distortion_retries', 0))
        logger.info("  - Video generation: %s", 'ENABLED' if summary.get('video_generation_enabled') else 'DISABLED')
    
    # Print final video URL if available
    final_video_url = final_state.get('final_video_url')
    if final_video_url:
        logger.info("\n🎬 Final Video:")
        logger.info("  %s", final_video_url)
    
    # Print each shot's final output
    final_outputs = final_state.get('final_outputs', [])
    if final_outputs:
        logger.info("\nFinal Outputs:")
        for output in final_outputs:
            logger.info(f"\n  Shot {output['shot_index']}: {output['shot_description'][:60]}...")
            logger.info(f"    - Composed image: {output['composed_image_url']}")
            if output.get('video_url'):
                logger.info(f"    - Video: {output['video_url']}")
            else:
                logger.info(f"    - Video prompt: {output['video_prompt'][:80]}...")
    
    return final_state


if __name__ == "__main__":
    # Example usage - set generate_video=True to generate and concatenate videos
    result = run_ad_workflow(
        product_name="Polaroid Camera",
        brand_identity="Nostalgia, Artistic, Instant Sharing, Creativity, Authenticity",
        product_images="https://m.media-amazon.com/images/I/71a0-JzaiEL._AC_SL1500_.jpg",
        must_have_shots="Scenes of friends instantly sharing photos",
        generate_video=True,  # Set to True to generate and concatenate videos
        video_model="seedance"     # Choose "veo", "kling", or "seedance"
    )
    
    print("\n" + "=" * 80)
    print("🎬 Final Output")
    print("=" * 80)
    
    summary = result.get('aggregated_summary', {})
    if summary:
        print(f"Total shots processed: {summary.get('successful_shots', 0)}/{summary.get('total_shots', 0)}")
        print(f"Video generation: {'ENABLED' if summary.get('video_generation_enabled') else 'DISABLED'}")
        
        # Print final video URL if available
        final_video_url = result.get('final_video_url')
        if final_video_url:
            print("\n🎬 Final Concatenated Video:")
            print(f"  {final_video_url}")
        
        final_outputs = result.get('final_outputs', [])
        for output in final_outputs:
            print(f"\nShot {output['shot_index']}:")
            print(f"  Description: {output['shot_description']}")
            print(f"  Composed image: {output['composed_image_url']}")
            if output.get('video_url'):
                print(f"  Video: {output['video_url']}")
            else:
                print(f"  Video prompt: {output['video_prompt'][:100]}...")
    
    print("=" * 80)
