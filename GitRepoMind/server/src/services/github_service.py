# lets have a serivce like when user comes and give the repo url and from the repourl , we need to find the name of the owner and the proejct name then we need to take the nesscary files that are needed mainly and log the to the consle for develoment purpose bu initally we need to get ask the repo url and then we need to find the owner name and the project name and then we need to get the nesscary files that are needed mainly and log the to the consle for develoment purpose

import os
import requests
from dotenv import load_dotenv

class GitHubService:
    # Initialize the GitHubService with the necessary configuration
    def __init__(self):
        load_dotenv()
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    # Extract owner and repo name from the provided repository URL 
    def get_repo_info(self, repo_url):
        # Extract owner and repo name from URL
        try:
            parts = repo_url.strip('/').split('/')
            owner = parts[-2]
            repo_name = parts[-1]
            return owner, repo_name
        except Exception as e:
            print(f"Error parsing repository URL: {e}")
            return None, None
        
    # Fetch the contents of the repository using GitHub API  
    def get_repo_files(self, owner, repo_name):
        api_url = f'https://api.github.com/repos/{owner}/{repo_name}/contents'
        try:
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
            files = response.json()
            return files
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repository contents: {e}")
            return None
    
    # Main function to process the repository URL and log necessary files
    def process_repository(self, repo_url):
        owner, repo_name = self.get_repo_info(repo_url)
        if not owner or not repo_name:
            print("Invalid repository URL.")
            return
        
        files = self.get_repo_files(owner, repo_name)
        if files is None:
            print("Could not fetch repository files.")
            return
        
        # Log the necessary files (for development purposes, we can log all files for now)
        print(f"Files in repository '{owner}/{repo_name}':")
        for file in files:
            print(f"- {file['name']}")
        
# Example usage
if __name__ == "__main__":
    github_service = GitHubService()
    repo_url = input("Enter the GitHub repository URL: ")
    github_service.process_repository(repo_url)
    