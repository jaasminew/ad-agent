# Script Generation Agent

A LangChain ReAct Agent for generating creative advertising scripts with shot lists.

## Overview

This agent uses LLM reasoning combined with tool calling to generate high-quality advertising shot lists based on product information and brand identity. It can optionally conduct market research and stores intermediate results in memory for better context management.

## Features

- **ReAct Agent Architecture**: Uses LangChain's ReAct pattern for step-by-step reasoning
- **Tool Integration**: Leverages memory and web search tools
- **Market Research**: Optional web search for industry insights and inspiration
- **Memory Management**: Stores and recalls information throughout the generation process
- **Flexible Configuration**: Supports various LLMs (GPT-4, Claude, etc.)

## Installation

Ensure you have the required dependencies installed:

```bash
# Install from project root
uv sync
```

## Usage

### Basic Example

```python
from langchain_openai import ChatOpenAI
from agent.script_gen_agent import ScriptGenerationAgent, ScriptConfig

# Initialize LLM
llm = ChatOpenAI(model="gpt-4", temperature=0.7)

# Create agent
agent = ScriptGenerationAgent(llm=llm, verbose=True)

# Configure script generation
script_config = ScriptConfig(
    product_name="Smart Watch X1",
    brand_identity="Young, tech-savvy, fitness-focused",
    must_have_shots="product closeup, workout scene, user smiling",
    num_shots=5,
)

# Generate script
result = agent.generate_script(script_config)

# Access results
for shot in result.shots:
    print(f"{shot.shot_number}. {shot.description}")
```

### Running the Example

```bash
# Set required API keys
export OPENAI_API_KEY="your-openai-key"
export TAVILY_API_KEY="your-tavily-key"  # Optional, for web search

# Run example
python -m agent.script_gen_agent.example
```

## Configuration

### ScriptConfig Parameters

- **product_name** (str): Product name
- **brand_identity** (str): Brand positioning/identity
- **must_have_shots** (str): Required shots (comma-separated)
- **num_shots** (int): Number of shots to generate (default: 3)

### Agent Parameters

- **llm** (BaseChatModel): Language model to use (required)
- **verbose** (bool): Enable detailed logging (default: True)
- **max_iterations** (int): Maximum agent iterations (default: 30)
- **max_execution_time** (float, optional): Timeout in seconds

## Workflow

The agent follows a structured workflow:

1. **Understand Requirements**: Analyze product info and brand identity
2. **Market Research**: Optionally search for inspiration and best practices
3. **Generate Shot Ideas**: Create creative, brand-aligned shots
4. **Optimize and Refine**: Review and improve shot descriptions
5. **Store Results**: Save generated shots to memory

## Output

### ScriptResult

```python
{
    "shots": [
        {"shot_number": 1, "description": "..."},
        {"shot_number": 2, "description": "..."},
        ...
    ],
    "total_shots": 5,
    "research_notes": ["Research: ...", ...]
}
```

## Tools Used

- **remember**: Store information in memory
- **recall**: Retrieve stored information
- **web_search**: Search the web for context and inspiration

## Supported LLMs

The agent supports any LangChain-compatible chat model:

```python
# OpenAI
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4", temperature=0.7)

# Anthropic
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.7)
```

## Best Practices

1. **Clear Brand Identity**: Provide specific brand positioning for better results
2. **Specific Must-Have Shots**: List concrete required shots, not abstract concepts
3. **Appropriate Shot Count**: 3-7 shots work best for most ad campaigns
4. **Enable Web Search**: Set TAVILY_API_KEY for research-backed results
5. **Review Output**: Always review generated shots before production

## Notes

- The agent uses a structured ReAct loop for reasoning
- Web search is optional but recommended for better creativity
- Memory tools help maintain consistency across shots
- Generated shots are numbered and ready for downstream processing

