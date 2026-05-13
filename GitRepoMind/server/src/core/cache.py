"""In-memory cache for repository analysis results."""

import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime


class RepoCache:
    """Simple in-memory cache for storing analysis results."""

    _store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def generate_repo_id(cls, owner: str, repo_name: str) -> str:
        """Generate a stable repository ID from owner and repo name.
        
        Args:
            owner: GitHub repository owner
            repo_name: GitHub repository name
            
        Returns:
            Stable repo_id in format "owner_repo"
        """
        return f"{owner}_{repo_name}".lower()

    @classmethod
    def set(cls, repo_id: str, data: Dict[str, Any]) -> None:
        """Store repository analysis data in cache.
        
        Args:
            repo_id: Unique repository identifier
            data: Analysis data to store
        """
        cls._store[repo_id] = {
            **data,
            "cached_at": datetime.utcnow().isoformat(),
        }

    @classmethod
    def get(cls, repo_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve repository analysis data from cache.
        
        Args:
            repo_id: Unique repository identifier
            
        Returns:
            Cached data or None if not found
        """
        return cls._store.get(repo_id)

    @classmethod
    def exists(cls, repo_id: str) -> bool:
        """Check if repository exists in cache.
        
        Args:
            repo_id: Unique repository identifier
            
        Returns:
            True if repository is in cache, False otherwise
        """
        return repo_id in cls._store

    @classmethod
    def delete(cls, repo_id: str) -> bool:
        """Remove repository from cache.
        
        Args:
            repo_id: Unique repository identifier
            
        Returns:
            True if deleted, False if not found
        """
        if repo_id in cls._store:
            del cls._store[repo_id]
            return True
        return False

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """Get summaries of all cached repositories.
        
        Returns:
            List of repository summaries with repo_id, repo_name, indexed_at, total_files
        """
        summaries = []
        for repo_id, data in cls._store.items():
            summaries.append({
                "repo_id": repo_id,
                "repo_name": data.get("repo_name", "Unknown"),
                "indexed_at": data.get("indexed_at", data.get("cached_at", "")),
                "total_files": data.get("total_files", 0),
                "primary_language": cls._get_primary_language(data),
            })
        return summaries

    @classmethod
    def clear(cls) -> None:
        """Clear all cached repositories."""
        cls._store.clear()

    @classmethod
    def _get_primary_language(cls, data: Dict[str, Any]) -> str:
        """Extract primary language from language_info dict.
        
        Args:
            data: Repository analysis data
            
        Returns:
            Primary language or "Unknown"
        """
        language_info = data.get("language_info", {})
        if not language_info:
            return "Unknown"
        
        # Get the language with the highest count
        if isinstance(language_info, dict):
            primary = max(language_info.items(), key=lambda x: x[1], default=("Unknown", 0))
            return primary[0]
        
        return "Unknown"
