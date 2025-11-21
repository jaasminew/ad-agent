"""Main Storyboard Generation Agent implementation."""

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
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
from .prompt_templates import (
    SYSTEM_PROMPT,
    BEAT_PROCESSING_PROMPT,
    SHOT_MEMORY_SUMMARY_PROMPT,
)
from .utils import (
    normalize_beat,
    format_global_memory_notes,
    build_global_memory_with_uploaded_urls,
)
from .checklist import (
    ChecklistItem,
    build_checklist,
    format_checklist_markdown,
    extract_checklist_statuses,
    find_checklist_gaps,
    find_optional_incomplete,
)
from tools.memory import MEM, recall as recall_tool
from tools.upload_memory import clear_uploaded_urls, get_uploaded_urls, format_uploaded_urls_note

logger = logging.getLogger(__name__)

UPLOADED_URL_NOTE_PREFIX = "uploaded_final_urls:"
SHOT_MEMORY_NOTE_PREFIX = "shot_memory:"


@dataclass
class ChecklistValidationReport:
    """Structured summary of checklist statuses for a beat."""

    statuses: Dict[str, str]
    missing_mandatory: List[str]
    incomplete_optional: List[str]

    def is_valid(self) -> bool:
        """Return True when all mandatory and optional slugs are resolved."""
        return not self.missing_mandatory and not self.incomplete_optional

    def summary(self) -> str:
        """Human readable summary."""
        parts: List[str] = []
        if self.missing_mandatory:
            parts.append(
                "Missing mandatory slugs: "
                + ", ".join(sorted(self.missing_mandatory))
            )
        if self.incomplete_optional:
            parts.append(
                "Optional slugs unresolved (mark done or skipped): "
                + ", ".join(sorted(self.incomplete_optional))
            )
        return "; ".join(parts) if parts else "Checklist complete"


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
        self.global_memory: List[List[str]] = []
        self._persistent_notes: List[str] = []
        self._uploaded_urls: List[str] = []
        self.memory_summary_prompt = PromptTemplate.from_template(
            SHOT_MEMORY_SUMMARY_PROMPT
        )
        self._shot_seed_memory: List[str] = []
    
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
        self.global_memory = []
        self._persistent_notes = []
        self._clear_agent_memory()
        self._clear_agent_memory()
        self._reset_uploaded_url_memory()
        
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
                    video_format=episode_config.video_format,
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
                # Re-raise the exception to stop processing
                raise
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
            global_memory=self._build_global_memory_snapshot(),
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 Episode Complete!")
        logger.info(f"   Total beats: {episode_result.total_beats}")
        logger.info(f"   Successful: {episode_result.successful_beats}")
        logger.info(f"   Flagged: {episode_result.flagged_beats}")
        logger.info(f"{'='*60}\n")
        final_memory_snapshot = self._build_global_memory_snapshot()
        if final_memory_snapshot:
            logger.info("🧠 Final global memory (%d items):", len(final_memory_snapshot))
            for item in final_memory_snapshot:
                logger.info("   - %s", item)
        else:
            logger.info("🧠 Final global memory is empty")

        self._emit_final_product_urls(episode_result.product_url_memory)
        
        return episode_result
    
    def process_beat(
        self,
        beat: Beat,
        product_config: ProductConfig,
        is_first_beat: bool = False,
        total_beats: int = 1,
        progress_summary: Optional[str] = None,
        video_format: str = "16:9",
    ) -> BeatResult:
        """
        Process a single beat using the ReAct agent.
        
        Args:
            beat: Beat to process
            product_config: Product configuration
            is_first_beat: Whether this is the first beat
            total_beats: Total number of beats in episode
            video_format: Video format aspect ratio (16:9, 9:16, 1:1, etc.)
            
        Returns:
            BeatResult with all generation details
        """
        # Build input prompt for agent
        checklist_items = build_checklist(is_first_beat=is_first_beat)
        checklist_markdown = format_checklist_markdown(checklist_items)
        self._start_shot_episode()
        global_memory_notes = self._format_global_memory_for_prompt()

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
            global_memory_notes=global_memory_notes,
            checklist_markdown=checklist_markdown,
            video_format=video_format,
        )
        
        logger.debug(f"Agent input prompt: {input_prompt}")
        
        # Execute agent
        memory_snapshot: List[str] = []
        validation_report: Optional[ChecklistValidationReport] = None
        checklist_confirmed = False
        try:
            result = self.executor.invoke({"input": input_prompt})
            
            logger.info(f"Agent execution completed for beat {beat.beat}")
            logger.debug(f"Agent output: {result.get('output', '')[:200]}...")
            memory_snapshot = list(MEM)
            validation_report = self._evaluate_checklist_completion(
                beat_number=beat.beat,
                checklist_items=checklist_items,
                notes=memory_snapshot,
            )
            checklist_confirmed = validation_report.is_valid()
            if not checklist_confirmed:
                logger.warning(
                    "Checklist validation failed for beat %s: %s",
                    beat.beat,
                    validation_report.summary(),
                )
            new_notes = self._filter_new_shot_notes(memory_snapshot)
            self._persist_episode_state_from_notes(new_notes)
            shot_memory_entry = self._summarize_shot_memory(
                beat=beat,
                agent_output=result,
                new_notes=new_notes,
            )
            if shot_memory_entry:
                logger.info(
                    "🧠 Beat %s continuity record stored",
                    beat.beat,
                )
                self._append_shot_memory_entry(shot_memory_entry)
            
            # Parse the result from agent memory
            # TODO: Implement proper result parsing from agent's memory/recall
            # For now, we'll return a placeholder result structure
            
            beat_result = self._extract_beat_result_from_agent_output(
                beat=beat,
                agent_output=result,
                checklist_confirmed=checklist_confirmed,
                checklist_report=validation_report,
            )
            
            return beat_result
            
        except Exception as e:
            logger.error(f"Agent execution failed for beat {beat.beat}: {e}")
            raise
        finally:
            self._shot_seed_memory = []
            self._clear_agent_memory()
    
    def _extract_beat_result_from_agent_output(
        self,
        beat: Beat,
        agent_output: dict,
        checklist_confirmed: bool,
        checklist_report: Optional[ChecklistValidationReport],
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
        
        flagged = not checklist_confirmed
        review_reason = None
        if flagged:
            review_reason = (
                self._format_checklist_review_reason(checklist_report)
                or "Checklist QA incomplete or unverified"
            )

        # Placeholder result - in real implementation, extract from memory
        beat_result = BeatResult(
            beat_number=beat.beat,
            shot_text=shot_text,
            total_attempts=1,  # Would be extracted from memory
            storyboard_image_url="",  # Would be extracted from memory
            storyboard_task_id="",  # Would be extracted from memory
            quality_check_passed=checklist_confirmed,
            product_replacement_success=checklist_confirmed,
            flagged_for_review=flagged,
            review_reason=review_reason,
        )
        
        logger.warning(
            f"Using placeholder beat result extraction. "
            f"Full implementation should parse agent's memory."
        )
        
        return beat_result

    def _format_checklist_review_reason(
        self, report: Optional[ChecklistValidationReport]
    ) -> Optional[str]:
        """Convert a validation report into a readable review reason."""
        if not report or report.is_valid():
            return None
        return f"Checklist gaps: {report.summary()}"
    
    def reset(self):
        """Reset the agent state for a new episode."""
        self.episode_id = None
        self.episode_palette = None
        self.episode_config = None
        self.beat_results = []
        self.global_product_urls = {}
        self.beat_summaries = []
        self.global_memory = []
        self._persistent_notes = []
        self._shot_seed_memory = []
        
        self._clear_agent_memory()
        self._reset_uploaded_url_memory()
        
        logger.info("🔄 Agent state reset")

    # ------------------------------------------------------------------ #
    # Internal helpers for memory + progress management
    # ------------------------------------------------------------------ #

    ESSENTIAL_MEMORY_PREFIXES = ("episode_palette:", "global_product_url:")

    def _clear_agent_memory(self):
        """Completely clear shared tool memory."""
        MEM.clear()
        logger.debug("🧹 Cleared shared agent memory")

    def _reset_uploaded_url_memory(self) -> None:
        """Clear shared uploaded URL registry and local cache."""
        clear_uploaded_urls()
        self._uploaded_urls = []

    def _sync_uploaded_url_cache(self) -> None:
        """Refresh cached uploaded URLs from the shared registry."""
        latest = get_uploaded_urls()
        if latest != self._uploaded_urls:
            self._uploaded_urls = latest

    def _build_global_memory_snapshot(self) -> List[List[str]]:
        """Combine uploaded URL list with controller-managed shot entries."""
        self._sync_uploaded_url_cache()
        return build_global_memory_with_uploaded_urls(
            self.global_memory, self._uploaded_urls
        )

    def _serialize_global_memory_snapshot(self, snapshot: List[List[str]]) -> List[str]:
        """Convert structured global memory into serializable notes for the agent."""
        serialized: List[str] = []
        if not snapshot:
            return serialized

        first = snapshot[0]
        if isinstance(first, list):
            serialized.append(format_uploaded_urls_note(first))
        elif isinstance(first, str):
            serialized.append(first)

        for entry in snapshot[1:]:
            if isinstance(entry, list) and len(entry) == 5:
                serialized.append(self._serialize_shot_memory_entry(entry))
            elif isinstance(entry, str):
                serialized.append(entry)

        return serialized

    def _serialize_shot_memory_entry(self, entry: List[str]) -> str:
        """Convert a five-element shot record into a deterministic string."""
        segments = [
            f"title_number={entry[0] if len(entry) > 0 else ''}",
            f"main_character={entry[1] if len(entry) > 1 else ''}",
            f"style={entry[2] if len(entry) > 2 else ''}",
            f"color_palette={entry[3] if len(entry) > 3 else ''}",
            f"shot_description={entry[4] if len(entry) > 4 else ''}",
        ]
        compact = " | ".join(
            f"{segment.split('=', 1)[0]}={segment.split('=', 1)[1].strip()}"
            for segment in segments
        )
        normalized = " ".join(compact.split())
        return f"{SHOT_MEMORY_NOTE_PREFIX} {normalized}"

    def _normalize_shot_memory_entry(self, entry: Any, beat: Beat) -> Optional[List[str]]:
        """Validate and coerce LLM response into a five-element list."""
        if not isinstance(entry, list):
            logger.debug("Shot memory response missing list payload: %s", entry)
            return None

        sanitized: List[str] = []
        for value in entry[:5]:
            if isinstance(value, list):
                value = ", ".join(str(item).strip() for item in value if str(item).strip())
            elif value is None:
                value = ""
            sanitized.append(str(value).strip())

        while len(sanitized) < 5:
            sanitized.append("")

        if not sanitized[0]:
            sanitized[0] = f"Shot {beat.beat}"
        if not sanitized[4]:
            sanitized[4] = normalize_beat(beat)

        return sanitized

    def _start_shot_episode(self):
        """Reset scratchpad and seed it with curated global memory."""
        self._clear_agent_memory()
        structured_snapshot = self._build_global_memory_snapshot()
        serialized_snapshot = self._serialize_global_memory_snapshot(structured_snapshot)
        self._shot_seed_memory = serialized_snapshot + list(self._persistent_notes)
        if self._shot_seed_memory:
            MEM.extend(self._shot_seed_memory)
            logger.debug(
                "🧠 Seeded shot memory with %d global items", len(self._shot_seed_memory)
            )
        else:
            logger.debug("🧠 Shot memory seeded with 0 global items")

    def _format_global_memory_for_prompt(self) -> str:
        """Return formatted global memory block for the prompt."""
        snapshot = self._build_global_memory_snapshot()
        return format_global_memory_notes(snapshot)

    def _filter_new_shot_notes(self, snapshot: List[str]) -> List[str]:
        """Return only the notes created during the current shot."""
        if not snapshot:
            return []
        seed_set = set(self._shot_seed_memory)
        filtered: List[str] = []
        for note in snapshot:
            if not note:
                continue
            if note.startswith(UPLOADED_URL_NOTE_PREFIX):
                continue
            if note not in seed_set:
                filtered.append(note)
        return filtered

    def _evaluate_checklist_completion(
        self,
        beat_number: int,
        checklist_items: List[ChecklistItem],
        notes: Optional[List[str]],
    ) -> ChecklistValidationReport:
        """Summarize checklist statuses and detect gaps."""
        note_list = notes or []
        statuses = extract_checklist_statuses(note_list, beat_number)
        missing_mandatory = find_checklist_gaps(statuses, checklist_items)
        incomplete_optional = find_optional_incomplete(statuses, checklist_items)
        report = ChecklistValidationReport(
            statuses=statuses,
            missing_mandatory=missing_mandatory,
            incomplete_optional=incomplete_optional,
        )
        if report.is_valid():
            logger.debug("Checklist validated for beat %s", beat_number)
        return report

    def _persist_episode_state_from_notes(self, notes: List[str]) -> None:
        """Capture essential controller-owned state from shot notes."""
        if not notes:
            return
        essentials = self._extract_essential_memory_items(notes)
        if essentials:
            self._append_persistent_notes(essentials)

    def _summarize_shot_memory(
        self,
        beat: Beat,
        agent_output: dict,
        new_notes: List[str],
    ) -> Optional[List[str]]:
        """Use the controller LLM to produce a structured continuity record."""
        if not new_notes and not agent_output.get("output"):
            return None

        episode_title = self.episode_config.title if self.episode_config else ""
        prompt = self.memory_summary_prompt.format(
            episode_title=episode_title,
            beat_number=beat.beat,
            beat_heading=beat.heading,
            beat_summary=normalize_beat(beat),
            final_answer=agent_output.get("output", ""),
            agent_notes="\n".join(new_notes) or "(empty)",
            existing_memory=format_global_memory_notes(
                self._build_global_memory_snapshot()
            ),
        )

        try:
            response = self.llm.invoke(prompt)
            parsed = json.loads(response.content)
            entry = parsed.get("shot_memory")
        except Exception as exc:
            logger.warning(
                "⚠️  Failed to summarize shot memory for beat %s: %s",
                beat.beat,
                exc,
            )
            return None

        normalized = self._normalize_shot_memory_entry(entry, beat)
        return normalized

    def _append_shot_memory_entry(self, entry: List[str]) -> None:
        """Persist one five-element shot continuity record."""
        if len(entry) != 5:
            logger.debug("Rejected malformed shot memory entry: %s", entry)
            return
        snapshot = [segment.strip() for segment in entry]
        self.global_memory.append(snapshot)
        logger.info("🧠 Stored continuity record for %s", snapshot[0] or f"Shot {len(self.global_memory)}")

    def _append_persistent_notes(self, items: List[str]) -> None:
        """Keep essential controller notes (palette, product URLs) available."""
        added: List[str] = []
        for item in items:
            normalized = item.strip()
            if not normalized:
                continue
            if normalized not in self._persistent_notes:
                self._persistent_notes.append(normalized)
                added.append(normalized)
        if added:
            logger.debug(
                "Stored %d persistent controller note(s).", len(added)
            )

    def _record_product_url_memory(self, beat_result: BeatResult):
        """Persist final product URL to global state and memory."""
        final_url = beat_result.final_image_url
        if not final_url:
            return
        self.global_product_urls[beat_result.beat_number] = final_url
        prefix = f"global_product_url: beat={beat_result.beat_number}"
        note = f"{prefix}, url={final_url}"
        self._append_persistent_notes([note])

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

    def _extract_essential_memory_items(self, notes: List[str]) -> List[str]:
        """Filter shot notes down to controller-defined essential records."""
        essentials: List[str] = []
        for note in notes:
            if not note:
                continue
            if self._is_essential_memory(note):
                stripped = note.strip()
                if stripped:
                    essentials.append(stripped)
                if note.startswith("episode_palette:"):
                    self._update_episode_palette_from_note(note)
        return essentials

    def _update_episode_palette_from_note(self, note: str) -> None:
        """Update cached palette when the agent stores a palette note."""
        try:
            palette_text = note.split(":", 1)[1].strip()
        except IndexError:
            return
        if not palette_text:
            return
        palette = [color.strip() for color in palette_text.split(",") if color.strip()]
        if palette:
            self.episode_palette = palette

    def _is_essential_memory(self, note: str) -> bool:
        """Check whether a memory note should persist across beats."""
        return any(note.startswith(prefix) for prefix in self.ESSENTIAL_MEMORY_PREFIXES)

    def _post_process_beat(self, beat_result: BeatResult):
        """Handle memory + summary updates after each beat."""
        self._record_product_url_memory(beat_result)
        summary = self._capture_beat_summary(beat_result)
        logger.debug(f"Stored beat summary: {summary}")

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


