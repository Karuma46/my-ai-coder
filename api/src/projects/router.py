from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status
from fastapi.responses import JSONResponse

from src.projects.dependencies import ProjectServiceDep
from src.projects.schemas import (
    AssignTodoRequest,
    CreateProjectRequest,
    CreateVersionRequest,
    CreateVersionTodoRequest,
    CreateWipTodoRequest,
    MergeTodoRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectTodoResponse,
    ProjectVersionResponse,
    ReleaseVersionRequest,
    UpdateProjectRequest,
    UpdateTodoRequest,
    UpdateVersionRequest,
)

router = APIRouter(prefix="/api/v1/projects")

ProjectId = Annotated[str, Path(alias="projectId", min_length=1)]
VersionId = Annotated[str, Path(alias="versionId", min_length=1)]
TodoId = Annotated[str, Path(alias="todoId", min_length=1)]


@router.get(
    "",
    response_model=ProjectListResponse,
    tags=["Projects"],
    summary="List projects for the sidebar",
)
async def list_projects(
    service: ProjectServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> dict[str, object]:
    items, next_cursor = await service.list_projects(limit=limit, cursor=cursor)
    return {"items": items, "next_cursor": next_cursor}


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects"],
    summary="Create a project",
)
async def create_project(
    payload: CreateProjectRequest,
    service: ProjectServiceDep,
) -> JSONResponse:
    project = await service.create_project(payload)
    body = ProjectResponse.model_validate(project).model_dump(mode="json", by_alias=True)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=body,
        headers={"Location": f"/api/v1/projects/{project.id}"},
    )


@router.get(
    "/{projectId}",
    response_model=ProjectResponse,
    tags=["Projects"],
    summary="Get a project roadmap",
)
async def get_project(project_id: ProjectId, service: ProjectServiceDep):
    return await service.get_project(project_id)


@router.patch(
    "/{projectId}",
    response_model=ProjectResponse,
    tags=["Projects"],
    summary="Update project metadata",
)
async def update_project(
    project_id: ProjectId,
    payload: UpdateProjectRequest,
    service: ProjectServiceDep,
):
    return await service.update_project(project_id, payload)


@router.delete(
    "/{projectId}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Projects"],
    summary="Delete a project and its roadmap",
)
async def delete_project(project_id: ProjectId, service: ProjectServiceDep) -> Response:
    await service.delete_project(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{projectId}/versions",
    response_model=ProjectVersionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Versions"],
    summary="Add a version to a project",
)
async def create_version(
    project_id: ProjectId,
    payload: CreateVersionRequest,
    service: ProjectServiceDep,
):
    return await service.create_version(project_id, payload)


@router.get(
    "/{projectId}/versions/{versionId}",
    response_model=ProjectVersionResponse,
    tags=["Versions"],
    summary="Get one version with its todos",
)
async def get_version(
    project_id: ProjectId,
    version_id: VersionId,
    service: ProjectServiceDep,
):
    return await service.get_version(project_id, version_id)


@router.patch(
    "/{projectId}/versions/{versionId}",
    response_model=ProjectVersionResponse,
    tags=["Versions"],
    summary="Update version metadata or workflow status",
)
async def update_version(
    project_id: ProjectId,
    version_id: VersionId,
    payload: UpdateVersionRequest,
    service: ProjectServiceDep,
):
    return await service.update_version(project_id, version_id, payload)


@router.delete(
    "/{projectId}/versions/{versionId}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Versions"],
    summary="Delete a version",
)
async def delete_version(
    project_id: ProjectId,
    version_id: VersionId,
    service: ProjectServiceDep,
) -> Response:
    await service.delete_version(project_id, version_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{projectId}/versions/{versionId}/release",
    response_model=ProjectVersionResponse,
    tags=["Versions"],
    summary="Release a completed version",
)
async def release_version(
    project_id: ProjectId,
    version_id: VersionId,
    service: ProjectServiceDep,
    payload: ReleaseVersionRequest | None = None,
):
    return await service.release_version(
        project_id,
        version_id,
        payload or ReleaseVersionRequest(),
    )


@router.post(
    "/{projectId}/versions/{versionId}/todos",
    response_model=ProjectTodoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Todos"],
    summary="Create a todo in a version",
)
async def create_version_todo(
    project_id: ProjectId,
    version_id: VersionId,
    payload: CreateVersionTodoRequest,
    service: ProjectServiceDep,
):
    return await service.create_version_todo(project_id, version_id, payload)


@router.post(
    "/{projectId}/wip/todos",
    response_model=ProjectTodoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Todos"],
    summary="Create an unassigned draft todo in WIP",
)
async def create_wip_todo(
    project_id: ProjectId,
    payload: CreateWipTodoRequest,
    service: ProjectServiceDep,
):
    return await service.create_wip_todo(project_id, payload)


@router.get(
    "/{projectId}/todos/{todoId}",
    response_model=ProjectTodoResponse,
    tags=["Todos"],
    summary="Get todo details",
)
async def get_todo(
    project_id: ProjectId,
    todo_id: TodoId,
    service: ProjectServiceDep,
):
    return await service.get_todo(project_id, todo_id)


@router.patch(
    "/{projectId}/todos/{todoId}",
    response_model=ProjectTodoResponse,
    tags=["Todos"],
    summary="Update todo details or status",
)
async def update_todo(
    project_id: ProjectId,
    todo_id: TodoId,
    payload: UpdateTodoRequest,
    service: ProjectServiceDep,
):
    return await service.update_todo(project_id, todo_id, payload)


@router.delete(
    "/{projectId}/todos/{todoId}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Todos"],
    summary="Delete a todo",
)
async def delete_todo(
    project_id: ProjectId,
    todo_id: TodoId,
    service: ProjectServiceDep,
) -> Response:
    await service.delete_todo(project_id, todo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{projectId}/todos/{todoId}/assign",
    response_model=ProjectTodoResponse,
    tags=["Todos"],
    summary="Assign a WIP todo to a version",
)
async def assign_todo(
    project_id: ProjectId,
    todo_id: TodoId,
    payload: AssignTodoRequest,
    service: ProjectServiceDep,
):
    return await service.assign_todo(project_id, todo_id, payload)


@router.post(
    "/{projectId}/todos/{todoId}/merge",
    response_model=ProjectTodoResponse,
    tags=["Todos"],
    summary="Merge a completed todo pull request",
)
async def merge_todo(
    project_id: ProjectId,
    todo_id: TodoId,
    service: ProjectServiceDep,
    payload: MergeTodoRequest | None = None,
):
    return await service.merge_todo(
        project_id,
        todo_id,
        payload or MergeTodoRequest(),
    )
