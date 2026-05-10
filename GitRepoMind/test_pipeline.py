#!/usr/bin/env python
"""
Test the full GitRepoMind pipeline with a real GitHub repository.
Uses a public repo (no token needed).
"""

import sys
sys.path.insert(0, 'd:\\wadinternal\\GitRepoMind\\server')
sys.path.insert(0, 'd:\\wadinternal\\GitRepoMind\\server\\src')

from src.services.github_service import GitHubService

def main():
    print("=" * 80)
    print("GitRepoMind Full Pipeline Test")
    print("=" * 80)
    
    # Using a small, clean public repo for testing
    repo_url = "https://github.com/ROHANGINJUPALLI18/Chat_Appilication"
    branch = "main"
    
    print(f"\nTesting with repository: {repo_url}")
    print(f"Branch: {branch}")
    print("\nThis will demonstrate:")
    print("  1. File filtering (skip node_modules, binaries, etc.)")
    print("  2. File content fetching from GitHub API")
    print("  3. Text chunking with type-specific strategies")
    print("  4. Metadata tracking (line numbers, token counts)")
    
    # Initialize service
    service = GitHubService()
    
    # Run the full pipeline
    print("\n" + "=" * 80)
    print("STARTING PIPELINE EXECUTION")
    print("=" * 80)
    
    try:
        service.process_repository(repo_url, branch)
        print("\n" + "=" * 80)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 80)
    except Exception as e:
        print(f"\nPipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
