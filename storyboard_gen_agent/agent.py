"""Main Storyboard Generation Agent implementation."""

import logging
import uuid
from typing import Optional, List
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel

from .models import (
    Beat,
    EpisodeConfig,
    BeatResult,
    EpisodeResult,
    GenerationAttempt,
    ProductConfig,
)
from .tools import get_storyboard_tools
from .prompt_templates import SYSTEM_PROMPT, BEAT_PROCESSING_PROMPT
from .utils import normalize_beat, extract_color_palette

logger = logging.getLogger(__name__)


class StoryboardAgent:
    """
    LangChain ReAct Agent for generating storyboard frames from script beats.
    
    This agent orchestrates the full workflow:
    1. Find reference images (PixelHub)
    2. Extract and manage color palette
    3. Generate storyboards with quality checks (MidJourney + Distortion Checker)
    4. Integrate products into final images (Nanobanana)
    5. Store results in memory
    """
    
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        verbose: bool = True,
        max_iterations: int = 50,
        max_execution_time: Optional[float] = None,
    ):
        """
        Initialize the Storyboard Generation Agent.
        
        Args:
            llm: Language model to use (must be provided - supports any LangChain chat model)
            verbose: Whether to print detailed execution logs
            max_iterations: Maximum iterations for the agent
            max_execution_time: Maximum execution time in seconds
        """
        # Initialize LLM
        if llm is None:
            # Require LLM to be provided to avoid dependency on specific provider
            raise ValueError(
                "LLM must be provided. Example:\n"
                "  from langchain_openai import ChatOpenAI\n"
                "  llm = ChatOpenAI(model='gpt-4', temperature=0.7)\n"
                "  agent = StoryboardAgent(llm=llm)\n"
                "\n"
                "Or with Anthropic:\n"
                "  from langchain_anthropic import ChatAnthropic\n"
                "  llm = ChatAnthropic(model='claude-sonnet-4-20250514', temperature=0.7)\n"
                "  agent = StoryboardAgent(llm=llm)"
            )
        else:
            self.llm = llm
            logger.info(f"✓ Using provided LLM: {type(llm).__name__}")
        
        # Load tools
        self.tools = get_storyboard_tools()
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
        
        # State tracking
        self.episode_id: Optional[str] = None
        self.episode_palette: Optional[List[str]] = None
        self.episode_config: Optional[EpisodeConfig] = None
        self.beat_results: List[BeatResult] = []
    
    def _create_react_agent(self):
        """Create the structured chat agent with system prompt."""
        # Create prompt template for structured chat agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{SYSTEM_PROMPT}

Use the following format for your responses:

{{{{tools}}}}

Tool names: {{{{tool_names}}}}

Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

Valid "action" values: "Final Answer" or one of the tool names listed above.

Provide only ONE action per response, like this:

```
{{{{
  "action": "tool_name",
  "action_input": {{"param1": "value1", "param2": "value2"}}
}}}}
```

or for the final answer:

```
{{{{
  "action": "Final Answer",
  "action_input": "your summary of what was accomplished"
}}}}
```

IMPORTANT: Tool action_input must be valid JSON matching the tool's parameter schema. For example:
- list_tags: {{"page": 1, "limit": 1000}}
- search_images_by_tags: {{"tags": ["portrait", "outdoor"], "page": 1, "limit": 20}}
- extract_color_palette: {{"image_url": "https://example.com/image.jpg"}}
- midjourney_imagine: {{"prompt": "cinematic portrait --ar 16:9 --v 6"}}
- remember: {{"note": "episode_palette: #FF5733, #3498DB"}}
- recall: {{}}  (no parameters)

Follow the workflow steps carefully and process each beat systematically."""),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        return create_structured_chat_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )
    
    def process_episode(self, episode_config: EpisodeConfig) -> EpisodeResult:
        """
        Process an entire episode (all beats).
        
        Args:
            episode_config: Episode configuration with beats and product info
            
        Returns:
            EpisodeResult with all beat results
        """
        # Initialize episode
        self.episode_id = str(uuid.uuid4())
        self.episode_config = episode_config
        self.episode_palette = None
        self.beat_results = []
        
        logger.info(f"🎬 Starting episode: {episode_config.title}")
        logger.info(f"   Episode ID: {self.episode_id}")
        logger.info(f"   Total beats: {len(episode_config.beats)}")
        
        # Process each beat
        for idx, beat in enumerate(episode_config.beats):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing Beat {beat.beat} ({idx + 1}/{len(episode_config.beats)})")
            logger.info(f"{'='*60}")
            
            try:
                beat_result = self.process_beat(
                    beat=beat,
                    product_config=episode_config.product_config,
                    is_first_beat=(idx == 0),
                    total_beats=len(episode_config.beats),
                )
                self.beat_results.append(beat_result)
                
                logger.info(f"✓ Beat {beat.beat} completed")
                
            except Exception as e:
                logger.error(f"❌ Failed to process beat {beat.beat}: {e}")
                # Create a failed beat result
                beat_result = BeatResult(
                    beat_number=beat.beat,
                    shot_text=normalize_beat(beat),
                    total_attempts=0,
                    storyboard_image_url="",
                    storyboard_task_id="",
                    quality_check_passed=False,
                    flagged_for_review=True,
                    review_reason=f"Processing error: {str(e)}",
                )
                self.beat_results.append(beat_result)
        
        # Create episode result
        episode_result = EpisodeResult(
            episode_id=self.episode_id,
            title=episode_config.title,
            episode_palette=self.episode_palette,
            beats=self.beat_results,
            total_beats=len(episode_config.beats),
            successful_beats=sum(1 for b in self.beat_results if b.product_replacement_success),
            flagged_beats=sum(1 for b in self.beat_results if b.flagged_for_review),
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 Episode Complete!")
        logger.info(f"   Total beats: {episode_result.total_beats}")
        logger.info(f"   Successful: {episode_result.successful_beats}")
        logger.info(f"   Flagged: {episode_result.flagged_beats}")
        logger.info(f"{'='*60}\n")
        
        return episode_result
    
    def process_beat(
        self,
        beat: Beat,
        product_config: ProductConfig,
        is_first_beat: bool = False,
        total_beats: int = 1,
    ) -> BeatResult:
        """
        Process a single beat using the ReAct agent.
        
        Args:
            beat: Beat to process
            product_config: Product configuration
            is_first_beat: Whether this is the first beat
            total_beats: Total number of beats in episode
            
        Returns:
            BeatResult with all generation details
        """
        # Build input prompt for agent
        input_prompt = BEAT_PROCESSING_PROMPT.format(
            beat_number=beat.beat,
            heading=beat.heading,
            shot_description=beat.shot_description,
            action=beat.action,
            target_object=product_config.target_object,
            product_image_url=product_config.product_image_url,
            total_beats=total_beats,
            is_first_beat=is_first_beat,
        )
        
        logger.debug(f"Agent input prompt: {input_prompt}")
        
        # Execute agent
        try:
            result = self.executor.invoke({"input": input_prompt})
            
            logger.info(f"Agent execution completed for beat {beat.beat}")
            logger.debug(f"Agent output: {result.get('output', '')[:200]}...")
            
            # Parse the result from agent memory
            # TODO: Implement proper result parsing from agent's memory/recall
            # For now, we'll return a placeholder result structure
            
            beat_result = self._extract_beat_result_from_agent_output(
                beat=beat,
                agent_output=result,
            )
            
            return beat_result
            
        except Exception as e:
            logger.error(f"Agent execution failed for beat {beat.beat}: {e}")
            raise
    
    def _extract_beat_result_from_agent_output(
        self,
        beat: Beat,
        agent_output: dict,
    ) -> BeatResult:
        """
        Extract BeatResult from agent's execution output.
        
        This method parses the agent's final answer and intermediate steps
        to reconstruct the complete beat result.
        
        Args:
            beat: Original beat
            agent_output: Agent execution output
            
        Returns:
            Populated BeatResult
        """
        # This is a simplified implementation
        # In a full implementation, we would parse the agent's memory recalls
        # to extract all the stored information about attempts, URLs, etc.
        
        shot_text = normalize_beat(beat)
        
        # Placeholder result - in real implementation, extract from memory
        beat_result = BeatResult(
            beat_number=beat.beat,
            shot_text=shot_text,
            total_attempts=1,  # Would be extracted from memory
            storyboard_image_url="",  # Would be extracted from memory
            storyboard_task_id="",  # Would be extracted from memory
            quality_check_passed=False,  # Would be extracted from memory
            flagged_for_review=False,
        )
        
        logger.warning(
            f"Using placeholder beat result extraction. "
            f"Full implementation should parse agent's memory."
        )
        
        return beat_result
    
    def reset(self):
        """Reset the agent state for a new episode."""
        self.episode_id = None
        self.episode_palette = None
        self.episode_config = None
        self.beat_results = []
        
        # Clear memory
        from tools.memory import MEM
        MEM.clear()
        
        logger.info("🔄 Agent state reset")

