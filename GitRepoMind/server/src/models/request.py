"""Request models for GitRepoMind API endpoints."""

from typing import Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request payload for repository analysis."""

    repo_url: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="GitHub repository URL (https://github.com/owner/repo)",
    )
    branch: str = Field(
        default="main",
        min_length=1,
        max_length=255,
        description="Repository branch to analyze",
    )
    force_reindex: bool = Field(
        default=False,
        description="Force re-analysis of repository even if cached",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/microsoft/vscode",
                "branch": "main",
                "force_reindex": False,
            }
        }


class ReindexRequest(BaseModel):
    """Request payload for repository reindexing."""

    repo_url: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="GitHub repository URL (https://github.com/owner/repo)",
    )
    branch: str = Field(
        default="main",
        min_length=1,
        max_length=255,
        description="Repository branch to reindex",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "repo_url": "https://github.com/microsoft/vscode",
                "branch": "main",
            }
        }


class ChatRequest(BaseModel):
    """Request payload for RAG chat."""

    repo_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Repository ID (returned from analyze endpoint)",
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural language question about the codebase",
    )
    session_id: str = Field(
        default="default",
        min_length=1,
        max_length=255,
        description="Conversation session ID for maintaining history",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "repo_id": "owner_repo",
                "query": "How does the authentication module work?",
                "session_id": "user_12345",
            }
        }
