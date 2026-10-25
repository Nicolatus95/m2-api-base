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
IDEMPOTENCY_CONFLICT_MESSAGE = (
    "La clave de idempotencia ya se usó con un cuerpo distinto"
)


def local_date(instant: datetime) -> date:
    """Fecha que corresponde a un instante en la zona de negocio."""
    return instant.astimezone(BUSINESS_TIMEZONE).date()


def current_date() -> date:
    """Única vía para obtener "hoy"; los tests la sustituyen."""
    return local_date(datetime.now(timezone.utc))


def _replay(key: str, data: TaskCreate) -> Task | None:
    """Resuelve una clave de idempotencia ya registrada.

    Devuelve la tarea original si el cuerpo normalizado coincide, `None` si la clave
    es nueva y lanza el 409 si la clave se usó con un cuerpo distinto.
    """
    record = repository.find_by_key(key)
    if record is None:
        return None
    if record.body != data:
        raise errors.conflict(IDEMPOTENCY_CONFLICT_MESSAGE)
    return get_task(record.task_id)


def _require_user(user_id: int) -> None:
    """Falla con el 404 de `users` si el usuario no existe; no devuelve nada."""
    users_service.get_user(user_id)


def create_task(data: TaskCreate, idempotency_key: str | None = None) -> Task:
    """Crea una tarea, con soporte opcional de idempotencia.

    `data` ya llega validado en formato (422 de Pydantic). Orden de las reglas:

    1. Clave de idempotencia (vacía o de solo espacios cuenta como ausente): si ya
       se usó con el mismo cuerpo normalizado devuelve la tarea original; si se
       usó con otro cuerpo, 409.
    2. Fecha límite anterior a "hoy" (`current_date()`): 422.
    3. Asignado inexistente: 404 (el error lo levanta `users.service`).

    Solo cuando se crea la tarea se registra la clave: un fallo no la consume.
    """
    key = (idempotency_key or "").strip()
    if key:
        replayed = _replay(key, data)
        if replayed is not None:
            return replayed
    if data.due_date < current_date():
        raise errors.invalid_request("La fecha límite no puede estar en el pasado")
    if data.assignee_id is not None:
        _require_user(data.assignee_id)
    task = repository.add(**data.model_dump())
    if key:
        repository.remember_key(key, data, task.id)
    return task


def get_task(task_id: int) -> Task:
    """Devuelve la tarea con ese id; 404 si no existe."""
    task = repository.get(task_id)
    if task is None:
        raise errors.not_found("tarea", task_id)
    return task


def list_tasks(assignee_id: int | None = None) -> list[Task]:
    """Lista las tareas en orden de creación, todas o solo las de un usuario.

    Con `assignee_id` primero comprueba que el usuario exista (404 si no) y después
    filtra; un usuario existente sin tareas da una lista vacía.
    """
    if assignee_id is None:
        return repository.list_all()
    _require_user(assignee_id)
    return repository.list_by_assignee(assignee_id)