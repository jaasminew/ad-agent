"""Helpers for cooperative task cancellation inside workflow workers/tools."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Ensure backend root (which contains the `service` package) is on sys.path
_backend_root = Path(__file__).resolve().parent.parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))


def _get_task_context() -> Tuple[Optional[str], Optional["TaskManager"]]:
    """Return current (task_id, task_manager) tuple if service is active."""
    try:
        from service.task_manager import TaskContext, get_task_manager
    except Exception:
        return None, None

    task_id = TaskContext.get_task_id()
    if not task_id:
        return None, None

    try:
        task_manager = get_task_manager()
    except Exception as exc:
        logger.debug(f"Failed to fetch TaskManager for cancellation check: {exc}")
        return None, None

    return task_id, task_manager


def cancellation_requested() -> bool:
    """Return True if the current task has been cancelled."""
    task_id, task_manager = _get_task_context()
    if not task_id or not task_manager:
        return False
    try:
        return task_manager.is_cancelled(task_id)
    except Exception as exc:
        logger.debug(f"Cancellation check failed: {exc}")
        return False


def raise_if_cancelled(location: Optional[str] = None):
    """Raise TaskCancelledException if the current task is cancelled."""
    task_id, task_manager = _get_task_context()
    if not task_id or not task_manager:
        return

    try:
        cancelled = task_manager.is_cancelled(task_id)
    except Exception as exc:
        logger.debug(f"Cancellation check failed: {exc}")
        return

    if not cancelled:
        return

    try:
        from service.workflow_executor import TaskCancelledException
    except Exception:
        # If the service layer isn't available, quietly return so tests can continue.
        logger.debug("TaskCancelledException unavailable; skipping cancellation raise.")
        return

    location_msg = f" during {location}" if location else ""
    logger.info(f"[Task {task_id}] Task cancelled by user{location_msg}")
    raise TaskCancelledException(f"Task {task_id} cancelled")


def sleep_with_cancellation(total_seconds: float, location: Optional[str] = None, check_interval: float = 0.5):
    """Sleep cooperatively while staying responsive to cancellation signals."""
    if total_seconds <= 0:
        return

    deadline = time.time() + total_seconds
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        raise_if_cancelled(location)
        time.sleep(min(check_interval, remaining))


__all__ = ["cancellation_requested", "raise_if_cancelled", "sleep_with_cancellation"]

