import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api import analyze, chat, repos, health


# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="GitRepoMind API",
        version="1.0.0",
        description="AI-powered GitHub Repository Analyzer & RAG Chat",
        debug=settings.debug,
    )

    # Add CORS middleware - allow all origins for frontend on localhost:5173
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def root_health():
        """Root health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": "1.0.0",
        }

    # Include API routers
    app.include_router(analyze.router)
    app.include_router(chat.router)
    app.include_router(repos.router)
    app.include_router(health.router)

    logger.info("GitRepoMind API app created successfully")
    return app


# Create the FastAPI application instance
app = create_app()


# Create app instance
app = create_app()
