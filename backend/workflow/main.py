"""AD Agent Workflow - Generate advertising videos using AI"""

import os
import logging
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from workers import (
    WorkflowState,
    write_ad_script,
    run_storyboard_agent,
    generate_videos_sequentially,
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

# Load environment variables
load_dotenv()
logger.info("=" * 80)
logger.info("AD Agent Workflow - Generate Advertising Videos")
logger.info("=" * 80)


# ==================== Main Workflow with Storyboard Agent ====================

def run_ad_workflow(
    product_name: str,
    brand_identity: str,
    product_images: str,
    must_have_shots: str,
    generate_video: bool = False,
    video_model: str = "seedance",
    video_format: str = "16:9"
) -> dict:
    """
    Run the complete AD Agent workflow with integrated Storyboard Agent.
    
    Workflow:
    1. Write ad script (shots list)
    2. Run Storyboard Agent (replaces old steps 2-6)
    3. Generate videos sequentially (with transitions)
    4. Aggregate results
    5. Concatenate videos
    6. Generate and add BGM
    
    Args:
        product_name: Product name
        brand_identity: Brand positioning/identity
        product_images: Product image URL
        must_have_shots: Required shots (comma-separated)
        generate_video: Whether to generate video (default: False)
        video_model: Which video generation model to use ("veo", "kling", or "seedance", default: "kling")
    
    Returns:
        Final state dict containing all results
    """
    logger.info("\n" + "=" * 80)
    logger.info("Starting AD Agent Workflow with Storyboard Agent")
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
    
    # Add nodes
    graph.add_node("write_script", write_ad_script)
    graph.add_node("run_storyboard_agent", run_storyboard_agent)
    graph.add_node("generate_videos", generate_videos_sequentially)
    graph.add_node("aggregate_results", aggregate_results)
    graph.add_node("concatenate_videos", concatenate_videos)
    graph.add_node("generate_bgm", generate_and_add_bgm)
    
    # Add edges
    graph.add_edge(START, "write_script")
    graph.add_edge("write_script", "run_storyboard_agent")
    graph.add_edge("run_storyboard_agent", "generate_videos")
    graph.add_edge("generate_videos", "aggregate_results")
    graph.add_edge("aggregate_results", "concatenate_videos")
    graph.add_edge("concatenate_videos", "generate_bgm")
    graph.add_edge("generate_bgm", END)
    
    app = graph.compile()
    
    # Initialize state
    initial_state = {
        "product_name": product_name,
        "brand_identity": brand_identity,
        "product_images": product_images,
        "must_have_shots": must_have_shots,
        "generate_video": generate_video,
        "video_model": video_model,
        "video_format": video_format,
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
    
    episode_result = final_state.get('episode_result')
    if episode_result:
        logger.info("  - Storyboard Agent processed %d beats", episode_result.total_beats)
        logger.info("  - Successful images: %d", episode_result.successful_beats)
        logger.info("  - Flagged for review: %d", episode_result.flagged_beats)
    
    logger.info("  - Processed %d videos", len(final_state.get('shot_results', [])))
    
    # Print aggregated summary
    summary = final_state.get('aggregated_summary', {})
    if summary:
        logger.info("\nAggregated Summary:")
        logger.info("  - Total shots: %d", summary.get('total_shots', 0))
        logger.info("  - Successful: %d", summary.get('successful_shots', 0))
        logger.info("  - Video generation: %s", 'ENABLED' if summary.get('video_generation_enabled') else 'DISABLED')
    
    # Print final video URL if available
    final_video_url = final_state.get('final_video_url')
    final_video_with_bgm_url = final_state.get('final_video_with_bgm_url')
    
    if final_video_with_bgm_url:
        logger.info("\n🎬 Final Video with BGM:")
        logger.info("  %s", final_video_with_bgm_url)
        
        # Print BGM info
        music_prompt = final_state.get('music_prompt')
        music_style = final_state.get('music_style')
        if music_prompt:
            logger.info("\n🎵 Background Music:")
            logger.info("  Style: %s", music_style or 'N/A')
            logger.info("  Prompt: %s", music_prompt[:100] + '...' if len(music_prompt) > 100 else music_prompt)
    elif final_video_url:
        logger.info("\n🎬 Final Video (without BGM):")
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
        final_video_with_bgm_url = result.get('final_video_with_bgm_url')
        final_video_url = result.get('final_video_url')
        
        if final_video_with_bgm_url:
            print("\n🎬 Final Video with BGM:")
            print(f"  {final_video_with_bgm_url}")
            
            music_prompt = result.get('music_prompt')
            music_style = result.get('music_style')
            if music_prompt:
                print(f"\n🎵 Background Music:")
                print(f"  Style: {music_style}")
                print(f"  Prompt: {music_prompt[:100]}...")
        elif final_video_url:
            print("\n🎬 Final Video (without BGM):")
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
