"""Script Writer Worker - Generate advertising script with shots"""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .state import WorkflowState
from workflow.prompts.script_writer import SCRIPT_WRITER_SYSTEM_PROMPT, SCRIPT_WRITER_USER_PROMPT

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Script Writer: Attempt {retry_state.attempt_number} failed, retrying in {retry_state.next_action.sleep} seconds..."
    )
)
def _generate_shots_with_retry(product_name: str, brand_identity: str, must_have_shots: str) -> str:
    """Generate shots with retry mechanism for LLM API calls."""
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", SCRIPT_WRITER_SYSTEM_PROMPT),
        ("user", SCRIPT_WRITER_USER_PROMPT)
    ])
    
    # Call LLM
    llm = ChatOpenAI(model="gpt-4", temperature=0.7)
    chain = prompt | llm
    
    response = chain.invoke({
        "product_name": product_name,
        "brand_identity": brand_identity,
        "must_have_shots": must_have_shots,
    })
    
    return response.content.strip()


def write_ad_script(state: WorkflowState) -> dict:
    """
    Generate advertising script with shot list.
    
    Inputs:
    - product_name: Product name
    - brand_identity: Brand positioning
    - must_have_shots: Required shots (comma-separated)
    
    Outputs:
    - shots: List of shot descriptions
    """
    logger.info("=== Script Writer: Generating ad shots ===")
    
    product_name = state["product_name"]
    brand_identity = state["brand_identity"]
    must_have_shots = state["must_have_shots"]
    
    # Call LLM with retry mechanism
    shots_text = _generate_shots_with_retry(product_name, brand_identity, must_have_shots)
    
    # Parse shot list
    shots = [line.strip() for line in shots_text.split("\n") if line.strip()]
    
    # Limit to maximum 3 shots
    max_shots = 3
    if len(shots) > max_shots:
        logger.info(f"Generated {len(shots)} shots, limiting to {max_shots}")
        shots = shots[:max_shots]
    
    logger.info(f"Generated {len(shots)} shots:")
    for i, shot in enumerate(shots, 1):
        logger.info(f"  {i}. {shot}")
    
    return {
        "shots": shots,
        "messages": [f"✓ Script Writer: Generated {len(shots)} ad shots"]
    }

