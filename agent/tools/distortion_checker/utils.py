"""Utility functions for image loading and bounding box calculations."""

import base64
import io
from typing import Tuple, Union, List

import numpy as np
import requests
from PIL import Image


REMOTE_DOWNLOAD_TIMEOUT = 30  # seconds


def _image_from_bytes(image_bytes: bytes) -> Tuple[np.ndarray, int, int]:
    """Convert raw image bytes to numpy array plus dimensions."""
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")
    width, height = img.size
    return np.array(img), width, height


def load_image(image_input: Union[str, bytes]) -> Tuple[np.ndarray, int, int]:
    """
    Load an image from various input formats.
    
    Args:
        image_input: Can be:
            - File path (str)
            - Base64 string with data URI prefix (str)
            - Base64 string with 'base64:' prefix (str)
            - Raw image bytes (bytes)
    
    Returns:
        Tuple of (image_array, width, height)
        Image array is in RGB format ready for MediaPipe
    """
    # If bytes, load directly
    if isinstance(image_input, bytes):
        return _image_from_bytes(image_input)
    
    # If string, check if it's base64 or file path
    if isinstance(image_input, str):
        # Normalize whitespace or stray quotes that may come from agent formatting
        normalized_input = image_input.strip()
        if normalized_input and normalized_input[0] in {"'", '"'}:
            normalized_input = normalized_input[1:]
        if normalized_input and normalized_input[-1] in {"'", '"'}:
            normalized_input = normalized_input[:-1]
        normalized_input = normalized_input.strip()
        image_input = normalized_input
        
        # Check for remote URL
        if image_input.startswith(("http://", "https://")):
            try:
                response = requests.get(image_input, timeout=REMOTE_DOWNLOAD_TIMEOUT)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise ValueError(
                    f"Failed to download image from URL '{image_input}': {exc}"
                ) from exc
            return _image_from_bytes(response.content)

        # Check for data URI format
        if image_input.startswith("data:"):
            # Format: data:image/png;base64,<base64_data>
            header, b64_data = image_input.split(",", 1)
            image_bytes = base64.b64decode(b64_data)
            return _image_from_bytes(image_bytes)
        
        # Check for base64: prefix
        if image_input.startswith("base64:"):
            b64_data = image_input[7:]  # Remove 'base64:' prefix
            image_bytes = base64.b64decode(b64_data)
            return _image_from_bytes(image_bytes)
        
        # Otherwise treat as file path
        img = Image.open(image_input)
        img = img.convert("RGB")
        width, height = img.size
        return np.array(img), width, height
    
    raise ValueError(f"Unsupported image input type: {type(image_input)}")


def calculate_bounding_box(
    landmarks: List[Tuple[float, float]],
    image_width: int,
    image_height: int,
    padding: float = 0.15
) -> dict:
    """
    Calculate bounding box from normalized landmarks.
    
    Args:
        landmarks: List of (x, y) tuples in normalized coordinates [0, 1]
        image_width: Image width in pixels
        image_height: Image height in pixels
        padding: Additional padding around the box (as fraction of box size)
    
    Returns:
        Dictionary with keys: x, y, w, h (all in pixels)
    """
    if not landmarks:
        return {"x": 0, "y": 0, "w": 0, "h": 0}
    
    # Find min/max coordinates
    x_coords = [lm[0] for lm in landmarks]
    y_coords = [lm[1] for lm in landmarks]
    
    min_x = min(x_coords)
    max_x = max(x_coords)
    min_y = min(y_coords)
    max_y = max(y_coords)
    
    # Calculate dimensions
    width = max_x - min_x
    height = max_y - min_y
    
    # Add padding
    pad_x = width * padding
    pad_y = height * padding
    
    min_x = max(0, min_x - pad_x)
    max_x = min(1, max_x + pad_x)
    min_y = max(0, min_y - pad_y)
    max_y = min(1, max_y + pad_y)
    
    # Convert to pixel coordinates
    x_px = int(min_x * image_width)
    y_px = int(min_y * image_height)
    w_px = int((max_x - min_x) * image_width)
    h_px = int((max_y - min_y) * image_height)
    
    return {"x": x_px, "y": y_px, "w": w_px, "h": h_px}


def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def calculate_angle(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
    """
    Calculate angle at p2 formed by p1-p2-p3 in degrees.
    
    Args:
        p1: First point
        p2: Vertex point
        p3: Third point
    
    Returns:
        Angle in degrees [0, 180]
    """
    # Vectors
    v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
    v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    
    # Calculate angle
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = np.arccos(cos_angle)
    
    return np.degrees(angle)

