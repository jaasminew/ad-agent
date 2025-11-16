"""Main Storyboard Generation Agent implementation."""

import logging
import uuid
from typing import Dict, List, Optional
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
from .utils import normalize_beat
from .checklist import (
    ChecklistItem,
    build_checklist,
    format_checklist_markdown,
    extract_checklist_statuses,
    find_checklist_gaps,
)
from tools.memory import MEM

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
        self.global_product_urls: Dict[int, str] = {}
        self.beat_summaries: List[str] = []
    
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

IMPORTANT FORMATTING RULES:
- "Action:" and "Action Input:" MUST be on separate lines
- Do NOT write "Action: tool_name(parameters)" - this is WRONG
- Do NOT write "Action: tool_name(parameters)" - this is WRONG
- CORRECT format examples:

Example 1 - Tool with no parameters:
Thought: I need to check what's in memory
Action: recall
Action Input: ""

Observation: (empty)

Example 2 - Tool with JSON parameters:
Thought: Memory is empty, I should search for reference images
Action: list_tags
Action Input: {{{{"page": 1, "limit": 1000}}}}

Observation: {{{{"total": 150, "tags": ["sunset", "beach", "ocean"]}}}}

Begin!

Question: {{input}}
Thought: {{agent_scratchpad}}
"""
        
        tool_descriptions = "\n".join(
            f"{tool.name}: {getattr(tool, 'description', 'No description provided.')}"
            for tool in self.tools
        ) or "No tools available."
        tool_names = ", ".join(tool.name for tool in self.tools) or "None"

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "tools": tool_descriptions,
                "tool_names": tool_names,
            },
        )
        
        return create_react_agent(
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
        self.global_product_urls = {}
        self.beat_summaries = []
        self._clear_agent_memory()
        
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
                    progress_summary=self._format_progress_summary(),
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
            finally:
                self._post_process_beat(beat_result)
        
        # Create episode result
        episode_result = EpisodeResult(
            episode_id=self.episode_id,
            title=episode_config.title,
            episode_palette=self.episode_palette,
            beats=self.beat_results,
            total_beats=len(episode_config.beats),
            successful_beats=sum(1 for b in self.beat_results if b.product_replacement_success),
            flagged_beats=sum(1 for b in self.beat_results if b.flagged_for_review),
            product_url_memory=self.global_product_urls.copy(),
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 Episode Complete!")
        logger.info(f"   Total beats: {episode_result.total_beats}")
        logger.info(f"   Successful: {episode_result.successful_beats}")
        logger.info(f"   Flagged: {episode_result.flagged_beats}")
        logger.info(f"{'='*60}\n")

        self._emit_final_product_urls(episode_result.product_url_memory)
        
        return episode_result
    
    def process_beat(
        self,
        beat: Beat,
        product_config: ProductConfig,
        is_first_beat: bool = False,
        total_beats: int = 1,
        progress_summary: Optional[str] = None,
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
        checklist_items = build_checklist(is_first_beat=is_first_beat)
        checklist_markdown = format_checklist_markdown(checklist_items)

        input_prompt = BEAT_PROCESSING_PROMPT.format(
            beat_number=beat.beat,
            heading=beat.heading,
            shot_description=beat.shot_description,
            action=beat.action,
            target_object=product_config.target_object,
            product_image_url=product_config.product_image_url,
            total_beats=total_beats,
            is_first_beat=is_first_beat,
            progress_summary=progress_summary or "No beats completed yet.",
            checklist_markdown=checklist_markdown,
        )
        
        logger.debug(f"Agent input prompt: {input_prompt}")
        
        # Execute agent
        try:
            result = self.executor.invoke({"input": input_prompt})
            
            logger.info(f"Agent execution completed for beat {beat.beat}")
            logger.debug(f"Agent output: {result.get('output', '')[:200]}...")

            self._validate_checklist_progress(
                beat_number=beat.beat,
                checklist_items=checklist_items,
                agent_output=result,
            )
            
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
        self.global_product_urls = {}
        self.beat_summaries = []
        
        self._clear_agent_memory()
        
        logger.info("🔄 Agent state reset")

    # ------------------------------------------------------------------ #
    # Internal helpers for memory + progress management
    # ------------------------------------------------------------------ #

    ESSENTIAL_MEMORY_PREFIXES = ("episode_palette:", "global_product_url:")

    def _clear_agent_memory(self):
        """Completely clear shared tool memory."""
        MEM.clear()
        logger.debug("🧹 Cleared shared agent memory")

    def _refresh_episode_palette_from_memory(self):
        """Update cached episode palette from memory notes."""
        for note in reversed(MEM):
            if note.startswith("episode_palette:"):
                palette_text = note.split(":", 1)[1].strip()
                if not palette_text:
                    return
                palette = [color.strip() for color in palette_text.split(",") if color.strip()]
                if palette:
                    self.episode_palette = palette
                return

    def _record_product_url_memory(self, beat_result: BeatResult):
        """Persist final product URL to global state and memory."""
        final_url = beat_result.final_image_url
        if not final_url:
            return
        self.global_product_urls[beat_result.beat_number] = final_url
        prefix = f"global_product_url: beat={beat_result.beat_number}"
        note = f"{prefix}, url={final_url}"
        self._upsert_memory_note(prefix, note)

    def _capture_beat_summary(self, beat_result: BeatResult) -> str:
        """Create a concise summary for internal context passing."""
        summary = (
            f"Beat {beat_result.beat_number}: "
            f"storyboard={beat_result.storyboard_image_url or 'N/A'}, "
            f"final={beat_result.final_image_url or 'N/A'}, "
            f"quality={'PASS' if beat_result.quality_check_passed else 'FAIL'}, "
            f"product={'YES' if beat_result.product_replacement_success else 'NO'}"
        )
        self.beat_summaries.append(summary)
        return summary

    def _format_progress_summary(self) -> str:
        """Return a short textual recap for prompt context."""
        if not self.beat_summaries:
            return "No beats completed yet."
        recent = self.beat_summaries[-2:]
        return "\n".join(recent)

    def _trim_memory_for_next_beat(self):
        """Reduce tool memory to essential elements only."""
        if not MEM:
            return
        essential_notes = [
            note for note in MEM if self._is_essential_memory(note)
        ]
        MEM.clear()
        MEM.extend(essential_notes)

    def _is_essential_memory(self, note: str) -> bool:
        """Check whether a memory note should persist across beats."""
        return any(note.startswith(prefix) for prefix in self.ESSENTIAL_MEMORY_PREFIXES)

    def _upsert_memory_note(self, prefix: str, note: str):
        """Insert or replace a memory note with the same prefix."""
        for idx, existing in enumerate(MEM):
            if existing.startswith(prefix):
                MEM[idx] = note
                return
        MEM.append(note)

    def _post_process_beat(self, beat_result: BeatResult):
        """Handle memory + summary updates after each beat."""
        self._refresh_episode_palette_from_memory()
        self._record_product_url_memory(beat_result)
        summary = self._capture_beat_summary(beat_result)
        logger.debug(f"Stored beat summary: {summary}")
        self._trim_memory_for_next_beat()

    def _emit_final_product_urls(self, product_url_memory: Dict[int, str]) -> None:
        """
        Print the final product-integrated URL list as the episode's closing summary.
        Outputs URLs only, one per line, sorted by beat number. If none exist, prints nothing.
        """

        if not product_url_memory:
            return

        ordered_urls = [
            url for _, url in sorted(product_url_memory.items(), key=lambda item: item[0])
            if url
        ]

        if not ordered_urls:
            return

        summary = "\n".join(ordered_urls)
        print(summary)

    # ------------------------------------------------------------------ #
    # Checklist enforcement helpers
    # ------------------------------------------------------------------ #

    def _validate_checklist_progress(
        self,
        beat_number: int,
        checklist_items: List[ChecklistItem],
        agent_output: dict,
    ) -> None:
        """Confirm the agent honored the checklist contract."""

        self._ensure_checklist_rendered(agent_output)

        statuses = extract_checklist_statuses(list(MEM), beat_number)
        missing, unresolved_optional = find_checklist_gaps(statuses, checklist_items)

        errors = []
        if missing:
            errors.append(
                f"missing DONE status for mandatory items: {', '.join(missing)}"
            )
        if unresolved_optional:
            errors.append(
                "optional items must be DONE or SKIPPED: "
                + ", ".join(unresolved_optional)
            )

        if errors:
            raise RuntimeError(
                f"Checklist incomplete for beat {beat_number}: " + "; ".join(errors)
            )

    def _ensure_checklist_rendered(self, agent_output: dict) -> None:
        """Ensure the first thought included the checklist before any action."""

        steps = agent_output.get("intermediate_steps") or []
        if not steps:
            raise RuntimeError("Agent produced no intermediate steps; checklist missing.")

        first = steps[0]
        if isinstance(first, tuple):
            first_log = getattr(first[0], "log", "")
        else:
            first_log = getattr(first, "log", "")

        if "Checklist" not in (first_log or ""):
            raise RuntimeError(
                "Agent must print the checklist before its first tool call."
            )

