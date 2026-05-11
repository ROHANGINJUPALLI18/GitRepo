"""
Local embedding service.

Generates semantic vectors for tagged chunks using a SentenceTransformer model.
The model is loaded lazily so startup stays fast.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from ..config import settings


class EmbeddingService:
    """Generate embeddings for text chunks with a local HuggingFace model."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        batch_size: Optional[int] = None,
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or settings.embedding_model_name
        self.batch_size = batch_size or settings.embedding_batch_size
        self.device = device or settings.embedding_device
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts and return vectors as plain Python lists."""
        if not texts:
            return []

        model = self._load_model()
        vectors = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=False,
        )

        return [vector.tolist() for vector in vectors]

    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Attach embeddings to each chunk dict."""
        if not chunks:
            return []

        texts = [chunk.get("text", "") for chunk in chunks]
        vectors = self.embed_texts(texts)

        embedded_chunks: List[Dict] = []
        for chunk, vector in zip(chunks, vectors):
            embedded_chunk = chunk.copy()
            embedded_chunk["embedding"] = vector
            embedded_chunk["embedding_dim"] = len(vector)
            embedded_chunks.append(embedded_chunk)

        return embedded_chunks

    def embed_chunk_groups(self, chunks_by_path: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Embed chunks grouped by file path and return the same structure."""
        return {
            file_path: self.embed_chunks(chunks)
            for file_path, chunks in chunks_by_path.items()
        }

