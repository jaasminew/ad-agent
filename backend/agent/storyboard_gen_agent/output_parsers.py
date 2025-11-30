"""Custom output parsers used by the Storyboard agent."""

import logging
import re
from typing import ClassVar, Optional, Sequence, Union

try:
    from langchain.agents.output_parsers.react_single_input import (
        ReActSingleInputOutputParser,
    )
except ImportError:  # pragma: no cover - compatibility for langchain_classic installs
    from langchain_classic.agents.output_parsers.react_single_input import (
        ReActSingleInputOutputParser,  # type: ignore[assignment]
    )
from langchain_core.agents import AgentAction
from langchain_core.messages import BaseMessage
from langchain_core.pydantic_v1 import PrivateAttr

try:  # pragma: no cover - compatibility shim across LangChain versions
    from langchain_core.outputs import AgentFinish
except ImportError:
    try:
        from langchain_core.agents import AgentFinish  # type: ignore[assignment]
    except ImportError:
        from langchain.schema import AgentFinish  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class SanitizingReActOutputParser(ReActSingleInputOutputParser):
    """
    A drop-in replacement for ReActSingleInputOutputParser that tolerates
    lightweight formatting noise around tool names and inputs.

    The storyboard agent streams its thoughts into a UI that often applies
    Markdown emphasis (e.g. wrapping the action line with `**`), so we
    occasionally receive tool names such as `midjourney_imagine)` or
    `**midjourney_imagine**`. LangChain treats tool names as exact matches,
    which causes avoidable execution failures. This parser aggressively
    normalizes the tool name by stripping surrounding punctuation/markdown
    and then mapping the result back to the known tool list.
    """

    MARKDOWN_SUFFIXES: ClassVar[tuple[str, ...]] = ("**", "__", "~~")

    _allowed_tools: list[str] = PrivateAttr(default_factory=list)
    _normalized_lookup: dict[str, str] = PrivateAttr(default_factory=dict)

    def __init__(self, allowed_tools: Optional[Sequence[str]] = None, **kwargs):
        super().__init__(**kwargs)
        tools = list(allowed_tools or [])
        self._allowed_tools = tools
        self._normalized_lookup = {
            self._normalize_key(name): name for name in tools if name
        }

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        parsed = super().parse(text)

        if isinstance(parsed, AgentAction):
            sanitized_tool = self._sanitize_tool_name(parsed.tool)
            sanitized_input = self._sanitize_tool_input(parsed.tool_input)

            if sanitized_tool != parsed.tool or sanitized_input != parsed.tool_input:
                logger.debug(
                    "Normalized agent action (tool: '%s' -> '%s').",
                    parsed.tool,
                    sanitized_tool,
                )
                return AgentAction(
                    tool=sanitized_tool,
                    tool_input=sanitized_input,
                    log=parsed.log,
                )

        return parsed

    def _sanitize_tool_input(self, tool_input: Union[str, dict, list, BaseMessage]):
        if not isinstance(tool_input, str):
            return tool_input

        cleaned = tool_input.strip()

        for suffix in self.MARKDOWN_SUFFIXES:
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)].rstrip()

        # Remove lone trailing quotes left behind by Markdown emphasis.
        if cleaned.endswith('"') and cleaned.count('"') % 2 == 1:
            cleaned = cleaned[:-1].rstrip()
        if cleaned.endswith("'") and cleaned.count("'") % 2 == 1:
            cleaned = cleaned[:-1].rstrip()

        return cleaned

    def _sanitize_tool_name(self, raw_tool: str) -> str:
        if not raw_tool:
            return raw_tool

        trimmed = raw_tool.strip()
        trimmed = trimmed.strip("*`")
        trimmed = trimmed.strip()
        trimmed = trimmed.rstrip(")）】>]。.,;:!`'\"")
        trimmed = trimmed.lstrip("([<`*")

        resolved = self._match_allowed_tool(trimmed)
        if resolved:
            return resolved

        # As a fallback, split on whitespace/punctuation and attempt to match
        # partial tokens (e.g., "**midjourney_imagine**" or "midjourney_imagine)**").
        for token in re.split(r"[\s/|]+", trimmed):
            resolved = self._match_allowed_tool(token)
            if resolved:
                return resolved

        return trimmed or raw_tool

    def _match_allowed_tool(self, candidate: str) -> Optional[str]:
        normalized = self._normalize_key(candidate)
        if not normalized:
            return None
        return self._normalized_lookup.get(normalized)

    @staticmethod
    def _normalize_key(value: str) -> str:
        return re.sub(r"[^a-z0-9_]+", "", value.lower())

