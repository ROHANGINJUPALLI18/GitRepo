import os
from pathlib import Path
from functools import lru_cache
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

    # Redis config
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI config
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4-turbo-preview"

    # Quadrant config
    quadrant_url: str = "http://localhost:6333"
    quadrant_api_key: str = ""

    # GitHub config
    github_token: str = ""  # Optional, for private repos later

    # Processing config
    max_repo_size_gb: float = 1.0
    max_file_size_mb: float = 10.0
    chunk_size: int = 1024
    chunk_overlap: int = 128
    search_top_k: int = 5

    # Paths
    base_path: Path = Path(__file__).parent.parent.parent
    data_path: Path = base_path / "data"
    temp_path: Path = data_path / "temp"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

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
