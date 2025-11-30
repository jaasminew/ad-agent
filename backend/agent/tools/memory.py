# tools/memory.py
import logging
import contextvars
from typing import List
from langchain.tools import tool

logger = logging.getLogger(__name__)

# ContextVar for thread-local memory storage
# Each thread (task) will have its own independent list
_MEM_VAR: contextvars.ContextVar[List[str]] = contextvars.ContextVar("agent_memory")

def get_memory() -> List[str]:
    """Get the current thread's memory list. Initializes if empty."""
    try:
        return _MEM_VAR.get()
    except LookupError:
        # Initialize with a new empty list for this context
        new_mem = []
        _MEM_VAR.set(new_mem)
        return new_mem

def reset_memory() -> None:
    """Clear/Reset the memory for the current thread."""
    _MEM_VAR.set([])

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
    mem = get_memory()
    mem.append(note)
    result = f"stored ({len(mem)} total)"
    logger.info(f"✓ [remember] Note stored, total count: {len(mem)}")
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
    mem = get_memory()
    logger.info(f"🔖 [recall] Retrieving notes - Current count: {len(mem)}")
    result = "\n".join(mem) or "(empty)"
    logger.info(f"✓ [recall] Returned {len(mem)} notes")
    return result

