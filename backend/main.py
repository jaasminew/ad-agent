#!/usr/bin/env python3
"""AD Agent API Service - Main Entry Point"""

import uvicorn
import logging
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

if __name__ == "__main__":
    uvicorn.run(
        "service.app:app",  # Import from service.app
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
