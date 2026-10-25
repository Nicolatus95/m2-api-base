"""Almacén en memoria del recurso `tasks`.

Guarda las tareas y el registro de claves de idempotencia. Vive aquí, y no en
`service.py`, para que `reset()` limpie ambos a la vez entre tests.
"""
from datetime import date, datetime, timezone

from tasks.schemas import Task, TaskCreate

_tasks: dict[int, Task] = {}
_next_id: int = 1
_idempotency_keys: dict[str, tuple[TaskCreate, int]] = {}


def add(
    *,
    title: str,
    description: str | None,
    due_date: date,
    priority: int,
    assignee_id: int | None,
) -> Task:
    global _next_id
    task = Task(
        id=_next_id,
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
        assignee_id=assignee_id,
        created_at=datetime.now(timezone.utc),
    )
    _tasks[task.id] = task
    _next_id += 1
    return task


def get(task_id: int) -> Task | None:
    return _tasks.get(task_id)


def list_all() -> list[Task]:
    return list(_tasks.values())


def list_by_assignee(assignee_id: int) -> list[Task]:
    return [task for task in _tasks.values() if task.assignee_id == assignee_id]


def find_by_key(key: str) -> tuple[TaskCreate, int] | None:
    """Cuerpo normalizado e `id` de la tarea creada con esa clave, si existe."""
    return _idempotency_keys.get(key)


def remember_key(key: str, body: TaskCreate, task_id: int) -> None:
    _idempotency_keys[key] = (body, task_id)


def reset() -> None:
    """Deja el almacén vacío, sin datos semilla. Se usa entre tests."""
    global _next_id
    _tasks.clear()
    _idempotency_keys.clear()
    _next_id = 1
