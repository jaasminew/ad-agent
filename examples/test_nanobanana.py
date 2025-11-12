# examples/test_nanobanana.py
"""
Test script for Nanobanana tool functionality.

This script generates images using Google Gemini's image generation API
based on a text prompt and a reference image, then optionally uploads
the result to Tencent Cloud COS.

Usage:
    # Use default test image and prompt
    python examples/test_nanobanana.py

    # Specify custom image and prompt
    python examples/test_nanobanana.py --image https://example.com/image.jpg --prompt "your prompt"

    # Use local image file
    python examples/test_nanobanana.py --image /path/to/local/image.jpg --prompt "your prompt"

    # Disable COS upload
    python examples/test_nanobanana.py --image https://example.com/image.jpg --prompt "your prompt" --no-cos

Environment Variables Required:
    GOOGLE_API_KEY: Your Google Gemini API key (required)
    COS_SECRET_ID: Tencent Cloud COS Secret ID (optional, for upload)
    COS_SECRET_KEY: Tencent Cloud COS Secret Key (optional, for upload)
    COS_REGION: COS region (optional, for upload)
    COS_BUCKET: COS bucket name (optional, for upload)
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.nanobanana import nanobanana_generate


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Nanobanana image generation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default test image and prompt
  python examples/test_nanobanana.py

  # Custom image URL and prompt
  python examples/test_nanobanana.py \\
    --image https://example.com/image.jpg \\
    --prompt "transform this image into cyberpunk style"

  # Local image file
  python examples/test_nanobanana.py \\
    --image /path/to/photo.jpg \\
    --prompt "add a rainbow in the background"

  # Disable COS upload
  python examples/test_nanobanana.py \\
    --image https://example.com/image.jpg \\
    --prompt "make it black and white" \\
    --no-cos
        """
    )
    
    parser.add_argument(
        "--image",
        "-i",
        type=str,
        default="https://style-pictures-1309327302.cos.ap-guangzhou.myqcloud.com/img_38f0bc87-5c18-4ec3-93fa-bd1c4d7025b6.jpg",
        help="Input image URL or local file path (default: test image)"
    )
    
    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        default="Change the phone to Apple",
        help="Text prompt for image generation (default: 'Change the phone to Apple')"
    )
    
    parser.add_argument(
        "--no-cos",
        action="store_true",
        help="Disable COS upload (save locally only)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def check_environment():
    """
    Check if required environment variables are configured.
    
    Returns:
        tuple: (google_api_configured, cos_configured)
    """
    # Check Google API key (required)
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    google_configured = bool(google_api_key)
    
    # Check COS configuration (optional)
    cos_configured = all([
        os.environ.get("COS_SECRET_ID"),
        os.environ.get("COS_SECRET_KEY"),
        os.environ.get("COS_REGION"),
        os.environ.get("COS_BUCKET"),
    ])
    
    return google_configured, cos_configured


def main():
    """Main function."""
    args = parse_args()
    
    print("=" * 60)
    print("🍌 Nanobanana Tool Test")
    print("=" * 60)
    
    # Check environment configuration
    google_configured, cos_configured = check_environment()
    
    if not google_configured:
        print("❌ Error: GOOGLE_API_KEY environment variable not found")
        print("Please set GOOGLE_API_KEY in your .env file")
        return 1
    
    if args.verbose:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        print(f"✓ Google API Key: {google_api_key[:10]}...")
    else:
        print("✓ Google API Key configured")
    
    # Determine if COS upload should be enabled
    upload_to_cos = not args.no_cos and cos_configured
    
    if cos_configured:
        if args.verbose:
            print(f"✓ COS configured")
            print(f"  Region: {os.environ.get('COS_REGION')}")
            print(f"  Bucket: {os.environ.get('COS_BUCKET')}")
        else:
            print("✓ COS configured")
        
        if args.no_cos:
            print("  (COS upload disabled by --no-cos flag)")
    else:
        print("⚠️  COS not configured - image will be saved locally only")
    
    print("\n" + "=" * 60)
    print("Generating Image")
    print("=" * 60)
    
    # Display test parameters
    print(f"\nInput image: {args.image}")
    print(f"Prompt: {args.prompt}")
    print(f"Upload to COS: {upload_to_cos}")
    print("\nProcessing...")
    print("-" * 60)
    
    try:
        # Call nanobanana_generate tool
        result = nanobanana_generate.invoke({
            "prompt": args.prompt,
            "input_image_path": args.image,
            "upload_to_cos": upload_to_cos,
        })
        
        print("\n" + "-" * 60)
        print("✓ Generation completed!")
        print("=" * 60)
        print("\nResult:")
        print(result)
        print("\n" + "=" * 60)
        
        return 0
        
    except Exception as e:
        print("\n" + "-" * 60)
        print(f"❌ Error: {e}")
        print("=" * 60)
        
        if args.verbose:
            import traceback
            print("\nDetailed error information:")
            traceback.print_exc()
        
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

