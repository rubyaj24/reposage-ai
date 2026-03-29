"""
PR Analysis service.
Collects PR data and related files for LLM analysis.
"""

from typing import Optional
from services.github_client import GitHubClient


class PRAnalyzer:
    """Analyzes pull requests by gathering relevant context."""
    
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
        ".rb", ".php", ".c", ".cpp", ".h", ".cs", ".swift", ".kt"
    }
    
    def __init__(self, github: GitHubClient):
        self.github = github
    
    async def get_changed_files(self, repo: str, pr_number: int) -> list:
        """Get list of changed files in PR with their diffs."""
        files = await self.github.get_pr_files(repo, pr_number)
        
        return [
            {
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "patch": f.get("patch", ""),
                "directory": "/".join(f["filename"].split("/")[:-1])
            }
            for f in files
        ]
    
    async def get_commits(self, repo: str, pr_number: int) -> list:
        """Get commits in the PR."""
        return await self.github.get_commits(repo, pr_number)
    
    async def get_related_files(
        self,
        repo: str,
        changed_files: list,
        max_files: int = 3
    ) -> list:
        """
        Get related files from the same directories as changed files.
        Prioritizes files in the most frequently changed directories.
        """
        if not changed_files:
            return []
        
        # Count directory occurrences
        dir_counts: dict[str, int] = {}
        for f in changed_files:
            directory = f.get("directory", "")
            if directory:
                dir_counts[directory] = dir_counts.get(directory, 0) + 1
        
        # Sort directories by frequency
        sorted_dirs = sorted(dir_counts.items(), key=lambda x: -x[1])
        
        related = []
        seen_files = {f["filename"] for f in changed_files}
        
        for directory, _ in sorted_dirs:
            if len(related) >= max_files:
                break
            
            files = await self.github.get_directory_files(repo, directory)
            
            for file_info in files:
                if len(related) >= max_files:
                    break
                
                if file_info.get("type") != "file":
                    continue
                
                filename = file_info.get("name", "")
                if not any(filename.endswith(ext) for ext in self.CODE_EXTENSIONS):
                    continue
                
                full_path = f"{directory}/{filename}" if directory else filename
                if full_path in seen_files:
                    continue
                
                try:
                    content = await self.github.get_file_content(repo, full_path)
                    related.append({
                        "path": full_path,
                        "name": filename,
                        "content": content[:2000]  # Limit content size
                    })
                    seen_files.add(full_path)
                except Exception:
                    continue
        
        return related
