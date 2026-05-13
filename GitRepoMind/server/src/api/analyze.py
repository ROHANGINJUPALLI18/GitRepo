"""FastAPI routes for repository analysis pipeline."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from ..core.cache import RepoCache
from ..models.request import AnalyzeRequest, ReindexRequest
from ..models.response import AnalyzeResponse
from ..services.github_service import GitHubService
from ..services.analyze_repo import analyze_repository as build_analysis_report
from ..services.chunking_service import ChunkingService
from ..services.metadata_tagger import MetadataTagger, tag_all_chunks
from ..services.embedding_service import EmbeddingService
from ..services.vector_store_service import QdrantVectorStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analyze"])


@router.post(
    "/analyze-repo",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_repository(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze a GitHub repository and prepare it for RAG queries.

    This endpoint performs the following steps:
    1. Parses the GitHub repository URL
    2. Checks cache for existing analysis
    3. Fetches all files from the repository
    4. Analyzes static repository structure
    5. Chunks files into semantic units
    6. Tags chunks with metadata
    7. Generates embeddings
    8. Stores vectors in Qdrant
    9. Caches the analysis result

    Args:
        request: AnalyzeRequest with repo_url and optional branch

    Returns:
        AnalyzeResponse with success status, repo_id, and analysis details

    Raises:
        HTTPException: For invalid URLs, GitHub errors, or processing failures
    """
    try:
        # Step 1: Parse repo URL
        logger.info(f"Analyzing repository: {request.repo_url}")
        github_service = GitHubService()
        owner, repo_name = github_service.get_repo_info(request.repo_url)

        if not owner or not repo_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "code": "INVALID_REPO_URL",
                    "message": "Invalid GitHub repository URL format",
                    "hint": "Use format: https://github.com/owner/repo",
                },
            )

        # Generate repo_id
        repo_id = RepoCache.generate_repo_id(owner, repo_name)
        repo_full_name = f"{owner}/{repo_name}"

        # Step 2: Check cache
        if not request.force_reindex and RepoCache.exists(repo_id):
            logger.info(f"Repository {repo_id} already cached, returning cached result")
            cached = RepoCache.get(repo_id)
            return AnalyzeResponse(**cached)

        # Step 3: Fetch all files
        logger.info(f"Fetching files from {request.branch} branch")
        files = github_service.get_all_files(request.branch)
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "code": "BRANCH_NOT_FOUND",
                    "message": f"Branch '{request.branch}' not found or is empty",
                    "hint": "Check that the branch exists and the repository is not empty",
                },
            )

        logger.info(f"Found {len(files)} files in repository")

        # Step 4: Fetch file contents for indexable files
        logger.info("Fetching file contents")
        files_with_content = []
        for file in files:
            file_path = file.get("path", "")
            
            # Skip binary and non-code files
            if _should_skip_file(file_path):
                continue
            
            try:
                content = github_service.get_file_content(file_path, request.branch)
                if content:
                    files_with_content.append({
                        "path": file_path,
                        "content": content,
                        "sha": file.get("sha"),
                        "size": file.get("size", 0),
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch {file_path}: {str(e)}")
                continue

        if not files_with_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "code": "NO_INDEXABLE_FILES",
                    "message": "No indexable files found in repository",
                    "hint": "Ensure repository contains text files",
                },
            )

        logger.info(f"Successfully fetched content for {len(files_with_content)} files")

        # Step 5: Run static analysis
        logger.info("Running static analysis")
        file_paths = [f["path"] for f in files_with_content]
        analysis = build_analysis_report(file_paths)

        # Step 6: Chunk files
        logger.info("Chunking files")
        chunking_service = ChunkingService()
        chunks_by_path = {}
        for file_data in files_with_content:
            file_path = file_data.get("path", "")
            content = file_data.get("content", "")
            file_chunks = chunking_service.chunk_files([{"path": file_path, "content": content}])
            if file_chunks:
                chunks_by_path[file_path] = file_chunks
        
        all_chunks = []
        for chunks in chunks_by_path.values():
            all_chunks.extend(chunks)
        logger.info(f"Created {len(all_chunks)} chunks")

        # Step 7: Tag chunks with metadata
        logger.info("Tagging chunks with metadata")
        repo_info = {
            "owner": owner,
            "repo": repo_name,
            "repo_id": repo_id,
            "branch": request.branch,
        }
        # Extract entry point file paths from analysis output
        entry_points = [
            entry["file"]
            for entry in analysis.get("entry_points", [])
            if isinstance(entry, dict) and entry.get("file")
        ]
        entry_point_set = set(entry_points)
        tagged_chunks_by_path = tag_all_chunks(
            chunks_by_path, repo_info, entry_point_set
        )
        # Flatten back to single list for embedding
        tagged_chunks = []
        for chunks in tagged_chunks_by_path.values():
            tagged_chunks.extend(chunks)

        # Step 8: Generate embeddings
        logger.info("Generating embeddings")
        embedding_service = EmbeddingService()
        chunks_with_embeddings = embedding_service.embed_chunks(tagged_chunks)

        # Step 9: Store in Qdrant
        logger.info("Storing vectors in Qdrant")
        vector_store = QdrantVectorStore()
        # Group chunks by file path for upsert
        chunks_by_path_for_upsert = {}
        for chunk in chunks_with_embeddings:
            file_path = chunk.get("path", "unknown")
            if file_path not in chunks_by_path_for_upsert:
                chunks_by_path_for_upsert[file_path] = []
            chunks_by_path_for_upsert[file_path].append(chunk)
        
        # Use stable repo_id when storing vectors to allow filtering by repo_id
        chunk_count = vector_store.upsert_chunks(
            chunks_by_path_for_upsert,
            repo_id,
        )
        logger.info(f"Stored {chunk_count} chunks in Qdrant")

        # Step 10: Build and cache response
        response_data = {
            "success": True,
            "repo_id": repo_id,
            "repo_name": repo_full_name,
            "total_files": len(files),
            "indexed_files": len(files_with_content),
            "language_info": analysis.get("language_info", {}),
            "entry_points": entry_points,
            "architecture": analysis.get("architecture", {}),
            "readme_overview": analysis.get("readme_overview", ""),
            "indexed_at": datetime.utcnow().isoformat(),
        }

        RepoCache.set(repo_id, response_data)
        logger.info(f"Repository {repo_id} analysis completed and cached")

        return AnalyzeResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing repository: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "ANALYSIS_ERROR",
                "message": "Failed to analyze repository",
                "hint": f"Error: {str(e)}",
            },
        )


@router.post("/reindex", response_model=AnalyzeResponse)
async def reindex_repository(request: ReindexRequest) -> AnalyzeResponse:
    """
    Re-analyze a GitHub repository, discarding cached data.

    This endpoint forces a fresh analysis of a repository:
    1. Deletes existing vectors from Qdrant
    2. Clears cached analysis
    3. Runs the full analysis pipeline

    Args:
        request: ReindexRequest with repo_url and optional branch

    Returns:
        Fresh AnalyzeResponse with new analysis data

    Raises:
        HTTPException: For invalid URLs or processing failures
    """
    try:
        logger.info(f"Reindexing repository: {request.repo_url}")
        
        # Parse repo URL
        github_service = GitHubService()
        owner, repo_name = github_service.get_repo_info(request.repo_url)

        if not owner or not repo_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "code": "INVALID_REPO_URL",
                    "message": "Invalid GitHub repository URL format",
                    "hint": "Use format: https://github.com/owner/repo",
                },
            )

        repo_id = RepoCache.generate_repo_id(owner, repo_name)
        repo_full_name = f"{owner}/{repo_name}"

        # Delete from vector store
        logger.info(f"Deleting vectors for {repo_id}")
        try:
            vector_store = QdrantVectorStore()
            vector_store.delete_repo(repo_full_name)
        except Exception as e:
            logger.warning(f"Failed to delete vectors: {str(e)}")

        # Clear from cache
        RepoCache.delete(repo_id)
        logger.info(f"Cleared cache for {repo_id}")

        # Re-run full analysis with force_reindex=True
        analyze_request = AnalyzeRequest(
            repo_url=request.repo_url,
            branch=request.branch,
            force_reindex=True,
        )
        return await analyze_repository(analyze_request)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reindexing repository: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "REINDEX_ERROR",
                "message": "Failed to reindex repository",
                "hint": str(e),
            },
        )


@router.get("/analysis/{repo_id}", response_model=AnalyzeResponse)
async def get_analysis(repo_id: str) -> AnalyzeResponse:
    """
    Retrieve cached analysis for a repository.

    Args:
        repo_id: Repository ID returned from analyze-repo endpoint

    Returns:
        Cached AnalyzeResponse

    Raises:
        HTTPException: If repository not found
    """
    try:
        cached = RepoCache.get(repo_id)
        if not cached:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "code": "REPO_NOT_FOUND",
                    "message": "Repository has not been analyzed yet.",
                    "hint": "Call POST /api/analyze-repo first.",
                },
            )
        return AnalyzeResponse(**cached)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "code": "RETRIEVAL_ERROR",
                "message": "Failed to retrieve analysis",
            },
        )


def _should_skip_file(file_path: str) -> bool:
    """
    Determine if a file should be skipped during analysis.

    Skips binary files, images, compiled code, and other non-code files.

    Args:
        file_path: Path to the file

    Returns:
        True if file should be skipped, False if it should be indexed
    """
    skip_extensions = {
        # Binary formats
        ".bin", ".exe", ".dll", ".so", ".dylib", ".o",
        # Images
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
        # Archives
        ".zip", ".tar", ".gz", ".rar", ".7z",
        # Videos
        ".mp4", ".avi", ".mov", ".mkv", ".flv",
        # Audio
        ".mp3", ".wav", ".flac", ".aac", ".ogg",
        # Compiled/Generated
        ".pyc", ".pyo", ".class", ".jar",
        # Dependencies
        ".lock",
    }
    
    skip_dirs = {
        ".git", ".github", "node_modules", ".venv", "venv", 
        "dist", "build", "__pycache__", ".pytest_cache",
        ".vscode", ".idea", "target", "vendor",
    }
    
    file_path_lower = file_path.lower()
    
    # Check extension
    for ext in skip_extensions:
        if file_path_lower.endswith(ext):
            return True
    
    # Check directories
    parts = file_path.split("/")
    for part in parts:
        if part in skip_dirs:
            return True
    
    return False
