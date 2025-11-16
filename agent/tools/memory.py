# tools/memory.py
import logging
from langchain.tools import tool

logger = logging.getLogger(__name__)

# In-memory storage for the session
MEM = []

@tool("remember")
def remember(note: str) -> str:
    """
    Store a note in memory for the current session.
    
    Args:
        note: The information to remember (e.g., "episode_palette: #FF5733, #33FF57, #3357FF, #F333FF")
    
    Returns:
        Confirmation message with total count of stored notes.
    """
    logger.info(f"💾 [remember] Storing note: '{note[:50]}...'")
    MEM.append(note)
    result = f"stored ({len(MEM)} total)"
    logger.info(f"✓ [remember] Note stored, total count: {len(MEM)}")
    return result

@tool("recall")
def recall(query: str = "") -> str:
    """
    Return all stored notes from memory.
    
    Args:
        query: Optional search query (currently unused, leave empty)
    
    Returns:
        All stored notes separated by newlines, or "(empty)" if no notes exist.
    """
    logger.info(f"🔖 [recall] Retrieving notes - Current count: {len(MEM)}")
    result = "\n".join(MEM) or "(empty)"
    logger.info(f"✓ [recall] Returned {len(MEM)} notes")
    return result

