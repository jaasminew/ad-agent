# tools/memory.py
import logging
from typing import List
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class Memory:
    """
    Instance-based memory storage for agent sessions.
    Ensures each agent/task execution has its own isolated memory context.
    """
    def __init__(self):
        self.storage: List[str] = []

    def remember(self, note: str) -> str:
        """
        Store a note in memory for the current session.
        
        Args:
            note: The information to remember (e.g., "episode_palette: #FF5733, #33FF57, #3357FF, #F333FF")
        
        Returns:
            Confirmation message with total count of stored notes.
        """
        logger.info(f"💾 [remember] Storing note: '{note[:50]}...'")
        self.storage.append(note)
        result = f"stored ({len(self.storage)} total)"
        logger.info(f"✓ [remember] Note stored, total count: {len(self.storage)}")
        return result

    def recall(self, query: str = "") -> str:
        """
        Return all stored notes from memory.
        
        Args:
            query: Optional search query (currently unused, leave empty)
        
        Returns:
            All stored notes separated by newlines, or "(empty)" if no notes exist.
        """
        logger.info(f"🔖 [recall] Retrieving notes - Current count: {len(self.storage)}")
        result = "\n".join(self.storage) or "(empty)"
        logger.info(f"✓ [recall] Returned {len(self.storage)} notes")
        return result
    
    def clear(self):
        """Clear all notes from memory."""
        self.storage.clear()
        
    def extend(self, notes: List[str]):
        """Add multiple notes to memory."""
        self.storage.extend(notes)
        
    def __iter__(self):
        return iter(self.storage)

class RememberInput(BaseModel):
    note: str = Field(description="The information to remember")

class RecallInput(BaseModel):
    query: str = Field(default="", description="Optional search query")

def create_memory_tools(memory_instance: Memory) -> List[StructuredTool]:
    """
    Create LangChain tools bound to a specific memory instance.
    
    Args:
        memory_instance: The Memory object to bind the tools to.
        
    Returns:
        List of StructuredTool objects (remember, recall).
    """
    
    remember_tool = StructuredTool.from_function(
        func=memory_instance.remember,
        name="remember",
        description="Store a note in memory for the current session.",
        args_schema=RememberInput
    )
    
    recall_tool = StructuredTool.from_function(
        func=memory_instance.recall,
        name="recall",
        description="Return all stored notes from memory.",
        args_schema=RecallInput
    )
    
    return [remember_tool, recall_tool]
