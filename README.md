# RepoSage - PR Intelligence Bot

A minimal GitHub App that listens to pull request events and posts AI-powered review comments.

## Features

- Handles `pull_request.opened` events
- Fetches PR title, description, commits, and changed files
- Retrieves 2-3 related files from the same directories
- Generates structured review using OpenRouter LLM
- Posts one consolidated comment per PR

## Project Structure

```
backend/
├── main.py                 # FastAPI app entry point
├── routes/
│   └── webhook.py         # Webhook handler
├── services/
│   ├── auth.py            # JWT generation & webhook verification
│   ├── github_client.py   # GitHub API client
│   ├── pr_analyzer.py     # PR data gathering
│   └── llm.py             # OpenRouter API integration
├── requirements.txt
└── .env.example
```

## Setup

### 1. Create GitHub App

1. Go to GitHub Settings → Developer settings → GitHub Apps
2. Create new GitHub App with:
   - **Webhook URL**: Your deployment URL (e.g., `https://your-app.railway.app/webhook`)
   - **Webhook secret**: Generate a random string
   - **Permissions**: Read access to `pull_requests`, `contents`, `commit`
   - **Events**: Subscribe to `Pull request`

### 2. Deploy to Railway

1. Create new Railway project
2. Connect GitHub repo
3. Add environment variables:
   ```
   GITHUB_APP_ID=<your-app-id>
   GITHUB_PRIVATE_KEY=<private-key-pem>
   GITHUB_WEBHOOK_SECRET=<webhook-secret>
   OPENROUTER_API_KEY=<your-openrouter-key>
   APP_URL=https://your-app.railway.app
   ```

### 3. Install App

1. Install the GitHub App on your account/organization
2. Select repositories to monitor

## Local Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your values

# Run
uvicorn main:app --reload --port 8000
```

### Testing Webhooks Locally

Use [smee.io](https://smee.io) to forward webhooks to localhost:

```bash
npx smee -u <your-smee-url> -t http://localhost:8000/webhook
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_APP_ID` | Yes | GitHub App ID |
| `GITHUB_PRIVATE_KEY` | Yes | Private key (PEM format, newlines as `\n`) |
| `GITHUB_WEBHOOK_SECRET` | Yes | Webhook secret for signature verification |
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key |
| `APP_URL` | No | Your app URL for OpenRouter headers |

## API Endpoints

- `GET /health` - Health check
- `POST /webhook/` - GitHub webhook endpoint

## Response Format

The bot posts comments in this format:

```
🔍 Summary:
(Brief overview of changes)

🧠 Key Insight:
(Cross-file issues, duplication, or inconsistencies)

⚠️ Risk:
(Potential problems or maintainability risks)

💡 Suggestion:
(Actionable fix)

🎯 Impact:
(What part of the system is affected)
```
