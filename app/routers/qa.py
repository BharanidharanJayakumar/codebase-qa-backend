import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import httpx

from app.dependencies import get_http_client
from app.services.agent_client import call_agent
from app.services.auth import AuthUser, get_optional_user
from app.services import supabase_db as db
from app.schemas.qa import (
    AnswerQuestionRequest,
    FindRelevantFilesRequest,
    GetFileContentRequest,
    ListProjectFilesRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["qa"])


@router.post("/answer")
async def answer_question(
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
        if user_projects:
            return {"projects": user_projects}
    # Fallback: list from engine (for unauthenticated or users with no saved projects)
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
    project_id: str,
    user: AuthUser | None = Depends(get_optional_user),
):
    """List all chat sessions for a user's project."""
    if not user:
        return {"sessions": []}
    sessions = db.list_project_sessions(user.id, project_id)
    return {"sessions": sessions}
