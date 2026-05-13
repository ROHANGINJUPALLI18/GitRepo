"""In-memory conversation history store."""

from typing import Dict, List, Optional
from datetime import datetime


class ConversationStore:
    """Store and retrieve conversation history."""

    _store: Dict[str, List[Dict[str, str]]] = {}

    @classmethod
    def add_message(
        cls,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[str]] = None,
    ) -> None:
        """
        Add a message to the conversation history.

        Args:
            session_id: Conversation session ID
            role: Message role ('user' or 'assistant')
            content: Message content
            sources: Optional list of source references (for assistant messages)
        """
        if session_id not in cls._store:
            cls._store[session_id] = []

        message = {
            "role": role,
            "content": content,
            "sources": sources or [],
            "timestamp": datetime.utcnow().isoformat(),
        }
        cls._store[session_id].append(message)

    @classmethod
    def get_history(cls, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for a session.

        Args:
            session_id: Conversation session ID

        Returns:
            List of messages in the conversation
        """
        return cls._store.get(session_id, [])

    @classmethod
    def clear_history(cls, session_id: str) -> bool:
        """
        Clear conversation history for a session.

        Args:
            session_id: Conversation session ID

        Returns:
            True if history was cleared, False if session not found
        """
        if session_id in cls._store:
            del cls._store[session_id]
            return True
        return False

    @classmethod
    def exists(cls, session_id: str) -> bool:
        """
        Check if a conversation session exists.

        Args:
            session_id: Conversation session ID

        Returns:
            True if session has messages, False otherwise
        """
        return session_id in cls._store and len(cls._store[session_id]) > 0
