"""
Entry point for the FastAPI application.
Run with: python -m uvicorn src.main:app --reload
Or from server directory: uvicorn src.main:app --reload
"""

import uvicorn
from app import app
from config import settings
import base64


def main():
    """Run the FastAPI application."""
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
