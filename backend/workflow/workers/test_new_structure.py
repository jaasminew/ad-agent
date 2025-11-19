"""Test new content blocks structure"""

from checklist_parser import parse_thought_into_blocks, has_checklist, get_checklist_summary
import json


def test_new_structure():
    """Test the new content blocks structure"""
    
    sample = """
I'm starting Beat 1. Let me analyze the requirements and understand what needs to be done.

The brand identity suggests a modern, minimalist approach.

```
Checklist:

- [x] reference_search - List tags and pick the reference image
- [x] palette_extract - Extract palette from the reference image
- [ ] attempt1_generation - Run MidJourney Attempt 1
- [ ] product_integration - Use nanobanana_generate

```

Now that the checklist is set up, I'll proceed with recalling previous information.

I'm also considering the lighting conditions - natural daylight with soft shadows.
"""
    
    print("=" * 80)
    print("Testing New Content Blocks Structure")
    print("=" * 80)
    
    blocks = parse_thought_into_blocks(sample)
    
    print(f"\n📦 Total blocks: {len(blocks)}")
    print(f"📋 Has checklist: {has_checklist(blocks)}")
    
    if has_checklist(blocks):
        print(f"📊 Summary: {get_checklist_summary(blocks)}")
    
    print("\n🔍 Block breakdown:")
    for i, block in enumerate(blocks, 1):
        print(f"\nBlock {i} - Type: {block.type}")
        if block.type == "text":
            preview = block.content[:60] + "..." if len(block.content) > 60 else block.content
            print(f"  Content: {preview}")
        elif block.type == "checklist":
            print(f"  Items: {block.total_items}")
            print(f"  Checked: {block.checked_items}")
            print(f"  Progress: {block.progress * 100:.0f}%")
    
    print("\n" + "=" * 80)
    print("📤 Frontend receives (JSON):")
    print("=" * 80)
    
    # Simulate what frontend receives
    frontend_data = {
        "type": "LLM_OUTPUT",
        "timestamp": "2024-01-15T10:30:00.000Z",
        "data": {
            "stage": "STORYBOARD_GEN_AGENT",
            "message": f"💭 {sample}",  # Still keep full text for backward compatibility
            "output": {
                "type": "thought",
                "content_blocks": [block.to_dict() for block in blocks],
                "checklist_summary": get_checklist_summary(blocks) if has_checklist(blocks) else None
            }
        }
    }
    
    print(json.dumps(frontend_data, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("✅ Advantages of this structure:")
    print("=" * 80)
    print("1. ✅ No duplication - content only stored once in blocks")
    print("2. ✅ Preserves order - array maintains sequence")
    print("3. ✅ Clear structure - each block has explicit type")
    print("4. ✅ Easy rendering - frontend loops through blocks")
    print("5. ✅ Extensible - can add more block types (image, table, etc.)")
    print("6. ✅ Backward compatible - still includes full message field")


if __name__ == "__main__":
    test_new_structure()

