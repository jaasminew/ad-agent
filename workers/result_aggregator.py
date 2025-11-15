"""Result Aggregator Worker - Aggregate results from all shots"""

import logging
from typing import Dict, Any, List
from .state import WorkflowState

logger = logging.getLogger(__name__)


def aggregate_results(state: WorkflowState) -> dict:
    """
    Aggregate and summarize results from all processed shots.
    
    Inputs:
    - shot_results: List of results from each shot
    - shots: Original shot descriptions
    - generate_video: Whether videos were generated
    
    Outputs:
    - aggregated_summary: Summary of all results
    - final_outputs: List of final outputs for each shot
    """
    logger.info("=== Result Aggregator: Summarizing all shot results ===")
    
    shot_results = state.get("shot_results", [])
    shots = state.get("shots", [])
    generate_video_flag = state.get("generate_video", False)
    
    logger.info(f"Aggregating results from {len(shot_results)} shots")
    
    # Prepare aggregated summary
    final_outputs = []
    
    for i, (shot, result) in enumerate(zip(shots, shot_results), 1):
        logger.info(f"\nShot {i} Summary:")
        logger.info(f"  Description: {shot}")
        
        output = {
            "shot_index": i,
            "shot_description": shot,
            "style_image_url": result.get("style_image_url"),
            "midjourney_image_url": result.get("midjourney_image_url"),
            "composed_image_url": result.get("nanobanana_image_url"),
            "video_prompt": result.get("video_prompt"),
            "distortion_retries": result.get("distortion_retry_count", 1) - 1,
        }
        
        # Add video URL if generated
        if generate_video_flag:
            output["video_url"] = result.get("video_url")
            logger.info(f"  ✓ Video: {output['video_url']}")
        else:
            logger.info(f"  ✓ Video prompt: {output['video_prompt'][:80]}...")
            logger.info(f"  ✓ Composed image: {output['composed_image_url']}")
        
        final_outputs.append(output)
    
    # Create summary statistics
    total_retries = sum(result.get("distortion_retry_count", 1) - 1 for result in shot_results)
    
    summary = {
        "total_shots": len(shots),
        "successful_shots": len(shot_results),
        "total_distortion_retries": total_retries,
        "video_generation_enabled": generate_video_flag,
        "outputs": final_outputs
    }
    
    logger.info(f"\n{'=' * 80}")
    logger.info("Aggregation Summary:")
    logger.info(f"  - Total shots: {summary['total_shots']}")
    logger.info(f"  - Successfully processed: {summary['successful_shots']}")
    logger.info(f"  - Total distortion retries: {summary['total_distortion_retries']}")
    logger.info(f"  - Video generation: {'ENABLED' if generate_video_flag else 'DISABLED'}")
    logger.info(f"{'=' * 80}")
    
    return {
        "aggregated_summary": summary,
        "final_outputs": final_outputs,
        "messages": [f"✓ Result Aggregator: Summarized {len(shot_results)} shots"]
    }

