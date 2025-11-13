#!/usr/bin/env python3
"""Quick test script for storyboard agent - checks everything step by step."""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def print_section(title):
    """Print a section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def check_environment():
    """Check if environment variables are set."""
    print_section("1. ENVIRONMENT VARIABLES CHECK")
    
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API (for agent - uses GPT-4o)",
        "PIXELHUB_API_URL": "PixelHub API (for reference images)",
        "MIDJOURNEY_PROXY_BASE_URL": "MidJourney Proxy (for image generation)",
        "GOOGLE_API_KEY": "Google Gemini API (for Nanobanana)",
    }
    
    optional_vars = {
        "ANTHROPIC_API_KEY": "Anthropic Claude (alternative LLM - not primary)",
        "COS_SECRET_ID": "Tencent COS (for uploads)",
        "COS_SECRET_KEY": "Tencent COS (for uploads)",
    }
    
    all_set = True
    
    print("\nRequired:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"  ✓ {var}: {masked}")
        else:
            print(f"  ✗ {var}: NOT SET ({desc})")
            all_set = False
    
    print("\nOptional:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"  ✓ {var}: {masked}")
        else:
            print(f"  - {var}: not set ({desc})")
    
    return all_set

def check_dependencies():
    """Check if required packages are installed."""
    print_section("2. DEPENDENCIES CHECK")
    
    required = [
        ("langchain", "LangChain framework"),
        ("langchain_core", "LangChain core"),
        ("pydantic", "Data validation"),
        ("requests", "HTTP requests"),
    ]
    
    optional = [
        ("langchain_openai", "OpenAI LLM support"),
        ("langchain_anthropic", "Anthropic LLM support"),
        ("PIL", "Image processing (Pillow)"),
        ("colorthief", "Color palette extraction"),
        ("google.genai", "Google Gemini (Nanobanana)"),
    ]
    
    all_installed = True
    
    print("\nRequired:")
    for module, desc in required:
        try:
            __import__(module)
            print(f"  ✓ {module}: installed ({desc})")
        except ImportError:
            print(f"  ✗ {module}: MISSING ({desc})")
            all_installed = False
    
    print("\nOptional (but recommended):")
    llm_available = False
    for module, desc in optional:
        try:
            __import__(module)
            print(f"  ✓ {module}: installed ({desc})")
            if "langchain_" in module:
                llm_available = True
        except ImportError:
            print(f"  - {module}: not installed ({desc})")
    
    if not llm_available:
        print("\n  ⚠️  WARNING: No LLM provider installed!")
        print("     Install one of: langchain-openai, langchain-anthropic")
        all_installed = False
    
    return all_installed

def check_imports():
    """Check if storyboard agent imports work."""
    print_section("3. STORYBOARD AGENT IMPORTS")
    
    try:
        from storyboard_gen_agent import (
            StoryboardAgent,
            Beat,
            EpisodeConfig,
            ProductConfig,
            BeatResult,
            EpisodeResult,
        )
        print("\n  ✓ All imports successful!")
        print(f"    - StoryboardAgent: {StoryboardAgent.__name__}")
        print(f"    - Beat: {Beat.__name__}")
        print(f"    - EpisodeConfig: {EpisodeConfig.__name__}")
        print(f"    - ProductConfig: {ProductConfig.__name__}")
        return True
    except Exception as e:
        print(f"\n  ✗ Import failed: {e}")
        return False

def check_tools():
    """Check if tools are loadable."""
    print_section("4. TOOLS CHECK")
    
    try:
        from storyboard_gen_agent.tools import get_storyboard_tools, get_tool_names
        
        # This will try to import all tools
        tools = get_storyboard_tools()
        tool_names = get_tool_names()
        
        print(f"\n  ✓ Successfully loaded {len(tools)} tools:")
        for i, name in enumerate(tool_names, 1):
            print(f"    {i}. {name}")
        
        return True
    except Exception as e:
        print(f"\n  ✗ Failed to load tools: {e}")
        print(f"\n  This might be due to missing API credentials or tool dependencies.")
        return False

def test_data_models():
    """Test creating data models."""
    print_section("5. DATA MODELS TEST")
    
    try:
        from storyboard_gen_agent import Beat, ProductConfig, EpisodeConfig
        
        # Create test models
        beat = Beat(
            beat=1,
            heading="Test Scene",
            shot_description="A person in a bright room",
            action="Sits down and opens laptop"
        )
        print(f"\n  ✓ Beat created: #{beat.beat} '{beat.heading}'")
        
        product = ProductConfig(
            product_image_url="https://example.com/product.jpg",
            target_object="laptop"
        )
        print(f"  ✓ Product config created: target='{product.target_object}'")
        
        episode = EpisodeConfig(
            title="Test Episode",
            product_config=product,
            beats=[beat]
        )
        print(f"  ✓ Episode config created: '{episode.title}' with {len(episode.beats)} beat(s)")
        
        return True
    except Exception as e:
        print(f"\n  ✗ Data model test failed: {e}")
        return False

def test_utilities():
    """Test utility functions."""
    print_section("6. UTILITY FUNCTIONS TEST")
    
    try:
        from storyboard_gen_agent.utils import (
            normalize_beat,
            format_palette_for_prompt,
            build_midjourney_prompt,
        )
        from storyboard_gen_agent import Beat
        
        # Test normalize_beat
        beat = Beat(
            beat=1,
            heading="Coffee Shop",
            shot_description="Cozy morning scene",
            action="Person smiles at laptop"
        )
        shot_text = normalize_beat(beat)
        print(f"\n  ✓ normalize_beat: '{shot_text[:60]}...'")
        
        # Test format_palette
        palette = ["#FF5733", "#3366FF", "#28A745"]
        formatted = format_palette_for_prompt(palette)
        print(f"  ✓ format_palette: '{formatted}'")
        
        # Test build_midjourney_prompt
        prompt = build_midjourney_prompt(
            reference_image_url="https://example.com/ref.jpg",
            shot_text="Friends in a park",
            palette=palette
        )
        print(f"  ✓ build_midjourney_prompt: '{prompt[:70]}...'")
        
        return True
    except Exception as e:
        print(f"\n  ✗ Utility test failed: {e}")
        return False

def main():
    """Run all checks."""
    print("\n" + "█"*70)
    print("  STORYBOARD GENERATION AGENT - QUICK TEST")
    print("█"*70)
    
    results = []
    
    # Run all checks
    results.append(("Environment Variables", check_environment()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Agent Imports", check_imports()))
    results.append(("Tools Loading", check_tools()))
    results.append(("Data Models", test_data_models()))
    results.append(("Utility Functions", test_utilities()))
    
    # Summary
    print_section("SUMMARY")
    
    print()
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\n  Results: {passed_count}/{total_count} checks passed")
    
    if passed_count == total_count:
        print("\n  ✅ All checks passed! Agent is ready to use.")
        print("\n  Next steps:")
        print("    1. Run: python3 storyboard_gen_agent/test_palette.py")
        print("    2. Run: python3 storyboard_gen_agent/example.py")
    else:
        print("\n  ❌ Some checks failed. Please fix the issues above.")
        print("\n  Common fixes:")
        print("    - Install missing packages: pip install langchain langchain-openai")
        print("    - Set environment variables in .env file or export them")
        print("    - See TESTING_GUIDE.md for detailed instructions")
    
    print("\n" + "█"*70)
    
    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())

