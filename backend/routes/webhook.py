"""
Webhook handler for GitHub App events.
"""

from fastapi import APIRouter, Request, HTTPException, Header
import logging
import hmac
import hashlib
import json

from services.auth import verify_webhook_signature
from services.github_client import GitHubClient
from services.pr_analyzer import PRAnalyzer
from services.llm import LLMService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/")
async def handle_webhook(request: Request, x_github_event: str = Header(None)):
    """
    Handle incoming GitHub webhook events.
    Only processes pull_request events with action=opened.
    """
    body = await request.json()
    
    # Verify webhook signature (skip for development)
    # In production, uncomment:
    # payload = await request.body()
    # if not verify_webhook_signature(payload, request.headers):
    #     raise HTTPException(status_code=401, detail="Invalid signature")
    
    logger.info(f"Received event: {x_github_event}")
    
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"Event {x_github_event} not handled"}
    
    action = body.get("action")
    if action != "opened":
        return {"status": "ignored", "reason": f"Action {action} not handled"}
    
    # Extract PR info
    pr = body["pull_request"]
    repo = body["repository"]
    installation_id = body["installation"]["id"]
    
    pr_data = {
        "number": pr["number"],
        "title": pr["title"],
        "body": pr["body"] or "",
        "head_sha": pr["head"]["sha"],
        "repo_name": repo["full_name"],
        "repo_owner": repo["owner"]["login"],
        "repo_name_only": repo["name"],
    }
    
    logger.info(f"Processing PR #{pr_data['number']}: {pr_data['title']}")
    
    try:
        github = GitHubClient(installation_id)
        analyzer = PRAnalyzer(github)
        llm = LLMService()
        
        # Fetch PR data
        files = await analyzer.get_changed_files(pr_data["repo_name"], pr_data["number"])
        commits = await analyzer.get_commits(pr_data["repo_name"], pr_data["number"])
        commit_message = commits[0]["commit"]["message"] if commits else ""
        
        # Fetch related files
        related_files = await analyzer.get_related_files(
            pr_data["repo_name"],
            files,
            max_files=3
        )
        
        # Build prompt and call LLM
        review = await llm.analyze_pr(
            pr_title=pr_data["title"],
            pr_body=pr_data["body"],
            commit_message=commit_message,
            changed_files=files,
            related_files=related_files
        )
        
        # Post comment
        await github.post_comment(
            pr_data["repo_name"],
            pr_data["number"],
            review
        )
        
        logger.info(f"Posted review comment on PR #{pr_data['number']}")
        return {"status": "success", "review": review[:100] + "..."}
        
    except Exception as e:
        logger.error(f"Error processing PR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
