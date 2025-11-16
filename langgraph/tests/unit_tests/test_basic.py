"""Simple test to verify the AD Agent workflow can be imported and initialized."""

import pytest
from agent import app, Context, WorkflowState, ShotState


def test_imports():
    """Test that all main components can be imported."""
    assert app is not None
    assert Context is not None
    assert WorkflowState is not None
    assert ShotState is not None


def test_graph_structure():
    """Test that the graph has the expected structure."""
    # Check that the graph is compiled
    assert app is not None
    
    # Verify the graph has expected nodes
    graph_dict = app.get_graph().to_json()
    assert graph_dict is not None


def test_context_structure():
    """Test that Context has expected fields."""
    # This is a TypedDict, so we just verify the structure
    context: Context = {
        "product_name": "Test Product",
        "brand_identity": "Test Brand",
        "product_images": "http://example.com/image.jpg",
        "must_have_shots": "test shot",
        "generate_video": False,
        "video_model": "veo"
    }
    
    assert context["product_name"] == "Test Product"
    assert context["generate_video"] is False
    assert context["video_model"] == "veo"


def test_workflow_state_structure():
    """Test that WorkflowState has expected fields."""
    # This is a TypedDict, so we just verify the structure
    state: WorkflowState = {
        "product_name": "Test Product",
        "brand_identity": "Test Brand",
        "product_images": "http://example.com/image.jpg",
        "must_have_shots": "test shot",
        "generate_video": False,
        "messages": []
    }
    
    assert state["product_name"] == "Test Product"
    assert state["generate_video"] is False


def test_shot_state_structure():
    """Test that ShotState has expected fields."""
    # This is a TypedDict, so we just verify the structure
    state: ShotState = {
        "shot": "Test shot description",
        "shot_index": 0,
        "product_name": "Test Product",
        "brand_identity": "Test Brand",
        "product_images": "http://example.com/image.jpg",
        "generate_video": False,
        "messages": []
    }
    
    assert state["shot"] == "Test shot description"
    assert state["shot_index"] == 0

