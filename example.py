"""Example usage of the Storyboard Generation Agent."""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from storyboard_gen_agent import (
    StoryboardAgent,
    EpisodeConfig,
    Beat,
    ProductConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run a simple example episode."""
    
    # Configure episode
    episode = EpisodeConfig(
        title="Creative Workspace - Summer Campaign",
        product_config=ProductConfig(
            product_image_url="https://example.com/product-laptop.png",
            target_object="laptop"
        ),
        beats=[
            Beat(
                beat=1,
                heading="Morning Coffee Shop",
                shot_description="A young creative professional sits by a large sunlit window in a cozy coffee shop",
                action="Opens their laptop and smiles while reading an email, morning light streaming in"
            ),
            Beat(
                beat=2,
                heading="Collaborative Brainstorm",
                shot_description="A diverse team of four people gathered around a wooden table, laptops open, sticky notes on the wall",
                action="Team members gesture enthusiastically while discussing ideas, one person takes notes on their laptop"
            ),
            Beat(
                beat=3,
                heading="Outdoor Innovation",
                shot_description="A person working on a laptop in a vibrant urban park, trees and city skyline in background",
                action="Types intently while sipping from a reusable water bottle, looking inspired and focused"
            ),
        ]
    )
    
    logger.info("="*80)
    logger.info("🎬 Starting Storyboard Generation Example")
    logger.info("="*80)
    
    # Initialize LLM (using OpenAI GPT-4o)
    logger.info("\n🤖 Initializing LLM...")
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model="gpt-4o",  # GPT-4o (ChatGPT-5 class model)
        temperature=0.7,
        max_tokens=4096,
    )
    
    # Initialize agent
    logger.info("\n📦 Initializing Storyboard Agent...")
    agent = StoryboardAgent(
        llm=llm,
        verbose=True,
        max_iterations=50,
        max_execution_time=3600,  # 1 hour max
    )
    
    # Process episode
    logger.info(f"\n🎥 Processing Episode: {episode.title}")
    logger.info(f"   Total beats: {len(episode.beats)}")
    logger.info(f"   Product: {episode.product_config.target_object}")
    
    try:
        result = agent.process_episode(episode)
        
        # Print results
        logger.info("\n" + "="*80)
        logger.info("✅ EPISODE COMPLETED")
        logger.info("="*80)
        logger.info(f"Episode ID: {result.episode_id}")
        logger.info(f"Title: {result.title}")
        logger.info(f"Episode Palette: {result.episode_palette}")
        logger.info(f"\n📊 Statistics:")
        logger.info(f"   Total beats: {result.total_beats}")
        logger.info(f"   Successful: {result.successful_beats}")
        logger.info(f"   Flagged for review: {result.flagged_beats}")
        
        logger.info(f"\n🎞️  Beat Results:")
        for beat_result in result.beats:
            logger.info(f"\n   Beat {beat_result.beat_number}:")
            logger.info(f"      Shot: {beat_result.shot_text[:60]}...")
            logger.info(f"      Reference: {beat_result.reference_image_url}")
            logger.info(f"      Storyboard: {beat_result.storyboard_image_url}")
            logger.info(f"      Final: {beat_result.final_image_url}")
            logger.info(f"      Attempts: {beat_result.total_attempts}")
            logger.info(f"      Quality Passed: {'✓' if beat_result.quality_check_passed else '✗'}")
            logger.info(f"      Product Integrated: {'✓' if beat_result.product_replacement_success else '✗'}")
            
            if beat_result.flagged_for_review:
                logger.warning(f"      ⚠️  FLAGGED: {beat_result.review_reason}")
        
        # Export results as JSON
        import json
        output_file = f"episode_result_{result.episode_id}.json"
        with open(output_file, "w") as f:
            json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
        logger.info(f"\n💾 Results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"\n❌ Episode processing failed: {e}", exc_info=True)
        raise
    
    logger.info("\n" + "="*80)
    logger.info("🏁 Example Complete")
    logger.info("="*80)


if __name__ == "__main__":
    main()

