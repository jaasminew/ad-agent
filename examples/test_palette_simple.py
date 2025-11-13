"""
Simple standalone test for palette extractor.
This version doesn't require LangChain dependencies.
"""
import sys
import os
import logging
import requests
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def rgb_to_hex(rgb):
    """Convert RGB tuple to hex color code"""
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"

def test_palette_extractor_simple():
    """Test palette extraction with ColorThief directly"""
    try:
        from colorthief import ColorThief
    except ImportError:
        print("❌ ColorThief not installed. Run: pip install colorthief")
        return
    
    # Test image URLs
    test_images = [
        {
            "name": "Mountain Landscape",
            "url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4"
        },
        {
            "name": "Architecture",
            "url": "https://images.unsplash.com/photo-1541963463532-d68292c34b19"
        },
        {
            "name": "Sunset",
            "url": "https://images.unsplash.com/photo-1506157786151-b8491531f063"
        }
    ]
    
    print("\n" + "=" * 80)
    print("🎨 Palette Extractor Test - Simple Version")
    print("=" * 80)
    print()
    
    for i, test_image in enumerate(test_images, 1):
        print(f"\n📸 Test {i}: {test_image['name']}")
        print(f"URL: {test_image['url']}")
        print("-" * 80)
        
        try:
            # Fetch image
            logger.info(f"Fetching image...")
            response = requests.get(test_image['url'], timeout=30)
            response.raise_for_status()
            
            # Extract palette
            logger.info(f"Extracting colors...")
            image_file = BytesIO(response.content)
            color_thief = ColorThief(image_file)
            palette = color_thief.get_palette(color_count=3, quality=10)
            
            # Display results
            print(f"\n✅ Extracted {len(palette)} dominant colors:\n")
            for j, (r, g, b) in enumerate(palette, 1):
                hex_code = rgb_to_hex((r, g, b))
                # Create a simple text representation of the color
                print(f"Color {j}: RGB({r:3d}, {g:3d}, {b:3d}) - Hex: {hex_code}")
            
            print()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching image: {e}")
        except Exception as e:
            print(f"❌ Error extracting palette: {e}")
    
    print("\n" + "=" * 80)
    print("✅ All tests completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    test_palette_extractor_simple()

