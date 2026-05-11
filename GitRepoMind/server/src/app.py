import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api.search import router as search_router


# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Update for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Check API and dependency health."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    # Include API routers
    app.include_router(search_router)

    logger.info(f"{settings.app_name} app created successfully")
    return app


# Create app instance
app = create_app()
