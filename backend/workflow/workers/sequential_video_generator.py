"""Sequential Video Generator - 串行生成视频(步骤 3)"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from workflow.tools.veo_video import get_veo_video_client
from workflow.tools.kling_video import get_kling_video_client
from workflow.tools.seedance_video import get_seedance_video_client
from workflow.prompts.video_generator import VIDEO_GENERATOR_SYSTEM_PROMPT, VIDEO_GENERATOR_USER_PROMPT

# Add backend to path for service imports
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)


def _check_cancellation():
    """Check if task has been cancelled and raise exception if so."""
    try:
        from service.task_manager import TaskContext, get_task_manager
        from service.workflow_executor import TaskCancelledException
        
        task_id = TaskContext.get_task_id()
        if task_id:
            task_manager = get_task_manager()
            if task_manager.is_cancelled(task_id):
                logger.info(f"[Task {task_id}] Task cancelled by user during video generation")
                raise TaskCancelledException(f"Task {task_id} cancelled")
    except Exception as e:
        # If it's a cancellation exception, re-raise it
        if e.__class__.__name__ == "TaskCancelledException":
            raise
        # Otherwise, silently ignore other errors
        logger.debug(f"Failed to check cancellation: {e}")


def _stream_progress(message: str, output: dict = None):
    """Send progress update to task manager if available."""
    try:
        from service.task_manager import TaskContext, get_task_manager
        from service.models import WorkflowStage
        
        task_id = TaskContext.get_task_id()
        task_manager = get_task_manager() if task_id else None
        
        if task_manager and task_id:
            task_manager.add_llm_output(
                task_id=task_id,
                stage=WorkflowStage.VIDEO_GENERATOR,
                message=message,
                output=output or {},
            )
    except Exception as e:
        # Silently ignore streaming errors
        logger.debug(f"Failed to stream progress: {e}")
    
    logger.info(message)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Video Generator (Prompt): Attempt {retry_state.attempt_number} failed, retrying..."
    )
)
def _generate_video_prompt_with_retry(shot: str, context_info: str, position_hint: str) -> str:
    """Generate video prompt with retry mechanism for LLM API calls."""
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", VIDEO_GENERATOR_SYSTEM_PROMPT),
        ("user", VIDEO_GENERATOR_USER_PROMPT)
    ])
    
    llm = ChatOpenAI(model="gpt-4", temperature=0.6)
    chain = prompt_template | llm
    
    response = chain.invoke({
        "shot": shot,
        "context": context_info,
        "position": position_hint,
    })
    
    return response.content.strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=20),
    retry=retry_if_exception_type((RuntimeError, ConnectionError, TimeoutError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Video Generator (API): Attempt {retry_state.attempt_number} failed, retrying..."
    )
)
def _generate_video_with_api(video_model: str, image_url: str, video_prompt: str) -> dict:
    """Generate video with specified model with retry mechanism."""
    if video_model == "kling":
        client = get_kling_video_client()
        result = client.generate_video(
            image_url=image_url,
            prompt=video_prompt,
            duration="5",
            mode="pro",
            cfg_scale=0.5,
            upload_to_cos=True
        )
    elif video_model == "seedance":
        client = get_seedance_video_client()
        result = client.generate_video(
            prompt=video_prompt,
            image_url=image_url,
            resolution="1080p",
            duration=5,
            camera_fixed=False,
            watermark=True,
            upload_to_cos=True
        )
    else:  # veo
        client = get_veo_video_client()
        result = client.generate_video(
            prompt=video_prompt,
            image_url=image_url,
            upload_to_cos=True
        )
    
    if not result["success"]:
        raise RuntimeError(f"{video_model.upper()} video generation failed: {result.get('error')}")
    
    return result


def generate_videos_sequentially(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    串行生成视频 (步骤 3) - 考虑相邻镜头的过渡连贯性.
    
    从 Storyboard Agent 的输出(nanobanana_images)生成视频。
    
    Input from state:
    - episode_result: EpisodeResult from Storyboard Agent
    - nanobanana_images: List of final composed image URLs
    - generate_video: Whether to generate video
    - video_model: Which model to use ("veo", "kling", "seedance")
    
    Output to state:
    - shot_results: List of video generation results for each beat
    """
    logger.info("\n" + "=" * 80)
    logger.info("Generating Videos Sequentially (Step 3)")
    logger.info("=" * 80)
    
    episode_result = state["episode_result"]
    nanobanana_images = state["nanobanana_images"]
    generate_video_flag = state.get("generate_video", False)
    video_model = state.get("video_model", "kling").lower()
    
    total_beats = len(episode_result.beats)
    logger.info(f"Total beats: {total_beats}")
    logger.info(f"Video generation: {'ENABLED' if generate_video_flag else 'DISABLED'}")
    logger.info(f"Video model: {video_model.upper()}")
    
    shot_results = []
    
    _stream_progress(
        f"🎬 Starting video generation for {total_beats} beats using {video_model.upper()}",
        {"total_beats": total_beats, "model": video_model}
    )
    
    for i, beat_result in enumerate(episode_result.beats):
        # Check for cancellation at the start of each beat
        _check_cancellation()
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Processing Beat {i+1}/{total_beats}")
        logger.info(f"{'=' * 80}")
        
        beat_number = beat_result.beat_number
        shot_text = beat_result.shot_text
        final_image_url = nanobanana_images[i] if i < len(nanobanana_images) else beat_result.final_image_url
        
        _stream_progress(
            f"🎥 Generating video for Beat {i+1}/{total_beats}",
            {"beat_number": beat_number, "shot_text": shot_text[:100]}
        )
        
        logger.info(f"Beat {beat_number}: {shot_text[:60]}...")
        logger.info(f"Source image: {final_image_url}")
        
        # Determine previous and next beats for smooth transitions
        previous_beat = episode_result.beats[i-1] if i > 0 else None
        next_beat = episode_result.beats[i+1] if i < total_beats - 1 else None
        
        # Build context information
        context_parts = []
        if previous_beat:
            context_parts.append(f"Previous shot: {previous_beat.shot_text}")
            logger.info(f"  Previous: {previous_beat.shot_text[:60]}...")
        if next_beat:
            context_parts.append(f"Next shot: {next_beat.shot_text}")
            logger.info(f"  Next: {next_beat.shot_text[:60]}...")
        
        context_info = "\n".join(context_parts) if context_parts else "This is a standalone shot."
        
        # Determine position in sequence
        if not previous_beat and next_beat:
            position_hint = "This is the FIRST shot. End with camera movement/state that flows into the next shot."
        elif previous_beat and next_beat:
            position_hint = "This is a MIDDLE shot. Start smoothly from previous shot and end preparing for next shot."
        elif previous_beat and not next_beat:
            position_hint = "This is the FINAL shot. Start smoothly from previous shot and end with a strong closing."
        else:
            position_hint = "This is a SINGLE shot. Create a complete, self-contained scene."
        
        logger.info(f"Position: {position_hint}")
        
        # Generate video prompt
        try:
            _stream_progress(
                f"📝 Generating video prompt for Beat {i+1}...",
                {"action": "prompt_generation"}
            )
            video_prompt = _generate_video_prompt_with_retry(shot_text, context_info, position_hint)
            _stream_progress(
                f"✓ Generated prompt: {video_prompt[:150]}...",
                {"prompt": video_prompt}
            )
            logger.info(f"✓ Generated video prompt: {video_prompt[:100]}...")
        except Exception as e:
            logger.error(f"❌ Failed to generate video prompt for beat {beat_number}: {e}")
            _stream_progress(
                f"❌ Prompt generation failed for Beat {i+1}: {str(e)}",
                {"error": str(e)}
            )
            shot_results.append({
                "beat_number": beat_number,
                "shot_text": shot_text,
                "source_image_url": final_image_url,
                "video_prompt": f"Error: {str(e)}",
                "video_url": None,
                "success": False,
                "error": str(e),
            })
            continue
        
        # Optionally generate actual video
        video_url = None
        success = True
        error = None
        
        if generate_video_flag:
            _stream_progress(
                f"🎬 Calling {video_model.upper()} API to generate video...",
                {"action": "video_generation", "model": video_model}
            )
            logger.info(f"Generating video with {video_model.upper()}...")
            try:
                result = _generate_video_with_api(video_model, final_image_url, video_prompt)
                video_url = result.get("cos_url") or result.get("local_path")
                _stream_progress(
                    f"✅ Video generated successfully for Beat {i+1}",
                    {"video_url": video_url}
                )
                logger.info(f"✓ Video generated: {video_url}")
            except Exception as e:
                logger.error(f"❌ Failed to generate video for beat {beat_number}: {e}")
                _stream_progress(
                    f"❌ Video generation failed for Beat {i+1}: {str(e)}",
                    {"error": str(e)}
                )
                success = False
                error = str(e)
        else:
            _stream_progress(
                f"⏭️ Skipping video generation (disabled)",
                {"action": "skip"}
            )
            logger.info("Skipping video generation (generate_video=False)")
        
        shot_results.append({
            "beat_number": beat_number,
            "shot_text": shot_text,
            "source_image_url": final_image_url,
            "video_prompt": video_prompt,
            "video_url": video_url,
            "success": success,
            "error": error,
        })
        
        logger.info(f"✓ Beat {beat_number} completed")
    
    _stream_progress(
        f"✅ Video generation completed for all {len(shot_results)} beats",
        {"total_beats": len(shot_results)}
    )
    logger.info(f"\n✓ Video generation completed for {len(shot_results)} beats")
    
    return {
        "shot_results": shot_results,
        "messages": [f"✓ Generated videos for {len(shot_results)} beats"],
    }

