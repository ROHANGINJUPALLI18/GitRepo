"""
Metadata Tagger Service

Attaches rich context metadata to every chunk for RAG retrieval.
Metadata includes repo info, language, file type, entry points, etc.
"""

import os
from typing import Dict, List, Optional, Set


class MetadataTagger:
    """Tags chunks with contextual metadata for RAG retrieval."""

    # Language detection from file extension
    EXTENSION_TO_LANGUAGE = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript (React)",
        ".jsx": "JavaScript (React)",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".md": "Markdown",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".sh": "Shell",
        ".bat": "Batch",
        ".tf": "Terraform",
        ".sql": "SQL",
    }

    # File type detection patterns
    TEST_PATTERNS = {"test", "__test", "spec", "e2e", ".test.", ".spec."}
    CONFIG_PATTERNS = {"config", "settings", ".env", "dockerfile", "makefile"}

    @staticmethod
    def _detect_language(file_path: str) -> str:
        """Detect language from file extension."""
        _, ext = os.path.splitext(file_path)
        return MetadataTagger.EXTENSION_TO_LANGUAGE.get(ext.lower(), "Unknown")

    @staticmethod
    def _detect_file_type(file_path: str) -> str:
        """
        Detect file type: source_code, documentation, config, or test.
        """
        path_lower = file_path.lower()

        # Check test patterns first
        for pattern in MetadataTagger.TEST_PATTERNS:
            if pattern in path_lower:
                return "test"

        # Check for documentation
        doc_exts = {".md", ".markdown", ".txt", ".rst"}
        doc_names = {"readme", "changelog", "contributing", "license", "install"}
        _, ext = os.path.splitext(path_lower)
        if ext in doc_exts or any(doc_name in path_lower for doc_name in doc_names):
            return "documentation"

        # Check for config files
        config_exts = {".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".config"}
        if ext in config_exts or any(cfg in path_lower for cfg in MetadataTagger.CONFIG_PATTERNS):
            return "config"

        # Default to source_code
        return "source_code"

    @staticmethod
    def _extract_folder(file_path: str) -> str:
        """Extract the immediate parent folder from file path."""
        parts = file_path.replace("\\", "/").split("/")
        if len(parts) > 1:
            return parts[-2]
        return "root"

    @staticmethod
    def _is_entry_point(file_path: str, entry_points: Optional[Set[str]] = None) -> bool:
        """Check if file is an entry point."""
        if not entry_points:
            return False
        normalized_path = file_path.replace("\\", "/").strip("/").lower()
        return any(ep.lower() in normalized_path for ep in entry_points)

    @staticmethod
    def tag_chunks(
        chunks: List[Dict],
        file_path: str,
        repo_info: Dict,
        entry_points: Optional[Set[str]] = None,
    ) -> List[Dict]:
        """
        Attach metadata to chunks.

        Args:
            chunks: List of chunk dicts from chunking_service.chunk_text()
            file_path: Original file path (e.g., "src/auth/login.py")
            repo_info: Dict with keys "owner", "repo", "branch"
            entry_points: Set of entry point file names/patterns

        Returns:
            List of chunks with "metadata" dict attached to each
        """
        if not chunks:
            return []

        # Detect metadata once per file (not per chunk)
        language = MetadataTagger._detect_language(file_path)
        file_type = MetadataTagger._detect_file_type(file_path)
        folder = MetadataTagger._extract_folder(file_path)
        is_entry_point = MetadataTagger._is_entry_point(file_path, entry_points)
        repo_full_name = f"{repo_info.get('owner', 'unknown')}/{repo_info.get('repo', 'unknown')}"

        # Attach metadata to each chunk
        tagged_chunks = []
        total_chunks = len(chunks)
        for chunk in chunks:
            tagged_chunk = chunk.copy()
            tagged_chunk["metadata"] = {
                "file_path": file_path,
                "language": language,
                "chunk_index": chunk.get("chunk_index", 0),
                "total_chunks": total_chunks,
                "file_type": file_type,
                "repo": repo_full_name,
                "branch": repo_info.get("branch", "main"),
                "is_entry_point": is_entry_point,
                "folder": folder,
            }
            tagged_chunks.append(tagged_chunk)

        return tagged_chunks


def tag_all_chunks(
    all_chunks_by_path: Dict[str, List[Dict]],
    repo_info: Dict,
    entry_points: Optional[Set[str]] = None,
) -> Dict[str, List[Dict]]:
    """
    Convenience function to tag all chunks in a batch.

    Args:
        all_chunks_by_path: Dict mapping file paths to chunk lists
        repo_info: Repository context
        entry_points: Set of entry point patterns

    Returns:
        Same structure with metadata attached to all chunks
    """
    result = {}
    for file_path, chunks in all_chunks_by_path.items():
        result[file_path] = MetadataTagger.tag_chunks(
            chunks, file_path, repo_info, entry_points
        )
    return result
