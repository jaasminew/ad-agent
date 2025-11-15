"""Midjourney Generator Worker - Generate images using Midjourney"""

import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from tools.midjourney import get_midjourney_client
from .state import ShotState

logger = logging.getLogger(__name__)


def generate_midjourney_image(state: ShotState) -> dict:
    """
    Generate image using Midjourney with style reference and color palette.
    
    Inputs:
    - style_image_url: Style reference image URL
    - palette: Dominant color palette
    - shot: Single shot description
    
    Outputs:
    - midjourney_task_id: Midjourney task ID
    - midjourney_image_url: Generated and upscaled image URL
    """
    logger.info("=== Midjourney Generator: Creating image ===")
    
    style_image_url = state["style_image_url"]
    palette = state["palette"]
    shot = state["shot"]
    
    # Step 1: Use LLM to generate Midjourney prompt
    logger.info("Step 1: Generating Midjourney prompt")
    
    # Convert colors to hex
    color_hex_list = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in palette]
    colors_text = ", ".join(color_hex_list)
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a professional Midjourney prompt engineer. Generate high-quality Midjourney prompts based on the advertising shot and color schemes.

Requirements:
1. Write prompt in English
2. Description should be concise and clear, highlighting visual focus
3. Can include style keywords (e.g., cinematic, professional photography, 8k, etc.)
4. Incorporate the given color scheme
5. Output only the prompt text without additional explanations
6. Do NOT include -- parameters in the prompt, only describe the visual content"""),
        ("user", """Ad shot:
{shot}

Color scheme: {colors}

Please generate Midjourney prompt (pure English, no parameters):""")
    ])
    
    llm = ChatOpenAI(model="gpt-4", temperature=0.7)
    chain = prompt_template | llm
    
    response = chain.invoke({
        "shot": shot,
        "colors": colors_text,
    })
    
    generated_prompt = response.content.strip()
    logger.info(f"Generated prompt: {generated_prompt}")
    
    # Step 2: Combine style image URL and prompt
    # Midjourney format: image URL + prompt
    full_prompt = f"{style_image_url} {generated_prompt}"
    logger.info(f"Full Midjourney input: {full_prompt}")
    
    # Step 3: Call Midjourney imagine
    logger.info("Step 2: Submitting to Midjourney imagine")
    client = get_midjourney_client()
    
    submit_response = client.submit_imagine(full_prompt)
    code = submit_response.get("code")
    
    if code not in [1, 21, 22]:
        raise RuntimeError(f"Midjourney imagine submission failed: {submit_response}")
    
    task_id = submit_response.get("result")
    logger.info(f"Task submitted: {task_id}")
    
    # Poll until complete
    task = client.poll_task_until_complete(task_id)
    image_url = task.get("imageUrl")
    
    logger.info(f"Image generation complete: {image_url}")
    
    # Step 4: Call Midjourney upscale to select first image
    logger.info("Step 3: Upscaling first image")
    upscale_response = client.submit_change(task_id, "UPSCALE", 1)
    upscale_code = upscale_response.get("code")
    
    if upscale_code not in [1, 21, 22]:
        raise RuntimeError(f"Midjourney upscale submission failed: {upscale_response}")
    
    upscale_task_id = upscale_response.get("result")
    logger.info(f"Upscale task submitted: {upscale_task_id}")
    
    # Poll upscale task
    upscale_task = client.poll_task_until_complete(upscale_task_id)
    upscaled_image_url = upscale_task.get("imageUrl")
    
    logger.info(f"Upscale complete: {upscaled_image_url}")
    
    return {
        "midjourney_task_id": upscale_task_id,
        "midjourney_image_url": upscaled_image_url,
        "messages": [f"✓ Midjourney Generator: Created image {upscaled_image_url}"]
    }

