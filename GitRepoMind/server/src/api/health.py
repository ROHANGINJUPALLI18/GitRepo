"""FastAPI routes for health checks."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from ..config import settings
from ..models.response import HealthResponse, QdrantStatsResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Check the overall health of the API and dependencies.

    Tests:
    - API server availability
    - Qdrant vector database connectivity

    Returns:
        HealthResponse with overall status and component statuses

    Raises:
        HTTPException: If critical dependencies are unavailable
    """
    try:
        # Check Qdrant connectivity
        qdrant_status = _check_qdrant_connection()
        
        if qdrant_status == "disconnected":
            # Qdrant is required for functionality
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "success": False,
                    "code": "QDRANT_OFFLINE",
                    "message": "Vector database is unavailable",
                    "hint": f"Check Qdrant server at {settings.quadrant_url}",
                },
            )

        return HealthResponse(
            status="ok",
            qdrant=qdrant_status,
            timestamp=datetime.utcnow().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking health: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "HEALTH_CHECK_ERROR",
                "message": "Failed to perform health check",
            },
        )


@router.get("/qdrant", response_model=QdrantStatsResponse)
async def qdrant_health() -> QdrantStatsResponse:
    """
    Check Qdrant vector database status and statistics.

    Returns connection status, number of collections, and server URL.

    Returns:
        QdrantStatsResponse with connection details

    Raises:
        HTTPException: If check fails
    """
    try:
        connected = False
        collections = 0

        try:
            from ..services.vector_store_service import QdrantVectorStore

            vector_store = QdrantVectorStore()
            # Try to list collections to verify connection
            try:
                collections_list = vector_store.client.get_collections()
                collections = len(collections_list.collections) if collections_list else 0
                connected = True
            except Exception as e:
                logger.warning(f"Failed to get collections: {str(e)}")
                connected = False

        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {str(e)}")
            connected = False

        return QdrantStatsResponse(
            connected=connected,
            collections=collections,
            url=settings.quadrant_url,
        )

    except Exception as e:
        logger.error(f"Error checking Qdrant: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "QDRANT_CHECK_ERROR",
                "message": "Failed to check Qdrant status",
            },
        )


def _check_qdrant_connection() -> str:
    """
    Check if Qdrant is reachable.

    Returns:
        "connected" if Qdrant is available, "disconnected" otherwise
    """
    try:
        from ..services.vector_store_service import QdrantVectorStore

        vector_store = QdrantVectorStore()
        # Try to perform a simple operation
        vector_store.client.get_collections()
        return "connected"
    except Exception as e:
        logger.warning(f"Qdrant connection check failed: {str(e)}")
        return "disconnected"
