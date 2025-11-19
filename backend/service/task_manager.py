"""Task Manager - Manages asynchronous task execution"""

import uuid
import threading
import logging
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from queue import Queue

from .database import Database
from .models import (
    TaskStatus,
    WorkflowStage,
    ContentBlock,
    ContentType,
    CreateTaskRequest,
    TaskQueryResponse,
)

logger = logging.getLogger(__name__)


class TaskContext:
    """Task execution context (thread-local storage)"""
    _local = threading.local()
    
    @classmethod
    def set_task_id(cls, task_id: str):
        """Set current task ID"""
        cls._local.task_id = task_id
    
    @classmethod
    def get_task_id(cls) -> Optional[str]:
        """Get current task ID"""
        return getattr(cls._local, 'task_id', None)
    
    @classmethod
    def clear(cls):
        """Clear context"""
        if hasattr(cls._local, 'task_id'):
            delattr(cls._local, 'task_id')


class TaskManager:
    """Task Manager - Manages task lifecycle"""
    
    def __init__(self, db: Database):
        """Initialize task manager
        
        Args:
            db: Database instance
        """
        self.db = db
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.cancel_flags: Dict[str, threading.Event] = {}
        self.content_queues: Dict[str, Queue] = {}  # For real-time content pushing
        logger.info("✓ TaskManager initialized")
    
    # ==================== Task Creation and Management ====================
    
    def create_task(self, request: CreateTaskRequest) -> str:
        """Create new task and start asynchronous execution
        
        Args:
            request: Task creation request
            
        Returns:
            task_id: Task ID
        """
        task_id = str(uuid.uuid4())
        
        # Create database record
        self.db.create_task(
            task_id=task_id,
            product_name=request.product_name,
            brand_identity=request.brand_identity,
            must_have_shots=request.must_have_shots,
            product_images=request.product_images,
            video_format=request.video_format,
            max_shots=request.max_shots,
        )
        
        # Create cancel flag
        self.cancel_flags[task_id] = threading.Event()
        
        # Create content queue
        self.content_queues[task_id] = Queue()
        
        # Start background execution thread
        thread = threading.Thread(
            target=self._execute_workflow,
            args=(task_id, request),
            daemon=True,
        )
        thread.start()
        self.running_tasks[task_id] = thread
        
        logger.info(f"✓ Task created and started: {task_id}")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel task
        
        Args:
            task_id: Task ID
            
        Returns:
            Whether cancellation was successful
        """
        task = self.db.get_task(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return False
        
        if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
            logger.warning(f"Cannot cancel task in status: {task.status}")
            return False
        
        # Set cancel flag
        if task_id in self.cancel_flags:
            self.cancel_flags[task_id].set()
            logger.info(f"✓ Cancellation requested for task: {task_id}")
            return True
        
        return False
    
    def is_cancelled(self, task_id: str) -> bool:
        """Check if task is cancelled"""
        if task_id in self.cancel_flags:
            return self.cancel_flags[task_id].is_set()
        return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskQueryResponse]:
        """Get task status
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status response
        """
        task = self.db.get_task(task_id)
        if not task:
            return None
        
        contents = self.db.get_contents(task_id)
        
        return TaskQueryResponse(
            task_id=task.task_id,
            stage=WorkflowStage(task.stage),
            status=TaskStatus(task.status),
            product_name=task.product_name,
            final_script=task.final_script,
            final_video_url=task.final_video_url,
            final_video_with_bgm_url=task.final_video_with_bgm_url,
            created_at=task.created_at.isoformat(),
            contents=contents,
        )
    
    # ==================== Content Recording ====================
    
    def add_llm_output(
        self,
        task_id: str,
        stage: WorkflowStage,
        message: str,
        output: Dict[str, Any],
        reasoning: Optional[str] = None,
    ):
        """Record LLM output
        
        Args:
            task_id: Task ID
            stage: Workflow stage
            message: Message description
            output: Output data
            reasoning: Reasoning process (optional)
        """
        timestamp = datetime.now().isoformat()
        data = {
            "stage": stage.value,
            "message": message,
            "reasoning": reasoning,
            "output": output,
        }
        
        self.db.add_content(
            task_id=task_id,
            content_type=ContentType.LLM_OUTPUT.value,
            timestamp=timestamp,
            data=data,
        )
        
        # Push to queue (for streaming output)
        if task_id in self.content_queues:
            self.content_queues[task_id].put(ContentBlock(
                type=ContentType.LLM_OUTPUT,
                timestamp=timestamp,
                data=data,
            ))
        
        logger.debug(f"Recorded LLM output for task {task_id}: {message[:50]}...")
    
    def add_tool_calling(
        self,
        task_id: str,
        stage: WorkflowStage,
        tool_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
    ):
        """Record tool calling
        
        Args:
            task_id: Task ID
            stage: Workflow stage
            tool_name: Tool name
            input_data: Input data
            output_data: Output data
            success: Whether successful
            error: Error message (optional)
        """
        timestamp = datetime.now().isoformat()
        data = {
            "tool_name": tool_name,
            "stage": stage.value,
            "input": input_data,
            "output": output_data,
            "success": success,
            "error": error,
        }
        
        self.db.add_content(
            task_id=task_id,
            content_type=ContentType.TOOL_CALLING.value,
            timestamp=timestamp,
            data=data,
        )
        
        # Push to queue (for streaming output)
        if task_id in self.content_queues:
            self.content_queues[task_id].put(ContentBlock(
                type=ContentType.TOOL_CALLING,
                timestamp=timestamp,
                data=data,
            ))
        
        logger.debug(f"Recorded tool calling for task {task_id}: {tool_name}")
    
    # ==================== Internal Execution Methods ====================
    
    def _execute_workflow(self, task_id: str, request: CreateTaskRequest):
        """Execute workflow in background thread
        
        Args:
            task_id: Task ID
            request: Task request
        """
        # Set thread-local task ID
        TaskContext.set_task_id(task_id)
        
        try:
            logger.info(f"Starting workflow execution for task: {task_id}")
            
            # Update status to processing
            self.db.update_task_status(
                task_id=task_id,
                status=TaskStatus.PROCESSING,
                stage=WorkflowStage.SCRIPT_GEN_AGENT,
            )
            
            # Import workflow (lazy import to avoid circular dependency)
            from .workflow_executor import execute_workflow
            
            # Execute workflow
            final_state = execute_workflow(
                task_manager=self,
                task_id=task_id,
                product_name=request.product_name,
                brand_identity=request.brand_identity,
                product_images=request.product_images,
                must_have_shots=request.must_have_shots,
                max_shots=request.max_shots,
                video_format=request.video_format,
            )
            
            # Update final results
            # Extract script from state
            final_script = None
            if "shots" in final_state and final_state["shots"]:
                # Format shots into readable script
                shots_list = []
                for i, shot in enumerate(final_state["shots"], 1):
                    desc = shot.get("description", shot.get("shot_description", ""))
                    shots_list.append(f"Shot {i}: {desc}")
                final_script = "\n\n".join(shots_list)
            
            self.db.update_task_final_urls(
                task_id=task_id,
                final_script=final_script,
                final_video_url=final_state.get("final_video_url"),
                final_video_with_bgm_url=final_state.get("final_video_with_bgm_url"),
            )
            
            # Update status to completed
            self.db.update_task_status(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                stage=WorkflowStage.COMPLETED,
            )
            
            logger.info(f"✓ Workflow completed successfully for task: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ Workflow failed for task {task_id}: {e}", exc_info=True)
            
            # Check if cancellation caused the failure
            if self.is_cancelled(task_id):
                self.db.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.CANCELLED,
                    error_message="Task cancelled by user",
                )
            else:
                self.db.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error_message=str(e),
                )
        
        finally:
            # Cleanup resources
            TaskContext.clear()
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.cancel_flags:
                del self.cancel_flags[task_id]
            # Keep content_queue for subsequent queries


# ==================== Global Instance ====================

# This will be initialized when FastAPI starts
_task_manager: Optional[TaskManager] = None


def init_task_manager(db: Database):
    """Initialize global task manager"""
    global _task_manager
    _task_manager = TaskManager(db)
    logger.info("✓ Global TaskManager initialized")


def get_task_manager() -> TaskManager:
    """Get global task manager"""
    if _task_manager is None:
        raise RuntimeError("TaskManager not initialized. Call init_task_manager() first.")
    return _task_manager

