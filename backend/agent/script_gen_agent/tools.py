"""Tools configuration for the Script Generation Agent."""

import logging
from typing import List, Optional
try:
    from langchain_classic.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from tools.memory import Memory, create_memory_tools

logger = logging.getLogger(__name__)


def get_script_gen_tools(memory_instance: Optional[Memory] = None) -> List[BaseTool]:
    """
    Get all tools needed for the script generation agent.
    
    Args:
        memory_instance: Optional Memory instance. If provided, creates scoped memory tools.
                        If None, no memory tools are loaded (safe default).
    
    Returns:
        List of LangChain tools
    """
    tools = []
    
    # Import Memory tools
    try:
        if memory_instance:
            tools.extend(create_memory_tools(memory_instance))
            logger.info("✓ Loaded Scoped Memory tools")
        else:
            logger.warning("⚠️ No memory instance provided for Script Gen tools. Memory tools skipped.")
    except ImportError as e:
        logger.error(f"Failed to import Memory tools: {e}")
        raise
    
    # Import Web Search tool
    try:
        from tools.web_search import web_search
        tools.append(web_search)
        logger.info("✓ Loaded Web Search tool")
    except ImportError as e:
        logger.error(f"Failed to import Web Search tool: {e}")
        raise
    
    logger.info(f"✓ Total tools loaded: {len(tools)}")
    return tools


def get_tool_names() -> List[str]:
    """
    Get names of all available tools.
    
    Returns:
        List of tool names
    """
    # Note: this creates default global tools if no memory instance is provided
    tools = get_script_gen_tools()
    return [tool.name for tool in tools]
