"""
RepoSage - PR Intelligence Bot
Minimal FastAPI app for GitHub App webhook handling.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os fljdvnfda;vnzc p
wfsnb qsfk nc
import logging

# Load .env from backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from routes.webhook import router as webhook_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RepoSage", version="1.0.1")

app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
