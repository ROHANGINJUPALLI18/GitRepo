"""FastAPI routes for RAG chat interface."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request payload for RAG chat."""

    query: str = Field(
        ..., 
        min_length=1, 
        max_length=5000,
        description="Natural language question about the codebase"
    )
    top_k: Optional[int] = Field(
        default=5, 
        ge=1, 
        le=50,
        description="Number of code chunks to retrieve"
    )
    repo_filter: Optional[str] = Field(
        default=None,
        description="Optional repository filter for scoped search",
    )


class ChunkMetadata(BaseModel):
    """Metadata about a retrieved code chunk."""

    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    language: Optional[str] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    """Response payload for RAG chat."""

    success: bool
    query: str
    answer: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    chunks_used: int = 0
    chunks_metadata: List[ChunkMetadata] = Field(default_factory=list)
    error: Optional[str] = None


@lru_cache()
def get_chat_service() -> ChatService:
    """Return a cached chat service instance."""
    return ChatService()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest, 
    service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    """
    Chat with the RAG-powered repository assistant.

    Retrieves relevant code chunks, generates a RAG prompt,
    and uses an LLM to provide a conversational answer.

    Args:
        request: Chat request with query and optional parameters

    Returns:
        Chat response with answer, sources, and metadata
    """
    result = service.chat(
        query=request.query,
        top_k=request.top_k,
        repo_filter=request.repo_filter,
    )

    return ChatResponse(**result)


@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    service: ChatService = Depends(get_chat_service)
) -> Dict[str, Any]:
    """
    Check the health of RAG chat components.

    Returns:
        Health status of search, LLM, and prompt services
    """
    return service.health_check()
