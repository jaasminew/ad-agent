"""Service package initialization"""

from .main import app
from .database import Database
from .task_manager import TaskManager, init_task_manager, get_task_manager
from .models import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskQueryResponse,
    TaskStatus,
    WorkflowStage,
    ContentType,
)

__version__ = "1.0.0"

__all__ = [
    "app",
    "Database",
    "TaskManager",
    "init_task_manager",
    "get_task_manager",
    "CreateTaskRequest",
    "CreateTaskResponse",
    "TaskQueryResponse",
    "TaskStatus",
    "WorkflowStage",
    "ContentType",
]

