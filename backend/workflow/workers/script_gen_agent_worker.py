"""Script Generation Agent Worker - Generate advertising script using ReAct Agent"""

import logging
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .state import WorkflowState

# Import the Script Generation Agent
import sys
from pathlib import Path
agent_path = Path(__file__).resolve().parent.parent.parent / "agent"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))

from script_gen_agent import ScriptGenerationAgent, ScriptConfig

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Script Generation Agent: Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _generate_script_with_agent(product_name: str, brand_identity: str, must_have_shots: str, num_shots: int = 3):
    """Generate shots using Script Generation Agent with retry mechanism."""
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4", temperature=0.7)
    
    # Create agent
    agent = ScriptGenerationAgent(llm=llm, verbose=True)
    
    # Configure script generation
    script_config = ScriptConfig(
        product_name=product_name,
        brand_identity=brand_identity,
        must_have_shots=must_have_shots,
        num_shots=num_shots,
    )
    
    # Generate script
    result = agent.generate_script(script_config)
    
    # Clean up agent memory
    agent.reset()
    
    return result


def write_ad_script_with_agent(state: WorkflowState) -> dict:
    """
    Generate advertising script with shot list using Script Generation Agent.
    
    This worker uses a ReAct Agent that:
    - Understands requirements and brand identity
    - Optionally conducts market research using web_search
    - Generates creative shot ideas
    - Optimizes and refines shot descriptions
    - Stores results in memory
    
    Inputs:
    - product_name: Product name
    - brand_identity: Brand positioning
    - must_have_shots: Required shots (comma-separated)
    - num_shots: Number of shots to generate (default: 3)
    
    Outputs:
    - shots: List of shot descriptions (strings)
    """
    logger.info("=== Script Generation Agent: Generating ad shots ===")
    
    product_name = state["product_name"]
    brand_identity = state["brand_identity"]
    must_have_shots = state["must_have_shots"]
    num_shots = state.get("num_shots", 3)
    
    logger.info(f"Product: {product_name}")
    logger.info(f"Brand Identity: {brand_identity}")
    logger.info(f"Must-Have Shots: {must_have_shots}")
    logger.info(f"Requested number of shots: {num_shots}")
    
    # Call Script Generation Agent with retry mechanism
    script_result = _generate_script_with_agent(product_name, brand_identity, must_have_shots, num_shots)
    
    # Convert Shot objects to strings for workflow compatibility
    shots = [shot.description for shot in script_result.shots]
    
    # Log research notes if any
    if script_result.research_notes:
        logger.info(f"\nResearch notes captured: {len(script_result.research_notes)}")
        for note in script_result.research_notes:
            logger.info(f"  - {note}")
    
    logger.info(f"\nFinal: {script_result.total_shots} shots generated:")
    for i, shot in enumerate(shots, 1):
        logger.info(f"  {i}. {shot}")
    
    return {
        "shots": shots,
        "script_result": script_result,  # Store full result for potential future use
        "messages": [f"✓ Script Generation Agent: Generated {len(shots)} ad shots with ReAct reasoning"]
    }

