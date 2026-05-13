"""Response models for GitRepoMind API endpoints."""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AnalyzeResponse(BaseModel):
    """Response payload for repository analysis."""

    success: bool = Field(..., description="Whether analysis succeeded")
    repo_id: str = Field(..., description="Unique identifier for the analyzed repository")
    repo_name: str = Field(..., description="Repository name (owner/repo)")
    total_files: int = Field(..., description="Total files in repository")
    indexed_files: int = Field(..., description="Number of files indexed")
    language_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Programming language distribution",
    )
    entry_points: List[str] = Field(
        default_factory=list,
        description="Main entry point files",
    )
    architecture: Dict[str, Any] = Field(
        default_factory=dict,
        description="Repository architecture analysis",
    )
    readme_overview: str = Field(
        default="",
        description="README summary if available",
    )
    indexed_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp when analysis was completed",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "repo_id": "owner_repo",
                "repo_name": "owner/repo",
                "total_files": 150,
                "indexed_files": 120,
                "language_info": {"Python": 45, "JavaScript": 30, "JSON": 25},
                "entry_points": ["main.py", "index.js"],
                "architecture": {"layers": ["api", "services", "utils"]},
                "readme_overview": "This is a project about...",
                "indexed_at": "2026-05-13T12:34:56.000000",
            }
        }


class ChatMessage(BaseModel):
    """A message in conversation history."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    sources: List[str] = Field(
        default_factory=list,
        description="Source code snippets (only for assistant messages)",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Message timestamp",
    )


class ChatResponse(BaseModel):
    """Response payload for RAG chat."""

    success: bool = Field(..., description="Whether request succeeded")
    answer: str = Field(..., description="AI-generated answer to the query")
    sources: List[str] = Field(
        default_factory=list,
        description="Relevant source code snippets",
    )
    session_id: str = Field(..., description="Conversation session ID")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "The authentication is handled by...",
                "sources": ["src/auth/login.py:10-45", "src/auth/tokens.py:1-30"],
                "session_id": "user_12345",
            }
        }


class HistoryResponse(BaseModel):
    """Response payload for conversation history."""

    session_id: str = Field(..., description="Conversation session ID")
    messages: List[ChatMessage] = Field(..., description="List of messages in conversation")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "user_12345",
                "messages": [
                    {
                        "role": "user",
                        "content": "How does auth work?",
                        "sources": [],
                        "timestamp": "2026-05-13T12:00:00.000000",
                    },
                    {
                        "role": "assistant",
                        "content": "The auth system...",
                        "sources": ["src/auth.py"],
                        "timestamp": "2026-05-13T12:00:05.000000",
                    },
                ],
            }
        }


class RepoSummary(BaseModel):
    """Summary of an indexed repository."""

    repo_id: str = Field(..., description="Repository ID")
    repo_name: str = Field(..., description="Repository name (owner/repo)")
    indexed_at: str = Field(..., description="When it was indexed")
    total_files: int = Field(..., description="Total files")
    primary_language: str = Field(default="Unknown", description="Primary language")


class RepoListResponse(BaseModel):
    """Response payload for repository list."""

    total: int = Field(..., description="Total number of repositories indexed")
    repos: List[RepoSummary] = Field(..., description="List of indexed repositories")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 2,
                "repos": [
                    {
                        "repo_id": "owner_repo1",
                        "repo_name": "owner/repo1",
                        "indexed_at": "2026-05-13T12:00:00.000000",
                        "total_files": 150,
                        "primary_language": "Python",
                    },
                    {
                        "repo_id": "owner_repo2",
                        "repo_name": "owner/repo2",
                        "indexed_at": "2026-05-13T11:00:00.000000",
                        "total_files": 200,
                        "primary_language": "JavaScript",
                    },
                ],
            }
        }


class RepoStatsResponse(BaseModel):
    """Response payload for repository statistics."""

    repo_id: str = Field(..., description="Repository ID")
    repo_name: str = Field(..., description="Repository name (owner/repo)")
    total_files: int = Field(..., description="Total files in repository")
    indexed_files: int = Field(..., description="Number of indexed files")
    total_chunks: int = Field(..., description="Total chunks in vector store")
    languages: Dict[str, int] = Field(
        default_factory=dict,
        description="Language distribution",
    )
    frameworks: List[str] = Field(
        default_factory=list,
        description="Detected frameworks",
    )
    indexed_at: str = Field(..., description="When it was indexed")

    class Config:
        json_schema_extra = {
            "example": {
                "repo_id": "owner_repo",
                "repo_name": "owner/repo",
                "total_files": 150,
                "indexed_files": 120,
                "total_chunks": 5000,
                "languages": {"Python": 60, "JavaScript": 30, "JSON": 10},
                "frameworks": ["FastAPI", "React"],
                "indexed_at": "2026-05-13T12:00:00.000000",
            }
        }


class HealthResponse(BaseModel):
    """Response payload for health check."""

    status: str = Field(..., description="Overall status ('ok' or 'degraded')")
    qdrant: str = Field(
        ...,
        description="Qdrant connection status ('connected' or 'disconnected')",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Health check timestamp",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "qdrant": "connected",
                "timestamp": "2026-05-13T12:34:56.000000",
            }
        }


class QdrantStatsResponse(BaseModel):
    """Response payload for Qdrant statistics."""

    connected: bool = Field(..., description="Whether connected to Qdrant")
    collections: int = Field(..., description="Number of collections")
    url: str = Field(..., description="Qdrant server URL")

    class Config:
        json_schema_extra = {
            "example": {
                "connected": True,
                "collections": 3,
                "url": "http://localhost:6333",
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response format."""

    success: bool = Field(False, description="Always false for errors")
    code: str = Field(..., description="Error code (e.g., REPO_NOT_FOUND)")
    message: str = Field(..., description="Error message")
    hint: Optional[str] = Field(
        default=None,
        description="Helpful hint for resolving the error",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "code": "REPO_NOT_FOUND",
                "message": "Repository has not been analyzed yet.",
                "hint": "Call POST /api/analyze-repo first.",
            }
        }


class SuccessResponse(BaseModel):
    """Simple success response."""

    success: bool = Field(True, description="Always true for success")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully.",
            }
        }
