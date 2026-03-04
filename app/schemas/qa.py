from pydantic import BaseModel
from typing import Optional


class AnswerQuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    project_path: Optional[str] = None


class FindRelevantFilesRequest(BaseModel):
    query: str
    project_path: Optional[str] = None


class GetFileContentRequest(BaseModel):
    file_path: str
    project_path: Optional[str] = None


class ListProjectFilesRequest(BaseModel):
    project_path: str
