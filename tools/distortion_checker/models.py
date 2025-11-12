"""Data models for distortion detection."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates in pixels."""
    x: int = Field(..., description="Top-left x coordinate")
    y: int = Field(..., description="Top-left y coordinate")
    w: int = Field(..., description="Width in pixels")
    h: int = Field(..., description="Height in pixels")


DistortionLabel = Literal[
    "extra_fingers",
    "extra_hands",
    "warped_hand",
    "warped_limbs",
    "elongated_limbs",
    "extra_limbs",
    "deformed_face",
]


class Distortion(BaseModel):
    """A detected distortion in the image."""
    label: DistortionLabel = Field(..., description="Type of distortion detected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    bounding_box: BoundingBox = Field(..., description="Location of distortion")
    details: str = Field(..., description="Human-readable description")


class DetectionResult(BaseModel):
    """Result of distortion detection on an image."""
    has_distortion: bool = Field(..., description="Whether any distortions were found")
    distortions: List[Distortion] = Field(default_factory=list, description="List of detected distortions")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    image_width: int = Field(..., description="Image width in pixels")
    image_height: int = Field(..., description="Image height in pixels")


class LandmarkData(BaseModel):
    """Raw landmark data from MediaPipe detectors."""
    x: float
    y: float
    z: Optional[float] = None
    visibility: Optional[float] = None


class HandLandmarks(BaseModel):
    """Hand detection landmarks."""
    landmarks: List[LandmarkData]
    handedness: str  # "Left" or "Right"
    score: float


class PoseLandmarks(BaseModel):
    """Pose detection landmarks."""
    landmarks: List[LandmarkData]
    score: float


class FaceLandmarks(BaseModel):
    """Face mesh landmarks."""
    landmarks: List[LandmarkData]
    score: float

