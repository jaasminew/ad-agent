"""Script Writer Worker - Generate advertising script with shots"""

import logging
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from .state import WorkflowState

logger = logging.getLogger(__name__)


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
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a professional advertising creative director who excels at writing compelling ad scripts.
You need to create a creative shot list for advertisements based on product information and brand positioning.

Requirements:
1. Each shot should be concise and clear, describing specific visual content
2. Shots must align with brand positioning and tone
3. Must include user-specified required shots
4. Usually contains 3-5 shots forming a complete story arc
5. One shot per line, no numbering needed

Please output the shot list directly, one shot per line, without any extra text."""),
        ("user", """Product name: {product_name}
Brand positioning: {brand_identity}
Required shots: {must_have_shots}

Please create an advertising shot list for this product:""")
    ])
    
    # Call LLM
    llm = ChatOpenAI(model="gpt-4", temperature=0.7)
    chain = prompt | llm
    
    response = chain.invoke({
        "product_name": product_name,
        "brand_identity": brand_identity,
        "must_have_shots": must_have_shots,
    })
    
    # Parse shot list
    shots_text = response.content.strip()
    shots = [line.strip() for line in shots_text.split("\n") if line.strip()]
    
    logger.info(f"Generated {len(shots)} shots:")
    for i, shot in enumerate(shots, 1):
        logger.info(f"  {i}. {shot}")
    
    return {
        "shots": shots,
        "messages": [f"✓ Script Writer: Generated {len(shots)} ad shots"]
    }

