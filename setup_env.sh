#!/bin/bash
# Quick script to set up environment variables for testing

echo "=================================="
echo "  Environment Setup Helper"
echo "=================================="
echo ""
echo "Please enter your API keys:"
echo ""

# OpenAI
read -p "OpenAI API Key: " OPENAI_KEY
export OPENAI_API_KEY="$OPENAI_KEY"
echo "✓ OPENAI_API_KEY set"

# PixelHub
read -p "PixelHub API URL: " PIXELHUB_URL
export PIXELHUB_API_URL="$PIXELHUB_URL"
echo "✓ PIXELHUB_API_URL set"

# MidJourney
read -p "MidJourney Proxy URL: " MIDJOURNEY_URL
export MIDJOURNEY_PROXY_BASE_URL="$MIDJOURNEY_URL"
echo "✓ MIDJOURNEY_PROXY_BASE_URL set"

# Google
read -p "Google API Key: " GOOGLE_KEY
export GOOGLE_API_KEY="$GOOGLE_KEY"
echo "✓ GOOGLE_API_KEY set"

echo ""
echo "=================================="
echo "✅ All environment variables set!"
echo "=================================="
echo ""
echo "You can now run:"
echo "  python3 storyboard_gen_agent/quick_test.py"
echo "  python3 example.py"
echo ""
echo "Note: These variables are only set for this terminal session."
echo "To make them permanent, add them to your .env file or ~/.bashrc"

