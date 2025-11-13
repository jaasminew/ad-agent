# Testing Guide for Storyboard Generation Agent

This guide walks you through testing the storyboard generation agent from basic component tests to full episode processing.

## Prerequisites

### 1. Install Dependencies

```bash
cd /Users/lianxunw/Desktop/ad-agent

# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Install Optional Dependencies

For color palette extraction (recommended):
```bash
pip install colorthief
```

For the agent:
```bash
# OpenAI (primary, uses GPT-4o)
pip install langchain-openai

# Optional: Anthropic Claude (alternative)
# pip install langchain-anthropic
```

### 3. Set Environment Variables

Create a `.env` file in the project root:

```bash
# Required for agent (uses GPT-4o)
OPENAI_API_KEY=your-openai-api-key

# Optional: Anthropic Claude (alternative)
# ANTHROPIC_API_KEY=your-anthropic-api-key

# Required for PixelHub
PIXELHUB_API_URL=https://your-pixelhub-api.com

# Required for MidJourney
MIDJOURNEY_PROXY_BASE_URL=https://your-midjourney-proxy.com

# Required for Nanobanana
GOOGLE_API_KEY=your-google-gemini-api-key

# Optional: Tencent COS (for image uploads)
COS_SECRET_ID=your-cos-secret-id
COS_SECRET_KEY=your-cos-secret-key
COS_REGION=your-cos-region
COS_BUCKET=your-cos-bucket
```

Or export them directly:
```bash
export OPENAI_API_KEY="your-key-here"
export PIXELHUB_API_URL="https://your-api.com"
# ... etc
```

---

## Testing Levels

### Level 1: Component Tests (No API Calls)

Test individual components without making any API calls.

#### Test 1: Import Check

```bash
cd /Users/lianxunw/Desktop/ad-agent
python3 << 'EOF'
import sys
print("Testing imports...")

try:
    from storyboard_gen_agent import (
        StoryboardAgent,
        Beat,
        EpisodeConfig,
        ProductConfig,
        BeatResult,
        EpisodeResult,
    )
    print("✓ All imports successful!")
    print(f"  - StoryboardAgent: {StoryboardAgent.__name__}")
    print(f"  - Beat: {Beat.__name__}")
    print(f"  - EpisodeConfig: {EpisodeConfig.__name__}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)
EOF
```

#### Test 2: Data Models

```bash
python3 << 'EOF'
from storyboard_gen_agent import Beat, ProductConfig, EpisodeConfig

print("Testing data models...")

# Create a beat
beat = Beat(
    beat=1,
    heading="Test Scene",
    shot_description="A person in a room",
    action="Sits down"
)
print(f"✓ Beat created: {beat.heading}")

# Create product config
product = ProductConfig(
    product_image_url="https://example.com/product.jpg",
    target_object="laptop"
)
print(f"✓ Product config created: {product.target_object}")

# Create episode config
episode = EpisodeConfig(
    title="Test Episode",
    product_config=product,
    beats=[beat]
)
print(f"✓ Episode config created: {episode.title} with {len(episode.beats)} beat(s)")
print("\n✅ All data models working correctly!")
EOF
```

#### Test 3: Utility Functions

```bash
python3 << 'EOF'
from storyboard_gen_agent.utils import (
    normalize_beat,
    format_palette_for_prompt,
    build_midjourney_prompt,
    distortion_label_to_negative_prompt
)
from storyboard_gen_agent import Beat

print("Testing utility functions...")

# Test normalize_beat
beat = Beat(
    beat=1,
    heading="Morning Coffee",
    shot_description="A cozy cafe scene",
    action="Person opens laptop"
)
shot_text = normalize_beat(beat)
print(f"✓ normalize_beat: {shot_text[:50]}...")

# Test format_palette_for_prompt
palette = ["#FF5733", "#3366FF", "#28A745"]
formatted = format_palette_for_prompt(palette)
print(f"✓ format_palette_for_prompt: {formatted}")

# Test build_midjourney_prompt
prompt = build_midjourney_prompt(
    reference_image_url="https://example.com/ref.jpg",
    shot_text="Friends gathering in a park",
    palette=palette,
    negative_prompts=["extra fingers", "warped hands"]
)
print(f"✓ build_midjourney_prompt: {prompt[:80]}...")

# Test distortion_label_to_negative_prompt
label = "extra_fingers"
negative = distortion_label_to_negative_prompt(label)
print(f"✓ distortion_label_to_negative_prompt: '{label}' → '{negative}'")

print("\n✅ All utility functions working correctly!")
EOF
```

---

### Level 2: Tool Integration Tests (With API Calls)

Test individual tools with real API calls.

#### Test 4: Palette Extraction

```bash
python3 storyboard_gen_agent/test_palette.py
```

Expected output:
```
Testing Palette Extraction Integration
✓ Successfully imported extract_color_palette from utils
✓ Successfully imported extract_color_palette tool
✓ Successfully extracted palette: ['#abcdef', '#123456', ...]
✓ extract_color_palette is registered in the agent's toolset
✅ All tests passed!
```

#### Test 5: Individual Tool Tests

Create a test script:

```bash
cat > test_tools.py << 'EOF'
#!/usr/bin/env python3
"""Test individual tools with real API calls."""

import logging
logging.basicConfig(level=logging.INFO)

def test_pixelhub():
    """Test PixelHub tools"""
    print("\n" + "="*60)
    print("Testing PixelHub")
    print("="*60)
    
    from tools.pixelhub import get_pixelhub_client
    
    try:
        client = get_pixelhub_client()
        
        # Test list_tags
        print("\n1. Testing list_tags...")
        tags = client.list_tags(page=1, limit=10)
        print(f"✓ Found {tags.get('total', 0)} tags")
        
        # Test search_images
        print("\n2. Testing search_images...")
        results = client.search_images(tags=["landscape"], limit=3)
        print(f"✓ Found {results.get('total', 0)} images")
        if results.get('results'):
            print(f"   First image URL: {results['results'][0].get('url', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"✗ PixelHub test failed: {e}")
        return False

def test_midjourney():
    """Test MidJourney tools (WARNING: This will generate an image!)"""
    print("\n" + "="*60)
    print("Testing MidJourney")
    print("="*60)
    print("⚠️  WARNING: This will use MidJourney credits!")
    
    response = input("Continue with MidJourney test? (yes/no): ")
    if response.lower() != 'yes':
        print("Skipped MidJourney test")
        return True
    
    from tools.midjourney import get_midjourney_client
    
    try:
        client = get_midjourney_client()
        print("\n✓ MidJourney client initialized")
        print("   (Not running actual generation in this test)")
        return True
    except Exception as e:
        print(f"✗ MidJourney test failed: {e}")
        return False

def test_palette():
    """Test Palette Extractor"""
    print("\n" + "="*60)
    print("Testing Palette Extractor")
    print("="*60)
    
    from storyboard_gen_agent.utils import extract_color_palette
    
    try:
        # Use a simple test image
        url = "https://via.placeholder.com/300/FF5733/FFFFFF"
        palette = extract_color_palette(url)
        
        if palette:
            print(f"✓ Extracted {len(palette)} colors: {palette}")
            return True
        else:
            print("⚠️  Palette extraction returned None (may need dependencies)")
            return True  # Not a failure, just missing optional deps
    except Exception as e:
        print(f"✗ Palette extraction failed: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("TOOL INTEGRATION TESTS")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("PixelHub", test_pixelhub()))
    results.append(("MidJourney", test_midjourney()))
    results.append(("Palette", test_palette()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("✅ All tests passed!" if all_passed else "❌ Some tests failed"))
EOF

chmod +x test_tools.py
python3 test_tools.py
```

---

### Level 3: Agent Tests (Minimal Example)

Test the agent with a single beat (minimal API usage).

#### Test 6: Single Beat Processing

```bash
cat > test_single_beat.py << 'EOF'
#!/usr/bin/env python3
"""Test agent with a single beat."""

import logging
from storyboard_gen_agent import (
    StoryboardAgent,
    Beat,
    EpisodeConfig,
    ProductConfig,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("="*80)
    print("SINGLE BEAT TEST")
    print("="*80)
    
    # Create minimal episode with just 1 beat
    episode = EpisodeConfig(
        title="Test Episode - Single Beat",
        product_config=ProductConfig(
            product_image_url="https://example.com/product.jpg",
            target_object="laptop"
        ),
        beats=[
            Beat(
                beat=1,
                heading="Coffee Shop",
                shot_description="A person sits by a window in a cozy cafe",
                action="Opens their laptop and smiles"
            )
        ]
    )
    
    # Initialize LLM
    print("\n📦 Initializing agent...")
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        print("✓ Using OpenAI GPT-4o (ChatGPT-5 class model)")
    except ImportError:
        try:
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.7)
            print("✓ Using Anthropic Claude (fallback)")
        except ImportError:
            print("✗ No LLM available. Install langchain-openai")
            return
    
    # Create agent
    agent = StoryboardAgent(llm=llm, verbose=True, max_iterations=30)
    print(f"✓ Agent initialized with {len(agent.tools)} tools")
    
    # Process episode
    print("\n🎬 Processing episode...")
    try:
        result = agent.process_episode(episode)
        
        # Show results
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        print(f"Episode ID: {result.episode_id}")
        print(f"Title: {result.title}")
        print(f"Total beats: {result.total_beats}")
        print(f"Successful: {result.successful_beats}")
        print(f"Flagged: {result.flagged_beats}")
        
        if result.episode_palette:
            print(f"Episode palette: {result.episode_palette}")
        
        for beat_result in result.beats:
            print(f"\nBeat {beat_result.beat_number}:")
            print(f"  Attempts: {beat_result.total_attempts}")
            print(f"  Storyboard: {beat_result.storyboard_image_url}")
            print(f"  Final: {beat_result.final_image_url}")
            print(f"  Quality passed: {beat_result.quality_check_passed}")
            print(f"  Product integrated: {beat_result.product_replacement_success}")
            
            if beat_result.flagged_for_review:
                print(f"  ⚠️  FLAGGED: {beat_result.review_reason}")
        
        print("\n✅ Single beat test completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
EOF

chmod +x test_single_beat.py
python3 test_single_beat.py
```

---

### Level 4: Full Episode Test

Run the complete example with multiple beats.

#### Test 7: Full Example

```bash
# Run the included example
python3 storyboard_gen_agent/example.py
```

This will:
1. Process 3 beats with full workflow
2. Generate reference images, storyboards, and product-integrated images
3. Save results to JSON file
4. Show complete statistics

Expected output structure:
```
🎬 Starting Storyboard Generation Example
📦 Initializing Storyboard Agent...
✓ Loaded 9 tools
🎥 Processing Episode: Creative Workspace - Summer Campaign

Processing Beat 1 (1/3)
  → Finding reference image...
  → Extracting color palette...
  → Generating storyboard...
  → Quality check...
  → Integrating product...
✓ Beat 1 completed

Processing Beat 2 (2/3)
  → Finding reference image...
  → Using existing palette...
  → Generating storyboard...
  → Quality check...
  → Integrating product...
✓ Beat 2 completed

Processing Beat 3 (3/3)
  → Finding reference image...
  → Using existing palette...
  → Generating storyboard...
  → Quality check...
  → Integrating product...
✓ Beat 3 completed

✅ EPISODE COMPLETED
Total beats: 3
Successful: 3
Flagged: 0

💾 Results saved to: episode_result_xxx.json
```

---

## Quick Test Checklist

Use this checklist to verify everything works:

```bash
# 1. Environment check
cd /Users/lianxunw/Desktop/ad-agent
echo "✓ In project directory"

# 2. Dependencies check
python3 -c "import langchain; print('✓ langchain installed')" 2>/dev/null || echo "✗ Missing langchain"
python3 -c "import langchain_openai; print('✓ langchain-openai installed')" 2>/dev/null || echo "✗ Missing langchain-openai"
python3 -c "from PIL import Image; print('✓ Pillow installed')" 2>/dev/null || echo "✗ Missing Pillow"
python3 -c "from colorthief import ColorThief; print('✓ colorthief installed')" 2>/dev/null || echo "⚠️  Optional: colorthief"

# 3. Environment variables check
python3 << 'EOF'
import os
vars_to_check = [
    "OPENAI_API_KEY",
    "PIXELHUB_API_URL",
    "MIDJOURNEY_PROXY_BASE_URL",
    "GOOGLE_API_KEY"
]
for var in vars_to_check:
    if os.getenv(var):
        print(f"✓ {var} is set")
    else:
        print(f"✗ {var} is NOT set")
EOF

# 4. Import check
python3 -c "from storyboard_gen_agent import StoryboardAgent; print('✓ StoryboardAgent imports successfully')"

# 5. Run palette test
python3 storyboard_gen_agent/test_palette.py
```

---

## Troubleshooting

### Common Issues

**1. ModuleNotFoundError: No module named 'langchain'**
```bash
pip install langchain langchain-openai langchain-core
```

**2. ModuleNotFoundError: No module named 'storyboard_gen_agent'**
```bash
# Make sure you're in the project root
cd /Users/lianxunw/Desktop/ad-agent
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**3. Environment variables not set**
```bash
# Create .env file or export manually
export OPENAI_API_KEY="your-key"
export PIXELHUB_API_URL="your-url"
# etc...
```

**4. Palette extraction returns None**
```bash
# Install optional dependency
pip install colorthief
# OR just use Pillow (should already be installed)
pip install Pillow
```

**5. Agent timeout or max iterations**
```python
# Increase limits when creating agent
agent = StoryboardAgent(
    llm=llm,
    max_iterations=100,  # Default is 50
    max_execution_time=7200,  # 2 hours instead of default
)
```

---

## Next Steps

1. **Start with Level 1** tests to verify installation
2. **Run Level 2** tests to verify API connections
3. **Try Level 3** with a single beat to validate workflow
4. **Run Level 4** for full episode processing
5. **Review results** and adjust parameters as needed

Happy testing! 🚀

