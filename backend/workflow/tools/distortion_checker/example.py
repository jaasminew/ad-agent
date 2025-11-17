#!/usr/bin/env python3
"""
Simple example of using distortion checker tools.

Usage (from project root):
    uv run python workflow/tools/distortion_checker/example.py [image_path]
    
Example:
    uv run python workflow/tools/distortion_checker/example.py /path/to/image.jpg
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from workflow.tools import check_image_distortion, get_distortion_labels


def main():
    # Example 1: Get available labels
    print("Available Distortion Types:")
    print("=" * 60)
    print(get_distortion_labels(""))
    print()
    
    # Example 2: Check an image
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"\nChecking image: {image_path}")
        print("=" * 60)
        print("Loading MediaPipe models (first run may take ~30 seconds)...")
        
        result = check_image_distortion(image_path)
        print(result)
    else:
        print("\nUsage: python example.py <image_path>")
        print("Example: python example.py /path/to/image.jpg")


if __name__ == "__main__":
    main()

