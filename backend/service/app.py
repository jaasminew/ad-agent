"""Application module - exports the FastAPI app

This is a convenience module that re-exports the app from main.py
to provide a cleaner import path: service.app instead of service.main
"""

from .main import app

__all__ = ["app"]

