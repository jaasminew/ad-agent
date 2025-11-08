# LangGraph ReAct Agent - Ad Script Generator

Automatically generate and optimize advertising scripts using LangGraph and ReAct Agent.

## Features

- 🤖 **Three-stage Workflow**: Write → Critique → ReAct Agent Improvement
- 🔍 **Automatic Web Search**: Forces use of web_search to gather real product information
- 📝 **Detailed Logging**: Complete reasoning process (Thought/Action/Observation) visible
- 🛠️ **Three Tools**: web_search, remember, recall

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure API Keys

Create a `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Or set directly in command line:

```bash
export OPENAI_API_KEY="your_key"
export TAVILY_API_KEY="your_key"
```

### 3. Run

```bash
uv run python main.py
```

Save logs:

```bash
uv run python main.py 2>&1 | tee output.log
```

## Workflow

```
1. Writer Node
   ↓ Generate draft (5 scenes)
   
2. Critic Node  
   ↓ Evaluate script, point out what needs research
   
3. ReAct Agent Node
   ↓ Use web_search to gather information
   ↓ Improve script based on real data
   
4. Output final script
```

## Log Output

The program displays the complete execution process:

```
============================================================
Starting LangGraph ReAct Agent
============================================================

📝 Step 1: Writer Node - Generate Draft
Product: Polaroid-style Instant Camera
Theme: Golden-hour beach vacation
✓ Draft generated

🔍 Step 2: Critic Node - Evaluate Script
Critique:
{
  "issues": [...],
  "needs_research": "Search for camera specs and photography trends"
}

🤖 Step 3: ReAct Agent - Iterative Improvement
⚠️  Note: Agent should use web_search tool first

> Entering new AgentExecutor chain...
Thought: Need to search for product information
Action: web_search
Action Input: Polaroid camera specifications

🔍 [web_search] Called - Query: 'Polaroid camera specifications'
✓ [web_search] Returned 5 results

Observation: [Search results...]

Thought: Now I can improve the script
Final Answer: {improved script}
```

## Check Tool Usage

See if web_search was used:

```bash
# Count calls
grep -c "\[web_search\]" output.log

# View details
grep "\[web_search\]" output.log
```

## Customization

Modify the test case in `main.py`:

```python
if __name__ == "__main__":
    init = {
        "product": "Your Product Name",
        "theme": "Your Theme"
    }
    out = app.invoke(init)
```

## Project Structure

```
.
├── pyproject.toml           # Project configuration
├── main.py   # Main program
├── tools.py                 # Tool definitions
└── README.md               # This document
```

## Dependencies

- Python >= 3.13
- langchain >= 0.3.0
- langchain-openai >= 0.3.0
- langgraph >= 0.2.0
- tavily-python >= 0.5.0
- python-dotenv >= 1.0.0

## Get API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Tavily**: https://tavily.com/

## Prompt Optimization

The project has optimized prompts to **force** use of web_search:

1. **Critic Prompt**: Explicitly identifies what needs research (`needs_research` field)
2. **ReAct Prompt**: Requires web_search to gather information first
3. **Input Question**: Explicitly commands "Start by searching for information!"

This ensures the Agent improves scripts based on real data rather than imagination alone.

## Troubleshooting

### Issue: Agent doesn't use web_search

Check logs for `[web_search]` markers. If missing:
1. Confirm prompt contains "MUST use web_search"
2. Check if Critic generated `needs_research` field
3. Review Agent's reasoning in verbose output

### Issue: Output parsing error

Already added `handle_parsing_errors=True`, Agent will automatically retry.

## License

MIT
