"""Midjourney Generator Worker - Generate images using Midjourney"""

import logging
from workflow.utils.llm_factory import get_chat_model
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from workflow.tools.midjourney import get_midjourney_client
from .state import ShotState
from workflow.prompts.midjourney_generator import get_midjourney_system_prompt, MIDJOURNEY_USER_PROMPT

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Midjourney Generator (LLM): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _generate_midjourney_prompt_with_retry(shot: str, colors_text: str, retry_count: int) -> str:
    """Generate Midjourney prompt with retry mechanism for LLM API calls."""
    # Get system prompt with sensitivity warning if retrying
    system_prompt = get_midjourney_system_prompt(retry_count)
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", MIDJOURNEY_USER_PROMPT)
    ])
    
    llm = get_chat_model(model="gpt-4", temperature=0.7)
    chain = prompt_template | llm
    
    response = chain.invoke({
        "shot": shot,
        "colors": colors_text,
    })
    
    return response.content.strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=20),
    retry=retry_if_exception_type((RuntimeError, ConnectionError, TimeoutError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Midjourney Generator (API - Imagine): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _submit_imagine_with_retry(client, full_prompt: str) -> dict:
    """Submit imagine request with retry mechanism."""
    submit_response = client.submit_imagine(full_prompt)
    code = submit_response.get("code")
    
    # Check for sensitive word error (code 24) - don't retry this via tenacity
    if code == 24:
        # Let the main function handle sensitive word retries
        return submit_response
    
    if code not in [1, 21, 22]:
        raise RuntimeError(f"Midjourney imagine submission failed: {submit_response}")
    
    return submit_response


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=30),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Midjourney Generator (API - Poll): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _poll_task_with_retry(client, task_id: str) -> dict:
    """Poll task with retry mechanism. Timeout is handled by poll_task_until_complete (default 3 minutes)."""
    return client.poll_task_until_complete(task_id, timeout=180)  # 3 minutes timeout for image generation


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=20),
    retry=retry_if_exception_type((RuntimeError, ConnectionError, TimeoutError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Midjourney Generator (API - Upscale): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _submit_upscale_with_retry(client, task_id: str) -> dict:
    """Submit upscale request with retry mechanism."""
    upscale_response = client.submit_change(task_id, "UPSCALE", 1)
    upscale_code = upscale_response.get("code")
    
    if upscale_code not in [1, 21, 22]:
        raise RuntimeError(f"Midjourney upscale submission failed: {upscale_response}")
    
    return upscale_response


def generate_midjourney_image(state: ShotState) -> dict:
    """
    Generate image using Midjourney with style reference and color palette.
    
    Supports automatic retry if sensitive words are detected.
    
    Inputs:
    - style_image_url: Style reference image URL
    - palette: Dominant color palette
    - shot: Single shot description
    - midjourney_retry_count: Number of retries due to sensitive words (optional)
    
    Outputs:
    - midjourney_task_id: Midjourney task ID
    - midjourney_image_url: Generated and upscaled image URL
    - midjourney_retry_count: Updated retry count
    """
    logger.info("=== Midjourney Generator: Creating image ===")
    
    style_image_url = state["style_image_url"]
    palette = state["palette"]
    shot = state["shot"]
    retry_count = state.get("midjourney_retry_count", 0)
    max_retries = 3
    
    # Step 1: Use LLM to generate Midjourney prompt
    logger.info(f"Step 1: Generating Midjourney prompt (attempt {retry_count + 1}/{max_retries + 1})")
    
    # Convert colors to hex
    color_hex_list = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in palette]
    colors_text = ", ".join(color_hex_list)
    
    # Generate prompt with retry
    generated_prompt = _generate_midjourney_prompt_with_retry(shot, colors_text, retry_count)
    logger.info(f"Generated prompt: {generated_prompt}")
    
    # Step 2: Combine style image URL and prompt
    # Midjourney format: image URL + prompt
    full_prompt = f"{style_image_url} {generated_prompt}"
    logger.info(f"Full Midjourney input: {full_prompt}")
    
    # Step 3: Call Midjourney imagine
    logger.info("Step 2: Submitting to Midjourney imagine")
    client = get_midjourney_client()
    
    submit_response = _submit_imagine_with_retry(client, full_prompt)
    code = submit_response.get("code")
    
    # Check for sensitive word error (code 24)
    if code == 24:
        banned_word = submit_response.get("properties", {}).get("bannedWord", 'unknown')
        logger.warning(f"Midjourney rejected prompt due to sensitive word: {banned_word}")
        
        if retry_count < max_retries:
            logger.info(f"Retrying with new prompt (attempt {retry_count + 2}/{max_retries + 1})...")
            # Increment retry count and recursively call this function
            new_state = state.copy()
            new_state["midjourney_retry_count"] = retry_count + 1
            return generate_midjourney_image(new_state)
        else:
            raise RuntimeError(
                f"Midjourney prompt rejected after {max_retries + 1} attempts. "
                f"Last banned word: {banned_word}. "
                f"Please modify the shot description or brand identity to use more neutral language."
            )
    
    if code not in [1, 21, 22]:
        raise RuntimeError(f"Midjourney imagine submission failed: {submit_response}")
    
    task_id = submit_response.get("result")
    logger.info(f"Task submitted: {task_id}")
    
    # Poll until complete with retry
    task = _poll_task_with_retry(client, task_id)
    image_url = task.get("imageUrl")
    
    logger.info(f"Image generation complete: {image_url}")
    
    # Step 4: Call Midjourney upscale to select first image
    logger.info("Step 3: Upscaling first image")
    upscale_response = _submit_upscale_with_retry(client, task_id)
    upscale_task_id = upscale_response.get("result")
    logger.info(f"Upscale task submitted: {upscale_task_id}")
    
    # Poll upscale task with retry
    upscale_task = _poll_task_with_retry(client, upscale_task_id)
    upscaled_image_url = upscale_task.get("imageUrl")
    
    logger.info(f"Upscale complete: {upscaled_image_url}")
    
    result = {
        "midjourney_task_id": upscale_task_id,
        "midjourney_image_url": upscaled_image_url,
        "messages": [f"✓ Midjourney Generator: Created image {upscaled_image_url}"]
    }
    
    # Include retry count if there were retries
    if retry_count > 0:
        result["midjourney_retry_count"] = retry_count
        result["messages"].append(f"  (Retried {retry_count} time(s) due to sensitive words)")
    
    return result

