"""Video Generator Worker - Generate video using Veo 3"""

import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from tools.veo_video import get_veo_video_client
from .state import ShotState

logger = logging.getLogger(__name__)


def generate_video(state: ShotState) -> dict:
    """
    Generate video from composed image using Veo 3.1.
    
    Inputs:
    - nanobanana_image_url: Composed image with product in scene
    - shot: Shot description
    - previous_shot: Previous shot description (if exists, for smooth transitions)
    - next_shot: Next shot description (if exists, for planning camera movement)
    - generate_video: Whether to actually generate the video
    
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
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a professional video director specializing in seamless shot transitions. Generate a clear, cinematic prompt for animating a still image into a video.

CRITICAL REQUIREMENTS for smooth transitions:
1. Write prompt in English
2. Consider the PREVIOUS and NEXT shots to create smooth transitions
3. Camera movement should flow naturally between shots:
   - For first shot: Start stable, end with movement direction toward next scene
   - For middle shots: Continue camera momentum from previous, prepare for next
   - For final shot: Continue from previous, end with a strong conclusion
4. Match camera angles, speed, and direction for continuity
5. Keep motion smooth and professional
6. Suitable for short advertisement videos (5-10 seconds)
7. Output only the prompt text

Example good transitions:
- "Camera slowly pans right, ending with momentum toward the next scene..."
- "Continuing the rightward pan from previous shot, camera gradually slows and focuses on..."
- "Following the previous zoom motion, camera pulls back and rotates to reveal..."
"""),
        ("user", """Current shot description:
{shot}

Context:
{context}

Position: {position}

Generate a video animation prompt that ensures smooth transitions with adjacent shots:""")
    ])
    
    llm = ChatOpenAI(model="gpt-4", temperature=0.6)
    chain = prompt_template | llm
    
    response = chain.invoke({
        "shot": shot,
        "context": context_info,
        "position": position_hint,
    })
    
    video_prompt = response.content.strip()
    logger.info(f"Generated video prompt: {video_prompt}")
    
    result = {
        "video_prompt": video_prompt,
        "messages": [f"✓ Video Generator: Generated video prompt with transition context"]
    }
    
    # Step 2: Optionally generate actual video
    if generate_video_flag:
        logger.info("Step 2: Generating video with Veo 3.1 (generate_video=True)")
        client = get_veo_video_client()
        
        veo_result = client.generate_video(
            prompt=video_prompt,
            image_url=nanobanana_image_url,
            upload_to_cos=True
        )
        
        if not veo_result["success"]:
            raise RuntimeError(f"Veo video generation failed: {veo_result.get('error')}")
        
        # Get video URL (COS URL if available, else local path)
        video_url = veo_result.get("cos_url") or veo_result.get("local_path")
        
        logger.info(f"Video generation complete: {video_url}")
        result["video_url"] = video_url
        result["messages"] = [f"✓ Video Generator: Created video {video_url}"]
    else:
        logger.info("Step 2: Skipping video generation (generate_video=False)")
        result["messages"] = [f"✓ Video Generator: Generated video prompt (video generation skipped)"]
    
    return result


