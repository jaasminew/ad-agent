"""Style Searcher Worker - Search for style reference images"""

import logging
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from agent.tools.pixelhub import get_pixelhub_client
from .state import ShotState
from agent.prompts.style_searcher import STYLE_SEARCHER_SYSTEM_PROMPT, STYLE_SEARCHER_USER_PROMPT

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Style Searcher (PixelHub API): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _list_tags_with_retry(client, page: int, limit: int) -> dict:
    """List tags with retry mechanism."""
    return client.list_tags(page=page, limit=limit)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Style Searcher (LLM): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _select_tags_with_retry(all_tags: list, product_name: str, brand_identity: str, shot: str) -> list:
    """Select tags with retry mechanism for LLM API calls."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", STYLE_SEARCHER_SYSTEM_PROMPT),
        ("user", STYLE_SEARCHER_USER_PROMPT)
    ])
    
    llm = ChatOpenAI(model="gpt-4", temperature=0.3)
    chain = prompt | llm
    
    response = chain.invoke({
        "all_tags": json.dumps(all_tags[:200], ensure_ascii=False),  # Only first 200 tags to avoid token limit
        "product_name": product_name,
        "brand_identity": brand_identity,
        "shot": shot,
    })
    
    # Parse selected tags
    selected_tags_text = response.content.strip()
    # Try to extract JSON array
    if selected_tags_text.startswith("```"):
        # Remove code block markers
        lines = selected_tags_text.split("\n")
        selected_tags_text = "\n".join(lines[1:-1])
    
    return json.loads(selected_tags_text)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Style Searcher (Search API): Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _search_images_with_retry(client, selected_tags: list) -> dict:
    """Search images with retry mechanism."""
    return client.search_images(tags=selected_tags, page=1, limit=1)


def search_style_image(state: ShotState) -> dict:
    """
    Search for style reference image from PixelHub.
    
    Inputs:
    - shot: Single shot description
    - product_name: Product name
    - brand_identity: Brand positioning
    
    Outputs:
    - style_image_url: Style reference image URL
    """
    logger.info("=== Style Searcher: Finding style reference image ===")
    
    shot = state["shot"]
    product_name = state["product_name"]
    brand_identity = state["brand_identity"]
    
    # Step 1: Get all available tags
    logger.info("Step 1: Fetching all PixelHub tags")
    client = get_pixelhub_client()
    
    all_tags = []
    page = 1
    limit = 1000
    
    while True:
        result = _list_tags_with_retry(client, page, limit)
        tags = result.get("tags", [])
        tag_names = [tag.get("name") for tag in tags if tag.get("name")]
        all_tags.extend(tag_names)
        
        if len(tags) < limit:
            break
        page += 1
    
    logger.info(f"Retrieved {len(all_tags)} tags")
    
    # Step 2: Use LLM to select most relevant tags
    logger.info("Step 2: Using LLM to select relevant tags")
    
    selected_tags = _select_tags_with_retry(all_tags, product_name, brand_identity, shot)
    logger.info(f"Selected tags: {selected_tags}")
    
    # Step 3: Search images using tags
    logger.info("Step 3: Searching for style images")
    search_result = _search_images_with_retry(client, selected_tags)
    
    results = search_result.get("results", [])
    if not results:
        raise ValueError(f"No images found matching tags {selected_tags}")
    
    # Select first image
    style_image = results[0]
    style_image_url = style_image["url"]
    
    logger.info(f"Selected style image: {style_image_url}")
    logger.info(f"Image description: {style_image.get('description', 'N/A')}")
    
    return {
        "style_image_url": style_image_url,
        "messages": [f"✓ Style Searcher: Found style image {style_image_url}"]
    }

