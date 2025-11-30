"""Shared registry for product-integrated COS URLs."""

from __future__ import annotations

import json
import contextvars
from typing import List, Optional

# Use ContextVar for thread-local storage instead of global list + lock
# This ensures tasks running in different threads don't interfere with each other
_UPLOADED_URLS_VAR: contextvars.ContextVar[List[str]] = contextvars.ContextVar("uploaded_urls")


def _get_urls_list() -> List[str]:
    """Get the current thread's URL list. Initializes if empty."""
    try:
        return _UPLOADED_URLS_VAR.get()
    except LookupError:
        new_list = []
        _UPLOADED_URLS_VAR.set(new_list)
        return new_list


def format_uploaded_urls_note(uploaded_urls: Optional[List[str]] = None) -> str:
    """Return the canonical serialized note for the uploaded URL list."""
    safe_urls = uploaded_urls or []
    return f"uploaded_final_urls: {json.dumps(safe_urls)}"


def register_uploaded_url(url: str) -> None:
    """
    Record a COS URL immediately after a successful upload.
    Duplicate URLs are ignored while preserving insertion order.
    """
    if not url:
        return

    normalized = url.strip()
    if not normalized:
        return

    urls = _get_urls_list()
    if normalized not in urls:
        urls.append(normalized)
    
    _update_memory_note()


def get_uploaded_urls() -> List[str]:
    """Return a copy of all uploaded COS URLs in insertion order."""
    return list(_get_urls_list())


def clear_uploaded_urls() -> None:
    """Reset the registry (e.g., when starting a new episode run)."""
    _UPLOADED_URLS_VAR.set([])
    _update_memory_note()


def _update_memory_note() -> None:
    """Keep the shared LangChain memory's first entry synchronized."""
    try:
        from .memory import get_memory
    except Exception:
        return

    urls = _get_urls_list()
    note = format_uploaded_urls_note(urls)
    mem = get_memory()

    if not mem:
        mem.append(note)
        return

    first = mem[0]
    if isinstance(first, str) and first.startswith("uploaded_final_urls:"):
        mem[0] = note
        return

    mem.insert(0, note)

