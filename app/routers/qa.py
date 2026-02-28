import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import httpx

from app.dependencies import get_http_client
from app.services.agent_client import call_agent
from app.schemas.qa import (
    AnswerQuestionRequest,
    FindRelevantFilesRequest,
    GetFileContentRequest,
)

router = APIRouter(tags=["qa"])


@router.post("/answer")
async def answer_question(
    body: AnswerQuestionRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """SSE endpoint — streams the answer as text/event-stream."""

    async def event_generator():
        # Call the agent (blocking for now — agent doesn't stream yet)
        result = await call_agent(
            client, "qa_answer_question", body.model_dump(exclude_none=True)
        )
        # Emit the answer as a delta event (for streaming UX)
        yield f"data: {json.dumps({'type': 'delta', 'text': result.get('answer', '')})}\n\n"
        # Emit the full response as done event
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
):
    return await call_agent(
        client, "qa_find_relevant_files", body.model_dump(exclude_none=True)
    )


@router.get("/projects")
async def list_projects(
    client: httpx.AsyncClient = Depends(get_http_client),
):
    return await call_agent(client, "qa_list_projects", {})


@router.post("/file-content")
async def get_file_content(
    body: GetFileContentRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
):
    return await call_agent(
        client, "qa_get_file_content", body.model_dump(exclude_none=True)
    )
