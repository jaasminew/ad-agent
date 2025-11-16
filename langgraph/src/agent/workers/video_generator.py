"""Video Generator Worker - Generate video using Veo 3, Kling AI, or SeeDance"""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from agent.tools.veo_video import get_veo_video_client
from agent.tools.kling_video import get_kling_video_client
from agent.tools.seedance_video import get_seedance_video_client
from .state import ShotState
from agent.prompts.video_generator import VIDEO_GENERATOR_SYSTEM_PROMPT, VIDEO_GENERATOR_USER_PROMPT

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Video Generator (Prompt): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
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
        f"Video Generator (API): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _generate_video_with_kling(client, nanobanana_image_url: str, video_prompt: str) -> dict:
    """Generate video with Kling AI with retry mechanism."""
    kling_result = client.generate_video(
        image_url=nanobanana_image_url,
        prompt=video_prompt,
        duration="5",  # 5 seconds
        mode="pro",    # High quality mode
        cfg_scale=0.5,
        upload_to_cos=True
    )
    
    if not kling_result["success"]:
        raise RuntimeError(f"Kling video generation failed: {kling_result.get('error')}")
    
    return kling_result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=20),
    retry=retry_if_exception_type((RuntimeError, ConnectionError, TimeoutError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Video Generator (API): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _generate_video_with_seedance(client, nanobanana_image_url: str, video_prompt: str) -> dict:
    """Generate video with SeeDance with retry mechanism."""
    seedance_result = client.generate_video(
        prompt=video_prompt,
        image_url=nanobanana_image_url,
        resolution="1080p",
        duration=5,
        camera_fixed=False,
        watermark=True,
        upload_to_cos=True
    )
    
    if not seedance_result["success"]:
        raise RuntimeError(f"SeeDance video generation failed: {seedance_result.get('error')}")
    
    return seedance_result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=20),
    retry=retry_if_exception_type((RuntimeError, ConnectionError, TimeoutError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Video Generator (API): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _generate_video_with_veo(client, nanobanana_image_url: str, video_prompt: str) -> dict:
    """Generate video with Veo 3.1 with retry mechanism."""
    veo_result = client.generate_video(
        prompt=video_prompt,
        image_url=nanobanana_image_url,
        upload_to_cos=True
    )
    
    if not veo_result["success"]:
        raise RuntimeError(f"Veo video generation failed: {veo_result.get('error')}")
    
    return veo_result


def generate_video(state: ShotState) -> dict:
    """
    Generate video from composed image using Veo 3.1 or Kling AI.
    
    Inputs:
    - nanobanana_image_url: Composed image with product in scene
    - shot: Shot description
    - previous_shot: Previous shot description (if exists, for smooth transitions)
    - next_shot: Next shot description (if exists, for planning camera movement)
    - generate_video: Whether to actually generate the video
    - video_model: Which video generation model to use ("veo" or "kling", default: "veo")
    
    Outputs:
    - video_prompt: Video prompt (always generated, with transition info)
    - video_url: Final generated video URL (only if generate_video=True)
    """
    logger.info("=== Video Generator: Creating video prompt ===")
    
    nanobanana_image_url = state["nanobanana_image_url"]
    shot = state["shot"]
    previous_shot = state.get("previous_shot")
    next_shot = state.get("next_shot")
    shot_index = state.get("shot_index", 0)
    generate_video_flag = state.get("generate_video", False)
    video_model = state.get("video_model", "kling").lower()  # Default to "kling"
    
    # Step 1: Always generate video prompt with context
    logger.info("Step 1: Generating video prompt with transition context")
    
    # Build context information
    context_parts = []
    if previous_shot:
        context_parts.append(f"Previous shot: {previous_shot}")
    if next_shot:
        context_parts.append(f"Next shot: {next_shot}")
    
    context_info = "\n".join(context_parts) if context_parts else "This is a standalone shot."
    
    # Determine position in sequence
    position_hint = ""
    if not previous_shot and next_shot:
        position_hint = "This is the FIRST shot. End with camera movement/state that flows into the next shot."
    elif previous_shot and next_shot:
        position_hint = "This is a MIDDLE shot. Start smoothly from previous shot and end preparing for next shot."
    elif previous_shot and not next_shot:
        position_hint = "This is the FINAL shot. Start smoothly from previous shot and end with a strong closing."
    else:
        position_hint = "This is a SINGLE shot. Create a complete, self-contained scene."
    
    logger.info(f"Shot position: {position_hint}")
    
    # Generate video prompt with retry
    video_prompt = _generate_video_prompt_with_retry(shot, context_info, position_hint)
    logger.info(f"Generated video prompt: {video_prompt}")
    
    result = {
        "video_prompt": video_prompt,
        "messages": [f"✓ Video Generator: Generated video prompt with transition context"]
    }
    
    # Step 2: Optionally generate actual video
    if generate_video_flag:
        logger.info(f"Step 2: Generating video with {video_model.upper()} (generate_video=True)")
        
        if video_model == "kling":
            # Use Kling AI for video generation
            logger.info("Using Kling AI for video generation")
            client = get_kling_video_client()
            
            kling_result = _generate_video_with_kling(client, nanobanana_image_url, video_prompt)
            
            # Get video URL (COS URL if available, else local path)
            video_url = kling_result.get("cos_url") or kling_result.get("local_path")
            
            logger.info(f"Kling video generation complete: {video_url}")
            result["video_url"] = video_url
            result["messages"] = [f"✓ Video Generator: Created video with Kling AI: {video_url}"]
        
        elif video_model == "seedance":
            # Use SeeDance for video generation
            logger.info("Using Doubao SeeDance for video generation")
            client = get_seedance_video_client()
            
            seedance_result = _generate_video_with_seedance(client, nanobanana_image_url, video_prompt)
            
            # Get video URL (COS URL if available, else local path)
            video_url = seedance_result.get("cos_url") or seedance_result.get("local_path")
            
            logger.info(f"SeeDance video generation complete: {video_url}")
            result["video_url"] = video_url
            result["messages"] = [f"✓ Video Generator: Created video with SeeDance: {video_url}"]
            
        else:  # Default to "veo"
            # Use Veo 3.1 for video generation
            logger.info("Using Veo 3.1 for video generation")
            client = get_veo_video_client()
            
            veo_result = _generate_video_with_veo(client, nanobanana_image_url, video_prompt)
            
            # Get video URL (COS URL if available, else local path)
            video_url = veo_result.get("cos_url") or veo_result.get("local_path")
            
            logger.info(f"Veo video generation complete: {video_url}")
            result["video_url"] = video_url
            result["messages"] = [f"✓ Video Generator: Created video with Veo 3.1: {video_url}"]
    else:
        logger.info("Step 2: Skipping video generation (generate_video=False)")
        result["messages"] = [f"✓ Video Generator: Generated video prompt (video generation skipped)"]
    
    return result


