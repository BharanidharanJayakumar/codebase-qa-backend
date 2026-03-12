import logging

from fastapi import APIRouter, Depends, HTTPException
import httpx

from app.dependencies import get_http_client
from app.services.agent_client import call_agent
from app.services.auth import AuthUser, get_optional_user
from app.services import supabase_db as db
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
    result = await call_agent(client, "indexer_index_project", body.model_dump())

    # Save project to Supabase for authenticated users
    if user and result.get("status") == "ok":
        project_id = result.get("project_id", "")
        slug = result.get("slug", "")
        db.save_user_project(
            user_id=user.id,
            project_id=project_id,
            slug=slug,
            project_root=body.project_path,
            total_files=result.get("total_files", 0),
        )

    return result


@router.post("/clone")
async def clone_and_index(
    body: CloneAndIndexRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    if user:
        logger.info("Clone+index from user %s for %s", user.id, body.github_url)
    result = await call_agent(client, "indexer_clone_and_index", body.model_dump())

    # Check for engine-level errors (e.g. private repo, invalid URL)
    if result.get("error"):
        error_type = result.get("error_type", "")
        error_msg = result["error"]

        if error_type == "repo_not_accessible":
            raise HTTPException(
                status_code=403,
                detail="This repository is private or does not exist. Only public repositories are supported.",
            )
        elif error_type == "invalid_url":
            raise HTTPException(status_code=422, detail=error_msg)
        elif error_type == "timeout":
            raise HTTPException(status_code=504, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)

    # Derive slug from owner_repo
    owner_repo = result.get("owner_repo", "")
    slug = owner_repo.replace("/", "-") if owner_repo else ""

    # Save project to Supabase for authenticated users
    if user and slug:
        import uuid
        project_id = result.get("project_id") or str(uuid.uuid4())
        project_root = result.get("project_root", "")
        db.save_user_project(
            user_id=user.id,
            project_id=project_id,
            slug=slug,
            project_root=project_root,
            github_url=body.github_url,
            total_files=result.get("files_indexed", 0),
        )

    # Ensure slug is always in the response
    result["slug"] = slug
    return result


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
    result = await call_agent(client, "indexer_delete_project", body.model_dump())

    # Also remove from Supabase
    if user:
        db.delete_user_project(user.id, body.project_identifier)

    return result
