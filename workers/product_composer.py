"""Product Composer Worker - Compose product into scene using Nanobanana"""

import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from tools.nanobanana import get_nanobanana_client
from .state import WorkflowState

logger = logging.getLogger(__name__)


def compose_with_product(state: WorkflowState) -> dict:
    """
    Compose product image into Midjourney generated scene using Nanobanana.
    
    Inputs:
    - midjourney_image_url: Midjourney generated scene image URL
    - product_images: Product image URL
    - shots: List of shot descriptions (for prompt generation)
    
    Outputs:
    - nanobanana_image_url: Composed image URL (with product in scene)
    """
    logger.info("=== Product Composer: Composing product into scene ===")
    
    midjourney_image_url = state["midjourney_image_url"]
    product_images = state["product_images"]
    shots = state["shots"]
    
    # Step 1: Generate composition prompt using LLM
    logger.info("Step 1: Generating composition prompt")
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a professional image composition expert. Generate a clear, concise prompt for placing a product into an advertising scene.

CRITICAL REQUIREMENTS:
1. Write prompt in English
2. The product should be ADDED to the scene, NOT replacing anything unless it is absolutely necessary(e.g. the product is a replacement for a different product in the scene).
3. Keep ALL existing elements in the scene (people, furniture, atmosphere) UNCHANGED
4. Only describe where and how to place the NEW product
5. Use phrases like "add", "place", "integrate", "include" - NEVER "replace", "change", "transform"
6. The product should feel naturally placed in the scene
7. Output only the prompt text

Example good prompt: "Add the product naturally in the foreground while keeping all existing scene elements intact"
Example bad prompt: "Replace the items with the product" (This is wrong!)"""),
        ("user", """Ad shot description (using first one):
{first_shot}

Generate a prompt that ADDS the product to this scene while KEEPING all existing elements (people, objects, atmosphere) completely unchanged:""")
    ])
    
    llm = ChatOpenAI(model="gpt-4", temperature=0.5)
    chain = prompt_template | llm
    
    first_shot = shots[0] if shots else "product showcase in scene"
    
    response = chain.invoke({
        "first_shot": first_shot,
    })
    
    composition_prompt = response.content.strip()
    logger.info(f"Generated composition prompt: {composition_prompt}")
    
    # Step 2: Call Nanobanana to compose images
    logger.info("Step 2: Calling Nanobanana to compose images")
    client = get_nanobanana_client()
    
    # Nanobanana takes multiple input images: [scene_image, product_image] + prompt
    result = client.generate_image(
        prompt=composition_prompt,
        input_image_paths=[midjourney_image_url, product_images],
        upload_to_cos=True
    )
    
    if not result["success"]:
        raise RuntimeError(f"Nanobanana generation failed: {result.get('error')}")
    
    # Get composed image URL (COS URL if available, else local path)
    composed_image_url = result.get("cos_url") or result.get("local_path")
    
    logger.info(f"Product composition complete: {composed_image_url}")
    
    return {
        "nanobanana_image_url": composed_image_url,
        "messages": [f"✓ Product Composer: Created composed image {composed_image_url}"]
    }

