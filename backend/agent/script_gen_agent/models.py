"""Data models for script generation."""

from typing import List
from pydantic import BaseModel, Field


class Shot(BaseModel):
    """A single shot/scene from the advertising script."""
    
    shot_number: int = Field(..., description="Shot number")
    description: str = Field(..., description="Shot description")


class ScriptConfig(BaseModel):
    """Configuration for script generation."""
    
    product_name: str = Field(..., description="Product name")
    brand_identity: str = Field(..., description="Brand identity/positioning")
    must_have_shots: str = Field(..., description="Required shots (comma-separated)")
    num_shots: int = Field(default=3, description="Number of shots to generate")


class ScriptResult(BaseModel):
    """Result of script generation."""
    
    shots: List[Shot] = Field(default_factory=list, description="Generated shot list")
    total_shots: int = Field(..., description="Total number of shots generated")
    research_notes: List[str] = Field(default_factory=list, description="Research notes from web search")

