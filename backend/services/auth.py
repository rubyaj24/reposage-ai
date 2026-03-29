"""
GitHub App authentication utilities.
Handles JWT generation and webhook signature verification.
"""

import os
import time
import hmac
import hashlib
from typing import Optional
import jwt
import httpx


def _get_private_key() -> str:
    """Get private key from environment, loading .env if needed."""
    # Try to load from environment first
    key = os.getenv("GITHUB_PRIVATE_KEY")
    if key:
        return key.replace("\\n", "\n")
    
    # Fallback: try loading from .env file directly
    from dotenv import load_dotenv
    # Get path to backend/.env relative to this file
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(backend_dir, '.env')
    load_dotenv(env_path)
    key = os.getenv("GITHUB_PRIVATE_KEY", "")
    # Replace literal \n with actual newlines
    return key.replace("\n", "\n")


def _get_app_id() -> str:
    """Get GitHub App ID from environment."""
    app_id = os.getenv("GITHUB_APP_ID")
    if app_id:
        return app_id
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    return os.getenv("GITHUB_APP_ID", "")


def _get_webhook_secret() -> str:
    """Get webhook secret from environment."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if secret:
        return secret
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    return os.getenv("GITHUB_WEBHOOK_SECRET", "")


def generate_jwt() -> str:
    """Generate JWT for GitHub App authentication."""
    private_key = _get_private_key()
    app_id = _get_app_id()
    
    if not private_key:
        raise ValueError("GITHUB_PRIVATE_KEY not set")
    
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,  # 10 minutes
        "iss": app_id
    }
    
    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    """Get installation access token for a GitHub App."""
    jwt_token = generate_jwt()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )
        response.raise_for_status()
        return response.json()["token"]


def verify_webhook_signature(payload: bytes, headers) -> bool:
    """
    Verify webhook signature from GitHub.
    Compares HMAC hex digest of payload with X-Hub-Signature-256 header.
    """
    webhook_secret = _get_webhook_secret()
    if not webhook_secret:
        return True  # Skip verification if no secret set
    
    signature = headers.get("x-hub-signature-256", "")
    if not signature:
        return False
    
    expected = "sha256=" + hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)
