import os
import requests
import base64
from dotenv import load_dotenv
from typing import Dict


class GitHubService:

    def __init__(self):
        load_dotenv()
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.owner = None
        self.repo_name = None

    def _get_repo_info(self, branch="main") -> Dict:
        """Build repo context dict for metadata tagging."""
        return {
            "owner": self.owner or "unknown",
            "repo": self.repo_name or "unknown",
            "branch": branch,
        }

    def _apply_index_filter(self, files):
        """Apply hardcoded file-filter rules and split files into index/skip groups."""
        from .analyze_repo import should_index_file

        to_index = []
        skipped = []
        for file in files:
            path = file.get("path", "") if isinstance(file, dict) else ""
            if should_index_file(path):
                to_index.append(file)
            else:
                skipped.append(file)
        return to_index, skipped

    def get_repo_info(self, repo_url):
        try:
            parts = repo_url.strip('/').split('/')
            self.owner = parts[-2]
            self.repo_name = parts[-1]
            print(f"Parsed repository info: Owner='{self.owner}', Repo='{self.repo_name}'")
            return self.owner, self.repo_name
        except Exception as e:
            print(f"Error parsing repository URL: {e}")
            return None, None

    def get_all_files(self, branch="main"):
        """
        Uses the Git Trees API with recursive=1 to fetch ALL files
        (including nested ones) in a single request.
        Returns a list of dicts with 'path', 'sha', 'size', etc.
        """
        if not self.owner or not self.repo_name:
            print("Error: owner and repo_name must be set before calling get_all_files().")
            return []

        api_url = (
            f"https://api.github.com/repos/{self.owner}/{self.repo_name}"
            f"/git/trees/{branch}?recursive=1"
        )
        try:
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
            tree = response.json().get("tree", [])
            # Filter only files (blobs), not directories (trees)
            files = [item for item in tree if item["type"] == "blob"]
            return files
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repository tree: {e}")
            return []

    def get_file_content(self, file_path, branch="main"):
        """
        Fetches content of a specific file by its path.
        Returns decoded string content or None for binary/failed files.
        """
        api_url = (
            f"https://api.github.com/repos/{self.owner}/{self.repo_name}"
            f"/contents/{file_path}"
        )
        try:
            response = requests.get(
                api_url,
                headers=self.headers,
                params={"ref": branch}
            )
            response.raise_for_status()
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return content
        except requests.exceptions.RequestException as e:
            print(f"Error fetching file '{file_path}': {e}")
            return None
        except UnicodeDecodeError:
            print(f"Skipping binary file: {file_path}")
            return None

    def process_repository(self, repo_url, branch="main"):
        """
        Full pipeline:
          1. Parse the URL
          2. Fetch all file paths
          3. Print file listing
                    4. Fetch, chunk, tag, and embed each file's content
                    5. Run static analysis and print report
        """
        # ── Step 1: parse URL ────────────────────────────────────────────
        owner, repo_name = self.get_repo_info(repo_url)
        if not owner or not repo_name:
            print("Invalid repository URL.")
            return

        # ── Step 2: fetch all files ──────────────────────────────────────
        print(f"\nFetching all files from '{owner}/{repo_name}' on branch '{branch}'...\n")
        all_files = self.get_all_files(branch)
        if not all_files:
            print("No files found or failed to fetch.")
            return

        files, skipped_files = self._apply_index_filter(all_files)
        print(f"Total files: {len(all_files)}")
        print(f"Files to index: {len(files)} [OK]")
        print(f"Files skipped: {len(skipped_files)} [SKIP]")

        if not files:
            print("No indexable files found.")
            return

        # ── Step 3: print file listing ───────────────────────────────────
        print(f"Found {len(files)} files:\n")
        for file in files:
            print(f"   {file['path']}")

        # ── Step 4: fetch each file's content, chunk, tag, embed, and store ──
        from .chunking_service import chunk_text, get_chunking_summary
        from .embedding_service import EmbeddingService
        from .metadata_tagger import MetadataTagger
        from .vector_store_service import QdrantVectorStore
        
        print("\n--- Fetching file contents, chunking, tagging metadata, generating embeddings, and storing in Qdrant ---\n")
        all_chunks = {}
        all_chunks_with_metadata = {}
        all_chunks_with_embeddings = {}
        entry_points = set()  # Collect entry points for metadata
        embedding_service = EmbeddingService()
        vector_store = QdrantVectorStore()
        
        for file in files:
            path = file["path"]
            print(f"\n{'=' * 60}")
            print(f"File: {path}")
            print('=' * 60)
            content = self.get_file_content(path, branch)
            if content:
                # Chunk the content for embedding
                chunks = chunk_text(content, file_path=path)
                all_chunks[path] = chunks
                
                # Tag chunks with metadata
                repo_info = self._get_repo_info(branch)
                tagged_chunks = MetadataTagger.tag_chunks(
                    chunks, path, repo_info, entry_points
                )
                all_chunks_with_metadata[path] = tagged_chunks

                embedded_chunks = embedding_service.embed_chunks(tagged_chunks)
                all_chunks_with_embeddings[path] = embedded_chunks
                
                summary = get_chunking_summary(chunks)
                print(f"Content preview (first 200 chars):\n{content[:200]}...")
                print(f"\nChunking summary: {summary['total_chunks']} chunks, {summary['total_tokens']} total tokens")
                
                # Show sample metadata from first chunk
                if tagged_chunks:
                    sample_meta = tagged_chunks[0].get("metadata", {})
                    sample_embedding = embedded_chunks[0].get("embedding", []) if embedded_chunks else []
                    print(f"\nMetadata sample: file_type={sample_meta.get('file_type')}, "
                          f"language={sample_meta.get('language')}, "
                          f"repo={sample_meta.get('repo')}")
                    print(f"Embedding sample: dim={len(sample_embedding)}")
            else:
                all_chunks[path] = []
                all_chunks_with_metadata[path] = []
                all_chunks_with_embeddings[path] = []

        # ── Step 5: store embeddings in Qdrant ───────────────────────────
        repo_full_name = f"{self.owner}/{self.repo_name}"
        try:
            stored_count = vector_store.upsert_chunks(all_chunks_with_embeddings, repo_full_name)
            print(f"\n--- Vector Storage ---")
            print(f"Stored {stored_count} chunks in Qdrant collection '{vector_store.collection_name}'")
            collection_info = vector_store.get_collection_info()
            print(f"Collection info: {collection_info['points_count']} total points")
        except Exception as e:
            print(f"Warning: Failed to store chunks in Qdrant: {e}")

        # ── Step 6: run static analysis ──────────────────────────────────
        self.analyze_git_repo(
            files,
            already_filtered=True,
            chunks=all_chunks_with_embeddings,
        )

    def analyze_git_repo(self, files=None, branch="main", already_filtered=False, chunks=None):
        """
        Runs static analysis on the fetched files.
        Accepts an already-fetched file list, or re-fetches if not provided.
        `chunks` dict maps file paths to their chunked content (optional).
        """
        # Lazy import to avoid circular dependency issues
        from .analyze_repo import analyze_repository, to_json

        if files is None:
            all_files = self.get_all_files(branch)
            files, skipped_files = self._apply_index_filter(all_files)
            print(f"Total files: {len(all_files)}")
            print(f"Files to index: {len(files)} [OK]")
            print(f"Files skipped: {len(skipped_files)} [SKIP]")
        elif not already_filtered:
            all_files = files
            files, skipped_files = self._apply_index_filter(all_files)
            print(f"Total files: {len(all_files)}")
            print(f"Files to index: {len(files)} [OK]")
            print(f"Files skipped: {len(skipped_files)} [SKIP]")

        if not files:
            print("No files to analyze.")
            return

        # analyze_repository() expects plain path strings, not full dicts
        paths = [f["path"] for f in files if isinstance(f, dict) and f.get("path")]

        print("\n\n" + "=" * 60)
        print("       STATIC ANALYSIS REPORT")
        print("=" * 60)

        result = analyze_repository(paths)
        print(to_json(result))
        return result


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    github_service = GitHubService()
    repo_url = input("Enter the GitHub repository URL: ").strip()
    branch = input("Enter branch name (default: main): ").strip() or "main"
    github_service.process_repository(repo_url, branch)