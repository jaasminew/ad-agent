"""Checklist Parser - Parse thought into structured content blocks"""

import re
from typing import List, Optional, Union
from dataclasses import dataclass, asdict


@dataclass
class ChecklistItem:
    """Represents a single checklist item"""
    slug: str
    description: str
    checked: bool
    optional: bool = False


@dataclass
class TextBlock:
    """Text content block"""
    type: str = "text"
    content: str = ""
    
    def to_dict(self) -> dict:
        return {"type": self.type, "content": self.content}


@dataclass
class ChecklistBlock:
    """Checklist content block"""
    type: str = "checklist"
    items: List[ChecklistItem] = None
    total_items: int = 0
    checked_items: int = 0
    mandatory_items: int = 0
    mandatory_checked: int = 0
    progress: float = 0.0
    mandatory_complete: bool = False
    summary: str = ""
    
    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "items": [asdict(item) for item in self.items],
            "total_items": self.total_items,
            "checked_items": self.checked_items,
            "mandatory_items": self.mandatory_items,
            "mandatory_checked": self.mandatory_checked,
            "progress": self.progress,
            "mandatory_complete": self.mandatory_complete,
            "summary": self.summary,
        }


ContentBlock = Union[TextBlock, ChecklistBlock]


def parse_thought_into_blocks(thought_text: str) -> List[ContentBlock]:
    """
    Parse thought text into ordered content blocks.
    
    Splits text by checklist blocks and creates structured content.
    
    Args:
        thought_text: The full thought text from agent
        
    Returns:
        List of content blocks (TextBlock or ChecklistBlock) in order
    """
    blocks: List[ContentBlock] = []
    
    # Pattern to find checklist blocks with their positions
    checklist_pattern = r'```\s*\n?\s*Checklist:\s*\n(.*?)\n```'
    
    last_pos = 0
    
    for match in re.finditer(checklist_pattern, thought_text, re.DOTALL | re.IGNORECASE):
        # Add text before checklist
        text_before = thought_text[last_pos:match.start()].strip()
        if text_before:
            blocks.append(TextBlock(content=text_before))
        
        # Parse and add checklist block
        checklist_content = match.group(1)
        checklist_block = _parse_checklist_block(checklist_content)
        if checklist_block:
            blocks.append(checklist_block)
        
        last_pos = match.end()
    
    # Add remaining text after last checklist
    text_after = thought_text[last_pos:].strip()
    if text_after:
        blocks.append(TextBlock(content=text_after))
    
    # If no checklist found, return entire text as one block
    if not blocks:
        blocks.append(TextBlock(content=thought_text.strip()))
    
    return blocks


def _parse_checklist_block(checklist_content: str) -> Optional[ChecklistBlock]:
    """
    Parse checklist markdown into structured ChecklistBlock.
    
    Args:
        checklist_content: The content inside checklist code block
        
    Returns:
        ChecklistBlock or None if parsing fails
    """
    # Pattern: - [ ] slug - description
    # or: - [x] slug - description
    item_pattern = r'[-*]\s*\[([ x])\]\s+([a-z_0-9]+)\s*[-–—]\s*(.+?)(?:\(.*?\))?$'
    
    items = []
    for line in checklist_content.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        item_match = re.match(item_pattern, line, re.IGNORECASE)
        if item_match:
            checked = item_match.group(1).lower() == 'x'
            slug = item_match.group(2).strip()
            description = item_match.group(3).strip()
            
            # Detect if optional
            optional = bool(re.search(r'\(only if|if .* fail', line, re.IGNORECASE))
            
            items.append(ChecklistItem(
                slug=slug,
                description=description,
                checked=checked,
                optional=optional,
            ))
    
    if not items:
        return None
    
    # Calculate statistics
    total_items = len(items)
    checked_items = sum(1 for item in items if item.checked)
    mandatory_items = sum(1 for item in items if not item.optional)
    mandatory_checked = sum(1 for item in items if item.checked and not item.optional)
    progress = checked_items / total_items if total_items > 0 else 0
    mandatory_complete = mandatory_checked == mandatory_items
    summary = f"Checklist: {checked_items}/{total_items} items completed ({mandatory_checked}/{mandatory_items} mandatory)"
    
    return ChecklistBlock(
        items=items,
        total_items=total_items,
        checked_items=checked_items,
        mandatory_items=mandatory_items,
        mandatory_checked=mandatory_checked,
        progress=progress,
        mandatory_complete=mandatory_complete,
        summary=summary,
    )


def has_checklist(blocks: List[ContentBlock]) -> bool:
    """Check if content blocks contain any checklist"""
    return any(block.type == "checklist" for block in blocks)


def get_checklist_summary(blocks: List[ContentBlock]) -> Optional[str]:
    """Get summary of first checklist in blocks"""
    for block in blocks:
        if isinstance(block, ChecklistBlock):
            return block.summary
    return None


# Legacy compatibility functions
def extract_checklist_from_thought(thought_text: str) -> Optional[ChecklistBlock]:
    """
    Legacy function: Extract first checklist from thought.
    
    For backward compatibility. New code should use parse_thought_into_blocks().
    """
    blocks = parse_thought_into_blocks(thought_text)
    for block in blocks:
        if isinstance(block, ChecklistBlock):
            return block
    return None


def format_checklist_summary(checklist: ChecklistBlock) -> str:
    """
    Legacy function: Format checklist summary.
    
    For backward compatibility.
    """
    return checklist.summary
