"""FastAPI routes for RAG chat interface."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from ..core.cache import RepoCache
from ..models.request import ChatRequest
from ..models.response import ChatResponse, HistoryResponse, ChatMessage
from ..services.conversation_store import ConversationStore
from ..services.chat_service import ChatService
from ..services.search_service import SimilaritySearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat with the RAG-powered repository assistant.

    Retrieves relevant code chunks from the indexed repository,
    generates a RAG prompt, and uses an LLM to provide a conversational answer.

    Args:
        request: Chat request with repo_id, query, and optional session_id

    Returns:
        Chat response with answer and sources

    Raises:
        HTTPException: If repo not found or chat generation fails
    """
    try:
        # Validate repository exists
        if not RepoCache.exists(request.repo_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "code": "REPO_NOT_FOUND",
                    "message": "Repository has not been analyzed yet.",
                    "hint": "Call POST /api/analyze-repo first.",
                },
            )

        # Validate query is not empty
        if not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "code": "EMPTY_QUERY",
                    "message": "Query cannot be empty.",
                    "hint": "Provide a non-empty question about the codebase.",
                },
            )

        logger.info(f"Chat request for repo {request.repo_id}, session {request.session_id}")

        # Get conversation history
        history = ConversationStore.get_history(request.session_id)

        # Initialize chat service and perform RAG
        chat_service = ChatService()
        
        try:
            rag_result = chat_service.chat(
                query=request.query,
                repo_filter=request.repo_id,
            )
        except Exception as e:
            logger.error(f"RAG chat error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "code": "RAG_ERROR",
                    "message": "Failed to generate response",
                    "hint": str(e),
                },
            )

        answer = rag_result.get("answer", "")
        sources = rag_result.get("sources", [])

        # Store user message in conversation history
        ConversationStore.add_message(
            session_id=request.session_id,
            role="user",
            content=request.query,
            sources=[],
        )

        # Store assistant response in conversation history
        ConversationStore.add_message(
            session_id=request.session_id,
            role="assistant",
            content=answer,
            sources=sources,
        )

        logger.info(f"Chat response generated with {len(sources)} sources")

        return ChatResponse(
            success=True,
            answer=answer,
            sources=sources,
            session_id=request.session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "CHAT_ERROR",
                "message": "Failed to process chat request",
            },
        )


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_chat_history(session_id: str) -> HistoryResponse:
    """
    Retrieve conversation history for a session.

    Args:
        session_id: Conversation session ID

    Returns:
        HistoryResponse with list of messages
    """
    try:
        history = ConversationStore.get_history(session_id)
        
        messages = [
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                sources=msg.get("sources", []),
                timestamp=msg.get("timestamp", ""),
            )
            for msg in history
        ]

        return HistoryResponse(
            session_id=session_id,
            messages=messages,
        )
    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "HISTORY_ERROR",
                "message": "Failed to retrieve conversation history",
            },
        )


@router.delete("/history/{session_id}", status_code=status.HTTP_200_OK)
async def delete_chat_history(session_id: str) -> dict:
    """
    Delete conversation history for a session.

    Args:
        session_id: Conversation session ID

    Returns:
        Success response

    Raises:
        HTTPException: If operation fails
    """
    try:
        ConversationStore.clear_history(session_id)
        logger.info(f"Cleared history for session {session_id}")
        return {"success": True, "message": f"Cleared history for session {session_id}"}
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "DELETE_ERROR",
                "message": "Failed to delete conversation history",
            },
        )
