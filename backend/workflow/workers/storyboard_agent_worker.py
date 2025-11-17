"""Storyboard Agent Worker - 集成 Storyboard Agent 到 Workflow"""

import logging
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add agent directory to Python path
agent_dir = Path(__file__).resolve().parent.parent.parent / "agent"
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from storyboard_gen_agent import (
    StoryboardAgent,
    EpisodeConfig,
    Beat,
    ProductConfig,
    EpisodeResult,
)

logger = logging.getLogger(__name__)


def create_storyboard_agent(llm=None) -> StoryboardAgent:
    """
    Create and configure a Storyboard Agent instance.
    
    Args:
        llm: Optional pre-configured LLM. If not provided, will create GPT-4o-mini.
    
    Returns:
        StoryboardAgent instance
    """
    if llm is None:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=4096,
            )
            logger.info("✓ Using OpenAI GPT-4o-mini for Storyboard Agent")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM: {e}")
            raise
    
    agent = StoryboardAgent(
        llm=llm,
        verbose=True,
        max_iterations=50,
        max_execution_time=3600,  # 1 hour max
    )
    
    logger.info(f"✓ Storyboard Agent initialized with {len(agent.tools)} tools")
    return agent


def parse_shot_to_beat(shot: str, index: int) -> Beat:
    """
    Parse a shot description into a Beat object.
    
    Expected shot format examples:
    - "Scene: Morning coffee shop. Action: Opens laptop and smiles"
    - "A person running on the beach at sunset"
    
    Args:
        shot: Shot description string
        index: Beat number (1-based)
    
    Returns:
        Beat object
    """
    # Simple parsing: split by common patterns
    parts = shot.split(".", 1)
    
    if len(parts) >= 2:
        # Has structure like "Scene description. Action description"
        heading = f"Shot {index}"
        shot_description = parts[0].strip()
        action = parts[1].strip() if len(parts) > 1 else "Camera follows the scene"
    else:
        # Single description
        heading = f"Shot {index}"
        shot_description = shot.strip()
        action = "Camera follows the scene"
    
    return Beat(
        beat=index,
        heading=heading,
        shot_description=shot_description,
        action=action,
    )


def extract_uploaded_final_urls(episode_result: EpisodeResult) -> List[str]:
    """
    Extract uploaded_final_urls from episode_result.global_memory.
    
    Args:
        episode_result: EpisodeResult from Storyboard Agent
    
    Returns:
        List of final image URLs
    """
    # Method 1: From global_memory (recommended)
    for item in episode_result.global_memory:
        if item.startswith("uploaded_final_urls:"):
            try:
                urls_json = item.split(":", 1)[1].strip()
                return json.loads(urls_json)
            except Exception as e:
                logger.warning(f"Failed to parse uploaded_final_urls from global_memory: {e}")
                break
    
    # Method 2: Fallback to beats collection
    logger.info("Falling back to collecting final_image_url from beats")
    final_urls = [
        beat.final_image_url
        for beat in episode_result.beats
        if beat.final_image_url and beat.product_replacement_success
    ]
    
    return final_urls


def run_storyboard_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run Storyboard Agent to generate composed images for all shots.
    
    This replaces the original steps 2-6:
    - search_style_image
    - extract_palette
    - generate_midjourney_image
    - check_distortion
    - compose_with_product
    
    Input from state:
    - product_name: Product name
    - brand_identity: Brand identity (used for title)
    - product_images: Product image URL
    - shots: List of shot descriptions
    
    Output to state:
    - episode_result: Complete EpisodeResult from Storyboard Agent
    - nanobanana_images: List of final composed image URLs (from uploaded_final_urls)
    - messages: Log messages
    """
    logger.info("\n" + "=" * 80)
    logger.info("Running Storyboard Agent (Black Box)")
    logger.info("=" * 80)
    
    product_name = state["product_name"]
    brand_identity = state["brand_identity"]
    product_images = state["product_images"]
    shots = state["shots"]
    
    logger.info(f"Product: {product_name}")
    logger.info(f"Brand Identity: {brand_identity}")
    logger.info(f"Product Image: {product_images}")
    logger.info(f"Total shots: {len(shots)}")
    
    # Parse shots into beats
    logger.info("\nParsing shots into beats...")
    beats = [parse_shot_to_beat(shot, i + 1) for i, shot in enumerate(shots)]
    
    for beat in beats:
        logger.info(f"  Beat {beat.beat}: {beat.heading}")
        logger.info(f"    Scene: {beat.shot_description}")
        logger.info(f"    Action: {beat.action}")
    
    # Create episode config
    episode_config = EpisodeConfig(
        title=f"{product_name} - {brand_identity[:50]}",
        product_config=ProductConfig(
            product_image_url=product_images,
            target_object=product_name.lower().replace(" ", "_"),
        ),
        beats=beats,
    )
    
    logger.info(f"\nEpisode Config:")
    logger.info(f"  Title: {episode_config.title}")
    logger.info(f"  Target Object: {episode_config.product_config.target_object}")
    logger.info(f"  Total Beats: {len(episode_config.beats)}")
    
    # Create and run agent
    logger.info("\nInitializing Storyboard Agent...")
    agent = create_storyboard_agent()
    
    logger.info("\nProcessing episode with Storyboard Agent...")
    logger.info("(This will take several minutes depending on the number of beats)")
    
    try:
        episode_result = agent.process_episode(episode_config)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Storyboard Agent Completed")
        logger.info("=" * 80)
        logger.info(f"Episode ID: {episode_result.episode_id}")
        logger.info(f"Total Beats: {episode_result.total_beats}")
        logger.info(f"Successful: {episode_result.successful_beats}")
        logger.info(f"Flagged: {episode_result.flagged_beats}")
        
        # Extract uploaded_final_urls
        nanobanana_images = extract_uploaded_final_urls(episode_result)
        
        logger.info(f"\n📸 Generated Images:")
        logger.info(f"  Total: {len(nanobanana_images)}")
        for i, url in enumerate(nanobanana_images, 1):
            logger.info(f"  {i}. {url}")
        
        # Log any flagged beats
        flagged_beats = [beat for beat in episode_result.beats if beat.flagged_for_review]
        if flagged_beats:
            logger.warning(f"\n⚠️  {len(flagged_beats)} beat(s) flagged for review:")
            for beat in flagged_beats:
                logger.warning(f"  Beat {beat.beat_number}: {beat.review_reason}")
        
        return {
            "episode_result": episode_result,
            "nanobanana_images": nanobanana_images,
            "messages": [
                f"✓ Storyboard Agent processed {episode_result.total_beats} beats",
                f"✓ Successfully generated {len(nanobanana_images)} composed images",
            ],
        }
        
    except Exception as e:
        logger.error(f"\n❌ Storyboard Agent failed: {e}", exc_info=True)
        raise

