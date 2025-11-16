# AD Agent

AI-powered advertising video generation workflow built with LangGraph.

## Features

- 🎬 Complete video generation pipeline (script → images → videos → BGM)
- 🤖 Multi-stage workflow with LangGraph
- 🎨 Style-consistent image generation with Midjourney
- 🔍 Automatic quality control and distortion detection
- 🎵 AI-generated background music
- 🎞️ Multiple video generation models (Veo, Kling, Seedance)

## Quick Start

1. **Install dependencies**

```bash
uv sync
```

2. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Start LangGraph Server**

```bash
uv run langgraph dev
```

Visit http://localhost:2024 for the API or https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024 for LangGraph Studio.

## Usage

### With LangGraph Server

```bash
uv run langgraph dev
```

Use LangGraph Studio UI to configure and run workflows.

### Programmatically

```python
from agent import app

result = app.invoke(
    {
        "product_name": "Your Product",
        "brand_identity": "Brand Values",
        "product_images": "https://example.com/image.jpg",
        "must_have_shots": "Required scenes",
    },
    {
        "configurable": {
            "product_name": "Your Product",
            "brand_identity": "Brand Values", 
            "product_images": "https://example.com/image.jpg",
            "must_have_shots": "Required scenes",
            "generate_video": True,
            "video_model": "veo"
        }
    }
)
```

## Configuration

The workflow uses two separate configuration mechanisms:

### 1. Input State (`InputState`)
User-provided inputs when invoking the graph. These are the fields exposed in the LangGraph Studio UI:

- `product_name`: Product name
- `brand_identity`: Brand identity/values
- `product_images`: Product image URL(s)
- `must_have_shots`: Required shots (comma-separated)
- `num_shots`: Number of shots to generate (integer, default: 3)
- `generate_video`: Enable video generation (boolean, default: False)
- `video_model`: Video model - "veo", "kling", or "seedance" (default: "veo")

### 2. Runtime Context (`Context`)
Optional configuration parameters set via the `configurable` key for advanced use cases.

**Note**: For most use cases, you only need to provide the `InputState` fields. The `Context` is used for programmatic invocations where you want to override defaults.

## Project Structure

```
langgraph/
├── src/agent/
│   ├── graph.py           # Main workflow graph
│   ├── workers/           # Workflow nodes
│   ├── tools/             # LangChain tools
│   ├── prompts/           # LLM prompts
│   └── utils/             # Utilities
├── tests/                 # Tests
├── examples/              # Example scripts
├── docs/                  # Documentation
├── langgraph.json         # LangGraph config
└── pyproject.toml         # Dependencies
```

## Workflow

The workflow uses LangGraph's **Fan-out/Fan-in** pattern for parallel shot processing:

1. **Script Writing** (`write_script`) - Generate ad script from product info
2. **Fan-out** (`fan_out_shots`) - Dispatch shots for parallel processing using `Send` API
3. **Shot Processing** (`process_single_shot`) - Each shot is processed concurrently through:
   - Style image search
   - Color palette extraction
   - Midjourney image generation
   - Distortion detection (with retry)
   - Product composition
   - Video generation
4. **Fan-in** (`aggregate_results`) - Collect all shot results (automatic via state updates)
5. **Video Concatenation** (`concatenate_videos`) - Merge videos with smooth transitions
6. **BGM Generation** (`generate_bgm`) - Add background music

### Why use Send API instead of a simple loop?

The previous implementation had a `process_shots` node that manually called `shot_workflow.invoke()` in a loop. This had several limitations:

- ❌ No visibility into shot processing in LangGraph Studio UI
- ❌ No automatic parallelization by LangGraph
- ❌ Lost debugging and tracing capabilities
- ❌ Subgraph execution hidden from the graph visualization

The new implementation uses `Send` to properly integrate shot processing:

- ✅ Each shot is a separate task visible in Studio UI
- ✅ LangGraph can parallelize shot processing automatically
- ✅ Full tracing and debugging support
- ✅ Clean graph visualization showing the fan-out/fan-in pattern

## API Keys

- `OPENAI_API_KEY` - OpenAI API
- `TAVILY_API_KEY` - Tavily search
- `MIDJOURNEY_PROXY_BASE_URL` - Midjourney proxy
- `PIXELHUB_API_URL` - PixelHub image search
- `GOOGLE_API_KEY` - Google Gemini (Nanobanana & Veo)
- `COS_*` - Tencent Cloud COS (for storage)
- `LANGSMITH_API_KEY` - LangSmith tracing

## Development

```bash
# Run tests
make test

# Lint code
make lint

# Format code
make format
```

## License

MIT
