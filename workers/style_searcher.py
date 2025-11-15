"""Style Searcher Worker - Search for style reference images"""

import logging
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from tools.pixelhub import get_pixelhub_client
from .state import ShotState

logger = logging.getLogger(__name__)


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
        result = client.list_tags(page=page, limit=limit)
        tags = result.get("tags", [])
        tag_names = [tag.get("name") for tag in tags if tag.get("name")]
        all_tags.extend(tag_names)
        
        if len(tags) < limit:
            break
        page += 1
    
    logger.info(f"Retrieved {len(all_tags)} tags")
    
    # Step 2: Use LLM to select most relevant tags
    logger.info("Step 2: Using LLM to select relevant tags")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a professional visual designer. Based on the advertising shot description, product information, and brand positioning, 
select the most appropriate style tags from the given tag list.

Requirements:
1. Select 3-5 tags that best represent the ad style and brand tone
2. Tags MUST be selected from the provided tag list
3. Prioritize tags that express emotion, atmosphere, and visual style
4. Output as JSON array, e.g.: ["modern", "minimalist", "elegant"]"""),
        ("user", """Available tags:
{all_tags}

Product name: {product_name}
Brand positioning: {brand_identity}
Ad shot:
{shot}

Please select 3-5 most appropriate tags and output as JSON array:""")
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
    
    selected_tags = json.loads(selected_tags_text)
    logger.info(f"Selected tags: {selected_tags}")
    
    # Step 3: Search images using tags
    logger.info("Step 3: Searching for style images")
    search_result = client.search_images(tags=selected_tags, page=1, limit=1)
    
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

