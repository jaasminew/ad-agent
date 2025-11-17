"""Tools configuration for the Script Generation Agent."""

import logging
from typing import List
try:
    from langchain_classic.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


def get_script_gen_tools() -> List[BaseTool]:
    """
    Get all tools needed for the script generation agent.
    
    Returns:
        List of LangChain tools
    """
    tools = []
    
    # Import Memory tools
    try:
        from tools.memory import remember, recall
        tools.extend([remember, recall])
        logger.info("✓ Loaded Memory tools")
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
    tools = get_script_gen_tools()
    return [tool.name for tool in tools]

