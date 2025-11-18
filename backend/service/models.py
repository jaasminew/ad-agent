"""Data models definition"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration"""
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStage(str, Enum):
    """Workflow stage enumeration"""
    SCRIPT_GEN_AGENT = "script_gen_agent"
    STORYBOARD_GEN_AGENT = "storyboard_gen_agent"
    VIDEO_GENERATOR = "video_generator"
    VIDEO_CONCATENATER = "video_concatenater"
    BGM_GENERATOR = "bgm_generator"
    COMPLETED = "completed"


class ContentType(str, Enum):
    """Content block type enumeration"""
    LLM_OUTPUT = "llm_output"
    TOOL_CALLING = "tool_calling"


# ==================== API Request/Response Models ====================

class CreateTaskRequest(BaseModel):
    """Create task request"""
    product_name: str = Field(..., description="Product name")
    brand_identity: str = Field(..., description="Brand identity/positioning")
    must_have_shots: str = Field(..., description="Required shots (comma-separated)")
    product_images: str = Field(..., description="Product image URL")
    video_format: str = Field(..., description="Video format (16:9, 9:16, 1:1)")
    max_shots: int = Field(..., ge=1, le=10, description="Maximum number of shots")


class CreateTaskResponse(BaseModel):
    """Create task response"""
    task_id: str


class CancelTaskResponse(BaseModel):
    """Cancel task response"""
    success: bool
    message: str


class AssessmentRequest(BaseModel):
    """Assessment request"""
    task_id: str
    stage: WorkflowStage
    comment: Optional[str] = None


class AssessmentResponse(BaseModel):
    """Assessment response"""
    success: bool
    message: str


# ==================== Content Block Models ====================

class LLMOutputData(BaseModel):
    """LLM output data"""
    stage: str
    message: str
    reasoning: Optional[str] = None
    output: Dict[str, Any]


class ToolCallingData(BaseModel):
    """Tool calling data"""
    tool_name: str
    stage: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    success: bool
    error: Optional[str] = None


class ContentBlock(BaseModel):
    """Content block (LLM output or tool calling)"""
    type: ContentType
    timestamp: str
    data: Dict[str, Any]  # LLMOutputData or ToolCallingData
    
    class Config:
        use_enum_values = True


# ==================== Task Query Response ====================

class TaskQueryResponse(BaseModel):
    """Task query response"""
    task_id: str
    stage: WorkflowStage
    status: TaskStatus
    product_name: str = Field(default="", description="Product name")
    final_script: Optional[str] = Field(default=None, description="Final script")
    final_video_url: Optional[str] = Field(default=None, description="Final video URL (without BGM)")
    final_video_with_bgm_url: Optional[str] = Field(default=None, description="Final video URL (with BGM)")
    created_at: str = Field(default="", description="Creation timestamp")
    contents: List[ContentBlock] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


# ==================== Database Models ====================

class TaskRecord:
    """Task record (database)"""
    def __init__(
        self,
        task_id: str,
        status: str,
        stage: str,
        product_name: str,
        brand_identity: str,
        must_have_shots: str,
        product_images: str,
        video_format: str,
        max_shots: int,
        created_at: datetime,
        updated_at: datetime,
        error_message: Optional[str] = None,
        final_script: Optional[str] = None,
        final_video_url: Optional[str] = None,
        final_video_with_bgm_url: Optional[str] = None,
    ):
        self.task_id = task_id
        self.status = status
        self.stage = stage
        self.product_name = product_name
        self.brand_identity = brand_identity
        self.must_have_shots = must_have_shots
        self.product_images = product_images
        self.video_format = video_format
        self.max_shots = max_shots
        self.created_at = created_at
        self.updated_at = updated_at
        self.error_message = error_message
        self.final_script = final_script
        self.final_video_url = final_video_url
        self.final_video_with_bgm_url = final_video_with_bgm_url


class ContentRecord:
    """Content record (database)"""
    def __init__(
        self,
        id: int,
        task_id: str,
        content_type: str,
        timestamp: str,
        data_json: str,
        created_at: datetime,
    ):
        self.id = id
        self.task_id = task_id
        self.content_type = content_type
        self.timestamp = timestamp
        self.data_json = data_json
        self.created_at = created_at

