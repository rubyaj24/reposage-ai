"""
GitHub API client for RepoSage.
Handles installation tokens and API calls.
"""

import httpx
from services.auth import get_installation_token


class GitHubClient:
    """GitHub API client using installation tokens."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, installation_id: int):
        self.installation_id = installation_id
        self._token = None
    
    async def _get_headers(self) -> dict:
        """Get headers with authentication token."""
        if not self._token:
            self._token = await get_installation_token(self.installation_id)
        
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    async def _get(self, endpoint: str) -> dict:
        """Make GET request to GitHub API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}{endpoint}",
                headers=await self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def _get_paginated(self, endpoint: str) -> list:
        """Make GET request and return all pages as list."""
        results = []
        async with httpx.AsyncClient() as client:
            url = f"{self.BASE_URL}{endpoint}"
            headers = await self._get_headers()
            
            while url:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
                
                # Handle pagination
                url = None
                if "next" in response.links:
                    url = response.links["next"]["url"]
        
        return results
    
    async def get_pr_files(self, repo: str, pr_number: int) -> list:
        """Get files changed in a PR."""
        return await self._get_paginated(f"/repos/{repo}/pulls/{pr_number}/files")
    
    async def get_commits(self, repo: str, pr_number: int) -> list:
        """Get commits in a PR."""
        return await self._get_paginated(f"/repos/{repo}/pulls/{pr_number}/commits")
    
    async def get_file_content(self, repo: str, file_path: str, ref: str = "main") -> str:
        """Get content of a file."""
        data = await self._get(f"/repos/{repo}/contents/{file_path}?ref={ref}")
        import base64
        return base64.b64decode(data["content"]).decode("utf-8")
    
    async def get_directory_files(self, repo: str, path: str = "", ref: str = "main") -> list:
        """List files in a directory."""
        try:
            data = await self._get(f"/repos/{repo}/contents/{path}?ref={ref}")
            return data if isinstance(data, list) else []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise
    
    async def post_comment(self, repo: str, pr_number: int, body: str) -> dict:
        """Post a comment on a PR."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/repos/{repo}/issues/{pr_number}/comments",
                headers=await self._get_headers(),
                json={"body": body}
            )
            response.raise_for_status()
            return response.json()
