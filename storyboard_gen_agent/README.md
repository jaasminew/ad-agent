# Storyboard Generation Agent

A LangChain ReAct agent that transforms script beats into product-integrated advertisement images.

## Overview

The Storyboard Generation Agent orchestrates multiple AI services to create high-quality advertisement storyboards:

1. **PixelHub** - Find style reference images
2. **MidJourney** - Generate storyboard frames
3. **Distortion Checker** - Quality control for anatomical correctness
4. **Nanobanana** - Product integration via object replacement
5. **Memory** - Episode state and palette management

## Architecture

Based on the [Image Generation Agent Architecture](../image_gen_agent_architecture.md).

### Key Features

- ✅ **ReAct Pattern**: Agent reasons about quality feedback and decides when to retry
- ✅ **Color Palette Consistency**: First beat establishes colors, reused across episode
- ✅ **Quality Gates**: Up to 3 attempts with distortion checking
- ✅ **Graceful Degradation**: Flags issues for review, continues processing
- ✅ **Product Integration**: Seamless object replacement with Nanobanana

## Installation

```bash
cd /Users/lianxunw/Desktop/ad-agent
pip install -e .
```

### Required Environment Variables

```bash
# PixelHub API
export PIXELHUB_API_URL="https://your-pixelhub-api.com"

# MidJourney Proxy
export MIDJOURNEY_PROXY_BASE_URL="https://your-midjourney-proxy.com"

# Google Gemini (for Nanobanana)
export GOOGLE_API_KEY="your-google-api-key"

# Anthropic Claude (for the agent)
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Optional: Tencent COS (for image upload)
export COS_SECRET_ID="your-cos-secret-id"
export COS_SECRET_KEY="your-cos-secret-key"
export COS_REGION="your-cos-region"
export COS_BUCKET="your-cos-bucket"
```

## Usage

### Basic Example

```python
from storyboard_gen_agent import StoryboardAgent, EpisodeConfig, Beat, ProductConfig
from langchain_openai import ChatOpenAI

# Initialize LLM
llm = ChatOpenAI(model="gpt-4", temperature=0.7)

# Configure episode
episode = EpisodeConfig(
    title="Summer Product Launch",
    product_config=ProductConfig(
        product_image_url="https://example.com/product.png",
        target_object="laptop"
    ),
    beats=[
        Beat(
            beat=1,
            heading="Morning Coffee Shop",
            shot_description="A creative professional sits by a sunlit window",
            action="Opens laptop and smiles at the screen"
        ),
        Beat(
            beat=2,
            heading="Collaborative Workspace",
            shot_description="A team gathered around a table with laptops",
            action="Brainstorming session with notes and diagrams"
        ),
    ]
)

# Initialize agent with LLM
agent = StoryboardAgent(llm=llm, verbose=True)

# Process episode
result = agent.process_episode(episode)

# Access results
print(f"Episode ID: {result.episode_id}")
print(f"Total beats: {result.total_beats}")
print(f"Successful: {result.successful_beats}")
print(f"Flagged: {result.flagged_beats}")

# Access individual beat results
for beat_result in result.beats:
    print(f"\nBeat {beat_result.beat_number}:")
    print(f"  Storyboard: {beat_result.storyboard_image_url}")
    print(f"  Final: {beat_result.final_image_url}")
    print(f"  Attempts: {beat_result.total_attempts}")
    print(f"  Quality Pass: {beat_result.quality_check_passed}")
    print(f"  Product Success: {beat_result.product_replacement_success}")
```

### Advanced Usage

```python
# You can use any LangChain-compatible chat model

# Example with OpenAI:
from langchain_openai import ChatOpenAI
custom_llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.5,
    max_tokens=8192,
)

# Or with Anthropic (requires: pip install langchain-anthropic):
# from langchain_anthropic import ChatAnthropic
# custom_llm = ChatAnthropic(
#     model="claude-sonnet-4-20250514",
#     temperature=0.5,
#     max_tokens=8192,
# )

agent = StoryboardAgent(
    llm=custom_llm,
    verbose=True,
    max_iterations=100,
    max_execution_time=3600,  # 1 hour
)

# Process multiple episodes
episodes = [episode1, episode2, episode3]
results = []

for ep in episodes:
    result = agent.process_episode(ep)
    results.append(result)
    agent.reset()  # Clear state between episodes
```

## Workflow Details

### Per-Beat Processing Flow

```
1. Check Memory for Episode Palette
   ↓
2. Find Reference Image (PixelHub)
   ↓
3. Extract/Store Color Palette (first beat only)
   ↓
4-6. Generation Loop (max 3 attempts):
   ├─ Generate with MidJourney
   ├─ Upscale best image
   ├─ Check for distortions
   └─ Retry with negative prompts if needed
   ↓
7. Replace Object with Product (Nanobanana)
   ↓
8. Store Results in Memory
```

### Quality Control

Each generated storyboard is checked for:
- ✓ Extra fingers / hands
- ✓ Warped hand geometry
- ✓ Warped limbs / impossible angles
- ✓ Elongated limbs
- ✓ Extra limbs
- ✓ Deformed face

### Retry Logic

- **Attempt 1**: Default negative prompts
- **Attempt 2**: Add detected distortion labels to negatives
- **Attempt 3**: Final retry with all accumulated negatives
- **If all fail**: Use best attempt (lowest distortion count), flag for review

## Data Models

### Input Models

```python
class Beat(BaseModel):
    beat: int
    heading: str
    shot_description: str
    action: str

class ProductConfig(BaseModel):
    product_image_url: str
    target_object: str

class EpisodeConfig(BaseModel):
    title: str
    product_config: ProductConfig
    beats: List[Beat]
```

### Output Models

```python
class BeatResult(BaseModel):
    beat_number: int
    shot_text: str
    reference_image_url: Optional[str]
    color_palette: Optional[List[str]]
    
    # Generation details
    attempts: List[GenerationAttempt]
    total_attempts: int
    
    # Final images
    storyboard_image_url: str
    final_image_url: Optional[str]
    
    # Status flags
    quality_check_passed: bool
    product_replacement_success: bool
    flagged_for_review: bool
    review_reason: Optional[str]

class EpisodeResult(BaseModel):
    episode_id: str
    title: str
    episode_palette: Optional[List[str]]
    beats: List[BeatResult]
    
    # Statistics
    total_beats: int
    successful_beats: int
    flagged_beats: int
```

## Logging

The agent uses Python's `logging` module. Configure as needed:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Troubleshooting

### Common Issues

1. **"PIXELHUB_API_URL environment variable is not set"**
   - Set all required environment variables before running

2. **Agent takes too long / times out**
   - Increase `max_execution_time` parameter
   - Check MidJourney proxy response times
   - Verify network connectivity to all services

3. **All quality checks fail**
   - Review the generated images manually
   - Adjust negative prompts in `utils.py`
   - Consider adjusting distortion detection thresholds

4. **Product replacement fails**
   - Verify product image URL is accessible
   - Check that target_object description is clear
   - Review Nanobanana logs for specific errors

## Development

### Project Structure

```
storyboard_gen_agent/
├── __init__.py              # Package exports
├── agent.py                 # Main StoryboardAgent class
├── models.py                # Pydantic data models
├── tools.py                 # Tool loading and configuration
├── utils.py                 # Helper functions
├── prompt_templates.py      # Agent system prompts
└── README.md               # This file
```

### Adding New Features

1. **New Tools**: Add to `tools.py` and update `get_storyboard_tools()`
2. **New Prompt Logic**: Update `prompt_templates.py`
3. **New Data Fields**: Extend models in `models.py`
4. **New Utilities**: Add to `utils.py`

## Future Enhancements

- [x] **Color Palette Extraction**: Extract dominant colors from reference images ✓
- [ ] **MidJourney Inpainting**: Support targeted region regeneration
- [ ] **Parallel Beat Processing**: Process multiple beats concurrently
- [ ] **Custom Quality Thresholds**: Configurable distortion tolerance levels
- [ ] **Result Caching**: Avoid regenerating identical scenes
- [ ] **A/B Testing**: Generate multiple variations per beat

## License

See main project LICENSE file.

## Credits

Built on top of:
- LangChain
- Anthropic Claude
- MidJourney
- Google Gemini
- MediaPipe (for distortion detection)

