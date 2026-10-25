"""Rutas HTTP del recurso `tasks`.

Sin lógica de negocio: cada función delega en `service.py`. Los ids ≤ 0 se
rechazan aquí con 422 (`gt=0`); que el id exista lo decide el servicio (404).
"""
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from tasks import service
from tasks.schemas import Task, TaskCreate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def list_tasks(assignee_id: Annotated[int | None, Query(gt=0)] = None) -> list[Task]:
    return service.list_tasks(assignee_id)


@router.get("/{task_id}", response_model=Task)
def get_task(task_id: Annotated[int, Path(gt=0)]) -> Task:
    return service.get_task(task_id)


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate) -> Task:
    return service.create_task(data)
