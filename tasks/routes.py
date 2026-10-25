"""Rutas HTTP del recurso `tasks`.

Sin lógica de negocio: cada función delega en `service.py`. Los ids ≤ 0 se
rechazan aquí con 422 (`gt=0`); que el id exista lo decide el servicio (404).
Los docstrings de las rutas son la descripción que muestra Swagger (`/docs`).
"""
from typing import Annotated, Any

from fastapi import APIRouter, Header, Path, Query, status

from tasks import service
from tasks.schemas import Task, TaskCreate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _error_response(description: str, detail: str) -> dict[str, Any]:
    """Entrada de `responses=` para Swagger: descripción y cuerpo `{"detail": ...}`."""
    return {
        "description": description,
        "content": {"application/json": {"example": {"detail": detail}}},
    }


@router.get(
    "",
    response_model=list[Task],
    responses={
        404: _error_response(
            "El usuario del filtro no existe", "No se encontró usuario: 999"
        ),
    },
)
def list_tasks(assignee_id: Annotated[int | None, Query(gt=0)] = None) -> list[Task]:
    """Lista las tareas en orden de creación (`id` ascendente).

    Con `assignee_id` devuelve solo las tareas de ese usuario.

    - **200**: la lista; vacía si no hay tareas (o el usuario no tiene ninguna).
    - **404**: el usuario de `assignee_id` no existe.
    - **422**: `assignee_id` no es un entero mayor que 0.
    """
    return service.list_tasks(assignee_id)


@router.get(
    "/{task_id}",
    response_model=Task,
    responses={404: _error_response("La tarea no existe", "No se encontró tarea: 999")},
)
def get_task(task_id: Annotated[int, Path(gt=0)]) -> Task:
    """Devuelve una tarea por su id.

    - **200**: la tarea.
    - **404**: no existe una tarea con ese id.
    - **422**: `task_id` no es un entero mayor que 0.
    """
    return service.get_task(task_id)


@router.post(
    "",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: _error_response(
            "El usuario de `assignee_id` no existe", "No se encontró usuario: 999"
        ),
        409: _error_response(
            "La `Idempotency-Key` ya se usó con un cuerpo distinto",
            service.IDEMPOTENCY_CONFLICT_MESSAGE,
        ),
    },
)
def create_task(
    data: TaskCreate,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> Task:
    """Crea una tarea, opcionalmente asignada a un usuario existente.

    Reintentos seguros con el header `Idempotency-Key`: si repites la petición con
    la misma clave y el mismo cuerpo, recibes la tarea original (mismo `id` y
    `created_at`) sin crear un duplicado, aunque la fecha límite ya haya vencido.
    La clave es global y una clave vacía se trata como ausente.

    - **201**: la tarea creada, o la original si es un reintento idempotente.
    - **404**: `assignee_id` no corresponde a ningún usuario.
    - **409**: la `Idempotency-Key` ya se usó con un cuerpo distinto.
    - **422**: el cuerpo no cumple el formato (título, `due_date` con formato
      `YYYY-MM-DD`, prioridad de 1 a 5, `assignee_id` mayor que 0) o la fecha
      límite está en el pasado (el "hoy" se calcula en `America/Mexico_City`).
    """
    return service.create_task(data, idempotency_key)
