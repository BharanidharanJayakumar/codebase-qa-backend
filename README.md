# Codebase QA Backend

Thin FastAPI proxy that connects the web frontend to the Codebase QA Agent engine.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/indexer/clone` | Clone and index a GitHub repo |
| POST | `/api/indexer/index` | Index a local project |
| POST | `/api/indexer/update` | Incremental index update |
| POST | `/api/indexer/watch` | Start file watcher |
| POST | `/api/indexer/unwatch` | Stop file watcher |
| DELETE | `/api/indexer/project` | Delete an indexed project |
| POST | `/api/qa/answer` | Ask a question (SSE stream) |
| POST | `/api/qa/files` | Find relevant files |
| GET | `/api/qa/projects` | List all indexed projects |
| POST | `/api/qa/file-content` | Get file source code |

## Environment Variables

- `AGENT_BASE_URL` — Agentfield agent URL (default: `http://localhost:8080`)
- `CORS_ORIGINS` — Comma-separated allowed origins
