# tools/memory.py
import logging
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# In-memory storage for the session
MEM = []


# Input schemas for tools
class RememberInput(BaseModel):
    """Input schema for remember tool"""
    note: str = Field(description="The note to store for this session")


# Implementation functions
def _remember_impl(note: str) -> str:
    """Implementation for remember tool"""
    logger.info(f"💾 [remember] Storing note: '{note[:50]}...'")
    MEM.append(note)
    result = f"stored ({len(MEM)} total)"
    logger.info(f"✓ [remember] Note stored, total count: {len(MEM)}")
    return result


def _recall_impl() -> str:
    """Implementation for recall tool"""
    logger.info(f"🔖 [recall] Retrieving notes - Current count: {len(MEM)}")
    result = "\n".join(MEM) or "(empty)"
    logger.info(f"✓ [recall] Returned {len(MEM)} notes")
    return result


# Create StructuredTool instances
remember = StructuredTool.from_function(
    func=_remember_impl,
    name="remember",
    description="Store a note for this session. Use this to remember important information like image URLs, task IDs, palette colors, or any other data you need to track across multiple steps.",
    args_schema=RememberInput,
)

recall = StructuredTool.from_function(
    func=_recall_impl,
    name="recall",
    description="Return all stored notes from this session. Use this to retrieve all the information you've remembered so far.",
)

