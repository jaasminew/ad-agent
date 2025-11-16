"""Product Composer Worker - Compose product into scene using Nanobanana"""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from workflow.tools.nanobanana import get_nanobanana_client
from .state import ShotState
from workflow.prompts.product_composer import PRODUCT_COMPOSER_SYSTEM_PROMPT, PRODUCT_COMPOSER_USER_PROMPT

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Product Composer (LLM): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _generate_composition_prompt_with_retry(shot: str) -> str:
    """Generate composition prompt with retry mechanism for LLM API calls."""
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", PRODUCT_COMPOSER_SYSTEM_PROMPT),
        ("user", PRODUCT_COMPOSER_USER_PROMPT)
    ])
    
    llm = ChatOpenAI(model="gpt-4", temperature=0.5)
    chain = prompt_template | llm
    
    response = chain.invoke({
        "shot": shot,
    })
    
    return response.content.strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=20),
    retry=retry_if_exception_type((RuntimeError, ConnectionError, TimeoutError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Product Composer (Nanobanana API): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _compose_images_with_retry(client, composition_prompt: str, midjourney_image_url: str, product_images: str) -> dict:
    """Compose images with retry mechanism for Nanobanana API calls."""
    result = client.generate_image(
        prompt=composition_prompt,
        input_image_paths=[midjourney_image_url, product_images],
        upload_to_cos=True
    )
    
    if not result["success"]:
        raise RuntimeError(f"Nanobanana generation failed: {result.get('error')}")
    
    return result


def compose_with_product(state: ShotState) -> dict:
    """
    Compose product image into Midjourney generated scene using Nanobanana.
    
    Inputs:
    - midjourney_image_url: Midjourney generated scene image URL
    - product_images: Product image URL
    - shot: Shot description (for prompt generation)
    
    Outputs:
    - nanobanana_image_url: Composed image URL (with product in scene)
    """
    logger.info("=== Product Composer: Composing product into scene ===")
    
    midjourney_image_url = state["midjourney_image_url"]
    product_images = state["product_images"]
    shot = state["shot"]
    
    # Step 1: Generate composition prompt using LLM
    logger.info("Step 1: Generating composition prompt")
    
    composition_prompt = _generate_composition_prompt_with_retry(shot)
    logger.info(f"Generated composition prompt: {composition_prompt}")
    
    # Step 2: Call Nanobanana to compose images
    logger.info("Step 2: Calling Nanobanana to compose images")
    client = get_nanobanana_client()
    
    # Nanobanana takes multiple input images: [scene_image, product_image] + prompt
    result = _compose_images_with_retry(client, composition_prompt, midjourney_image_url, product_images)
    
    # Get composed image URL (COS URL if available, else local path)
    composed_image_url = result.get("cos_url") or result.get("local_path")
    
    logger.info(f"Product composition complete: {composed_image_url}")
    
    return {
        "nanobanana_image_url": composed_image_url,
        "messages": [f"✓ Product Composer: Created composed image {composed_image_url}"]
    }

