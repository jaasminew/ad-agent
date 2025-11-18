# Quick Start - AD Agent Backend Service

Step-by-step guide to get the service running.

## Prerequisites

- Python 3.10+
- `uv` package manager (recommended) or `pip`
- API keys for required services (Anthropic, MidJourney, etc.)

## Installation

### Step 1: Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or using pip:
```bash
pip install uv
```

### Step 2: Navigate to backend directory

```bash
cd backend
```

### Step 3: Install dependencies

```bash
uv pip install -e .
```

This will install:
- FastAPI and uvicorn (API server)
- LangChain and LangGraph (AI agents)
- All required dependencies

### Step 4: Configure environment variables

Copy the example env file:
```bash
cp workflow/.env.example .env
```

Edit `.env` and add your API keys:
```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# MidJourney
MIDJOURNEY_API_URL=https://...
MIDJOURNEY_API_KEY=...

# Other services
# ... add as needed
```

## Running the Service

### Start the server

```bash
python main.py
```

You should see:
```
================================================================================
Starting AD Agent API Service
================================================================================
✓ Database initialized: ad_agent.db
✓ TaskManager initialized
✓ Service started successfully
================================================================================
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

### Access the API

Open your browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Info**: http://localhost:8000/

## Test the Service

### Option 1: Using the Web UI (Swagger)

1. Go to http://localhost:8000/docs
2. Click on `POST /v1/tasks`
3. Click "Try it out"
4. Fill in the request body:
   ```json
   {
     "product_name": "Test Product",
     "brand_identity": "Modern, Innovative",
     "must_have_shots": "Product showcase",
     "product_images": "https://example.com/image.jpg",
     "video_format": "16:9",
     "max_shots": 3
   }
   ```
5. Click "Execute"
6. Copy the `task_id` from the response

### Option 2: Using curl

```bash
# Create task
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Test Product",
    "brand_identity": "Modern, Innovative",
    "must_have_shots": "Product showcase",
    "product_images": "https://example.com/image.jpg",
    "video_format": "16:9",
    "max_shots": 3
  }'

# Query task (replace with your task_id)
curl http://localhost:8000/v1/tasks/YOUR_TASK_ID

# Stream updates (real-time)
curl -N http://localhost:8000/v1/tasks/YOUR_TASK_ID?stream=true
```

### Option 3: Using Python test client

```bash
cd service
python test_client.py streaming
```

## Verify Everything is Working

### Check health endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy"
}
```

### Check database

The service creates a SQLite database:
```bash
ls -lh ad_agent.db
```

### View logs

Logs will appear in the terminal where you ran `python main.py`.

## Next Steps

### 1. Explore the API

- Try creating different tasks
- Test the streaming endpoint
- Experiment with task cancellation

### 2. Integrate with Frontend

Use the test client as a reference:
```python
from service.test_client import ADAgentClient

client = ADAgentClient()
task_id = client.create_task(
    product_name="My Product",
    brand_identity="Cool Brand",
    # ...
)

for event in client.stream_task(task_id):
    print(event)
```

### 3. Customize Configuration

Edit `service/main.py` to:
- Change CORS settings
- Adjust ports
- Add authentication
- Configure logging

## Troubleshooting

### Service won't start

**Error: Port 8000 already in use**
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use a different port in main.py
```

**Error: Module not found**
```bash
# Reinstall dependencies
uv pip install -e . --force-reinstall
```

### Tasks not executing

**Check API keys**
```bash
cat .env | grep API_KEY
```

**Check logs**
Look for error messages in the terminal output.

**Check database**
```bash
sqlite3 ad_agent.db "SELECT * FROM tasks;"
```

### Streaming not working

**Use correct headers**
```bash
curl -N -H "Accept: text/event-stream" \
  http://localhost:8000/v1/tasks/YOUR_TASK_ID?stream=true
```

**Check browser support**
Modern browsers support SSE natively via `EventSource`.

## Common Issues

### Issue: Import errors in workflow_executor

**Cause**: Python path not set correctly

**Solution**: The service automatically adds paths in `main.py`. If issues persist:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

### Issue: Database locked

**Cause**: Multiple processes accessing the database

**Solution**:
```bash
# Stop all processes
pkill -f "python main.py"

# Remove lock
rm -f ad_agent.db-journal

# Restart
python main.py
```

### Issue: Slow response times

**Cause**: LLM/tool calls take time

**Solution**: Use streaming to see progress in real-time:
```bash
curl -N http://localhost:8000/v1/tasks/YOUR_TASK_ID?stream=true
```

## Development Tips

### Auto-reload on code changes

The service runs with `reload=True` by default, so code changes trigger automatic restart.

### View database contents

```bash
sqlite3 ad_agent.db

# List tables
.tables

# Query tasks
SELECT task_id, status, stage FROM tasks;

# Query contents
SELECT task_id, content_type, timestamp FROM contents LIMIT 10;

# Exit
.quit
```

### Debug mode

Add to `main.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Production Checklist

Before deploying to production:

- [ ] Set `reload=False` in `main.py`
- [ ] Configure CORS with specific origins
- [ ] Use environment-specific `.env` files
- [ ] Set up database backups
- [ ] Configure reverse proxy (nginx)
- [ ] Set up SSL/TLS certificates
- [ ] Configure monitoring and alerts
- [ ] Set up log rotation
- [ ] Document API keys management
- [ ] Test error handling and edge cases

## Getting Help

- Read the full documentation: [README.md](README.md)
- Check API reference: [../API_zh.md](../API_zh.md)
- Review architecture: [service/ARCHITECTURE.md](service/ARCHITECTURE.md)
- Run example code: `service/test_client.py`

Happy coding! 🚀

