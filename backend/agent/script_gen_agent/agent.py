"""Main Script Generation Agent implementation."""

import logging
import re
from typing import Optional
try:
    # Try newer langchain structure
    from langchain_classic.agents import AgentExecutor, create_react_agent
except ImportError:
    # Fallback to older langchain structure
    from langchain.agents import AgentExecutor, create_react_agent
try:
    from langchain_classic.prompts import PromptTemplate
except ImportError:
    from langchain.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel

from .models import ScriptConfig, ScriptResult, Shot
from .tools import get_script_gen_tools
from .prompt_templates import SYSTEM_PROMPT, SCRIPT_GENERATION_PROMPT

logger = logging.getLogger(__name__)


class ScriptGenerationAgent:
    """
    LangChain ReAct Agent for generating advertising script with shots.
    
    This agent orchestrates the full workflow:
    1. Understand requirements (product, brand, must-have shots)
    2. Conduct market research (optional, using web_search)
    3. Generate creative shot ideas
    4. Optimize and refine shots
    5. Store results in memory
    """
    
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        verbose: bool = True,
        max_iterations: int = 30,
        max_execution_time: Optional[float] = None,
    ):
        """
        Initialize the Script Generation Agent.
        
        Args:
            llm: Language model to use (must be provided - supports any LangChain chat model)
            verbose: Whether to print detailed execution logs
            max_iterations: Maximum iterations for the agent
            max_execution_time: Maximum execution time in seconds
        """
        # Initialize LLM
        if llm is None:
            raise ValueError(
                "LLM must be provided. Example:\n"
                "  from langchain_openai import ChatOpenAI\n"
                "  llm = ChatOpenAI(model='gpt-4', temperature=0.7)\n"
                "  agent = ScriptGenerationAgent(llm=llm)\n"
                "\n"
                "Or with Anthropic:\n"
                "  from langchain_anthropic import ChatAnthropic\n"
                "  llm = ChatAnthropic(model='claude-sonnet-4-20250514', temperature=0.7)\n"
                "  agent = ScriptGenerationAgent(llm=llm)"
            )
        else:
            self.llm = llm
            logger.info(f"✓ Using provided LLM: {type(llm).__name__}")
        
        # Load tools
        self.tools = get_script_gen_tools()
        logger.info(f"✓ Loaded {len(self.tools)} tools")
        
        # Create ReAct agent
        self.agent = self._create_react_agent()
        
        # Create agent executor
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=verbose,
            max_iterations=max_iterations,
            max_execution_time=max_execution_time,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )
        logger.info("✓ Agent executor initialized")
    
    def _create_react_agent(self):
        """Create the ReAct agent with system prompt."""
        # Create prompt template for ReAct
        template = f"""{SYSTEM_PROMPT}

{{tools}}

Use the following format:

Question: the input question/task you must solve
Thought: you should always think about what to do
Action: the action to take, should be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now have completed the task
Final Answer: the final summary of what was accomplished

Begin!

Question: {{input}}
Thought: {{agent_scratchpad}}
"""
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "tools", "tool_names", "agent_scratchpad"],
        )
        
        return create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )
    
    def generate_script(self, script_config: ScriptConfig) -> ScriptResult:
        """
        Generate advertising script with shots.
        
        Args:
            script_config: Script configuration with product info
            
        Returns:
            ScriptResult with generated shots
        """
        logger.info("🎬 Starting script generation")
        logger.info(f"   Product: {script_config.product_name}")
        logger.info(f"   Brand: {script_config.brand_identity}")
        logger.info(f"   Must-have shots: {script_config.must_have_shots}")
        logger.info(f"   Number of shots: {script_config.num_shots}")
        
        # Build input prompt for agent
        input_prompt = SCRIPT_GENERATION_PROMPT.format(
            product_name=script_config.product_name,
            brand_identity=script_config.brand_identity,
            must_have_shots=script_config.must_have_shots,
            num_shots=script_config.num_shots,
        )
        
        logger.debug(f"Agent input prompt: {input_prompt}")
        
        # Execute agent
        try:
            result = self.executor.invoke({"input": input_prompt})
            
            logger.info("Agent execution completed")
            logger.debug(f"Agent output: {result.get('output', '')[:200]}...")
            
            # Parse the result
            script_result = self._extract_script_result(
                agent_output=result,
                num_shots=script_config.num_shots,
            )
            
            logger.info(f"✓ Generated {script_result.total_shots} shots")
            for shot in script_result.shots:
                logger.info(f"   {shot.shot_number}. {shot.description}")
            
            return script_result
            
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise
    
    def _extract_script_result(
        self,
        agent_output: dict,
        num_shots: int,
    ) -> ScriptResult:
        """
        Extract ScriptResult from agent's execution output.
        
        This method parses the agent's final answer to extract the generated shots.
        
        Args:
            agent_output: Agent execution output
            num_shots: Expected number of shots
            
        Returns:
            Populated ScriptResult
        """
        final_answer = agent_output.get("output", "")
        
        # Parse shots from final answer
        shots = self._parse_shots_from_text(final_answer)
        
        # Validate shot count
        if len(shots) != num_shots:
            logger.warning(
                f"Expected {num_shots} shots but got {len(shots)}. "
                f"This might be acceptable if the agent made a justified decision."
            )
        
        # Extract research notes from intermediate steps
        research_notes = self._extract_research_notes(agent_output)
        
        return ScriptResult(
            shots=shots,
            total_shots=len(shots),
            research_notes=research_notes,
        )
    
    def _parse_shots_from_text(self, text: str) -> list[Shot]:
        """
        Parse shots from the final answer text.
        
        Expected format:
        1. [shot description]
        2. [shot description]
        3. [shot description]
        
        Args:
            text: Text to parse
            
        Returns:
            List of Shot objects
        """
        shots = []
        
        # Match numbered lines: "1. description", "2. description", etc.
        pattern = r'^\s*(\d+)\.\s*(.+)$'
        
        lines = text.strip().split('\n')
        for line in lines:
            match = re.match(pattern, line.strip())
            if match:
                shot_number = int(match.group(1))
                description = match.group(2).strip()
                shots.append(Shot(
                    shot_number=shot_number,
                    description=description,
                ))
        
        return shots
    
    def _extract_research_notes(self, agent_output: dict) -> list[str]:
        """
        Extract research notes from agent's intermediate steps.
        
        Args:
            agent_output: Agent execution output
            
        Returns:
            List of research notes
        """
        notes = []
        
        intermediate_steps = agent_output.get("intermediate_steps", [])
        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                # Check if this was a web_search action
                if hasattr(action, 'tool') and action.tool == 'web_search':
                    notes.append(f"Research: {action.tool_input}")
        
        return notes
    
    def reset(self):
        """Reset the agent state."""
        # Clear memory
        from tools.memory import MEM
        MEM.clear()
        
        logger.info("🔄 Agent state reset")

