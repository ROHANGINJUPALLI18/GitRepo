"""
Qdrant Vector Store Service

Stores embeddings + metadata + text in Qdrant for fast semantic retrieval.
"""

from typing import Dict, List, Optional
from uuid import uuid4
import hashlib

from ..config import settings


class QdrantVectorStore:
    """Store and retrieve embeddings in Qdrant."""

    def __init__(
        self,
        collection_name: str = "gitrepomind_chunks",
        vector_dim: int = 384,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize Qdrant connection."""
        self.collection_name = collection_name
        self.vector_dim = vector_dim
        self.url = url or settings.quadrant_url
        self.api_key = api_key or settings.quadrant_api_key

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self.client = QdrantClient(url=self.url, api_key=self.api_key if self.api_key else None)
            self.Distance = Distance
            self.VectorParams = VectorParams
            self._ensure_collection_exists()
        except ImportError:
            raise ImportError("qdrant-client is required for vector storage. Install with: pip install qdrant-client")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Qdrant at {self.url}: {e}")

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            # Collection doesn't exist, create it
            try:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=self.VectorParams(
                        size=self.vector_dim,
                        distance=self.Distance.COSINE,
                    ),
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create collection {self.collection_name}: {e}"
                )

    def _generate_point_id(self, repo_name: str, file_path: str, chunk_index: int) -> int:
        """Generate a stable, unique point ID from repo, file, and chunk index."""
        key = f"{repo_name}#{file_path}#{chunk_index}"
        hash_digest = hashlib.md5(key.encode()).hexdigest()
        # Convert hex to int, modulo to fit in unsigned 64-bit
        return int(hash_digest, 16) % (2**63 - 1)

    def upsert_chunks(
        self,
        chunks_by_path: Dict[str, List[Dict]],
        repo_name: str,
    ) -> int:
        """
        Store all chunks (with embeddings and metadata) in Qdrant.

        Args:
            chunks_by_path: Dict mapping file paths to list of chunk dicts
            repo_name: Repository identifier (e.g., "owner/repo")

        Returns:
            Number of chunks stored
        """
        try:
            from qdrant_client.models import PointStruct

            points = []
            chunk_count = 0

            for file_path, chunks in chunks_by_path.items():
                for chunk in chunks:
                    embedding = chunk.get("embedding")
                    if not embedding:
                        # Skip chunks without embeddings
                        continue

                    chunk_index = chunk.get("chunk_index", 0)
                    point_id = self._generate_point_id(repo_name, file_path, chunk_index)

                    # Build payload with all chunk data
                    payload = {
                        "file_path": file_path,
                        "text": chunk.get("text", ""),
                        "chunk_index": chunk_index,
                        "start_line": chunk.get("start_line"),
                        "end_line": chunk.get("end_line"),
                        "tokens": chunk.get("tokens", 0),
                        "embedding_dim": chunk.get("embedding_dim", self.vector_dim),
                        "repo": repo_name,
                    }

                    # Merge metadata if present
                    if "metadata" in chunk:
                        payload.update(chunk["metadata"])

                    point = PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                    points.append(point)
                    chunk_count += 1

            # Batch upsert all points
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )

            return chunk_count

        except Exception as e:
            raise RuntimeError(f"Failed to upsert chunks to Qdrant: {e}")

    def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 5,
        repo_filter: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search for semantically similar chunks.

        Args:
            query_vector: 384-dimensional embedding vector
            top_k: Number of results to return
            repo_filter: Optional repo name to filter results

        Returns:
            List of results with payload and similarity score
        """
        try:
            # Apply repo filter if specified
            query_filter = None
            if repo_filter:
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="repo",
                            match=MatchValue(value=repo_filter),
                        )
                    ]
                )

            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
            )

            # Convert results to plain dicts (results is a QueryResponse with .points list)
            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "file_path": result.payload.get("file_path"),
                    "text": result.payload.get("text"),
                    "payload": dict(result.payload),
                }
                for result in results.points
            ]

        except Exception as e:
            raise RuntimeError(f"Search failed: {e}")

    def delete_repo(self, repo_name: str) -> int:
        """Delete all chunks for a repository."""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Create filter for repo
            repo_filter = Filter(
                must=[
                    FieldCondition(
                        key="repo",
                        match=MatchValue(value=repo_name),
                    )
                ]
            )

            # Count before deletion
            points = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=repo_filter,
                limit=1,
            )[0]
            count_before = len(points) if points else 0

            # Delete
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=repo_filter,
            )

            return count_before

        except Exception as e:
            raise RuntimeError(f"Failed to delete repo {repo_name}: {e}")

    def get_collection_info(self) -> Dict:
        """Get collection stats."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": getattr(collection_info, "vectors_count", collection_info.points_count),
                "indexed_vectors_count": getattr(
                    collection_info, "indexed_vectors_count", collection_info.points_count
                ),
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get collection info: {e}")
