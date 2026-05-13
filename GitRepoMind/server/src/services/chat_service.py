"""
Chat Service for RAG orchestration.

Coordinates retrieval, prompt generation, and LLM response
to provide conversational AI repository assistance.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..config import settings
from .llm_service import LLMService
from .prompt_service import PromptService
from .search_service import SimilaritySearchService

logger = logging.getLogger(__name__)


class ChatService:
    """Main RAG orchestration layer combining search, prompt, and LLM services."""

    def __init__(
        self,
        search_service: Optional[SimilaritySearchService] = None,
        prompt_service: Optional[PromptService] = None,
        llm_service: Optional[LLMService] = None,
        default_top_k: Optional[int] = None,
    ) -> None:
        """
        Initialize the chat service.

        Args:
            search_service: Service for semantic code search
            prompt_service: Service for building RAG prompts
            llm_service: Service for LLM generation
            default_top_k: Default number of chunks to retrieve
        """
        self.search_service = search_service or SimilaritySearchService()
        self.prompt_service = prompt_service or PromptService()
        self.llm_service = llm_service or LLMService()
        self.default_top_k = default_top_k or settings.rag_top_k

    def chat(
        self,
        query: str,
        top_k: Optional[int] = None,
        repo_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main RAG chat interface.

        Retrieves relevant code chunks, builds a RAG prompt,
        sends it to the LLM, and returns a formatted response.

        Args:
            query: User's natural language question
            top_k: Number of chunks to retrieve (default: from settings)
            repo_filter: Optional repository filter for scoped search

        Returns:
            Dictionary with answer, sources, and metadata

        Raises:
            ValueError: If query is empty
            RuntimeError: If generation fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        limit = top_k or self.default_top_k

        logger.info(f"Chat request: query='{query[:100]}...' top_k={limit}")

        try:
            # Step 1: Retrieve relevant code chunks
            logger.info("Step 1: Retrieving relevant code chunks...")
            search_results = self.search_service.search(
                query=query,
                top_k=limit,
                repo_filter=repo_filter,
            )

            chunks = search_results.get("results", [])
            retrieved_count = len(chunks)

            if retrieved_count == 0:
                logger.warning("No chunks retrieved for query")

            logger.info(f"Retrieved {retrieved_count} chunks")

            # Step 2: Build RAG prompt
            logger.info("Step 2: Building RAG prompt...")
            rag_prompt = self.prompt_service.build_rag_prompt(query, chunks)

            logger.info(
                f"RAG prompt built: {len(rag_prompt)} chars, "
                f"{retrieved_count} chunks"
            )

            # Step 3: Generate response from LLM
            logger.info("Step 3: Generating LLM response...")
            answer = self.llm_service.generate_response(rag_prompt)

            logger.info(f"Response generated: {len(answer)} chars")

            # Step 4: Extract citations and format response
            logger.info("Step 4: Extracting citations...")
            citations = self._extract_citations(chunks)

            response = {
                "success": True,
                "query": query,
                "answer": answer,
                "sources": citations,
                "chunks_used": retrieved_count,
                "chunks_metadata": [
                    {
                        "file_path": chunk.get("file_path"),
                        "start_line": chunk.get("start_line"),
                        "end_line": chunk.get("end_line"),
                        "language": chunk.get("language"),
                        "score": chunk.get("score"),
                    }
                    for chunk in chunks
                ],
            }

            logger.info(f"Chat completed successfully. Citations: {len(citations)}")

            return response

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
            }
        except RuntimeError as e:
            logger.error(f"Generation failed: {e}")
            return {
                "success": False,
                "error": f"Failed to generate response: {e}",
                "query": query,
                "chunks_used": retrieved_count if "chunks" in locals() else 0,
            }
        except Exception as e:
            logger.error(f"Unexpected error during chat: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"An unexpected error occurred: {e}",
                "query": query,
            }

    def _extract_citations(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """
        Extract unique source file citations from chunks.

        Removes duplicates and preserves relevance ordering.

        Args:
            chunks: List of retrieved chunks with metadata

        Returns:
            List of unique source file paths
        """
        seen = set()
        citations = []

        for chunk in chunks:
            file_path = chunk.get("file_path")

            if file_path and file_path not in seen:
                seen.add(file_path)
                citations.append(file_path)

        return citations

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of all RAG components.

        Returns:
            Dictionary with health status of each component
        """
        return {
            "search_service": "healthy",  # TODO: Add actual health check
            "llm_service": self.llm_service.health_check(),
            "prompt_service": "healthy",  # Stateless service
        }
