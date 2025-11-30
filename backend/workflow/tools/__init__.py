# tools/__init__.py
# from .memory import remember, recall  # Deprecated: use create_memory_tools from memory.py instead
from .web_search import web_search
from .midjourney import midjourney_imagine, midjourney_upscale
from .pixelhub import list_tags, search_images_by_tags
from .nanobanana import nanobanana_generate
from .veo_video import veo_generate_video
from .palette_extractor import extract_color_palette

# Distortion checker tools (optional, requires mediapipe)
try:
    from .distortion_checker import (
        check_image_distortion,
        get_distortion_labels,
        get_distortion_stats,
    )
    DISTORTION_CHECKER_AVAILABLE = True
except ImportError:
    DISTORTION_CHECKER_AVAILABLE = False
    check_image_distortion = None
    get_distortion_labels = None
    get_distortion_stats = None

# COS uploader (optional)
try:
    from .cos_uploader import COSUploader, get_cos_uploader, is_cos_available, COS_AVAILABLE
except ImportError:
    COSUploader = None
    get_cos_uploader = None
    is_cos_available = None
    COS_AVAILABLE = False

__all__ = [
    "web_search",
    # "remember",  # Removed from public API
    # "recall",    # Removed from public API
    "midjourney_imagine",
    "midjourney_upscale",
    "list_tags",
    "search_images_by_tags",
    "nanobanana_generate",
    "veo_generate_video",
    "extract_color_palette",
    "COSUploader",
    "get_cos_uploader",
    "is_cos_available",
    "COS_AVAILABLE",
    "check_image_distortion",
    "get_distortion_labels",
    "get_distortion_stats",
    "DISTORTION_CHECKER_AVAILABLE",
]
