import os
import requests
import base64
from dotenv import load_dotenv


class GitHubService:

    def __init__(self):
        load_dotenv()
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.owner = None       # ✅ initialize instance variables
        self.repo_name = None

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
        """
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

            # GitHub returns content as base64 encoded
            content = base64.b64decode(data["content"]).decode("utf-8")
            return content
        except requests.exceptions.RequestException as e:
            print(f"Error fetching file '{file_path}': {e}")
            return None
        except UnicodeDecodeError:
            print(f"Skipping binary file: {file_path}")
            return None

    def process_repository(self, repo_url, branch="main"):
        owner, repo_name = self.get_repo_info(repo_url)
        if not owner or not repo_name:
            print("Invalid repository URL.")
            return

        print(f"\nFetching all files from '{owner}/{repo_name}' on branch '{branch}'...\n")

        files = self.get_all_files(branch)
        if not files:
            print("No files found or failed to fetch.")
            return

        print(f"Found {len(files)} files:\n")
        for file in files:
            print(f"   {file['path']}") 

        print("\n--- Fetching file contents ---\n")
        for file in files:
            path = file["path"]
            print(f"\n{'='*60}")
            print(f"File: {path}")
            print('='*60)
            content = self.get_file_content(path, branch)
            if content:
                print(content)


# Example usage
if __name__ == "__main__":
    github_service = GitHubService()
    repo_url = input("Enter the GitHub repository URL: ")
    branch = input("Enter branch name (default: main): ").strip() or "main"
    github_service.process_repository(repo_url, branch)