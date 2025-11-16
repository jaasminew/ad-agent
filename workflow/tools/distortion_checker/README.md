# Distortion Checker

LangChain tools for detecting anatomical distortions in images using Google MediaPipe.

## Installation

From the project root, install dependencies:

```bash
uv pip install mediapipe opencv-python pillow numpy
```

**Note:** Requires Python ≤ 3.12 (MediaPipe not yet compatible with 3.13)

Dependencies are documented in `pyproject.toml`.

## Quick Start

```python
from tools import check_image_distortion

# Check an image for distortions
result = check_image_distortion("path/to/image.jpg")
print(result)
```

## Available Tools

### `check_image_distortion(image_path: str) -> str`

Detects anatomical distortions in images.

**Detects:**
- `extra_fingers` - More than 5 fingers on a hand
- `extra_hands` - More than 2 hands in image
- `warped_hand` - Abnormal hand geometry
- `warped_limbs` - Impossible joint angles
- `elongated_limbs` - Abnormal limb proportions
- `deformed_face` - Distorted facial features

**Returns:** Detailed report with confidence scores and bounding boxes

### `get_distortion_labels(_: str) -> str`

Returns descriptions of all distortion types.

### `get_distortion_stats(_: str) -> str`

Returns detection thresholds and configuration.

## Example

See `example.py` for usage examples.

```bash
# From project root - show available labels
uv run python tools/distortion_checker/example.py

# Check an image
uv run python tools/distortion_checker/example.py /path/to/image.jpg
```

## Performance

- Processing: 100-200ms per image (CPU)
- First run: ~500ms (model loading)
- Memory: 200-400MB

## LangChain Integration

```python
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from tools import check_image_distortion

llm = ChatOpenAI(model="gpt-4")
agent = initialize_agent(
    tools=[check_image_distortion],
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
)

response = agent.run("Check this image: photo.jpg")
```

## Architecture

```
distortion_checker/
├── models.py       # Data models
├── utils.py        # Image utilities
├── detectors.py    # MediaPipe wrappers
├── analyzers.py    # Detection logic
├── checker.py      # Main pipeline
└── tools.py        # LangChain tools
```

## Dependencies

Managed by `pyproject.toml`:
- mediapipe ≥ 0.10.0
- opencv-python ≥ 4.8.0
- Pillow ≥ 10.0.0
- numpy ≥ 1.24.0
- pydantic ≥ 2.0.0
- langchain ≥ 0.3.0

