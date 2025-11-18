"""FastAPI Application - AD Agent API

This module is now imported by backend/main.py
Old path: backend/service/main.py
New usage: from service.app import app
"""

import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import AsyncGenerator
import asyncio

from .database import Database
from .task_manager import TaskManager, init_task_manager, get_task_manager
from .models import (
    CreateTaskRequest,
    CreateTaskResponse,
    CancelTaskResponse,
    AssessmentRequest,
    AssessmentResponse,
    TaskQueryResponse,
    TaskStatus,
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="AD Agent API",
    description="AI-powered advertising video generation API",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
db: Database = None
task_manager: TaskManager = None


@app.on_event("startup")
async def startup_event():
    """Initialize database and task manager on application startup"""
    global db, task_manager
    
    logger.info("=" * 80)
    logger.info("Starting AD Agent API Service")
    logger.info("=" * 80)
    
    # Initialize database
    db = Database(db_path="ad_agent.db")
    
    # Initialize task manager
    init_task_manager(db)
    task_manager = get_task_manager()
    
    logger.info("✓ Service started successfully")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown"""
    logger.info("Shutting down AD Agent API Service...")


# ==================== API Endpoints ====================

@app.post("/v1/tasks", response_model=CreateTaskResponse, status_code=201)
async def create_task(request: CreateTaskRequest):
    """Create new advertising video generation task
    
    Args:
        request: Task creation request
        
    Returns:
        CreateTaskResponse: Contains task_id
    """
    try:
        task_id = task_manager.create_task(request)
        logger.info(f"✓ Task created via API: {task_id}")
        return CreateTaskResponse(task_id=task_id)
    
    except Exception as e:
        logger.error(f"Failed to create task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/tasks/{task_id}/cancel", response_model=CancelTaskResponse)
async def cancel_task(task_id: str):
    """Cancel running task
    
    Args:
        task_id: Task ID
        
    Returns:
        CancelTaskResponse: Cancellation result
    """
    # Check if task exists
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check task status
    if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Task cannot be cancelled (current status: {task.status})"
        )
    
    # Cancel task
    success = task_manager.cancel_task(task_id)
    
    if success:
        logger.info(f"✓ Task cancelled via API: {task_id}")
        return CancelTaskResponse(
            success=True,
            message="Task cancellation initiated"
        )
    else:
        raise HTTPException(status_code=400, detail="Failed to cancel task")


@app.get("/v1/tasks/{task_id}", response_model=TaskQueryResponse)
async def get_task(
    task_id: str,
    stream: bool = Query(False, description="Enable streaming response")
):
    """Query task status and results
    
    Args:
        task_id: Task ID
        stream: Whether to enable streaming response
        
    Returns:
        TaskQueryResponse: Task status and contents
    """
    # Check if task exists
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Enable streaming if requested
    if stream:
        return StreamingResponse(
            _stream_task_updates(task_id),
            media_type="text/event-stream",
        )
    
    # Otherwise return current status
    task_response = task_manager.get_task_status(task_id)
    return task_response


async def _stream_task_updates(task_id: str) -> AsyncGenerator[str, None]:
    """Stream task updates
    
    Args:
        task_id: Task ID
        
    Yields:
        SSE formatted event data
    """
    try:
        # First send current status
        task = db.get_task(task_id)
        if not task:
            yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"
            return
        
        # Send status update
        yield f"event: update\ndata: {json.dumps({'stage': task.stage, 'status': task.status})}\n\n"
        
        # Send existing contents
        contents = db.get_contents(task_id)
        for content in contents:
            content_json = json.dumps(content.dict(), ensure_ascii=False)
            yield f"event: content\ndata: {content_json}\n\n"
        
        # Continue pushing new contents
        last_content_id = db.get_latest_content_id(task_id)
        
        while True:
            # Check task status
            task = db.get_task(task_id)
            
            # Get new contents
            new_contents = db.get_contents_after(task_id, last_content_id)
            for content in new_contents:
                content_json = json.dumps(content.dict(), ensure_ascii=False)
                yield f"event: content\ndata: {content_json}\n\n"
            
            if new_contents:
                last_content_id = db.get_latest_content_id(task_id)
            
            # If task is completed or failed, send complete event and end
            if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                yield f"event: complete\ndata: {json.dumps({'task_id': task_id, 'status': task.status})}\n\n"
                break
            
            # Wait before checking again
            await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"Error in stream for task {task_id}: {e}", exc_info=True)
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@app.post("/v1/tasks/{task_id}/assessment", response_model=AssessmentResponse)
async def submit_assessment(task_id: str, request: AssessmentRequest):
    """Submit stage assessment feedback
    
    Args:
        task_id: Task ID
        request: Assessment request
        
    Returns:
        AssessmentResponse: Assessment result
    """
    # Check if task exists
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Validate task_id match
    if request.task_id != task_id:
        raise HTTPException(status_code=400, detail="Task ID mismatch")
    
    # TODO: Implement assessment logic
    # Currently just logging the assessment
    logger.info(f"Assessment received for task {task_id}, stage {request.stage}: {request.comment}")
    
    return AssessmentResponse(
        success=True,
        message="Assessment received"
    )


@app.get("/")
async def root():
    """Root path - API information"""
    return {
        "service": "AD Agent API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "create_task": "POST /v1/tasks",
            "cancel_task": "POST /v1/tasks/{task_id}/cancel",
            "query_task": "GET /v1/tasks/{task_id}",
            "query_task_stream": "GET /v1/tasks/{task_id}?stream=true",
            "assessment": "POST /v1/tasks/{task_id}/assessment",
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}
