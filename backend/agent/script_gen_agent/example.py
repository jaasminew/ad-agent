"""Example usage of the Script Generation Agent."""

import logging
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from workflow.utils.llm_factory import get_chat_model

from agent.script_gen_agent import ScriptGenerationAgent, ScriptConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run script generation example."""
    
    # Ensure API keys are set
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        return
    
    # Initialize LLM
    llm = get_chat_model(model="gpt-4", temperature=0.7)
    
    # Create agent
    agent = ScriptGenerationAgent(llm=llm, verbose=True)
    
    # Configure script generation
    script_config = ScriptConfig(
        product_name="Smart Watch X1",
        brand_identity="Young, tech-savvy, fitness-focused",
        must_have_shots="product closeup, workout scene, user smiling",
        num_shots=5,
    )
    
    logger.info("="*60)
    logger.info("Script Generation Example")
    logger.info("="*60)
    
    try:
        # Generate script
        result = agent.generate_script(script_config)
        
        logger.info("\n" + "="*60)
        logger.info("Generated Script Shots:")
        logger.info("="*60)
        
        for shot in result.shots:
            logger.info(f"\n{shot.shot_number}. {shot.description}")
        
        if result.research_notes:
            logger.info("\n" + "="*60)
            logger.info("Research Notes:")
            logger.info("="*60)
            for note in result.research_notes:
                logger.info(f"- {note}")
        
        logger.info("\n" + "="*60)
        logger.info(f"✓ Successfully generated {result.total_shots} shots")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Failed to generate script: {e}", exc_info=True)
    
    finally:
        # Clean up
        agent.reset()


if __name__ == "__main__":
    main()

