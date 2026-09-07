"""Almacén en memoria del recurso `reports`."""
import threading
import time
from datetime import datetime, timezone

from reports.schemas import Report

_reports: dict[int, Report] = {}
_next_id: int = 1
_lock = threading.Lock()


def add(*, user_id: int, title: str, body: str) -> Report:
    global _next_id
    # La asignación de id es una sección crítica: leer el contador, usarlo y
    # actualizarlo debe ocurrir de forma atómica frente a llamadas concurrentes.
    with _lock:
        new_id = _next_id
        time.sleep(0.001)  # simula el trabajo real entre leer y escribir
        report = Report(
            id=new_id,
            user_id=user_id,
            title=title,
            body=body,
            created_at=datetime.now(timezone.utc),
        )
        _reports[new_id] = report
        _next_id = new_id + 1
    return report


def get(report_id: int) -> Report | None:
    return _reports.get(report_id)


def list_all() -> list[Report]:
    return list(_reports.values())


def reset() -> None:
    global _next_id
    _reports.clear()
    _next_id = 1
