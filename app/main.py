from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, indexer, qa


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.agent_base_url,
        timeout=httpx.Timeout(120.0),
    )
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="Codebase QA API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(indexer.router, prefix="/api/indexer")
app.include_router(qa.router, prefix="/api/qa")
