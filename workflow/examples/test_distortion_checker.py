#!/usr/bin/env python3
"""
Example script demonstrating the distortion checker LangChain tools.

This script shows various ways to use the distortion checker tools
in different scenarios.
"""
import sys
from pathlib import Path

# Add parent directory to path to import tools
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import (
    check_image_distortion,
    get_distortion_labels,
    get_distortion_stats,
)


def example_1_check_image():
    """Example 1: Check a single image for distortions"""
    print("=" * 60)
    print("Example 1: Check Image for Distortions")
    print("=" * 60)
    
    # Replace with your actual image path
    image_path = "path/to/your/image.jpg"
    
    print(f"\nChecking image: {image_path}\n")
    result = check_image_distortion(image_path)
    print(result)
    print()


def example_2_get_labels():
    """Example 2: Get all available distortion labels"""
    print("=" * 60)
    print("Example 2: Get Available Distortion Labels")
    print("=" * 60)
    print()
    
    labels = get_distortion_labels("")
    print(labels)
    print()


def example_3_get_stats():
    """Example 3: Get detection statistics and configuration"""
    print("=" * 60)
    print("Example 3: Get Detection Statistics")
    print("=" * 60)
    print()
    
    stats = get_distortion_stats("")
    print(stats)
    print()


def example_4_batch_check():
    """Example 4: Check multiple images"""
    print("=" * 60)
    print("Example 4: Batch Check Multiple Images")
    print("=" * 60)
    print()
    
    # Replace with your actual image paths
    image_paths = [
        "path/to/image1.jpg",
        "path/to/image2.jpg",
        "path/to/image3.jpg",
    ]
    
    for i, image_path in enumerate(image_paths, 1):
        print(f"[{i}/{len(image_paths)}] Checking: {image_path}")
        result = check_image_distortion(image_path)
        
        # Extract summary line
        first_line = result.split('\n')[0]
        print(f"  Result: {first_line}")
        print()


def example_5_with_langchain_agent():
    """Example 5: Use tools with a LangChain agent"""
    print("=" * 60)
    print("Example 5: LangChain Agent Integration")
    print("=" * 60)
    print()
    
    try:
        from langchain.agents import initialize_agent, AgentType
        from langchain_openai import ChatOpenAI
        
        # Initialize LLM
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        
        # Set up tools
        tools = [
            check_image_distortion,
            get_distortion_labels,
            get_distortion_stats,
        ]
        
        # Create agent
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
        )
        
        # Example query
        print("Agent Query: What types of distortions can you detect?\n")
        response = agent.run("What types of distortions can you detect?")
        print("\nAgent Response:")
        print(response)
        print()
        
    except ImportError as e:
        print("Note: This example requires langchain and langchain_openai packages.")
        print("Install with: pip install langchain langchain-openai")
        print(f"Error: {e}")
        print()


def example_6_error_handling():
    """Example 6: Demonstrate error handling"""
    print("=" * 60)
    print("Example 6: Error Handling")
    print("=" * 60)
    print()
    
    # Test with non-existent file
    print("Testing with non-existent file:")
    result = check_image_distortion("nonexistent_file.jpg")
    print(result)
    print()
    
    # Test with invalid path
    print("Testing with invalid path:")
    result = check_image_distortion("")
    print(result)
    print()


def example_7_base64_image():
    """Example 7: Check base64-encoded image"""
    print("=" * 60)
    print("Example 7: Check Base64-Encoded Image")
    print("=" * 60)
    print()
    
    # Example base64 string (replace with actual base64 image data)
    base64_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    print("Checking base64-encoded image (1x1 red pixel example):")
    result = check_image_distortion(base64_image)
    print(result)
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("Distortion Checker Tool Examples")
    print("=" * 60 + "\n")
    
    # Run examples
    examples = [
        ("Get Labels", example_2_get_labels),
        ("Get Stats", example_3_get_stats),
        ("Check Image", example_1_check_image),
        ("Batch Check", example_4_batch_check),
        ("Error Handling", example_6_error_handling),
        ("Base64 Image", example_7_base64_image),
        ("LangChain Agent", example_5_with_langchain_agent),
    ]
    
    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print()
    
    # You can run specific examples or all of them
    # For now, let's run the informational ones that don't require images
    print("Running examples that don't require image files:\n")
    
    example_2_get_labels()
    example_3_get_stats()
    example_6_error_handling()
    
    print("=" * 60)
    print("Examples that require image files are commented out.")
    print("To test with real images, uncomment and provide image paths.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()

