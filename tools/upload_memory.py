"""Shared registry for product-integrated COS URLs."""

from __future__ import annotations

import json
import threading
from typing import List, Optional

_UPLOADED_URLS: List[str] = []
_LOCK = threading.Lock()


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

    with _LOCK:
        if normalized not in _UPLOADED_URLS:
            _UPLOADED_URLS.append(normalized)
    _update_memory_note()


def get_uploaded_urls() -> List[str]:
    """Return a copy of all uploaded COS URLs in insertion order."""
    with _LOCK:
        return list(_UPLOADED_URLS)


def clear_uploaded_urls() -> None:
    """Reset the registry (e.g., when starting a new episode run)."""
    with _LOCK:
        _UPLOADED_URLS.clear()
    _update_memory_note()


def _update_memory_note() -> None:
    """Keep the shared LangChain memory's first entry synchronized."""
    try:
        from .memory import MEM
    except Exception:
        return

    note = format_uploaded_urls_note(_UPLOADED_URLS)

    if not MEM:
        MEM.append(note)
        return

    first = MEM[0]
    if isinstance(first, str) and first.startswith("uploaded_final_urls:"):
        MEM[0] = note
        return

    MEM.insert(0, note)

