"""Storyboard Agent Worker - 集成 Storyboard Agent 到 Workflow"""

import logging
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add agent directory to Python path
agent_dir = Path(__file__).resolve().parent.parent.parent / "agent"
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

# Add backend directory to Python path (for service modules)
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from storyboard_gen_agent import (
    StoryboardAgent,
    EpisodeConfig,
    Beat,
    ProductConfig,
    EpisodeResult,
)
from service.tool_intents import emit_tool_intent_message, get_tool_intent_label

logger = logging.getLogger(__name__)


def create_storyboard_agent(llm=None) -> StoryboardAgent:
    """
    Create and configure a Storyboard Agent instance.
    
    Args:
        llm: Optional pre-configured LLM. If not provided, will create GPT-4o-mini.
    
    Returns:
        StoryboardAgent instance
    """
    if llm is None:
        try:
            from workflow.utils.llm_factory import get_chat_model
            llm = get_chat_model(
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=4096,
            )
            logger.info("✓ Using LLM (OpenAI/DeepSeek) for Storyboard Agent")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM: {e}")
            raise
    
    agent = StoryboardAgent(
        llm=llm,
        verbose=True,
        max_iterations=50,
        max_execution_time=3600,  # 1 hour max
    )
    
    logger.info(f"✓ Storyboard Agent initialized with {len(agent.tools)} tools")
    return agent


def parse_shot_to_beat(shot: str, index: int) -> Beat:
    """
    Parse a shot description into a Beat object.
    
    Expected shot format examples:
    - "Scene: Morning coffee shop. Action: Opens laptop and smiles"
    - "A person running on the beach at sunset"
    
    Args:
        shot: Shot description string
        index: Beat number (1-based)
    
    Returns:
        Beat object
    """
    # Simple parsing: split by common patterns
    parts = shot.split(".", 1)
    
    if len(parts) >= 2:
        # Has structure like "Scene description. Action description"
        heading = f"Shot {index}"
        shot_description = parts[0].strip()
        action = parts[1].strip() if len(parts) > 1 else "Camera follows the scene"
    else:
        # Single description
        heading = f"Shot {index}"
        shot_description = shot.strip()
        action = "Camera follows the scene"
    
    return Beat(
        beat=index,
        heading=heading,
        shot_description=shot_description,
        action=action,
    )


def extract_uploaded_final_urls(episode_result: EpisodeResult) -> List[str]:
    """
    Extract uploaded_final_urls from episode_result.global_memory.
    
    Args:
        episode_result: EpisodeResult from Storyboard Agent
    
    Returns:
        List of final image URLs
    """
    # Method 1: From global_memory (recommended)
    for idx, item in enumerate(episode_result.global_memory):
        if idx == 0 and isinstance(item, list):
            return item
        if isinstance(item, str) and item.startswith("uploaded_final_urls:"):
            try:
                urls_json = item.split(":", 1)[1].strip()
                return json.loads(urls_json)
            except Exception as e:
                logger.warning(f"Failed to parse uploaded_final_urls from global_memory: {e}")
                break
    
    # Method 2: Fallback to collecting final_image_url from beats
    logger.info("Falling back to collecting final_image_url from beats")
    final_urls = [
        beat.final_image_url
        for beat in episode_result.beats
        if beat.final_image_url and beat.product_replacement_success
    ]
    
    return final_urls


def run_storyboard_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run Storyboard Agent to generate composed images for all shots.
    
    This replaces the original steps 2-6:
    - search_style_image
    - extract_palette
    - generate_midjourney_image
    - check_distortion
    - compose_with_product
    
    Input from state:
    - product_name: Product name
    - brand_identity: Brand identity (used for title)
    - product_images: Product image URL
    - shots: List of shot descriptions
    
    Output to state:
    - episode_result: Complete EpisodeResult from Storyboard Agent
    - nanobanana_images: List of final composed image URLs (from uploaded_final_urls)
    - messages: Log messages
    """
    # Import from service module for streaming updates
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from service.task_manager import TaskContext, get_task_manager
    from service.models import WorkflowStage
    from service.tool_intents import emit_tool_intent_message, get_tool_intent_label
    
    logger.info("\n" + "=" * 80)
    logger.info("Running Storyboard Agent (Black Box)")
    logger.info("=" * 80)
    
    product_name = state["product_name"]
    brand_identity = state["brand_identity"]
    product_images = state["product_images"]
    shots = state["shots"]
    video_format = state.get("video_format", "16:9")  # Get video format from state, default to 16:9
    
    logger.info(f"Product: {product_name}")
    logger.info(f"Brand Identity: {brand_identity}")
    logger.info(f"Product Image: {product_images}")
    logger.info(f"Video Format: {video_format}")
    logger.info(f"Total shots: {len(shots)}")
    
    # Get task manager for real-time updates
    task_id = TaskContext.get_task_id()
    task_manager = get_task_manager() if task_id else None
    
    # Parse shots into beats
    logger.info("\nParsing shots into beats...")
    beats = [parse_shot_to_beat(shot, i + 1) for i, shot in enumerate(shots)]
    
    for beat in beats:
        logger.info(f"  Beat {beat.beat}: {beat.heading}")
        logger.info(f"    Scene: {beat.shot_description}")
        logger.info(f"    Action: {beat.action}")
    
    # Create episode config
    episode_config = EpisodeConfig(
        title=f"{product_name} - {brand_identity[:50]}",
        product_config=ProductConfig(
            product_image_url=product_images,
            target_object=product_name.lower().replace(" ", "_"),
        ),
        beats=beats,
        video_format=video_format,  # Pass video format to episode config
    )
    
    logger.info(f"\nEpisode Config:")
    logger.info(f"  Title: {episode_config.title}")
    logger.info(f"  Target Object: {episode_config.product_config.target_object}")
    logger.info(f"  Total Beats: {len(episode_config.beats)}")
    
    # Create and run agent with streaming
    logger.info("\nInitializing Storyboard Agent...")
    agent = create_storyboard_agent()
    
    logger.info("\nProcessing episode with Storyboard Agent...")
    logger.info("(This will take several minutes depending on the number of beats)")
    
    try:
        # Use streaming version if task_manager is available
        if task_manager and task_id:
            episode_result = _process_episode_with_streaming(
                agent, episode_config, task_manager, task_id
            )
        else:
                episode_result = agent.process_episode(episode_config)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Storyboard Agent Completed")
        logger.info("=" * 80)
        logger.info(f"Episode ID: {episode_result.episode_id}")
        logger.info(f"Total Beats: {episode_result.total_beats}")
        logger.info(f"Successful: {episode_result.successful_beats}")
        logger.info(f"Flagged: {episode_result.flagged_beats}")
        
        # Extract uploaded_final_urls
        nanobanana_images = extract_uploaded_final_urls(episode_result)
        
        logger.info(f"\n📸 Generated Images:")
        logger.info(f"  Total: {len(nanobanana_images)}")
        for i, url in enumerate(nanobanana_images, 1):
            logger.info(f"  {i}. {url}")
        
        # Log any flagged beats
        flagged_beats = [beat for beat in episode_result.beats if beat.flagged_for_review]
        if flagged_beats:
            logger.warning(f"\n⚠️  {len(flagged_beats)} beat(s) flagged for review:")
            for beat in flagged_beats:
                logger.warning(f"  Beat {beat.beat_number}: {beat.review_reason}")
        
        return {
            "episode_result": episode_result,
            "nanobanana_images": nanobanana_images,
            "messages": [
                f"✓ Storyboard Agent processed {episode_result.total_beats} beats",
                f"✓ Successfully generated {len(nanobanana_images)} composed images",
            ],
        }
        
    except Exception as e:
        logger.error(f"\n❌ Storyboard Agent failed: {e}", exc_info=True)
        raise


def _process_episode_with_streaming(
    agent: StoryboardAgent,
    episode_config: EpisodeConfig,
    task_manager,
    task_id: str,
) -> EpisodeResult:
    """
    Process episode with streaming callback to capture agent thoughts and tool calls.
    
    This creates a custom beat processing loop with callbacks.
    """
    from langchain_core.callbacks.base import BaseCallbackHandler
    from service.models import WorkflowStage
    from .checklist_parser import parse_thought_into_blocks, has_checklist, get_checklist_summary
    import uuid
    
    class StoryboardStreamingCallback(BaseCallbackHandler):
        """Callback to stream storyboard agent thoughts and actions."""
        
        def __init__(self, task_manager, task_id: str):
            self.task_manager = task_manager
            self.task_id = task_id
        
        def _check_cancellation(self):
            """Check if task is cancelled"""
            if self.task_manager and self.task_id and self.task_manager.is_cancelled(self.task_id):
                logger.info(f"[Task {self.task_id}] Task cancelled by user during agent execution")
                from service.workflow_executor import TaskCancelledException
                raise TaskCancelledException(f"Task {self.task_id} cancelled")
        
        def on_agent_action(self, action, **kwargs):
            """Called when agent takes an action."""
            # Check for cancellation before action
            self._check_cancellation()
            
            tool_name = action.tool
            
            # Extract and display Thought from action log
            if hasattr(action, 'log') and action.log:
                # Parse thought from the action log
                # The log typically contains: "Thought: ... \nAction: ... \nAction Input: ..."
                thought_text = ""
                if 'Thought:' in action.log:
                    parts = action.log.split('Action:', 1)
                    if parts and parts[0]:
                        thought_part = parts[0].replace('Thought:', '').strip()
                        if thought_part:
                            thought_text = thought_part
                
                if thought_text:
                    # Parse thought into structured content blocks
                    content_blocks = parse_thought_into_blocks(thought_text)
                    has_checklist_flag = has_checklist(content_blocks)
                    
                    # Build output data
                    output_data = {
                        "type": "thought",
                        "content_blocks": [block.to_dict() for block in content_blocks],
                    }
                    
                    # Add checklist summary if present
                    if has_checklist_flag:
                        summary = get_checklist_summary(content_blocks)
                        if summary:
                            output_data["checklist_summary"] = summary
                    
                    # Send structured thought
                    self.task_manager.add_llm_output(
                        task_id=self.task_id,
                        stage=WorkflowStage.STORYBOARD_GEN_AGENT,
                        message=f"💭 {thought_text}",
                        output=output_data,
                    )
                    
                    if has_checklist_flag:
                        logger.info(f"[Storyboard Agent] Thought with checklist: {summary}")
                    else:
                        logger.info(f"[Storyboard Agent] Thought: {thought_text[:100]}...")
            
            # Send abstracted tool intent message
            emit_tool_intent_message(
                task_manager=self.task_manager,
                task_id=self.task_id,
                stage=WorkflowStage.STORYBOARD_GEN_AGENT,
                tool_name=tool_name,
            )
            intent_label = get_tool_intent_label(tool_name)
            logger.info(f"[Storyboard Agent] 🔧 {intent_label} ({tool_name})")
        
        def on_tool_end(self, output, **kwargs):
            """Called when a tool finishes running."""
            # 工具执行完成,不输出任何内容到前端
            # 只记录到日志用于调试
            output_str = str(output)
            if len(output_str) > 200:
                output_str = output_str[:200] + "... (truncated)"
            logger.debug(f"[Storyboard Agent] Tool output (internal): {output_str}")
        
        def on_agent_finish(self, finish, **kwargs):
            """Called when agent finishes."""
            # Beat 完成,不需要输出任何信息
            # 最终结果会在 beat 处理完成后统一输出
            logger.info(f"[Storyboard Agent] Beat completed")
    
    # Initialize episode
    agent.episode_id = str(uuid.uuid4())
    agent.episode_config = episode_config
    agent.episode_palette = None
    agent.beat_results = []
    agent.global_product_urls = {}
    agent.beat_summaries = []
    agent.global_memory = []
    agent._clear_agent_memory()
    agent._reset_uploaded_url_memory()
    
    logger.info(f"🎬 Starting episode: {episode_config.title}")
    logger.info(f"   Episode ID: {agent.episode_id}")
    logger.info(f"   Total beats: {len(episode_config.beats)}")
    
    # Create callback
    callback = StoryboardStreamingCallback(task_manager, task_id)
    
    # Process each beat with callback
    for idx, beat in enumerate(episode_config.beats):
        # Check for cancellation before processing each beat
        if task_manager and task_id and task_manager.is_cancelled(task_id):
            logger.info(f"[Task {task_id}] Task cancelled by user during beat {idx + 1}")
            from service.workflow_executor import TaskCancelledException
            raise TaskCancelledException(f"Task {task_id} cancelled")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing Beat {beat.beat} ({idx + 1}/{len(episode_config.beats)})")
        logger.info(f"{'='*60}")
        
        # Send progress update
        task_manager.add_llm_output(
            task_id=task_id,
            stage=WorkflowStage.STORYBOARD_GEN_AGENT,
            message=f"🎬 Processing Beat {beat.beat}/{len(episode_config.beats)}: {beat.heading}",
            output={"type": "progress", "beat_number": beat.beat, "total": len(episode_config.beats)},
        )
        
        try:
            # Process beat with custom callback injection
            beat_result = _process_beat_with_callback(
                agent=agent,
                beat=beat,
                product_config=episode_config.product_config,
                is_first_beat=(idx == 0),
                total_beats=len(episode_config.beats),
                callback=callback,
                video_format=episode_config.video_format,
            )
            
            agent.beat_results.append(beat_result)
            logger.info(f"✓ Beat {beat.beat} completed")
            
            # 输出 Beat 的结果 (传递给下一个节点的数据)
            result_message = f"✅ Beat {beat.beat} completed"
            result_data = {
                "beat_number": beat.beat,
                "quality_passed": beat_result.quality_check_passed,
                "product_replaced": beat_result.product_replacement_success,
            }
            
            # 如果有最终图片 URL,添加到结果中
            if beat_result.final_image_url:
                result_data["image_url"] = beat_result.final_image_url
                result_message += f"\n📸 Generated product image: {beat_result.final_image_url}"
            
            if beat_result.flagged_for_review:
                result_message += f"\n⚠️ Flagged for review: {beat_result.review_reason}"
                result_data["flagged"] = True
                result_data["reason"] = beat_result.review_reason
            
            task_manager.add_llm_output(
                task_id=task_id,
                stage=WorkflowStage.STORYBOARD_GEN_AGENT,
                message=result_message,
                output=result_data,
            )
            
        except Exception as e:
            # If it's a cancellation exception, re-raise it
            if e.__class__.__name__ == "TaskCancelledException":
                raise

            logger.error(f"❌ Failed to process beat {beat.beat}: {e}")
            # Create a failed beat result
            from storyboard_gen_agent.models import BeatResult
            from storyboard_gen_agent.utils import normalize_beat
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
            agent.beat_results.append(beat_result)
        finally:
            agent._post_process_beat(beat_result)
    
    # Create episode result
    episode_result = EpisodeResult(
        episode_id=agent.episode_id,
        title=episode_config.title,
        episode_palette=agent.episode_palette,
        beats=agent.beat_results,
        total_beats=len(episode_config.beats),
        successful_beats=sum(1 for b in agent.beat_results if b.product_replacement_success),
        flagged_beats=sum(1 for b in agent.beat_results if b.flagged_for_review),
        product_url_memory=agent.global_product_urls.copy(),
        global_memory=agent._build_global_memory_snapshot(),
    )
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 Episode Complete!")
    logger.info(f"   Total beats: {episode_result.total_beats}")
    logger.info(f"   Successful: {episode_result.successful_beats}")
    logger.info(f"   Flagged: {episode_result.flagged_beats}")
    logger.info(f"{'='*60}\n")
    
    final_memory_snapshot = agent._build_global_memory_snapshot()
    if final_memory_snapshot:
        logger.info("🧠 Final global memory (%d items):", len(final_memory_snapshot))
        for item in final_memory_snapshot:
            logger.info("   - %s", item)
    else:
        logger.info("🧠 Final global memory is empty")
    
    agent._emit_final_product_urls(episode_result.product_url_memory)
    
    return episode_result


def _process_beat_with_callback(
    agent: StoryboardAgent,
    beat: Beat,
    product_config: ProductConfig,
    is_first_beat: bool,
    total_beats: int,
    callback,
    video_format: str = "16:9",
) -> "BeatResult":
    """
    Process a single beat with callback injected.
    
    This reimplements the core logic of agent.process_beat but with callback support.
    """
    from storyboard_gen_agent.prompt_templates import BEAT_PROCESSING_PROMPT
    
    # Build input prompt (same as agent.process_beat)
    agent._start_shot_episode()
    global_memory_notes = agent._format_global_memory_for_prompt()
    progress_summary = agent._format_progress_summary()
    
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
        video_format=video_format,
    )
    
    logger.debug(f"Agent input prompt: {input_prompt}")
    
    # Execute agent with callback
    memory_snapshot = []
    try:
        result = agent.executor.invoke(
            {"input": input_prompt},
            config={"callbacks": [callback]}
        )
        
        logger.info(f"Agent execution completed for beat {beat.beat}")
        logger.debug(f"Agent output: {result.get('output', '')[:200]}...")
        memory_snapshot = list(agent.memory)
        checklist_confirmed, checklist_gap_reason = agent._evaluate_dynamic_checklist(
            beat.beat, memory_snapshot
        )
        new_notes = agent._filter_new_shot_notes(memory_snapshot)
        agent._persist_episode_state_from_notes(new_notes)
        summary_items = agent._summarize_shot_memory(
            beat=beat,
            agent_output=result,
            new_notes=new_notes,
        )
        if summary_items:
            logger.info(
                "🧠 Beat %s summary items:\n%s",
                beat.beat,
                "\n".join(f"   - {item}" for item in summary_items),
            )
            # FIX: Use _append_shot_memory_entry instead of _append_global_memory_items
            # which seems to be the correct method name in StoryboardAgent
            agent._append_shot_memory_entry(summary_items)
        
        # Extract beat result
        beat_result = agent._extract_beat_result_from_agent_output(
            beat=beat,
            agent_output=result,
            checklist_confirmed=checklist_confirmed,
            checklist_gap_reason=checklist_gap_reason,
        )
        
        return beat_result
        
    except Exception as e:
        logger.error(f"Agent execution failed for beat {beat.beat}: {e}")
        raise
