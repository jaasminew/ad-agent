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


def _generate_script_with_agent_streaming(
    product_name: str, 
    brand_identity: str, 
    must_have_shots: str, 
    num_shots: int = 3,
    task_manager=None,
    task_id=None
):
    """Generate shots using Script Generation Agent with real-time streaming of intermediate steps."""
    # Import callback handler from correct location (LangChain 1.0+)
    try:
        from langchain_core.callbacks.base import BaseCallbackHandler
    except ImportError:
        from langchain.callbacks.base import BaseCallbackHandler
    
    # Import WorkflowStage (need to import as a package)
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from service.models import WorkflowStage
    
    # Custom callback to capture agent's thoughts and actions
    class StreamingCallback(BaseCallbackHandler):
        def __init__(self, task_manager, task_id):
            self.task_manager = task_manager
            self.task_id = task_id
            self.step_count = 0
        
        def on_agent_action(self, action, **kwargs):
            """Called when agent decides on an action"""
            if self.task_manager and self.task_id:
                self.step_count += 1
                
                # Extract and display Thought from action log
                thought_text = ""
                if hasattr(action, 'log') and action.log and 'Action:' in action.log:
                    parts = action.log.split('Action:', 1)
                    if parts and parts[0]:
                        thought_part = parts[0].replace('Thought:', '').strip()
                        if thought_part:
                            thought_text = thought_part
                
                # Push thought to frontend
                if thought_text:
                    self.task_manager.add_llm_output(
                        task_id=self.task_id,
                        stage=WorkflowStage.SCRIPT_GEN_AGENT,
                        message=f"💭 {thought_text}",
                        output={"type": "thought"},
                    )
                
                # Send simple tool call message (only tool name, no parameters)
                tool_name = action.tool
                message = f"🔧 Calling tool: {tool_name}"
                
                self.task_manager.add_llm_output(
                    task_id=self.task_id,
                    stage=WorkflowStage.SCRIPT_GEN_AGENT,
                    message=message,
                    output={"type": "tool_call", "tool": tool_name},
                )
        
        def on_tool_end(self, output, **kwargs):
            """Called when tool finishes"""
            # 工具执行完成,不输出任何内容到前端
            # 只记录到日志用于调试
            if self.task_manager and self.task_id:
                output_str = str(output)
                if len(output_str) > 200:
                    output_str = output_str[:200] + "..."
                logger.debug(f"[Script Gen Agent] Tool output (internal): {output_str}")
    
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
    
    # Generate script with callbacks
    try:
        if task_manager and task_id:
            # Use custom callback for streaming
            callbacks = [StreamingCallback(task_manager, task_id)]
            
            # Build input prompt (same logic as agent.generate_script)
            from script_gen_agent.prompt_templates import SCRIPT_GENERATION_PROMPT
            input_prompt = SCRIPT_GENERATION_PROMPT.format(
                product_name=script_config.product_name,
                brand_identity=script_config.brand_identity,
                must_have_shots=script_config.must_have_shots,
                num_shots=script_config.num_shots,
            )
            
            # Execute agent with callbacks
            result_dict = agent.executor.invoke(
                {"input": input_prompt},
                config={"callbacks": callbacks}
            )
            
            # Parse result (reuse agent's parsing logic)
            result = agent._extract_script_result(
                agent_output=result_dict,
                num_shots=script_config.num_shots,
            )
        else:
            # No streaming, use normal generate_script
            result = agent.generate_script(script_config)
    finally:
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
    # Import from service module (need to import as a package)
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from service.task_manager import TaskContext, get_task_manager
    
    logger.info("=== Script Generation Agent: Generating ad shots ===")
    
    product_name = state["product_name"]
    brand_identity = state["brand_identity"]
    must_have_shots = state["must_have_shots"]
    num_shots = state.get("num_shots", 3)
    
    logger.info(f"Product: {product_name}")
    logger.info(f"Brand Identity: {brand_identity}")
    logger.info(f"Must-Have Shots: {must_have_shots}")
    logger.info(f"Requested number of shots: {num_shots}")
    
    # Get task manager for real-time updates
    task_id = TaskContext.get_task_id()
    task_manager = get_task_manager() if task_id else None
    
    # Call Script Generation Agent with custom callback for intermediate steps
    script_result = _generate_script_with_agent_streaming(
        product_name, brand_identity, must_have_shots, num_shots,
        task_manager=task_manager, task_id=task_id
    )
    
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
    
    # 输出最终结果 (传递给下一个节点的数据)
    if task_manager and task_id:
        from service.models import WorkflowStage
        
        result_message = f"✅ Script generation completed\nGenerated {len(shots)} shots:"
        for i, shot in enumerate(shots, 1):
            # 截断过长的描述
            shot_preview = shot if len(shot) <= 80 else shot[:77] + "..."
            result_message += f"\n  {i}. {shot_preview}"
        
        task_manager.add_llm_output(
            task_id=task_id,
            stage=WorkflowStage.SCRIPT_GEN_AGENT,
            message=result_message,
            output={
                "type": "result",
                "total_shots": len(shots),
                "shots": shots,
            },
        )
    
    return {
        "shots": shots,
        "script_result": script_result,  # Store full result for potential future use
        "messages": [f"✓ Script Generation Agent: Generated {len(shots)} ad shots with ReAct reasoning"]
    }

