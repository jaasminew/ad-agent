# AD Agent Backend

Complete backend implementation including API service, agents, and workflow.

## Project Structure

```
backend/
├── main.py                 # Service entry point
├── pyproject.toml          # Project dependencies (uv managed)
├── service/                # API service
│   ├── app.py             # FastAPI app export
│   ├── main.py            # API routes and endpoints
│   ├── models.py          # Data models
│   ├── database.py        # SQLite operations
│   ├── task_manager.py    # Task management
│   └── workflow_executor.py  # Workflow integration
├── agent/                  # AI agents
│   ├── script_gen_agent/  # Script generation
│   └── storyboard_gen_agent/  # Storyboard generation
└── workflow/               # Workflow orchestration
    ├── main.py
    └── workers/           # Worker nodes
```

## Quick Start

### 1. Install uv (if needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Configure Environment

```bash
cd backend
cp workflow/.env.example .env
# Edit .env with your API keys
```

Required environment variables:
```env
ANTHROPIC_API_KEY=your_key_here
MIDJOURNEY_API_URL=...
MIDJOURNEY_API_KEY=...
# ... other service configurations
```

### 3. Start the Service

**Method 1: Using `uv run` (recommended)**

```bash
cd backend
uv run main.py
```

`uv run` automatically:
- Creates a virtual environment
- Installs dependencies from `pyproject.toml`
- Runs the script

**Method 2: Install then run**

```bash
cd backend
uv pip install -e .
python3 main.py
```

The service will start on http://localhost:8000

### 4. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Core Endpoints

- `POST /v1/tasks` - Create new task
- `GET /v1/tasks/{task_id}` - Query task (non-streaming)
- `GET /v1/tasks/{task_id}?stream=true` - Query task (streaming)
- `POST /v1/tasks/{task_id}/cancel` - Cancel task
- `POST /v1/tasks/{task_id}/assessment` - Submit assessment

### Utility Endpoints

- `GET /` - API information
- `GET /health` - Health check

## Usage Examples

### Create a Task

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Polaroid Camera",
    "brand_identity": "Nostalgia, Artistic, Instant Sharing",
    "must_have_shots": "Friends sharing photos, Camera close-up",
    "product_images": "https://example.com/polaroid.jpg",
    "video_format": "16:9",
    "max_shots": 5
  }'
```

Response:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### Query Task (Non-streaming)

```bash
curl http://localhost:8000/v1/tasks/123e4567-e89b-12d3-a456-426614174000
```

### Query Task (Streaming)

```bash
curl -N http://localhost:8000/v1/tasks/123e4567-e89b-12d3-a456-426614174000?stream=true
```

### Cancel Task

```bash
curl -X POST http://localhost:8000/v1/tasks/123e4567-e89b-12d3-a456-426614174000/cancel
```

## Development

### Run with Auto-reload

```bash
python main.py
# Uvicorn will auto-reload on file changes
```

### Run Tests

```bash
uv pip install -e ".[dev]"
pytest
```

### Code Formatting

```bash
ruff check .
ruff format .
```

## Architecture

### Task Lifecycle

```
1. Client creates task → POST /v1/tasks
2. TaskManager starts background thread
3. WorkflowExecutor runs LangGraph workflow
4. Each stage records outputs to SQLite
5. Client queries via streaming or polling
6. Task completes/fails/cancelled
```

### Database Schema

**tasks table:**
- Stores task metadata and status
- Fields: task_id, status, stage, product info, timestamps, URLs

**contents table:**
- Stores content blocks (LLM outputs, tool callings)
- Fields: id, task_id, content_type, timestamp, data_json

### Streaming Implementation

Uses Server-Sent Events (SSE):
- Real-time progress updates
- Incremental content delivery
- Automatic reconnection (browser native)
- One-way server→client communication

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY backend/ .

RUN pip install uv && uv pip install -e .

EXPOSE 8000
CMD ["python", "main.py"]
```

### Using systemd

```ini
[Unit]
Description=AD Agent API Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/ad-agent/backend
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Variables

Production checklist:
- ✅ Set all API keys in `.env`
- ✅ Configure CORS origins in `service/main.py`
- ✅ Set up database backups
- ✅ Configure logging level
- ✅ Set up monitoring (Prometheus/Grafana)

## Troubleshooting

### Port already in use

```bash
# Find process using port 8000
lsof -ti:8000
# Kill it
kill -9 $(lsof -ti:8000)
```

### Database locked

```bash
# Remove lock file
rm ad_agent.db-journal
```

### Import errors

```bash
# Reinstall dependencies
uv pip install -e . --force-reinstall
```

## Documentation

- [API Documentation](../API_zh.md) - Complete API reference
- [Service Architecture](service/ARCHITECTURE.md) - Technical details
- [Quick Start Guide](service/QUICKSTART.md) - Detailed setup guide

## Support

For issues or questions:
- Check the documentation
- Review example code in `service/test_client.py`
- Open an issue on GitHub

## License

Copyright © 2025 AD Agent. All rights reserved.

