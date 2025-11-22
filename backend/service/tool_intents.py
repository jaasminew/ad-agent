"""User-facing intent labels for tool activity."""

import logging
from typing import Any, Dict, Optional

from .models import WorkflowStage

logger = logging.getLogger(__name__)

_TOOL_INTENT_LABELS: Dict[str, str] = {
    "list_tags": "Surveying available reference tags",
    "search_images_by_tags": "Searching for reference imagery",
    "extract_color_palette": "Extracting color inspiration",
    "midjourney_imagine": "Drafting a new concept frame",
    "midjourney_upscale": "Enhancing the selected concept frame",
    "check_image_distortion": "Running a visual quality check",
    "nanobanana_generate": "Compositing the product into the scene",
    "remember": "Saving a working note",
    "recall": "Reviewing saved notes",
    "web_search": "Researching background context",
}

_DEFAULT_INTENT_LABEL = "Running helper task"


def get_tool_intent_label(tool_name: str) -> str:
    """
    Return the friendly label for a tool.

    Unknown tools fall back to a generic description.
    """
    if not tool_name:
        return _DEFAULT_INTENT_LABEL
    return _TOOL_INTENT_LABELS.get(tool_name, _DEFAULT_INTENT_LABEL)


def emit_tool_intent_message(
    task_manager,
    task_id: Optional[str],
    stage: WorkflowStage,
    tool_name: str,
    *,
    extra_output: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit a user-facing tool intent message while logging the raw tool usage.

    Args:
        task_manager: Task manager instance used for streaming output.
        task_id: Current task id.
        stage: Workflow stage enumeration value.
        tool_name: Raw tool name from the agent action.
        extra_output: Optional extra payload to merge into the output dict.
    """
    if task_manager is None or task_id is None:
        return

    intent_label = get_tool_intent_label(tool_name)
    stage_name = getattr(stage, "value", str(stage))

    output_payload: Dict[str, Any] = {
        "type": "tool_call",
        "tool": tool_name,
        "intent_label": intent_label,
    }
    if extra_output:
        output_payload.update(extra_output)

    task_manager.add_llm_output(
        task_id=task_id,
        stage=stage,
        message=f"🔧 {intent_label}",
        output=output_payload,
    )

    logger.info(
        "[ToolIntent] stage=%s tool=%s intent='%s'",
        stage_name,
        tool_name,
        intent_label,
    )

