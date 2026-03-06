import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import httpx

from app.dependencies import get_http_client
from app.services.agent_client import call_agent
from app.services.auth import AuthUser, get_optional_user
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
    """SSE endpoint — streams the answer as text/event-stream."""
    if user:
        logger.info("Q&A request from user %s", user.id)

    async def event_generator():
        result = await call_agent(
            client, "qa_answer_question", body.model_dump(exclude_none=True)
        )
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
    return await call_agent(
        client, "qa_get_session_history", {"session_id": session_id}
    )
