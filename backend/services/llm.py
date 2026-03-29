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
        Analyze a PR and generate a structured review with stat cards.
        """
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        # Calculate stats for stat cards
        stats = self._calculate_stats(changed_files)
        
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
                            "content": """You are a senior software engineer performing a pull request review.

Your goal is to identify only meaningful, evidence-based issues that a human reviewer would care about.

STRICT RULES:
- Do NOT give generic advice (e.g., "improve code quality", "add tests")
- Do NOT repeat obvious information from the diff
- Do NOT invent problems if none are clearly present
- Only report issues if confidence is medium or high
- Prefer silence over weak or speculative feedback

FOCUS ONLY ON:
- cross-file inconsistencies
- duplicated logic
- incorrect or risky changes
- missing validation or error handling
- breaking changes or side effects

IGNORE:
- style issues
- formatting
- trivial refactors
- anything already obvious from the diff

OUTPUT FORMAT (strict):

🔍 Summary:
(1-2 lines describing what changed)

🧠 Key Insight:
(ONLY if a real issue exists. Mention exact file(s) and reasoning.)

⚠️ Risk:
(ONLY if there is a concrete risk. Explain why.)

💡 Suggestion:
(Actionable fix directly tied to the issue)

IF NO SIGNIFICANT ISSUES:
Return exactly:
"No significant issues found. Changes look consistent."

CONSTRAINTS:
- Keep total response under 120 words
- Be precise and direct
- Avoid unnecessary explanation"""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 250
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            raw_review = data["choices"][0]["message"]["content"].strip()
            
            # Wrap with stat cards and formatting
            return self._format_with_stat_cards(raw_review, stats, pr_title)
    
    def _calculate_stats(self, changed_files: list) -> dict:
        """Calculate PR statistics for stat cards."""
        total_files = len(changed_files)
        total_additions = sum(f.get('additions', 0) for f in changed_files)
        total_deletions = sum(f.get('deletions', 0) for f in changed_files)
        
        # Determine risk level based on changes
        if total_deletions > 100 or total_additions > 200:
            risk_level = "High"
            risk_color = "red"
            risk_emoji = "🔴"
        elif total_deletions > 50 or total_additions > 100:
            risk_level = "Medium"
            risk_color = "yellow"
            risk_emoji = "🟡"
        else:
            risk_level = "Low"
            risk_color = "brightgreen"
            risk_emoji = "🟢"
        
        # Check for sensitive files
        sensitive_keywords = ['.env', 'config', 'password', 'secret', 'key', 'token', '.gitignore', '.pem', '.p12', '.pfx', 'credentials', 'private']
        sensitive_files = [f for f in changed_files if any(
            keyword in f['filename'].lower() 
            for keyword in sensitive_keywords
        )]
        
        if sensitive_files:
            risk_level = "High"
            risk_color = "red"
            risk_emoji = "🚨"
        
        return {
            "files": total_files,
            "additions": total_additions,
            "deletions": total_deletions,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "risk_emoji": risk_emoji,
            "total_changes": total_additions + total_deletions,
            "sensitive_files": len(sensitive_files)
        }
    
    def _format_with_stat_cards(self, review: str, stats: dict, pr_title: str) -> str:
        """Format the review with stat cards header."""
        
        # URL-encode risk level for shields.io
        risk_encoded = stats['risk_level'].replace(' ', '%20')
        
        # Create stat cards with shields.io badges
        stat_cards = f"""<div align="center">

### 🤖 RepoSage AI Review

<br/>

<table>
  <tr>
    <td align="center">
      <img src="https://img.shields.io/badge/📁%20Files-{stats['files']}-blue?style=for-the-badge" alt="Files"/>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/➕%20Additions-{stats['additions']}-green?style=for-the-badge" alt="Additions"/>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/➖%20Deletions-{stats['deletions']}-red?style=for-the-badge" alt="Deletions"/>
    </td>
    <td align="center">
      <img src="https://img.shields.io/badge/⚠️%20Risk-{risk_encoded}-{stats['risk_color']}?style=for-the-badge" alt="Risk"/>
    </td>
  </tr>
</table>

<br/>

| 📊 Metric | 📈 Value | 🔍 Details |
|:----------|:--------:|:-----------|
| 📝 Total Changes | **{stats['total_changes']}** lines | `+{stats['additions']}/-{stats['deletions']}` |
| 🔒 Security Check | {"⚠️ Issues Found" if stats['sensitive_files'] > 0 else "✅ Clear"} | {stats['sensitive_files']} sensitive file{'s' if stats['sensitive_files'] != 1 else ''} |
| 📊 Complexity | {stats['risk_emoji']} **{stats['risk_level']}** | Based on change scope |

</div>

---

"""
        
        # Simple footer
        footer = """

---
<sup>🤖 RepoSage AI</sup>
"""
        
        return stat_cards + review + footer
    
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
            for f in changed_files[:10]
        ])
        
        # Format related files
        related_summary = ""
        for f in related_files:
            related_summary += f"\n### {f['path']}\n```\n{f['content'][:500]}\n```\n"
        
        # Format diffs
        diffs = ""
        for f in changed_files[:5]:
            if f.get("patch"):
                diffs += f"\n### {f['filename']}\n```diff\n{f['patch'][:800]}\n```\n"
        
        # Format related files for context
        related = ""
        for f in related_files:
            related += f"\n{f['path']}:\n{f['content'][:300]}\n"
        
        prompt = f"""Title: {pr_title}
Commit: {commit_message or "N/A"}

---

CHANGES (diff):

{diffs or "No diff available"}

---

RELATED CODE (for comparison):

{related or "No related context"}

---

TASK:

Analyze the PR changes and identify ONLY meaningful issues.

Focus on:
- duplicated logic across files
- missing validation or error handling
- risky or breaking changes

IMPORTANT:
- Compare CHANGES with RELATED CODE
- Be specific (mention file names)
- Do NOT give generic advice
- Do NOT repeat obvious info
- Only report if confident

Return output using required format."""
        
        return prompt
