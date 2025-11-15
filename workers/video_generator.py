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
    - generate_video: Whether to actually generate the video
    
    Outputs:
    - video_prompt: Video prompt (always generated)
    - video_url: Final generated video URL (only if generate_video=True)
    """
    logger.info("=== Video Generator: Creating video prompt ===")
    
    nanobanana_image_url = state["nanobanana_image_url"]
    shot = state["shot"]
    generate_video_flag = state.get("generate_video", False)
    
    # Step 1: Always generate video prompt
    logger.info("Step 1: Generating video prompt")
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a professional video director. Generate a clear, cinematic prompt for animating a still image into a video.

Requirements:
1. Write prompt in English
2. Focus on camera movement and scene dynamics
3. Keep the motion smooth and professional
4. Suitable for short advertisement videos (5-10 seconds)
5. Output only the prompt text"""),
        ("user", """Ad shot description:
{shot}

Generate a video animation prompt for this scene:""")
    ])
    
    llm = ChatOpenAI(model="gpt-4", temperature=0.6)
    chain = prompt_template | llm
    
    response = chain.invoke({
        "shot": shot,
    })
    
    video_prompt = response.content.strip()
    logger.info(f"Generated video prompt: {video_prompt}")
    
    result = {
        "video_prompt": video_prompt,
        "messages": [f"✓ Video Generator: Generated video prompt"]
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


