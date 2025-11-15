# Quick Start Guide - AD Agent Workflow

## Installation

1. **Install dependencies:**
```bash
uv pip install -e .
```

2. **Configure environment variables:**

Create a `.env` file in the project root:
```bash
# Required
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
MIDJOURNEY_PROXY_BASE_URL=https://...
PIXELHUB_API_URL=https://...

# Optional (for COS upload)
COS_SECRET_ID=...
COS_SECRET_KEY=...
COS_BUCKET=...
COS_REGION=...
```

## Basic Usage

### Option 1: Use main.py directly

```python
python main.py
```

This will run with the example data defined in `main.py`.

### Option 2: Import and use programmatically

```python
from main import run_ad_workflow

result = run_ad_workflow(
    product_name="Your Product Name",
    brand_identity="Your Brand Identity",
    product_images="https://example.com/product.jpg",
    must_have_shots="shot1, shot2, shot3"
)

print(f"Video URL: {result['video_url']}")
```

### Option 3: Use the example script

```python
python examples/run_ad_workflow.py
```

## Workflow Steps

The workflow consists of 8 main steps:

1. **Script Writer** - Generate ad script with shots (max 3)
2. **Style Searcher** - Find style reference images (per shot, concurrent)
3. **Palette Extractor** - Extract dominant colors (per shot, concurrent)
4. **Midjourney Generator** - Generate scene images (per shot, concurrent)
5. **Distortion Checker** - Validate image quality with retry (per shot, concurrent)
6. **Product Composer** - Replace product in scene (per shot, concurrent)
7. **Video Generator** - Generate video or prompt (per shot, concurrent)
8. **Video Concatenator** - Concatenate all videos into final video (if enabled)

**Note**: Steps 2-7 run concurrently for each shot for better performance.

## Output

The workflow returns a dictionary containing:

```python
{
    # Aggregated results
    "aggregated_summary": {
        "total_shots": 3,
        "successful_shots": 3,
        "failed_shots": 0,
        "total_distortion_retries": 1,
        "video_generation_enabled": False
    },
    
    # Individual shot outputs
    "final_outputs": [
        {
            "shot_index": 1,
            "shot_description": "...",
            "style_image_url": "https://...",
            "midjourney_image_url": "https://...",
            "composed_image_url": "https://...",
            "video_prompt": "...",  # Always present
            "video_url": "https://...",  # Only if generate_video=True
            "status": "completed"
        },
        # ... more shots
    ],
    
    # Final concatenated video (only if generate_video=True)
    "final_video_url": "https://...",
    
    # Process logs
    "messages": ["Step 1 done", "Step 2 done", ...]
}
```

## Usage Examples

### Generate only images and prompts (faster, no video)

```python
result = run_ad_workflow(
    product_name="Polaroid Camera",
    brand_identity="Nostalgia, Artistic, Instant Sharing",
    product_images="https://example.com/product.jpg",
    must_have_shots="Scenes of friends sharing photos",
    generate_video=False  # Default
)
```

### Generate and concatenate videos (slower, full workflow)

```python
result = run_ad_workflow(
    product_name="Polaroid Camera",
    brand_identity="Nostalgia, Artistic, Instant Sharing",
    product_images="https://example.com/product.jpg",
    must_have_shots="Scenes of friends sharing photos",
    generate_video=True  # Enable video generation and concatenation
)

# Access final video
final_video = result['final_video_url']
```

## Visualize Workflow

```bash
python visualize_workflow.py
```

This will:
- Print the workflow structure
- Generate `workflow_graph.png` (if dependencies available)
- Generate `workflow_graph.mmd` (Mermaid format)

## Troubleshooting

### Import Errors

If you see import errors for `dotenv`, `langgraph`, etc.:
```bash
pip install python-dotenv langgraph langchain langchain-openai google-genai pillow requests
```

### API Errors

Make sure all API keys are correctly configured in `.env`.

### COS Upload Failures

COS upload is optional. The workflow will continue even if COS upload fails, using local file paths instead.

## Documentation

- **WORKFLOW_README.md** - Complete documentation
- **IMPLEMENTATION_SUMMARY.md** - Implementation details
- **workflow.md** - Original workflow specification

## Project Structure

```
ad-agent/
├── main.py                    # Main workflow
├── workers/                   # Worker nodes
│   ├── script_writer.py
│   ├── style_searcher.py
│   ├── palette_extractor.py
│   ├── midjourney_generator.py
│   ├── distortion_checker.py
│   ├── product_composer.py
│   └── video_generator.py
├── tools/                     # API clients
└── examples/                  # Examples
```

## Next Steps

1. Review `WORKFLOW_README.md` for detailed information
2. Customize workers in `workers/` directory
3. Add your own product data
4. Run the workflow and generate videos!

