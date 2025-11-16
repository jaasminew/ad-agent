# tools/memory.py
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# In-memory storage for the session
MEM = []

@tool("remember")
def remember(note: str) -> str:
    """Store a note for this session."""
    logger.info(f"💾 [remember] Storing note: '{note[:50]}...'")
    MEM.append(note)
    result = f"stored ({len(MEM)} total)"
    logger.info(f"✓ [remember] Note stored, total count: {len(MEM)}")
    return result

@tool("recall")
def recall(_: str="") -> str:
    """Return all stored notes."""
    logger.info(f"🔖 [recall] Retrieving notes - Current count: {len(MEM)}")
    result = "\n".join(MEM) or "(empty)"
    logger.info(f"✓ [recall] Returned {len(MEM)} notes")
    return result

