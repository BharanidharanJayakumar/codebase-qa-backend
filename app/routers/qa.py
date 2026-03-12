import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
import httpx

from app.dependencies import get_http_client
from app.services.agent_client import call_agent
from app.services.auth import AuthUser, get_optional_user
from app.services import supabase_db as db
from app.middleware.rate_limit import limiter, GUEST_QUESTION_LIMIT, AUTH_QUESTION_LIMIT
from app.schemas.qa import (
    AnswerQuestionRequest,
    FindRelevantFilesRequest,
    GetFileContentRequest,
    ListProjectFilesRequest,
    ProjectSummaryRequest,
    ProjectCategoriesRequest,
    ProjectImportsRequest,
    SearchCodeRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["qa"])


@router.post("/answer")
@limiter.limit(AUTH_QUESTION_LIMIT)
async def answer_question(
    request: Request,
    body: AnswerQuestionRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    """SSE endpoint — streams the answer as text/event-stream.
    If user is authenticated, persists the Q&A turn to Supabase."""
    if user:
        logger.info("Q&A request from user %s", user.id)

    async def event_generator():
        result = await call_agent(
            client, "qa_answer_question", body.model_dump(exclude_none=True)
        )

        # Persist the turn to Supabase if user is authenticated
        if user and body.session_id and body.project_path:
            try:
                # Ensure session exists
                project_id = body.project_path.rsplit("/", 1)[-1] if "/" in body.project_path else body.project_path
                db.ensure_session(user.id, project_id, body.session_id)
                db.touch_project(project_id)

                # Get the current turn count for this session
                history = db.load_chat_history(body.session_id)
                turn_index = len(history)

                # Auto-title session from first question
                if turn_index == 0:
                    title = body.question[:80].strip()
                    db.update_session_title(body.session_id, title)

                db.save_chat_turn(
                    session_id=body.session_id,
                    turn_index=turn_index,
                    question=body.question,
                    answer=result.get("answer", ""),
                    relevant_files=result.get("top_files", []),
                )
            except Exception as e:
                logger.error("Failed to persist turn: %s", e)

        yield f"data: {json.dumps({'type': 'delta', 'text': result.get('answer', '')})}\n\n"
        yield f"data: {json.dumps({'type': 'done', **result})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/files")
async def find_relevant_files(
    body: FindRelevantFilesRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    return await call_agent(
        client, "qa_find_relevant_files", body.model_dump(exclude_none=True)
    )


@router.get("/projects")
async def list_projects(
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    """List projects. If authenticated, returns user's Supabase projects.
    Falls back to engine projects for unauthenticated users."""
    if user:
        user_projects = db.list_user_projects(user.id)
        # Authenticated users only see their own projects (no engine fallback)
        normalized = []
        if user_projects:
            for p in user_projects:
                indexed_at = p.get("indexed_at", "")
                # Convert ISO string to epoch if needed
                if isinstance(indexed_at, str) and indexed_at:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(indexed_at.replace("Z", "+00:00"))
                        indexed_at = dt.timestamp()
                    except ValueError:
                        indexed_at = 0
                normalized.append({
                    "project_id": p["id"],
                    "slug": p["slug"],
                    "project_root": p["project_root"],
                    "github_url": p.get("github_url"),
                    "total_files": p.get("total_files", 0),
                    "indexed_at": indexed_at,
                })
        return {"projects": normalized, "total": len(normalized)}
    # Unauthenticated users: show engine projects (legacy/demo mode)
    return await call_agent(client, "qa_list_projects", {})


@router.post("/file-content")
async def get_file_content(
    body: GetFileContentRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    return await call_agent(
        client, "qa_get_file_content", body.model_dump(exclude_none=True)
    )


@router.post("/project-files")
async def list_project_files(
    body: ListProjectFilesRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    return await call_agent(
        client, "qa_list_project_files", body.model_dump()
    )


@router.get("/sessions/{session_id}")
async def get_session_history(
    session_id: str,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    """Get session history. Tries Supabase first, falls back to engine."""
    if user:
        turns = db.load_chat_history(session_id)
        if turns:
            return {"session_id": session_id, "turns": turns}
    return await call_agent(
        client, "qa_get_session_history", {"session_id": session_id}
    )


@router.get("/user/sessions")
async def list_user_sessions(
    project_id: str | None = None,
    slug: str | None = None,
    user: AuthUser | None = Depends(get_optional_user),
):
    """List all chat sessions for a user's project (by project_id or slug)."""
    if not user:
        return {"sessions": []}
    pid = project_id
    if not pid and slug:
        project = db.get_project_by_slug(user.id, slug)
        if project:
            pid = project["id"]
    if not pid:
        return {"sessions": []}
    sessions = db.list_project_sessions(user.id, pid)
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: AuthUser | None = Depends(get_optional_user),
):
    """Delete a chat session and its turns."""
    if not user:
        return {"deleted": False, "error": "Authentication required"}
    deleted = db.delete_session(user.id, session_id)
    return {"deleted": deleted, "session_id": session_id}


@router.get("/user/me")
async def get_current_user_info(
    user: AuthUser | None = Depends(get_optional_user),
):
    """Return current authenticated user info, or null."""
    if not user:
        return {"user": None}
    project_count = len(db.list_user_projects(user.id))
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "is_anonymous": user.is_anonymous,
            "project_count": project_count,
        }
    }


@router.post("/project-summary")
async def get_project_summary(
    body: ProjectSummaryRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    """Get project-level summary: languages, frameworks, dir tree, README, stats."""
    return await call_agent(
        client, "summary_get_project_overview", body.model_dump()
    )


@router.post("/project-categories")
async def get_project_categories(
    body: ProjectCategoriesRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    """Get categorized symbols (DTOs, routes, tests, services, etc.)."""
    return await call_agent(
        client, "summary_query_categories", body.model_dump(exclude_none=True)
    )


@router.post("/project-imports")
async def get_project_imports(
    body: ProjectImportsRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    """Get import graph data for visualization."""
    return await call_agent(
        client, "summary_query_imports", body.model_dump(exclude_none=True)
    )


@router.post("/search-code")
async def search_code(
    body: SearchCodeRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
    user: AuthUser | None = Depends(get_optional_user),
):
    """Grep-like code search across indexed files."""
    return await call_agent(
        client, "retrieval_search_code", body.model_dump(exclude_none=True)
    )
