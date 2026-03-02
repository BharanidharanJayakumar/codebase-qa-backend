# Codebase QA Backend

Thin FastAPI proxy that connects the web frontend to the Codebase QA Agent engine. Handles CORS, SSE streaming, and request routing.

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

## Architecture

```
Frontend (Next.js) → Backend (FastAPI) → Engine (Agentfield)
     :3000              :8000               :8080
```

The backend is a zero-logic proxy. All indexing, retrieval, and LLM reasoning happens in the engine.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AGENT_BASE_URL` | `http://localhost:8080` | Agentfield agent URL |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

## Docker

```bash
docker build -t codebase-qa-backend .
docker run -p 8000:8000 -e AGENT_BASE_URL=http://host.docker.internal:8080 codebase-qa-backend
```

## Related Repos

- [codebase-qa-agent](https://github.com/BharanidharanJayakumar/codebase-qa-agent) — RAG engine
- [codebase-qa-frontend](https://github.com/BharanidharanJayakumar/codebase-qa-frontend) — Next.js web UI
