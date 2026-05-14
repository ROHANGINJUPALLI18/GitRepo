import http
import os
from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App config
    app_name: str = "GitRepoMind"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server config
    host: str = "0.0.0.0"
    port: int = 8000

    # Database config
    database_url: str = "postgresql://postgres:password@localhost:5432/gitrepomind"

    # Celery config
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # OpenAI config
    openai_api_key: str = ""

    # Local embedding config
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 16
    embedding_device: str = "cpu"
    embedding_dimension: int = 384

    # Qdrant config (vector database)
    quadrant_url: str = Field(default="http://localhost:6333", validation_alias="QDRANT_URL")
    quadrant_api_key: str = Field(default="", validation_alias="QDRANT_API_KEY")
    qdrant_collection_name: str = "gitrepomind_chunks"
    qdrant_vector_dim: int = 384

    # GitHub config
    github_token: str = ""  # Optional, for private repos later

    # Processing config
    max_repo_size_gb: float = 1.0
    max_file_size_mb: float = 10.0
    chunk_size: int = 1024
    chunk_overlap: int = 128
    search_top_k: int = 5

    # Ollama config
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_temperature: float = 0.2
    ollama_top_p: float = 0.9
    ollama_timeout: int = 60

    # RAG config
    rag_top_k: int = 5
    rag_max_context_chars: int = 12000
    rag_chunk_separator: str = "\n---\n"

    # Paths
    base_path: Path = Path(__file__).parent.parent.parent
    data_path: Path = base_path / "data"
    temp_path: Path = data_path / "temp"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    def __init__(self, **kwargs):
        """Initialize settings and create necessary directories."""
        super().__init__(**kwargs)
        # Create data and temp directories if they don't exist
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export for easy import
settings = get_settings()
