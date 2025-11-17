"""Real integration test for the Storyboard Generation Agent.

This example runs the agent with REAL external API calls:
- PixelHub for reference images
- MidJourney for storyboard generation
- Distortion Checker for quality validation
- Nanobanana for product integration

Make sure you have:
1. Set up necessary API keys/credentials
2. Internet connection
3. Sufficient API credits
"""

import logging
import json
import sys
import io
import os
import atexit
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from storyboard_gen_agent import (
    StoryboardAgent,
    EpisodeConfig,
    Beat,
    ProductConfig,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
_stdout_tee = None
_stderr_tee = None


class _StreamTee(io.TextIOBase):
    """Mirror writes to original stream and a log file."""

    def __init__(self, original: io.TextIOBase, log_path: Path):
        self._original = original
        self._log_file = open(log_path, "a", encoding="utf-8")
        atexit.register(self._log_file.close)

    def write(self, message: str) -> int:
        if not message:
            return 0
        self._original.write(message)
        self._original.flush()
        self._log_file.write(message)
        self._log_file.flush()
        return len(message)

    def flush(self):
        self._original.flush()
        self._log_file.flush()

    def __getattr__(self, name):
        return getattr(self._original, name)


def setup_storyboard_logging() -> Path:
    """Configure per-session logging file capturing stdout/stderr as well."""
    root_dir = Path(__file__).resolve().parents[1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = root_dir / f"storyboard_gen_agent_{timestamp}.log"
    os.environ["AD_AGENT_SESSION_LOG"] = str(log_path)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    global _stdout_tee, _stderr_tee
    if _stdout_tee is None:
        _stdout_tee = _StreamTee(sys.stdout, log_path)
        sys.stdout = _stdout_tee
    if _stderr_tee is None:
        _stderr_tee = _StreamTee(sys.stderr, log_path)
        sys.stderr = _stderr_tee

    logger.info(f"🗂️ Storyboard agent logs will also be saved to: {log_path}")
    return log_path


def main():
    """Run a real integration test of the storyboard generation agent."""
    setup_storyboard_logging()
    logger.info("="*80)
    logger.info("🎬 Starting REAL Storyboard Generation Test")
    logger.info("="*80)
    logger.info("\n⚠️  WARNING: This will call REAL external APIs!")
    logger.info("   - PixelHub API")
    logger.info("   - MidJourney API")
    logger.info("   - Distortion Checker")
    logger.info("   - Nanobanana API")
    logger.info("\n   Make sure you have proper credentials configured.\n")
    
    # Configure a simple test episode
    episode = EpisodeConfig(
        title="Morning Run - Real Momentum",
        product_config=ProductConfig(
            product_image_url="https://cdn.discordapp.com/attachments/1073330837912821780/1439534000434708523/7e037bea93156e1017ae3fd60ad8eb8d.jpg?ex=691ade02&is=69198c82&hm=51b9d20dc2ded19f649dbd376b2f577820bf47ee4f0505f471019a8a3ff80824",
            target_object="sports_shoes"
        ),
        beats=[
            Beat(
                beat=1,
                heading="Lace-Up Ritual",
                shot_description="Early morning light hits a quiet outdoor track; a young runner kneels down to tie their shoes",
                action="They pull the laces tight with a confident tug, tapping the heel to secure the fit"
            ),
            Beat(
                beat=2,
                heading="First Burst of Motion",
                shot_description="Close-up of the shoes hitting the ground, dust lifting slightly as they accelerate",
                action="They push off into a steady run, stride smooth and powerful, energy building with each step"
            ),
        ]
    )
    
    # Initialize LLM
    logger.info("🤖 Initializing LLM...")
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=4096,
        )
        logger.info("✓ Using OpenAI GPT-4o-mini")
    except Exception as e:
        logger.error(f"❌ Failed to initialize LLM: {e}")
        logger.error("\nPlease set up your OpenAI API key:")
        logger.error("  export OPENAI_API_KEY='your-key'")
        return
    
    # Initialize agent with REAL tools
    logger.info("\n📦 Initializing Storyboard Agent with REAL tools...")
    logger.info("   This will load all external API integrations...")
    
    try:
        agent = StoryboardAgent(
            llm=llm,
            verbose=True,
            max_iterations=50,
            max_execution_time=3600,  # 1 hour max
        )
        logger.info("✓ Agent initialized successfully")
        logger.info(f"✓ Loaded {len(agent.tools)} tools")
        
        # List the tools
        logger.info("\n🛠️  Available Tools:")
        for i, tool in enumerate(agent.tools, 1):
            logger.info(f"   {i}. {tool.name}")
        
    except Exception as e:
        logger.error(f"\n❌ Failed to initialize agent: {e}", exc_info=True)
        logger.error("\nPlease check:")
        logger.error("  - All required dependencies are installed")
        logger.error("  - API credentials are properly configured")
        logger.error("  - Tool modules are accessible")
        return
    
    # Process episode
    logger.info(f"\n{'='*80}")
    logger.info(f"🎥 Processing Episode: {episode.title}")
    logger.info(f"{'='*80}")
    logger.info(f"   Total beats: {len(episode.beats)}")
    logger.info(f"   Product: {episode.product_config.target_object}")
    logger.info(f"   Product Image: {episode.product_config.product_image_url}")
    
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
            logger.info(f"\n   {'='*70}")
            logger.info(f"   Beat {beat_result.beat_number}:")
            logger.info(f"   {'='*70}")
            logger.info(f"      Shot: {beat_result.shot_text[:80]}...")
            
            if beat_result.reference_image_url:
                logger.info(f"      Reference Image: {beat_result.reference_image_url}")
            
            if beat_result.color_palette:
                logger.info(f"      Color Palette: {', '.join(beat_result.color_palette)}")
            
            logger.info(f"      Storyboard Image: {beat_result.storyboard_image_url}")
            logger.info(f"      Final Image: {beat_result.final_image_url or 'N/A'}")
            
            logger.info(f"      Generation Attempts: {beat_result.total_attempts}")
            logger.info(f"      Quality Check Passed: {'✓' if beat_result.quality_check_passed else '✗'}")
            logger.info(f"      Product Integration: {'✓' if beat_result.product_replacement_success else '✗'}")
            
            if beat_result.attempts:
                logger.info(f"      Attempt Details:")
                for attempt in beat_result.attempts:
                    logger.info(f"         - Attempt {attempt.attempt_number}:")
                    logger.info(f"           Distortion Check: {'PASS' if attempt.distortion_check_passed else 'FAIL'}")
                    if not attempt.distortion_check_passed:
                        logger.info(f"           Distortions Found: {', '.join(attempt.distortion_labels)}")
            
            if beat_result.flagged_for_review:
                logger.warning(f"      ⚠️  FLAGGED FOR REVIEW: {beat_result.review_reason}")
            
            if beat_result.product_replacement_error:
                logger.warning(f"      ⚠️  Product Replacement Error: {beat_result.product_replacement_error}")
        
        # Export results to JSON
        output_file = f"episode_result_{result.episode_id}.json"
        logger.info(f"\n💾 Saving results to: {output_file}")
        
        with open(output_file, "w") as f:
            json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Results saved successfully")
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("🎉 Real integration test completed!")
        logger.info("="*80)
        
        if result.successful_beats == result.total_beats:
            logger.info("✅ All beats processed successfully!")
        elif result.successful_beats > 0:
            logger.info(f"⚠️  Partial success: {result.successful_beats}/{result.total_beats} beats successful")
        else:
            logger.warning("❌ No beats were processed successfully")
        
        if result.flagged_beats > 0:
            logger.warning(f"⚠️  {result.flagged_beats} beat(s) flagged for manual review")
        
        logger.info(f"\n📄 Full results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"\n❌ Episode processing failed: {e}", exc_info=True)
        raise
    
    logger.info("\n" + "="*80)
    logger.info("🏁 Test Complete")
    logger.info("="*80)


if __name__ == "__main__":
    main()
