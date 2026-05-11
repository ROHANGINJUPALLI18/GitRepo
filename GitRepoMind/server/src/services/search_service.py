"""Semantic query service for retrieving relevant chunks from Qdrant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..config import settings

from .embedding_service import EmbeddingService
from .vector_store_service import QdrantVectorStore


class SimilaritySearchService:
    """Embed a user query and return the most relevant stored chunks."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[QdrantVectorStore] = None,
        default_top_k: Optional[int] = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or QdrantVectorStore()
        self.default_top_k = default_top_k or settings.search_top_k

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        repo_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for the most relevant chunks for a natural-language query."""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Query cannot be empty.")

        limit = top_k or self.default_top_k
        query_vector = self.embedding_service.embed_texts([normalized_query])[0]
        results = self.vector_store.search_similar(
            query_vector=query_vector,
            top_k=limit,
            repo_filter=repo_filter,
        )

        return {
            "query": normalized_query,
            "top_k": limit,
            "repo_filter": repo_filter,
            "count": len(results),
            "results": self._format_results(results),
        }

    def _format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted_results: List[Dict[str, Any]] = []

        for rank, result in enumerate(results, start=1):
            payload = result.get("payload", {})
            text = payload.get("text", "")

            formatted_results.append(
                {
                    "rank": rank,
                    "score": result.get("score", 0.0),
                    "file_path": result.get("file_path") or payload.get("file_path"),
                    "chunk_index": payload.get("chunk_index"),
                    "start_line": payload.get("start_line"),
                    "end_line": payload.get("end_line"),
                    "tokens": payload.get("tokens"),
                    "repo": payload.get("repo"),
                    "branch": payload.get("branch"),
                    "language": payload.get("language"),
                    "file_type": payload.get("file_type"),
                    "folder": payload.get("folder"),
                    "is_entry_point": payload.get("is_entry_point"),
                    "text": text,
                    "snippet": self._build_snippet(text),
                    "payload": payload,
                }
            )

        return formatted_results

    @staticmethod
    def _build_snippet(text: str, max_length: int = 240) -> str:
        """Create a compact preview string for UI and API responses."""
        cleaned = " ".join(text.split())
        if len(cleaned) <= max_length:
            return cleaned
        return f"{cleaned[: max_length - 3]}..."