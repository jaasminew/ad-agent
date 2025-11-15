# tools/__init__.py
from .web_search import web_search
from .memory import remember, recall
from .midjourney import midjourney_imagine, midjourney_upscale
from .pixelhub import list_tags, search_images_by_tags
from .nanobanana import nanobanana_generate
from .veo_video import veo_generate_video

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

__all__ = [
    "web_search",
    "remember",
    "recall",
    "midjourney_imagine",
    "midjourney_upscale",
    "list_tags",
    "search_images_by_tags",
    "nanobanana_generate",
    "veo_generate_video",
    "check_image_distortion",
    "get_distortion_labels",
    "get_distortion_stats",
    "DISTORTION_CHECKER_AVAILABLE",
]

