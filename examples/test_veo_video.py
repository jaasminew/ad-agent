# examples/test_veo_video.py
"""
Test script for Veo Video Generation tool functionality.

This script generates videos using Google Veo 3.1 API based on a text prompt 
and a reference image, then optionally uploads the result to Tencent Cloud COS.

Usage:
    # Use default test image and prompt
    uv run python examples/test_veo_video.py

    # Specify custom image and prompt
    uv run python examples/test_veo_video.py --image https://example.com/image.jpg --prompt "your prompt"

    # Use local image file
    uv run python examples/test_veo_video.py --image /path/to/local/image.jpg --prompt "your prompt"

    # Disable COS upload
    uv run python examples/test_veo_video.py --image https://example.com/image.jpg --prompt "your prompt" --no-cos

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

from tools.veo_video import veo_generate_video


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Veo Video Generation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default test image and prompt
  uv run python examples/test_veo_video.py

  # Custom image URL and prompt
  uv run python examples/test_veo_video.py \\
    --image https://example.com/image.jpg \\
    --prompt "Panning wide shot of a calico kitten sleeping in the sunshine"

  # Local image file
  uv run python examples/test_veo_video.py \\
    --image /path/to/photo.jpg \\
    --prompt "Slow motion zoom into the scene with cinematic lighting"

  # Disable COS upload
  uv run python examples/test_veo_video.py \\
    --image https://example.com/image.jpg \\
    --prompt "Dramatic dolly shot moving forward" \\
    --no-cos

  # Creative camera movements
  uv run python examples/test_veo_video.py \\
    --image https://example.com/forest.jpg \\
    --prompt "Slow motion dolly shot moving through a magical forest with particles of light floating in the air"
        """
    )
    
    parser.add_argument(
        "--image",
        "-i",
        type=str,
        help="Input image URL or local file path. If not specified, uses a default test image."
    )
    
    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        default="Panning wide shot of a calico kitten sleeping in the sunshine",
        help="Text prompt for video generation (default: 'Panning wide shot of a calico kitten sleeping in the sunshine')"
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
    print("🎬 Veo Video Generation Tool Test")
    print("=" * 60)
    
    # Check environment configuration
    google_configured, cos_configured = check_environment()
    
    if not google_configured:
        print("❌ Error: GOOGLE_API_KEY environment variable not found")
        print("Please set GOOGLE_API_KEY in your .env file or environment")
        print("\nExample:")
        print("  export GOOGLE_API_KEY='your-google-api-key'")
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
        print("⚠️  COS not configured - video will be saved locally only")
    
    print("\n" + "=" * 60)
    print("Generating Video")
    print("=" * 60)
    
    # Use default test image if none specified
    if args.image is None:
        input_image = "https://style-pictures-1309327302.cos.ap-guangzhou.myqcloud.com/img_38f0bc87-5c18-4ec3-93fa-bd1c4d7025b6.jpg"
    else:
        input_image = args.image
    
    # Display test parameters
    print(f"\nInput image: {input_image}")
    print(f"Prompt: {args.prompt}")
    print(f"Upload to COS: {upload_to_cos}")
    print("\nProcessing...")
    print("⚠️  Note: Video generation may take several minutes (typically 1-5 minutes)")
    print("-" * 60)
    
    try:
        # Call veo_generate_video tool
        result = veo_generate_video.invoke({
            "prompt": args.prompt,
            "image_url": input_image,
            "upload_to_cos": upload_to_cos,
        })
        
        print("\n" + "-" * 60)
        print("✓ Generation completed!")
        print("=" * 60)
        print("\nResult:")
        print(result)
        print("\n" + "=" * 60)
        
        # Additional info if it's a local file
        if result.startswith("/") and os.path.exists(result):
            import subprocess
            file_size = os.path.getsize(result) / (1024 * 1024)  # MB
            print(f"\n📹 Video saved locally")
            print(f"   Path: {result}")
            print(f"   Size: {file_size:.2f} MB")
            print(f"\n💡 Tip: You can open it with:")
            print(f"   open {result}")
        
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
