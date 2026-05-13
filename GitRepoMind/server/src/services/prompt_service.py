"""
Prompt Service for building high-quality RAG prompts.

Combines user queries with retrieved code chunks and metadata
to create structured prompts that reduce hallucinations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..config import settings

logger = logging.getLogger(__name__)


class PromptService:
    """Build RAG prompts that combine context with user queries."""

    def __init__(
        self,
        max_context_chars: Optional[int] = None,
        chunk_separator: Optional[str] = None,
    ) -> None:
        """
        Initialize the prompt service.

        Args:
            max_context_chars: Maximum characters for context (default: from settings)
            chunk_separator: Separator between chunks (default: from settings)
        """
        self.max_context_chars = max_context_chars or settings.rag_max_context_chars
        self.chunk_separator = chunk_separator or settings.rag_chunk_separator

    def build_rag_prompt(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
    ) -> str:
        """
        Build a structured RAG prompt from query and code chunks.

        Args:
            query: User's natural language query
            chunks: List of retrieved code chunks with metadata

        Returns:
            Formatted prompt ready for LLM

        Raises:
            ValueError: If query is empty
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not chunks:
            return self._build_empty_context_prompt(query)

        # Format chunks with metadata
        formatted_chunks = self._format_chunks(chunks)
        context_text = self._build_context_section(formatted_chunks)

        # Build the final prompt
        prompt = f"""You are an expert AI repository assistant.

Your role is to answer technical questions about the codebase ONLY using the provided repository context.

User Question:
{query}

Repository Context:
{context_text}

Instructions:
- Answer ONLY using the provided repository context
- Be accurate and technical
- Mention source files and line numbers when relevant
- If the context doesn't contain the answer, explicitly say "The information is not available in the provided context"
- Provide concise but thorough explanations
- Do not make up or hallucinate information
- Format code examples clearly with language markers

Answer:"""

        logger.info(
            f"Built RAG prompt: {len(prompt)} chars, {len(chunks)} chunks, "
            f"context: {len(context_text)} chars"
        )

        return prompt

    def _format_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Format chunks for prompt insertion with proper metadata.

        Args:
            chunks: Raw chunks from vector search

        Returns:
            Formatted chunks with required fields
        """
        formatted = []

        for chunk in chunks:
            # Handle both direct fields and payload nesting
            if isinstance(chunk, dict):
                file_path = chunk.get("file_path") or chunk.get("payload", {}).get(
                    "file_path"
                )
                text = chunk.get("text") or chunk.get("payload", {}).get("text")
                start_line = chunk.get("start_line") or chunk.get("payload", {}).get(
                    "start_line"
                )
                end_line = chunk.get("end_line") or chunk.get("payload", {}).get(
                    "end_line"
                )
                language = chunk.get("language") or chunk.get("payload", {}).get(
                    "language"
                )
                score = chunk.get("score", 0.0)

                formatted.append(
                    {
                        "file_path": file_path,
                        "text": text,
                        "start_line": start_line,
                        "end_line": end_line,
                        "language": language,
                        "score": score,
                        "original": chunk,
                    }
                )

        # Sort by relevance score descending
        formatted.sort(key=lambda x: x["score"], reverse=True)

        return formatted

    def _build_context_section(
        self,
        formatted_chunks: List[Dict[str, Any]],
    ) -> str:
        """
        Build the context section with proper formatting and truncation.

        Args:
            formatted_chunks: List of formatted chunks

        Returns:
            Context text for the prompt
        """
        context_parts = []
        current_length = 0

        for chunk in formatted_chunks:
            file_path = chunk["file_path"] or "unknown"
            start_line = chunk["start_line"] or "?"
            end_line = chunk["end_line"] or "?"
            text = chunk["text"] or ""
            language = chunk["language"] or "text"

            # Build chunk header
            chunk_header = (
                f"\nFile: {file_path}\n"
                f"Lines: {start_line}-{end_line}\n"
                f"Language: {language}\n"
            )

            # Truncate text if needed
            max_chunk_length = self.max_context_chars // max(len(formatted_chunks), 1)
            if len(text) > max_chunk_length:
                text = text[:max_chunk_length] + "..."

            chunk_text = f"{chunk_header}\n```{language}\n{text}\n```"

            chunk_length = len(chunk_text)
            if current_length + chunk_length > self.max_context_chars:
                # Stop adding chunks if we exceed limit
                logger.info(
                    f"Context truncated at {len(context_parts)} chunks "
                    f"({current_length} chars)"
                )
                break

            context_parts.append(chunk_text)
            current_length += chunk_length

        return self.chunk_separator.join(context_parts)

    def _build_empty_context_prompt(self, query: str) -> str:
        """
        Build a prompt when no context is available.

        Args:
            query: User's natural language query

        Returns:
            Prompt indicating lack of context
        """
        return f"""You are an expert AI repository assistant.

Unfortunately, no relevant code context was found for your question.

User Question:
{query}

Instructions:
- There is no repository context available to answer this question
- Explicitly state that the information is not available in the indexed code
- Do not make up or hallucinate information
- Suggest what information might help answer the question

Answer:"""

    def truncate_context(self, text: str, max_length: int) -> str:
        """
        Safely truncate text while preserving meaning.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        truncated = text[:max_length]

        # Try to cut at word boundary
        last_newline = truncated.rfind("\n")
        if last_newline > max_length * 0.8:
            truncated = truncated[:last_newline]

        return truncated + "..."
