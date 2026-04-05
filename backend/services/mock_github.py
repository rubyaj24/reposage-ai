"""
Mock GitHub client for development/testing.
"""


class MockGitHubClient:
    """Mock GitHub client that simulates API responses."""
    
    def __init__(self, installation_id: int):
        self.installation_id = installation_id
        self.comments = []
    
    async def get_pr_files(self, repo: str, pr_number: int) -> list:
        return [
            {
                "filename": "README.md",
                "status": "modified",
                "additions": 5,
                "deletions": 2,
                "patch": "@@ -1,5 +1,8 @@\n # Title\n+New line\n Old content"
            }
        ]
    
    async def get_commits(self, repo: str, pr_number: int) -> list:
        return [
            {
                "sha": "abc123",
                "commit": {
                    "message": "Update README"
                }
            }
        ]
    
    async def get_file_content(self, repo: str, file_path: str, ref: str = "main") -> str:
        return "# Sample file content"
    
    async def get_directory_files(self, repo: str, path: str = "", ref: str = "main") -> list:
        return [
            {"name": "example.py", "type": "file", "path": f"{path}/example.py"},
            {"name": "utils.py", "type": "file", "path": f"{path}/utils.py"}
        ]
    
    async def post_comment(self, repo: str, pr_number: int, body: str) -> dict:
        self.comments.append({"repo": repo, "pr": pr_number, "body": body})
        print(f"[MOCK] Posted comment to {repo} PR #{pr_number}")
        return {"id": 1, "body": body}
