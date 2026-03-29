"""
LLM integration using OpenRouter API.
"""

import os
import httpx
from typing import Optional


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMService:
    """Handles LLM calls via OpenRouter."""
    
    MODEL = "anthropic/claude-3-haiku"
    
    async def analyze_pr(
        self,
        pr_title: str,
        pr_body: str,
        commit_message: str,
        changed_files: list,
        related_files: list
    ) -> str:
        """
        Analyze a PR and generate a structured review.
        Response is limited to 150 words as per requirements.
        """
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        # Build prompt with PR data
        prompt = self._build_prompt(
            pr_title, pr_body, commit_message, changed_files, related_files
        )
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": os.getenv("APP_URL", "https://reposage.app"),
                    "X-Title": "RepoSage"
                },
                json={
                    "model": self.MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a senior software engineer reviewing pull requests. Provide concise, actionable feedback. Focus on: code quality issues, potential bugs, security concerns, and maintainability. Keep response under 150 words."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 400
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            return data["choices"][0]["message"]["content"].strip()
    
    def _build_prompt(
        self,
        pr_title: str,
        pr_body: str,
        commit_message: str,
        changed_files: list,
        related_files: list
    ) -> str:
        """Build analysis prompt from PR data."""
        
        # Format changed files summary
        files_summary = "\n".join([
            f"- {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})"
            for f in changed_files[:10]  # Limit to 10 files
        ])
        
        # Format related files
        related_summary = ""
        for f in related_files:
            related_summary += f"\n### {f['path']}\n```\n{f['content']}\n```\n"
        
        # Format diffs
        diffs = ""
        for f in changed_files[:5]:  # Limit to 5 diffs
            if f.get("patch"):
                diffs += f"\n### {f['filename']}\n```diff\n{f['patch'][:1000]}\n```\n"
        
        prompt = f"""Review this pull request:

**Title:** {pr_title}

**Description:** {pr_body or 'No description provided'}

**Latest Commit:** {commit_message or 'No commit message'}

**Changed Files ({len(changed_files)} total):**
{files_summary}

**Diffs:**
{diffs}

**Related Files (for context):**
{related_summary}

Provide a structured review with: Summary, Key Insight, Risk, Suggestion, and Impact sections."""
        
        return prompt
