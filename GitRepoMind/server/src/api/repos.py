"""FastAPI routes for repository management."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from ..core.cache import RepoCache
from ..models.response import RepoListResponse, RepoStatsResponse, SuccessResponse
from ..services.vector_store_service import QdrantVectorStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/repos", tags=["repos"])


@router.get("", response_model=RepoListResponse)
async def list_repositories() -> RepoListResponse:
    """
    List all indexed repositories.

    Returns all repositories that have been analyzed and cached.

    Returns:
        RepoListResponse with list of all indexed repositories

    Raises:
        HTTPException: If operation fails
    """
    try:
        repos = RepoCache.list_all()
        logger.info(f"Returning {len(repos)} repositories")
        
        return RepoListResponse(
            total=len(repos),
            repos=[
                {
                    "repo_id": r["repo_id"],
                    "repo_name": r["repo_name"],
                    "indexed_at": r["indexed_at"],
                    "total_files": r["total_files"],
                    "primary_language": r["primary_language"],
                }
                for r in repos
            ],
        )
    except Exception as e:
        logger.error(f"Error listing repositories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "LIST_ERROR",
                "message": "Failed to list repositories",
            },
        )


@router.get("/{repo_id}/stats", response_model=RepoStatsResponse)
async def get_repository_stats(repo_id: str) -> RepoStatsResponse:
    """
    Get statistics for an indexed repository.

    Combines cached analysis data with vector store statistics
    to provide comprehensive repository information.

    Args:
        repo_id: Repository ID returned from analyze-repo endpoint

    Returns:
        RepoStatsResponse with detailed repository statistics

    Raises:
        HTTPException: If repository not found or operation fails
    """
    try:
        # Get cached analysis
        cached = RepoCache.get(repo_id)
        if not cached:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "code": "REPO_NOT_FOUND",
                    "message": "Repository has not been analyzed yet.",
                    "hint": "Call POST /api/analyze-repo first.",
                },
            )

        repo_name = cached.get("repo_name", "Unknown")

        # Get vector store statistics
        try:
            vector_store = QdrantVectorStore()
            stats = vector_store.get_collection_info()
            chunk_count = stats.get("points_count", 0)
        except Exception as e:
            logger.warning(f"Failed to get vector store stats: {str(e)}")
            chunk_count = 0

        return RepoStatsResponse(
            repo_id=repo_id,
            repo_name=repo_name,
            total_files=cached.get("total_files", 0),
            indexed_files=cached.get("indexed_files", 0),
            total_chunks=chunk_count,
            languages=cached.get("language_info", {}),
            frameworks=_extract_frameworks(cached),
            indexed_at=cached.get("indexed_at", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting repository stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "STATS_ERROR",
                "message": "Failed to retrieve repository statistics",
            },
        )


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(repo_id: str) -> None:
    """
    Delete an indexed repository from cache and vector store.

    Removes all associated data:
    - Vectors from Qdrant
    - Cached analysis results
    - Conversation history (if exists)

    Args:
        repo_id: Repository ID returned from analyze-repo endpoint

    Returns:
        Empty response on success

    Raises:
        HTTPException: If repository not found or operation fails
    """
    try:
        # Get cached data to find repo name
        cached = RepoCache.get(repo_id)
        if not cached:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "code": "REPO_NOT_FOUND",
                    "message": "Repository has not been analyzed yet.",
                    "hint": "Call POST /api/analyze-repo first.",
                },
            )

        repo_name = cached.get("repo_name", repo_id)

        # Delete from vector store
        logger.info(f"Deleting vectors for {repo_id}")
        try:
            vector_store = QdrantVectorStore()
            vector_store.delete_repo(repo_name)
        except Exception as e:
            logger.warning(f"Failed to delete vectors: {str(e)}")

        # Delete from cache
        RepoCache.delete(repo_id)
        logger.info(f"Deleted repository {repo_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting repository: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "DELETE_ERROR",
                "message": "Failed to delete repository",
            },
        )


def _extract_frameworks(cached_data: dict) -> list:
    """
    Extract framework names from architecture data.

    Args:
        cached_data: Cached analysis data

    Returns:
        List of detected frameworks
    """
    frameworks = []
    
    # Try to extract from architecture section
    architecture = cached_data.get("architecture", {})
    if isinstance(architecture, dict):
        frameworks_from_arch = architecture.get("frameworks", [])
        if isinstance(frameworks_from_arch, list):
            frameworks.extend(frameworks_from_arch)
    
    return list(set(frameworks))  # Remove duplicates
