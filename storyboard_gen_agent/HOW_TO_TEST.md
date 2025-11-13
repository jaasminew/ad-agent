# How to Test the Storyboard Generation Agent

## Quick Start (3 Steps)

### Step 1: Run Quick Test
```bash
cd /Users/lianxunw/Desktop/ad-agent
python3 storyboard_gen_agent/quick_test.py
```

This will check:
- ✓ Environment variables
- ✓ Dependencies
- ✓ Imports
- ✓ Tools
- ✓ Data models
- ✓ Utilities

**Expected Output:**
```
████████████████████████████████████████████████
  STORYBOARD GENERATION AGENT - QUICK TEST
████████████████████████████████████████████████

==================================================================
  1. ENVIRONMENT VARIABLES CHECK
==================================================================
Required:
  ✓ OPENAI_API_KEY: sk-proj...
  ✓ PIXELHUB_API_URL: https://...
  ✓ MIDJOURNEY_PROXY_BASE_URL: https://...
  ✓ GOOGLE_API_KEY: AIzaSy...

==================================================================
  2. DEPENDENCIES CHECK
==================================================================
Required:
  ✓ langchain: installed
  ✓ pydantic: installed
  ...

==================================================================
  SUMMARY
==================================================================
  ✓ PASS: Environment Variables
  ✓ PASS: Dependencies
  ✓ PASS: Agent Imports
  ✓ PASS: Tools Loading
  ✓ PASS: Data Models
  ✓ PASS: Utility Functions

  Results: 6/6 checks passed

  ✅ All checks passed! Agent is ready to use.
```

---

### Step 2: Test Palette Extraction
```bash
python3 storyboard_gen_agent/test_palette.py
```

**Expected Output:**
```
Testing Palette Extraction Integration
✓ Successfully imported extract_color_palette from utils
✓ Successfully imported extract_color_palette tool
✓ Successfully extracted palette: ['#ff5733', '#3366ff', '#28a745', '#ffc107']
✓ extract_color_palette is registered in the agent's toolset
✅ All tests passed! Palette extraction is properly integrated.
```

---

### Step 3: Run Full Example
```bash
python3 storyboard_gen_agent/example.py
```

**This will:**
1. Process 3 beats from a sample episode
2. Generate storyboards with MidJourney
3. Check quality with distortion detection
4. Integrate product with Nanobanana
5. Save results to JSON file

**Expected Output:**
```
🎬 Starting Storyboard Generation Example
🤖 Initializing LLM...
✓ Using OpenAI GPT-4o
📦 Initializing Storyboard Agent...
✓ Loaded 9 tools

🎥 Processing Episode: Creative Workspace - Summer Campaign
   Total beats: 3

============================================================
Processing Beat 1 (1/3)
============================================================
[Agent workflow...]
✓ Beat 1 completed

[... beats 2 and 3 ...]

============================================================
🎉 Episode Complete!
   Total beats: 3
   Successful: 3
   Flagged: 0
============================================================

💾 Results saved to: episode_result_xxx.json
```

---

## If Quick Test Fails

### Missing Dependencies?
```bash
# Install with uv (recommended)
cd /Users/lianxunw/Desktop/ad-agent
uv sync

# Or with pip
pip install langchain langchain-openai langchain-core
pip install colorthief  # Optional but recommended
```

### Missing Environment Variables?
```bash
# Set them in .env file (create if doesn't exist)
cat > .env << EOF
OPENAI_API_KEY=your-key-here
PIXELHUB_API_URL=https://your-pixelhub-api.com
MIDJOURNEY_PROXY_BASE_URL=https://your-midjourney-proxy.com
GOOGLE_API_KEY=your-google-api-key
EOF

# Or export manually
export OPENAI_API_KEY="your-key"
export PIXELHUB_API_URL="https://..."
```

### Import Errors?
```bash
# Make sure you're in the project root
cd /Users/lianxunw/Desktop/ad-agent

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## Testing Levels

### Level 1: Basic Checks (No API calls)
```bash
python3 storyboard_gen_agent/quick_test.py
```
✓ Fastest (< 1 second)  
✓ No API credits used  
✓ Checks imports and setup

### Level 2: Component Tests (Minimal API calls)
```bash
python3 storyboard_gen_agent/test_palette.py
```
✓ Fast (< 5 seconds)  
✓ Tests palette extraction  
✓ Minimal API usage

### Level 3: Full Example (Full API calls)
```bash
python3 storyboard_gen_agent/example.py
```
⚠️ Slower (5-15 minutes)  
⚠️ Uses API credits  
✓ Tests complete workflow

---

## Detailed Testing Guide

For comprehensive testing instructions, see:
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Full testing documentation
- **[INSTALL.md](INSTALL.md)** - Installation instructions
- **[README.md](README.md)** - Usage documentation

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: langchain` | Run: `pip install langchain langchain-openai` |
| `No module named storyboard_gen_agent` | Ensure you're in `/Users/lianxunw/Desktop/ad-agent` |
| Environment variables not set | Create `.env` file or `export` them |
| Palette returns None | Install: `pip install colorthief` |
| Agent timeout | Increase `max_execution_time` in agent init |

---

## What Gets Tested

```
Quick Test (quick_test.py)
├─ Environment Variables ✓
├─ Dependencies ✓
├─ Imports ✓
├─ Tools ✓
├─ Data Models ✓
└─ Utilities ✓

Palette Test (test_palette.py)
├─ Import palette extractor ✓
├─ Extract colors from URL ✓
└─ Tool registration ✓

Full Example (example.py)
├─ Episode with 3 beats
├─ For each beat:
│  ├─ Find reference image (PixelHub)
│  ├─ Extract color palette (first beat only)
│  ├─ Generate storyboard (MidJourney)
│  ├─ Quality check (Distortion Checker)
│  └─ Product integration (Nanobanana)
└─ Save results to JSON ✓
```

---

## Quick Commands Reference

```bash
# Navigate to project
cd /Users/lianxunw/Desktop/ad-agent

# Run quick test
python3 storyboard_gen_agent/quick_test.py

# Test palette extraction
python3 storyboard_gen_agent/test_palette.py

# Run full example
python3 storyboard_gen_agent/example.py

# Check environment
python3 -c "import os; print('OpenAI:', os.getenv('OPENAI_API_KEY')[:10] + '...' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"

# List all tools
python3 -c "from storyboard_gen_agent.tools import get_tool_names; print('\n'.join(get_tool_names()))"
```

---

## Ready to Go? ✅

If `quick_test.py` passes all checks, you're ready to use the agent!

**Next:** Run `python3 storyboard_gen_agent/example.py` to see it in action.

