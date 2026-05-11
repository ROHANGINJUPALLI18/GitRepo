"""FastAPI routes for semantic similarity search."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services.search_service import SimilaritySearchService

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    """Request payload for semantic retrieval."""

    query: str = Field(..., min_length=1, description="Natural-language question")
    top_k: Optional[int] = Field(default=None, ge=1, le=50)
    repo_filter: Optional[str] = Field(
        default=None,
        description="Optional owner/repo filter for scoped retrieval",
    )


class SearchResponse(BaseModel):
    """Response payload for semantic retrieval."""

    query: str
    top_k: int
    repo_filter: Optional[str] = None
    count: int
    results: List[Dict[str, Any]]


@lru_cache()
def get_search_service() -> SimilaritySearchService:
    """Return a cached search service instance."""

    return SimilaritySearchService()


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest, service: SimilaritySearchService = Depends(get_search_service)):
    """Embed the user query and return the most relevant stored chunks."""

    return service.search(
        query=request.query,
        top_k=request.top_k,
        repo_filter=request.repo_filter,
    )