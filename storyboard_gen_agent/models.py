"""Data models for storyboard generation."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Beat(BaseModel):
    """A single beat/scene from the script."""
    
    beat: int = Field(..., description="Beat number")
    heading: str = Field(..., description="Scene title/heading")
    shot_description: str = Field(..., description="Visual description of the shot")
    action: str = Field(..., description="What happens in this beat")


class ProductConfig(BaseModel):
    """Product configuration for replacement."""
    
    product_image_url: str = Field(..., description="URL to the product image")
    target_object: str = Field(..., description="Object to replace (e.g., 'laptop', 'phone')")


class EpisodeConfig(BaseModel):
    """Configuration for an entire episode."""
    
    title: str = Field(..., description="Episode title")
    product_config: ProductConfig = Field(..., description="Product configuration")
    beats: List[Beat] = Field(..., description="List of beats to process")


class GenerationAttempt(BaseModel):
    """Details of a single generation attempt."""
    
    attempt_number: int = Field(..., description="Attempt number (1-3)")
    storyboard_image_url: str = Field(..., description="Generated storyboard image URL")
    midjourney_task_id: str = Field(..., description="MidJourney task ID")
    distortion_check_passed: bool = Field(..., description="Whether distortion check passed")
    distortion_count: int = Field(default=0, description="Number of distortions found")
    distortion_labels: List[str] = Field(default_factory=list, description="Distortion labels found")
    negative_prompts_used: List[str] = Field(default_factory=list, description="Negative prompts used in this attempt")


class BeatResult(BaseModel):
    """Result of processing a single beat."""
    
    beat_number: int = Field(..., description="Beat number")
    shot_text: str = Field(..., description="Normalized shot text used for generation")
    reference_image_url: Optional[str] = Field(None, description="Reference image from PixelHub")
    color_palette: Optional[List[str]] = Field(None, description="Color palette (hex codes)")
    
    # Generation attempts
    attempts: List[GenerationAttempt] = Field(default_factory=list, description="All generation attempts")
    total_attempts: int = Field(..., description="Total number of attempts made")
    
    # Final selected storyboard
    storyboard_image_url: str = Field(..., description="Final selected storyboard image URL")
    storyboard_task_id: str = Field(..., description="MidJourney task ID for final storyboard")
    quality_check_passed: bool = Field(..., description="Whether final storyboard passed quality check")
    
    # Product replacement
    final_image_url: Optional[str] = Field(None, description="Product-integrated image URL (after nanobanana)")
    product_replacement_success: bool = Field(default=False, description="Whether product replacement succeeded")
    product_replacement_error: Optional[str] = Field(None, description="Error message if replacement failed")
    
    # Metadata
    flagged_for_review: bool = Field(default=False, description="Whether this beat needs manual review")
    review_reason: Optional[str] = Field(None, description="Reason for flagging (e.g., 'All 3 attempts failed quality check')")


class EpisodeResult(BaseModel):
    """Result of processing an entire episode."""
    
    episode_id: str = Field(..., description="Episode identifier")
    title: str = Field(..., description="Episode title")
    episode_palette: Optional[List[str]] = Field(None, description="Shared color palette for all beats")
    beats: List[BeatResult] = Field(default_factory=list, description="Results for each beat")
    
    # Summary statistics
    total_beats: int = Field(..., description="Total number of beats processed")
    successful_beats: int = Field(default=0, description="Beats with successful product replacement")
    flagged_beats: int = Field(default=0, description="Beats flagged for review")
    
    # Global memory artifacts
    product_url_memory: Dict[int, str] = Field(
        default_factory=dict,
        description="Mapping of beat numbers to final product-integrated URLs",
    )
    global_memory: List[str] = Field(
        default_factory=list,
        description="Compact continuity memory distilled after each beat",
    )

