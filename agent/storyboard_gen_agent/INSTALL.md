# Installation Guide

## Prerequisites

This project uses `uv` for dependency management. Install it if you haven't:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Install Dependencies

From the project root:

```bash
cd /Users/lianxunw/Desktop/ad-agent
uv sync
```

This will install all dependencies defined in `pyproject.toml`.

## Verify Installation

```bash
# Activate the virtual environment (if using uv venv)
source .venv/bin/activate

# Test imports
python -c "from storyboard_gen_agent import StoryboardAgent; print('✓ Installation successful')"
```

## Environment Variables

Create a `.env` file in the project root:

```bash
# PixelHub API
PIXELHUB_API_URL=https://your-pixelhub-api.com

# MidJourney Proxy
MIDJOURNEY_PROXY_BASE_URL=https://your-midjourney-proxy.com

# Google Gemini (for Nanobanana)
GOOGLE_API_KEY=your-google-api-key

# OpenAI (for the agent)
OPENAI_API_KEY=your-openai-api-key

# Optional: Anthropic Claude (alternative LLM)
# ANTHROPIC_API_KEY=your-anthropic-api-key

# Optional: Tencent COS (for image upload)
# COS_SECRET_ID=your-cos-secret-id
# COS_SECRET_KEY=your-cos-secret-key
# COS_REGION=your-cos-region
# COS_BUCKET=your-cos-bucket
```

## Quick Test

```bash
cd /Users/lianxunw/Desktop/ad-agent
python storyboard_gen_agent/example.py
```

Note: Make sure all environment variables are set before running the example.

