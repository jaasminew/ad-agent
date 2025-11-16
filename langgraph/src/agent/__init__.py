"""AD Agent - LangGraph-based advertising video generation.

This package provides a complete workflow for generating advertising videos
using AI, including script writing, image generation, video creation, and
background music generation.

Usage with LangGraph Server:
    langgraph dev

Usage programmatically:
    from agent import app
    
    result = app.invoke(
        {"product_name": "Product", ...},
        {"configurable": {
            "product_name": "Product",
            "brand_identity": "Brand Values",
            "product_images": "https://...",
            "must_have_shots": "Required scenes",
            "generate_video": False,
            "video_model": "veo"
        }}
    )
"""

from agent.graph import app, Context, InputState
from agent.workers import WorkflowState, ShotState

__all__ = ["app", "Context", "InputState", "WorkflowState", "ShotState"]
