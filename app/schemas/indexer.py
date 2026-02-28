from pydantic import BaseModel


class IndexProjectRequest(BaseModel):
    project_path: str


class CloneAndIndexRequest(BaseModel):
    github_url: str


class UpdateIndexRequest(BaseModel):
    project_path: str


class WatchProjectRequest(BaseModel):
    project_path: str


class UnwatchProjectRequest(BaseModel):
    project_path: str


class DeleteProjectRequest(BaseModel):
    project_identifier: str
