"""AD Agent Workflow - Generate advertising videos using AI"""

import logging
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from workers import (
    WorkflowState,
    write_ad_script,
    search_style_image,
    extract_palette,
    generate_midjourney_image,
    check_distortion,
    compose_with_product,
    generate_video,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("=" * 80)
logger.info("AD Agent Workflow - Generate Advertising Videos")
logger.info("=" * 80)


# ==================== Conditional Edge Functions ====================

def should_retry_midjourney(state: WorkflowState) -> str:
    """
    Decide whether to retry Midjourney generation based on distortion check.
    
    Returns:
        - "retry": If distortion detected and retry count < max retries
        - "compose": If no distortion or max retries reached
    """
    max_retries = 3
    retry_count = state.get("distortion_retry_count", 0)
    check_result = state.get("distortion_check_result", {})
    has_distortion = check_result.get("has_distortion", False)
    
    if has_distortion and retry_count < max_retries:
        logger.warning("Distortion detected, retrying Midjourney (attempt %d/%d)", retry_count, max_retries)
        return "retry"
    elif has_distortion and retry_count >= max_retries:
        logger.warning("Max retries reached, proceeding despite distortion")
        return "compose"
    else:
        logger.info("No distortion detected, proceeding to composition")
        return "compose"


# ==================== Build Workflow Graph ====================

def build_workflow() -> StateGraph:
    """
    Build the AD Agent workflow graph.
    
    Workflow steps:
    1. write_ad_script: Generate advertising script with shots
    2. search_style_image: Search for style reference image
    3. extract_palette: Extract dominant colors from style image
    4. generate_midjourney_image: Generate scene image with Midjourney
    5. check_distortion: Check for anatomical distortions
       - If distortion detected: retry from step 4 (max 3 times)
       - If clean or max retries: proceed to step 6
    6. compose_with_product: Compose product into scene with Nanobanana
    7. generate_video: Generate final video with Veo 3.1
    """
    logger.info("Building workflow graph...")
    
    # Create state graph
    graph = StateGraph(WorkflowState)
    
    # Add nodes
    graph.add_node("write_script", write_ad_script)
    graph.add_node("search_style", search_style_image)
    graph.add_node("extract_palette", extract_palette)
    graph.add_node("generate_image", generate_midjourney_image)
    graph.add_node("check_distortion", check_distortion)
    graph.add_node("compose_product", compose_with_product)
    graph.add_node("generate_video", generate_video)
    
    # Build linear flow with conditional loop for distortion check
    graph.add_edge(START, "write_script")
    graph.add_edge("write_script", "search_style")
    graph.add_edge("search_style", "extract_palette")
    graph.add_edge("extract_palette", "generate_image")
    graph.add_edge("generate_image", "check_distortion")
    
    # Conditional edge: retry if distortion detected
    graph.add_conditional_edges(
        "check_distortion",
        should_retry_midjourney,
        {
            "retry": "generate_image",  # Loop back to regenerate
            "compose": "compose_product"  # Continue to next step
        }
    )
    
    graph.add_edge("compose_product", "generate_video")
    graph.add_edge("generate_video", END)
    
    logger.info("✓ Workflow graph built successfully")
    logger.info("  Flow: write_script -> search_style -> extract_palette")
    logger.info("        -> generate_image -> check_distortion")
    logger.info("        -> [retry loop if distortion]")
    logger.info("        -> compose_product -> generate_video")
    
    return graph


# ==================== Main Execution ====================

def run_ad_workflow(
    product_name: str,
    brand_identity: str,
    product_images: str,
    must_have_shots: str
) -> dict:
    """
    Run the complete AD Agent workflow.
    
    Args:
        product_name: Product name
        brand_identity: Brand positioning/identity
        product_images: Product image URL
        must_have_shots: Required shots (comma-separated)
    
    Returns:
        Final state dict containing all intermediate results and final video URL
    """
    logger.info("\n" + "=" * 80)
    logger.info("Starting AD Agent Workflow")
    logger.info("=" * 80)
    logger.info(f"Product: {product_name}")
    logger.info(f"Brand Identity: {brand_identity}")
    logger.info(f"Product Images: {product_images}")
    logger.info(f"Must Have Shots: {must_have_shots}")
    logger.info("=" * 80 + "\n")
    
    # Build and compile workflow
    graph = build_workflow()
    app = graph.compile()
    
    # Initialize state
    initial_state = {
        "product_name": product_name,
        "brand_identity": brand_identity,
        "product_images": product_images,
        "must_have_shots": must_have_shots,
        "distortion_retry_count": 0,
        "messages": [],
    }
    
    # Execute workflow
    logger.info("Executing workflow...\n")
    final_state = app.invoke(initial_state)
    
    # Log completion
    logger.info("\n" + "=" * 80)
    logger.info("Workflow Completed Successfully!")
    logger.info("=" * 80)
    
    # Print summary
    logger.info("\nWorkflow Summary:")
    logger.info(f"  - Generated {len(final_state.get('shots', []))} shots")
    logger.info(f"  - Style image: {final_state.get('style_image_url', 'N/A')}")
    logger.info(f"  - Midjourney image: {final_state.get('midjourney_image_url', 'N/A')}")
    logger.info(f"  - Distortion retries: {final_state.get('distortion_retry_count', 0)}")
    logger.info(f"  - Composed image: {final_state.get('nanobanana_image_url', 'N/A')}")
    logger.info(f"  - Final video: {final_state.get('video_url', 'N/A')}")
    
    # Print messages
    if final_state.get("messages"):
        logger.info("\nStep-by-step Messages:")
        for msg in final_state["messages"]:
            logger.info(f"  {msg}")
    
    return final_state


if __name__ == "__main__":
    # Example usage
    result = run_ad_workflow(
        product_name="Polaroid Camera",
        brand_identity="Nostalgia, Artistic, Instant Sharing, Creativity, Authenticity",
        product_images="https://m.media-amazon.com/images/I/71a0-JzaiEL._AC_SL1500_.jpg",
        must_have_shots="Scenes of friends instantly sharing photos"
    )
    
    print("\n" + "=" * 80)
    print("🎬 Final Output")
    print("=" * 80)
    print(f"Video URL: {result.get('video_url')}")
    print("=" * 80)
