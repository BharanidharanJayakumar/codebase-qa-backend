import logging

from fastapi import APIRouter, Depends
import httpx

from app.dependencies import get_http_client
from app.services.agent_client import call_agent
from app.services.auth import AuthUser, get_optional_user
from app.schemas.indexer import (
    IndexProjectRequest,
    CloneAndIndexRequest,
    UpdateIndexRequest,
    WatchProjectRequest,
    UnwatchProjectRequest,
    DeleteProjectRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["indexer"])


@router.post("/index")
async def index_project(
    body: IndexProjectRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    if user:
        logger.info("Index request from user %s", user.id)
    return await call_agent(client, "indexer_index_project", body.model_dump())


@router.post("/clone")
async def clone_and_index(
    body: CloneAndIndexRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    if user:
        logger.info("Clone+index request from user %s for %s", user.id, body.github_url)
    return await call_agent(client, "indexer_clone_and_index", body.model_dump())


@router.post("/update")
async def update_index(
    body: UpdateIndexRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    return await call_agent(client, "indexer_update_index", body.model_dump())


@router.post("/watch")
async def watch_project(
    body: WatchProjectRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    return await call_agent(client, "indexer_watch_project", body.model_dump())


@router.post("/unwatch")
async def unwatch_project(
    body: UnwatchProjectRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    return await call_agent(client, "indexer_unwatch_project", body.model_dump())


@router.delete("/project")
async def delete_project(
    body: DeleteProjectRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    return await call_agent(client, "indexer_delete_project", body.model_dump())
