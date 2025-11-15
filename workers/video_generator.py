"""Video Generator Worker - Generate video using Veo 3"""

import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from tools.veo_video import get_veo_video_client
from .state import WorkflowState

logger = logging.getLogger(__name__)


def generate_video(state: WorkflowState) -> dict:
    """
    Generate video from composed image using Veo 3.1.
    
    Inputs:
    - nanobanana_image_url: Composed image with product in scene
    - shots: List of shot descriptions (use first one for video generation)
    
    Outputs:
    - video_url: Final generated video URL
    """
    logger.info("=== Video Generator: Creating video from image ===")
    
    nanobanana_image_url = state["nanobanana_image_url"]
    shots = state["shots"]
    
    # Step 1: Generate video prompt using LLM
    logger.info("Step 1: Generating video prompt")
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a professional video director. Generate a clear, cinematic prompt for animating a still image into a video.

Requirements:
1. Write prompt in English
2. Focus on camera movement and scene dynamics
3. Keep the motion smooth and professional
4. Suitable for short advertisement videos (5-10 seconds)
5. Output only the prompt text"""),
        ("user", """Ad shot description (using first one):
{first_shot}

Generate a video animation prompt for this scene:""")
    ])
    
    llm = ChatOpenAI(model="gpt-4", temperature=0.6)
    chain = prompt_template | llm
    
    first_shot = shots[0] if shots else "showcase the product in an engaging way"
    
    response = chain.invoke({
        "first_shot": first_shot,
    })
    
    video_prompt = response.content.strip()
    logger.info(f"Generated video prompt: {video_prompt}")
    
    # Step 2: Call Veo 3.1 to generate video
    logger.info("Step 2: Calling Veo 3.1 to generate video")
    client = get_veo_video_client()
    
    result = client.generate_video(
        prompt=video_prompt,
        image_url=nanobanana_image_url,
        upload_to_cos=True
    )
    
    if not result["success"]:
        raise RuntimeError(f"Veo video generation failed: {result.get('error')}")
    
    # Get video URL (COS URL if available, else local path)
    video_url = result.get("cos_url") or result.get("local_path")
    
    logger.info(f"Video generation complete: {video_url}")
    
    return {
        "video_url": video_url,
        "messages": [f"✓ Video Generator: Created video {video_url}"]
    }

