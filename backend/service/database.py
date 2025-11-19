"""SQLite database operations"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from pathlib import Path

from .models import TaskRecord, ContentRecord, TaskStatus, WorkflowStage, ContentBlock

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager"""
    
    def __init__(self, db_path: str = "ad_agent.db"):
        """Initialize database
        
        Args:
            db_path: Database file path
        """
        self.db_path = db_path
        self._init_db()
        logger.info(f"✓ Database initialized: {db_path}")
    
    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    brand_identity TEXT NOT NULL,
                    must_have_shots TEXT NOT NULL,
                    product_images TEXT NOT NULL,
                    video_format TEXT NOT NULL,
                    max_shots INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    error_message TEXT,
                    final_script TEXT,
                    final_video_url TEXT,
                    final_video_with_bgm_url TEXT
                )
            """)
            
            # Create contents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_contents_task_id 
                ON contents(task_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status 
                ON tasks(status)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection (context manager)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ==================== Task Operations ====================
    
    def create_task(
        self,
        task_id: str,
        product_name: str,
        brand_identity: str,
        must_have_shots: str,
        product_images: str,
        video_format: str,
        max_shots: int,
    ) -> TaskRecord:
        """Create new task"""
        now = datetime.now()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, status, stage, product_name, brand_identity,
                    must_have_shots, product_images, video_format, max_shots,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                TaskStatus.CREATED.value,
                WorkflowStage.SCRIPT_GEN_AGENT.value,
                product_name,
                brand_identity,
                must_have_shots,
                product_images,
                video_format,
                max_shots,
                now,
                now,
            ))
            conn.commit()
        
        logger.info(f"✓ Created task: {task_id}")
        return self.get_task(task_id)
    
    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Get task by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                return TaskRecord(**dict(row))
            return None
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        stage: Optional[WorkflowStage] = None,
        error_message: Optional[str] = None,
    ):
        """Update task status"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if stage:
                cursor.execute("""
                    UPDATE tasks 
                    SET status = ?, stage = ?, updated_at = ?, error_message = ?
                    WHERE task_id = ?
                """, (status.value, stage.value, datetime.now(), error_message, task_id))
            else:
                cursor.execute("""
                    UPDATE tasks 
                    SET status = ?, updated_at = ?, error_message = ?
                    WHERE task_id = ?
                """, (status.value, datetime.now(), error_message, task_id))
            
            conn.commit()
        
        logger.debug(f"Updated task {task_id}: status={status.value}, stage={stage.value if stage else 'N/A'}")
    
    def update_task_stage(self, task_id: str, stage: WorkflowStage):
        """Update task stage"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET stage = ?, updated_at = ?
                WHERE task_id = ?
            """, (stage.value, datetime.now(), task_id))
            conn.commit()
        
        logger.debug(f"Updated task {task_id}: stage={stage.value}")
    
    def update_task_final_urls(
        self,
        task_id: str,
        final_script: Optional[str] = None,
        final_video_url: Optional[str] = None,
        final_video_with_bgm_url: Optional[str] = None,
    ):
        """Update final script and video URLs"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET final_script = ?, final_video_url = ?, final_video_with_bgm_url = ?, updated_at = ?
                WHERE task_id = ?
            """, (final_script, final_video_url, final_video_with_bgm_url, datetime.now(), task_id))
            conn.commit()
        
        logger.debug(f"Updated task {task_id}: final script and URLs")
    
    # ==================== Content Operations ====================
    
    def add_content(
        self,
        task_id: str,
        content_type: str,
        timestamp: str,
        data: Dict[str, Any],
    ):
        """Add content block"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO contents (task_id, content_type, timestamp, data_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task_id,
                content_type,
                timestamp,
                json.dumps(data, ensure_ascii=False),
                datetime.now(),
            ))
            conn.commit()
        
        logger.debug(f"Added content to task {task_id}: type={content_type}")
    
    def get_contents(self, task_id: str) -> List[ContentBlock]:
        """Get all content blocks for a task"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content_type, timestamp, data_json
                FROM contents
                WHERE task_id = ?
                ORDER BY id ASC
            """, (task_id,))
            
            rows = cursor.fetchall()
            contents = []
            
            for row in rows:
                try:
                    contents.append(ContentBlock(
                        type=row["content_type"],
                        timestamp=row["timestamp"],
                        data=json.loads(row["data_json"]),
                    ))
                except Exception as e:
                    logger.error(f"Failed to parse content: {e}")
            
            return contents
    
    def get_contents_after(self, task_id: str, after_id: int) -> List[ContentBlock]:
        """Get content blocks after specified ID (for streaming updates)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, content_type, timestamp, data_json
                FROM contents
                WHERE task_id = ? AND id > ?
                ORDER BY id ASC
            """, (task_id, after_id))
            
            rows = cursor.fetchall()
            contents = []
            
            for row in rows:
                try:
                    contents.append(ContentBlock(
                        type=row["content_type"],
                        timestamp=row["timestamp"],
                        data=json.loads(row["data_json"]),
                    ))
                except Exception as e:
                    logger.error(f"Failed to parse content: {e}")
            
            return contents
    
    def get_latest_content_id(self, task_id: str) -> int:
        """Get latest content ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(id) as max_id
                FROM contents
                WHERE task_id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            return row["max_id"] if row["max_id"] else 0

