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


class ProjectSummaryRequest(BaseModel):
    project_path: str


class ProjectCategoriesRequest(BaseModel):
    project_path: str
    category: Optional[str] = None


class ProjectImportsRequest(BaseModel):
    project_path: str
    file_path: Optional[str] = None


class SearchCodeRequest(BaseModel):
    query: str
    project_path: Optional[str] = None
