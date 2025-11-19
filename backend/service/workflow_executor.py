"""Workflow Executor - Integrates existing workflow with content interception"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, TYPE_CHECKING

# Add workflow directory to Python path
workflow_path = Path(__file__).parent.parent / "workflow"
sys.path.insert(0, str(workflow_path))

from workers import WorkflowState
from workers.script_gen_agent_worker import write_ad_script_with_agent
from workers.storyboard_agent_worker import run_storyboard_agent
from workers.sequential_video_generator import generate_videos_sequentially
from workers.result_aggregator import aggregate_results
from workers.video_concatenator import concatenate_videos
from workers.bgm_generator import generate_and_add_bgm

if TYPE_CHECKING:
    from .task_manager import TaskManager

from .models import WorkflowStage

logger = logging.getLogger(__name__)


class TaskCancelledException(Exception):
    """Task cancelled exception"""
    pass


def execute_workflow(
    task_manager: 'TaskManager',
    task_id: str,
    product_name: str,
    brand_identity: str,
    product_images: str,
    must_have_shots: str,
    max_shots: int,
    video_format: str,
) -> Dict[str, Any]:
    """Execute complete AD Agent workflow
    
    Args:
        task_manager: Task manager
        task_id: Task ID
        product_name: Product name
        brand_identity: Brand identity/positioning
        product_images: Product image URL
        must_have_shots: Required shots
        max_shots: Maximum number of shots
        video_format: Video format
        
    Returns:
        Final state dictionary
    """
    logger.info(f"Starting workflow execution for task: {task_id}")
    
    # Initialize state
    state: WorkflowState = {
        "product_name": product_name,
        "brand_identity": brand_identity,
        "product_images": product_images,
        "must_have_shots": must_have_shots,
        "num_shots": max_shots,
        "generate_video": True,  # Generate video by default
        "video_model": "kling",  # Use kling by default
        "messages": [],
    }
    
    # ==================== Stage 1: Script Generation ====================
    logger.info(f"[Task {task_id}] Stage 1: Script Generation")
    _check_cancelled(task_manager, task_id)
    task_manager.db.update_task_stage(task_id, WorkflowStage.SCRIPT_GEN_AGENT)
    
    try:
        state = _execute_with_logging(
            task_manager=task_manager,
            task_id=task_id,
            stage=WorkflowStage.SCRIPT_GEN_AGENT,
            worker_func=write_ad_script_with_agent,
            state=state,
        )
        logger.info(f"[Task {task_id}] ✓ Script generation completed")
    except Exception as e:
        logger.error(f"[Task {task_id}] ❌ Script generation failed: {e}")
        raise
    
    # ==================== Stage 2: Storyboard Generation ====================
    logger.info(f"[Task {task_id}] Stage 2: Storyboard Generation")
    _check_cancelled(task_manager, task_id)
    task_manager.db.update_task_stage(task_id, WorkflowStage.STORYBOARD_GEN_AGENT)
    
    try:
        state = _execute_with_logging(
            task_manager=task_manager,
            task_id=task_id,
            stage=WorkflowStage.STORYBOARD_GEN_AGENT,
            worker_func=run_storyboard_agent,
            state=state,
        )
        logger.info(f"[Task {task_id}] ✓ Storyboard generation completed")
    except Exception as e:
        logger.error(f"[Task {task_id}] ❌ Storyboard generation failed: {e}")
        raise
    
    # ==================== Stage 3: Video Generation ====================
    logger.info(f"[Task {task_id}] Stage 3: Video Generation")
    _check_cancelled(task_manager, task_id)
    task_manager.db.update_task_stage(task_id, WorkflowStage.VIDEO_GENERATOR)
    
    try:
        state = _execute_with_logging(
            task_manager=task_manager,
            task_id=task_id,
            stage=WorkflowStage.VIDEO_GENERATOR,
            worker_func=generate_videos_sequentially,
            state=state,
        )
        logger.info(f"[Task {task_id}] ✓ Video generation completed")
    except Exception as e:
        logger.error(f"[Task {task_id}] ❌ Video generation failed: {e}")
        raise
    
    # ==================== Stage 4: Result Aggregation ====================
    logger.info(f"[Task {task_id}] Stage 4: Result Aggregation")
    _check_cancelled(task_manager, task_id)
    
    try:
        state = _execute_with_logging(
            task_manager=task_manager,
            task_id=task_id,
            stage=WorkflowStage.VIDEO_GENERATOR,  # Still part of video generation stage
            worker_func=aggregate_results,
            state=state,
        )
        logger.info(f"[Task {task_id}] ✓ Result aggregation completed")
    except Exception as e:
        logger.error(f"[Task {task_id}] ❌ Result aggregation failed: {e}")
        raise
    
    # ==================== Stage 5: Video Concatenation ====================
    logger.info(f"[Task {task_id}] Stage 5: Video Concatenation")
    _check_cancelled(task_manager, task_id)
    task_manager.db.update_task_stage(task_id, WorkflowStage.VIDEO_CONCATENATER)
    
    try:
        state = _execute_with_logging(
            task_manager=task_manager,
            task_id=task_id,
            stage=WorkflowStage.VIDEO_CONCATENATER,
            worker_func=concatenate_videos,
            state=state,
        )
        logger.info(f"[Task {task_id}] ✓ Video concatenation completed")
    except Exception as e:
        logger.error(f"[Task {task_id}] ❌ Video concatenation failed: {e}")
        raise
    
    # ==================== Stage 6: BGM Generation ====================
    logger.info(f"[Task {task_id}] Stage 6: BGM Generation")
    _check_cancelled(task_manager, task_id)
    task_manager.db.update_task_stage(task_id, WorkflowStage.BGM_GENERATOR)
    
    try:
        state = _execute_with_logging(
            task_manager=task_manager,
            task_id=task_id,
            stage=WorkflowStage.BGM_GENERATOR,
            worker_func=generate_and_add_bgm,
            state=state,
        )
        logger.info(f"[Task {task_id}] ✓ BGM generation completed")
    except Exception as e:
        logger.error(f"[Task {task_id}] ❌ BGM generation failed: {e}")
        raise
    
    logger.info(f"[Task {task_id}] ✓ Workflow completed successfully")
    return state


def _check_cancelled(task_manager: 'TaskManager', task_id: str):
    """Check if task is cancelled
    
    Args:
        task_manager: Task manager
        task_id: Task ID
        
    Raises:
        TaskCancelledException: If task is cancelled
    """
    if task_manager.is_cancelled(task_id):
        logger.info(f"[Task {task_id}] Task cancelled by user")
        raise TaskCancelledException(f"Task {task_id} cancelled")


def _execute_with_logging(
    task_manager: 'TaskManager',
    task_id: str,
    stage: WorkflowStage,
    worker_func: callable,
    state: WorkflowState,
) -> WorkflowState:
    """Execute worker function and record output
    
    Args:
        task_manager: Task manager
        task_id: Task ID
        stage: Workflow stage
        worker_func: Worker function
        state: Current state
        
    Returns:
        Updated state (merged with original state)
    """
    # ✅ Stage started - push immediate update
    task_manager.add_llm_output(
        task_id=task_id,
        stage=stage,
        message=f"🚀 Starting {stage.value.replace('_', ' ').title()}...",
        output={"status": "started"},
    )
    
    # Execute worker (worker itself will push intermediate updates)
    result = worker_func(state)
    
    # Record final output after completion
    _record_worker_output(task_manager, task_id, stage, state, result)
    
    # Merge result with original state (preserve all fields)
    # This ensures that fields like product_name, brand_identity, etc. are not lost
    merged_state = {**state, **result}
    
    return merged_state


def _record_worker_output(
    task_manager: 'TaskManager',
    task_id: str,
    stage: WorkflowStage,
    state: WorkflowState,
    result: WorkflowState,
):
    """Record worker output to database
    
    Args:
        task_manager: Task manager
        task_id: Task ID
        stage: Workflow stage
        state: Input state
        result: Output state
    """
    # Record different outputs based on stage
    if stage == WorkflowStage.SCRIPT_GEN_AGENT:
        # Record generated script
        shots = result.get("shots", [])
        if shots:
            task_manager.add_llm_output(
                task_id=task_id,
                stage=stage,
                message=f"Generated {len(shots)} shots for {state['product_name']}",
                output={
                    "shots": [{"shot_number": i+1, "description": shot} for i, shot in enumerate(shots)],
                    "total_shots": len(shots),
                },
                reasoning=f"Analyzed brand identity: {state['brand_identity']}",
            )
    
    elif stage == WorkflowStage.STORYBOARD_GEN_AGENT:
        # Record storyboard results
        episode_result = result.get("episode_result")
        if episode_result:
            task_manager.add_llm_output(
                task_id=task_id,
                stage=stage,
                message=f"Generated storyboards for {episode_result.total_beats} beats",
                output={
                    "total_beats": episode_result.total_beats,
                    "successful_beats": episode_result.successful_beats,
                    "flagged_beats": episode_result.flagged_beats,
                },
            )
    
    elif stage == WorkflowStage.VIDEO_GENERATOR:
        # Record video generation results
        shot_results = result.get("shot_results", [])
        if shot_results:
            task_manager.add_llm_output(
                task_id=task_id,
                stage=stage,
                message=f"Generated {len(shot_results)} videos",
                output={
                    "total_videos": len(shot_results),
                    "video_urls": [r.get("video_url", "") for r in shot_results],
                },
            )
    
    elif stage == WorkflowStage.VIDEO_CONCATENATER:
        # Record video concatenation results
        final_video_url = result.get("final_video_url")
        if final_video_url:
            task_manager.add_llm_output(
                task_id=task_id,
                stage=stage,
                message="Concatenated all video clips",
                output={
                    "final_video_url": final_video_url,
                    "duration": result.get("video_duration", 0),
                },
            )
    
    elif stage == WorkflowStage.BGM_GENERATOR:
        # Record BGM generation results
        final_video_with_bgm_url = result.get("final_video_with_bgm_url")
        if final_video_with_bgm_url:
            task_manager.add_llm_output(
                task_id=task_id,
                stage=stage,
                message="Generated and added background music",
                output={
                    "final_video_with_bgm_url": final_video_with_bgm_url,
                    "music_prompt": result.get("music_prompt", ""),
                    "music_style": result.get("music_style", ""),
                },
            )

