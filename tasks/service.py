"""Lógica de negocio del recurso `tasks`.

Las rutas no acceden al repositorio directamente: pasan por aquí. Esta capa es la
única que conoce `repository.py` y la que decide cuándo algo es un error de
dominio (usando `core.errors`).
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from core import errors
from tasks import repository
from tasks.schemas import Task, TaskCreate
from users import service as users_service

BUSINESS_TIMEZONE = ZoneInfo("America/Mexico_City")


def local_date(instant: datetime) -> date:
    """Fecha que corresponde a un instante en la zona de negocio."""
    return instant.astimezone(BUSINESS_TIMEZONE).date()


def current_date() -> date:
    """Única vía para obtener "hoy"; los tests la sustituyen."""
    return local_date(datetime.now(timezone.utc))


def create_task(data: TaskCreate) -> Task:
    if data.due_date < current_date():
        raise errors.invalid_request("La fecha límite no puede estar en el pasado")
    if data.assignee_id is not None:
        users_service.get_user(data.assignee_id)
    return repository.add(**data.model_dump())


def get_task(task_id: int) -> Task:
    task = repository.get(task_id)
    if task is None:
        raise errors.not_found("tarea", task_id)
    return task


def list_tasks(assignee_id: int | None = None) -> list[Task]:
    if assignee_id is None:
        return repository.list_all()
    users_service.get_user(assignee_id)
    return repository.list_by_assignee(assignee_id)